#!/usr/bin/env python3
"""
Backend API Testing Script for TaskAct 4-Status Task System
Comprehensive testing of the updated task status system with 4 statuses and immutability
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
                if response2.status_code == 201:
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
                
                if transition_success >= 2:
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
    
    def run_all_tests(self):
        """Run all comprehensive 4-status system tests"""
        print(f"🚀 Starting TaskAct 4-Status System Tests")
        print(f"📍 Testing against: {API_BASE_URL}")
        print("=" * 80)
        
        # Test authentication first
        auth_success = self.test_authentication()
        
        if not auth_success:
            print("❌ Authentication failed - cannot proceed with other tests")
            return False
        
        # Run comprehensive 4-status system tests
        test_results = []
        
        test_results.append(self.test_status_enum_verification())
        test_results.append(self.test_task_creation_default_status())
        test_results.append(self.test_status_transitions())
        test_results.append(self.test_completed_task_immutability())
        test_results.append(self.test_overdue_auto_update())
        test_results.append(self.test_dashboard_counts())
        
        # Clean up test tasks
        self.cleanup_test_tasks()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TASKACT 4-STATUS SYSTEM TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  • {test['test']}: {test['message']}")
                if test.get('details'):
                    print(f"    Details: {test['details']}")
        
        # Show successful tests summary
        successful_tests = [result for result in self.test_results if result['success']]
        if successful_tests:
            print(f"\n✅ SUCCESSFUL TESTS ({len(successful_tests)}):")
            for test in successful_tests:
                print(f"  • {test['test']}")
        
        # Show critical issues
        critical_issues = []
        
        # Check for critical 4-status system issues
        status_enum_failed = not any(r['test'] == 'Status Enum Verification' and r['success'] for r in self.test_results)
        task_creation_failed = not any(r['test'] == 'Task Creation Default Status' and r['success'] for r in self.test_results)
        transitions_failed = not any(r['test'] == 'Status Transitions' and r['success'] for r in self.test_results)
        immutability_failed = not any(r['test'] == 'Completed Task Immutability' and r['success'] for r in self.test_results)
        overdue_failed = not any(r['test'] == 'Overdue Auto-Update' and r['success'] for r in self.test_results)
        dashboard_failed = not any(r['test'] == 'Dashboard Status Counts' and r['success'] for r in self.test_results)
        
        if status_enum_failed:
            critical_issues.append("Status enum validation not working - invalid statuses may be accepted")
        if task_creation_failed:
            critical_issues.append("New tasks not defaulting to 'pending' status")
        if transitions_failed:
            critical_issues.append("Status transitions not working properly")
        if immutability_failed:
            critical_issues.append("Completed task immutability not enforced")
        if overdue_failed:
            critical_issues.append("Overdue auto-update system not working")
        if dashboard_failed:
            critical_issues.append("Dashboard not showing correct status counts")
        
        if critical_issues:
            print(f"\n🚨 CRITICAL 4-STATUS SYSTEM ISSUES:")
            for issue in critical_issues:
                print(f"  • {issue}")
        
        # Overall assessment
        core_features_working = sum([
            not status_enum_failed,
            not task_creation_failed, 
            not transitions_failed,
            not immutability_failed,
            not overdue_failed,
            not dashboard_failed
        ])
        
        print(f"\n📈 4-STATUS SYSTEM HEALTH: {core_features_working}/6 core features working")
        
        if core_features_working == 6:
            print("🎉 All 4-status system features are working correctly!")
        elif core_features_working >= 4:
            print("⚠️  Most 4-status system features working, some issues need attention")
        else:
            print("🚨 Major issues with 4-status system - requires immediate attention")
        
        return passed == total

if __name__ == "__main__":
    tester = TaskActTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)