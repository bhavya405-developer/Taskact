import React, { useState, useEffect } from 'react';
import axios from 'axios';
import SuperAdminLogin from './SuperAdminLogin';
import SuperAdminDashboard from './SuperAdminDashboard';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const SuperAdminApp = () => {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [impersonationData, setImpersonationData] = useState(null);

  useEffect(() => {
    // Check for existing super admin session
    const token = localStorage.getItem('superAdminToken');
    const savedAdmin = localStorage.getItem('superAdmin');
    
    if (token && savedAdmin) {
      try {
        const adminData = JSON.parse(savedAdmin);
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        // Verify token is still valid
        axios.get(`${API_URL}/api/super-admin/me`)
          .then(response => {
            setAdmin(response.data);
          })
          .catch(() => {
            handleLogout();
          })
          .finally(() => {
            setLoading(false);
          });
      } catch (e) {
        handleLogout();
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (adminData, token) => {
    setAdmin(adminData);
  };

  const handleLogout = () => {
    localStorage.removeItem('superAdminToken');
    localStorage.removeItem('superAdmin');
    delete axios.defaults.headers.common['Authorization'];
    setAdmin(null);
  };

  const handleImpersonate = (data) => {
    // Store the impersonation data
    setImpersonationData(data);
    
    // Store in localStorage for the main app to pick up
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('tenant', JSON.stringify({
      id: data.user.tenant_id,
      name: data.user.tenant_name,
      code: data.user.tenant_code
    }));
    localStorage.setItem('impersonation', JSON.stringify({
      impersonated_by: data.impersonated_by,
      original_admin: admin
    }));
    
    // Redirect to main app
    window.location.href = '/';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto"></div>
          <p className="mt-4 text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (!admin) {
    return <SuperAdminLogin onLogin={handleLogin} />;
  }

  return (
    <SuperAdminDashboard 
      admin={admin} 
      onLogout={handleLogout}
      onImpersonate={handleImpersonate}
    />
  );
};

export default SuperAdminApp;
