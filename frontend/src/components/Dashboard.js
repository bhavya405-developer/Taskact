import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TaskDetailModal from './TaskDetailModal';
import { useAuth } from '../contexts/AuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ users, tasks }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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
    
    fetchDashboardData();
  }, []);

  if (loading || !dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const { task_counts, recent_tasks, team_stats } = dashboardData;

  const StatusCard = ({ title, count, status, icon }) => (
    <div className={`stats-card animate-fade-in`} data-testid={`status-card-${status}`}>
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 flex items-center justify-center text-lg">
            {icon}
          </div>
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{count}</p>
        </div>
      </div>
    </div>
  );

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

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center lg:text-left">
        <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
        <p className="mt-2 text-gray-600">Overview of your team's task management</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <StatusCard
          title="Total Tasks"
          count={task_counts.total}
          status="total"
          icon="📊"
        />
        <StatusCard
          title="Pending"
          count={task_counts.pending}
          status="pending"
          icon="⏳"
        />
        <StatusCard
          title="In Progress"
          count={task_counts.in_progress}
          status="in_progress"
          icon="🔄"
        />
        <StatusCard
          title="Completed"
          count={task_counts.completed}
          status="completed"
          icon="✅"
        />
        <StatusCard
          title="Overdue"
          count={task_counts.overdue}
          status="overdue"
          icon="⚠️"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Tasks */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900" data-testid="recent-tasks-title">
              Recent Tasks
            </h3>
          </div>
          <div className="p-6">
            {recent_tasks.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>No recent tasks found</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recent_tasks.map((task) => {
                  const status = getStatusDisplay(task.status);
                  const priority = getPriorityDisplay(task.priority);
                  
                  return (
                    <div key={task.id} className="border border-gray-200 rounded-lg p-4 card-hover" data-testid={`recent-task-${task.id}`}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900">{task.title}</h4>
                          <p className="text-sm text-gray-600 mt-1">
                            Client: {task.client_name} • Assigned to: {task.assignee_name}
                          </p>
                          <div className="flex items-center space-x-2 mt-2">
                            <span className={`badge ${status.class}`}>
                              {status.label}
                            </span>
                            <span className={`badge ${priority.class}`}>
                              {priority.label}
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                              {task.category}
                            </span>
                          </div>
                        </div>
                        <div className="text-sm text-gray-500">
                          {formatDate(task.created_at)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Team Performance */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900" data-testid="team-performance-title">
              Team Performance
            </h3>
          </div>
          <div className="p-6">
            {team_stats.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>No team members found</p>
              </div>
            ) : (
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
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;