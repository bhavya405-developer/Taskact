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
  FolderKanban,
  Settings,
  Shield
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Navigation = () => {
  const location = useLocation();
  const { user, tenant, logout, isPartner, isSuperAdmin } = useAuth();
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
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  
  // Check if user is super admin (logged in with TASKACT1)
  const isAdminTenant = tenant?.code === 'TASKACT1';
  
  // Regular nav items (not for super admin)
  const navItems = [
    { path: '/dashboard', name: 'Dashboard', icon: BarChart3 },
    { path: '/tasks', name: 'Tasks', icon: CheckSquare },
    { path: '/projects', name: 'Projects', icon: FolderKanban },
    { path: '/timesheet', name: 'Timesheet', icon: Timer },
    { path: '/attendance', name: 'Attendance', icon: Clock }
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

  // Check if super admin for dark theme
  const isDarkTheme = isSuperAdmin();
  
  return (
    <nav className={`${isDarkTheme ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'} shadow-sm border-b`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <img 
                src="/taskact-logo.svg" 
                alt="TaskAct" 
                className="h-10 w-auto"
                style={{ maxWidth: '160px', filter: isDarkTheme ? 'brightness(0) invert(1)' : 'none' }}
              />
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center">
            <div className="flex items-baseline space-x-1 lg:space-x-2">
              {navItems.map((item) => {
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center whitespace-nowrap px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isDarkTheme 
                        ? location.pathname === item.path 
                          ? 'bg-slate-700 text-white' 
                          : 'text-slate-300 hover:text-white hover:bg-slate-700'
                        : location.pathname === item.path 
                          ? 'text-blue-600 bg-blue-50' 
                          : 'text-gray-600 hover:text-blue-600'
                    }`}
                    data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
                  >
                    <item.icon size={16} className="mr-1.5" />
                    <span className="hidden lg:inline">{item.name}</span>
                    <span className="lg:hidden">{item.name.split(' ')[0]}</span>
                  </Link>
                );
              })}
              
              {/* Masters Dropdown (Partner only, not for super admin) */}
              {isPartner() && !isSuperAdmin() && (
                <div 
                  className="relative"
                  onMouseEnter={handleMastersMouseEnter}
                  onMouseLeave={handleMastersMouseLeave}
                >
                  <button
                    className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isDarkTheme 
                        ? mastersItems.some(item => location.pathname === item.path) 
                          ? 'bg-slate-700 text-white' 
                          : 'text-slate-300 hover:text-white hover:bg-slate-700'
                        : mastersItems.some(item => location.pathname === item.path) 
                          ? 'text-blue-600 bg-blue-50' 
                          : 'text-gray-600 hover:text-blue-600'
                    }`}
                    data-testid="nav-masters"
                  >
                    <Database size={16} className="mr-2" />
                    Masters
                    <ChevronDown size={14} className="ml-1" />
                  </button>
                  
                  {showMastersDropdown && (
                    <div className={`absolute left-0 mt-1 w-48 rounded-lg shadow-lg py-1 z-50 ${
                      isDarkTheme ? 'bg-slate-700 border border-slate-600' : 'bg-white border border-gray-200'
                    }`}>
                      {mastersItems.map((item) => (
                        <Link
                          key={item.path}
                          to={item.path}
                          className={`flex items-center px-4 py-2 text-sm ${
                            isDarkTheme
                              ? location.pathname === item.path 
                                ? 'bg-slate-600 text-white' 
                                : 'text-slate-300 hover:bg-slate-600 hover:text-white'
                              : location.pathname === item.path 
                                ? 'bg-blue-50 text-blue-600' 
                                : 'text-gray-700 hover:bg-gray-100'
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
            
            {/* Right side - Notifications and Profile */}
            <div className={`flex items-center space-x-2 ml-4 border-l pl-4 ${isDarkTheme ? 'border-slate-600' : 'border-gray-200'}`}>
              <NotificationPanel />
              
              {/* Profile Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button 
                    className={`flex items-center space-x-2 rounded-lg px-2 py-1.5 transition-colors ${
                      isDarkTheme ? 'hover:bg-slate-700' : 'hover:bg-gray-100'
                    }`}
                    data-testid="profile-dropdown-trigger"
                  >
                    <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-full flex items-center justify-center shadow-sm">
                      <span className="text-white font-medium text-sm">
                        {user?.name?.charAt(0)?.toUpperCase()}
                      </span>
                    </div>
                    <div className="hidden lg:block text-left">
                      <div className={`text-sm font-medium max-w-[120px] truncate ${isDarkTheme ? 'text-white' : 'text-gray-700'}`}>{user?.name}</div>
                      <div className="text-xs text-gray-500 capitalize">{user?.role?.replace('_', ' ')}</div>
                    </div>
                    <ChevronDown className="h-4 w-4 text-gray-400 hidden lg:block" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="px-3 py-2 border-b border-gray-100">
                    <div className="text-sm font-medium text-gray-900">{user?.name}</div>
                    <div className="text-xs text-gray-500">{user?.email}</div>
                    {tenant && tenant.code !== 'TASKACT1' && (
                      <div className="text-xs text-indigo-600 mt-1">{tenant.name}</div>
                    )}
                  </div>
                  
                  <DropdownMenuItem 
                    onClick={() => setShowChangePassword(true)}
                    className="cursor-pointer"
                  >
                    <Key className="h-4 w-4 mr-2" />
                    Change Password
                  </DropdownMenuItem>
                  
                  {isSuperAdmin() && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem asChild>
                        <Link to="/admin-panel" className="flex items-center cursor-pointer">
                          <Shield className="h-4 w-4 mr-2" />
                          Admin Panel
                        </Link>
                      </DropdownMenuItem>
                    </>
                  )}
                  
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={logout}
                    className="cursor-pointer text-red-600 focus:text-red-600"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
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