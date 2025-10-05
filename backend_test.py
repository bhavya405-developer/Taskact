#!/usr/bin/env python3
"""
Backend API Testing Script for Task Management Application
Tests Excel template download endpoints with authentication
"""

import requests
import json
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv('frontend/.env')
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_authentication(self):
        """Test authentication with partner credentials"""
        print("\n=== Testing Authentication ===")
        
        # Test partner login
        login_data = {
            "email": "sarah@firm.com",
            "password": "password123"  # Common default password
        }
        
        try:
            response = self.session.post(f"{API_BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('access_token')
                user_info = data.get('user', {})
                
                if self.auth_token and user_info.get('role') == 'partner':
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.auth_token}'
                    })
                    self.log_test(
                        "Partner Authentication", 
                        True, 
                        f"Successfully authenticated as {user_info.get('name')} (partner)",
                        {'token_length': len(self.auth_token), 'user_role': user_info.get('role')}
                    )
                    return True
                else:
                    self.log_test(
                        "Partner Authentication", 
                        False, 
                        "Login successful but missing token or wrong role",
                        {'response': data}
                    )
            else:
                self.log_test(
                    "Partner Authentication", 
                    False, 
                    f"Login failed with status {response.status_code}",
                    {'response_text': response.text}
                )
        except Exception as e:
            self.log_test(
                "Partner Authentication", 
                False, 
                f"Authentication request failed: {str(e)}"
            )
        
        return False
    
    def test_categories_template_download(self):
        """Test categories template download endpoint"""
        print("\n=== Testing Categories Template Download ===")
        
        # Test without authentication first
        session_no_auth = requests.Session()
        try:
            response = session_no_auth.get(f"{API_BASE_URL}/categories/download-template")
            if response.status_code in [401, 403]:
                self.log_test(
                    "Categories Template (No Auth)", 
                    True, 
                    f"Correctly rejected unauthenticated request with {response.status_code}"
                )
            else:
                self.log_test(
                    "Categories Template (No Auth)", 
                    False, 
                    f"Should reject unauthenticated request but got {response.status_code}",
                    {'response_text': response.text[:200]}
                )
        except Exception as e:
            self.log_test(
                "Categories Template (No Auth)", 
                False, 
                f"Request failed: {str(e)}"
            )
        
        # Test with authentication
        if not self.auth_token:
            self.log_test(
                "Categories Template (With Auth)", 
                False, 
                "Cannot test - no authentication token available"
            )
            return False
        
        try:
            response = self.session.get(f"{API_BASE_URL}/categories/download-template")
            
            if response.status_code == 200:
                # Check if it's an Excel file
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                is_excel = (
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type or
                    'categories_template.xlsx' in content_disposition
                )
                
                if is_excel and len(response.content) > 0:
                    self.log_test(
                        "Categories Template (With Auth)", 
                        True, 
                        f"Successfully downloaded Excel template ({len(response.content)} bytes)",
                        {
                            'content_type': content_type,
                            'content_disposition': content_disposition,
                            'file_size': len(response.content)
                        }
                    )
                    return True
                else:
                    self.log_test(
                        "Categories Template (With Auth)", 
                        False, 
                        "Response received but not a valid Excel file",
                        {
                            'content_type': content_type,
                            'content_disposition': content_disposition,
                            'response_size': len(response.content),
                            'response_preview': response.text[:200] if response.text else 'Binary content'
                        }
                    )
            else:
                self.log_test(
                    "Categories Template (With Auth)", 
                    False, 
                    f"Request failed with status {response.status_code}",
                    {'response_text': response.text[:200]}
                )
        except Exception as e:
            self.log_test(
                "Categories Template (With Auth)", 
                False, 
                f"Request failed: {str(e)}"
            )
        
        return False
    
    def test_clients_template_download(self):
        """Test clients template download endpoint"""
        print("\n=== Testing Clients Template Download ===")
        
        # Test without authentication first
        session_no_auth = requests.Session()
        try:
            response = session_no_auth.get(f"{API_BASE_URL}/clients/download-template")
            if response.status_code in [401, 403]:
                self.log_test(
                    "Clients Template (No Auth)", 
                    True, 
                    f"Correctly rejected unauthenticated request with {response.status_code}"
                )
            else:
                self.log_test(
                    "Clients Template (No Auth)", 
                    False, 
                    f"Should reject unauthenticated request but got {response.status_code}",
                    {'response_text': response.text[:200]}
                )
        except Exception as e:
            self.log_test(
                "Clients Template (No Auth)", 
                False, 
                f"Request failed: {str(e)}"
            )
        
        # Test with authentication
        if not self.auth_token:
            self.log_test(
                "Clients Template (With Auth)", 
                False, 
                "Cannot test - no authentication token available"
            )
            return False
        
        try:
            response = self.session.get(f"{API_BASE_URL}/clients/download-template")
            
            if response.status_code == 200:
                # Check if it's an Excel file
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                is_excel = (
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type or
                    'clients_template.xlsx' in content_disposition
                )
                
                if is_excel and len(response.content) > 0:
                    self.log_test(
                        "Clients Template (With Auth)", 
                        True, 
                        f"Successfully downloaded Excel template ({len(response.content)} bytes)",
                        {
                            'content_type': content_type,
                            'content_disposition': content_disposition,
                            'file_size': len(response.content)
                        }
                    )
                    return True
                else:
                    self.log_test(
                        "Clients Template (With Auth)", 
                        False, 
                        "Response received but not a valid Excel file",
                        {
                            'content_type': content_type,
                            'content_disposition': content_disposition,
                            'response_size': len(response.content),
                            'response_preview': response.text[:200] if response.text else 'Binary content'
                        }
                    )
            else:
                self.log_test(
                    "Clients Template (With Auth)", 
                    False, 
                    f"Request failed with status {response.status_code}",
                    {'response_text': response.text[:200]}
                )
        except Exception as e:
            self.log_test(
                "Clients Template (With Auth)", 
                False, 
                f"Request failed: {str(e)}"
            )
        
        return False
    
    def test_route_registration(self):
        """Test if routes are properly registered"""
        print("\n=== Testing Route Registration ===")
        
        # Test basic API health check
        try:
            response = self.session.get(f"{API_BASE_URL}/")
            if response.status_code == 200:
                self.log_test(
                    "API Root Endpoint", 
                    True, 
                    "API root endpoint accessible",
                    {'response': response.json()}
                )
            else:
                self.log_test(
                    "API Root Endpoint", 
                    False, 
                    f"API root endpoint returned {response.status_code}",
                    {'response_text': response.text}
                )
        except Exception as e:
            self.log_test(
                "API Root Endpoint", 
                False, 
                f"API root endpoint failed: {str(e)}"
            )
        
        # Test if template endpoints exist (should return 401/403 without auth)
        endpoints_to_test = [
            "/categories/download-template",
            "/clients/download-template"
        ]
        
        session_no_auth = requests.Session()
        for endpoint in endpoints_to_test:
            try:
                response = session_no_auth.get(f"{API_BASE_URL}{endpoint}")
                if response.status_code in [401, 403]:
                    self.log_test(
                        f"Route Registration {endpoint}", 
                        True, 
                        f"Route exists and properly protected (status {response.status_code})"
                    )
                elif response.status_code == 404:
                    self.log_test(
                        f"Route Registration {endpoint}", 
                        False, 
                        "Route not found - may not be properly registered"
                    )
                else:
                    self.log_test(
                        f"Route Registration {endpoint}", 
                        True, 
                        f"Route exists (status {response.status_code})"
                    )
            except Exception as e:
                self.log_test(
                    f"Route Registration {endpoint}", 
                    False, 
                    f"Route test failed: {str(e)}"
                )
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"🚀 Starting Backend API Tests")
        print(f"📍 Testing against: {API_BASE_URL}")
        print("=" * 60)
        
        # Test authentication first
        auth_success = self.test_authentication()
        
        # Test route registration
        self.test_route_registration()
        
        # Test template downloads
        categories_success = self.test_categories_template_download()
        clients_success = self.test_clients_template_download()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  • {test['test']}: {test['message']}")
        
        # Show critical issues
        critical_issues = []
        if not auth_success:
            critical_issues.append("Authentication system not working")
        if not categories_success:
            critical_issues.append("Categories template download failing")
        if not clients_success:
            critical_issues.append("Clients template download failing")
        
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in critical_issues:
                print(f"  • {issue}")
        
        return passed == total

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)