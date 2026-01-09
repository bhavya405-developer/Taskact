import React from 'react';
import { Clock, History, Trash2 } from 'lucide-react';

const TaskDetailModal = ({ task, isOpen, onClose, onEdit, onDelete }) => {
  if (!isOpen || !task) return null;

  const handleDelete = () => {
    if (onDelete) {
      onDelete(task);
    }
  };

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
    if (!dateString) return 'Not set';
    return new Date(dateString).toLocaleDateString('en-IN', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Format datetime to IST display
  const formatDateTimeIST = (dateString) => {
    if (!dateString) return 'Not set';
    const date = new Date(dateString);
    return date.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    }) + ' IST';
  };

  const status = getStatusDisplay(task.status);
  const priority = getPriorityDisplay(task.priority);

  // Get status history or create default from task data
  const statusHistory = task.status_history || [];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="task-detail-modal"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-start">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900">{task.title}</h2>
            <div className="flex items-center space-x-2 mt-2">
              <span className={`badge ${status.class}`}>
                {status.label}
              </span>
              <span className={`badge ${priority.class}`}>
                {priority.label}
              </span>
              {task.category && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                  {task.category}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
            data-testid="close-modal"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Description */}
          {task.description && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
              <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">{task.description}</p>
            </div>
          )}

          {/* Task Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Client Information */}
            {task.client_name && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Client</h3>
                <p className="text-gray-900 font-medium">{task.client_name}</p>
              </div>
            )}

            {/* Category */}
            {task.category && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Category</h3>
                <p className="text-gray-900">{task.category}</p>
              </div>
            )}

            {/* Assignee */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Assigned To</h3>
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                  <span className="text-blue-600 font-medium text-sm">
                    {task.assignee_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span className="text-gray-900">{task.assignee_name}</span>
              </div>
            </div>

            {/* Creator */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Created By</h3>
              <div className="flex items-center">
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                  <span className="text-green-600 font-medium text-sm">
                    {task.creator_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span className="text-gray-900">{task.creator_name}</span>
              </div>
            </div>

            {/* Due Date */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Due Date</h3>
              <p className="text-gray-900">{formatDate(task.due_date)}</p>
            </div>

            {/* Created Date with IST */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Created At (IST)</h3>
              <p className="text-gray-900">{formatDateTimeIST(task.created_at)}</p>
            </div>
          </div>

          {/* Completion Date (if completed) */}
          {task.completed_at && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-green-800 mb-1">Completed At (IST)</h3>
              <p className="text-green-900 font-medium">{formatDateTimeIST(task.completed_at)}</p>
            </div>
          )}

          {/* Status History Timeline */}
          {statusHistory.length > 0 && (
            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                <History className="w-4 h-4 mr-2" />
                Status History (IST)
              </h3>
              <div className="relative">
                <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-gray-200"></div>
                <div className="space-y-4">
                  {statusHistory.slice().reverse().map((entry, index) => {
                    const entryStatus = getStatusDisplay(entry.status);
                    return (
                      <div key={index} className="relative pl-8">
                        <div className={`absolute left-0 w-6 h-6 rounded-full flex items-center justify-center ${
                          entry.action === 'created' ? 'bg-blue-100' : 
                          entry.status === 'completed' ? 'bg-green-100' : 
                          entry.status === 'overdue' ? 'bg-red-100' : 'bg-gray-100'
                        }`}>
                          <Clock className={`w-3 h-3 ${
                            entry.action === 'created' ? 'text-blue-600' : 
                            entry.status === 'completed' ? 'text-green-600' : 
                            entry.status === 'overdue' ? 'text-red-600' : 'text-gray-600'
                          }`} />
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="flex items-center justify-between">
                            <span className={`badge text-xs ${entryStatus.class}`}>
                              {entry.action === 'created' ? 'Created' : entryStatus.label}
                            </span>
                            <span className="text-xs text-gray-500">
                              {entry.changed_at_ist || formatDateTimeIST(entry.changed_at)}
                            </span>
                          </div>
                          <p className="text-xs text-gray-600 mt-1">
                            {entry.action === 'created' 
                              ? `Task created by ${entry.changed_by}`
                              : `Changed to ${entryStatus.label} by ${entry.changed_by}`
                            }
                            {entry.previous_status && entry.action !== 'created' && (
                              <span className="text-gray-400"> (from {getStatusDisplay(entry.previous_status).label})</span>
                            )}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          <div>
            <p className="text-xs text-gray-500">
              Last updated: {formatDateTimeIST(task.updated_at)}
            </p>
          </div>
          <div className="flex items-center space-x-3">
            {onEdit && task.status !== 'completed' && (
              <button
                onClick={() => onEdit(task)}
                className="btn-secondary"
                data-testid="edit-task-button"
              >
                Edit Task
              </button>
            )}
            {onDelete && task.status !== 'completed' && (
              <button
                onClick={handleDelete}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete Task"
                data-testid="delete-task-button"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            )}
            {task.status === 'completed' && (
              <div className="text-sm text-gray-500 italic">
                ✓ This task is completed and cannot be edited
              </div>
            )}
            <button
              onClick={onClose}
              className="btn-primary"
              data-testid="close-button"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskDetailModal;
