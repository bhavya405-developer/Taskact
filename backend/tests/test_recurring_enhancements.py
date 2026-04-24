"""
Test cases for recurring task enhancements:
1. Daily recurring tasks with exclude_days option
2. Every Working Day (Mon-Sat) recurrence type
3. Regression tests for existing recurrence types
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMPANY_CODE = "SCO1"
EMAIL = "bhavika@sundesha.in"
PASSWORD = "password123"

# Known test data
ASSIGNEE_ID = "1e99009f-23a2-42ff-aad8-1caa7d54e951"  # Sonu kanwar
CLIENT_NAME = "Abhay textiles"
CATEGORY = "Accounting"


class TestRecurringEnhancements:
    """Test new recurring task features"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_task_ids = []
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code} - {login_response.text}")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        
        # Cleanup: Delete all test tasks created
        for task_id in self.created_task_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/tasks/{task_id}")
            except Exception:
                pass
    
    def _create_recurring_task(self, recurrence_type, recurrence_config=None, title_suffix=""):
        """Helper to create a recurring task and track for cleanup"""
        due_date = (datetime.now() + timedelta(days=1)).isoformat()
        end_date = (datetime.now() + timedelta(days=30)).isoformat()
        
        task_data = {
            "title": f"TEST_Recurring_{recurrence_type}_{title_suffix}_{datetime.now().strftime('%H%M%S')}",
            "description": f"Test task for {recurrence_type} recurrence",
            "client_name": CLIENT_NAME,
            "category": CATEGORY,
            "assignee_id": ASSIGNEE_ID,
            "priority": "medium",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": recurrence_type,
            "recurrence_config": recurrence_config or {},
            "recurrence_end_date": end_date
        }
        
        response = self.session.post(f"{BASE_URL}/api/tasks", json=task_data)
        
        if response.status_code == 200 or response.status_code == 201:
            task = response.json()
            self.created_task_ids.append(task["id"])
            # Also track child tasks for cleanup
            if "recurring_instances_created" in task:
                # Get all tasks with this parent_recurring_id
                tasks_response = self.session.get(f"{BASE_URL}/api/tasks")
                if tasks_response.status_code == 200:
                    all_tasks = tasks_response.json()
                    for t in all_tasks:
                        if t.get("parent_recurring_id") == task["id"]:
                            self.created_task_ids.append(t["id"])
        
        return response
    
    # ==================== Feature 1: Daily with Exclude Days ====================
    
    def test_01_daily_recurring_with_exclude_sunday(self):
        """Test daily recurring task that excludes Sunday"""
        response = self._create_recurring_task(
            recurrence_type="daily",
            recurrence_config={"exclude_days": ["sunday"]},
            title_suffix="exclude_sunday"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("is_recurring") == True
        assert task.get("recurrence_type") == "daily"
        assert "recurring_instances_created" in task
        
        # Verify instances were created
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Created {instances_count} daily recurring instances (excluding Sunday)")
    
    def test_02_daily_recurring_exclude_saturday_sunday(self):
        """Test daily recurring task that excludes Saturday and Sunday (weekdays only)"""
        response = self._create_recurring_task(
            recurrence_type="daily",
            recurrence_config={"exclude_days": ["saturday", "sunday"]},
            title_suffix="weekdays_only"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("is_recurring") == True
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Created {instances_count} weekday-only recurring instances")
    
    def test_03_daily_recurring_no_exclusions(self):
        """Test daily recurring task with no exclusions (all days)"""
        response = self._create_recurring_task(
            recurrence_type="daily",
            recurrence_config={},
            title_suffix="all_days"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Created {instances_count} daily recurring instances (all days)")
    
    # ==================== Feature 2: Every Working Day (Mon-Sat) ====================
    
    def test_04_every_working_day_recurrence(self):
        """Test 'every_working_day' recurrence type (Mon-Sat, no Sunday)"""
        response = self._create_recurring_task(
            recurrence_type="every_working_day",
            recurrence_config={},
            title_suffix="mon_sat"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("is_recurring") == True
        assert task.get("recurrence_type") == "every_working_day"
        
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Created {instances_count} working day (Mon-Sat) recurring instances")
    
    def test_05_verify_working_day_excludes_sunday(self):
        """Verify that every_working_day tasks don't include Sunday"""
        response = self._create_recurring_task(
            recurrence_type="every_working_day",
            recurrence_config={},
            title_suffix="verify_no_sunday"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        parent_id = task["id"]
        
        # Get all child tasks
        tasks_response = self.session.get(f"{BASE_URL}/api/tasks")
        assert tasks_response.status_code == 200
        
        all_tasks = tasks_response.json()
        child_tasks = [t for t in all_tasks if t.get("parent_recurring_id") == parent_id]
        
        # Check that no child task falls on Sunday (weekday 6)
        sunday_tasks = []
        for child in child_tasks:
            if child.get("due_date"):
                due_date = datetime.fromisoformat(child["due_date"].replace('Z', '+00:00'))
                if due_date.weekday() == 6:  # Sunday
                    sunday_tasks.append(child)
        
        assert len(sunday_tasks) == 0, f"Found {len(sunday_tasks)} tasks on Sunday - should be 0"
        print(f"Verified: {len(child_tasks)} child tasks, none on Sunday")
    
    # ==================== Regression Tests: Existing Recurrence Types ====================
    
    def test_06_weekly_recurrence_still_works(self):
        """Regression: Weekly recurrence type still works"""
        response = self._create_recurring_task(
            recurrence_type="weekly",
            recurrence_config={"day_of_week": "monday"},
            title_suffix="monday"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("is_recurring") == True
        assert task.get("recurrence_type") == "weekly"
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Weekly recurrence: {instances_count} instances created")
    
    def test_07_fortnightly_recurrence_still_works(self):
        """Regression: Fortnightly recurrence type still works"""
        response = self._create_recurring_task(
            recurrence_type="fortnightly",
            recurrence_config={},
            title_suffix="biweekly"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("recurrence_type") == "fortnightly"
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Fortnightly recurrence: {instances_count} instances created")
    
    def test_08_monthly_recurrence_still_works(self):
        """Regression: Monthly recurrence type still works"""
        # Use longer end date for monthly (90 days to ensure at least 2 instances)
        due_date = (datetime.now() + timedelta(days=1)).isoformat()
        end_date = (datetime.now() + timedelta(days=90)).isoformat()
        
        task_data = {
            "title": f"TEST_Recurring_monthly_{datetime.now().strftime('%H%M%S')}",
            "description": "Test task for monthly recurrence",
            "client_name": CLIENT_NAME,
            "category": CATEGORY,
            "assignee_id": ASSIGNEE_ID,
            "priority": "medium",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "monthly",
            "recurrence_config": {},
            "recurrence_end_date": end_date
        }
        
        response = self.session.post(f"{BASE_URL}/api/tasks", json=task_data)
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        self.created_task_ids.append(task["id"])
        
        # Track child tasks for cleanup
        tasks_response = self.session.get(f"{BASE_URL}/api/tasks")
        if tasks_response.status_code == 200:
            all_tasks = tasks_response.json()
            for t in all_tasks:
                if t.get("parent_recurring_id") == task["id"]:
                    self.created_task_ids.append(t["id"])
        
        assert task.get("recurrence_type") == "monthly"
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Monthly recurrence: {instances_count} instances created")
    
    def test_09_custom_day_of_month_still_works(self):
        """Regression: Custom day of month recurrence still works"""
        # Use longer end date for custom_day_of_month (90 days to ensure at least 2 instances)
        due_date = (datetime.now() + timedelta(days=1)).isoformat()
        end_date = (datetime.now() + timedelta(days=90)).isoformat()
        
        task_data = {
            "title": f"TEST_Recurring_custom_day_of_month_{datetime.now().strftime('%H%M%S')}",
            "description": "Test task for custom_day_of_month recurrence",
            "client_name": CLIENT_NAME,
            "category": CATEGORY,
            "assignee_id": ASSIGNEE_ID,
            "priority": "medium",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_type": "custom_day_of_month",
            "recurrence_config": {"day_of_month": 15},
            "recurrence_end_date": end_date
        }
        
        response = self.session.post(f"{BASE_URL}/api/tasks", json=task_data)
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        self.created_task_ids.append(task["id"])
        
        # Track child tasks for cleanup
        tasks_response = self.session.get(f"{BASE_URL}/api/tasks")
        if tasks_response.status_code == 200:
            all_tasks = tasks_response.json()
            for t in all_tasks:
                if t.get("parent_recurring_id") == task["id"]:
                    self.created_task_ids.append(t["id"])
        
        assert task.get("recurrence_type") == "custom_day_of_month"
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Custom day of month: {instances_count} instances created")
    
    def test_10_custom_day_of_week_still_works(self):
        """Regression: Custom day of week recurrence still works"""
        response = self._create_recurring_task(
            recurrence_type="custom_day_of_week",
            recurrence_config={"day_of_week": "wednesday", "every_n_weeks": 2},
            title_suffix="wed_every_2_weeks"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("recurrence_type") == "custom_day_of_week"
        instances_count = task.get("recurring_instances_created", 0)
        assert instances_count > 0, "No recurring instances were created"
        print(f"Custom day of week: {instances_count} instances created")
    
    def test_11_half_yearly_recurrence_still_works(self):
        """Regression: Half yearly recurrence type still works"""
        response = self._create_recurring_task(
            recurrence_type="half_yearly",
            recurrence_config={},
            title_suffix="6months"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("recurrence_type") == "half_yearly"
        instances_count = task.get("recurring_instances_created", 0)
        # Half yearly may have 0 or 1 instance in 30 days
        print(f"Half yearly recurrence: {instances_count} instances created")
    
    def test_12_annually_recurrence_still_works(self):
        """Regression: Annual recurrence type still works"""
        response = self._create_recurring_task(
            recurrence_type="annually",
            recurrence_config={},
            title_suffix="yearly"
        )
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task.get("recurrence_type") == "annually"
        # Annual may have 0 instances in 30 days
        print(f"Annual recurrence: task created successfully")


class TestNonRecurringTaskBaseline:
    """Baseline test for non-recurring tasks"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_task_ids = []
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        
        # Cleanup
        for task_id in self.created_task_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/tasks/{task_id}")
            except Exception:
                pass
    
    def test_non_recurring_task_creation(self):
        """Baseline: Non-recurring task creation still works"""
        task_data = {
            "title": f"TEST_NonRecurring_{datetime.now().strftime('%H%M%S')}",
            "description": "Test non-recurring task",
            "client_name": CLIENT_NAME,
            "category": CATEGORY,
            "assignee_id": ASSIGNEE_ID,
            "priority": "medium",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "is_recurring": False
        }
        
        response = self.session.post(f"{BASE_URL}/api/tasks", json=task_data)
        
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        
        task = response.json()
        self.created_task_ids.append(task["id"])
        
        assert task.get("title") == task_data["title"]
        assert "recurring_instances_created" not in task or task.get("recurring_instances_created", 0) == 0
        print("Non-recurring task created successfully")
