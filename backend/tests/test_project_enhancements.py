"""
Test Project Management Enhancements:
1. Due date cascade - When project due_date is changed, all tasks get the new due_date
2. Auto-computed project status - 'pending' when not all tasks completed, 'completed' when all completed
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMPANY_CODE = "SCO1"
EMAIL = "bhavika@sundesha.in"
PASSWORD = "password123"

# Known user IDs from context
USER_SONU = "1e99009f-23a2-42ff-aad8-1caa7d54e951"
USER_NITISH = "e7ae9f26-0684-44a6-ab56-14cfc5f868d8"


class TestProjectEnhancements:
    """Test project management enhancements"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.auth_token = None
        self.created_project_ids = []
        self.created_task_ids = []
        
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
    
    # ==================== FEATURE 1: DUE DATE CASCADE ====================
    
    def test_01_due_date_cascade_on_project_update(self):
        """Test that updating project due_date cascades to all tasks"""
        # Create a project with tasks
        original_due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        new_due_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_DueDateCascade_{uuid.uuid4().hex[:8]}",
            "description": "Test project for due date cascade",
            "due_date": original_due_date,
            "tasks": [
                {"title": "Task 1 - Due Date Test", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Due Date Test", "assignee_id": USER_NITISH, "priority": "high"},
                {"title": "Task 3 - Due Date Test", "assignee_id": USER_SONU, "priority": "low"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201], f"Failed to create project: {create_response.text}"
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Verify initial task due dates
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()
        
        for task in tasks:
            assert task["due_date"].startswith(original_due_date), f"Task {task['title']} has wrong initial due_date"
        
        print(f"✓ Created project with {len(tasks)} tasks, all with due_date {original_due_date}")
        
        # Update project due_date
        update_response = self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={
            "due_date": new_due_date
        })
        assert update_response.status_code == 200, f"Failed to update project: {update_response.text}"
        
        # Verify all tasks now have the new due_date
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        assert tasks_response.status_code == 200
        updated_tasks = tasks_response.json()
        
        for task in updated_tasks:
            assert task["due_date"].startswith(new_due_date), \
                f"Task '{task['title']}' due_date not updated. Expected {new_due_date}, got {task['due_date']}"
        
        print(f"✓ All {len(updated_tasks)} tasks updated to new due_date {new_due_date}")
    
    def test_02_due_date_cascade_with_mixed_task_statuses(self):
        """Test due date cascade works even when some tasks are completed"""
        original_due_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        new_due_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_MixedStatus_{uuid.uuid4().hex[:8]}",
            "description": "Test with mixed task statuses",
            "due_date": original_due_date,
            "tasks": [
                {"title": "Task A - Will Complete", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task B - Stay Pending", "assignee_id": USER_NITISH, "priority": "high"}
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
        
        # Complete one task
        task_to_complete = tasks[0]
        complete_response = self.session.put(f"{BASE_URL}/api/tasks/{task_to_complete['id']}", json={
            "status": "completed",
            "actual_hours": 2
        })
        assert complete_response.status_code == 200, f"Failed to complete task: {complete_response.text}"
        
        print(f"✓ Completed task: {task_to_complete['title']}")
        
        # Update project due_date
        update_response = self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={
            "due_date": new_due_date
        })
        assert update_response.status_code == 200
        
        # Verify ALL tasks (including completed) have new due_date
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        updated_tasks = tasks_response.json()
        
        for task in updated_tasks:
            assert task["due_date"].startswith(new_due_date), \
                f"Task '{task['title']}' (status: {task['status']}) due_date not updated"
        
        print(f"✓ Due date cascade works for all tasks regardless of status")
    
    # ==================== FEATURE 2: AUTO-COMPUTED PROJECT STATUS ====================
    
    def test_03_project_status_pending_when_tasks_not_completed(self):
        """Test project status is 'pending' when not all tasks are completed"""
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusPending_{uuid.uuid4().hex[:8]}",
            "description": "Test pending status",
            "due_date": due_date,
            "tasks": [
                {"title": "Task 1 - Pending", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Pending", "assignee_id": USER_NITISH, "priority": "high"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Get project via list endpoint
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_response.status_code == 200
        
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        
        assert test_project is not None, "Project not found in list"
        assert test_project["status"] == "pending", \
            f"Expected status 'pending', got '{test_project['status']}'"
        
        print(f"✓ Project status is 'pending' when no tasks completed")
        
        # Also verify via single project endpoint
        single_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}")
        assert single_response.status_code == 200
        single_project = single_response.json()
        
        assert single_project["status"] == "pending", \
            f"Single endpoint: Expected 'pending', got '{single_project['status']}'"
        
        print(f"✓ Single project endpoint also returns 'pending' status")
    
    def test_04_project_status_completed_when_all_tasks_completed(self):
        """Test project status becomes 'completed' when all tasks are completed"""
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusCompleted_{uuid.uuid4().hex[:8]}",
            "description": "Test completed status",
            "due_date": due_date,
            "tasks": [
                {"title": "Task 1 - Will Complete", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Will Complete", "assignee_id": USER_NITISH, "priority": "high"}
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
        
        # Complete all tasks
        for task in tasks:
            complete_response = self.session.put(f"{BASE_URL}/api/tasks/{task['id']}", json={
                "status": "completed",
                "actual_hours": 2
            })
            assert complete_response.status_code == 200, f"Failed to complete task: {complete_response.text}"
            print(f"  ✓ Completed task: {task['title']}")
        
        # Verify project status is now 'completed'
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_response.status_code == 200
        
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        
        assert test_project is not None, "Project not found in list"
        assert test_project["status"] == "completed", \
            f"Expected status 'completed', got '{test_project['status']}'"
        
        print(f"✓ Project status is 'completed' when all tasks completed")
    
    def test_05_project_status_pending_when_some_tasks_completed(self):
        """Test project status stays 'pending' when only some tasks are completed"""
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusPartial_{uuid.uuid4().hex[:8]}",
            "description": "Test partial completion",
            "due_date": due_date,
            "tasks": [
                {"title": "Task 1 - Will Complete", "assignee_id": USER_SONU, "priority": "medium"},
                {"title": "Task 2 - Stay Pending", "assignee_id": USER_NITISH, "priority": "high"},
                {"title": "Task 3 - Stay Pending", "assignee_id": USER_SONU, "priority": "low"}
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
        
        # Complete only the first task
        complete_response = self.session.put(f"{BASE_URL}/api/tasks/{tasks[0]['id']}", json={
            "status": "completed",
            "actual_hours": 2
        })
        assert complete_response.status_code == 200
        print(f"  ✓ Completed 1 of 3 tasks")
        
        # Verify project status is still 'pending'
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        
        assert test_project["status"] == "pending", \
            f"Expected status 'pending' with partial completion, got '{test_project['status']}'"
        
        print(f"✓ Project status remains 'pending' with partial task completion (1/3)")
    
    def test_06_project_status_on_hold_stays_on_hold(self):
        """Test that on_hold projects stay on_hold regardless of task completion"""
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusOnHold_{uuid.uuid4().hex[:8]}",
            "description": "Test on_hold status",
            "due_date": due_date,
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
        
        # Set project to on_hold
        update_response = self.session.put(f"{BASE_URL}/api/projects/{project_id}", json={
            "status": "on_hold"
        })
        assert update_response.status_code == 200
        print(f"  ✓ Set project status to on_hold")
        
        # Complete all tasks
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        
        for task in tasks:
            self.session.put(f"{BASE_URL}/api/tasks/{task['id']}", json={
                "status": "completed",
                "actual_hours": 1
            })
        print(f"  ✓ Completed all tasks")
        
        # Verify project status is still 'on_hold'
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        
        assert test_project["status"] == "on_hold", \
            f"Expected status 'on_hold' to persist, got '{test_project['status']}'"
        
        print(f"✓ Project status stays 'on_hold' even when all tasks completed")
    
    def test_07_project_with_zero_tasks_shows_pending(self):
        """Test that project with 0 tasks shows as 'pending'"""
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Create project without tasks - need to add at least one task then delete
        project_payload = {
            "name": f"TEST_ZeroTasks_{uuid.uuid4().hex[:8]}",
            "description": "Test zero tasks status",
            "due_date": due_date,
            "tasks": [
                {"title": "Temp Task", "assignee_id": USER_SONU, "priority": "medium"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Get and delete the task
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        
        if len(tasks) > 0:
            # Delete task via tasks endpoint
            delete_response = self.session.delete(f"{BASE_URL}/api/tasks/{tasks[0]['id']}")
            # If delete endpoint doesn't exist, skip this test
            if delete_response.status_code == 404:
                pytest.skip("Task delete endpoint not available")
        
        # Verify project with 0 tasks shows as 'pending'
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        
        if test_project["total_tasks"] == 0:
            assert test_project["status"] == "pending", \
                f"Expected status 'pending' for 0 tasks, got '{test_project['status']}'"
            print(f"✓ Project with 0 tasks shows as 'pending'")
        else:
            print(f"  Note: Could not delete task, skipping zero-task test")
    
    def test_08_status_transition_pending_to_completed_to_pending(self):
        """Test status transitions correctly when tasks are completed then uncompleted"""
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        project_payload = {
            "name": f"TEST_StatusTransition_{uuid.uuid4().hex[:8]}",
            "description": "Test status transitions",
            "due_date": due_date,
            "tasks": [
                {"title": "Single Task", "assignee_id": USER_SONU, "priority": "medium"}
            ]
        }
        
        # Create project
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=project_payload)
        assert create_response.status_code in [200, 201]
        
        project = create_response.json()
        project_id = project["id"]
        self.created_project_ids.append(project_id)
        
        # Initial status should be pending
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        assert test_project["status"] == "pending", "Initial status should be pending"
        print(f"  ✓ Initial status: pending")
        
        # Complete the task
        tasks_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks")
        tasks = tasks_response.json()
        task_id = tasks[0]["id"]
        
        self.session.put(f"{BASE_URL}/api/tasks/{task_id}", json={
            "status": "completed",
            "actual_hours": 2
        })
        
        # Status should now be completed
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        assert test_project["status"] == "completed", "Status should be completed after completing task"
        print(f"  ✓ After completing task: completed")
        
        # Uncomplete the task (set back to pending)
        self.session.put(f"{BASE_URL}/api/tasks/{task_id}", json={
            "status": "pending"
        })
        
        # Status should go back to pending
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        test_project = next((p for p in projects if p["id"] == project_id), None)
        assert test_project["status"] == "pending", "Status should return to pending after uncompleting task"
        print(f"  ✓ After uncompleting task: pending")
        
        print(f"✓ Status transitions correctly: pending → completed → pending")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
