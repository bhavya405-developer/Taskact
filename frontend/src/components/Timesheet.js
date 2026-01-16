import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { 
  Clock, 
  Calendar, 
  Download, 
  Users, 
  ChevronLeft, 
  ChevronRight,
  FileSpreadsheet,
  Timer,
  CheckCircle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Timesheet = ({ users }) => {
  const { user, isPartner } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState('weekly');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [timesheetData, setTimesheetData] = useState(null);
  const [teamData, setTeamData] = useState(null);
  const [viewMode, setViewMode] = useState('personal'); // personal or team (for partners)
  const [exporting, setExporting] = useState(false);

  const fetchTimesheet = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      if (viewMode === 'team' && isPartner()) {
        const response = await axios.get(`${API}/timesheet/team`, {
          params: { period, date: selectedDate }
        });
        setTeamData(response.data);
        setTimesheetData(null);
      } else {
        const params = { period, date: selectedDate };
        if (selectedUserId && isPartner()) {
          params.user_id = selectedUserId;
        }
        const response = await axios.get(`${API}/timesheet`, { params });
        setTimesheetData(response.data);
        setTeamData(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load timesheet');
    } finally {
      setLoading(false);
    }
  }, [period, selectedDate, selectedUserId, viewMode, isPartner]);

  useEffect(() => {
    fetchTimesheet();
  }, [fetchTimesheet]);

  const handleExport = async () => {
    try {
      setExporting(true);
      let url, filename;

      if (viewMode === 'team' && isPartner()) {
        url = `${API}/timesheet/team/export?period=${period}&date=${selectedDate}`;
        filename = `Team_Timesheet_${period}.xlsx`;
      } else {
        const params = new URLSearchParams({ period, date: selectedDate });
        if (selectedUserId && isPartner()) {
          params.append('user_id', selectedUserId);
        }
        url = `${API}/timesheet/export?${params.toString()}`;
        filename = `Timesheet_${period}.xlsx`;
      }

      const response = await axios.get(url, { responseType: 'blob' });
      
      const downloadUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      setError('Failed to export timesheet');
    } finally {
      setExporting(false);
    }
  };

  const navigateDate = (direction) => {
    const current = new Date(selectedDate);
    let newDate;

    if (period === 'daily') {
      newDate = new Date(current.setDate(current.getDate() + direction));
    } else if (period === 'weekly') {
      newDate = new Date(current.setDate(current.getDate() + (direction * 7)));
    } else {
      newDate = new Date(current.setMonth(current.getMonth() + direction));
    }

    setSelectedDate(newDate.toISOString().split('T')[0]);
  };

  const formatHours = (hours) => {
    if (!hours) return '0h';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Timesheet</h2>
          <p className="mt-2 text-gray-600">Track time spent on completed tasks</p>
        </div>
        <div className="mt-4 sm:mt-0">
          <button
            onClick={handleExport}
            disabled={exporting}
            className="btn-primary flex items-center"
            data-testid="export-timesheet-btn"
          >
            {exporting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Exporting...
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2" />
                Export Excel
              </>
            )}
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex flex-wrap gap-4 items-center">
          {/* View Mode Toggle (Partners only) */}
          {isPartner() && (
            <div className="flex rounded-lg border border-gray-300 overflow-hidden">
              <button
                onClick={() => setViewMode('personal')}
                className={`px-4 py-2 text-sm font-medium ${
                  viewMode === 'personal' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                data-testid="personal-view-btn"
              >
                <Clock className="w-4 h-4 inline mr-1" />
                Personal
              </button>
              <button
                onClick={() => setViewMode('team')}
                className={`px-4 py-2 text-sm font-medium ${
                  viewMode === 'team' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                data-testid="team-view-btn"
              >
                <Users className="w-4 h-4 inline mr-1" />
                Team
              </button>
            </div>
          )}

          {/* Period Selection */}
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="form-input w-auto"
            data-testid="period-select"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>

          {/* User Selection (Partners viewing personal) */}
          {isPartner() && viewMode === 'personal' && (
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              className="form-input w-auto"
              data-testid="user-select"
            >
              <option value="">My Timesheet</option>
              {users.map(u => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          )}

          {/* Date Navigation */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => navigateDate(-1)}
              className="p-2 hover:bg-gray-100 rounded-lg"
              data-testid="prev-period-btn"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="form-input w-auto"
              data-testid="date-input"
            />
            <button
              onClick={() => navigateDate(1)}
              className="p-2 hover:bg-gray-100 rounded-lg"
              data-testid="next-period-btn"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Team View */}
      {viewMode === 'team' && teamData && (
        <div className="space-y-6">
          {/* Team Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Calendar className="w-6 h-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Period</p>
                  <p className="text-lg font-semibold text-gray-900">{teamData.period_label}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-3 bg-green-100 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Tasks</p>
                  <p className="text-lg font-semibold text-gray-900">{teamData.grand_total_tasks}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Timer className="w-6 h-6 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Hours</p>
                  <p className="text-lg font-semibold text-gray-900">{formatHours(teamData.grand_total_hours)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Team Table */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Team Summary</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Employee</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Department</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Tasks</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Total Hours</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Avg/Task</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {teamData.team_summary.map((member) => (
                    <tr key={member.user_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                            <span className="text-blue-600 font-medium text-sm">
                              {member.user_name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <span className="font-medium text-gray-900">{member.user_name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-gray-600">{member.department}</td>
                      <td className="px-6 py-4 text-center">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          {member.tasks_completed}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center font-medium text-gray-900">
                        {formatHours(member.total_hours)}
                      </td>
                      <td className="px-6 py-4 text-center text-gray-600">
                        {formatHours(member.avg_hours_per_task)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Personal View */}
      {viewMode === 'personal' && timesheetData && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Calendar className="w-6 h-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Period</p>
                  <p className="text-lg font-semibold text-gray-900">{timesheetData.period_label}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-3 bg-indigo-100 rounded-lg">
                  <Users className="w-6 h-6 text-indigo-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Employee</p>
                  <p className="text-lg font-semibold text-gray-900">{timesheetData.user_name}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-3 bg-green-100 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Tasks Completed</p>
                  <p className="text-lg font-semibold text-gray-900">{timesheetData.total_tasks}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Timer className="w-6 h-6 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Hours</p>
                  <p className="text-lg font-semibold text-gray-900">{formatHours(timesheetData.total_hours)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Daily Summary */}
          {Object.keys(timesheetData.daily_summary).length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Breakdown</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-7 gap-3">
                {Object.entries(timesheetData.daily_summary).map(([date, data]) => (
                  <div key={date} className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-xs text-gray-500">{new Date(date).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric' })}</p>
                    <p className="text-lg font-semibold text-gray-900">{formatHours(data.hours)}</p>
                    <p className="text-xs text-gray-500">{data.tasks} task{data.tasks !== 1 ? 's' : ''}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Task Entries */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Completed Tasks</h3>
            </div>
            {timesheetData.entries.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <FileSpreadsheet className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No completed tasks in this period</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Task</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Client</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Category</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Est.</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Actual</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {timesheetData.entries.map((entry) => (
                      <tr key={entry.task_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{entry.completed_date}</p>
                            <p className="text-xs text-gray-500">{entry.completed_time}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <p className="text-sm font-medium text-gray-900">{entry.title}</p>
                          {entry.description && (
                            <p className="text-xs text-gray-500 truncate max-w-xs">{entry.description}</p>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{entry.client_name}</td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                            {entry.category}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center text-sm text-gray-500">
                          {entry.estimated_hours ? formatHours(entry.estimated_hours) : '-'}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {formatHours(entry.actual_hours)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Timesheet;
