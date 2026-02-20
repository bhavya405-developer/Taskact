"""
Test tenant management features:
1. Deactivate tenant endpoint
2. Reactivate tenant endpoint
3. Permanent delete tenant endpoint
4. TASKACT1 protection (cannot delete)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN = {
    "company_code": "TASKACT1",
    "email": "admin@taskact.com",
    "password": "admin123"
}

TENANT_USER = {
    "company_code": "SCO1",
    "email": "bhavika@sundesha.in",
    "password": "password123"
}


class TestTenantManagement:
    """Test tenant deactivate, reactivate, and delete functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get super admin token"""
        # Login as super admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN)
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
    
    def test_01_list_tenants(self):
        """Verify can list all tenants"""
        response = requests.get(f"{BASE_URL}/api/tenants", headers=self.headers)
        assert response.status_code == 200, f"List tenants failed: {response.text}"
        tenants = response.json()
        assert isinstance(tenants, list)
        assert len(tenants) > 0, "Should have at least one tenant"
        
        # Find TASKACT1 tenant
        taskact_tenant = next((t for t in tenants if t["code"] == "TASKACT1"), None)
        assert taskact_tenant is not None, "TASKACT1 tenant should exist"
        print(f"Found {len(tenants)} tenants including TASKACT1")
    
    def test_02_create_test_tenant_for_deactivation(self):
        """Create a test tenant to deactivate"""
        test_code = f"TST{str(uuid.uuid4())[:4].upper()}"
        payload = {
            "name": f"Test Tenant for Deactivation {test_code}",
            "code": test_code,
            "contact_email": f"test_{test_code.lower()}@test.com",
            "plan": "free",
            "max_users": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/tenants", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Create tenant failed: {response.text}"
        
        tenant = response.json()
        assert tenant["code"] == test_code
        assert tenant["active"] == True
        
        # Store for other tests
        TestTenantManagement.test_tenant_id = tenant["id"]
        TestTenantManagement.test_tenant_code = tenant["code"]
        print(f"Created test tenant: {tenant['name']} (ID: {tenant['id']})")
    
    def test_03_deactivate_tenant(self):
        """Test deactivating a tenant"""
        tenant_id = getattr(TestTenantManagement, 'test_tenant_id', None)
        if not tenant_id:
            pytest.skip("No test tenant to deactivate")
        
        response = requests.delete(f"{BASE_URL}/api/tenants/{tenant_id}", headers=self.headers)
        assert response.status_code == 200, f"Deactivate tenant failed: {response.text}"
        
        result = response.json()
        assert "deactivated" in result["message"].lower()
        print(f"Deactivation response: {result['message']}")
        
        # Verify tenant is now inactive
        get_response = requests.get(f"{BASE_URL}/api/tenants/{tenant_id}", headers=self.headers)
        assert get_response.status_code == 200
        tenant = get_response.json()
        assert tenant["active"] == False, "Tenant should be inactive"
        print(f"Verified tenant is now inactive: active={tenant['active']}")
    
    def test_04_reactivate_tenant(self):
        """Test reactivating a tenant"""
        tenant_id = getattr(TestTenantManagement, 'test_tenant_id', None)
        if not tenant_id:
            pytest.skip("No test tenant to reactivate")
        
        response = requests.put(f"{BASE_URL}/api/tenants/{tenant_id}/reactivate", headers=self.headers)
        assert response.status_code == 200, f"Reactivate tenant failed: {response.text}"
        
        result = response.json()
        assert "reactivated" in result["message"].lower()
        print(f"Reactivation response: {result['message']}")
        
        # Verify tenant is now active
        get_response = requests.get(f"{BASE_URL}/api/tenants/{tenant_id}", headers=self.headers)
        assert get_response.status_code == 200
        tenant = get_response.json()
        assert tenant["active"] == True, "Tenant should be active"
        print(f"Verified tenant is now active: active={tenant['active']}")
    
    def test_05_delete_tenant_permanently(self):
        """Test permanently deleting a tenant"""
        tenant_id = getattr(TestTenantManagement, 'test_tenant_id', None)
        if not tenant_id:
            pytest.skip("No test tenant to delete")
        
        response = requests.delete(f"{BASE_URL}/api/tenants/{tenant_id}/permanent", headers=self.headers)
        assert response.status_code == 200, f"Delete tenant failed: {response.text}"
        
        result = response.json()
        assert "deleted" in result["message"].lower()
        assert "deleted" in result
        print(f"Delete response: {result['message']}")
        print(f"Deleted data counts: {result['deleted']}")
        
        # Verify tenant no longer exists
        get_response = requests.get(f"{BASE_URL}/api/tenants/{tenant_id}", headers=self.headers)
        assert get_response.status_code == 404, "Tenant should not exist after permanent deletion"
        print("Verified tenant no longer exists")
    
    def test_06_cannot_delete_taskact1_tenant(self):
        """Test that TASKACT1 tenant cannot be deleted"""
        # Get TASKACT1 tenant
        response = requests.get(f"{BASE_URL}/api/tenants", headers=self.headers)
        assert response.status_code == 200
        tenants = response.json()
        
        taskact_tenant = next((t for t in tenants if t["code"] == "TASKACT1"), None)
        assert taskact_tenant is not None, "TASKACT1 tenant should exist"
        
        # Try to delete it permanently - should fail
        delete_response = requests.delete(
            f"{BASE_URL}/api/tenants/{taskact_tenant['id']}/permanent", 
            headers=self.headers
        )
        assert delete_response.status_code == 403, f"Should not be able to delete TASKACT1: {delete_response.text}"
        print(f"Correctly prevented deletion of TASKACT1: {delete_response.json()}")
    
    def test_07_cannot_reactivate_already_active_tenant(self):
        """Test that reactivating an already active tenant returns error"""
        # Get any active tenant
        response = requests.get(f"{BASE_URL}/api/tenants", headers=self.headers)
        assert response.status_code == 200
        tenants = response.json()
        
        active_tenant = next((t for t in tenants if t["active"]), None)
        assert active_tenant is not None, "Should have at least one active tenant"
        
        # Try to reactivate - should fail
        reactivate_response = requests.put(
            f"{BASE_URL}/api/tenants/{active_tenant['id']}/reactivate", 
            headers=self.headers
        )
        assert reactivate_response.status_code == 400, f"Should not reactivate active tenant: {reactivate_response.text}"
        print(f"Correctly prevented reactivation of active tenant: {reactivate_response.json()}")


class TestTenantUserAccess:
    """Test that regular tenant users cannot access admin endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get tenant user token"""
        # Login as regular tenant user
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TENANT_USER)
        if response.status_code != 200:
            pytest.skip(f"Tenant user login failed: {response.text}")
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
    
    def test_tenant_user_cannot_list_tenants(self):
        """Regular user should not access tenant list"""
        response = requests.get(f"{BASE_URL}/api/tenants", headers=self.headers)
        assert response.status_code in [401, 403], f"Should deny access: {response.status_code}"
        print(f"Correctly denied tenant list access to regular user: {response.status_code}")
    
    def test_tenant_user_cannot_deactivate_tenant(self):
        """Regular user should not deactivate tenants"""
        # Try to deactivate a tenant
        response = requests.delete(f"{BASE_URL}/api/tenants/fake-tenant-id", headers=self.headers)
        assert response.status_code in [401, 403], f"Should deny access: {response.status_code}"
        print(f"Correctly denied deactivate access to regular user: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
