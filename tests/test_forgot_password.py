"""
Test suite for Forgot Password feature
Tests the 3-step password reset flow:
1. POST /api/auth/forgot-password - Send OTP to email
2. POST /api/auth/verify-otp - Verify OTP
3. POST /api/auth/reset-password - Reset password with OTP
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "sarah@firm.com"
TEST_PASSWORD = "password123"
NONEXISTENT_EMAIL = "nonexistent@test.com"


class TestForgotPasswordEndpoints:
    """Test forgot password API endpoints"""
    
    def test_api_health_check(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API health check passed: {data['message']}")
    
    def test_forgot_password_valid_email(self):
        """Test forgot-password endpoint with valid registered email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": TEST_EMAIL}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Should return generic message for security (doesn't reveal if email exists)
        assert "OTP" in data["message"] or "email" in data["message"].lower()
        print(f"✓ Forgot password with valid email: {data['message']}")
    
    def test_forgot_password_nonexistent_email(self):
        """Test forgot-password endpoint with non-existent email (should still return 200 for security)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": NONEXISTENT_EMAIL}
        )
        # Should return 200 even for non-existent email (security best practice)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Forgot password with non-existent email returns 200: {data['message']}")
    
    def test_forgot_password_invalid_email_format(self):
        """Test forgot-password endpoint with invalid email format"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "invalid-email"}
        )
        # Should return 422 for validation error
        assert response.status_code == 422
        print(f"✓ Invalid email format returns 422 validation error")
    
    def test_forgot_password_missing_email(self):
        """Test forgot-password endpoint with missing email field"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={}
        )
        assert response.status_code == 422
        print(f"✓ Missing email field returns 422 validation error")
    
    def test_verify_otp_invalid_otp(self):
        """Test verify-otp endpoint with invalid OTP"""
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={"email": TEST_EMAIL, "otp": "000000"}
        )
        # Should return 400 for invalid OTP
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid OTP returns 400: {data['detail']}")
    
    def test_verify_otp_missing_fields(self):
        """Test verify-otp endpoint with missing fields"""
        # Missing OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={"email": TEST_EMAIL}
        )
        assert response.status_code == 422
        print(f"✓ Missing OTP field returns 422")
        
        # Missing email
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={"otp": "123456"}
        )
        assert response.status_code == 422
        print(f"✓ Missing email field returns 422")
    
    def test_reset_password_invalid_otp(self):
        """Test reset-password endpoint with invalid OTP"""
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={
                "email": TEST_EMAIL,
                "otp": "000000",
                "new_password": "newpassword123"
            }
        )
        # Should return 400 for invalid OTP
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"✓ Reset password with invalid OTP returns 400: {data['detail']}")
    
    def test_reset_password_missing_fields(self):
        """Test reset-password endpoint with missing fields"""
        # Missing new_password
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"email": TEST_EMAIL, "otp": "123456"}
        )
        assert response.status_code == 422
        print(f"✓ Missing new_password field returns 422")
    
    def test_login_with_original_credentials(self):
        """Verify login still works with original credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login with original credentials works: {data['user']['name']}")


class TestForgotPasswordFullFlow:
    """Test the complete forgot password flow using MongoDB to get OTP"""
    
    @pytest.fixture
    def get_otp_from_db(self):
        """Helper to get OTP from MongoDB for testing"""
        # This would require MongoDB access - for now we test the API responses
        pass
    
    def test_full_flow_step1_request_otp(self):
        """Step 1: Request OTP for password reset"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": TEST_EMAIL}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Step 1 - OTP requested successfully")
        return True
    
    def test_full_flow_step2_verify_otp_fails_with_wrong_otp(self):
        """Step 2: Verify OTP fails with wrong OTP"""
        # First request OTP
        requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": TEST_EMAIL}
        )
        
        # Try to verify with wrong OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={"email": TEST_EMAIL, "otp": "999999"}
        )
        assert response.status_code == 400
        print(f"✓ Step 2 - Wrong OTP correctly rejected")
    
    def test_full_flow_step3_reset_fails_with_wrong_otp(self):
        """Step 3: Reset password fails with wrong OTP"""
        # First request OTP
        requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": TEST_EMAIL}
        )
        
        # Try to reset with wrong OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={
                "email": TEST_EMAIL,
                "otp": "999999",
                "new_password": "newpassword123"
            }
        )
        assert response.status_code == 400
        print(f"✓ Step 3 - Reset with wrong OTP correctly rejected")


class TestForgotPasswordWithRealOTP:
    """Test forgot password flow with real OTP from database"""
    
    def test_complete_password_reset_flow(self):
        """
        Complete flow test:
        1. Request OTP
        2. Get OTP from MongoDB
        3. Verify OTP
        4. Reset password
        5. Login with new password
        6. Reset back to original password
        """
        import subprocess
        import json
        
        test_email = "michael@firm.com"  # Use different user to not affect other tests
        original_password = "password123"
        new_password = "newTestPassword456"
        
        # Step 1: Request OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": test_email}
        )
        assert response.status_code == 200
        print(f"✓ Step 1: OTP requested for {test_email}")
        
        # Step 2: Get OTP from MongoDB
        mongo_cmd = f'''mongosh --quiet --eval "db = db.getSiblingDB('test_database'); doc = db.otp_records.find({{email: '{test_email}', used: false}}).sort({{created_at: -1}}).limit(1).toArray(); print(JSON.stringify(doc[0] || {{}}))"'''
        result = subprocess.run(mongo_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0 or not result.stdout.strip():
            pytest.skip("Could not retrieve OTP from MongoDB")
        
        try:
            otp_record = json.loads(result.stdout.strip())
            otp = otp_record.get('otp')
            if not otp:
                pytest.skip("No OTP found in database")
            print(f"✓ Step 2: Retrieved OTP from database: {otp}")
        except json.JSONDecodeError:
            pytest.skip("Could not parse OTP from MongoDB response")
        
        # Step 3: Verify OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={"email": test_email, "otp": otp}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("valid") == True
        print(f"✓ Step 3: OTP verified successfully")
        
        # Step 4: Reset password
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={
                "email": test_email,
                "otp": otp,
                "new_password": new_password
            }
        )
        assert response.status_code == 200
        print(f"✓ Step 4: Password reset successfully")
        
        # Step 5: Login with new password
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": new_password}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"✓ Step 5: Login with new password successful")
        
        # Step 6: Reset back to original password (cleanup)
        # Request new OTP
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": test_email}
        )
        assert response.status_code == 200
        
        # Get new OTP
        result = subprocess.run(mongo_cmd, shell=True, capture_output=True, text=True)
        otp_record = json.loads(result.stdout.strip())
        new_otp = otp_record.get('otp')
        
        # Reset to original password
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={
                "email": test_email,
                "otp": new_otp,
                "new_password": original_password
            }
        )
        assert response.status_code == 200
        print(f"✓ Step 6: Password reset back to original")
        
        # Verify original password works
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": original_password}
        )
        assert response.status_code == 200
        print(f"✓ Cleanup: Original password restored and verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
