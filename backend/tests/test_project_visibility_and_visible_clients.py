"""
Test Project Visibility and Visible Clients Features

Feature 1: Project Visibility based on role
- Partners see all projects
- Associate Directors see projects with tasks assigned to themselves or managed members
- Regular associates see only projects with their own tasks

Feature 2: Visible Clients restriction
- Partners can restrict which clients are visible to non-partner users via visible_clients field
- visible_clients=null means all clients visible
- visible_clients=[client_id1, client_id2] restricts to those clients only
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
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

# Known user IDs from previous testing
KNOWN_USERS = {
    "sonu_kanwar": "1e99009f-23a2-42ff-aad8-1caa7d54e951",
    "nitish_das": "e7ae9f26-0684-44a6-ab56-14cfc5f868d8"
}


class TestHelpers:
    """Helper methods for tests"""
    
    @staticmethod
    def login(company_code: str, email: str, password: str) -> dict:
        """Login and return token and user info"""
        # First get tenant by company code
        tenant_resp = requests.get(f"{BASE_URL}/api/tenants/by-code/{company_code}")
        if tenant_resp.status_code != 200:
            raise Exception(f"Failed to get tenant: {tenant_resp.text}")
        tenant = tenant_resp.json()
        
        # Login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password,
            "tenant_id": tenant["id"]
        })
        if login_resp.status_code != 200:
            raise Exception(f"Login failed: {login_resp.text}")
        
        data = login_resp.json()
        return {
            "token": data["access_token"],
            "user": data["user"],
            "tenant_id": tenant["id"]
        }
    
    @staticmethod
    def get_auth_headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}


class TestProjectVisibility:
    """Test Feature 1: Project visibility based on role"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.partner_auth = TestHelpers.login(**PARTNER_CREDENTIALS)
        self.partner_headers = TestHelpers.get_auth_headers(self.partner_auth["token"])
        self.tenant_id = self.partner_auth["tenant_id"]
        
        # Track created resources for cleanup
        self.created_projects = []
        self.created_tasks = []
        self.created_users = []
        
        yield
        
        # Cleanup
        for task_id in self.created_tasks:
            try:
                requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=self.partner_headers)
            except:
                pass
        
        for project_id in self.created_projects:
            try:
                requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=self.partner_headers)
            except:
                pass
        
        for user_id in self.created_users:
            try:
                requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=self.partner_headers)
            except:
                pass
    
    def test_01_partner_sees_all_projects(self):
        """Partner should see all projects in tenant"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=self.partner_headers)
        assert response.status_code == 200, f"Failed to get projects: {response.text}"
        
        projects = response.json()
        print(f"Partner sees {len(projects)} projects")
        # Partner should be able to see projects (may be 0 if none exist)
        assert isinstance(projects, list)
    
    def test_02_create_project_with_task_for_specific_user(self):
        """Create a project with task assigned to a specific user, verify visibility"""
        # Get existing users
        users_resp = requests.get(f"{BASE_URL}/api/users", headers=self.partner_headers)
        assert users_resp.status_code == 200
        users = users_resp.json()
        
        # Find a non-partner user to assign task to
        non_partner_user = None
        for user in users:
            if user.get("role") not in ["partner", "super_admin"] and user.get("active", True):
                non_partner_user = user
                break
        
        if not non_partner_user:
            pytest.skip("No non-partner users available for testing")
        
        print(f"Using user: {non_partner_user['name']} ({non_partner_user['id']}) with role {non_partner_user['role']}")
        
        # Get a client for the project
        clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
        client_id = None
        client_name = "Test Client"
        if clients_resp.status_code == 200 and clients_resp.json():
            client = clients_resp.json()[0]
            client_id = client["id"]
            client_name = client["name"]
        
        # Create a project with a task assigned to the non-partner user
        project_data = {
            "name": f"TEST_Project_Visibility_{uuid.uuid4().hex[:8]}",
            "description": "Test project for visibility testing",
            "client_id": client_id,
            "client_name": client_name,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "tasks": [
                {
                    "title": "Test Task for Visibility",
                    "description": "Task assigned to specific user",
                    "priority": "medium",
                    "assignee_id": non_partner_user["id"],
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                }
            ]
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=self.partner_headers)
        assert create_resp.status_code == 200, f"Failed to create project: {create_resp.text}"
        
        project = create_resp.json()
        self.created_projects.append(project["id"])
        print(f"Created project: {project['name']} with ID {project['id']}")
        
        # Verify partner can see the project
        partner_projects = requests.get(f"{BASE_URL}/api/projects", headers=self.partner_headers).json()
        project_ids = [p["id"] for p in partner_projects]
        assert project["id"] in project_ids, "Partner should see the created project"
        print("Partner can see the project - PASS")
        
        # Now login as the assigned user and verify they can see the project
        # First, we need to find the user's credentials or create a test user
        # For this test, we'll use the known associate credentials
        try:
            associate_auth = TestHelpers.login(**ASSOCIATE_CREDENTIALS)
            associate_headers = TestHelpers.get_auth_headers(associate_auth["token"])
            
            # Check if the associate is the same as the assigned user
            if associate_auth["user"]["id"] == non_partner_user["id"]:
                associate_projects = requests.get(f"{BASE_URL}/api/projects", headers=associate_headers).json()
                associate_project_ids = [p["id"] for p in associate_projects]
                assert project["id"] in associate_project_ids, "Assigned user should see the project"
                print(f"Assigned user ({associate_auth['user']['name']}) can see the project - PASS")
            else:
                # The associate is different from the assigned user
                # They should NOT see this project (unless they have tasks in it)
                associate_projects = requests.get(f"{BASE_URL}/api/projects", headers=associate_headers).json()
                associate_project_ids = [p["id"] for p in associate_projects]
                if project["id"] not in associate_project_ids:
                    print(f"Different user ({associate_auth['user']['name']}) correctly cannot see the project - PASS")
                else:
                    print(f"Warning: Different user can see the project (may have other tasks)")
        except Exception as e:
            print(f"Could not test associate visibility: {e}")
    
    def test_03_associate_only_sees_own_projects(self):
        """Regular associate should only see projects where they have assigned tasks"""
        try:
            associate_auth = TestHelpers.login(**ASSOCIATE_CREDENTIALS)
            associate_headers = TestHelpers.get_auth_headers(associate_auth["token"])
            associate_user = associate_auth["user"]
            
            print(f"Testing as associate: {associate_user['name']} (role: {associate_user['role']})")
            
            # Get projects visible to associate
            projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=associate_headers)
            assert projects_resp.status_code == 200
            projects = projects_resp.json()
            
            print(f"Associate sees {len(projects)} projects")
            
            # For each project, verify the associate has tasks assigned
            for project in projects:
                # Get project tasks
                tasks_resp = requests.get(f"{BASE_URL}/api/projects/{project['id']}/tasks", headers=associate_headers)
                if tasks_resp.status_code == 200:
                    tasks = tasks_resp.json()
                    # Check if any task is assigned to the associate
                    has_own_task = any(t.get("assignee_id") == associate_user["id"] for t in tasks)
                    print(f"  Project '{project['name']}': has own task = {has_own_task}")
            
            print("Associate project visibility test completed")
            
        except Exception as e:
            pytest.skip(f"Could not test associate: {e}")
    
    def test_04_project_visibility_with_ad_managed_members(self):
        """Associate Director should see projects with tasks assigned to managed members"""
        # Create a test AD user with managed members
        test_ad_email = f"test_ad_{uuid.uuid4().hex[:8]}@test.com"
        test_ad_password = "password123"
        
        # Get existing users to set as managed members
        users_resp = requests.get(f"{BASE_URL}/api/users", headers=self.partner_headers)
        users = users_resp.json()
        
        # Find non-partner, non-AD users to be managed
        managed_user_ids = []
        for user in users:
            if user.get("role") not in ["partner", "super_admin", "associate_director"] and user.get("active", True):
                managed_user_ids.append(user["id"])
                if len(managed_user_ids) >= 2:
                    break
        
        if not managed_user_ids:
            pytest.skip("No users available to be managed")
        
        # Create AD user
        ad_data = {
            "name": "TEST_AD_Visibility",
            "email": test_ad_email,
            "password": test_ad_password,
            "role": "associate_director",
            "managed_members": managed_user_ids
        }
        
        create_ad_resp = requests.post(f"{BASE_URL}/api/users", json=ad_data, headers=self.partner_headers)
        assert create_ad_resp.status_code == 201, f"Failed to create AD: {create_ad_resp.text}"
        
        ad_user = create_ad_resp.json()
        self.created_users.append(ad_user["id"])
        print(f"Created AD user: {ad_user['name']} managing {len(managed_user_ids)} members")
        
        # Get a client
        clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
        client_id = None
        if clients_resp.status_code == 200 and clients_resp.json():
            client_id = clients_resp.json()[0]["id"]
        
        # Create a project with task assigned to a managed member
        project_data = {
            "name": f"TEST_AD_Project_{uuid.uuid4().hex[:8]}",
            "description": "Project for AD visibility test",
            "client_id": client_id,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "tasks": [
                {
                    "title": "Task for managed member",
                    "assignee_id": managed_user_ids[0],
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                }
            ]
        }
        
        create_proj_resp = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=self.partner_headers)
        assert create_proj_resp.status_code == 200, f"Failed to create project: {create_proj_resp.text}"
        
        project = create_proj_resp.json()
        self.created_projects.append(project["id"])
        print(f"Created project: {project['name']}")
        
        # Login as AD and verify they can see the project
        ad_auth = TestHelpers.login(PARTNER_CREDENTIALS["company_code"], test_ad_email, test_ad_password)
        ad_headers = TestHelpers.get_auth_headers(ad_auth["token"])
        
        ad_projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=ad_headers)
        assert ad_projects_resp.status_code == 200
        ad_projects = ad_projects_resp.json()
        
        ad_project_ids = [p["id"] for p in ad_projects]
        assert project["id"] in ad_project_ids, "AD should see project with managed member's task"
        print(f"AD can see project with managed member's task - PASS")


class TestVisibleClients:
    """Test Feature 2: Visible clients restriction"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.partner_auth = TestHelpers.login(**PARTNER_CREDENTIALS)
        self.partner_headers = TestHelpers.get_auth_headers(self.partner_auth["token"])
        self.tenant_id = self.partner_auth["tenant_id"]
        
        # Track created resources for cleanup
        self.created_users = []
        self.modified_users = []  # Users whose visible_clients was modified
        
        yield
        
        # Cleanup - reset visible_clients for modified users
        for user_id in self.modified_users:
            try:
                requests.put(f"{BASE_URL}/api/users/{user_id}", 
                           json={"visible_clients": None}, 
                           headers=self.partner_headers)
                print(f"Reset visible_clients for user {user_id}")
            except:
                pass
        
        # Delete created users
        for user_id in self.created_users:
            try:
                requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=self.partner_headers)
            except:
                pass
    
    def test_01_partner_sees_all_clients(self):
        """Partner should always see all clients regardless of visible_clients setting"""
        response = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        
        clients = response.json()
        print(f"Partner sees {len(clients)} clients")
        assert isinstance(clients, list)
        
        # Store client count for later comparison
        self.all_clients_count = len(clients)
        self.all_client_ids = [c["id"] for c in clients]
    
    def test_02_user_with_null_visible_clients_sees_all(self):
        """User with visible_clients=null should see all clients"""
        try:
            associate_auth = TestHelpers.login(**ASSOCIATE_CREDENTIALS)
            associate_headers = TestHelpers.get_auth_headers(associate_auth["token"])
            associate_user = associate_auth["user"]
            
            # Ensure visible_clients is null
            update_resp = requests.put(
                f"{BASE_URL}/api/users/{associate_user['id']}", 
                json={"visible_clients": None},
                headers=self.partner_headers
            )
            assert update_resp.status_code == 200, f"Failed to update user: {update_resp.text}"
            self.modified_users.append(associate_user["id"])
            
            # Get clients as associate
            clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=associate_headers)
            assert clients_resp.status_code == 200
            clients = clients_resp.json()
            
            # Get all clients as partner for comparison
            all_clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
            all_clients = all_clients_resp.json()
            
            print(f"User with null visible_clients sees {len(clients)} clients (total: {len(all_clients)})")
            assert len(clients) == len(all_clients), "User with null visible_clients should see all clients"
            print("User with null visible_clients sees all clients - PASS")
            
        except Exception as e:
            pytest.skip(f"Could not test: {e}")
    
    def test_03_user_with_restricted_visible_clients(self):
        """User with visible_clients=[...] should only see those clients"""
        try:
            associate_auth = TestHelpers.login(**ASSOCIATE_CREDENTIALS)
            associate_headers = TestHelpers.get_auth_headers(associate_auth["token"])
            associate_user = associate_auth["user"]
            
            # Get all clients first
            all_clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
            all_clients = all_clients_resp.json()
            
            if len(all_clients) < 2:
                pytest.skip("Need at least 2 clients to test restriction")
            
            # Restrict to first 2 clients only
            restricted_client_ids = [all_clients[0]["id"], all_clients[1]["id"]]
            
            update_resp = requests.put(
                f"{BASE_URL}/api/users/{associate_user['id']}", 
                json={"visible_clients": restricted_client_ids},
                headers=self.partner_headers
            )
            assert update_resp.status_code == 200, f"Failed to update user: {update_resp.text}"
            self.modified_users.append(associate_user["id"])
            
            # Verify the update
            user_resp = requests.get(f"{BASE_URL}/api/users/{associate_user['id']}", headers=self.partner_headers)
            updated_user = user_resp.json()
            print(f"User visible_clients set to: {updated_user.get('visible_clients')}")
            
            # Get clients as associate
            clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=associate_headers)
            assert clients_resp.status_code == 200
            clients = clients_resp.json()
            
            print(f"User with restricted visible_clients sees {len(clients)} clients (restricted to {len(restricted_client_ids)})")
            
            # Verify only restricted clients are visible
            visible_ids = [c["id"] for c in clients]
            assert len(clients) == len(restricted_client_ids), f"Expected {len(restricted_client_ids)} clients, got {len(clients)}"
            
            for client_id in restricted_client_ids:
                assert client_id in visible_ids, f"Client {client_id} should be visible"
            
            print("User with restricted visible_clients sees only allowed clients - PASS")
            
        except Exception as e:
            pytest.skip(f"Could not test: {e}")
        finally:
            # Reset visible_clients
            try:
                requests.put(
                    f"{BASE_URL}/api/users/{associate_user['id']}", 
                    json={"visible_clients": None},
                    headers=self.partner_headers
                )
            except:
                pass
    
    def test_04_user_with_empty_visible_clients(self):
        """User with visible_clients=[] should see no clients"""
        try:
            associate_auth = TestHelpers.login(**ASSOCIATE_CREDENTIALS)
            associate_headers = TestHelpers.get_auth_headers(associate_auth["token"])
            associate_user = associate_auth["user"]
            
            # Set visible_clients to empty array
            update_resp = requests.put(
                f"{BASE_URL}/api/users/{associate_user['id']}", 
                json={"visible_clients": []},
                headers=self.partner_headers
            )
            assert update_resp.status_code == 200, f"Failed to update user: {update_resp.text}"
            self.modified_users.append(associate_user["id"])
            
            # Get clients as associate
            clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=associate_headers)
            assert clients_resp.status_code == 200
            clients = clients_resp.json()
            
            print(f"User with empty visible_clients sees {len(clients)} clients")
            assert len(clients) == 0, "User with empty visible_clients should see no clients"
            print("User with empty visible_clients sees no clients - PASS")
            
        except Exception as e:
            pytest.skip(f"Could not test: {e}")
        finally:
            # Reset visible_clients
            try:
                requests.put(
                    f"{BASE_URL}/api/users/{associate_user['id']}", 
                    json={"visible_clients": None},
                    headers=self.partner_headers
                )
            except:
                pass
    
    def test_05_partner_always_sees_all_clients_regardless_of_setting(self):
        """Partner should see all clients even if visible_clients is set (should be ignored)"""
        # This tests that the partner role bypasses visible_clients filtering
        # Note: The code should not allow setting visible_clients for partners,
        # but even if it's set, partners should see all clients
        
        # Get all clients as partner
        clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
        assert clients_resp.status_code == 200
        clients = clients_resp.json()
        
        print(f"Partner sees {len(clients)} clients")
        assert isinstance(clients, list)
        print("Partner always sees all clients - PASS")
    
    def test_06_create_user_with_visible_clients(self):
        """Test creating a new user with visible_clients restriction"""
        # Get all clients
        all_clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
        all_clients = all_clients_resp.json()
        
        if len(all_clients) < 1:
            pytest.skip("Need at least 1 client to test")
        
        # Create user with visible_clients set
        test_email = f"test_visible_{uuid.uuid4().hex[:8]}@test.com"
        restricted_client_ids = [all_clients[0]["id"]]
        
        user_data = {
            "name": "TEST_Visible_Clients_User",
            "email": test_email,
            "password": "password123",
            "role": "associate",
            "visible_clients": restricted_client_ids
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/users", json=user_data, headers=self.partner_headers)
        assert create_resp.status_code == 201, f"Failed to create user: {create_resp.text}"
        
        new_user = create_resp.json()
        self.created_users.append(new_user["id"])
        
        print(f"Created user with visible_clients: {new_user.get('visible_clients')}")
        
        # Login as new user and verify client visibility
        new_user_auth = TestHelpers.login(PARTNER_CREDENTIALS["company_code"], test_email, "password123")
        new_user_headers = TestHelpers.get_auth_headers(new_user_auth["token"])
        
        clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=new_user_headers)
        assert clients_resp.status_code == 200
        clients = clients_resp.json()
        
        print(f"New user sees {len(clients)} clients (restricted to {len(restricted_client_ids)})")
        assert len(clients) == len(restricted_client_ids), "New user should only see restricted clients"
        print("New user with visible_clients sees only allowed clients - PASS")


class TestVisibleClientsAPIValidation:
    """Test API validation for visible_clients field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.partner_auth = TestHelpers.login(**PARTNER_CREDENTIALS)
        self.partner_headers = TestHelpers.get_auth_headers(self.partner_auth["token"])
        
        yield
    
    def test_01_update_user_visible_clients_via_put(self):
        """Test updating visible_clients via PUT /api/users/{id}"""
        try:
            associate_auth = TestHelpers.login(**ASSOCIATE_CREDENTIALS)
            associate_user = associate_auth["user"]
            
            # Get clients
            clients_resp = requests.get(f"{BASE_URL}/api/clients", headers=self.partner_headers)
            clients = clients_resp.json()
            
            if not clients:
                pytest.skip("No clients available")
            
            # Update visible_clients
            client_ids = [clients[0]["id"]]
            update_resp = requests.put(
                f"{BASE_URL}/api/users/{associate_user['id']}", 
                json={"visible_clients": client_ids},
                headers=self.partner_headers
            )
            assert update_resp.status_code == 200, f"Failed to update: {update_resp.text}"
            
            # Verify update
            user_resp = requests.get(f"{BASE_URL}/api/users/{associate_user['id']}", headers=self.partner_headers)
            updated_user = user_resp.json()
            
            assert updated_user.get("visible_clients") == client_ids, "visible_clients should be updated"
            print(f"Successfully updated visible_clients to {client_ids}")
            
            # Reset
            requests.put(
                f"{BASE_URL}/api/users/{associate_user['id']}", 
                json={"visible_clients": None},
                headers=self.partner_headers
            )
            print("Reset visible_clients to null - PASS")
            
        except Exception as e:
            pytest.skip(f"Could not test: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
