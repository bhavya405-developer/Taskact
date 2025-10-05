import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CreateTask = ({ users, onTaskCreated }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    client_name: '',
    category: '',
    assignee_id: '',
    creator_id: users.find(u => u.role === 'partner')?.id || users[0]?.id || '',
    priority: 'medium',
    due_date: ''
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
    
    if (!formData.title.trim()) {
      alert('Please enter a task title');
      return;
    }
    
    if (!formData.client_name.trim()) {
      alert('Please enter a client name');
      return;
    }
    
    if (!formData.category.trim()) {
      alert('Please select a task category');
      return;
    }
    
    if (!formData.assignee_id) {
      alert('Please select an assignee');
      return;
    }

    setLoading(true);

    try {
      const taskData = {
        ...formData,
        due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null
      };

      await axios.post(`${API}/tasks`, taskData);
      
      await onTaskCreated();
      navigate('/tasks');
    } catch (error) {
      console.error('Error creating task:', error);
      alert('Failed to create task. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    navigate('/tasks');
  };

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-8 text-center">
        <h2 className="text-3xl font-bold text-gray-900">Create New Task</h2>
        <p className="mt-2 text-gray-600">Assign a new task to your team member</p>
      </div>

      {/* Form */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Task Title */}
          <div>
            <label htmlFor="title" className="form-label">
              Task Title *
            </label>
            <input
              type="text"
              id="title"
              name="title"
              value={formData.title}
              onChange={handleChange}
              placeholder="Enter task title..."
              className="form-input"
              data-testid="task-title-input"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="form-label">
              Description
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Enter task description..."
              rows={4}
              className="form-input resize-none"
              data-testid="task-description-input"
            />
          </div>

          {/* Client Name and Category Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="client_name" className="form-label">
                Client Name *
              </label>
              <input
                type="text"
                id="client_name"
                name="client_name"
                value={formData.client_name}
                onChange={handleChange}
                placeholder="Enter client name..."
                className="form-input"
                data-testid="client-name-input"
                required
              />
            </div>

            <div>
              <label htmlFor="category" className="form-label">
                Task Category *
              </label>
              <select
                id="category"
                name="category"
                value={formData.category}
                onChange={handleChange}
                className="form-input"
                data-testid="category-select"
                required
              >
                <option value="">Select category...</option>
                <option value="Legal Research">Legal Research</option>
                <option value="Contract Review">Contract Review</option>
                <option value="Client Meeting">Client Meeting</option>
                <option value="Court Filing">Court Filing</option>
                <option value="Document Preparation">Document Preparation</option>
                <option value="Case Analysis">Case Analysis</option>
                <option value="Negotiation">Negotiation</option>
                <option value="Due Diligence">Due Diligence</option>
                <option value="Compliance Review">Compliance Review</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          {/* Assignee and Creator Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="assignee_id" className="form-label">
                Assign To *
              </label>
              <select
                id="assignee_id"
                name="assignee_id"
                value={formData.assignee_id}
                onChange={handleChange}
                className="form-input"
                data-testid="assignee-select"
                required
              >
                <option value="">Select team member...</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.role})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="creator_id" className="form-label">
                Created By
              </label>
              <select
                id="creator_id"
                name="creator_id"
                value={formData.creator_id}
                onChange={handleChange}
                className="form-input"
                data-testid="creator-select"
                required
              >
                <option value="">Select creator...</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.role})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Priority and Due Date Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="priority" className="form-label">
                Priority
              </label>
              <select
                id="priority"
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                className="form-input"
                data-testid="priority-select"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div>
              <label htmlFor="due_date" className="form-label">
                Due Date
              </label>
              <input
                type="date"
                id="due_date"
                name="due_date"
                value={formData.due_date}
                onChange={handleChange}
                className="form-input"
                data-testid="due-date-input"
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex flex-col sm:flex-row gap-3 pt-6 border-t border-gray-200">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center justify-center"
              data-testid="create-task-submit"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Creating Task...
                </>
              ) : (
                <>
                  <span className="mr-2">✓</span>
                  Create Task
                </>
              )}
            </button>
            
            <button
              type="button"
              onClick={handleCancel}
              disabled={loading}
              className="btn-secondary"
              data-testid="cancel-button"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>

      {/* Helper Info */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <div className="w-5 h-5 text-blue-600">ℹ️</div>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">Task Creation Tips</h3>
            <div className="mt-2 text-sm text-blue-700">
              <ul className="list-disc list-inside space-y-1">
                <li>Use clear, specific task titles for better tracking</li>
                <li>Include detailed descriptions for complex tasks</li>
                <li>Set realistic due dates to improve completion rates</li>
                <li>Choose appropriate priority levels to help team focus</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateTask;