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

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, {
        email,
        password
      });
      
      const { access_token, user: userData } = response.data;
      
      // Store token
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      
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
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  const isPartner = () => {
    return user?.role === 'partner';
  };

  const value = {
    user,
    login,
    logout,
    isPartner,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;