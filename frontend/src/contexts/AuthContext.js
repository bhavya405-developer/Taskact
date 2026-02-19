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

  // Load tenant from localStorage on mount
  useEffect(() => {
    const savedTenant = localStorage.getItem('tenant');
    if (savedTenant) {
      try {
        setTenant(JSON.parse(savedTenant));
      } catch (e) {
        localStorage.removeItem('tenant');
      }
    }
  }, []);

  const login = async (companyCode, email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, {
        company_code: companyCode,
        email,
        password
      });
      
      const { access_token, user: userData, tenant: tenantData } = response.data;
      
      // Store token
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      
      // Store tenant info
      if (tenantData) {
        setTenant(tenantData);
        localStorage.setItem('tenant', JSON.stringify(tenantData));
      }
      
      // Set default Authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
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
    setToken(null);
    setUser(null);
    setTenant(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  const isPartner = () => {
    return user?.role === 'partner';
  };

  const isSuperAdmin = () => {
    return user?.role === 'super_admin';
  };

  const value = {
    user,
    tenant,
    login,
    logout,
    isPartner,
    isSuperAdmin,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
