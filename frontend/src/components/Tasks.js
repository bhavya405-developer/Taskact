import React, { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Tasks = ({ tasks, users, onTaskUpdate }) => {
  const [filter, setFilter] = useState('all');
  const [assigneeFilter, setAssigneeFilter] = useState('all');
  const [clientFilter, setClientFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [updating, setUpdating] = useState({});

  const getStatusDisplay = (status) => {
    const statusConfig = {
      pending: { label: 'Pending', class: 'status-pending' },
      on_hold: { label: 'On Hold', class: 'status-on_hold' },
      completed: { label: 'Completed', class: 'status-completed' },
      overdue: { label: 'Overdue', class: 'status-overdue' }
    };
    return statusConfig[status] || statusConfig.pending;
  };

  const getPriorityDisplay = (priority) => {
    const priorityConfig = {
      low: { label: 'Low', class: 'priority-low' },
      medium: { label: 'Medium', class: 'priority-medium' },
      high: { label: 'High', class: 'priority-high' },
      urgent: { label: 'Urgent', class: 'priority-urgent' }
    };
    return priorityConfig[priority] || priorityConfig.medium;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'No due date';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const handleStatusChange = async (taskId, newStatus) => {
    setUpdating(prev => ({ ...prev, [taskId]: true }));
    
    try {
      await axios.put(`${API}/tasks/${taskId}`, {
        status: newStatus
      });
      
      await onTaskUpdate();
    } catch (error) {
      console.error('Error updating task status:', error);
      alert('Failed to update task status');
    } finally {
      setUpdating(prev => ({ ...prev, [taskId]: false }));
    }
  };

  const filteredTasks = tasks.filter(task => {
    const matchesStatus = filter === 'all' || task.status === filter;
    const matchesAssignee = assigneeFilter === 'all' || task.assignee_id === assigneeFilter;
    const matchesClient = clientFilter === 'all' || (task.client_name && task.client_name.toLowerCase().includes(clientFilter.toLowerCase()));
    const matchesCategory = categoryFilter === 'all' || task.category === categoryFilter;
    return matchesStatus && matchesAssignee && matchesClient && matchesCategory;
  });

  // Get unique clients and categories for filter options
  const uniqueClients = [...new Set(tasks.map(task => task.client_name).filter(Boolean))].sort();
  const uniqueCategories = [...new Set(tasks.map(task => task.category).filter(Boolean))].sort();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Tasks</h2>
          <p className="mt-2 text-gray-600">Manage and track all team tasks</p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link
            to="/create-task"
            className="btn-primary"
            data-testid="create-task-button"
          >
            Create New Task
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="form-label">Filter by Status</label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="form-input"
              data-testid="status-filter"
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="on_hold">On Hold</option>
              <option value="completed">Completed</option>
              <option value="overdue">Overdue</option>
            </select>
          </div>
          <div>
            <label className="form-label">Filter by Assignee</label>
            <select
              value={assigneeFilter}
              onChange={(e) => setAssigneeFilter(e.target.value)}
              className="form-input"
              data-testid="assignee-filter"
            >
              <option value="all">All Team Members</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="form-label">Filter by Client</label>
            <select
              value={clientFilter}
              onChange={(e) => setClientFilter(e.target.value)}
              className="form-input"
              data-testid="client-filter"
            >
              <option value="all">All Clients</option>
              {uniqueClients.map(client => (
                <option key={client} value={client}>
                  {client}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="form-label">Filter by Category</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="form-input"
              data-testid="category-filter"
            >
              <option value="all">All Categories</option>
              {uniqueCategories.map(category => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Tasks List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        {filteredTasks.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-4xl mb-4">📋</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No tasks found</h3>
            <p className="text-gray-600 mb-4">
              {tasks.length === 0 
                ? "Get started by creating your first task"
                : "Try adjusting your filters or create a new task"
              }
            </p>
            <Link
              to="/create-task"
              className="btn-primary"
            >
              Create Task
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="table-header">Task</th>
                  <th className="table-header">Client</th>
                  <th className="table-header">Category</th>
                  <th className="table-header">Assignee</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Priority</th>
                  <th className="table-header">Due Date</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredTasks.map((task) => {
                  const status = getStatusDisplay(task.status);
                  const priority = getPriorityDisplay(task.priority);
                  
                  return (
                    <tr key={task.id} className="hover:bg-gray-50 transition-colors" data-testid={`task-row-${task.id}`}>
                      <td className="table-cell">
                        <div>
                          <div className="font-medium text-gray-900">{task.title}</div>
                          {task.description && (
                            <div className="text-sm text-gray-600 mt-1">
                              {task.description.length > 40 
                                ? `${task.description.substring(0, 40)}...`
                                : task.description
                              }
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="table-cell">
                        <div className="font-medium text-gray-900">{task.client_name}</div>
                      </td>
                      <td className="table-cell">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          {task.category}
                        </span>
                      </td>
                      <td className="table-cell">
                        <div className="flex items-center">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                            <span className="text-blue-600 font-medium text-sm">
                              {task.assignee_name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>{task.assignee_name}</div>
                        </div>
                      </td>
                      <td className="table-cell">
                        <span className={`badge ${status.class}`}>
                          {status.label}
                        </span>
                      </td>
                      <td className="table-cell">
                        <span className={`badge ${priority.class}`}>
                          {priority.label}
                        </span>
                      </td>
                      <td className="table-cell text-gray-600">
                        {formatDate(task.due_date)}
                      </td>
                      <td className="table-cell">
                        <select
                          value={task.status}
                          onChange={(e) => handleStatusChange(task.id, e.target.value)}
                          disabled={updating[task.id]}
                          className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          data-testid={`status-select-${task.id}`}
                        >
                          <option value="pending">Pending</option>
                          <option value="on_hold">On Hold</option>
                          <option value="completed">Completed</option>
                          <option value="overdue">Overdue</option>
                        </select>
                        {updating[task.id] && (
                          <div className="ml-2 inline-block">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{filteredTasks.length}</div>
            <div className="text-sm text-gray-600">Total Shown</div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-600">
              {filteredTasks.filter(t => t.status === 'on_hold').length}
            </div>
            <div className="text-sm text-gray-600">On Hold</div>
          </div>
          <div className="p-3 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">
              {filteredTasks.filter(t => t.status === 'completed').length}
            </div>
            <div className="text-sm text-gray-600">Completed</div>
          </div>
          <div className="p-3 bg-red-50 rounded-lg">
            <div className="text-2xl font-bold text-red-600">
              {filteredTasks.filter(t => t.status === 'overdue').length}
            </div>
            <div className="text-sm text-gray-600">Overdue</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Tasks;