import React, { useState } from 'react';
import axios from 'axios';
import UserProfileModal from './UserProfileModal';
import { useAuth } from '../contexts/AuthContext';
import { Trash2, UserX, UserCheck, Edit, AlertTriangle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TeamMembers = ({ users, tasks, onUserAdded }) => {
  const { isPartner, user: currentUser } = useAuth();
  const [showAddForm, setShowAddForm] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [isCreateMode, setIsCreateMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null); // Track which user action is loading
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
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

  // Delete user
  const handleDeleteUser = async (user) => {
    setConfirmAction({
      type: 'delete',
      user,
      title: 'Delete Team Member',
      message: `Are you sure you want to permanently delete "${user.name}"? This action cannot be undone.`,
      confirmText: 'Delete',
      confirmClass: 'bg-red-600 hover:bg-red-700'
    });
    setShowConfirmModal(true);
  };

  // Deactivate user
  const handleDeactivateUser = async (user) => {
    setConfirmAction({
      type: 'deactivate',
      user,
      title: 'Deactivate Team Member',
      message: `Are you sure you want to deactivate "${user.name}"? They will no longer be able to login, but their task history will be preserved.`,
      confirmText: 'Deactivate',
      confirmClass: 'bg-amber-600 hover:bg-amber-700'
    });
    setShowConfirmModal(true);
  };

  // Reactivate user
  const handleReactivateUser = async (user) => {
    setConfirmAction({
      type: 'reactivate',
      user,
      title: 'Reactivate Team Member',
      message: `Are you sure you want to reactivate "${user.name}"? They will be able to login again.`,
      confirmText: 'Reactivate',
      confirmClass: 'bg-green-600 hover:bg-green-700'
    });
    setShowConfirmModal(true);
  };

  // Execute confirmed action
  const executeAction = async () => {
    if (!confirmAction) return;
    
    const { type, user } = confirmAction;
    setActionLoading(user.id);
    setShowConfirmModal(false);

    try {
      let response;
      if (type === 'delete') {
        response = await axios.delete(`${API}/users/${user.id}`);
      } else if (type === 'deactivate') {
        response = await axios.put(`${API}/users/${user.id}/deactivate`);
      } else if (type === 'reactivate') {
        response = await axios.put(`${API}/users/${user.id}/reactivate`);
      }
      
      // Refresh users list
      await onUserAdded();
      
      // Show success message
      alert(response.data.message);
    } catch (error) {
      console.error(`Error ${type}ing user:`, error);
      alert(error.response?.data?.detail || `Failed to ${type} user. Please try again.`);
    } finally {
      setActionLoading(null);
      setConfirmAction(null);
    }
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
      {/* Confirmation Modal */}
      {showConfirmModal && confirmAction && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 animate-fade-in">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center mr-3">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">{confirmAction.title}</h3>
            </div>
            <p className="text-gray-600 mb-6">{confirmAction.message}</p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowConfirmModal(false);
                  setConfirmAction(null);
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                data-testid="confirm-cancel"
              >
                Cancel
              </button>
              <button
                onClick={executeAction}
                className={`px-4 py-2 text-white rounded-md transition-colors ${confirmAction.confirmClass}`}
                data-testid="confirm-action"
              >
                {confirmAction.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}

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
            const isCurrentUser = currentUser?.id === user.id;
            const isInactive = user.active === false;
            
            return (
              <div 
                key={user.id} 
                className={`bg-white rounded-lg shadow-sm border p-6 card-hover relative ${
                  isInactive ? 'border-gray-300 opacity-60' : 'border-gray-200'
                }`} 
                data-testid={`team-member-card-${user.id}`}
              >
                {/* Inactive Badge */}
                {isInactive && (
                  <div className="absolute top-3 right-3">
                    <span className="px-2 py-1 text-xs font-medium bg-gray-200 text-gray-600 rounded-full">
                      Inactive
                    </span>
                  </div>
                )}

                {/* Member Header */}
                <div className="flex items-center mb-4">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-4 overflow-hidden ${
                    isInactive ? 'bg-gray-200' : 'bg-blue-100'
                  }`}>
                    {user.profile_picture_url ? (
                      <img src={user.profile_picture_url} alt={user.name} className="w-full h-full object-cover" />
                    ) : (
                      <span className={`font-semibold text-lg ${isInactive ? 'text-gray-500' : 'text-blue-600'}`}>
                        {user.name.charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className={`font-semibold ${isInactive ? 'text-gray-500' : 'text-gray-900'}`}>
                      {user.name}
                      {isCurrentUser && <span className="text-xs text-blue-600 ml-2">(You)</span>}
                    </h3>
                    <p className="text-sm text-gray-600">{user.email}</p>
                    {user.phone && (
                      <p className="text-xs text-gray-500">{user.phone}</p>
                    )}
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

                {/* Action Buttons for Partners */}
                {isPartner() && !isCurrentUser && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="flex flex-wrap gap-2">
                      {/* Edit Button */}
                      <button
                        onClick={() => handleEditProfile(user)}
                        disabled={actionLoading === user.id}
                        className="flex items-center px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors"
                        data-testid={`edit-user-${user.id}`}
                        title="Edit Profile"
                      >
                        <Edit className="w-3.5 h-3.5 mr-1" />
                        Edit
                      </button>

                      {/* Deactivate/Reactivate Button */}
                      {isInactive ? (
                        <button
                          onClick={() => handleReactivateUser(user)}
                          disabled={actionLoading === user.id}
                          className="flex items-center px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-md transition-colors"
                          data-testid={`reactivate-user-${user.id}`}
                          title="Reactivate User"
                        >
                          {actionLoading === user.id ? (
                            <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-green-700 mr-1"></div>
                          ) : (
                            <UserCheck className="w-3.5 h-3.5 mr-1" />
                          )}
                          Reactivate
                        </button>
                      ) : (
                        <button
                          onClick={() => handleDeactivateUser(user)}
                          disabled={actionLoading === user.id}
                          className="flex items-center px-3 py-1.5 text-xs font-medium text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-md transition-colors"
                          data-testid={`deactivate-user-${user.id}`}
                          title="Deactivate User"
                        >
                          {actionLoading === user.id ? (
                            <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-amber-700 mr-1"></div>
                          ) : (
                            <UserX className="w-3.5 h-3.5 mr-1" />
                          )}
                          Deactivate
                        </button>
                      )}

                      {/* Delete Button - only if no tasks */}
                      {stats.total === 0 && (
                        <button
                          onClick={() => handleDeleteUser(user)}
                          disabled={actionLoading === user.id}
                          className="flex items-center px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-md transition-colors"
                          data-testid={`delete-user-${user.id}`}
                          title="Delete User (No tasks assigned)"
                        >
                          {actionLoading === user.id ? (
                            <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-red-700 mr-1"></div>
                          ) : (
                            <Trash2 className="w-3.5 h-3.5 mr-1" />
                          )}
                          Delete
                        </button>
                      )}
                    </div>
                    
                    {/* Info text for users with tasks */}
                    {stats.total > 0 && !isInactive && (
                      <p className="text-xs text-gray-500 mt-2">
                        User has {stats.total} task(s). Use "Deactivate" to revoke access while preserving history.
                      </p>
                    )}
                  </div>
                )}
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
              <div className="text-2xl font-bold text-blue-600">
                {users.filter(u => u.active !== false).length}
              </div>
              <div className="text-sm text-gray-600">Active Members</div>
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
