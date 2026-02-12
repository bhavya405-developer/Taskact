import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import TaskDetailModal from './TaskDetailModal';
import EditTaskModal from './EditTaskModal';
import { useAuth } from '../contexts/AuthContext';
import { Eye, Download, Upload, FileSpreadsheet, X, CheckCircle, AlertCircle, ChevronUp, ChevronDown, ChevronsUpDown, Trash2, Lock } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Tasks = ({ tasks, users, onTaskUpdate }) => {
  const { isPartner } = useAuth();
  const [filter, setFilter] = useState('all');
  const [assigneeFilter, setAssigneeFilter] = useState('all');
  const [clientFilter, setClientFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [updating, setUpdating] = useState({});
  const [selectedTask, setSelectedTask] = useState(null);
  const [showTaskDetail, setShowTaskDetail] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [taskToEdit, setTaskToEdit] = useState(null);
  
  // Sorting state - default sort by due_date ascending
  const [sortColumn, setSortColumn] = useState('due_date');
  const [sortDirection, setSortDirection] = useState('asc');
  
  // Bulk import/export states
  const [showImportModal, setShowImportModal] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const fileInputRef = useRef(null);

  // Bulk delete states
  const [showBulkDeleteModal, setShowBulkDeleteModal] = useState(false);
  const [bulkDeleteType, setBulkDeleteType] = useState(null); // 'completed' or 'all'
  const [bulkDeletePassword, setBulkDeletePassword] = useState('');
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState('');
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkDeleteError, setBulkDeleteError] = useState('');

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
    // Find the task to check if it's completed
    const task = tasks.find(t => t.id === taskId);
    if (task && task.status === 'completed') {
      alert('Cannot edit completed tasks. Completed tasks are immutable.');
      return;
    }
    
    setUpdating(prev => ({ ...prev, [taskId]: true }));
    
    try {
      await axios.put(`${API}/tasks/${taskId}`, {
        status: newStatus
      });
      
      await onTaskUpdate();
    } catch (error) {
      console.error('Error updating task status:', error);
      alert(error.response?.data?.detail || 'Failed to update task status');
    } finally {
      setUpdating(prev => ({ ...prev, [taskId]: false }));
    }
  };

  const handleTaskClick = (task) => {
    setSelectedTask(task);
    setShowTaskDetail(true);
  };

  const handleCloseTaskDetail = () => {
    setSelectedTask(null);
    setShowTaskDetail(false);
  };

  const handleEditTask = (task) => {
    setShowTaskDetail(false);
    setTaskToEdit(task);
    setShowEditModal(true);
  };

  const handleCloseEditModal = () => {
    setTaskToEdit(null);
    setShowEditModal(false);
  };

  const handleEditSave = () => {
    // Refresh task list after edit
    if (onTaskUpdate) {
      onTaskUpdate();
    }
  };

  const handleDeleteTask = async (task) => {
    try {
      await axios.delete(`${API}/tasks/${task.id}`);
      handleCloseTaskDetail();
      if (onTaskUpdate) {
        onTaskUpdate();
      }
    } catch (error) {
      console.error('Error deleting task:', error);
      alert(error.response?.data?.detail || 'Failed to delete task');
    }
  };

  // Download template
  const handleDownloadTemplate = async () => {
    try {
      const response = await axios.get(`${API}/tasks/download-template`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'tasks_template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading template:', error);
      alert('Failed to download template. Please try again.');
    }
  };

  // Export tasks
  const handleExportTasks = async () => {
    if (tasks.length === 0) {
      alert('No tasks to export');
      return;
    }
    
    setExporting(true);
    try {
      const response = await axios.get(`${API}/tasks/export`, {
        responseType: 'blob',
        timeout: 30000  // 30 second timeout
      });
      
      // Check if response is an error (JSON) disguised as blob
      const contentType = response.headers['content-type'];
      if (contentType && contentType.includes('application/json')) {
        const text = await response.data.text();
        const errorData = JSON.parse(text);
        throw new Error(errorData.detail || 'Export failed');
      }
      
      // Create blob with explicit type
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const today = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `tasks_export_${today}.xlsx`);
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      
      // Cleanup after a short delay
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (error) {
      console.error('Error exporting tasks:', error);
      // Handle blob error response
      if (error.response?.data instanceof Blob) {
        try {
          const text = await error.response.data.text();
          const errorData = JSON.parse(text);
          alert(errorData.detail || 'Failed to export tasks');
        } catch {
          alert('Failed to export tasks. Please try again.');
        }
      } else if (error.code === 'ECONNABORTED') {
        alert('Export timed out. Please try again.');
      } else {
        alert(error.message || error.response?.data?.detail || 'Failed to export tasks. Please try again.');
      }
    } finally {
      setExporting(false);
    }
  };

  // Import tasks
  const handleImportTasks = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setImporting(true);
    setImportResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/tasks/bulk-import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setImportResult(response.data);
      
      // Refresh tasks list
      await onTaskUpdate();
    } catch (error) {
      console.error('Error importing tasks:', error);
      setImportResult({
        success_count: 0,
        error_count: 1,
        errors: [error.response?.data?.detail || 'Failed to import tasks'],
        created_items: []
      });
    } finally {
      setImporting(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const closeImportModal = () => {
    setShowImportModal(false);
    setImportResult(null);
  };

  // Bulk delete functions
  const openBulkDeleteModal = (type) => {
    setBulkDeleteType(type);
    setBulkDeletePassword('');
    setBulkDeleteConfirm('');
    setBulkDeleteError('');
    setShowBulkDeleteModal(true);
  };

  const closeBulkDeleteModal = () => {
    setShowBulkDeleteModal(false);
    setBulkDeleteType(null);
    setBulkDeletePassword('');
    setBulkDeleteConfirm('');
    setBulkDeleteError('');
  };

  const handleBulkDelete = async () => {
    // Validate confirmation text
    const expectedConfirm = bulkDeleteType === 'completed' ? 'DELETE COMPLETED' : 'DELETE ALL';
    if (bulkDeleteConfirm !== expectedConfirm) {
      setBulkDeleteError(`Please type "${expectedConfirm}" to confirm`);
      return;
    }

    if (!bulkDeletePassword) {
      setBulkDeleteError('Please enter your password');
      return;
    }

    setBulkDeleting(true);
    setBulkDeleteError('');

    try {
      const endpoint = bulkDeleteType === 'completed' 
        ? `${API}/tasks/bulk-delete/completed`
        : `${API}/tasks/bulk-delete/all`;

      const response = await axios.post(endpoint, { password: bulkDeletePassword });
      
      closeBulkDeleteModal();
      alert(response.data.message);
      
      // Refresh tasks
      if (onTaskUpdate) {
        await onTaskUpdate();
      }
    } catch (error) {
      setBulkDeleteError(error.response?.data?.detail || 'Failed to delete tasks. Please check your password.');
    } finally {
      setBulkDeleting(false);
    }
  };

  // Handle column sort
  const handleSort = (column) => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to ascending
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Get sort icon for column header
  const getSortIcon = (column) => {
    if (sortColumn !== column) {
      return <ChevronsUpDown className="w-3 h-3 ml-1 text-gray-400" />;
    }
    return sortDirection === 'asc' 
      ? <ChevronUp className="w-3 h-3 ml-1 text-blue-600" />
      : <ChevronDown className="w-3 h-3 ml-1 text-blue-600" />;
  };

  // Priority order for sorting
  const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 };
  const statusOrder = { overdue: 0, pending: 1, on_hold: 2, completed: 3 };

  const filteredTasks = tasks.filter(task => {
    let matchesStatus;
    if (filter === 'all') {
      matchesStatus = true;
    } else if (filter === 'pending_overdue') {
      matchesStatus = task.status === 'pending' || task.status === 'overdue';
    } else if (filter === 'due_7_days') {
      // Due in next 7 days (pending/overdue tasks with due date within 7 days)
      if (!task.due_date) return false;
      const dueDate = new Date(task.due_date);
      const today = new Date();
      const sevenDaysLater = new Date();
      sevenDaysLater.setDate(today.getDate() + 7);
      matchesStatus = (task.status === 'pending' || task.status === 'overdue') && 
                      dueDate <= sevenDaysLater;
    } else {
      matchesStatus = task.status === filter;
    }
    const matchesAssignee = assigneeFilter === 'all' || task.assignee_id === assigneeFilter;
    const matchesClient = clientFilter === 'all' || (task.client_name && task.client_name.toLowerCase().includes(clientFilter.toLowerCase()));
    const matchesCategory = categoryFilter === 'all' || task.category === categoryFilter;
    return matchesStatus && matchesAssignee && matchesClient && matchesCategory;
  });

  // Sort filtered tasks
  const sortedTasks = [...filteredTasks].sort((a, b) => {
    let aValue, bValue;
    
    switch (sortColumn) {
      case 'title':
        aValue = (a.title || '').toLowerCase();
        bValue = (b.title || '').toLowerCase();
        break;
      case 'client_name':
        aValue = (a.client_name || '').toLowerCase();
        bValue = (b.client_name || '').toLowerCase();
        break;
      case 'category':
        aValue = (a.category || '').toLowerCase();
        bValue = (b.category || '').toLowerCase();
        break;
      case 'assignee_name':
        aValue = (a.assignee_name || '').toLowerCase();
        bValue = (b.assignee_name || '').toLowerCase();
        break;
      case 'status':
        aValue = statusOrder[a.status] ?? 99;
        bValue = statusOrder[b.status] ?? 99;
        break;
      case 'priority':
        aValue = priorityOrder[a.priority] ?? 99;
        bValue = priorityOrder[b.priority] ?? 99;
        break;
      case 'due_date':
        // Handle null/undefined due dates - put them at the end
        aValue = a.due_date ? new Date(a.due_date).getTime() : (sortDirection === 'asc' ? Infinity : -Infinity);
        bValue = b.due_date ? new Date(b.due_date).getTime() : (sortDirection === 'asc' ? Infinity : -Infinity);
        break;
      default:
        aValue = a[sortColumn] || '';
        bValue = b[sortColumn] || '';
    }
    
    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  // Get unique clients and categories for filter options
  const uniqueClients = [...new Set(tasks.map(task => task.client_name).filter(Boolean))].sort();
  const uniqueCategories = [...new Set(tasks.map(task => task.category).filter(Boolean))].sort();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Bulk Import Tasks</h3>
              <button
                onClick={closeImportModal}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {!importResult ? (
              <div className="space-y-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <FileSpreadsheet className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-600 mb-2">Upload Excel or CSV file</p>
                  <p className="text-xs text-gray-500 mb-4">Supported formats: .xlsx, .xls, .csv</p>
                  
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleImportTasks}
                    accept=".xlsx,.xls,.csv"
                    className="hidden"
                    id="task-file-input"
                    data-testid="task-file-input"
                  />
                  
                  <label
                    htmlFor="task-file-input"
                    className={`btn-primary cursor-pointer inline-flex items-center ${importing ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {importing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Importing...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        Select File
                      </>
                    )}
                  </label>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800 font-medium mb-2">Need a template?</p>
                  <button
                    onClick={handleDownloadTemplate}
                    className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
                    data-testid="download-template-modal"
                  >
                    <Download className="w-4 h-4 mr-1" />
                    Download Task Template
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Import Results */}
                <div className={`p-4 rounded-lg ${importResult.success_count > 0 ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                  <div className="flex items-center mb-2">
                    {importResult.success_count > 0 ? (
                      <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
                    )}
                    <span className="font-medium">
                      {importResult.success_count} task(s) imported successfully
                    </span>
                  </div>
                  {importResult.error_count > 0 && (
                    <p className="text-sm text-red-600">
                      {importResult.error_count} error(s) occurred
                    </p>
                  )}
                </div>

                {/* Created Items */}
                {importResult.created_items.length > 0 && (
                  <div className="max-h-32 overflow-y-auto">
                    <p className="text-sm font-medium text-gray-700 mb-2">Created Tasks:</p>
                    <ul className="text-sm text-gray-600 space-y-1">
                      {importResult.created_items.map((item, index) => (
                        <li key={index} className="flex items-center">
                          <CheckCircle className="w-3 h-3 text-green-500 mr-2" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Errors */}
                {importResult.errors.length > 0 && (
                  <div className="max-h-40 overflow-y-auto bg-red-50 rounded-lg p-3">
                    <p className="text-sm font-medium text-red-700 mb-2">Errors:</p>
                    <ul className="text-sm text-red-600 space-y-1">
                      {importResult.errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <button
                  onClick={closeImportModal}
                  className="w-full btn-primary"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bulk Delete Confirmation Modal */}
      {showBulkDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Lock className="w-5 h-5 mr-2 text-red-600" />
                {bulkDeleteType === 'completed' ? 'Clear Completed Tasks' : 'Clear All Tasks'}
              </h3>
              <button
                onClick={closeBulkDeleteModal}
                className="text-gray-400 hover:text-gray-600"
                data-testid="close-bulk-delete-modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Warning */}
              <div className={`p-4 rounded-lg ${bulkDeleteType === 'completed' ? 'bg-orange-50 border border-orange-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-start">
                  <AlertCircle className={`w-5 h-5 mr-3 mt-0.5 ${bulkDeleteType === 'completed' ? 'text-orange-600' : 'text-red-600'}`} />
                  <div>
                    <p className={`font-medium ${bulkDeleteType === 'completed' ? 'text-orange-800' : 'text-red-800'}`}>
                      {bulkDeleteType === 'completed' 
                        ? `This will permanently delete ${tasks.filter(t => t.status === 'completed').length} completed task(s).`
                        : `This will permanently delete ALL ${tasks.length} task(s).`
                      }
                    </p>
                    <p className={`text-sm mt-1 ${bulkDeleteType === 'completed' ? 'text-orange-700' : 'text-red-700'}`}>
                      This action cannot be undone.
                    </p>
                  </div>
                </div>
              </div>

              {/* Password Input */}
              <div>
                <label className="form-label">Enter your password to confirm</label>
                <input
                  type="password"
                  value={bulkDeletePassword}
                  onChange={(e) => setBulkDeletePassword(e.target.value)}
                  className="form-input"
                  placeholder="Your login password"
                  data-testid="bulk-delete-password"
                />
              </div>

              {/* Confirmation Text */}
              <div>
                <label className="form-label">
                  Type <span className="font-mono font-bold text-red-600">
                    {bulkDeleteType === 'completed' ? 'DELETE COMPLETED' : 'DELETE ALL'}
                  </span> to confirm
                </label>
                <input
                  type="text"
                  value={bulkDeleteConfirm}
                  onChange={(e) => setBulkDeleteConfirm(e.target.value)}
                  className="form-input"
                  placeholder={bulkDeleteType === 'completed' ? 'DELETE COMPLETED' : 'DELETE ALL'}
                  data-testid="bulk-delete-confirm"
                />
              </div>

              {/* Error Message */}
              {bulkDeleteError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-700">{bulkDeleteError}</p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={closeBulkDeleteModal}
                  className="flex-1 btn-secondary"
                  disabled={bulkDeleting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkDelete}
                  disabled={bulkDeleting}
                  className={`flex-1 flex items-center justify-center ${
                    bulkDeleteType === 'completed' 
                      ? 'bg-orange-600 hover:bg-orange-700 text-white' 
                      : 'bg-red-600 hover:bg-red-700 text-white'
                  } font-medium py-2 px-4 rounded-lg transition-colors`}
                  data-testid="confirm-bulk-delete"
                >
                  {bulkDeleting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4 mr-2" />
                      {bulkDeleteType === 'completed' ? 'Delete Completed' : 'Delete All'}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Tasks</h2>
          <p className="mt-2 text-gray-600">Manage and track all team tasks</p>
        </div>
        <div className="mt-4 sm:mt-0 flex flex-wrap gap-2">
          {/* Partner-only bulk actions */}
          {isPartner() && (
            <>
              <button
                onClick={handleDownloadTemplate}
                className="btn-secondary flex items-center text-sm"
                data-testid="download-template-btn"
                title="Download Task Template"
              >
                <FileSpreadsheet className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Template</span>
              </button>
              <button
                onClick={() => setShowImportModal(true)}
                className="btn-secondary flex items-center text-sm"
                data-testid="import-tasks-btn"
                title="Import Tasks"
              >
                <Upload className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Import</span>
              </button>
              <button
                onClick={handleExportTasks}
                disabled={exporting || tasks.length === 0}
                className={`btn-secondary flex items-center text-sm ${
                  tasks.length === 0 ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                data-testid="export-tasks-btn"
                title={tasks.length === 0 ? "No tasks to export" : "Export All Tasks"}
              >
                {exporting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-1"></div>
                    <span className="hidden sm:inline">Exporting...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-1" />
                    <span className="hidden sm:inline">Export</span>
                  </>
                )}
              </button>
              <button
                onClick={() => openBulkDeleteModal('completed')}
                className={`btn-secondary flex items-center text-sm ${
                  tasks.filter(t => t.status === 'completed').length === 0 
                    ? 'opacity-50 cursor-not-allowed' 
                    : 'text-orange-600 hover:text-orange-700 border-orange-300 hover:border-orange-400'
                }`}
                data-testid="clear-completed-btn"
                title={tasks.filter(t => t.status === 'completed').length === 0 
                  ? "No completed tasks to clear" 
                  : "Clear All Completed Tasks"}
                disabled={tasks.filter(t => t.status === 'completed').length === 0}
              >
                <Trash2 className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Clear Completed</span>
              </button>
              <button
                onClick={() => openBulkDeleteModal('all')}
                className={`btn-secondary flex items-center text-sm ${
                  tasks.length === 0 
                    ? 'opacity-50 cursor-not-allowed' 
                    : 'text-red-600 hover:text-red-700 border-red-300 hover:border-red-400'
                }`}
                data-testid="clear-all-btn"
                title={tasks.length === 0 ? "No tasks to clear" : "Clear All Tasks"}
                disabled={tasks.length === 0}
              >
                <Trash2 className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Clear All</span>
              </button>
            </>
          )}
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
              <option value="due_7_days">Due in Next 7 Days</option>
              <option value="pending_overdue">Pending + Overdue</option>
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
        {sortedTasks.length === 0 ? (
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
          <>
            {/* Desktop Table View - Hidden on Mobile */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th 
                      className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort('title')}
                      data-testid="sort-title"
                    >
                      <div className="flex items-center">
                        Task {getSortIcon('title')}
                      </div>
                    </th>
                    <th 
                      className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort('client_name')}
                      data-testid="sort-client"
                    >
                      <div className="flex items-center">
                        Client {getSortIcon('client_name')}
                      </div>
                    </th>
                    <th 
                      className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort('category')}
                      data-testid="sort-category"
                    >
                      <div className="flex items-center">
                        Category {getSortIcon('category')}
                      </div>
                    </th>
                    <th 
                      className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort('assignee_name')}
                      data-testid="sort-assignee"
                    >
                      <div className="flex items-center">
                        Assignee {getSortIcon('assignee_name')}
                      </div>
                    </th>
                    <th 
                      className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort('status')}
                      data-testid="sort-status"
                    >
                      <div className="flex items-center">
                        Status {getSortIcon('status')}
                      </div>
                    </th>
                    <th 
                      className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort('priority')}
                      data-testid="sort-priority"
                    >
                      <div className="flex items-center">
                        Priority {getSortIcon('priority')}
                      </div>
                    </th>
                    <th 
                      className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort('due_date')}
                      data-testid="sort-due-date"
                    >
                      <div className="flex items-center">
                        Due Date {getSortIcon('due_date')}
                      </div>
                    </th>
                    <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sortedTasks.map((task) => {
                    const status = getStatusDisplay(task.status);
                    const priority = getPriorityDisplay(task.priority);
                    
                    return (
                      <tr 
                        key={task.id} 
                        className="hover:bg-gray-50 transition-colors cursor-pointer" 
                        data-testid={`task-row-${task.id}`}
                        onClick={() => handleTaskClick(task)}
                      >
                        <td className="px-3 py-2 text-sm">
                          <div className="max-w-[180px]">
                            <div className="font-medium text-gray-900 truncate" title={task.title}>{task.title}</div>
                            {task.description && (
                              <div className="text-xs text-gray-500 truncate" title={task.description}>
                                {task.description}
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-2 py-2 text-sm">
                          <div className="max-w-[120px] truncate font-medium text-gray-900" title={task.client_name}>
                            {task.client_name}
                          </div>
                        </td>
                        <td className="px-2 py-2 text-sm">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 whitespace-nowrap">
                            {task.category}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-sm">
                          <div className="flex items-center max-w-[120px]">
                            <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-1.5 flex-shrink-0">
                              <span className="text-blue-600 font-medium text-xs">
                                {task.assignee_name.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <span className="truncate text-sm" title={task.assignee_name}>{task.assignee_name}</span>
                          </div>
                        </td>
                        <td className="px-2 py-2 text-sm">
                          <span className={`badge text-xs px-1.5 py-0.5 ${status.class}`}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-sm">
                          <span className={`badge text-xs px-1.5 py-0.5 ${priority.class}`}>
                            {priority.label}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-sm text-gray-600 whitespace-nowrap">
                          {formatDate(task.due_date)}
                        </td>
                        <td className="px-2 py-2 text-sm" onClick={(e) => e.stopPropagation()}>
                          <select
                            value={task.status}
                            onChange={(e) => handleStatusChange(task.id, e.target.value)}
                            disabled={updating[task.id] || task.status === 'completed'}
                            className={`text-xs border border-gray-300 rounded px-1.5 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                              task.status === 'completed' ? 'bg-gray-100 cursor-not-allowed' : ''
                            }`}
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

            {/* Mobile Card View - Visible on Mobile */}
            <div className="md:hidden divide-y divide-gray-200">
              {sortedTasks.map((task) => {
                const status = getStatusDisplay(task.status);
                const priority = getPriorityDisplay(task.priority);
                
                return (
                  <div 
                    key={task.id} 
                    className="p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                    data-testid={`mobile-task-${task.id}`}
                    onClick={() => handleTaskClick(task)}
                  >
                    <div className="space-y-3">
                      {/* Task Header */}
                      <div className="flex justify-between items-start">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-gray-900 truncate">{task.title}</h3>
                          {task.description && (
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                              {task.description}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTaskClick(task);
                          }}
                          className="ml-2 p-2 text-gray-400 hover:text-blue-600"
                        >
                          <Eye size={18} />
                        </button>
                      </div>

                      {/* Task Meta */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-500">Client:</span>
                          <span className="text-sm font-medium text-gray-900">{task.client_name}</span>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-500">Category:</span>
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            {task.category}
                          </span>
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-500">Assignee:</span>
                          <div className="flex items-center">
                            <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-2">
                              <span className="text-blue-600 font-medium text-xs">
                                {task.assignee_name.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <span className="text-sm font-medium text-gray-900">{task.assignee_name}</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-500">Due Date:</span>
                          <span className="text-sm text-gray-900">{formatDate(task.due_date)}</span>
                        </div>
                      </div>

                      {/* Status and Priority */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className={`badge ${status.class}`}>
                            {status.label}
                          </span>
                          <span className={`badge ${priority.class}`}>
                            {priority.label}
                          </span>
                        </div>
                      </div>

                      {/* Status Update */}
                      <div className="pt-2" onClick={(e) => e.stopPropagation()}>
                        <select
                          value={task.status}
                          onChange={(e) => handleStatusChange(task.id, e.target.value)}
                          disabled={updating[task.id] || task.status === 'completed'}
                          className={`w-full text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                            task.status === 'completed' ? 'bg-gray-100 cursor-not-allowed' : ''
                          }`}
                          style={{ minHeight: '44px' }}
                          data-testid={`mobile-status-select-${task.id}`}
                        >
                          <option value="pending">Pending</option>
                          <option value="on_hold">On Hold</option>
                          <option value="completed">Completed</option>
                          <option value="overdue">Overdue</option>
                        </select>
                        {updating[task.id] && (
                          <div className="flex items-center justify-center mt-2">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
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

      {/* Task Detail Modal */}
      <TaskDetailModal
        task={selectedTask}
        isOpen={showTaskDetail}
        onClose={handleCloseTaskDetail}
        onEdit={isPartner() ? handleEditTask : null}
        onDelete={isPartner() ? handleDeleteTask : null}
        isPartner={isPartner()}
        onTaskUpdate={onTaskUpdate}
      />

      {/* Edit Task Modal */}
      <EditTaskModal
        task={taskToEdit}
        users={users}
        isOpen={showEditModal}
        onClose={handleCloseEditModal}
        onSave={handleEditSave}
      />
    </div>
  );
};

export default Tasks;