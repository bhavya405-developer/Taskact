import React, { useState, useEffect } from 'react';
import { Bell, BellOff, Smartphone, Check, X, AlertCircle, RefreshCw } from 'lucide-react';
import pushService, { 
  registerServiceWorker, 
  requestPermission, 
  subscribeToPush,
  showLocalNotification,
  isNotificationSupported,
  getPermissionStatus 
} from '../services/pushNotificationService';

const NotificationSettings = () => {
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    initializeNotifications();
  }, []);

  const initializeNotifications = async () => {
    const supported = isNotificationSupported();
    setIsSupported(supported);
    
    if (supported) {
      setPermission(getPermissionStatus());
      
      // Register service worker
      await registerServiceWorker();
      
      // Check subscription status
      const subscribed = await pushService.isSubscribed();
      setIsSubscribed(subscribed);
    }
  };

  const handleEnableNotifications = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Request permission
      const permResult = await requestPermission();
      setPermission(permResult.permission || getPermissionStatus());

      if (!permResult.success) {
        setError('Notification permission denied. Please enable notifications in your browser settings.');
        setLoading(false);
        return;
      }

      // Subscribe to push
      const subResult = await subscribeToPush();
      
      if (subResult.success) {
        setIsSubscribed(true);
        setSuccess('Notifications enabled! You will now receive push notifications.');
        
        // Show a test notification
        await showLocalNotification('TaskAct Notifications Enabled', {
          body: 'You will now receive notifications for task assignments, deadlines, and updates.',
          tag: 'welcome-notification'
        });
      } else {
        setError(subResult.error || 'Failed to enable notifications');
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleDisableNotifications = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await pushService.unsubscribeFromPush();
      
      if (result.success) {
        setIsSubscribed(false);
        setSuccess('Notifications disabled.');
      } else {
        setError(result.error || 'Failed to disable notifications');
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleTestNotification = async () => {
    setLoading(true);
    setError('');

    try {
      const result = await showLocalNotification('Test Notification', {
        body: 'This is a test notification from TaskAct. Your notifications are working!',
        tag: 'test-notification',
        actions: [
          { action: 'view', title: 'View' },
          { action: 'dismiss', title: 'Dismiss' }
        ]
      });

      if (!result.success) {
        setError(result.error || 'Failed to show test notification');
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!isSupported) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-yellow-800">Notifications Not Supported</h4>
            <p className="text-sm text-yellow-700 mt-1">
              Your browser does not support push notifications. Try using a modern browser like Chrome, Firefox, or Edge.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <div className={`p-2 rounded-lg ${isSubscribed ? 'bg-green-100' : 'bg-gray-100'}`}>
            {isSubscribed ? (
              <Bell className="h-6 w-6 text-green-600" />
            ) : (
              <BellOff className="h-6 w-6 text-gray-500" />
            )}
          </div>
          <div className="ml-4">
            <h3 className="text-lg font-medium text-gray-900">Push Notifications</h3>
            <p className="text-sm text-gray-500">
              {isSubscribed 
                ? 'Notifications are enabled' 
                : 'Enable notifications to stay updated'}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {permission === 'granted' && (
            <span className="flex items-center text-sm text-green-600">
              <Check className="h-4 w-4 mr-1" />
              Permission Granted
            </span>
          )}
          {permission === 'denied' && (
            <span className="flex items-center text-sm text-red-600">
              <X className="h-4 w-4 mr-1" />
              Permission Denied
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4">
          <p className="text-sm text-green-600">{success}</p>
        </div>
      )}

      <div className="space-y-4">
        {/* Notification Types */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start p-3 bg-gray-50 rounded-lg">
            <Smartphone className="h-5 w-5 text-indigo-600 mt-0.5 mr-3 flex-shrink-0" />
            <div>
              <h4 className="text-sm font-medium text-gray-900">Task Assignments</h4>
              <p className="text-xs text-gray-500 mt-1">Get notified when tasks are assigned to you</p>
            </div>
          </div>
          
          <div className="flex items-start p-3 bg-gray-50 rounded-lg">
            <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0" />
            <div>
              <h4 className="text-sm font-medium text-gray-900">Deadline Reminders</h4>
              <p className="text-xs text-gray-500 mt-1">Receive alerts for upcoming deadlines</p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 pt-4 border-t border-gray-200">
          {!isSubscribed ? (
            <button
              onClick={handleEnableNotifications}
              disabled={loading || permission === 'denied'}
              className="btn-primary flex items-center"
              data-testid="enable-notifications-btn"
            >
              {loading ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Bell className="h-4 w-4 mr-2" />
              )}
              Enable Notifications
            </button>
          ) : (
            <>
              <button
                onClick={handleTestNotification}
                disabled={loading}
                className="btn-secondary flex items-center"
                data-testid="test-notification-btn"
              >
                {loading ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Bell className="h-4 w-4 mr-2" />
                )}
                Test Notification
              </button>
              
              <button
                onClick={handleDisableNotifications}
                disabled={loading}
                className="text-red-600 hover:text-red-700 flex items-center px-3 py-2"
                data-testid="disable-notifications-btn"
              >
                <BellOff className="h-4 w-4 mr-2" />
                Disable
              </button>
            </>
          )}
        </div>

        {permission === 'denied' && (
          <div className="bg-amber-50 border border-amber-200 rounded-md p-3 mt-4">
            <p className="text-sm text-amber-700">
              <strong>Permission Blocked:</strong> Notifications are blocked in your browser. 
              To enable them, click the lock icon in your browser's address bar and allow notifications.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default NotificationSettings;
