import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CreateTask = ({ users, onTaskCreated }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [clients, setClients] = useState([]);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    client_name: '',
    category: '',
    assignee_id: '',
    priority: 'medium',
    due_date: '',
    estimated_hours: '',
    is_recurring: false,
    recurrence_type: '',
    recurrence_end_date: '',
    custom_day_of_month: '1',
    custom_day_of_week: 'monday',
    custom_every_n_weeks: '1'
  });

  // Fetch categories and clients
  useEffect(() => {
    const fetchCategoriesAndClients = async () => {
      try {
        const [categoriesRes, clientsRes] = await Promise.all([
          axios.get(`${API}/categories`),
          axios.get(`${API}/clients`)
        ]);
        setCategories(categoriesRes.data);
        setClients(clientsRes.data);
      } catch (error) {
        console.error('Error fetching categories/clients:', error);
      }
    };
    
    fetchCategoriesAndClients();
  }, []);

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
        due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null,
        estimated_hours: formData.estimated_hours ? parseFloat(formData.estimated_hours) : null,
        is_recurring: formData.is_recurring,
        recurrence_type: formData.is_recurring ? formData.recurrence_type : null,
        recurrence_end_date: formData.is_recurring && formData.recurrence_end_date 
          ? new Date(formData.recurrence_end_date).toISOString() : null,
      };

      // Build recurrence_config based on type
      if (formData.is_recurring) {
        if (formData.recurrence_type === 'custom_day_of_month') {
          taskData.recurrence_config = { day_of_month: parseInt(formData.custom_day_of_month) };
        } else if (formData.recurrence_type === 'custom_day_of_week') {
          taskData.recurrence_config = { 
            day_of_week: formData.custom_day_of_week, 
            every_n_weeks: parseInt(formData.custom_every_n_weeks) 
          };
        } else if (formData.recurrence_type === 'weekly') {
          taskData.recurrence_config = { day_of_week: formData.custom_day_of_week };
        } else {
          taskData.recurrence_config = {};
        }
      }

      // Clean up extra form fields that backend doesn't need
      delete taskData.custom_day_of_month;
      delete taskData.custom_day_of_week;
      delete taskData.custom_every_n_weeks;

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
                Client *
              </label>
              <select
                id="client_name"
                name="client_name"
                value={formData.client_name}
                onChange={handleChange}
                className="form-input"
                data-testid="client-select"
                required
              >
                <option value="">Select client...</option>
                {clients.map(client => (
                  <option key={client.id} value={client.name}>
                    {client.name}
                  </option>
                ))}
              </select>
              {clients.length === 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  No clients available. Ask a partner to add clients.
                </p>
              )}
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
                {categories.map(category => (
                  <option key={category.id} value={category.name}>
                    {category.name}
                  </option>
                ))}
              </select>
              {categories.length === 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  No categories available. Ask a partner to add categories.
                </p>
              )}
            </div>
          </div>

          {/* Assignee */}
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
                  {user.name}
                </option>
              ))}
            </select>
          </div>

          {/* Priority, Due Date, and Estimated Hours Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

            <div>
              <label htmlFor="estimated_hours" className="form-label">
                Est. Hours <span className="text-gray-400 text-xs">(optional)</span>
              </label>
              <input
                type="number"
                id="estimated_hours"
                name="estimated_hours"
                value={formData.estimated_hours}
                onChange={handleChange}
                className="form-input"
                placeholder="e.g., 2.5"
                min="0"
                step="0.5"
                data-testid="estimated-hours-input"
              />
            </div>
          </div>

          {/* Recurring Task Section */}
          <div className="border-t border-gray-200 pt-6">
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                name="is_recurring"
                checked={formData.is_recurring}
                onChange={(e) => setFormData(prev => ({ ...prev, is_recurring: e.target.checked, recurrence_type: e.target.checked ? 'daily' : '' }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 h-4 w-4"
                data-testid="recurring-toggle"
              />
              <span className="form-label mb-0">Make this a recurring task</span>
            </label>

            {formData.is_recurring && (
              <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-4">
                <div>
                  <label htmlFor="recurrence_type" className="form-label">
                    Frequency *
                  </label>
                  <select
                    id="recurrence_type"
                    name="recurrence_type"
                    value={formData.recurrence_type}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="recurrence-type-select"
                    required
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="fortnightly">Fortnightly (Every 2 Weeks)</option>
                    <option value="monthly">Monthly</option>
                    <option value="half_yearly">Half Yearly (Every 6 Months)</option>
                    <option value="annually">Annually</option>
                    <option value="custom_day_of_month">Specific Date of Every Month</option>
                    <option value="custom_day_of_week">Specific Day of Week(s)</option>
                  </select>
                </div>

                {/* Weekly - pick a day */}
                {formData.recurrence_type === 'weekly' && (
                  <div>
                    <label htmlFor="custom_day_of_week" className="form-label">
                      Day of Week
                    </label>
                    <select
                      id="custom_day_of_week"
                      name="custom_day_of_week"
                      value={formData.custom_day_of_week}
                      onChange={handleChange}
                      className="form-input"
                      data-testid="weekly-day-select"
                    >
                      <option value="monday">Monday</option>
                      <option value="tuesday">Tuesday</option>
                      <option value="wednesday">Wednesday</option>
                      <option value="thursday">Thursday</option>
                      <option value="friday">Friday</option>
                      <option value="saturday">Saturday</option>
                      <option value="sunday">Sunday</option>
                    </select>
                  </div>
                )}

                {/* Custom day of month */}
                {formData.recurrence_type === 'custom_day_of_month' && (
                  <div>
                    <label htmlFor="custom_day_of_month" className="form-label">
                      Day of Month (1-31)
                    </label>
                    <input
                      type="number"
                      id="custom_day_of_month"
                      name="custom_day_of_month"
                      value={formData.custom_day_of_month}
                      onChange={handleChange}
                      className="form-input"
                      min="1"
                      max="31"
                      data-testid="day-of-month-input"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      If the month has fewer days, the last day of the month will be used.
                    </p>
                  </div>
                )}

                {/* Custom day of week with interval */}
                {formData.recurrence_type === 'custom_day_of_week' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="custom_day_of_week" className="form-label">
                        Day of Week
                      </label>
                      <select
                        id="custom_day_of_week"
                        name="custom_day_of_week"
                        value={formData.custom_day_of_week}
                        onChange={handleChange}
                        className="form-input"
                        data-testid="custom-day-of-week-select"
                      >
                        <option value="monday">Monday</option>
                        <option value="tuesday">Tuesday</option>
                        <option value="wednesday">Wednesday</option>
                        <option value="thursday">Thursday</option>
                        <option value="friday">Friday</option>
                        <option value="saturday">Saturday</option>
                        <option value="sunday">Sunday</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="custom_every_n_weeks" className="form-label">
                        Every N Weeks
                      </label>
                      <input
                        type="number"
                        id="custom_every_n_weeks"
                        name="custom_every_n_weeks"
                        value={formData.custom_every_n_weeks}
                        onChange={handleChange}
                        className="form-input"
                        min="1"
                        max="52"
                        data-testid="every-n-weeks-input"
                      />
                    </div>
                  </div>
                )}

                {/* Recurrence End Date */}
                <div>
                  <label htmlFor="recurrence_end_date" className="form-label">
                    End Date <span className="text-gray-400 text-xs">(optional, defaults to 1 year)</span>
                  </label>
                  <input
                    type="date"
                    id="recurrence_end_date"
                    name="recurrence_end_date"
                    value={formData.recurrence_end_date}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="recurrence-end-date-input"
                    min={formData.due_date || new Date().toISOString().split('T')[0]}
                  />
                </div>

                <p className="text-xs text-gray-600">
                  Recurring tasks will be auto-generated with the same details. Each instance can be managed independently.
                </p>
              </div>
            )}
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