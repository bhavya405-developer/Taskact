import React, { useState } from 'react';
import axios from 'axios';
import UserProfileModal from './UserProfileModal';
import { useAuth } from '../contexts/AuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TeamMembers = ({ users, tasks, onUserAdded }) => {
  const { isPartner } = useAuth();
  const [showAddForm, setShowAddForm] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [isCreateMode, setIsCreateMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    role: 'associate'
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim() || !formData.email.trim()) {
      alert('Please fill in all required fields');
      return;
    }

    setLoading(true);

    try {
      await axios.post(`${API}/users`, formData);
      
      // Reset form
      setFormData({
        name: '',
        email: '',
        role: 'associate'
      });
      
      setShowAddForm(false);
      await onUserAdded();
    } catch (error) {
      console.error('Error creating user:', error);
      alert('Failed to add team member. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setShowAddForm(false);
    setFormData({
      name: '',
      email: '',
      role: 'associate'
    });
  };

  const handleAddTeamMember = () => {
    setSelectedUser(null);
    setIsCreateMode(true);
    setShowProfileModal(true);
  };

  const handleEditProfile = (user) => {
    setSelectedUser(user);
    setIsCreateMode(false);
    setShowProfileModal(true);
  };

  const handleCloseProfileModal = () => {
    setShowProfileModal(false);
    setSelectedUser(null);
    setIsCreateMode(false);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Not specified';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getUserTaskStats = (userId) => {
    const userTasks = tasks.filter(task => task.assignee_id === userId);
    const completedTasks = userTasks.filter(task => task.status === 'completed');
    const pendingTasks = userTasks.filter(task => task.status === 'pending');
    const inProgressTasks = userTasks.filter(task => task.status === 'in_progress');
    const overdueTasks = userTasks.filter(task => task.status === 'overdue');

    return {
      total: userTasks.length,
      completed: completedTasks.length,
      pending: pendingTasks.length,
      inProgress: inProgressTasks.length,
      overdue: overdueTasks.length,
      completionRate: userTasks.length > 0 ? (completedTasks.length / userTasks.length * 100) : 0
    };
  };

  const getRoleIcon = (role) => {
    const roleIcons = {
      partner: '👔',
      associate: '👨‍💼',
      junior: '👨‍💻',
      intern: '🎓'
    };
    return roleIcons[role] || '👤';
  };

  const getRoleColor = (role) => {
    const roleColors = {
      partner: 'bg-purple-100 text-purple-800 border-purple-200',
      associate: 'bg-blue-100 text-blue-800 border-blue-200',
      junior: 'bg-green-100 text-green-800 border-green-200',
      intern: 'bg-yellow-100 text-yellow-800 border-yellow-200'
    };
    return roleColors[role] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Team Members</h2>
          <p className="mt-2 text-gray-600">Manage your team and track their performance</p>
        </div>
        <div className="mt-4 sm:mt-0">
          {isPartner() && (
            <button
              onClick={handleAddTeamMember}
              className="btn-primary"
              data-testid="add-team-member-button"
            >
              Add Team Member
            </button>
          )}
        </div>
      </div>

      {/* Add Team Member Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-fade-in">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Add New Team Member</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="name" className="form-label">
                  Full Name *
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter full name..."
                  className="form-input"
                  data-testid="member-name-input"
                  required
                />
              </div>
              <div>
                <label htmlFor="email" className="form-label">
                  Email Address *
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="Enter email address..."
                  className="form-input"
                  data-testid="member-email-input"
                  required
                />
              </div>
            </div>
            <div>
              <label htmlFor="role" className="form-label">
                Role
              </label>
              <select
                id="role"
                name="role"
                value={formData.role}
                onChange={handleChange}
                className="form-input"
                data-testid="member-role-select"
              >
                <option value="partner">Partner</option>
                <option value="associate">Associate</option>
                <option value="junior">Junior</option>
                <option value="intern">Intern</option>
              </select>
            </div>
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
                data-testid="add-member-submit"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Adding...
                  </>
                ) : (
                  'Add Member'
                )}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="btn-secondary"
                data-testid="add-member-cancel"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Team Members Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {users.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <div className="text-gray-400 text-4xl mb-4">👥</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No team members yet</h3>
            <p className="text-gray-600 mb-4">Add your first team member to get started</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="btn-primary"
            >
              Add Team Member
            </button>
          </div>
        ) : (
          users.map(user => {
            const stats = getUserTaskStats(user.id);
            
            return (
              <div key={user.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 card-hover" data-testid={`team-member-card-${user.id}`}>
                {/* Member Header */}
                <div className="flex items-center mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mr-4 overflow-hidden">
                    {user.profile_picture_url ? (
                      <img src={user.profile_picture_url} alt={user.name} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-blue-600 font-semibold text-lg">
                        {user.name.charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-900">{user.name}</h3>
                        <p className="text-sm text-gray-600">{user.email}</p>
                        {user.phone && (
                          <p className="text-xs text-gray-500">{user.phone}</p>
                        )}
                      </div>
                      {isPartner() && (
                        <button
                          onClick={() => handleEditProfile(user)}
                          className="text-gray-400 hover:text-blue-600 p-1"
                          data-testid={`edit-profile-${user.id}`}
                          title="Edit Profile"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="text-2xl">
                    {getRoleIcon(user.role)}
                  </div>
                </div>

                {/* Role and Department */}
                <div className="mb-4 space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className={`badge ${getRoleColor(user.role)} capitalize`}>
                      {user.role}
                    </span>
                    {user.department && (
                      <span className="badge bg-gray-100 text-gray-700 border-gray-200">
                        {user.department}
                      </span>
                    )}
                  </div>
                  {user.hire_date && (
                    <p className="text-xs text-gray-500">
                      Joined: {formatDate(user.hire_date)}
                    </p>
                  )}
                </div>

                {/* Skills */}
                {user.skills && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-700 mb-1">Skills</p>
                    <p className="text-xs text-gray-600 line-clamp-2">{user.skills}</p>
                  </div>
                )}

                {/* Task Statistics */}
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Total Tasks</span>
                    <span className="font-medium text-gray-900">{stats.total}</span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Completed</span>
                    <span className="font-medium text-green-600">{stats.completed}</span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">In Progress</span>
                    <span className="font-medium text-blue-600">{stats.inProgress}</span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Pending</span>
                    <span className="font-medium text-amber-600">{stats.pending}</span>
                  </div>

                  {stats.overdue > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Overdue</span>
                      <span className="font-medium text-red-600">{stats.overdue}</span>
                    </div>
                  )}

                  {/* Completion Rate */}
                  <div className="pt-2 border-t border-gray-100">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-gray-600">Completion Rate</span>
                      <span className="font-medium text-gray-900">
                        {stats.completionRate.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${stats.completionRate}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Team Summary */}
      {users.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Team Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{users.length}</div>
              <div className="text-sm text-gray-600">Total Members</div>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {tasks.filter(t => t.status === 'completed').length}
              </div>
              <div className="text-sm text-gray-600">Tasks Completed</div>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg">
              <div className="text-2xl font-bold text-amber-600">
                {tasks.filter(t => t.status === 'in_progress').length}
              </div>
              <div className="text-sm text-gray-600">In Progress</div>
            </div>
            <div className="p-3 bg-red-50 rounded-lg">
              <div className="text-2xl font-bold text-red-600">
                {tasks.filter(t => t.status === 'overdue').length}
              </div>
              <div className="text-sm text-gray-600">Overdue</div>
            </div>
          </div>
        </div>
      )}

      {/* User Profile Modal */}
      <UserProfileModal
        user={selectedUser}
        isOpen={showProfileModal}
        onClose={handleCloseProfileModal}
        onUserUpdated={onUserAdded}
        isCreate={isCreateMode}
      />
    </div>
  );
};

export default TeamMembers;