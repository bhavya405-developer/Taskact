import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { 
  Clock, MapPin, LogIn, LogOut, Settings, AlertCircle, 
  CheckCircle, Navigation, Calendar, Users, ChevronDown, ChevronUp 
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Attendance = () => {
  const { user, isPartner } = useAuth();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [todayStatus, setTodayStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [geofenceSettings, setGeofenceSettings] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [currentLocation, setCurrentLocation] = useState(null);
  const [locationError, setLocationError] = useState('');
  
  // Settings form
  const [settingsForm, setSettingsForm] = useState({
    enabled: false,
    office_latitude: '',
    office_longitude: '',
    radius_meters: 100
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [todayRes, historyRes, settingsRes] = await Promise.all([
        axios.get(`${API}/attendance/today`),
        axios.get(`${API}/attendance/history`),
        axios.get(`${API}/attendance/settings`)
      ]);
      
      setTodayStatus(todayRes.data);
      setHistory(historyRes.data);
      setGeofenceSettings(settingsRes.data);
      setSettingsForm({
        enabled: settingsRes.data.enabled,
        office_latitude: settingsRes.data.office_latitude || '',
        office_longitude: settingsRes.data.office_longitude || '',
        radius_meters: settingsRes.data.radius_meters || 100
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

      // First try with high accuracy (GPS)
      const tryHighAccuracy = () => {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            resolve({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude
            });
          },
          (error) => {
            // If high accuracy fails, try with low accuracy (network-based)
            if (error.code === error.TIMEOUT || error.code === error.POSITION_UNAVAILABLE) {
              tryLowAccuracy();
            } else if (error.code === error.PERMISSION_DENIED) {
              reject(new Error('Location permission denied. Please enable location access in your browser settings.'));
            } else {
              reject(new Error('Failed to get location. Please try again.'));
            }
          },
          {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 60000
          }
        );
      };

      // Fallback to low accuracy (faster, uses network/WiFi)
      const tryLowAccuracy = () => {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            resolve({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude
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
          {
            enableHighAccuracy: false,
            timeout: 30000,
            maximumAge: 300000
          }
        );
      };

      tryHighAccuracy();
    });
  };

  const handleClockIn = async () => {
    setError('');
    setSuccess('');
    setActionLoading(true);
    setLocationError('');

    try {
      const location = await getCurrentLocation();
      setCurrentLocation(location);

      const response = await axios.post(`${API}/attendance/clock-in`, {
        latitude: location.latitude,
        longitude: location.longitude,
        device_info: navigator.userAgent
      });

      setSuccess(`Clocked in successfully at ${response.data.address || 'your location'}`);
      await fetchData();
    } catch (err) {
      if (err.message) {
        setLocationError(err.message);
      }
      setError(err.response?.data?.detail || err.message || 'Failed to clock in');
    } finally {
      setActionLoading(false);
    }
  };

  const handleClockOut = async () => {
    setError('');
    setSuccess('');
    setActionLoading(true);
    setLocationError('');

    try {
      const location = await getCurrentLocation();
      setCurrentLocation(location);

      const response = await axios.post(`${API}/attendance/clock-out`, {
        latitude: location.latitude,
        longitude: location.longitude,
        device_info: navigator.userAgent
      });

      setSuccess(`Clocked out successfully. Work duration: ${response.data.work_duration_hours} hours`);
      await fetchData();
    } catch (err) {
      if (err.message) {
        setLocationError(err.message);
      }
      setError(err.response?.data?.detail || err.message || 'Failed to clock out');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setError('');
    setSuccess('');
    setActionLoading(true);

    try {
      await axios.put(`${API}/attendance/settings`, {
        enabled: settingsForm.enabled,
        office_latitude: settingsForm.office_latitude ? parseFloat(settingsForm.office_latitude) : null,
        office_longitude: settingsForm.office_longitude ? parseFloat(settingsForm.office_longitude) : null,
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

  const handleUseCurrentLocation = async () => {
    try {
      const location = await getCurrentLocation();
      setSettingsForm(prev => ({
        ...prev,
        office_latitude: location.latitude.toFixed(6),
        office_longitude: location.longitude.toFixed(6)
      }));
      setSuccess('Current location captured for office location');
    } catch (err) {
      setError(err.message || 'Failed to get current location');
    }
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
          <div className="mt-4 sm:mt-0 flex gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="btn-secondary flex items-center"
              data-testid="settings-btn"
            >
              <Settings className="w-4 h-4 mr-2" />
              Geofence Settings
            </button>
            <button
              onClick={fetchReport}
              className="btn-secondary flex items-center"
              data-testid="report-btn"
            >
              <Calendar className="w-4 h-4 mr-2" />
              Monthly Report
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
            Geofence Settings
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
                Enable Geofence Restriction (Users must be within radius to clock in)
              </label>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="form-label">Office Latitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={settingsForm.office_latitude}
                  onChange={(e) => setSettingsForm(prev => ({ ...prev, office_latitude: e.target.value }))}
                  className="form-input"
                  placeholder="19.0760"
                  data-testid="office-latitude"
                />
              </div>
              <div>
                <label className="form-label">Office Longitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={settingsForm.office_longitude}
                  onChange={(e) => setSettingsForm(prev => ({ ...prev, office_longitude: e.target.value }))}
                  className="form-input"
                  placeholder="72.8777"
                  data-testid="office-longitude"
                />
              </div>
              <div>
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
            </div>

            {geofenceSettings?.office_address && (
              <p className="text-sm text-gray-600">
                <MapPin className="w-4 h-4 inline mr-1" />
                Current office location: {geofenceSettings.office_address}
              </p>
            )}

            <div className="flex gap-3">
              <button
                onClick={handleUseCurrentLocation}
                className="btn-secondary flex items-center"
                data-testid="use-current-location"
              >
                <Navigation className="w-4 h-4 mr-2" />
                Use Current Location
              </button>
              <button
                onClick={handleSaveSettings}
                disabled={actionLoading}
                className="btn-primary"
                data-testid="save-settings"
              >
                {actionLoading ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
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
            <button onClick={() => setShowReport(false)} className="text-gray-400 hover:text-gray-600">
              ×
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Name</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Role</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Days Present</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Total Hours</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">Avg Hours/Day</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {report.report.map((row) => (
                  <tr key={row.user_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{row.user_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 capitalize">{row.role}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900">{row.days_present}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900">{row.total_hours}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900">{row.average_hours_per_day}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              ) : (
                <LogIn className="w-5 h-5 mr-2" />
              )}
              Clock In
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
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              ) : (
                <LogOut className="w-5 h-5 mr-2" />
              )}
              Clock Out
            </button>
          )}

          {todayStatus?.clock_in && todayStatus?.clock_out && (
            <div className="flex-1 text-center p-3 bg-gray-100 rounded-lg text-gray-600">
              <CheckCircle className="w-5 h-5 inline mr-2" />
              Attendance complete for today
            </div>
          )}
        </div>

        {/* Geofence Info */}
        {geofenceSettings?.enabled && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800 flex items-center">
              <MapPin className="w-4 h-4 mr-2" />
              Geofence enabled: You must be within {geofenceSettings.radius_meters}m of office to clock in.
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
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Location</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {Object.entries(groupedHistory).map(([date, records]) => {
                  let duration = '-';
                  if (records.clock_in && records.clock_out) {
                    const inTime = new Date(records.clock_in.timestamp);
                    const outTime = new Date(records.clock_out.timestamp);
                    const hours = ((outTime - inTime) / (1000 * 60 * 60)).toFixed(2);
                    duration = `${hours} hrs`;
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
