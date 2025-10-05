import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import NotificationPanel from './NotificationPanel';
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
  X
} from 'lucide-react';

const Navigation = () => {
  const location = useLocation();
  const { user, logout, isPartner } = useAuth();
  
  const navItems = [
    { path: '/dashboard', name: 'Dashboard', icon: BarChart3 },
    { path: '/tasks', name: 'Tasks', icon: CheckSquare },
    { path: '/team', name: 'Team', icon: Users, partnerOnly: true },
    { path: '/categories', name: 'Categories', icon: FolderOpen, partnerOnly: true },
    { path: '/clients', name: 'Clients', icon: Building2, partnerOnly: true },
    { path: '/create-task', name: 'Create Task', icon: Plus }
  ];

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
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
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-4">
              {navItems.map((item) => {
                // Hide partner-only items for non-partners
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
          </div>
          <div className="flex items-center space-x-4">
            <NotificationPanel />
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-600 font-medium text-sm">
                  {user?.name?.charAt(0)?.toUpperCase()}
                </span>
              </div>
              <div className="hidden md:block">
                <div className="text-sm font-medium text-gray-700">{user?.name}</div>
                <div className="text-xs text-gray-500 capitalize">{user?.role}</div>
              </div>
            </div>
            <button
              onClick={logout}
              className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md flex items-center"
              data-testid="logout-button"
            >
              <LogOut size={16} className="mr-1" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;