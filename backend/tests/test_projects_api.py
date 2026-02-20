"""
Test suite for Projects and Templates API
Tests the refactored project management where sub-tasks are real tasks stored in main tasks collection
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://workflow-hub-240.preview.emergentagent.com').rstrip('/')

# Test credentials
PARTNER_CREDENTIALS = {
    "company_code": "SCO1",
    "email": "bhavika@sundesha.in",
    "password": "password123"
}


class TestProjectsAPI:
    """Tests for Projects endpoints - projects with tasks stored in main tasks collection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=PARTNER_CREDENTIALS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data["access_token"]
        self.user_id = data["user"]["id"]
        self.tenant_id = data.get("tenant", {}).get("id")
        
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup
        self.session.close()
    
    def test_01_api_health(self):
        """Test API is running"""
        response = self.session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        assert "TaskAct API is running" in response.json().get("message", "")
        print("✓ API health check passed")
    
    def test_02_get_projects_list(self):
        """Test GET /api/projects returns project list"""
        response = self.session.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        
        projects = response.json()
        assert isinstance(projects, list)
        print(f"✓ Projects list returned {len(projects)} projects")
        
        # Verify project structure
        if len(projects) > 0:
            project = projects[0]
            assert "id" in project
            assert "name" in project
            assert "total_tasks" in project
            assert "completed_tasks" in project
            assert "progress" in project
            assert "can_edit" in project
            print(f"✓ First project: {project['name']} with {project['total_tasks']} tasks")
    
    def test_03_get_templates_list(self):
        """Test GET /api/project-templates returns templates list"""
        response = self.session.get(f"{BASE_URL}/api/project-templates")
        assert response.status_code == 200
        
        templates = response.json()
        assert isinstance(templates, list)
        print(f"✓ Templates list returned {len(templates)} templates")
        
        # Verify template structure
        if len(templates) > 0:
            template = templates[0]
            assert "id" in template
            assert "name" in template
            assert "tasks" in template or "sub_tasks" in template
            assert "can_edit" in template
            assert "can_delete" in template
            print(f"✓ First template: {template['name']}")
    
    def test_04_get_clients_for_dropdown(self):
        """Test GET /api/clients returns clients for dropdown"""
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        
        clients = response.json()
        assert isinstance(clients, list)
        assert len(clients) > 0, "Clients list should not be empty"
        
        # Verify client structure
        client = clients[0]
        assert "id" in client
        assert "name" in client
        print(f"✓ Clients dropdown: {len(clients)} clients available")
    
    def test_05_get_categories_for_dropdown(self):
        """Test GET /api/categories returns categories for dropdown"""
        response = self.session.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0, "Categories list should not be empty"
        
        # Verify category structure
        category = categories[0]
        assert "id" in category
        assert "name" in category
        print(f"✓ Categories dropdown: {len(categories)} categories available")
    
    def test_06_create_project_with_tasks(self):
        """Test POST /api/projects creates project with tasks in main tasks collection"""
        # Get a client ID
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        client_id = clients_response.json()[0]["id"] if clients_response.json() else None
        
        # Get a user ID for task assignment
        users_response = self.session.get(f"{BASE_URL}/api/users")
        assert users_response.status_code == 200
        users = users_response.json()
        assignee_id = users[0]["id"] if users else self.user_id
        
        # Create project with tasks
        unique_name = f"TEST_Project_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique_name,
            "description": "Test project created by pytest",
            "client_id": client_id,
            "category": "Accounting",
            "due_date": "2026-04-15",
            "tasks": [
                {
                    "title": "Task 1 - Test Task",
                    "description": "First test task",
                    "priority": "high",
                    "assignee_id": assignee_id
                },
                {
                    "title": "Task 2 - Another Task",
                    "description": "Second test task",
                    "priority": "medium",
                    "assignee_id": assignee_id
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/projects", json=payload)
        assert response.status_code == 200, f"Failed to create project: {response.text}"
        
        project = response.json()
        self.created_project_id = project["id"]
        
        # Verify project data
        assert project["name"] == unique_name
        assert project["total_tasks"] == 2
        assert "tasks" in project
        assert len(project["tasks"]) == 2
        
        # Verify tasks have project_id
        for task in project["tasks"]:
            assert task["project_id"] == project["id"]
            assert task["status"] == "pending"
        
        print(f"✓ Created project '{unique_name}' with 2 tasks")
        
        # Cleanup - delete the project
        delete_response = self.session.delete(f"{BASE_URL}/api/projects/{self.created_project_id}")
        assert delete_response.status_code == 200
        print(f"✓ Cleaned up test project")
    
    def test_07_get_project_details(self):
        """Test GET /api/projects/{id} returns project with tasks"""
        # First get list of projects
        response = self.session.get(f"{BASE_URL}/api/projects")
        projects = response.json()
        
        # Find a project with tasks
        project_with_tasks = None
        for p in projects:
            if p.get("total_tasks", 0) > 0:
                project_with_tasks = p
                break
        
        if not project_with_tasks:
            pytest.skip("No project with tasks found")
        
        # Get project details
        response = self.session.get(f"{BASE_URL}/api/projects/{project_with_tasks['id']}")
        assert response.status_code == 200
        
        project = response.json()
        assert project["id"] == project_with_tasks["id"]
        assert "tasks" in project
        assert len(project["tasks"]) == project["total_tasks"]
        
        print(f"✓ Project details: {project['name']} has {len(project['tasks'])} tasks")
    
    def test_08_create_template(self):
        """Test POST /api/project-templates creates a template"""
        unique_name = f"TEST_Template_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique_name,
            "description": "Test template created by pytest",
            "category": "Accounting",
            "tasks": [
                {
                    "title": "Template Task 1",
                    "description": "First task blueprint",
                    "priority": "high",
                    "order": 0
                },
                {
                    "title": "Template Task 2",
                    "description": "Second task blueprint",
                    "priority": "medium",
                    "order": 1
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/project-templates", json=payload)
        assert response.status_code == 200, f"Failed to create template: {response.text}"
        
        template = response.json()
        self.created_template_id = template["id"]
        
        # Verify template data
        assert template["name"] == unique_name
        assert len(template["tasks"]) == 2
        assert template["scope"] == "tenant"  # Partners create tenant-scope templates
        
        print(f"✓ Created template '{unique_name}' with 2 task blueprints")
        
        # Cleanup - delete the template
        delete_response = self.session.delete(f"{BASE_URL}/api/project-templates/{self.created_template_id}")
        assert delete_response.status_code == 200
        print(f"✓ Cleaned up test template")
    
    def test_09_delete_project_deletes_tasks(self):
        """Test DELETE /api/projects/{id} also deletes associated tasks"""
        # Create a test project
        users_response = self.session.get(f"{BASE_URL}/api/users")
        assignee_id = users_response.json()[0]["id"] if users_response.json() else self.user_id
        
        payload = {
            "name": f"TEST_Delete_Project_{uuid.uuid4().hex[:8]}",
            "description": "Project to test deletion",
            "due_date": "2026-05-01",
            "tasks": [
                {
                    "title": "Task to be deleted",
                    "priority": "medium",
                    "assignee_id": assignee_id
                }
            ]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/projects", json=payload)
        assert create_response.status_code == 200
        
        project_id = create_response.json()["id"]
        
        # Delete project
        delete_response = self.session.delete(f"{BASE_URL}/api/projects/{project_id}")
        assert delete_response.status_code == 200
        
        result = delete_response.json()
        assert "tasks deleted" in result["message"].lower() or "1 tasks" in result["message"]
        
        print(f"✓ Project deletion also deleted associated tasks")
    
    def test_10_partner_can_edit_own_template(self):
        """Test partner can edit/delete templates from their company"""
        # Get templates
        response = self.session.get(f"{BASE_URL}/api/project-templates")
        templates = response.json()
        
        # Find a tenant template (not global)
        tenant_template = None
        for t in templates:
            if t.get("scope") == "tenant" and t.get("can_edit"):
                tenant_template = t
                break
        
        if tenant_template:
            assert tenant_template["can_edit"] == True
            assert tenant_template["can_delete"] == True
            print(f"✓ Partner can edit/delete tenant template: {tenant_template['name']}")
        else:
            # Create one to test
            payload = {
                "name": f"TEST_EditCheck_{uuid.uuid4().hex[:8]}",
                "description": "Test edit permissions",
                "tasks": [{"title": "Test task", "priority": "medium", "order": 0}]
            }
            create_response = self.session.post(f"{BASE_URL}/api/project-templates", json=payload)
            assert create_response.status_code == 200
            
            template = create_response.json()
            assert template["can_edit"] == True
            assert template["can_delete"] == True
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/project-templates/{template['id']}")
            print(f"✓ Partner can edit/delete their own templates")
    
    def test_11_partner_cannot_edit_global_template(self):
        """Test partner cannot edit global templates (created by super admin)"""
        response = self.session.get(f"{BASE_URL}/api/project-templates")
        templates = response.json()
        
        # Find a global template
        global_template = None
        for t in templates:
            if t.get("scope") == "global":
                global_template = t
                break
        
        if global_template:
            assert global_template["can_edit"] == False
            assert global_template["can_delete"] == False
            print(f"✓ Partner cannot edit global template: {global_template['name']}")
        else:
            print("✓ No global templates found - test skipped (expected if no super admin templates)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
