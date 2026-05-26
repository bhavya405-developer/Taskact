"""
Test suite for the 4 fixes:
1. Date format DD-MMM-YY
2. Deactivated users not in assign dropdowns (code review - filter present)
3. Dashboard refresh after task update (frontend test)
4. Token expiry 8 hours + auto-redirect on 401
"""
import pytest
import requests
import os
import jwt
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMPANY_CODE = "SCO1"
EMAIL = "bhavika@sundesha.in"
PASSWORD = "password123"


class TestTokenExpiry:
    """Test Fix 4: Token expiry is now 8 hours (480 minutes)"""
    
    def test_01_login_returns_valid_token(self):
        """Test that login returns a valid JWT token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        
        # Store token for other tests
        TestTokenExpiry.token = data["access_token"]
        TestTokenExpiry.user = data["user"]
        print(f"Login successful for user: {data['user']['name']}")
    
    def test_02_token_expiry_is_8_hours(self):
        """Verify token expiry is approximately 8 hours (480 minutes)"""
        token = getattr(TestTokenExpiry, 'token', None)
        if not token:
            pytest.skip("No token available - login test may have failed")
        
        # Decode JWT without verification to check expiry
        try:
            # Decode without verification to inspect claims
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            exp_timestamp = decoded.get("exp")
            assert exp_timestamp is not None, "Token has no expiry claim"
            
            # Calculate expiry duration
            exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
            now = datetime.utcnow()
            duration = exp_datetime - now
            
            # Token should expire in approximately 8 hours (480 minutes)
            # Allow some tolerance (7.5 to 8.5 hours)
            duration_hours = duration.total_seconds() / 3600
            
            print(f"Token expires at: {exp_datetime}")
            print(f"Current time: {now}")
            print(f"Duration until expiry: {duration_hours:.2f} hours")
            
            assert 7.5 <= duration_hours <= 8.5, f"Token expiry should be ~8 hours, got {duration_hours:.2f} hours"
            print(f"✓ Token expiry is correctly set to ~8 hours ({duration_hours:.2f} hours)")
            
        except jwt.DecodeError as e:
            pytest.fail(f"Failed to decode JWT: {e}")
    
    def test_03_expired_token_returns_401(self):
        """Test that an expired/invalid token returns 401"""
        # Create an obviously invalid token
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkLXVzZXIiLCJleHAiOjE2MDAwMDAwMDB9.invalid"
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"
        print("✓ Invalid/expired token correctly returns 401")
    
    def test_04_valid_token_works(self):
        """Test that a valid token allows access to protected endpoints"""
        token = getattr(TestTokenExpiry, 'token', None)
        if not token:
            pytest.skip("No token available - login test may have failed")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200 for valid token, got {response.status_code}"
        data = response.json()
        assert data.get("email") == EMAIL, "User email mismatch"
        print(f"✓ Valid token works - user: {data.get('name')}")


class TestDashboardAPI:
    """Test Fix 3: Dashboard API returns correct data for refresh"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Login failed")
    
    def test_01_dashboard_returns_task_counts(self):
        """Test dashboard endpoint returns task counts"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=self.headers)
        
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "task_counts" in data, "Missing task_counts"
        assert "recent_tasks" in data, "Missing recent_tasks"
        
        task_counts = data["task_counts"]
        assert "total" in task_counts, "Missing total count"
        assert "pending" in task_counts, "Missing pending count"
        assert "completed" in task_counts, "Missing completed count"
        assert "overdue" in task_counts, "Missing overdue count"
        
        print(f"✓ Dashboard returns task counts: {task_counts}")
    
    def test_02_dashboard_returns_overdue_and_due_7_days(self):
        """Test dashboard returns overdue_tasks and due_7_days_tasks lists"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overdue_tasks" in data, "Missing overdue_tasks list"
        assert "due_7_days_tasks" in data, "Missing due_7_days_tasks list"
        
        print(f"✓ Dashboard returns overdue_tasks ({len(data['overdue_tasks'])}) and due_7_days_tasks ({len(data['due_7_days_tasks'])})")


class TestUsersAPI:
    """Test Fix 2: Users API returns active status for filtering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Login failed")
    
    def test_01_users_have_active_field(self):
        """Test that users API returns active field for filtering"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        
        assert response.status_code == 200, f"Users API failed: {response.text}"
        users = response.json()
        
        assert len(users) > 0, "No users returned"
        
        # Check that users have the 'active' field
        for user in users:
            assert "active" in user, f"User {user.get('name')} missing 'active' field"
            assert isinstance(user["active"], bool), f"User {user.get('name')} 'active' field is not boolean"
        
        active_users = [u for u in users if u["active"]]
        inactive_users = [u for u in users if not u["active"]]
        
        print(f"✓ Users API returns active field - Active: {len(active_users)}, Inactive: {len(inactive_users)}")


class TestTasksAPI:
    """Test that tasks API returns dates that can be formatted"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "company_code": COMPANY_CODE,
            "email": EMAIL,
            "password": PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Login failed")
    
    def test_01_tasks_have_due_date_field(self):
        """Test that tasks have due_date field for date formatting"""
        response = requests.get(f"{BASE_URL}/api/tasks", headers=self.headers)
        
        assert response.status_code == 200, f"Tasks API failed: {response.text}"
        tasks = response.json()
        
        if len(tasks) == 0:
            print("No tasks found - skipping date field check")
            return
        
        # Check that tasks have due_date field
        tasks_with_due_date = [t for t in tasks if t.get("due_date")]
        
        print(f"✓ Tasks API returns {len(tasks)} tasks, {len(tasks_with_due_date)} have due_date")
        
        # Verify date format is ISO string that can be parsed
        if tasks_with_due_date:
            sample_date = tasks_with_due_date[0]["due_date"]
            try:
                # Try to parse as ISO format
                if "T" in sample_date:
                    datetime.fromisoformat(sample_date.replace("Z", "+00:00"))
                else:
                    datetime.strptime(sample_date, "%Y-%m-%d")
                print(f"✓ Due date format is valid ISO: {sample_date}")
            except ValueError as e:
                pytest.fail(f"Invalid date format: {sample_date} - {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
