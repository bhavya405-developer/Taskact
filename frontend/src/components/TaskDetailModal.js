import React from 'react';

const TaskDetailModal = ({ task, isOpen, onClose, onEdit }) => {
  if (!isOpen || !task) return null;

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
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const status = getStatusDisplay(task.status);
  const priority = getPriorityDisplay(task.priority);

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

            {/* Created Date */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Created</h3>
              <p className="text-gray-900">{formatDate(task.created_at)}</p>
            </div>
          </div>

          {/* Completion Date (if completed) */}
          {task.completed_at && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Completed</h3>
              <p className="text-gray-900">{formatDate(task.completed_at)}</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          <div>
            <p className="text-xs text-gray-500">
              Last updated: {formatDate(task.updated_at)}
            </p>
          </div>
          <div className="flex space-x-3">
            {onEdit && (
              <button
                onClick={() => onEdit(task)}
                className="btn-secondary"
                data-testid="edit-task-button"
              >
                Edit Task
              </button>
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