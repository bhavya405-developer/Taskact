import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import NotificationPanel from './NotificationPanel';
import axios from 'axios';
import { 
  BarChart3, 
  CheckSquare, 
  Users, 
  FolderOpen, 
  Building2, 
  Plus,
  LogOut,
  User,
  Menu,
  X,
  Clock,
  Key,
  Eye,
  EyeOff
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Navigation = () => {
  const location = useLocation();
  const { user, logout, isPartner } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  
  const navItems = [
    { path: '/dashboard', name: 'Dashboard', icon: BarChart3 },
    { path: '/tasks', name: 'Tasks', icon: CheckSquare },
    { path: '/attendance', name: 'Attendance', icon: Clock },
    { path: '/team', name: 'Team', icon: Users, partnerOnly: true },
    { path: '/categories', name: 'Categories', icon: FolderOpen, partnerOnly: true },
    { path: '/clients', name: 'Clients', icon: Building2, partnerOnly: true },
    { path: '/create-task', name: 'Create Task', icon: Plus }
  ];

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }

    if (passwordData.newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters');
      return;
    }

    setPasswordLoading(true);
    try {
      await axios.put(`${API_URL}/api/auth/change-password`, {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      });
      setPasswordSuccess('Password changed successfully!');
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setTimeout(() => {
        setShowChangePassword(false);
        setPasswordSuccess('');
      }, 2000);
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <img 
                src="/taskact-logo.svg" 
                alt="TaskAct" 
                className="h-10 w-auto"
                style={{ maxWidth: '160px' }}
              />
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-4">
            <div className="flex items-baseline space-x-4">
              {navItems.map((item) => {
                if (item.partnerOnly && !isPartner()) {
                  return null;
                }
                
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`nav-link flex items-center ${
                      location.pathname === item.path ? 'active' : ''
                    }`}
                    data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
                  >
                    <item.icon size={16} className="mr-2" />
                    {item.name}
                  </Link>
                );
              })}
            </div>
            
            <div className="flex items-center space-x-4 ml-6 border-l border-gray-200 pl-6">
              <NotificationPanel />
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-medium text-sm">
                    {user?.name?.charAt(0)?.toUpperCase()}
                  </span>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-700">{user?.name}</div>
                  <div className="text-xs text-gray-500 capitalize">{user?.role}</div>
                </div>
              </div>
              <button
                onClick={() => setShowChangePassword(true)}
                className="text-sm text-gray-600 hover:text-gray-900 px-2 py-2 rounded-md flex items-center"
                title="Change Password"
                data-testid="change-password-button"
              >
                <Key size={16} />
              </button>
              <button
                onClick={logout}
                className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md flex items-center"
                data-testid="logout-button"
              >
                <LogOut size={16} className="mr-1" />
                <span className="hidden lg:inline">Logout</span>
              </button>
            </div>
          </div>

          {/* Mobile menu button and user info */}
          <div className="md:hidden flex items-center space-x-2">
            <NotificationPanel />
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600 font-medium text-sm">
                {user?.name?.charAt(0)?.toUpperCase()}
              </span>
            </div>
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              data-testid="mobile-menu-button"
            >
              {isMobileMenuOpen ? (
                <X size={24} />
              ) : (
                <Menu size={24} />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 border-t border-gray-200 bg-gray-50">
              {navItems.map((item) => {
                if (item.partnerOnly && !isPartner()) {
                  return null;
                }
                
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center px-3 py-3 rounded-md text-base font-medium transition-colors ${
                      location.pathname === item.path 
                        ? 'bg-blue-100 text-blue-700 border-l-4 border-blue-500' 
                        : 'text-gray-700 hover:bg-white hover:text-gray-900'
                    }`}
                    data-testid={`mobile-nav-${item.name.toLowerCase().replace(' ', '-')}`}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <item.icon size={20} className="mr-3" />
                    {item.name}
                  </Link>
                );
              })}
              
              {/* Mobile User Info and Logout */}
              <div className="border-t border-gray-200 pt-3 mt-3">
                <div className="px-3 py-2">
                  <div className="text-base font-medium text-gray-800">{user?.name}</div>
                  <div className="text-sm text-gray-500 capitalize">{user?.role}</div>
                </div>
                <button
                  onClick={() => {
                    logout();
                    setIsMobileMenuOpen(false);
                  }}
                  className="flex items-center w-full px-3 py-3 rounded-md text-base font-medium text-gray-700 hover:bg-white hover:text-gray-900 transition-colors"
                  data-testid="mobile-logout-button"
                >
                  <LogOut size={20} className="mr-3" />
                  Logout
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navigation;