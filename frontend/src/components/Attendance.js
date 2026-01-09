import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { 
  Clock, MapPin, LogIn, LogOut, Settings, AlertCircle, 
  CheckCircle, Navigation, Calendar, Users, Plus, Trash2, 
  CalendarDays, BookOpen, Download
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Attendance = () => {
  const { user, isPartner } = useAuth();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [locationFetching, setLocationFetching] = useState(false);
  const [todayStatus, setTodayStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [geofenceSettings, setGeofenceSettings] = useState(null);
  const [attendanceRules, setAttendanceRules] = useState(null);
  const [holidays, setHolidays] = useState([]);
  const [showSettings, setShowSettings] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [showHolidays, setShowHolidays] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [currentLocation, setCurrentLocation] = useState(null);
  const [locationError, setLocationError] = useState('');
  
  // Settings form - up to 5 locations
  const [settingsForm, setSettingsForm] = useState({
    enabled: false,
    locations: [],
    radius_meters: 100
  });

  // Rules form
  const [rulesForm, setRulesForm] = useState({
    min_hours_full_day: 8,
    working_days: [0, 1, 2, 3, 4, 5]
  });

  // Holiday form
  const [holidayForm, setHolidayForm] = useState({
    date: '',
    name: '',
    is_paid: true
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const requests = [
        axios.get(`${API}/attendance/today`),
        axios.get(`${API}/attendance/history`),
        axios.get(`${API}/attendance/settings`),
        axios.get(`${API}/attendance/rules`),
        axios.get(`${API}/attendance/holidays?year=${new Date().getFullYear()}`)
      ];
      
      const [todayRes, historyRes, settingsRes, rulesRes, holidaysRes] = await Promise.all(requests);
      
      setTodayStatus(todayRes.data);
      setHistory(historyRes.data);
      setGeofenceSettings(settingsRes.data);
      setAttendanceRules(rulesRes.data);
      setHolidays(holidaysRes.data);
      
      setSettingsForm({
        enabled: settingsRes.data.enabled || false,
        locations: settingsRes.data.locations || [],
        radius_meters: settingsRes.data.radius_meters || 100
      });
      
      setRulesForm({
        min_hours_full_day: rulesRes.data.min_hours_full_day || 8,
        working_days: rulesRes.data.working_days || [0, 1, 2, 3, 4, 5]
      });
    } catch (err) {
      console.error('Error fetching attendance data:', err);
      setError('Failed to load attendance data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getCurrentLocation = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by your browser'));
        return;
      }

      const tryHighAccuracy = () => {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            resolve({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy
            });
          },
          (error) => {
            if (error.code === error.TIMEOUT || error.code === error.POSITION_UNAVAILABLE) {
              tryLowAccuracy();
            } else if (error.code === error.PERMISSION_DENIED) {
              reject(new Error('Location permission denied. Please enable location access in your browser settings.'));
            } else {
              reject(new Error('Failed to get location. Please try again.'));
            }
          },
          { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }  // Force fresh location for attendance
        );
      };

      const tryLowAccuracy = () => {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            resolve({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy
            });
          },
          (error) => {
            switch (error.code) {
              case error.PERMISSION_DENIED:
                reject(new Error('Location permission denied. Please enable location access in your browser settings.'));
                break;
              case error.POSITION_UNAVAILABLE:
                reject(new Error('Location unavailable. Please check your device location settings.'));
                break;
              case error.TIMEOUT:
                reject(new Error('Location request timed out. Please ensure location services are enabled and try again.'));
                break;
              default:
                reject(new Error('Failed to get location. Please try again.'));
            }
          },
          { enableHighAccuracy: false, timeout: 30000, maximumAge: 0 }
        );
      };

      tryHighAccuracy();
    });
  };

  // More lenient location getter for settings (allows cached location, longer timeout)
  const getLocationForSettings = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by your browser'));
        return;
      }

      // Try multiple approaches in sequence
      let attempts = 0;
      const maxAttempts = 3;

      const attemptLocation = (highAccuracy, timeout, maxAge) => {
        attempts++;
        navigator.geolocation.getCurrentPosition(
          (position) => {
            resolve({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy
            });
          },
          (error) => {
            if (error.code === error.PERMISSION_DENIED) {
              reject(new Error('Location permission denied. Please enable location access in your browser settings.'));
              return;
            }
            
            // Try next approach
            if (attempts === 1) {
              // Second attempt: low accuracy, cached allowed
              attemptLocation(false, 30000, 300000);
            } else if (attempts === 2) {
              // Third attempt: any accuracy, longer cache
              attemptLocation(false, 60000, 600000);
            } else {
              reject(new Error('Unable to get location. Please enter coordinates manually or try again.'));
            }
          },
          { enableHighAccuracy: highAccuracy, timeout: timeout, maximumAge: maxAge }
        );
      };

      // First attempt: high accuracy, recent cache allowed
      attemptLocation(true, 15000, 60000);
    });
  };

  const handleClockIn = async () => {
    setError('');
    setSuccess('');
    setActionLoading(true);
    setLocationFetching(true);
    setLocationError('');

    try {
      const location = await getCurrentLocation();
      setLocationFetching(false);
      setCurrentLocation(location);

      const response = await axios.post(`${API}/attendance/clock-in`, {
        latitude: location.latitude,
        longitude: location.longitude,
        device_info: navigator.userAgent
      });

      setSuccess(`Clocked in successfully at ${response.data.address || 'your location'}`);
      await fetchData();
    } catch (err) {
      setLocationFetching(false);
      if (err.message) {
        setLocationError(err.message);
      }
      setError(err.response?.data?.detail || err.message || 'Failed to clock in');
    } finally {
      setActionLoading(false);
      setLocationFetching(false);
    }
  };

  const handleClockOut = async () => {
    setError('');
    setSuccess('');
    setActionLoading(true);
    setLocationFetching(true);
    setLocationError('');

    try {
      const location = await getCurrentLocation();
      setLocationFetching(false);
      setCurrentLocation(location);

      const response = await axios.post(`${API}/attendance/clock-out`, {
        latitude: location.latitude,
        longitude: location.longitude,
        device_info: navigator.userAgent
      });

      setSuccess(`Clocked out successfully. Work duration: ${response.data.work_duration_hours} hours`);
      await fetchData();
    } catch (err) {
      setLocationFetching(false);
      if (err.message) {
        setLocationError(err.message);
      }
      setError(err.response?.data?.detail || err.message || 'Failed to clock out');
    } finally {
      setActionLoading(false);
      setLocationFetching(false);
    }
  };

  const handleSaveSettings = async () => {
    setError('');
    setSuccess('');
    setActionLoading(true);

    try {
      await axios.put(`${API}/attendance/settings`, {
        enabled: settingsForm.enabled,
        locations: settingsForm.locations,
        radius_meters: parseFloat(settingsForm.radius_meters)
      });

      setSuccess('Geofence settings saved successfully');
      await fetchData();
      setShowSettings(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveRules = async () => {
    setError('');
    setSuccess('');
    setActionLoading(true);

    try {
      await axios.put(`${API}/attendance/rules`, rulesForm);
      setSuccess('Attendance rules saved successfully');
      await fetchData();
      setShowRules(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save rules');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddHoliday = async () => {
    if (!holidayForm.date || !holidayForm.name) {
      setError('Please enter date and name for the holiday');
      return;
    }

    setError('');
    setSuccess('');
    setActionLoading(true);

    try {
      await axios.post(`${API}/attendance/holidays`, holidayForm);
      setSuccess('Holiday added successfully');
      setHolidayForm({ date: '', name: '', is_paid: true });
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add holiday');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteHoliday = async (holidayId) => {
    if (!window.confirm('Are you sure you want to delete this holiday?')) return;

    try {
      await axios.delete(`${API}/attendance/holidays/${holidayId}`);
      setSuccess('Holiday deleted successfully');
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete holiday');
    }
  };

  const handleDeleteAttendance = async (attendanceId, type) => {
    if (!window.confirm(`Are you sure you want to delete this ${type === 'clock_in' ? 'clock in' : 'clock out'} record?`)) return;

    try {
      setActionLoading(true);
      await axios.delete(`${API}/attendance/${attendanceId}`);
      setSuccess('Attendance record deleted successfully');
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete attendance record');
    } finally {
      setActionLoading(false);
    }
  };

  const addLocation = async () => {
    if (settingsForm.locations.length >= 5) {
      setError('Maximum 5 locations allowed');
      return;
    }

    setError('');
    setActionLoading(true);
    
    try {
      const location = await getLocationForSettings();
      const newLocation = {
        name: `Office ${settingsForm.locations.length + 1}`,
        latitude: location.latitude,
        longitude: location.longitude,
        address: ''
      };
      setSettingsForm(prev => ({
        ...prev,
        locations: [...prev.locations, newLocation]
      }));
      setSuccess('Location added. Click Save to confirm.');
    } catch (err) {
      setError(err.message || 'Failed to get current location. You can also enter coordinates manually.');
    } finally {
      setActionLoading(false);
    }
  };

  const removeLocation = (index) => {
    setSettingsForm(prev => ({
      ...prev,
      locations: prev.locations.filter((_, i) => i !== index)
    }));
  };

  const updateLocation = (index, field, value) => {
    setSettingsForm(prev => ({
      ...prev,
      locations: prev.locations.map((loc, i) => 
        i === index ? { ...loc, [field]: value } : loc
      )
    }));
  };

  const fetchReport = async () => {
    try {
      const response = await axios.get(`${API}/attendance/report`);
      setReport(response.data);
      setShowReport(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load report');
    }
  };

  const downloadReport = async () => {
    try {
      setActionLoading(true);
      setError('');
      
      // Get the auth token
      const token = localStorage.getItem('token');
      
      const response = await fetch(`${API}/attendance/report/export`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to download report');
      }
      
      // Get blob from response
      const blob = await response.blob();
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Get filename from header or generate one
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'Attendance_Report.xlsx';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setSuccess('Report downloaded successfully');
    } catch (err) {
      console.error('Download error:', err);
      setError(err.message || 'Failed to download report');
    } finally {
      setActionLoading(false);
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleDateString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  const toggleWorkingDay = (dayIndex) => {
    setRulesForm(prev => ({
      ...prev,
      working_days: prev.working_days.includes(dayIndex)
        ? prev.working_days.filter(d => d !== dayIndex)
        : [...prev.working_days, dayIndex].sort()
    }));
  };

  // Group history by date
  const groupedHistory = history.reduce((acc, record) => {
    const date = formatDate(record.timestamp);
    if (!acc[date]) {
      acc[date] = { clock_in: null, clock_out: null };
    }
    if (record.type === 'clock_in') {
      acc[date].clock_in = record;
    } else {
      acc[date].clock_out = record;
    }
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Attendance</h2>
          <p className="mt-2 text-gray-600">Track your daily attendance with GPS</p>
        </div>
        {isPartner() && (
          <div className="mt-4 sm:mt-0 flex flex-wrap gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="btn-secondary flex items-center text-sm"
              data-testid="settings-btn"
            >
              <Settings className="w-4 h-4 mr-1" />
              Geofence
            </button>
            <button
              onClick={() => setShowRules(!showRules)}
              className="btn-secondary flex items-center text-sm"
              data-testid="rules-btn"
            >
              <BookOpen className="w-4 h-4 mr-1" />
              Rules
            </button>
            <button
              onClick={() => setShowHolidays(!showHolidays)}
              className="btn-secondary flex items-center text-sm"
              data-testid="holidays-btn"
            >
              <CalendarDays className="w-4 h-4 mr-1" />
              Holidays
            </button>
            <button
              onClick={fetchReport}
              className="btn-secondary flex items-center text-sm"
              data-testid="report-btn"
            >
              <Calendar className="w-4 h-4 mr-1" />
              Report
            </button>
          </div>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5" />
          <div>
            <p className="text-red-800">{error}</p>
            {locationError && <p className="text-red-600 text-sm mt-1">{locationError}</p>}
          </div>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start">
          <CheckCircle className="w-5 h-5 text-green-600 mr-3 mt-0.5" />
          <p className="text-green-800">{success}</p>
        </div>
      )}

      {/* Geofence Settings Panel (Partners only) */}
      {showSettings && isPartner() && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Settings className="w-5 h-5 mr-2" />
            Geofence Settings (Up to 5 Locations)
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="geofence-enabled"
                checked={settingsForm.enabled}
                onChange={(e) => setSettingsForm(prev => ({ ...prev, enabled: e.target.checked }))}
                className="h-4 w-4 text-blue-600 rounded border-gray-300"
                data-testid="geofence-enabled"
              />
              <label htmlFor="geofence-enabled" className="ml-2 text-sm text-gray-700">
                Enable Geofence Restriction (Users must be within radius of any location to clock in)
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="w-48">
                <label className="form-label">Radius (meters)</label>
                <input
                  type="number"
                  value={settingsForm.radius_meters}
                  onChange={(e) => setSettingsForm(prev => ({ ...prev, radius_meters: e.target.value }))}
                  className="form-input"
                  placeholder="100"
                  data-testid="radius-meters"
                />
              </div>
              <button
                onClick={addLocation}
                disabled={settingsForm.locations.length >= 5 || actionLoading}
                className="btn-secondary flex items-center mt-6"
                data-testid="add-location"
              >
                {actionLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                    Getting Location...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Current Location
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  if (settingsForm.locations.length >= 5) {
                    setError('Maximum 5 locations allowed');
                    return;
                  }
                  setSettingsForm(prev => ({
                    ...prev,
                    locations: [...prev.locations, {
                      name: `Office ${prev.locations.length + 1}`,
                      latitude: 0,
                      longitude: 0,
                      address: ''
                    }]
                  }));
                  setSuccess('Location added. Please enter coordinates manually.');
                }}
                disabled={settingsForm.locations.length >= 5}
                className="btn-secondary flex items-center mt-6 text-sm"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Manually
              </button>
            </div>

            {/* Location List */}
            <div className="space-y-3">
              {settingsForm.locations.map((loc, index) => (
                <div key={index} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-3">
                    <input
                      type="text"
                      value={loc.name}
                      onChange={(e) => updateLocation(index, 'name', e.target.value)}
                      className="form-input text-sm"
                      placeholder="Location Name"
                    />
                    <input
                      type="number"
                      step="0.000001"
                      value={loc.latitude}
                      onChange={(e) => updateLocation(index, 'latitude', parseFloat(e.target.value))}
                      className="form-input text-sm"
                      placeholder="Latitude"
                    />
                    <input
                      type="number"
                      step="0.000001"
                      value={loc.longitude}
                      onChange={(e) => updateLocation(index, 'longitude', parseFloat(e.target.value))}
                      className="form-input text-sm"
                      placeholder="Longitude"
                    />
                    <div className="flex items-center">
                      <span className="text-xs text-gray-500 truncate flex-1">{loc.address || 'No address'}</span>
                      <button
                        onClick={() => removeLocation(index)}
                        className="ml-2 text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {settingsForm.locations.length === 0 && (
                <p className="text-gray-500 text-sm">No locations added. Click "Add Current Location" to add office locations.</p>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleSaveSettings}
                disabled={actionLoading}
                className="btn-primary"
                data-testid="save-settings"
              >
                {actionLoading ? 'Saving...' : 'Save Settings'}
              </button>
              <button onClick={() => setShowSettings(false)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Attendance Rules Panel (Partners only) */}
      {showRules && isPartner() && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <BookOpen className="w-5 h-5 mr-2" />
            Attendance Rules
          </h3>
          
          <div className="space-y-4">
            <div>
              <label className="form-label">Minimum Hours for Full Day</label>
              <input
                type="number"
                step="0.5"
                value={rulesForm.min_hours_full_day}
                onChange={(e) => setRulesForm(prev => ({ ...prev, min_hours_full_day: parseFloat(e.target.value) }))}
                className="form-input w-32"
                data-testid="min-hours"
              />
              <p className="text-xs text-gray-500 mt-1">Hours below this will be counted as half day</p>
            </div>

            <div>
              <label className="form-label">Working Days</label>
              <div className="flex flex-wrap gap-2 mt-2">
                {dayNames.map((day, index) => (
                  <button
                    key={day}
                    onClick={() => toggleWorkingDay(index)}
                    className={`px-3 py-1 rounded-full text-sm ${
                      rulesForm.working_days.includes(index)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {day.substring(0, 3)}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">Selected days are working days. Unselected days are weekly off.</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleSaveRules}
                disabled={actionLoading}
                className="btn-primary"
              >
                {actionLoading ? 'Saving...' : 'Save Rules'}
              </button>
              <button onClick={() => setShowRules(false)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Holidays Panel (Partners only) */}
      {showHolidays && isPartner() && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <CalendarDays className="w-5 h-5 mr-2" />
            Office Holidays (Paid)
          </h3>
          
          <div className="space-y-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="form-label">Date</label>
                <input
                  type="date"
                  value={holidayForm.date}
                  onChange={(e) => setHolidayForm(prev => ({ ...prev, date: e.target.value }))}
                  className="form-input"
                  data-testid="holiday-date"
                />
              </div>
              <div className="flex-1 min-w-48">
                <label className="form-label">Holiday Name</label>
                <input
                  type="text"
                  value={holidayForm.name}
                  onChange={(e) => setHolidayForm(prev => ({ ...prev, name: e.target.value }))}
                  className="form-input"
                  placeholder="e.g., Diwali"
                  data-testid="holiday-name"
                />
              </div>
              <button
                onClick={handleAddHoliday}
                disabled={actionLoading}
                className="btn-primary flex items-center"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Holiday
              </button>
            </div>

            {/* Holiday List */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Date</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Holiday</th>
                    <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {holidays.map((holiday) => (
                    <tr key={holiday.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm text-gray-900">{holiday.date}</td>
                      <td className="px-4 py-2 text-sm text-gray-900">{holiday.name}</td>
                      <td className="px-4 py-2 text-center">
                        <button
                          onClick={() => handleDeleteHoliday(holiday.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {holidays.length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-4 py-4 text-center text-gray-500">No holidays added</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <button onClick={() => setShowHolidays(false)} className="btn-secondary">Close</button>
          </div>
        </div>
      )}

      {/* Monthly Report Panel (Partners only) */}
      {showReport && report && isPartner() && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Users className="w-5 h-5 mr-2" />
              Attendance Report - {report.month}/{report.year}
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={downloadReport}
                disabled={actionLoading}
                className="btn-primary flex items-center text-sm"
                data-testid="download-report-btn"
              >
                <Download className="w-4 h-4 mr-1" />
                {actionLoading ? 'Downloading...' : 'Download Excel'}
              </button>
              <button onClick={() => setShowReport(false)} className="text-gray-400 hover:text-gray-600 text-2xl">
                ×
              </button>
            </div>
          </div>

          {/* Summary */}
          {report.summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="text-xs text-gray-500">Working Days</p>
                <p className="text-xl font-bold text-gray-900">{report.summary.total_working_days}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Weekly Offs (Sundays)</p>
                <p className="text-xl font-bold text-gray-900">{report.summary.total_sundays}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Holidays</p>
                <p className="text-xl font-bold text-gray-900">{report.summary.total_holidays}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Min Hours (Full Day)</p>
                <p className="text-xl font-bold text-gray-900">{report.summary.min_hours_full_day}h</p>
              </div>
            </div>
          )}
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Name</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">Dept</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">Full Days</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">Half Days</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">Effective</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">Absent</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">Total Hrs</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">Avg Hrs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {report.report.map((row) => (
                  <tr key={row.user_id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-sm font-medium text-gray-900">{row.user_name}</td>
                    <td className="px-3 py-2 text-xs text-gray-600">{row.department || '-'}</td>
                    <td className="px-3 py-2 text-sm text-center text-green-600 font-medium">{row.full_days}</td>
                    <td className="px-3 py-2 text-sm text-center text-yellow-600 font-medium">{row.half_days}</td>
                    <td className="px-3 py-2 text-sm text-center text-blue-600 font-bold">{row.effective_days}</td>
                    <td className="px-3 py-2 text-sm text-center text-red-600 font-medium">{row.absent_days}</td>
                    <td className="px-3 py-2 text-sm text-center text-gray-900">{row.total_hours}</td>
                    <td className="px-3 py-2 text-sm text-center text-gray-900">{row.average_hours_per_day}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Holidays in month */}
          {report.summary?.holidays?.length > 0 && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm font-medium text-blue-800 mb-1">Holidays this month:</p>
              <div className="flex flex-wrap gap-2">
                {report.summary.holidays.map((h, i) => (
                  <span key={i} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    {h.date}: {h.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Today's Status Card */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Clock className="w-5 h-5 mr-2" />
          Today's Status
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Clock In Status */}
          <div className={`p-4 rounded-lg ${todayStatus?.clock_in ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Clock In</span>
              {todayStatus?.clock_in && <CheckCircle className="w-5 h-5 text-green-600" />}
            </div>
            {todayStatus?.clock_in ? (
              <>
                <p className="text-2xl font-bold text-green-700">{formatTime(todayStatus.clock_in.timestamp)}</p>
                {todayStatus.clock_in.address && (
                  <p className="text-xs text-gray-600 mt-2 flex items-start">
                    <MapPin className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                    <span className="line-clamp-2">{todayStatus.clock_in.address}</span>
                  </p>
                )}
              </>
            ) : (
              <p className="text-gray-500">Not clocked in</p>
            )}
          </div>

          {/* Clock Out Status */}
          <div className={`p-4 rounded-lg ${todayStatus?.clock_out ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50 border border-gray-200'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Clock Out</span>
              {todayStatus?.clock_out && <CheckCircle className="w-5 h-5 text-blue-600" />}
            </div>
            {todayStatus?.clock_out ? (
              <>
                <p className="text-2xl font-bold text-blue-700">{formatTime(todayStatus.clock_out.timestamp)}</p>
                {todayStatus.clock_out.address && (
                  <p className="text-xs text-gray-600 mt-2 flex items-start">
                    <MapPin className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                    <span className="line-clamp-2">{todayStatus.clock_out.address}</span>
                  </p>
                )}
              </>
            ) : (
              <p className="text-gray-500">Not clocked out</p>
            )}
          </div>

          {/* Work Duration */}
          <div className="p-4 rounded-lg bg-purple-50 border border-purple-200">
            <span className="text-sm font-medium text-gray-700">Work Duration</span>
            <p className="text-2xl font-bold text-purple-700 mt-2">
              {todayStatus?.work_duration_hours 
                ? `${todayStatus.work_duration_hours} hrs` 
                : todayStatus?.is_clocked_in 
                  ? 'In progress...' 
                  : '-'}
            </p>
            {todayStatus?.work_duration_hours && attendanceRules && (
              <p className={`text-xs mt-1 ${todayStatus.work_duration_hours >= attendanceRules.min_hours_full_day ? 'text-green-600' : 'text-yellow-600'}`}>
                {todayStatus.work_duration_hours >= attendanceRules.min_hours_full_day ? '✓ Full Day' : '½ Half Day'}
              </p>
            )}
          </div>
        </div>

        {/* Clock In/Out Buttons */}
        <div className="mt-6 flex flex-col sm:flex-row gap-4">
          {!todayStatus?.clock_in && (
            <button
              onClick={handleClockIn}
              disabled={actionLoading}
              className="btn-primary flex items-center justify-center flex-1 py-3"
              data-testid="clock-in-btn"
            >
              {actionLoading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  {locationFetching ? 'Getting location...' : 'Clocking in...'}
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5 mr-2" />
                  Clock In
                </>
              )}
            </button>
          )}

          {todayStatus?.is_clocked_in && !todayStatus?.clock_out && (
            <button
              onClick={handleClockOut}
              disabled={actionLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg flex items-center justify-center flex-1 transition-colors"
              data-testid="clock-out-btn"
            >
              {actionLoading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  {locationFetching ? 'Getting location...' : 'Clocking out...'}
                </>
              ) : (
                <>
                  <LogOut className="w-5 h-5 mr-2" />
                  Clock Out
                </>
              )}
            </button>
          )}

          {todayStatus?.clock_in && todayStatus?.clock_out && (
            <div className="flex-1 text-center p-3 bg-gray-100 rounded-lg text-gray-600">
              <CheckCircle className="w-5 h-5 inline mr-2" />
              Attendance complete for today
            </div>
          )}
        </div>

        {/* Geofence Info - Only show to partners */}
        {isPartner() && geofenceSettings?.enabled && geofenceSettings?.locations?.length > 0 && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800 flex items-center">
              <MapPin className="w-4 h-4 mr-2" />
              Geofence enabled: Users must be within {geofenceSettings.radius_meters}m of any office location to clock in.
            </p>
            <p className="text-xs text-amber-700 mt-1">
              Locations: {geofenceSettings.locations.map(l => l.name).join(', ')}
            </p>
          </div>
        )}

        {/* Location tip */}
        {!todayStatus?.clock_in && !todayStatus?.clock_out && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800 flex items-center">
              <Navigation className="w-4 h-4 mr-2" />
              Tip: Please ensure location services are enabled in your browser for accurate attendance tracking.
            </p>
          </div>
        )}
      </div>

      {/* Attendance History */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Calendar className="w-5 h-5 mr-2" />
          Attendance History
        </h3>

        {Object.keys(groupedHistory).length === 0 ? (
          <p className="text-gray-500 text-center py-8">No attendance records found</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Date</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Clock In</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Clock Out</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Duration</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Type</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Location</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {Object.entries(groupedHistory).map(([date, records]) => {
                  let duration = '-';
                  let dayType = '-';
                  if (records.clock_in && records.clock_out) {
                    const inTime = new Date(records.clock_in.timestamp);
                    const outTime = new Date(records.clock_out.timestamp);
                    const hours = ((outTime - inTime) / (1000 * 60 * 60)).toFixed(2);
                    duration = `${hours} hrs`;
                    dayType = parseFloat(hours) >= (attendanceRules?.min_hours_full_day || 8) ? 'Full' : 'Half';
                  }

                  return (
                    <tr key={date} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{date}</td>
                      <td className="px-4 py-3 text-sm text-center text-green-600">
                        {records.clock_in ? formatTime(records.clock_in.timestamp) : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-center text-blue-600">
                        {records.clock_out ? formatTime(records.clock_out.timestamp) : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-center text-gray-900">{duration}</td>
                      <td className="px-4 py-3 text-sm text-center">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          dayType === 'Full' ? 'bg-green-100 text-green-800' : 
                          dayType === 'Half' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {dayType}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600 max-w-xs truncate" title={records.clock_in?.address}>
                        {records.clock_in?.address ? (
                          <span className="flex items-center">
                            <MapPin className="w-3 h-3 mr-1 flex-shrink-0" />
                            <span className="truncate">{records.clock_in.address}</span>
                          </span>
                        ) : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Attendance;
