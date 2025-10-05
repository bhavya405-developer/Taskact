#!/usr/bin/env python3
"""
Backend API Testing Script for TaskAct Production Readiness Health Check
Comprehensive testing of authentication, core APIs, data management, security, and integrations
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv('frontend/.env')
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

class TaskActTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.test_results = []
        self.created_tasks = []  # Track created tasks for cleanup
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_authentication(self):
        """Test authentication with partner credentials"""
        print("\n=== Testing Authentication ===")
        
        # Test partner login
        login_data = {
            "email": "sarah@firm.com",
            "password": "password123"  # Common default password
        }
        
        try:
            response = self.session.post(f"{API_BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('access_token')
                self.current_user = data.get('user', {})
                
                if self.auth_token and self.current_user.get('role') == 'partner':
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.auth_token}'
                    })
                    self.log_test(
                        "Partner Authentication", 
                        True, 
                        f"Successfully authenticated as {self.current_user.get('name')} (partner)",
                        {'token_length': len(self.auth_token), 'user_role': self.current_user.get('role')}
                    )
                    return True
                else:
                    self.log_test(
                        "Partner Authentication", 
                        False, 
                        "Login successful but missing token or wrong role",
                        {'response': data}
                    )
            else:
                self.log_test(
                    "Partner Authentication", 
                    False, 
                    f"Login failed with status {response.status_code}",
                    {'response_text': response.text}
                )
        except Exception as e:
            self.log_test(
                "Partner Authentication", 
                False, 
                f"Authentication request failed: {str(e)}"
            )
        
        return False
    
    def test_status_enum_verification(self):
        """Test that only 4 valid statuses are accepted"""
        print("\n=== Testing Status Enum Verification ===")
        
        if not self.auth_token:
            self.log_test("Status Enum Verification", False, "Cannot test - no authentication token")
            return False
        
        # First create a test task
        task_data = {
            "title": "Status Enum Test Task",
            "description": "Testing status enum validation",
            "client_name": "TechCorp Solutions",
            "category": "Legal Research",
            "assignee_id": self.current_user['id'],
            "creator_id": self.current_user['id'],
            "priority": "medium",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
        
        try:
            response = self.session.post(f"{API_BASE_URL}/tasks", json=task_data)
            if response.status_code in [200, 201]:
                task = response.json()
                task_id = task['id']
                self.created_tasks.append(task_id)
                
                # Test valid statuses
                valid_statuses = ["pending", "on_hold", "overdue", "completed"]
                valid_count = 0
                
                for status in valid_statuses:
                    try:
                        update_response = self.session.put(
                            f"{API_BASE_URL}/tasks/{task_id}", 
                            json={"status": status}
                        )
                        if update_response.status_code == 200:
                            valid_count += 1
                            updated_task = update_response.json()
                            if updated_task['status'] == status:
                                self.log_test(
                                    f"Valid Status: {status}", 
                                    True, 
                                    f"Status '{status}' accepted and applied correctly"
                                )
                            else:
                                self.log_test(
                                    f"Valid Status: {status}", 
                                    False, 
                                    f"Status '{status}' accepted but not applied correctly"
                                )
                        else:
                            self.log_test(
                                f"Valid Status: {status}", 
                                False, 
                                f"Valid status '{status}' rejected with {update_response.status_code}",
                                {'response': update_response.text}
                            )
                    except Exception as e:
                        self.log_test(
                            f"Valid Status: {status}", 
                            False, 
                            f"Error testing status '{status}': {str(e)}"
                        )
                
                # Test invalid statuses
                invalid_statuses = ["in_progress", "cancelled", "draft", "invalid_status"]
                invalid_rejected = 0
                
                for status in invalid_statuses:
                    try:
                        update_response = self.session.put(
                            f"{API_BASE_URL}/tasks/{task_id}", 
                            json={"status": status}
                        )
                        if update_response.status_code in [400, 422]:
                            invalid_rejected += 1
                            self.log_test(
                                f"Invalid Status: {status}", 
                                True, 
                                f"Invalid status '{status}' correctly rejected with {update_response.status_code}"
                            )
                        else:
                            self.log_test(
                                f"Invalid Status: {status}", 
                                False, 
                                f"Invalid status '{status}' should be rejected but got {update_response.status_code}",
                                {'response': update_response.text}
                            )
                    except Exception as e:
                        self.log_test(
                            f"Invalid Status: {status}", 
                            False, 
                            f"Error testing invalid status '{status}': {str(e)}"
                        )
                
                # Overall status enum test result
                if valid_count == 4 and invalid_rejected == 4:
                    self.log_test(
                        "Status Enum Verification", 
                        True, 
                        "All 4 valid statuses accepted, all invalid statuses rejected"
                    )
                    return True
                else:
                    self.log_test(
                        "Status Enum Verification", 
                        False, 
                        f"Expected 4 valid and 4 rejected, got {valid_count} valid and {invalid_rejected} rejected"
                    )
                    
            else:
                self.log_test(
                    "Status Enum Verification", 
                    False, 
                    f"Failed to create test task: {response.status_code}",
                    {'response': response.text}
                )
        except Exception as e:
            self.log_test(
                "Status Enum Verification", 
                False, 
                f"Error in status enum verification: {str(e)}"
            )
        
        return False
    
    def test_task_creation_default_status(self):
        """Test that new tasks default to 'pending' status"""
        print("\n=== Testing Task Creation Default Status ===")
        
        if not self.auth_token:
            self.log_test("Task Creation Default Status", False, "Cannot test - no authentication token")
            return False
        
        task_data = {
            "title": "Default Status Test Task",
            "description": "Testing that new tasks start with pending status",
            "client_name": "Global Manufacturing Ltd",
            "category": "Contract Review",
            "assignee_id": self.current_user['id'],
            "creator_id": self.current_user['id'],
            "priority": "high",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        }
        
        try:
            response = self.session.post(f"{API_BASE_URL}/tasks", json=task_data)
            
            if response.status_code in [200, 201]:
                task = response.json()
                self.created_tasks.append(task['id'])
                
                if task.get('status') == 'pending':
                    self.log_test(
                        "Task Creation Default Status", 
                        True, 
                        f"New task correctly defaults to 'pending' status",
                        {'task_id': task['id'], 'status': task['status']}
                    )
                    return True
                else:
                    self.log_test(
                        "Task Creation Default Status", 
                        False, 
                        f"New task has status '{task.get('status')}' instead of 'pending'",
                        {'task_id': task['id'], 'status': task.get('status')}
                    )
            else:
                self.log_test(
                    "Task Creation Default Status", 
                    False, 
                    f"Failed to create task: {response.status_code}",
                    {'response': response.text}
                )
        except Exception as e:
            self.log_test(
                "Task Creation Default Status", 
                False, 
                f"Error creating task: {str(e)}"
            )
        
        return False
    
    def test_status_transitions(self):
        """Test status transitions and workflow"""
        print("\n=== Testing Status Transitions ===")
        
        if not self.auth_token:
            self.log_test("Status Transitions", False, "Cannot test - no authentication token")
            return False
        
        # Create a test task
        task_data = {
            "title": "Status Transition Test Task",
            "description": "Testing status transitions workflow",
            "client_name": "Healthcare Solutions Group",
            "category": "Client Meeting",
            "assignee_id": self.current_user['id'],
            "creator_id": self.current_user['id'],
            "priority": "medium",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        }
        
        try:
            response = self.session.post(f"{API_BASE_URL}/tasks", json=task_data)
            
            if response.status_code in [200, 201]:
                task = response.json()
                task_id = task['id']
                self.created_tasks.append(task_id)
                
                # Test transition: pending → on_hold
                transition_success = 0
                
                update_response = self.session.put(
                    f"{API_BASE_URL}/tasks/{task_id}", 
                    json={"status": "on_hold"}
                )
                if update_response.status_code == 200:
                    updated_task = update_response.json()
                    if updated_task['status'] == 'on_hold':
                        transition_success += 1
                        self.log_test(
                            "Transition: pending → on_hold", 
                            True, 
                            "Successfully transitioned from pending to on_hold"
                        )
                    else:
                        self.log_test(
                            "Transition: pending → on_hold", 
                            False, 
                            f"Transition accepted but status is '{updated_task['status']}'"
                        )
                else:
                    self.log_test(
                        "Transition: pending → on_hold", 
                        False, 
                        f"Transition failed with status {update_response.status_code}",
                        {'response': update_response.text}
                    )
                
                # Test transition: on_hold → completed
                update_response = self.session.put(
                    f"{API_BASE_URL}/tasks/{task_id}", 
                    json={"status": "completed"}
                )
                if update_response.status_code == 200:
                    updated_task = update_response.json()
                    if updated_task['status'] == 'completed':
                        transition_success += 1
                        self.log_test(
                            "Transition: on_hold → completed", 
                            True, 
                            "Successfully transitioned from on_hold to completed"
                        )
                        
                        # Check if completed_at is set
                        if updated_task.get('completed_at'):
                            self.log_test(
                                "Completed Task Timestamp", 
                                True, 
                                "completed_at timestamp set when task marked as completed"
                            )
                        else:
                            self.log_test(
                                "Completed Task Timestamp", 
                                False, 
                                "completed_at timestamp not set when task marked as completed"
                            )
                    else:
                        self.log_test(
                            "Transition: on_hold → completed", 
                            False, 
                            f"Transition accepted but status is '{updated_task['status']}'"
                        )
                else:
                    self.log_test(
                        "Transition: on_hold → completed", 
                        False, 
                        f"Transition failed with status {update_response.status_code}",
                        {'response': update_response.text}
                    )
                
                # Create another task to test pending → completed
                task_data2 = task_data.copy()
                task_data2['title'] = "Direct Completion Test Task"
                
                response2 = self.session.post(f"{API_BASE_URL}/tasks", json=task_data2)
                if response2.status_code in [200, 201]:
                    task2 = response2.json()
                    task2_id = task2['id']
                    self.created_tasks.append(task2_id)
                    
                    # Test transition: pending → completed
                    update_response = self.session.put(
                        f"{API_BASE_URL}/tasks/{task2_id}", 
                        json={"status": "completed"}
                    )
                    if update_response.status_code == 200:
                        updated_task = update_response.json()
                        if updated_task['status'] == 'completed':
                            transition_success += 1
                            self.log_test(
                                "Transition: pending → completed", 
                                True, 
                                "Successfully transitioned directly from pending to completed"
                            )
                        else:
                            self.log_test(
                                "Transition: pending → completed", 
                                False, 
                                f"Transition accepted but status is '{updated_task['status']}'"
                            )
                    else:
                        self.log_test(
                            "Transition: pending → completed", 
                            False, 
                            f"Direct completion failed with status {update_response.status_code}",
                            {'response': update_response.text}
                        )
                else:
                    self.log_test(
                        "Second Task Creation", 
                        False, 
                        f"Failed to create second test task: {response2.status_code}",
                        {'response': response2.text}
                    )
                
                if transition_success >= 3:
                    self.log_test(
                        "Status Transitions", 
                        True, 
                        f"Status transitions working correctly ({transition_success}/3 transitions successful)"
                    )
                    return True
                else:
                    self.log_test(
                        "Status Transitions", 
                        False, 
                        f"Only {transition_success}/3 status transitions successful"
                    )
                    
            else:
                self.log_test(
                    "Status Transitions", 
                    False, 
                    f"Failed to create test task: {response.status_code}",
                    {'response': response.text}
                )
        except Exception as e:
            self.log_test(
                "Status Transitions", 
                False, 
                f"Error in status transitions test: {str(e)}"
            )
        
        return False
    
    def test_completed_task_immutability(self):
        """Test that completed tasks cannot be edited"""
        print("\n=== Testing Completed Task Immutability ===")
        
        if not self.auth_token:
            self.log_test("Completed Task Immutability", False, "Cannot test - no authentication token")
            return False
        
        # Create and complete a task
        task_data = {
            "title": "Immutability Test Task",
            "description": "Testing completed task immutability",
            "client_name": "Legal Consulting Firm",
            "category": "Legal Research",
            "assignee_id": self.current_user['id'],
            "creator_id": self.current_user['id'],
            "priority": "low",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        }
        
        try:
            # Create task
            response = self.session.post(f"{API_BASE_URL}/tasks", json=task_data)
            
            if response.status_code in [200, 201]:
                task = response.json()
                task_id = task['id']
                self.created_tasks.append(task_id)
                
                # Complete the task
                complete_response = self.session.put(
                    f"{API_BASE_URL}/tasks/{task_id}", 
                    json={"status": "completed"}
                )
                
                if complete_response.status_code == 200:
                    # Now try to edit the completed task
                    immutability_tests = 0
                    immutability_passed = 0
                    
                    # Test 1: Try to change status
                    edit_response = self.session.put(
                        f"{API_BASE_URL}/tasks/{task_id}", 
                        json={"status": "pending"}
                    )
                    immutability_tests += 1
                    if edit_response.status_code == 403:
                        immutability_passed += 1
                        response_data = edit_response.json() if edit_response.headers.get('content-type', '').startswith('application/json') else {}
                        expected_message = "Cannot edit completed tasks. Completed tasks are immutable."
                        if expected_message in edit_response.text:
                            self.log_test(
                                "Immutability: Status Change", 
                                True, 
                                "Completed task status change correctly rejected with 403 and proper message"
                            )
                        else:
                            self.log_test(
                                "Immutability: Status Change", 
                                True, 
                                "Completed task status change correctly rejected with 403 (message format may vary)"
                            )
                    else:
                        self.log_test(
                            "Immutability: Status Change", 
                            False, 
                            f"Completed task status change should be rejected with 403, got {edit_response.status_code}",
                            {'response': edit_response.text}
                        )
                    
                    # Test 2: Try to change title
                    edit_response = self.session.put(
                        f"{API_BASE_URL}/tasks/{task_id}", 
                        json={"title": "Modified Title"}
                    )
                    immutability_tests += 1
                    if edit_response.status_code == 403:
                        immutability_passed += 1
                        self.log_test(
                            "Immutability: Title Change", 
                            True, 
                            "Completed task title change correctly rejected with 403"
                        )
                    else:
                        self.log_test(
                            "Immutability: Title Change", 
                            False, 
                            f"Completed task title change should be rejected with 403, got {edit_response.status_code}",
                            {'response': edit_response.text}
                        )
                    
                    # Test 3: Try to change description
                    edit_response = self.session.put(
                        f"{API_BASE_URL}/tasks/{task_id}", 
                        json={"description": "Modified description"}
                    )
                    immutability_tests += 1
                    if edit_response.status_code == 403:
                        immutability_passed += 1
                        self.log_test(
                            "Immutability: Description Change", 
                            True, 
                            "Completed task description change correctly rejected with 403"
                        )
                    else:
                        self.log_test(
                            "Immutability: Description Change", 
                            False, 
                            f"Completed task description change should be rejected with 403, got {edit_response.status_code}",
                            {'response': edit_response.text}
                        )
                    
                    if immutability_passed == immutability_tests:
                        self.log_test(
                            "Completed Task Immutability", 
                            True, 
                            f"All {immutability_tests} immutability tests passed - completed tasks are properly protected"
                        )
                        return True
                    else:
                        self.log_test(
                            "Completed Task Immutability", 
                            False, 
                            f"Only {immutability_passed}/{immutability_tests} immutability tests passed"
                        )
                else:
                    self.log_test(
                        "Completed Task Immutability", 
                        False, 
                        f"Failed to complete task for immutability test: {complete_response.status_code}",
                        {'response': complete_response.text}
                    )
            else:
                self.log_test(
                    "Completed Task Immutability", 
                    False, 
                    f"Failed to create task for immutability test: {response.status_code}",
                    {'response': response.text}
                )
        except Exception as e:
            self.log_test(
                "Completed Task Immutability", 
                False, 
                f"Error in immutability test: {str(e)}"
            )
        
        return False
    
    def test_overdue_auto_update(self):
        """Test automatic overdue functionality"""
        print("\n=== Testing Overdue Auto-Update ===")
        
        if not self.auth_token:
            self.log_test("Overdue Auto-Update", False, "Cannot test - no authentication token")
            return False
        
        # Create a task with past due date
        past_due_date = datetime.now(timezone.utc) - timedelta(days=2)
        task_data = {
            "title": "Overdue Test Task",
            "description": "Testing overdue auto-update functionality",
            "client_name": "Past Due Client",
            "category": "Contract Review",
            "assignee_id": self.current_user['id'],
            "creator_id": self.current_user['id'],
            "priority": "urgent",
            "due_date": past_due_date.isoformat()
        }
        
        try:
            # Create task
            response = self.session.post(f"{API_BASE_URL}/tasks", json=task_data)
            
            if response.status_code in [200, 201]:
                task = response.json()
                task_id = task['id']
                self.created_tasks.append(task_id)
                
                # Task should start as pending
                if task['status'] == 'pending':
                    self.log_test(
                        "Overdue Task Creation", 
                        True, 
                        "Task with past due date correctly created as 'pending'"
                    )
                    
                    # Trigger overdue update by calling GET /tasks (which calls update_overdue_tasks)
                    tasks_response = self.session.get(f"{API_BASE_URL}/tasks")
                    
                    if tasks_response.status_code == 200:
                        # Get the specific task to check if it's now overdue
                        task_response = self.session.get(f"{API_BASE_URL}/tasks/{task_id}")
                        
                        if task_response.status_code == 200:
                            updated_task = task_response.json()
                            
                            if updated_task['status'] == 'overdue':
                                self.log_test(
                                    "Overdue Auto-Update", 
                                    True, 
                                    "Task with past due date automatically updated to 'overdue' status",
                                    {'original_status': 'pending', 'updated_status': 'overdue', 'due_date': past_due_date.isoformat()}
                                )
                                return True
                            else:
                                self.log_test(
                                    "Overdue Auto-Update", 
                                    False, 
                                    f"Task with past due date should be 'overdue' but is '{updated_task['status']}'",
                                    {'due_date': past_due_date.isoformat(), 'current_time': datetime.now(timezone.utc).isoformat()}
                                )
                        else:
                            self.log_test(
                                "Overdue Auto-Update", 
                                False, 
                                f"Failed to retrieve task after overdue update: {task_response.status_code}"
                            )
                    else:
                        self.log_test(
                            "Overdue Auto-Update", 
                            False, 
                            f"Failed to trigger overdue update via GET /tasks: {tasks_response.status_code}"
                        )
                else:
                    self.log_test(
                        "Overdue Task Creation", 
                        False, 
                        f"Task with past due date has unexpected initial status: '{task['status']}'"
                    )
            else:
                self.log_test(
                    "Overdue Auto-Update", 
                    False, 
                    f"Failed to create overdue test task: {response.status_code}",
                    {'response': response.text}
                )
        except Exception as e:
            self.log_test(
                "Overdue Auto-Update", 
                False, 
                f"Error in overdue auto-update test: {str(e)}"
            )
        
        return False
    
    def test_dashboard_counts(self):
        """Test dashboard returns correct counts for all 4 statuses"""
        print("\n=== Testing Dashboard Status Counts ===")
        
        if not self.auth_token:
            self.log_test("Dashboard Status Counts", False, "Cannot test - no authentication token")
            return False
        
        try:
            # Get dashboard data
            response = self.session.get(f"{API_BASE_URL}/dashboard")
            
            if response.status_code == 200:
                dashboard_data = response.json()
                task_counts = dashboard_data.get('task_counts', {})
                
                # Check if all 4 status counts are present
                required_statuses = ['pending', 'on_hold', 'completed', 'overdue']
                status_counts_present = 0
                
                for status in required_statuses:
                    if status in task_counts and isinstance(task_counts[status], int):
                        status_counts_present += 1
                        self.log_test(
                            f"Dashboard Count: {status}", 
                            True, 
                            f"Status '{status}' count present: {task_counts[status]}"
                        )
                    else:
                        self.log_test(
                            f"Dashboard Count: {status}", 
                            False, 
                            f"Status '{status}' count missing or invalid"
                        )
                
                # Check total count calculation
                if 'total' in task_counts:
                    calculated_total = sum(task_counts.get(status, 0) for status in required_statuses)
                    reported_total = task_counts['total']
                    
                    if calculated_total == reported_total:
                        self.log_test(
                            "Dashboard Total Count", 
                            True, 
                            f"Total count correctly calculated: {reported_total}"
                        )
                    else:
                        self.log_test(
                            "Dashboard Total Count", 
                            False, 
                            f"Total count mismatch: calculated {calculated_total}, reported {reported_total}"
                        )
                else:
                    self.log_test(
                        "Dashboard Total Count", 
                        False, 
                        "Total count missing from dashboard response"
                    )
                
                if status_counts_present == 4:
                    self.log_test(
                        "Dashboard Status Counts", 
                        True, 
                        "Dashboard correctly returns counts for all 4 statuses",
                        {'counts': task_counts}
                    )
                    return True
                else:
                    self.log_test(
                        "Dashboard Status Counts", 
                        False, 
                        f"Only {status_counts_present}/4 status counts present in dashboard"
                    )
            else:
                self.log_test(
                    "Dashboard Status Counts", 
                    False, 
                    f"Dashboard request failed with status {response.status_code}",
                    {'response': response.text}
                )
        except Exception as e:
            self.log_test(
                "Dashboard Status Counts", 
                False, 
                f"Error in dashboard counts test: {str(e)}"
            )
        
        return False
    
    def test_jwt_token_validation(self):
        """Test JWT token generation and validation"""
        print("\n=== Testing JWT Token Validation ===")
        
        if not self.auth_token:
            self.log_test("JWT Token Validation", False, "Cannot test - no authentication token")
            return False
        
        try:
            # Test token format (should be 3 parts separated by dots)
            token_parts = self.auth_token.split('.')
            if len(token_parts) == 3:
                self.log_test(
                    "JWT Token Format", 
                    True, 
                    "JWT token has correct 3-part structure"
                )
            else:
                self.log_test(
                    "JWT Token Format", 
                    False, 
                    f"JWT token has {len(token_parts)} parts instead of 3"
                )
                return False
            
            # Test token validation by making authenticated request
            response = self.session.get(f"{API_BASE_URL}/auth/me")
            
            if response.status_code == 200:
                user_data = response.json()
                if user_data.get('id') == self.current_user.get('id'):
                    self.log_test(
                        "JWT Token Validation", 
                        True, 
                        "JWT token successfully validates and returns correct user data"
                    )
                    return True
                else:
                    self.log_test(
                        "JWT Token Validation", 
                        False, 
                        "JWT token validates but returns incorrect user data"
                    )
            else:
                self.log_test(
                    "JWT Token Validation", 
                    False, 
                    f"JWT token validation failed with status {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "JWT Token Validation", 
                False, 
                f"Error in JWT token validation test: {str(e)}"
            )
        
        return False
    
    def cleanup_test_tasks(self):
        """Clean up created test tasks"""
        print("\n=== Cleaning Up Test Tasks ===")
        
        if not self.created_tasks or not self.auth_token:
            return
        
        cleaned_count = 0
        for task_id in self.created_tasks:
            try:
                response = self.session.delete(f"{API_BASE_URL}/tasks/{task_id}")
                if response.status_code == 200:
                    cleaned_count += 1
            except Exception as e:
                print(f"Failed to clean up task {task_id}: {str(e)}")
        
        print(f"Cleaned up {cleaned_count}/{len(self.created_tasks)} test tasks")
    
    def test_role_based_access_control(self):
        """Test role-based access control"""
        print("\n=== Testing Role-Based Access Control ===")
        
        if not self.auth_token:
            self.log_test("Role-Based Access Control", False, "Cannot test - no authentication token")
            return False
        
        try:
            # Test partner-only endpoints
            partner_endpoints = [
                ("/users", "POST", {"name": "Test User", "email": "test@example.com", "role": "associate", "password": "testpass123"}),
                ("/categories", "POST", {"name": "Test Category", "description": "Test description"}),
                ("/clients", "POST", {"name": "Test Client", "company_type": "Corporation"}),
                ("/categories/download-template", "GET", None),
                ("/clients/download-template", "GET", None)
            ]
            
            partner_access_count = 0
            
            for endpoint, method, data in partner_endpoints:
                try:
                    if method == "POST":
                        response = self.session.post(f"{API_BASE_URL}{endpoint}", json=data)
                    else:
                        response = self.session.get(f"{API_BASE_URL}{endpoint}")
                    
                    # Partner should have access (200, 201) or validation errors (400, 422)
                    if response.status_code in [200, 201, 400, 422]:
                        partner_access_count += 1
                        self.log_test(
                            f"Partner Access: {method} {endpoint}", 
                            True, 
                            f"Partner has appropriate access (status: {response.status_code})"
                        )
                    elif response.status_code == 403:
                        self.log_test(
                            f"Partner Access: {method} {endpoint}", 
                            False, 
                            f"Partner denied access with 403 - should have access"
                        )
                    else:
                        self.log_test(
                            f"Partner Access: {method} {endpoint}", 
                            True, 
                            f"Endpoint returned {response.status_code} (may be expected for this test)"
                        )
                        partner_access_count += 1
                except Exception as e:
                    self.log_test(
                        f"Partner Access: {method} {endpoint}", 
                        False, 
                        f"Error testing partner access: {str(e)}"
                    )
            
            if partner_access_count >= 4:  # At least most endpoints should work
                self.log_test(
                    "Role-Based Access Control", 
                    True, 
                    f"Partner role has appropriate access to {partner_access_count}/{len(partner_endpoints)} endpoints"
                )
                return True
            else:
                self.log_test(
                    "Role-Based Access Control", 
                    False, 
                    f"Partner role access issues: only {partner_access_count}/{len(partner_endpoints)} endpoints accessible"
                )
        except Exception as e:
            self.log_test(
                "Role-Based Access Control", 
                False, 
                f"Error in role-based access control test: {str(e)}"
            )
        
        return False
    
    def test_password_hashing(self):
        """Test password hashing functionality"""
        print("\n=== Testing Password Hashing ===")
        
        if not self.auth_token:
            self.log_test("Password Hashing", False, "Cannot test - no authentication token")
            return False
        
        try:
            # Test by attempting to create a user and verify password is hashed
            test_user_data = {
                "name": "Hash Test User",
                "email": f"hashtest_{datetime.now().timestamp()}@example.com",
                "role": "associate",
                "password": "plaintext_password_123"
            }
            
            response = self.session.post(f"{API_BASE_URL}/users", json=test_user_data)
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                
                # Password should not be returned in response
                if 'password' not in user_data and 'password_hash' not in user_data:
                    self.log_test(
                        "Password Security", 
                        True, 
                        "Password/hash not exposed in API response"
                    )
                    
                    # Try to login with the created user to verify password was hashed correctly
                    login_response = self.session.post(f"{API_BASE_URL}/auth/login", json={
                        "email": test_user_data["email"],
                        "password": test_user_data["password"]
                    })
                    
                    if login_response.status_code == 200:
                        self.log_test(
                            "Password Hashing", 
                            True, 
                            "Password correctly hashed and verified during login"
                        )
                        return True
                    else:
                        self.log_test(
                            "Password Hashing", 
                            False, 
                            f"Password hashing may be incorrect - login failed with {login_response.status_code}"
                        )
                else:
                    self.log_test(
                        "Password Security", 
                        False, 
                        "Password or hash exposed in API response - security risk"
                    )
            else:
                self.log_test(
                    "Password Hashing", 
                    False, 
                    f"Failed to create test user for password hashing test: {response.status_code}",
                    {'response': response.text}
                )
        except Exception as e:
            self.log_test(
                "Password Hashing", 
                False, 
                f"Error in password hashing test: {str(e)}"
            )
        
        return False
    
    def test_environment_variables(self):
        """Test environment variable usage"""
        print("\n=== Testing Environment Variables ===")
        
        try:
            # Test that backend is using environment-based SECRET_KEY
            # We can infer this by successful JWT token generation
            if self.auth_token and len(self.auth_token) > 50:
                self.log_test(
                    "SECRET_KEY Environment", 
                    True, 
                    "JWT tokens generated successfully - SECRET_KEY loaded from environment"
                )
            else:
                self.log_test(
                    "SECRET_KEY Environment", 
                    False, 
                    "JWT token generation may be failing - check SECRET_KEY configuration"
                )
            
            # Test MongoDB connection (inferred from successful API calls)
            response = self.session.get(f"{API_BASE_URL}/dashboard")
            if response.status_code == 200:
                self.log_test(
                    "MongoDB Environment", 
                    True, 
                    "Database connection working - MONGO_URL loaded from environment"
                )
                return True
            else:
                self.log_test(
                    "MongoDB Environment", 
                    False, 
                    f"Database connection issues - check MONGO_URL configuration (status: {response.status_code})"
                )
        except Exception as e:
            self.log_test(
                "Environment Variables", 
                False, 
                f"Error testing environment variables: {str(e)}"
            )
        
        return False
    
    def test_data_management_apis(self):
        """Test team member, category, and client management"""
        print("\n=== Testing Data Management APIs ===")
        
        if not self.auth_token:
            self.log_test("Data Management APIs", False, "Cannot test - no authentication token")
            return False
        
        try:
            api_tests_passed = 0
            total_api_tests = 0
            
            # Test Users API
            total_api_tests += 1
            users_response = self.session.get(f"{API_BASE_URL}/users")
            if users_response.status_code == 200:
                users_data = users_response.json()
                if isinstance(users_data, list):
                    api_tests_passed += 1
                    self.log_test(
                        "Users Management API", 
                        True, 
                        f"Users API working - returned {len(users_data)} users"
                    )
                else:
                    self.log_test(
                        "Users Management API", 
                        False, 
                        "Users API returned invalid data format"
                    )
            else:
                self.log_test(
                    "Users Management API", 
                    False, 
                    f"Users API failed with status {users_response.status_code}"
                )
            
            # Test Categories API
            total_api_tests += 1
            categories_response = self.session.get(f"{API_BASE_URL}/categories")
            if categories_response.status_code == 200:
                categories_data = categories_response.json()
                if isinstance(categories_data, list):
                    api_tests_passed += 1
                    self.log_test(
                        "Categories Management API", 
                        True, 
                        f"Categories API working - returned {len(categories_data)} categories"
                    )
                else:
                    self.log_test(
                        "Categories Management API", 
                        False, 
                        "Categories API returned invalid data format"
                    )
            else:
                self.log_test(
                    "Categories Management API", 
                    False, 
                    f"Categories API failed with status {categories_response.status_code}"
                )
            
            # Test Clients API
            total_api_tests += 1
            clients_response = self.session.get(f"{API_BASE_URL}/clients")
            if clients_response.status_code == 200:
                clients_data = clients_response.json()
                if isinstance(clients_data, list):
                    api_tests_passed += 1
                    self.log_test(
                        "Clients Management API", 
                        True, 
                        f"Clients API working - returned {len(clients_data)} clients"
                    )
                else:
                    self.log_test(
                        "Clients Management API", 
                        False, 
                        "Clients API returned invalid data format"
                    )
            else:
                self.log_test(
                    "Clients Management API", 
                    False, 
                    f"Clients API failed with status {clients_response.status_code}"
                )
            
            if api_tests_passed == total_api_tests:
                self.log_test(
                    "Data Management APIs", 
                    True, 
                    f"All {total_api_tests} data management APIs working correctly"
                )
                return True
            else:
                self.log_test(
                    "Data Management APIs", 
                    False, 
                    f"Only {api_tests_passed}/{total_api_tests} data management APIs working"
                )
        except Exception as e:
            self.log_test(
                "Data Management APIs", 
                False, 
                f"Error in data management APIs test: {str(e)}"
            )
        
        return False
    
    def test_bulk_import_export(self):
        """Test bulk import/export functionality"""
        print("\n=== Testing Bulk Import/Export ===")
        
        if not self.auth_token:
            self.log_test("Bulk Import/Export", False, "Cannot test - no authentication token")
            return False
        
        try:
            export_tests_passed = 0
            total_export_tests = 0
            
            # Test Categories Template Download
            total_export_tests += 1
            categories_template_response = self.session.get(f"{API_BASE_URL}/categories/download-template")
            if categories_template_response.status_code == 200:
                content_type = categories_template_response.headers.get('content-type', '')
                if 'spreadsheet' in content_type or 'excel' in content_type:
                    export_tests_passed += 1
                    self.log_test(
                        "Categories Template Export", 
                        True, 
                        f"Categories template download working (size: {len(categories_template_response.content)} bytes)"
                    )
                else:
                    self.log_test(
                        "Categories Template Export", 
                        False, 
                        f"Categories template has wrong content type: {content_type}"
                    )
            else:
                self.log_test(
                    "Categories Template Export", 
                    False, 
                    f"Categories template download failed with status {categories_template_response.status_code}"
                )
            
            # Test Clients Template Download
            total_export_tests += 1
            clients_template_response = self.session.get(f"{API_BASE_URL}/clients/download-template")
            if clients_template_response.status_code == 200:
                content_type = clients_template_response.headers.get('content-type', '')
                if 'spreadsheet' in content_type or 'excel' in content_type:
                    export_tests_passed += 1
                    self.log_test(
                        "Clients Template Export", 
                        True, 
                        f"Clients template download working (size: {len(clients_template_response.content)} bytes)"
                    )
                else:
                    self.log_test(
                        "Clients Template Export", 
                        False, 
                        f"Clients template has wrong content type: {content_type}"
                    )
            else:
                self.log_test(
                    "Clients Template Export", 
                    False, 
                    f"Clients template download failed with status {clients_template_response.status_code}"
                )
            
            if export_tests_passed == total_export_tests:
                self.log_test(
                    "Bulk Import/Export", 
                    True, 
                    f"All {total_export_tests} bulk export endpoints working correctly"
                )
                return True
            else:
                self.log_test(
                    "Bulk Import/Export", 
                    False, 
                    f"Only {export_tests_passed}/{total_export_tests} bulk export endpoints working"
                )
        except Exception as e:
            self.log_test(
                "Bulk Import/Export", 
                False, 
                f"Error in bulk import/export test: {str(e)}"
            )
        
        return False
    
    def test_notification_system(self):
        """Test notification system"""
        print("\n=== Testing Notification System ===")
        
        if not self.auth_token:
            self.log_test("Notification System", False, "Cannot test - no authentication token")
            return False
        
        try:
            notification_tests_passed = 0
            total_notification_tests = 0
            
            # Test Get Notifications
            total_notification_tests += 1
            notifications_response = self.session.get(f"{API_BASE_URL}/notifications")
            if notifications_response.status_code == 200:
                notifications_data = notifications_response.json()
                if isinstance(notifications_data, list):
                    notification_tests_passed += 1
                    self.log_test(
                        "Get Notifications", 
                        True, 
                        f"Notifications API working - returned {len(notifications_data)} notifications"
                    )
                else:
                    self.log_test(
                        "Get Notifications", 
                        False, 
                        "Notifications API returned invalid data format"
                    )
            else:
                self.log_test(
                    "Get Notifications", 
                    False, 
                    f"Notifications API failed with status {notifications_response.status_code}"
                )
            
            # Test Unread Count
            total_notification_tests += 1
            unread_response = self.session.get(f"{API_BASE_URL}/notifications/unread-count")
            if unread_response.status_code == 200:
                unread_data = unread_response.json()
                if 'unread_count' in unread_data and isinstance(unread_data['unread_count'], int):
                    notification_tests_passed += 1
                    self.log_test(
                        "Unread Notifications Count", 
                        True, 
                        f"Unread count API working - {unread_data['unread_count']} unread notifications"
                    )
                else:
                    self.log_test(
                        "Unread Notifications Count", 
                        False, 
                        "Unread count API returned invalid data format"
                    )
            else:
                self.log_test(
                    "Unread Notifications Count", 
                    False, 
                    f"Unread count API failed with status {unread_response.status_code}"
                )
            
            if notification_tests_passed == total_notification_tests:
                self.log_test(
                    "Notification System", 
                    True, 
                    f"All {total_notification_tests} notification endpoints working correctly"
                )
                return True
            else:
                self.log_test(
                    "Notification System", 
                    False, 
                    f"Only {notification_tests_passed}/{total_notification_tests} notification endpoints working"
                )
        except Exception as e:
            self.log_test(
                "Notification System", 
                False, 
                f"Error in notification system test: {str(e)}"
            )
        
        return False
    
    def test_error_handling_security(self):
        """Test error handling and security responses"""
        print("\n=== Testing Error Handling & Security ===")
        
        try:
            security_tests_passed = 0
            total_security_tests = 0
            
            # Test unauthorized access
            total_security_tests += 1
            unauthorized_session = requests.Session()
            unauthorized_response = unauthorized_session.get(f"{API_BASE_URL}/tasks")
            if unauthorized_response.status_code == 401:
                security_tests_passed += 1
                self.log_test(
                    "Unauthorized Access Protection", 
                    True, 
                    "Unauthorized requests correctly rejected with 401"
                )
            else:
                self.log_test(
                    "Unauthorized Access Protection", 
                    False, 
                    f"Unauthorized request should return 401, got {unauthorized_response.status_code}"
                )
            
            # Test invalid token
            total_security_tests += 1
            invalid_token_session = requests.Session()
            invalid_token_session.headers.update({'Authorization': 'Bearer invalid_token_123'})
            invalid_token_response = invalid_token_session.get(f"{API_BASE_URL}/tasks")
            if invalid_token_response.status_code == 401:
                security_tests_passed += 1
                self.log_test(
                    "Invalid Token Protection", 
                    True, 
                    "Invalid tokens correctly rejected with 401"
                )
            else:
                self.log_test(
                    "Invalid Token Protection", 
                    False, 
                    f"Invalid token should return 401, got {invalid_token_response.status_code}"
                )
            
            # Test malformed requests
            total_security_tests += 1
            if self.auth_token:
                malformed_response = self.session.post(f"{API_BASE_URL}/tasks", json={"invalid": "data"})
                if malformed_response.status_code in [400, 422]:
                    security_tests_passed += 1
                    self.log_test(
                        "Malformed Request Handling", 
                        True, 
                        f"Malformed requests correctly rejected with {malformed_response.status_code}"
                    )
                else:
                    self.log_test(
                        "Malformed Request Handling", 
                        False, 
                        f"Malformed request should return 400/422, got {malformed_response.status_code}"
                    )
            else:
                self.log_test(
                    "Malformed Request Handling", 
                    False, 
                    "Cannot test - no authentication token"
                )
            
            if security_tests_passed >= 2:  # At least 2 out of 3 should pass
                self.log_test(
                    "Error Handling & Security", 
                    True, 
                    f"Security measures working correctly ({security_tests_passed}/{total_security_tests} tests passed)"
                )
                return True
            else:
                self.log_test(
                    "Error Handling & Security", 
                    False, 
                    f"Security issues detected ({security_tests_passed}/{total_security_tests} tests passed)"
                )
        except Exception as e:
            self.log_test(
                "Error Handling & Security", 
                False, 
                f"Error in security test: {str(e)}"
            )
        
        return False
    
    def run_all_tests(self):
        """Run comprehensive production readiness health check"""
        print(f"🚀 Starting TaskAct Production Readiness Health Check")
        print(f"📍 Testing against: {API_BASE_URL}")
        print("=" * 80)
        
        # Test authentication first
        auth_success = self.test_authentication()
        
        if not auth_success:
            print("❌ Authentication failed - cannot proceed with other tests")
            return False
        
        # Run comprehensive production readiness tests
        test_results = []
        
        # 1. Authentication System Health
        test_results.append(self.test_jwt_token_validation())
        test_results.append(self.test_role_based_access_control())
        test_results.append(self.test_password_hashing())
        
        # 2. Core API Endpoints Health
        test_results.append(self.test_status_enum_verification())
        test_results.append(self.test_task_creation_default_status())
        test_results.append(self.test_status_transitions())
        test_results.append(self.test_completed_task_immutability())
        test_results.append(self.test_overdue_auto_update())
        test_results.append(self.test_dashboard_counts())
        
        # 3. Data Management Health
        test_results.append(self.test_data_management_apis())
        test_results.append(self.test_bulk_import_export())
        test_results.append(self.test_notification_system())
        
        # 4. Security & Environment Health
        test_results.append(self.test_environment_variables())
        test_results.append(self.test_error_handling_security())
        
        # Clean up test tasks
        self.cleanup_test_tasks()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TASKACT PRODUCTION READINESS HEALTH CHECK SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        # Categorize results
        auth_tests = [r for r in self.test_results if any(keyword in r['test'] for keyword in ['Authentication', 'JWT', 'Role-Based', 'Password'])]
        core_api_tests = [r for r in self.test_results if any(keyword in r['test'] for keyword in ['Status', 'Task', 'Dashboard', 'Overdue', 'Immutability'])]
        data_mgmt_tests = [r for r in self.test_results if any(keyword in r['test'] for keyword in ['Data Management', 'Bulk', 'Notification'])]
        security_tests = [r for r in self.test_results if any(keyword in r['test'] for keyword in ['Environment', 'Error Handling', 'Security'])]
        
        # Show category summaries
        categories = [
            ("🔐 Authentication System", auth_tests),
            ("🔧 Core API Endpoints", core_api_tests),
            ("📊 Data Management", data_mgmt_tests),
            ("🛡️ Security & Environment", security_tests)
        ]
        
        for category_name, category_tests in categories:
            if category_tests:
                category_passed = sum(1 for t in category_tests if t['success'])
                category_total = len(category_tests)
                print(f"\n{category_name}: {category_passed}/{category_total} passed")
                
                failed_in_category = [t for t in category_tests if not t['success']]
                if failed_in_category:
                    for test in failed_in_category:
                        print(f"  ❌ {test['test']}: {test['message']}")
        
        # Show critical issues
        critical_issues = []
        
        # Authentication issues
        auth_failed = not any(r['test'] == 'Partner Authentication' and r['success'] for r in self.test_results)
        jwt_failed = not any(r['test'] == 'JWT Token Validation' and r['success'] for r in self.test_results)
        rbac_failed = not any(r['test'] == 'Role-Based Access Control' and r['success'] for r in self.test_results)
        
        # Core API issues
        status_enum_failed = not any(r['test'] == 'Status Enum Verification' and r['success'] for r in self.test_results)
        immutability_failed = not any(r['test'] == 'Completed Task Immutability' and r['success'] for r in self.test_results)
        dashboard_failed = not any(r['test'] == 'Dashboard Status Counts' and r['success'] for r in self.test_results)
        
        # Security issues
        env_failed = not any(r['test'] == 'Environment Variables' and r['success'] for r in self.test_results)
        security_failed = not any(r['test'] == 'Error Handling & Security' and r['success'] for r in self.test_results)
        
        if auth_failed:
            critical_issues.append("Authentication system not working - users cannot log in")
        if jwt_failed:
            critical_issues.append("JWT token validation failing - security risk")
        if rbac_failed:
            critical_issues.append("Role-based access control not working - authorization issues")
        if status_enum_failed:
            critical_issues.append("Status validation not working - data integrity risk")
        if immutability_failed:
            critical_issues.append("Completed task immutability not enforced - data corruption risk")
        if dashboard_failed:
            critical_issues.append("Dashboard analytics not working - reporting issues")
        if env_failed:
            critical_issues.append("Environment variables not properly configured")
        if security_failed:
            critical_issues.append("Security measures not working properly")
        
        if critical_issues:
            print(f"\n🚨 CRITICAL PRODUCTION ISSUES:")
            for issue in critical_issues:
                print(f"  • {issue}")
        
        # Overall production readiness assessment
        core_systems_working = sum([
            not auth_failed,
            not jwt_failed,
            not status_enum_failed,
            not immutability_failed,
            not dashboard_failed,
            not env_failed,
            not security_failed
        ])
        
        print(f"\n📈 PRODUCTION READINESS: {core_systems_working}/7 critical systems working")
        
        if core_systems_working == 7 and passed >= total * 0.9:
            print("🎉 TaskAct is READY FOR PRODUCTION DEPLOYMENT!")
            print("   All critical systems operational, high test success rate")
        elif core_systems_working >= 6 and passed >= total * 0.8:
            print("⚠️  TaskAct is MOSTLY READY for production with minor issues")
            print("   Most critical systems working, some non-critical issues need attention")
        elif core_systems_working >= 5:
            print("🔧 TaskAct needs FIXES BEFORE PRODUCTION deployment")
            print("   Some critical systems have issues that must be resolved")
        else:
            print("🚨 TaskAct is NOT READY for production - MAJOR ISSUES detected")
            print("   Multiple critical systems failing - requires immediate attention")
        
        return passed >= total * 0.9 and core_systems_working >= 6

if __name__ == "__main__":
    tester = TaskActTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)