import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TaskDetailModal from './TaskDetailModal';
import EditTaskModal from './EditTaskModal';
import { useAuth } from '../contexts/AuthContext';
import { 
  BarChart3, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  Calendar,
  Pause,
  Users,
  Building2,
  User,
  UsersRound
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// StatusCard component with dark mode support
const StatusCard = ({ title, count, status, icon, isDark }) => (
  <div className={`rounded-xl border p-4 transition-all duration-200 hover:shadow-lg ${
    isDark 
      ? 'bg-slate-800 border-slate-700 hover:border-slate-600' 
      : 'bg-white border-gray-100 shadow-sm hover:border-blue-100'
  }`} data-testid={`status-card-${status}`}>
    <div className="flex items-center">
      <div className="flex-shrink-0">
        <div className="w-8 h-8 flex items-center justify-center text-lg">
          {icon}
        </div>
      </div>
      <div className="ml-4">
        <p className={`text-sm font-medium ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>{title}</p>
        <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{count}</p>
      </div>
    </div>
  </div>
);

const Dashboard = ({ users, tasks, onTaskUpdate }) => {
  const { isPartner, user, isSuperAdmin } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState(null);
  const [showTaskDetail, setShowTaskDetail] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [taskToEdit, setTaskToEdit] = useState(null);
  const [showOnlyMyTasks, setShowOnlyMyTasks] = useState(false); // Partner filter for own tasks

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API}/dashboard`);
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading || !dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${isSuperAdmin() ? 'border-indigo-400' : 'border-blue-600'}`}></div>
      </div>
    );
  }

  // Check if super admin for dark theme
  const isDark = isSuperAdmin();

  const { task_counts, recent_tasks, team_stats, overdue_tasks, due_7_days_tasks } = dashboardData;
  
  // Use the new specific task lists from backend (already filtered by role)
  // Apply partner's "show only my tasks" filter if enabled
  const filterByPartner = (taskList) => {
    if (!isPartner() || !showOnlyMyTasks) return taskList || [];
    return (taskList || []).filter(task => task.assignee_id === user?.id);
  };
  
  const overdue_task_list = filterByPartner(overdue_tasks || recent_tasks.filter(task => task.status === 'overdue'));
  const due_7_days_list = filterByPartner(due_7_days_tasks || []);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getStatusDisplay = (status) => {
    const statusConfig = {
      pending: { label: 'Pending', class: 'status-pending' },
      in_progress: { label: 'In Progress', class: 'status-in_progress' },
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

  const handleTaskClick = (task) => {
    setSelectedTask(task);
    setShowTaskDetail(true);
  };

  const handleCloseTaskDetail = () => {
    setShowTaskDetail(false);
    setSelectedTask(null);
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
    // Refresh dashboard data after edit
    fetchDashboardData();
    if (onTaskUpdate) {
      onTaskUpdate();
    }
  };

  const handleDeleteTask = async (task) => {
    try {
      await axios.delete(`${API}/tasks/${task.id}`);
      handleCloseTaskDetail();
      fetchDashboardData();
      if (onTaskUpdate) {
        onTaskUpdate();
      }
    } catch (error) {
      console.error('Error deleting task:', error);
      alert(error.response?.data?.detail || 'Failed to delete task');
    }
  };

  return (
    <div className="space-y-6 md:space-y-8 animate-fade-in">
      {/* Header - Smaller on mobile */}
      <div className="text-center lg:text-left flex items-center justify-center lg:justify-start">
        <BarChart3 size={24} className={`mr-2 md:mr-3 md:w-8 md:h-8 ${isDark ? 'text-indigo-400' : 'text-blue-600'}`} />
        <div>
          <h2 className={`text-xl md:text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Dashboard</h2>
          <p className={`text-sm md:text-base ${isDark ? 'text-slate-400' : 'text-gray-600'}`}>Overview of your team&apos;s productivity</p>
        </div>
      </div>

      {/* Priority Tasks Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Overdue Tasks */}
        <div className={`rounded-lg shadow-sm border ${isDark ? 'bg-slate-800 border-red-900/50' : 'bg-white border-red-200'}`}>
          <div className={`px-6 py-4 border-b ${isDark ? 'border-red-900/50 bg-red-900/30' : 'border-red-200 bg-red-50'}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <AlertCircle size={20} className={isDark ? 'text-red-400 mr-2' : 'text-red-600 mr-2'} />
                <h3 className={`text-lg font-semibold ${isDark ? 'text-red-300' : 'text-red-900'}`} data-testid="overdue-tasks-title">
                  Overdue Tasks ({overdue_task_list.length})
                </h3>
              </div>
              {isPartner() && (
                <button
                  onClick={() => setShowOnlyMyTasks(!showOnlyMyTasks)}
                  className={`p-1.5 rounded-md transition-colors ${
                    isDark 
                      ? showOnlyMyTasks ? 'bg-red-800 text-red-200' : 'bg-red-900/50 text-red-300 hover:bg-red-800'
                      : showOnlyMyTasks ? 'bg-red-200 text-red-800' : 'bg-red-100 text-red-600 hover:bg-red-200'
                  }`}
                  title={showOnlyMyTasks ? "Showing my tasks only - Click to show all" : "Click to show only my tasks"}
                  data-testid="filter-my-tasks-btn"
                >
                  {showOnlyMyTasks ? <User size={16} /> : <UsersRound size={16} />}
                </button>
              )}
            </div>
            {isPartner() && (
              <p className={`text-xs mt-1 ${isDark ? 'text-red-400' : 'text-red-700'}`}>
                {showOnlyMyTasks ? "Showing only your tasks" : "Showing all team members"}
              </p>
            )}
          </div>
          <div className="p-6">
            {overdue_task_list.length === 0 ? (
              <div className={`text-center py-8 ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
                <p>No overdue tasks! 🎉</p>
              </div>
            ) : (
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {overdue_task_list.map((task) => {
                  const priority = getPriorityDisplay(task.priority);
                  
                  return (
                    <div 
                      key={task.id} 
                      className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                        isDark 
                          ? 'border-red-900/50 bg-red-900/20 hover:bg-red-900/30' 
                          : 'border-red-200 bg-red-50 hover:bg-red-100'
                      }`}
                      onClick={() => handleTaskClick(task)}
                      data-testid={`overdue-task-${task.id}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{task.title}</h4>
                          <p className={`text-sm mt-1 ${isDark ? 'text-slate-400' : 'text-gray-600'}`}>
                            {task.client_name ? `Client: ${task.client_name} • ` : ''}Assigned to: {task.assignee_name}
                          </p>
                          <div className="flex items-center space-x-2 mt-2">
                            <span className="badge status-overdue">
                              Overdue
                            </span>
                            <span className={`badge ${priority.class}`}>
                              {priority.label}
                            </span>
                            {task.category && (
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                isDark ? 'bg-slate-700 text-slate-300' : 'bg-gray-100 text-gray-700'
                              }`}>
                                {task.category}
                              </span>
                            )}
                          </div>
                          {task.due_date && (
                            <p className={`text-xs mt-1 font-medium ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                              Due: {new Date(task.due_date).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Due in Next 7 Days */}
        <div className={`rounded-lg shadow-sm border ${isDark ? 'bg-slate-800 border-yellow-900/50' : 'bg-white border-yellow-200'}`}>
          <div className={`px-6 py-4 border-b ${isDark ? 'border-yellow-900/50 bg-yellow-900/30' : 'border-yellow-200 bg-yellow-50'}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Calendar size={20} className={isDark ? 'text-yellow-400 mr-2' : 'text-yellow-600 mr-2'} />
                <h3 className={`text-lg font-semibold ${isDark ? 'text-yellow-300' : 'text-yellow-900'}`} data-testid="due-7-days-title">
                  Due in Next 7 Days ({due_7_days_list.length})
                </h3>
              </div>
              {isPartner() && (
                <button
                  onClick={() => setShowOnlyMyTasks(!showOnlyMyTasks)}
                  className={`p-1.5 rounded-md transition-colors ${
                    isDark 
                      ? showOnlyMyTasks ? 'bg-yellow-800 text-yellow-200' : 'bg-yellow-900/50 text-yellow-300 hover:bg-yellow-800'
                      : showOnlyMyTasks ? 'bg-yellow-200 text-yellow-800' : 'bg-yellow-100 text-yellow-600 hover:bg-yellow-200'
                  }`}
                  title={showOnlyMyTasks ? "Showing my tasks only - Click to show all" : "Click to show only my tasks"}
                  data-testid="filter-my-tasks-btn-2"
                >
                  {showOnlyMyTasks ? <User size={16} /> : <UsersRound size={16} />}
                </button>
              )}
            </div>
            {isPartner() && (
              <p className={`text-xs mt-1 ${isDark ? 'text-yellow-400' : 'text-yellow-700'}`}>
                {showOnlyMyTasks ? "Showing only your tasks" : "Showing all team members"}
              </p>
            )}
          </div>
          <div className="p-6">
            {due_7_days_list.length === 0 ? (
              <div className={`text-center py-8 ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
                <p>No tasks due in next 7 days</p>
              </div>
            ) : (
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {due_7_days_list.map((task) => {
                  const priority = getPriorityDisplay(task.priority);
                  const status = getStatusDisplay(task.status);
                  
                  return (
                    <div 
                      key={task.id} 
                      className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                        isDark 
                          ? 'border-yellow-900/50 bg-yellow-900/20 hover:bg-yellow-900/30' 
                          : 'border-yellow-200 bg-yellow-50 hover:bg-yellow-100'
                      }`}
                      onClick={() => handleTaskClick(task)}
                      data-testid={`due-7-days-task-${task.id}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{task.title}</h4>
                          <p className={`text-sm mt-1 ${isDark ? 'text-slate-400' : 'text-gray-600'}`}>
                            {task.client_name ? `Client: ${task.client_name} • ` : ''}Assigned to: {task.assignee_name}
                          </p>
                          <div className="flex items-center space-x-2 mt-2">
                            <span className={`badge ${status.class}`}>
                              {status.label}
                            </span>
                            <span className={`badge ${priority.class}`}>
                              {priority.label}
                            </span>
                            {task.category && (
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                isDark ? 'bg-slate-700 text-slate-300' : 'bg-gray-100 text-gray-700'
                              }`}>
                                {task.category}
                              </span>
                            )}
                          </div>
                          {task.due_date && (
                            <p className={`text-xs mt-1 font-medium ${isDark ? 'text-yellow-400' : 'text-yellow-700'}`}>
                              Due: {new Date(task.due_date).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <StatusCard
          title="Total Tasks"
          count={task_counts.total}
          status="total"
          icon={<BarChart3 size={20} className={isDark ? 'text-indigo-400' : 'text-blue-600'} />}
          isDark={isDark}
        />
        <StatusCard
          title="Pending"
          count={task_counts.pending}
          status="pending"
          icon={<Clock size={20} className="text-yellow-500" />}
          isDark={isDark}
        />
        <StatusCard
          title="On Hold"
          count={task_counts.on_hold}
          status="on_hold"
          icon={<Pause size={20} className="text-gray-600" />}
        />
        <StatusCard
          title="Completed"
          count={task_counts.completed}
          status="completed"
          icon={<CheckCircle size={20} className="text-green-600" />}
        />
        <StatusCard
          title="Overdue"
          count={task_counts.overdue}
          status="overdue"
          icon={<AlertCircle size={20} className="text-red-600" />}
        />
      </div>

      {/* Team Performance Section - Only for Partners */}
      {isPartner() && team_stats.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-1 gap-8">
          {/* Team Performance */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900" data-testid="team-performance-title">
                Team Performance
              </h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {team_stats.map((member) => (
                  <div key={member.user_id} className="border border-gray-200 rounded-lg p-4 card-hover" data-testid={`team-member-${member.user_id}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">{member.name}</h4>
                        <p className="text-sm text-gray-600 capitalize">{member.role}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-900">
                          {member.completed_tasks}/{member.total_tasks} tasks
                        </div>
                        <div className="text-sm text-gray-500">
                          {member.completion_rate.toFixed(1)}% completion
                        </div>
                      </div>
                    </div>
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${member.completion_rate}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

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

export default Dashboard;