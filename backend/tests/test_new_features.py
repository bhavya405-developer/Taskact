"""
Test cases for new features:
1. Edit Project - Task Reassignment (PUT /api/projects/{project_id}/tasks/{task_id})
2. Recurring Task Creation (POST /api/tasks with is_recurring=true)

Tests cover:
- Task reassignment within projects
- Recurring task generation for all recurrence types
- Validation of recurrence_config
- End date handling for recurring tasks
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PARTNER_CREDENTIALS = {
    "company_code": "SCO1",
    "email": "bhavika@sundesha.in",
    "password": "password123"
}

ASSOCIATE_CREDENTIALS = {
    "company_code": "SCO1",
    "email": "sonurajpurohit980@gmail.com",
    "password": "password123"
}

# Known project ID from context
EXISTING_PROJECT_ID = "17d58899-a0c5-4a81-ae08-fe76616a0d63"


class TestSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def partner_token(self):
        """Get partner authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDENTIALS)
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def partner_session(self, partner_token):
        """Create authenticated session for partner"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {partner_token}",
            "Content-Type": "application/json"
        })
        return session
    
    @pytest.fixture(scope="class")
    def users_list(self, partner_session):
        """Get list of users for assignee selection"""
        response = partner_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        return response.json()
    
    @pytest.fixture(scope="class")
    def clients_list(self, partner_session):
        """Get list of clients"""
        response = partner_session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        return response.json()
    
    @pytest.fixture(scope="class")
    def categories_list(self, partner_session):
        """Get list of categories"""
        response = partner_session.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        return response.json()


class TestProjectTaskReassignment(TestSetup):
    """Feature 1: Edit Project - Task Reassignment tests"""
    
    def test_01_get_existing_project_with_tasks(self, partner_session):
        """Verify existing project has tasks that can be reassigned"""
        response = partner_session.get(f"{BASE_URL}/api/projects/{EXISTING_PROJECT_ID}")
        assert response.status_code == 200, f"Failed to get project: {response.text}"
        
        project = response.json()
        assert "tasks" in project, "Project should have tasks array"
        assert len(project["tasks"]) > 0, "Project should have at least one task"
        
        print(f"Project '{project['name']}' has {len(project['tasks'])} tasks")
        for task in project["tasks"]:
            print(f"  - Task: {task['title']}, Assignee: {task.get('assignee_name', 'Unassigned')}")
    
    def test_02_reassign_task_to_different_user(self, partner_session, users_list):
        """Test reassigning a task to a different user"""
        # Get project tasks
        response = partner_session.get(f"{BASE_URL}/api/projects/{EXISTING_PROJECT_ID}")
        assert response.status_code == 200
        project = response.json()
        
        if len(project["tasks"]) == 0:
            pytest.skip("No tasks in project to reassign")
        
        task = project["tasks"][0]
        task_id = task["id"]
        original_assignee = task.get("assignee_id")
        
        # Find a different user to assign to
        new_assignee = None
        for user in users_list:
            if user["id"] != original_assignee:
                new_assignee = user
                break
        
        if not new_assignee:
            pytest.skip("No other users available for reassignment")
        
        # Reassign the task
        response = partner_session.put(
            f"{BASE_URL}/api/projects/{EXISTING_PROJECT_ID}/tasks/{task_id}",
            json={"assignee_id": new_assignee["id"]}
        )
        
        assert response.status_code == 200, f"Task reassignment failed: {response.text}"
        
        updated_task = response.json()
        assert updated_task["assignee_id"] == new_assignee["id"], "Assignee ID should be updated"
        assert updated_task["assignee_name"] == new_assignee["name"], "Assignee name should be updated"
        
        print(f"Successfully reassigned task '{task['title']}' to {new_assignee['name']}")
    
    def test_03_reassign_task_invalid_assignee(self, partner_session):
        """Test reassigning task with invalid assignee ID"""
        response = partner_session.get(f"{BASE_URL}/api/projects/{EXISTING_PROJECT_ID}")
        assert response.status_code == 200
        project = response.json()
        
        if len(project["tasks"]) == 0:
            pytest.skip("No tasks in project")
        
        task_id = project["tasks"][0]["id"]
        
        # Try to assign to non-existent user
        response = partner_session.put(
            f"{BASE_URL}/api/projects/{EXISTING_PROJECT_ID}/tasks/{task_id}",
            json={"assignee_id": "non-existent-user-id"}
        )
        
        assert response.status_code == 404, "Should return 404 for invalid assignee"
        print("Correctly rejected invalid assignee ID")
    
    def test_04_reassign_task_invalid_project(self, partner_session, users_list):
        """Test reassigning task in non-existent project"""
        response = partner_session.put(
            f"{BASE_URL}/api/projects/non-existent-project/tasks/some-task-id",
            json={"assignee_id": users_list[0]["id"]}
        )
        
        assert response.status_code == 404, "Should return 404 for invalid project"
        print("Correctly rejected invalid project ID")
    
    def test_05_reassign_task_invalid_task(self, partner_session, users_list):
        """Test reassigning non-existent task in valid project"""
        response = partner_session.put(
            f"{BASE_URL}/api/projects/{EXISTING_PROJECT_ID}/tasks/non-existent-task-id",
            json={"assignee_id": users_list[0]["id"]}
        )
        
        assert response.status_code == 404, "Should return 404 for invalid task"
        print("Correctly rejected invalid task ID")


class TestRecurringTaskCreation(TestSetup):
    """Feature 2: Recurring Task Creation tests"""
    
    created_task_ids = []  # Track created tasks for cleanup
    
    @pytest.fixture(autouse=True)
    def setup_cleanup(self, partner_session):
        """Cleanup created tasks after each test"""
        yield
        # Cleanup is done in the final test
    
    def test_01_create_daily_recurring_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a daily recurring task"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT00:00:00Z")
        
        task_data = {
            "title": "TEST Daily Recurring Task",
            "description": "Test daily recurrence",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "medium",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "daily",
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create daily recurring task: {response.text}"
        
        result = response.json()
        assert result.get("is_recurring") == True, "Task should be marked as recurring"
        assert result.get("recurrence_type") == "daily", "Recurrence type should be daily"
        
        # Check if recurring instances were created
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created recurring instances, got {recurring_count}"
        
        self.created_task_ids.append(result["id"])
        print(f"Created daily recurring task with {recurring_count} instances")
    
    def test_02_create_weekly_recurring_task_with_day(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a weekly recurring task with specific day of week"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%dT00:00:00Z")
        
        task_data = {
            "title": "TEST Weekly Status Report",
            "description": "Weekly status report every Monday",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "high",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "weekly",
            "recurrence_config": {"day_of_week": "monday"},
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create weekly recurring task: {response.text}"
        
        result = response.json()
        assert result.get("is_recurring") == True
        assert result.get("recurrence_type") == "weekly"
        
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created weekly instances, got {recurring_count}"
        
        self.created_task_ids.append(result["id"])
        print(f"Created weekly recurring task (Monday) with {recurring_count} instances")
    
    def test_03_create_fortnightly_recurring_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a fortnightly (every 2 weeks) recurring task"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z")
        
        task_data = {
            "title": "TEST Fortnightly Review",
            "description": "Bi-weekly review meeting",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "medium",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "fortnightly",
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create fortnightly task: {response.text}"
        
        result = response.json()
        assert result.get("recurrence_type") == "fortnightly"
        
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created fortnightly instances"
        
        self.created_task_ids.append(result["id"])
        print(f"Created fortnightly recurring task with {recurring_count} instances")
    
    def test_04_create_monthly_recurring_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a monthly recurring task"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z")
        
        task_data = {
            "title": "TEST Monthly Report",
            "description": "Monthly financial report",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "high",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "monthly",
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create monthly task: {response.text}"
        
        result = response.json()
        assert result.get("recurrence_type") == "monthly"
        
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created monthly instances"
        
        self.created_task_ids.append(result["id"])
        print(f"Created monthly recurring task with {recurring_count} instances")
    
    def test_05_create_custom_day_of_month_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a task on specific day of every month (e.g., 15th)"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%dT00:00:00Z")
        
        task_data = {
            "title": "TEST 15th of Month Task",
            "description": "Task due on 15th of every month",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "medium",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "custom_day_of_month",
            "recurrence_config": {"day_of_month": 15},
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create custom day of month task: {response.text}"
        
        result = response.json()
        assert result.get("recurrence_type") == "custom_day_of_month"
        assert result.get("recurrence_config", {}).get("day_of_month") == 15
        
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created instances for 15th of each month"
        
        self.created_task_ids.append(result["id"])
        print(f"Created custom day of month (15th) task with {recurring_count} instances")
    
    def test_06_create_custom_day_of_week_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a task on specific day every N weeks (e.g., Monday every 2 weeks)"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%dT00:00:00Z")
        
        task_data = {
            "title": "TEST Monday Every 2 Weeks",
            "description": "Task on Monday every 2 weeks",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "medium",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "custom_day_of_week",
            "recurrence_config": {"day_of_week": "monday", "every_n_weeks": 2},
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create custom day of week task: {response.text}"
        
        result = response.json()
        assert result.get("recurrence_type") == "custom_day_of_week"
        
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created instances for Monday every 2 weeks"
        
        self.created_task_ids.append(result["id"])
        print(f"Created custom day of week (Monday every 2 weeks) task with {recurring_count} instances")
    
    def test_07_create_half_yearly_recurring_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a half-yearly recurring task"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=730)).strftime("%Y-%m-%dT00:00:00Z")  # 2 years
        
        task_data = {
            "title": "TEST Half Yearly Audit",
            "description": "Semi-annual audit task",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "high",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "half_yearly",
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create half yearly task: {response.text}"
        
        result = response.json()
        assert result.get("recurrence_type") == "half_yearly"
        
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created half yearly instances"
        
        self.created_task_ids.append(result["id"])
        print(f"Created half yearly recurring task with {recurring_count} instances")
    
    def test_08_create_annually_recurring_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating an annual recurring task"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end_date = (datetime.now() + timedelta(days=1825)).strftime("%Y-%m-%dT00:00:00Z")  # 5 years
        
        task_data = {
            "title": "TEST Annual Review",
            "description": "Yearly performance review",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "high",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "annually",
            "recurrence_end_date": end_date
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create annual task: {response.text}"
        
        result = response.json()
        assert result.get("recurrence_type") == "annually"
        
        recurring_count = result.get("recurring_instances_created", 0)
        assert recurring_count > 0, f"Should have created annual instances"
        
        self.created_task_ids.append(result["id"])
        print(f"Created annual recurring task with {recurring_count} instances")
    
    def test_09_verify_child_tasks_have_parent_id(self, partner_session):
        """Verify that child recurring tasks have parent_recurring_id set"""
        # Get all tasks
        response = partner_session.get(f"{BASE_URL}/api/tasks")
        assert response.status_code == 200
        
        tasks = response.json()
        
        # Find tasks with parent_recurring_id
        child_tasks = [t for t in tasks if t.get("parent_recurring_id")]
        
        if len(child_tasks) == 0:
            pytest.skip("No child recurring tasks found")
        
        # Verify parent exists
        parent_ids = set(t.get("parent_recurring_id") for t in child_tasks)
        for parent_id in parent_ids:
            parent_task = next((t for t in tasks if t["id"] == parent_id), None)
            if parent_task:
                assert parent_task.get("is_recurring") == True, "Parent should be marked as recurring"
                print(f"Verified parent task '{parent_task['title']}' has child instances")
    
    def test_10_create_non_recurring_task(self, partner_session, users_list, clients_list, categories_list):
        """Test creating a regular non-recurring task (baseline)"""
        if not users_list or not clients_list or not categories_list:
            pytest.skip("Missing required data")
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
        
        task_data = {
            "title": "TEST Non-Recurring Task",
            "description": "Regular one-time task",
            "client_name": clients_list[0]["name"],
            "category": categories_list[0]["name"],
            "assignee_id": users_list[0]["id"],
            "priority": "low",
            "due_date": due_date,
            "is_recurring": False
        }
        
        response = partner_session.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 200, f"Failed to create non-recurring task: {response.text}"
        
        result = response.json()
        assert result.get("is_recurring", False) == False or result.get("is_recurring") is None
        assert "recurring_instances_created" not in result or result.get("recurring_instances_created", 0) == 0
        
        self.created_task_ids.append(result["id"])
        print("Created non-recurring task successfully")
    
    def test_99_cleanup_test_tasks(self, partner_session):
        """Cleanup all TEST_ prefixed tasks"""
        response = partner_session.get(f"{BASE_URL}/api/tasks")
        assert response.status_code == 200
        
        tasks = response.json()
        test_tasks = [t for t in tasks if t.get("title", "").startswith("TEST")]
        
        deleted_count = 0
        for task in test_tasks:
            del_response = partner_session.delete(f"{BASE_URL}/api/tasks/{task['id']}")
            if del_response.status_code == 200:
                deleted_count += 1
        
        print(f"Cleaned up {deleted_count} test tasks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
