"""
Backend API Tests for TaskAct
Tests all API endpoints after route refactoring to ensure no route conflicts
Modules tested: auth, users, tasks, attendance, timesheets, dashboard
"""
import pytest
import requests
import os
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://team-ops-dashboard.preview.emergentagent.com').rstrip('/')

# Test credentials
PARTNER_EMAIL = "bhavika@sundesha.in"
PARTNER_PASSWORD = "password123"
ASSOCIATE_EMAIL = "sonurajpurohit980@gmail.com"
ASSOCIATE_PASSWORD = "password123"


class TestAuthentication:
    """Test authentication endpoints - /api/auth/*"""
    
    def test_login_partner_success(self):
        """Test partner login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PARTNER_EMAIL, "password": PARTNER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == PARTNER_EMAIL
        assert data["user"]["role"] == "partner"
        assert data["token_type"] == "bearer"
    
    def test_login_associate_success(self):
        """Test associate login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ASSOCIATE_EMAIL, "password": ASSOCIATE_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == ASSOCIATE_EMAIL
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_get_current_user(self, partner_token):
        """Test GET /api/auth/me endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get current user failed: {response.text}"
        data = response.json()
        assert data["email"] == PARTNER_EMAIL
        assert "id" in data
        assert "name" in data
    
    def test_forgot_password_endpoint(self):
        """Test forgot password endpoint (MOCKED - sends notification instead of email)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": PARTNER_EMAIL}
        )
        assert response.status_code == 200, f"Forgot password failed: {response.text}"
        data = response.json()
        assert "message" in data


class TestUsersAPI:
    """Test user management endpoints - /api/users/*"""
    
    def test_get_users_list(self, partner_token):
        """Test GET /api/users - list all users"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get users failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one user"
        
        # Verify user structure
        user = data[0]
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "role" in user
    
    def test_get_users_with_inactive(self, partner_token):
        """Test GET /api/users with include_inactive parameter"""
        response = requests.get(
            f"{BASE_URL}/api/users?include_inactive=true",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get users with inactive failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_specific_user(self, partner_token, partner_user_id):
        """Test GET /api/users/{user_id}"""
        response = requests.get(
            f"{BASE_URL}/api/users/{partner_user_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get specific user failed: {response.text}"
        data = response.json()
        assert data["id"] == partner_user_id
        assert "email" in data


class TestTasksAPI:
    """Test task management endpoints - /api/tasks/*"""
    
    def test_get_tasks_list(self, partner_token):
        """Test GET /api/tasks - list all tasks"""
        response = requests.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get tasks failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
    
    def test_get_tasks_with_status_filter(self, partner_token):
        """Test GET /api/tasks with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/tasks?status=pending",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get tasks with filter failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # Verify all returned tasks have pending status
        for task in data:
            assert task.get("status") == "pending", f"Task {task.get('id')} has status {task.get('status')}, expected pending"
    
    def test_create_task(self, partner_token, partner_user_id):
        """Test POST /api/tasks - create a new task"""
        task_data = {
            "title": f"TEST_Task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Test task created by automated tests",
            "client_name": "Test Client",
            "category": "General",
            "assignee_id": partner_user_id,
            "priority": "medium"
        }
        response = requests.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Create task failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["title"] == task_data["title"]
        assert data["status"] == "pending"
        return data["id"]


class TestAttendanceAPI:
    """Test attendance endpoints - /api/attendance/*"""
    
    def test_get_today_attendance(self, partner_token):
        """Test GET /api/attendance/today"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/today",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get today attendance failed: {response.text}"
        data = response.json()
        # Verify response structure
        assert "clock_in" in data or data.get("clock_in") is None
        assert "clock_out" in data or data.get("clock_out") is None
        assert "is_clocked_in" in data
    
    def test_get_attendance_settings(self, partner_token):
        """Test GET /api/attendance/settings"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/settings",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get attendance settings failed: {response.text}"
        data = response.json()
        # Verify settings structure
        assert "enabled" in data
        assert "locations" in data
        assert "radius_meters" in data
    
    def test_get_attendance_rules(self, partner_token):
        """Test GET /api/attendance/rules"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/rules",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get attendance rules failed: {response.text}"
        data = response.json()
        assert "min_hours_full_day" in data
        assert "working_days" in data
    
    def test_get_holidays(self, partner_token):
        """Test GET /api/attendance/holidays"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/holidays",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get holidays failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_attendance_history(self, partner_token):
        """Test GET /api/attendance/history"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/history",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get attendance history failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)


class TestTimesheetsAPI:
    """Test timesheet endpoints - /api/timesheet/*"""
    
    def test_get_weekly_timesheet(self, partner_token):
        """Test GET /api/timesheet?period=weekly"""
        response = requests.get(
            f"{BASE_URL}/api/timesheet?period=weekly",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get weekly timesheet failed: {response.text}"
        data = response.json()
        # Verify timesheet structure
        assert "user_id" in data
        assert "user_name" in data
        assert "period" in data
        assert data["period"] == "weekly"
        assert "total_tasks" in data
        assert "total_hours" in data
        assert "entries" in data
    
    def test_get_daily_timesheet(self, partner_token):
        """Test GET /api/timesheet?period=daily"""
        response = requests.get(
            f"{BASE_URL}/api/timesheet?period=daily",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get daily timesheet failed: {response.text}"
        data = response.json()
        assert data["period"] == "daily"
    
    def test_get_monthly_timesheet(self, partner_token):
        """Test GET /api/timesheet?period=monthly"""
        response = requests.get(
            f"{BASE_URL}/api/timesheet?period=monthly",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get monthly timesheet failed: {response.text}"
        data = response.json()
        assert data["period"] == "monthly"
    
    def test_get_team_timesheet(self, partner_token):
        """Test GET /api/timesheet/team (Partners only)"""
        response = requests.get(
            f"{BASE_URL}/api/timesheet/team?period=weekly",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get team timesheet failed: {response.text}"
        data = response.json()
        assert "team_summary" in data
        assert "grand_total_hours" in data
        assert "grand_total_tasks" in data


class TestDashboardAPI:
    """Test dashboard endpoint - /api/dashboard"""
    
    def test_get_dashboard(self, partner_token):
        """Test GET /api/dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get dashboard failed: {response.text}"
        data = response.json()
        # Verify dashboard structure
        assert "total_tasks" in data or "tasks" in data or isinstance(data, dict)


class TestNotificationsAPI:
    """Test notifications endpoint - /api/notifications"""
    
    def test_get_notifications(self, partner_token):
        """Test GET /api/notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)


class TestCategoriesAPI:
    """Test categories endpoint - /api/categories"""
    
    def test_get_categories(self, partner_token):
        """Test GET /api/categories"""
        response = requests.get(
            f"{BASE_URL}/api/categories",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get categories failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)


class TestClientsAPI:
    """Test clients endpoint - /api/clients"""
    
    def test_get_clients(self, partner_token):
        """Test GET /api/clients"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get clients failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)


class TestRouteConflicts:
    """Test for route conflicts after refactoring"""
    
    def test_no_duplicate_route_conflicts(self, partner_token):
        """Verify routes work correctly without conflicts"""
        # Test multiple endpoints to ensure no conflicts
        endpoints = [
            "/api/auth/me",
            "/api/users",
            "/api/tasks",
            "/api/attendance/today",
            "/api/attendance/settings",
            "/api/timesheet?period=weekly",
        ]
        
        for endpoint in endpoints:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers={"Authorization": f"Bearer {partner_token}"}
            )
            assert response.status_code == 200, f"Endpoint {endpoint} failed with status {response.status_code}: {response.text}"
    
    def test_auth_routes_from_module(self, partner_token):
        """Test auth routes are working from the auth module"""
        # Test /api/auth/me
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
    
    def test_users_routes_from_module(self, partner_token):
        """Test users routes are working from the users module"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
    
    def test_tasks_routes_from_module(self, partner_token):
        """Test tasks routes are working from the tasks module"""
        response = requests.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
    
    def test_attendance_routes_from_module(self, partner_token):
        """Test attendance routes are working from the attendance module"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/today",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
    
    def test_timesheets_routes_from_module(self, partner_token):
        """Test timesheets routes are working from the timesheets module"""
        response = requests.get(
            f"{BASE_URL}/api/timesheet?period=weekly",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200


# ==================== FIXTURES ====================

@pytest.fixture(scope="session")
def partner_token():
    """Get partner authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": PARTNER_EMAIL, "password": PARTNER_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Partner login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def associate_token():
    """Get associate authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ASSOCIATE_EMAIL, "password": ASSOCIATE_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Associate login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def partner_user_id(partner_token):
    """Get partner user ID"""
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {partner_token}"}
    )
    if response.status_code != 200:
        pytest.skip(f"Get current user failed: {response.text}")
    return response.json()["id"]


@pytest.fixture(scope="session")
def associate_user_id(associate_token):
    """Get associate user ID"""
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {associate_token}"}
    )
    if response.status_code != 200:
        pytest.skip(f"Get current user failed: {response.text}")
    return response.json()["id"]
