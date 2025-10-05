import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UserProfileModal = ({ user, isOpen, onClose, onUserUpdated, isCreate = false }) => {
  const { isPartner } = useAuth();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    role: 'associate',
    phone: '',
    department: '',
    hire_date: '',
    profile_picture_url: '',
    address: '',
    emergency_contact: '',
    skills: '',
    bio: '',
    password: ''
  });

  useEffect(() => {
    if (user && !isCreate) {
      setFormData({
        name: user.name || '',
        email: user.email || '',
        role: user.role || 'associate',
        phone: user.phone || '',
        department: user.department || '',
        hire_date: user.hire_date ? new Date(user.hire_date).toISOString().split('T')[0] : '',
        profile_picture_url: user.profile_picture_url || '',
        address: user.address || '',
        emergency_contact: user.emergency_contact || '',
        skills: user.skills || '',
        bio: user.bio || '',
        password: ''
      });
    } else if (isCreate) {
      setFormData({
        name: '',
        email: '',
        role: 'associate',
        phone: '',
        department: '',
        hire_date: '',
        profile_picture_url: '',
        address: '',
        emergency_contact: '',
        skills: '',
        bio: '',
        password: ''
      });
    }
  }, [user, isCreate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isCreate) {
        // Validate required fields for creating new user
        if (!formData.name.trim()) {
          alert('Please enter the full name');
          setLoading(false);
          return;
        }
        if (!formData.email.trim()) {
          alert('Please enter the email address');
          setLoading(false);
          return;
        }
        if (!formData.password.trim()) {
          alert('Please enter an initial password for the new team member');
          setLoading(false);
          return;
        }
        if (formData.password.length < 6) {
          alert('Password must be at least 6 characters long');
          setLoading(false);
          return;
        }
        
        // Create new user
        const userData = { ...formData };
        
        // Handle empty date fields - convert empty strings to null
        if (userData.hire_date && userData.hire_date.trim()) {
          userData.hire_date = new Date(userData.hire_date).toISOString();
        } else {
          userData.hire_date = null;
        }
        
        // Clean up empty string fields
        Object.keys(userData).forEach(key => {
          if (userData[key] === '') {
            userData[key] = null;
          }
        });
        
        await axios.post(`${API}/users`, userData);
      } else {
        // Update existing user profile
        const updateData = { ...formData };
        delete updateData.password; // Don't include password in profile updates
        
        // Handle empty date fields - convert empty strings to null
        if (updateData.hire_date && updateData.hire_date.trim()) {
          updateData.hire_date = new Date(updateData.hire_date).toISOString();
        } else {
          updateData.hire_date = null;
        }
        
        // Clean up empty string fields
        Object.keys(updateData).forEach(key => {
          if (updateData[key] === '') {
            updateData[key] = null;
          }
        });
        
        await axios.put(`${API}/users/${user.id}`, updateData);
      }
      
      await onUserUpdated();
      onClose();
    } catch (error) {
      console.error('Error saving user:', error);
      
      // Enhanced error message handling for different error types
      let errorMessage = 'Failed to save user profile';
      
      if (error.response?.data?.detail) {
        // Handle string error messages
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } 
        // Handle Pydantic validation error arrays
        else if (Array.isArray(error.response.data.detail)) {
          const validationErrors = error.response.data.detail.map(err => {
            const field = err.loc ? err.loc.join('.') : 'field';
            return `${field}: ${err.msg}`;
          }).join('\n');
          errorMessage = `Validation errors:\n${validationErrors}`;
        }
        // Handle other object types
        else {
          errorMessage = JSON.stringify(error.response.data.detail);
        }
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordReset = async () => {
    if (!formData.password.trim()) {
      alert('Please enter a new password');
      return;
    }

    if (formData.password.length < 6) {
      alert('Password must be at least 6 characters long');
      return;
    }

    setLoading(true);

    try {
      await axios.put(`${API}/users/${user.id}/password`, {
        user_id: user.id,
        new_password: formData.password
      });
      
      setFormData(prev => ({ ...prev, password: '' }));
      alert('Password updated successfully');
    } catch (error) {
      console.error('Error updating password:', error);
      alert('Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const departments = [
    'Legal',
    'Corporate Law',
    'Litigation',
    'Tax Law',
    'Employment Law',
    'Real Estate Law',
    'Intellectual Property',
    'Family Law',
    'Criminal Law',
    'Administrative'
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        data-testid="user-profile-modal"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            {isCreate ? 'Add New Team Member' : `Edit ${user?.name}'s Profile`}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
            data-testid="close-modal"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 pt-4">
          <div className="flex space-x-6">
            <button
              onClick={() => setActiveTab('profile')}
              className={`pb-2 border-b-2 font-medium text-sm ${
                activeTab === 'profile'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              data-testid="profile-tab"
            >
              Profile Information
            </button>
            {!isCreate && (
              <button
                onClick={() => setActiveTab('security')}
                className={`pb-2 border-b-2 font-medium text-sm ${
                  activeTab === 'security'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
                data-testid="security-tab"
              >
                Security & Access
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="px-6 py-4" noValidate>
          {activeTab === 'profile' && (
            <div className="space-y-6 max-h-96 overflow-y-auto">
              {/* Basic Information */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">Full Name *</label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="name-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Email Address *</label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="email-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Role</label>
                    <select
                      name="role"
                      value={formData.role}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="role-select"
                    >
                      <option value="partner">Partner</option>
                      <option value="associate">Associate</option>
                      <option value="junior">Junior</option>
                      <option value="intern">Intern</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Phone Number</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="phone-input"
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                </div>
              </div>

              {/* Professional Information */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Professional Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">Department</label>
                    <select
                      name="department"
                      value={formData.department}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="department-select"
                    >
                      <option value="">Select Department...</option>
                      {departments.map(dept => (
                        <option key={dept} value={dept}>{dept}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Hire Date</label>
                    <input
                      type="date"
                      name="hire_date"
                      value={formData.hire_date}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="hire-date-input"
                    />
                  </div>
                </div>
                <div className="mt-4">
                  <label className="form-label">Skills & Specializations</label>
                  <textarea
                    name="skills"
                    value={formData.skills}
                    onChange={handleChange}
                    rows={3}
                    className="form-input resize-none"
                    data-testid="skills-input"
                    placeholder="e.g., Contract Law, Corporate Mergers, Litigation..."
                  />
                </div>
              </div>

              {/* Personal Information */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Personal Information</h3>
                <div className="space-y-4">
                  <div>
                    <label className="form-label">Profile Picture URL</label>
                    <input
                      type="url"
                      name="profile_picture_url"
                      value={formData.profile_picture_url}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="profile-picture-input"
                      placeholder="https://example.com/profile.jpg"
                    />
                  </div>
                  <div>
                    <label className="form-label">Address</label>
                    <textarea
                      name="address"
                      value={formData.address}
                      onChange={handleChange}
                      rows={2}
                      className="form-input resize-none"
                      data-testid="address-input"
                      placeholder="Street address, city, state, postal code"
                    />
                  </div>
                  <div>
                    <label className="form-label">Emergency Contact</label>
                    <input
                      type="text"
                      name="emergency_contact"
                      value={formData.emergency_contact}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="emergency-contact-input"
                      placeholder="Name, relationship, phone number"
                    />
                  </div>
                  <div>
                    <label className="form-label">Bio / Notes</label>
                    <textarea
                      name="bio"
                      value={formData.bio}
                      onChange={handleChange}
                      rows={3}
                      className="form-input resize-none"
                      data-testid="bio-input"
                      placeholder="Brief biography or additional notes..."
                    />
                  </div>
                </div>
              </div>

              {/* Initial Password for New Users */}
              {isCreate && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Login Credentials</h3>
                  <div>
                    <label className="form-label">Initial Password *</label>
                    <input
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="password-input"
                      required
                      minLength={6}
                      placeholder="Enter initial password (min 6 characters)"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'security' && !isCreate && (
            <div className="space-y-6 max-h-96 overflow-y-auto">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Password Management</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Reset the user's password. They will be notified of the change.
                </p>
                <div className="flex gap-4 items-end">
                  <div className="flex-1">
                    <label className="form-label">New Password</label>
                    <input
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="new-password-input"
                      minLength={6}
                      placeholder="Enter new password (min 6 characters)"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handlePasswordReset}
                    disabled={loading}
                    className="btn-secondary"
                    data-testid="reset-password-button"
                  >
                    {loading ? 'Updating...' : 'Reset Password'}
                  </button>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Access Information</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">Login Email:</span>
                      <p className="text-gray-900">{user?.email}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Role:</span>
                      <p className="text-gray-900 capitalize">{user?.role}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Account Created:</span>
                      <p className="text-gray-900">
                        {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Status:</span>
                      <p className="text-green-600 font-medium">Active</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              data-testid="cancel-button"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              data-testid="save-button"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {isCreate ? 'Creating...' : 'Saving...'}
                </>
              ) : (
                <>
                  {isCreate ? 'Create Team Member' : 'Save Changes'}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UserProfileModal;