"""
Test Task Status Redetermination on Project Due Date Change:
1. When project due_date changes, non-completed/non-on_hold tasks get status redetermined:
   - If new due_date < now_utc -> 'overdue'
   - If new due_date >= now_utc -> 'pending'
2. Completed and on_hold tasks keep their status (only due_date changes)
3. Frontend Projects page default status filter should be 'pending'
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMPANY_CODE = "SCO1"
EMAIL = "bhavika@sundesha.in"
PASSWORD = "password123"

# Known user IDs from context
USER_SONU = "1e99009f-23a2-42ff-aad8-1caa7d54e951"
USER_NITISH = "e7ae9f26-0684-44a6-ab56-14cfc5f868d8"


class TestTaskStatusRedetermination:
    """Test task status redetermination when project due_date changes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.auth_token = None
        self.created_project_ids = []
        
        # Authenticate
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        
        if login_response.status_code == 200:
            self.auth_token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
        
        yield
        
        # Cleanup: Delete test projects
        for project_id in self.created_project_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/projects/{project_id}")
            except:
                pass
    
    # ==================== FEATURE 1: TASK STATUS REDETERMINATION ====================
    
    def test_01_tasks_become_overdue_when_project_due_date_set_to_past(self):
        """Test that pending tasks become 'overdue' when project due_date is changed to past"""
        # Create project with future due date (tasks should be 'pending')
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusRedetermination_ToPast_{uuid.uuid4().hex[:8]}",
            "description": "Test task status redetermination to overdue",
            "due_date": future_date,
            "tasks": [
                {"title": "Task 1 - Should become overdue", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Should become overdue", "assignee_id": USER_NITISH, "priority": "high"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201], f"Failed to create project: {create_response.text}"
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Verify initial task statuses are 'pending'
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()
        
        for task in tasks:
            assert task["status"] == "pending", f"Initial task status should be 'pending', got '{task['status']}'"
        
        print(f"✓ Created project with {len(tasks)} tasks, all with status 'pending'")
        
        # Change project due_date to PAST
        update_response = self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={
            "due_date": past_date
        })
        assert update_response.status_code == 200, f"Failed to update project: {update_response.text}"
        
        # Verify all tasks now have status 'overdue'
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        assert tasks_response.status_code == 200
        updated_tasks = tasks_response.json()
        
        for task in updated_tasks:
            assert task["status"] == "overdue", \
                f"Task '{task['title']}' should be 'overdue' after due_date set to past, got '{task['status']}'"
            assert task["due_date"].startswith(past_date), \
                f"Task due_date should be updated to {past_date}"
        
        print(f"✓ All {len(updated_tasks)} tasks changed to 'overdue' after due_date set to past")
    
    def test_02_tasks_become_pending_when_project_due_date_set_to_future(self):
        """Test that overdue tasks become 'pending' when project due_date is changed to future"""
        # Create project with past due date (tasks should become 'overdue' after creation)
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusRedetermination_ToFuture_{uuid.uuid4().hex[:8]}",
            "description": "Test task status redetermination to pending",
            "due_date": past_date,  # Start with past date
            "tasks": [
                {"title": "Task 1 - Should become pending", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Should become pending", "assignee_id": USER_NITISH, "priority": "high"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201], f"Failed to create project: {create_response.text}"
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        print(f"✓ Created project with past due_date {past_date}")
        
        # Change project due_date to FUTURE
        update_response = self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={
            "due_date": future_date
        })
        assert update_response.status_code == 200, f"Failed to update project: {update_response.text}"
        
        # Verify all tasks now have status 'pending'
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        assert tasks_response.status_code == 200
        updated_tasks = tasks_response.json()
        
        for task in updated_tasks:
            assert task["status"] == "pending", \
                f"Task '{task['title']}' should be 'pending' after due_date set to future, got '{task['status']}'"
            assert task["due_date"].startswith(future_date), \
                f"Task due_date should be updated to {future_date}"
        
        print(f"✓ All {len(updated_tasks)} tasks changed to 'pending' after due_date set to future")
    
    def test_03_completed_tasks_keep_status_when_due_date_changes(self):
        """Test that completed tasks keep their status when project due_date changes"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_CompletedTasksKeepStatus_{uuid.uuid4().hex[:8]}",
            "description": "Test completed tasks keep status",
            "due_date": future_date,
            "tasks": [
                {"title": "Task 1 - Will be completed", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Will stay pending", "assignee_id": USER_NITISH, "priority": "high"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Get tasks
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        
        # Complete the first task
        task_to_complete = tasks[0]
        complete_response = self.session.put(f"{BASE_URL}/api/tasks/{task_to_complete['id']}", json={
            "status": "completed",
            "actual_hours": 2
        })
        assert complete_response.status_code == 200, f"Failed to complete task: {complete_response.text}"
        print(f"✓ Completed task: {task_to_complete['title']}")
        
        # Change project due_date to PAST
        update_response = self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={
            "due_date": past_date
        })
        assert update_response.status_code == 200
        
        # Verify task statuses
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        updated_tasks = tasks_response.json()
        
        for task in updated_tasks:
            if task["id"] == task_to_complete["id"]:
                # Completed task should KEEP its status
                assert task["status"] == "completed", \
                    f"Completed task should keep status 'completed', got '{task['status']}'"
                # But due_date should still be updated
                assert task["due_date"].startswith(past_date), \
                    f"Completed task due_date should still be updated"
                print(f"✓ Completed task kept status 'completed', due_date updated to {past_date}")
            else:
                # Non-completed task should become overdue
                assert task["status"] == "overdue", \
                    f"Non-completed task should become 'overdue', got '{task['status']}'"
                print(f"✓ Non-completed task changed to 'overdue'")
    
    def test_04_on_hold_tasks_keep_status_when_due_date_changes(self):
        """Test that on_hold tasks keep their status when project due_date changes"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_OnHoldTasksKeepStatus_{uuid.uuid4().hex[:8]}",
            "description": "Test on_hold tasks keep status",
            "due_date": future_date,
            "tasks": [
                {"title": "Task 1 - Will be on_hold", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Will stay pending", "assignee_id": USER_NITISH, "priority": "high"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Get tasks
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        
        # Set first task to on_hold
        task_to_hold = tasks[0]
        hold_response = self.session.put(f"{BASE_URL}/api/tasks/{task_to_hold['id']}", json={
            "status": "on_hold"
        })
        assert hold_response.status_code == 200, f"Failed to set task on_hold: {hold_response.text}"
        print(f"✓ Set task to on_hold: {task_to_hold['title']}")
        
        # Change project due_date to PAST
        update_response = self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={
            "due_date": past_date
        })
        assert update_response.status_code == 200
        
        # Verify task statuses
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        updated_tasks = tasks_response.json()
        
        for task in updated_tasks:
            if task["id"] == task_to_hold["id"]:
                # On_hold task should KEEP its status
                assert task["status"] == "on_hold", \
                    f"On_hold task should keep status 'on_hold', got '{task['status']}'"
                # But due_date should still be updated
                assert task["due_date"].startswith(past_date), \
                    f"On_hold task due_date should still be updated"
                print(f"✓ On_hold task kept status 'on_hold', due_date updated to {past_date}")
            else:
                # Non-on_hold task should become overdue
                assert task["status"] == "overdue", \
                    f"Non-on_hold task should become 'overdue', got '{task['status']}'"
                print(f"✓ Non-on_hold task changed to 'overdue'")
    
    def test_05_status_redetermination_round_trip(self):
        """Test status redetermination works correctly in both directions (future->past->future)"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusRoundTrip_{uuid.uuid4().hex[:8]}",
            "description": "Test status redetermination round trip",
            "due_date": future_date,
            "tasks": [
                {"title": "Task 1", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2", "assignee_id": USER_NITISH, "priority": "high"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Step 1: Verify initial status is 'pending'
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        for task in tasks:
            assert task["status"] == "pending", f"Initial status should be 'pending'"
        print(f"✓ Step 1: Initial status is 'pending' (due_date: {future_date})")
        
        # Step 2: Change to past -> should become 'overdue'
        self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={"due_date": past_date})
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        for task in tasks:
            assert task["status"] == "overdue", f"Status should be 'overdue' after past due_date"
        print(f"✓ Step 2: Status changed to 'overdue' (due_date: {past_date})")
        
        # Step 3: Change back to future -> should become 'pending' again
        self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={"due_date": future_date})
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        for task in tasks:
            assert task["status"] == "pending", f"Status should be 'pending' after future due_date"
        print(f"✓ Step 3: Status changed back to 'pending' (due_date: {future_date})")
        
        print(f"✓ Round trip test passed: pending -> overdue -> pending")
    
    def test_06_mixed_task_statuses_redetermination(self):
        """Test redetermination with mixed task statuses (pending, completed, on_hold)"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_MixedStatuses_{uuid.uuid4().hex[:8]}",
            "description": "Test mixed task statuses",
            "due_date": future_date,
            "tasks": [
                {"title": "Task 1 - Will be completed", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Will be on_hold", "assignee_id": USER_NITISH, "priority": "high"},
                {"title": "Task 3 - Will stay pending", "assignee_id": USER_SONU, "priority": "low"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Get tasks
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        
        # Set up mixed statuses
        completed_task_id = tasks[0]["id"]
        on_hold_task_id = tasks[1]["id"]
        pending_task_id = tasks[2]["id"]
        
        # Complete first task
        self.session.put(f"{BASE_URL}/api/tasks/{completed_task_id}", json={
            "status": "completed",
            "actual_hours": 2
        })
        
        # Set second task to on_hold
        self.session.put(f"{BASE_URL}/api/tasks/{on_hold_task_id}", json={
            "status": "on_hold"
        })
        
        print(f"✓ Set up mixed statuses: completed, on_hold, pending")
        
        # Change project due_date to PAST
        self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={"due_date": past_date})
        
        # Verify statuses
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        updated_tasks = tasks_response.json()
        
        for task in updated_tasks:
            if task["id"] == completed_task_id:
                assert task["status"] == "completed", f"Completed task should keep status"
                print(f"✓ Completed task kept status 'completed'")
            elif task["id"] == on_hold_task_id:
                assert task["status"] == "on_hold", f"On_hold task should keep status"
                print(f"✓ On_hold task kept status 'on_hold'")
            elif task["id"] == pending_task_id:
                assert task["status"] == "overdue", f"Pending task should become 'overdue'"
                print(f"✓ Pending task changed to 'overdue'")
            
            # All tasks should have updated due_date
            assert task["due_date"].startswith(past_date), f"All tasks should have updated due_date"
        
        print(f"✓ Mixed statuses test passed")


class TestDueDateCascadeRegression:
    """Regression tests for due date cascade (ensure it still works)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.auth_token = None
        self.created_project_ids = []
        
        # Authenticate
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        
        if login_response.status_code == 200:
            self.auth_token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
        
        yield
        
        # Cleanup
        for project_id in self.created_project_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/projects/{project_id}")
            except:
                pass
    
    def test_07_due_date_cascade_still_works(self):
        """Regression: Verify due date still cascades to all tasks"""
        original_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        new_date = (datetime.now(timezone.utc) + timedelta(days=60)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_DueDateCascadeRegression_{uuid.uuid4().hex[:8]}",
            "description": "Regression test for due date cascade",
            "due_date": original_date,
            "tasks": [
                {"title": "Task 1", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2", "assignee_id": USER_NITISH, "priority": "high"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Update due_date
        self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={"due_date": new_date})
        
        # Verify all tasks have new due_date
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        
        for task in tasks:
            assert task["due_date"].startswith(new_date), \
                f"Task due_date should be updated to {new_date}"
        
        print(f"✓ Due date cascade regression test passed")
    
    def test_08_project_auto_computed_status_still_works(self):
        """Regression: Verify project auto-computed status still works"""
        due_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_AutoStatusRegression_{uuid.uuid4().hex[:8]}",
            "description": "Regression test for auto-computed status",
            "due_date": due_date,
            "tasks": [
                {"title": "Task 1", "assignee_id": USER_SONU, "priority": "medium"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Verify initial status is 'pending'
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        assert test_project["status"] == "pending", "Initial status should be 'pending'"
        print(f"✓ Initial project status is 'pending'")
        
        # Complete the task
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        self.session.put(f"{BASE_URL}/api/tasks/{tasks[0]['id']}", json={
            "status": "completed",
            "actual_hours": 2
        })
        
        # Verify status becomes 'completed'
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        assert test_project["status"] == "completed", "Status should be 'completed' after all tasks completed"
        print(f"✓ Project status changed to 'completed' after all tasks completed")
        
        print(f"✓ Auto-computed status regression test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
