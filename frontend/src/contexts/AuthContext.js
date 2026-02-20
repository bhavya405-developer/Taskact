import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [isSuperAdminUser, setIsSuperAdminUser] = useState(false);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      // Set default Authorization header for all requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      // Verify token and get user info
      const verifyToken = async () => {
        try {
          const response = await axios.get(`${API}/auth/me`);
          setUser(response.data);
          // Store tenant info if available
          if (response.data.tenant) {
            setTenant(response.data.tenant);
            localStorage.setItem('tenant', JSON.stringify(response.data.tenant));
          }
          // Check for super admin
          if (response.data.is_super_admin) {
            setIsSuperAdminUser(true);
            localStorage.setItem('is_super_admin', 'true');
          }
        } catch (error) {
          console.error('Token verification failed:', error);
          logout();
        } finally {
          setLoading(false);
        }
      };
      
      verifyToken();
    } else {
      setLoading(false);
    }
  }, [token]);

  // Load tenant and admin status from localStorage on mount
  useEffect(() => {
    const savedTenant = localStorage.getItem('tenant');
    if (savedTenant) {
      try {
        setTenant(JSON.parse(savedTenant));
      } catch (e) {
        localStorage.removeItem('tenant');
      }
    }
    
    const savedSuperAdmin = localStorage.getItem('is_super_admin');
    if (savedSuperAdmin === 'true') {
      setIsSuperAdminUser(true);
    }
  }, []);

  const login = async (companyCode, email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, {
        company_code: companyCode,
        email,
        password
      });
      
      const { access_token, user: userData, tenant: tenantData, is_super_admin } = response.data;
      
      // Store token
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      
      // Store tenant info
      if (tenantData) {
        setTenant(tenantData);
        localStorage.setItem('tenant', JSON.stringify(tenantData));
      }
      
      // Store super admin status
      if (is_super_admin) {
        setIsSuperAdminUser(true);
        localStorage.setItem('is_super_admin', 'true');
      }
      
      // Set default Authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true, is_super_admin };
    } catch (error) {
      console.error('Login failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('tenant');
    localStorage.removeItem('is_super_admin');
    localStorage.removeItem('impersonation');
    setToken(null);
    setUser(null);
    setTenant(null);
    setIsSuperAdminUser(false);
    delete axios.defaults.headers.common['Authorization'];
  };

  const isPartner = () => {
    return user?.role === 'partner' || isSuperAdminUser;
  };

  const isSuperAdmin = () => {
    return isSuperAdminUser;
  };

  // Impersonate a user (for super admin)
  const impersonateUser = (impersonationData) => {
    const { access_token, user: userData, tenant: tenantData, original_admin } = impersonationData;
    
    // Store original admin info for returning later
    localStorage.setItem('impersonation', JSON.stringify({
      original_token: token,
      original_user: user,
      original_tenant: tenant,
      original_admin
    }));
    
    // Set new token and user
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
    setTenant(tenantData);
    localStorage.setItem('tenant', JSON.stringify(tenantData));
    setIsSuperAdminUser(false);
    localStorage.removeItem('is_super_admin');
    
    // Set default Authorization header
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    
    // Reload the page to ensure clean state
    window.location.href = '/dashboard';
  };

  // End impersonation and return to admin
  const endImpersonation = () => {
    const impersonationStr = localStorage.getItem('impersonation');
    if (!impersonationStr) return;
    
    const impersonation = JSON.parse(impersonationStr);
    
    // Restore original admin session
    localStorage.setItem('token', impersonation.original_token);
    setToken(impersonation.original_token);
    setUser(impersonation.original_user);
    if (impersonation.original_tenant) {
      setTenant(impersonation.original_tenant);
      localStorage.setItem('tenant', JSON.stringify(impersonation.original_tenant));
    }
    setIsSuperAdminUser(true);
    localStorage.setItem('is_super_admin', 'true');
    localStorage.removeItem('impersonation');
    
    // Set Authorization header
    axios.defaults.headers.common['Authorization'] = `Bearer ${impersonation.original_token}`;
    
    // Reload to admin panel
    window.location.href = '/admin-panel';
  };

  // Check if currently impersonating
  const isImpersonating = () => {
    return !!localStorage.getItem('impersonation');
  };

  const value = {
    user,
    tenant,
    login,
    logout,
    isPartner,
    isSuperAdmin,
    isSuperAdminUser,
    loading,
    impersonateUser,
    endImpersonation,
    isImpersonating
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
