import React, { useState, useRef } from 'react';
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
  EyeOff,
  Timer,
  ChevronDown,
  Database,
  Building,
  FolderKanban
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Navigation = () => {
  const location = useLocation();
  const { user, tenant, logout, isPartner } = useAuth();
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
    { path: '/projects', name: 'Projects', icon: FolderKanban },
    { path: '/timesheet', name: 'Timesheet', icon: Timer },
    { path: '/attendance', name: 'Attendance', icon: Clock },
    { path: '/create-task', name: 'Create Task', icon: Plus }
  ];

  // Masters dropdown items (Partner only)
  const mastersItems = [
    { path: '/team', name: 'Team', icon: Users },
    { path: '/categories', name: 'Categories', icon: FolderOpen },
    { path: '/clients', name: 'Clients', icon: Building2 }
  ];

  const [showMastersDropdown, setShowMastersDropdown] = useState(false);
  const mastersTimeoutRef = useRef(null);

  const handleMastersMouseEnter = () => {
    if (mastersTimeoutRef.current) {
      clearTimeout(mastersTimeoutRef.current);
      mastersTimeoutRef.current = null;
    }
    setShowMastersDropdown(true);
  };

  const handleMastersMouseLeave = () => {
    mastersTimeoutRef.current = setTimeout(() => {
      setShowMastersDropdown(false);
    }, 2000); // 2 second delay
  };

  const handleMastersItemClick = () => {
    if (mastersTimeoutRef.current) {
      clearTimeout(mastersTimeoutRef.current);
      mastersTimeoutRef.current = null;
    }
    setShowMastersDropdown(false);
  };

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
            {/* Tenant Badge */}
            {tenant && (
              <div className="ml-4 hidden sm:flex items-center px-3 py-1 bg-indigo-50 rounded-full border border-indigo-200">
                <Building className="h-3.5 w-3.5 text-indigo-600 mr-1.5" />
                <span className="text-xs font-medium text-indigo-700">{tenant.name}</span>
                <span className="ml-2 text-xs text-indigo-500 font-mono">{tenant.code}</span>
              </div>
            )}
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-4">
            <div className="flex items-baseline space-x-4">
              {navItems.map((item) => {
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
              
              {/* Masters Dropdown (Partner only) */}
              {isPartner() && (
                <div 
                  className="relative"
                  onMouseEnter={handleMastersMouseEnter}
                  onMouseLeave={handleMastersMouseLeave}
                >
                  <button
                    className={`nav-link flex items-center ${
                      mastersItems.some(item => location.pathname === item.path) ? 'active' : ''
                    }`}
                    data-testid="nav-masters"
                  >
                    <Database size={16} className="mr-2" />
                    Masters
                    <ChevronDown size={14} className="ml-1" />
                  </button>
                  
                  {showMastersDropdown && (
                    <div className="absolute left-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                      {mastersItems.map((item) => (
                        <Link
                          key={item.path}
                          to={item.path}
                          className={`flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 ${
                            location.pathname === item.path ? 'bg-blue-50 text-blue-600' : ''
                          }`}
                          data-testid={`nav-${item.name.toLowerCase()}`}
                          onClick={handleMastersItemClick}
                        >
                          <item.icon size={16} className="mr-3" />
                          {item.name}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              )}
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
              
              {/* Masters Section (Partner only) */}
              {isPartner() && (
                <>
                  <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-t border-gray-200 mt-2 pt-3">
                    Masters
                  </div>
                  {mastersItems.map((item) => (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center px-3 py-3 rounded-md text-base font-medium transition-colors ${
                        location.pathname === item.path 
                          ? 'bg-blue-100 text-blue-700 border-l-4 border-blue-500' 
                          : 'text-gray-700 hover:bg-white hover:text-gray-900'
                      }`}
                      data-testid={`mobile-nav-${item.name.toLowerCase()}`}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <item.icon size={20} className="mr-3" />
                      {item.name}
                    </Link>
                  ))}
                </>
              )}
              
              {/* Mobile User Info and Logout */}
              <div className="border-t border-gray-200 pt-3 mt-3">
                <div className="px-3 py-2">
                  <div className="text-base font-medium text-gray-800">{user?.name}</div>
                </div>
                <button
                  onClick={() => {
                    setShowChangePassword(true);
                    setIsMobileMenuOpen(false);
                  }}
                  className="flex items-center w-full px-3 py-3 rounded-md text-base font-medium text-gray-700 hover:bg-white hover:text-gray-900 transition-colors"
                  data-testid="mobile-change-password-button"
                >
                  <Key size={20} className="mr-3" />
                  Change Password
                </button>
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

      {/* Change Password Modal */}
      {showChangePassword && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Key className="w-5 h-5 mr-2" />
                Change Password
              </h3>
              <button
                onClick={() => {
                  setShowChangePassword(false);
                  setPasswordError('');
                  setPasswordSuccess('');
                  setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            </div>

            {passwordError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {passwordError}
              </div>
            )}

            {passwordSuccess && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
                {passwordSuccess}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="form-label">Current Password</label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={passwordData.currentPassword}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                    className="form-input pr-10"
                    required
                    data-testid="current-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="form-label">New Password</label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                    className="form-input pr-10"
                    required
                    minLength={6}
                    data-testid="new-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="form-label">Confirm New Password</label>
                <input
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  className="form-input"
                  required
                  minLength={6}
                  data-testid="confirm-password-input"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="btn-primary flex-1"
                  data-testid="submit-change-password"
                >
                  {passwordLoading ? 'Changing...' : 'Change Password'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowChangePassword(false);
                    setPasswordError('');
                    setPasswordSuccess('');
                    setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navigation;