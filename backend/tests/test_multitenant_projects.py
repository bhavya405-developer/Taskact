"""
Backend API Tests for TaskAct Multi-Tenant and Projects Feature
Tests: Multi-tenant login, Super Admin, Projects with sub-tasks, Templates
"""
import pytest
import requests
import os
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://taskact-preview.preview.emergentagent.com').rstrip('/')

# Test credentials - Multi-tenant login
COMPANY_CODE = "SCO1"
PARTNER_EMAIL = "bhavika@sundesha.in"
PARTNER_PASSWORD = "password123"

# Super Admin credentials
SUPER_ADMIN_EMAIL = "admin@taskact.com"
SUPER_ADMIN_PASSWORD = "admin123"


class TestTenantLookupAPI:
    """Test tenant lookup - public endpoint for company code verification"""
    
    def test_tenant_lookup_valid_code(self):
        """Test GET /api/tenant/lookup/{code} with valid code"""
        response = requests.get(f"{BASE_URL}/api/tenant/lookup/{COMPANY_CODE}")
        assert response.status_code == 200, f"Tenant lookup failed: {response.text}"
        data = response.json()
        assert "name" in data, "Missing 'name' in response"
        assert "code" in data, "Missing 'code' in response"
        assert data["code"] == COMPANY_CODE, f"Code mismatch: expected {COMPANY_CODE}, got {data['code']}"
        assert data["name"] == "Sundesha & Co LLP", f"Expected 'Sundesha & Co LLP', got {data['name']}"
    
    def test_tenant_lookup_invalid_code(self):
        """Test GET /api/tenant/lookup/{code} with invalid code"""
        response = requests.get(f"{BASE_URL}/api/tenant/lookup/INVALID123")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Missing error detail"
    
    def test_tenant_lookup_lowercase_code(self):
        """Test tenant lookup with lowercase code (should work - converted to uppercase)"""
        response = requests.get(f"{BASE_URL}/api/tenant/lookup/sco1")
        assert response.status_code == 200, f"Lowercase tenant lookup failed: {response.text}"


class TestMultiTenantLogin:
    """Test multi-tenant login with company code"""
    
    def test_login_with_company_code(self):
        """Test POST /api/auth/login with company_code, email, password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "company_code": COMPANY_CODE,
                "email": PARTNER_EMAIL,
                "password": PARTNER_PASSWORD
            }
        )
        assert response.status_code == 200, f"Multi-tenant login failed: {response.text}"
        data = response.json()
        
        # Verify token
        assert "access_token" in data, "Missing access_token"
        assert "token_type" in data, "Missing token_type"
        assert data["token_type"] == "bearer"
        
        # Verify user
        assert "user" in data, "Missing user object"
        assert data["user"]["email"] == PARTNER_EMAIL
        
        # Verify tenant info is returned
        assert "tenant" in data, "Missing tenant object in login response"
        assert data["tenant"]["code"] == COMPANY_CODE
        assert data["tenant"]["name"] == "Sundesha & Co LLP"
    
    def test_login_invalid_company_code(self):
        """Test login with invalid company code"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "company_code": "INVALID",
                "email": PARTNER_EMAIL,
                "password": PARTNER_PASSWORD
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_login_wrong_password(self):
        """Test login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "company_code": COMPANY_CODE,
                "email": PARTNER_EMAIL,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
    
    def test_get_current_user_with_tenant(self, partner_token):
        """Test GET /api/auth/me returns tenant info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get current user failed: {response.text}"
        data = response.json()
        
        # Verify tenant info in response
        assert "tenant" in data, "Missing tenant info in /auth/me response"
        assert data["tenant"]["code"] == COMPANY_CODE


class TestSuperAdminAPI:
    """Test Super Admin endpoints"""
    
    def test_super_admin_login(self):
        """Test POST /api/super-admin/login"""
        response = requests.post(
            f"{BASE_URL}/api/super-admin/login",
            json={
                "email": SUPER_ADMIN_EMAIL,
                "password": SUPER_ADMIN_PASSWORD
            }
        )
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data, "Missing access_token"
        assert "admin" in data, "Missing admin object"
        assert data["admin"]["role"] == "super_admin"
        assert data["admin"]["email"] == SUPER_ADMIN_EMAIL
    
    def test_super_admin_login_invalid(self):
        """Test super admin login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/super-admin/login",
            json={
                "email": "wrong@admin.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
    
    def test_super_admin_me(self, super_admin_token):
        """Test GET /api/super-admin/me"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/me",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200, f"Super admin /me failed: {response.text}"
        data = response.json()
        
        assert data["role"] == "super_admin"
        assert data["email"] == SUPER_ADMIN_EMAIL
    
    def test_super_admin_dashboard(self, super_admin_token):
        """Test GET /api/super-admin/dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/dashboard",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200, f"Super admin dashboard failed: {response.text}"
        data = response.json()
        
        # Verify statistics
        assert "statistics" in data, "Missing statistics"
        stats = data["statistics"]
        assert "total_tenants" in stats
        assert "active_tenants" in stats
        assert "total_users" in stats
        assert "active_users" in stats
        assert "total_tasks" in stats
        
        # Verify recent tenants
        assert "recent_tenants" in data
    
    def test_get_tenants_list(self, super_admin_token):
        """Test GET /api/tenants"""
        response = requests.get(
            f"{BASE_URL}/api/tenants",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200, f"Get tenants failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one tenant"
        
        # Verify tenant structure
        tenant = data[0]
        assert "id" in tenant
        assert "name" in tenant
        assert "code" in tenant
        assert "plan" in tenant
        assert "max_users" in tenant
        assert "active" in tenant
        assert "user_count" in tenant
        assert "task_count" in tenant
    
    def test_get_tenant_users(self, super_admin_token, tenant_id):
        """Test GET /api/tenants/{tenant_id}/users"""
        response = requests.get(
            f"{BASE_URL}/api/tenants/{tenant_id}/users",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200, f"Get tenant users failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        if len(data) > 0:
            user = data[0]
            assert "id" in user
            assert "name" in user
            assert "email" in user
            assert "role" in user


class TestProjectsAPI:
    """Test Projects management endpoints"""
    
    def test_get_projects_list(self, partner_token):
        """Test GET /api/projects"""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get projects failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
    
    def test_create_project(self, partner_token, partner_user_id):
        """Test POST /api/projects - create a project with sub-tasks"""
        project_data = {
            "title": f"TEST_Project_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Test project with sub-tasks",
            "client_name": "Test Client",
            "category": "Testing",
            "priority": "high",
            "estimated_hours": 10,
            "sub_tasks": [
                {"title": "Sub-task 1", "estimated_hours": 2, "priority": "high"},
                {"title": "Sub-task 2", "estimated_hours": 3, "priority": "medium"},
                {"title": "Sub-task 3", "estimated_hours": 5, "priority": "low"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects",
            json=project_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Create project failed: {response.text}"
        data = response.json()
        
        # Verify project fields
        assert "id" in data
        assert data["title"] == project_data["title"]
        assert data["status"] == "draft"  # No assignee, so draft
        assert "sub_tasks" in data
        assert len(data["sub_tasks"]) == 3
        
        # Verify sub-task structure
        for st in data["sub_tasks"]:
            assert "id" in st
            assert "title" in st
            assert "status" in st
            assert st["status"] == "pending"
        
        return data["id"]
    
    def test_create_project_with_assignee(self, partner_token, partner_user_id):
        """Test creating project with assignee - should be allocated"""
        project_data = {
            "title": f"TEST_Allocated_Project_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Allocated project test",
            "client_name": "Test Client",
            "category": "Testing",
            "assignee_id": partner_user_id,
            "sub_tasks": [
                {"title": "First task", "estimated_hours": 1, "priority": "high"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects",
            json=project_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Create allocated project failed: {response.text}"
        data = response.json()
        
        # Should be allocated status when assignee provided
        assert data["status"] == "allocated", f"Expected 'allocated', got {data['status']}"
        assert data["assignee_id"] == partner_user_id
        assert "assignee_name" in data
    
    def test_get_specific_project(self, partner_token, test_project_id):
        """Test GET /api/projects/{project_id}"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{test_project_id}",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get project failed: {response.text}"
        data = response.json()
        
        assert data["id"] == test_project_id
        assert "sub_tasks" in data


class TestProjectTemplatesAPI:
    """Test Project Templates endpoints"""
    
    def test_get_templates_list(self, partner_token):
        """Test GET /api/project-templates"""
        response = requests.get(
            f"{BASE_URL}/api/project-templates",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Get templates failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
    
    def test_create_template(self, partner_token):
        """Test POST /api/project-templates"""
        template_data = {
            "name": f"TEST_Template_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Test template",
            "category": "Testing",
            "estimated_hours": 5,
            "sub_tasks": [
                {"title": "Template sub-task 1", "estimated_hours": 2, "priority": "high"},
                {"title": "Template sub-task 2", "estimated_hours": 3, "priority": "medium"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/project-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Create template failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["name"] == template_data["name"]
        assert data["scope"] == "tenant"  # Partner creates tenant-scoped templates
        assert len(data["sub_tasks"]) == 2
        
        return data["id"]
    
    def test_use_template(self, partner_token, test_template_id):
        """Test POST /api/project-templates/{id}/use"""
        response = requests.post(
            f"{BASE_URL}/api/project-templates/{test_template_id}/use",
            params={
                "title": f"Project from Template {datetime.now().strftime('%H%M%S')}",
                "client_name": "Template Test Client"
            },
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Use template failed: {response.text}"
        data = response.json()
        
        # Verify project was created from template
        assert "id" in data
        assert data["from_template_id"] == test_template_id
        assert data["status"] == "ready"  # No assignee, but from template


class TestSubTasksAPI:
    """Test sub-task management within projects"""
    
    def test_add_subtask(self, partner_token, test_project_id):
        """Test POST /api/projects/{project_id}/subtasks"""
        subtask_data = {
            "title": f"Added Sub-task {datetime.now().strftime('%H%M%S')}",
            "estimated_hours": 2,
            "priority": "high"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects/{test_project_id}/subtasks",
            json=subtask_data,
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Add subtask failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["title"] == subtask_data["title"]
        assert data["status"] == "pending"
        
        return data["id"]
    
    def test_update_subtask_status(self, partner_token, test_project_id, test_subtask_id):
        """Test PUT /api/projects/{project_id}/subtasks/{subtask_id}"""
        response = requests.put(
            f"{BASE_URL}/api/projects/{test_project_id}/subtasks/{test_subtask_id}",
            json={"status": "completed"},
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200, f"Update subtask failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "completed"
        assert "completed_at" in data
        assert "completed_by" in data


class TestDataIsolation:
    """Test data isolation between tenants"""
    
    def test_projects_filtered_by_tenant(self, partner_token):
        """Test that projects API returns only tenant's projects"""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {partner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned projects should have same tenant_id
        if len(data) > 0:
            tenant_id = data[0].get("tenant_id")
            for project in data:
                assert project.get("tenant_id") == tenant_id, "Data isolation failure: projects from multiple tenants"


# ==================== FIXTURES ====================

@pytest.fixture(scope="session")
def partner_token():
    """Get partner authentication token with company code"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "company_code": COMPANY_CODE,
            "email": PARTNER_EMAIL,
            "password": PARTNER_PASSWORD
        }
    )
    if response.status_code != 200:
        pytest.skip(f"Partner login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def super_admin_token():
    """Get super admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/super-admin/login",
        json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        }
    )
    if response.status_code != 200:
        pytest.skip(f"Super admin login failed: {response.text}")
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
def tenant_id(super_admin_token):
    """Get first tenant ID"""
    response = requests.get(
        f"{BASE_URL}/api/tenants",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    if response.status_code != 200:
        pytest.skip(f"Get tenants failed: {response.text}")
    tenants = response.json()
    if not tenants:
        pytest.skip("No tenants found")
    return tenants[0]["id"]


@pytest.fixture(scope="session")
def test_project_id(partner_token, partner_user_id):
    """Create a test project and return its ID"""
    project_data = {
        "title": f"TEST_Fixture_Project_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "Test project for fixtures",
        "client_name": "Fixture Client",
        "category": "Testing",
        "sub_tasks": [
            {"title": "Fixture sub-task 1", "estimated_hours": 1, "priority": "high"},
            {"title": "Fixture sub-task 2", "estimated_hours": 2, "priority": "medium"}
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/projects",
        json=project_data,
        headers={"Authorization": f"Bearer {partner_token}"}
    )
    if response.status_code != 200:
        pytest.skip(f"Create test project failed: {response.text}")
    return response.json()["id"]


@pytest.fixture(scope="session")
def test_template_id(partner_token):
    """Create a test template and return its ID"""
    template_data = {
        "name": f"TEST_Fixture_Template_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "Test template for fixtures",
        "category": "Testing",
        "sub_tasks": [
            {"title": "Template task 1", "estimated_hours": 1, "priority": "high"}
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/project-templates",
        json=template_data,
        headers={"Authorization": f"Bearer {partner_token}"}
    )
    if response.status_code != 200:
        pytest.skip(f"Create test template failed: {response.text}")
    return response.json()["id"]


@pytest.fixture(scope="session")
def test_subtask_id(partner_token, test_project_id):
    """Get first subtask ID from test project"""
    response = requests.get(
        f"{BASE_URL}/api/projects/{test_project_id}",
        headers={"Authorization": f"Bearer {partner_token}"}
    )
    if response.status_code != 200:
        pytest.skip(f"Get project failed: {response.text}")
    
    project = response.json()
    if not project.get("sub_tasks"):
        pytest.skip("No sub-tasks in test project")
    
    return project["sub_tasks"][0]["id"]
