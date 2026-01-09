import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const NotificationPanel = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showPanel, setShowPanel] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState('default');
  const previousUnreadCount = useRef(0);
  const latestNotificationId = useRef(null);

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window) {
      setNotificationPermission(Notification.permission);
      
      // Auto-request permission when user first visits
      if (Notification.permission === 'default') {
        // Add a small delay to avoid blocking page load
        const timer = setTimeout(() => {
          Notification.requestPermission().then((permission) => {
            setNotificationPermission(permission);
          });
        }, 2000);
        return () => clearTimeout(timer);
      }
    }
  }, []);

  // Function to show browser/OS notification
  const showBrowserNotification = useCallback((title, message) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        const notification = new Notification(title, {
          body: message,
          icon: '/favicon.ico',
          badge: '/favicon.ico',
          tag: `taskact-${Date.now()}`,
          requireInteraction: false,
          silent: false,
          vibrate: [200, 100, 200]
        });

        // Auto close after 5 seconds
        setTimeout(() => notification.close(), 5000);

        // Handle click - focus the app
        notification.onclick = () => {
          window.focus();
          setShowPanel(true);
          notification.close();
        };
      } catch (error) {
        console.error('Error showing notification:', error);
      }
    }
  }, []);

  const fetchNotifications = async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      const response = await axios.get(`${API}/notifications`);
      const newNotifications = response.data;
      
      // Check if there's a new notification we haven't seen
      if (newNotifications.length > 0) {
        const latestNotif = newNotifications[0];
        if (latestNotificationId.current && latestNotif.id !== latestNotificationId.current && !latestNotif.read) {
          // Show browser notification for the new notification
          showBrowserNotification(latestNotif.title, latestNotif.message);
        }
        latestNotificationId.current = latestNotif.id;
      }
      
      setNotifications(newNotifications);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await axios.get(`${API}/notifications/unread-count`);
      const newCount = response.data.unread_count;
      
      // Show browser notification if count increased
      if (newCount > previousUnreadCount.current && previousUnreadCount.current >= 0) {
        // Fetch latest notification to show its content
        try {
          const notifResponse = await axios.get(`${API}/notifications`);
          const latestUnread = notifResponse.data.find(n => !n.read);
          if (latestUnread && latestUnread.id !== latestNotificationId.current) {
            showBrowserNotification(latestUnread.title, latestUnread.message);
            latestNotificationId.current = latestUnread.id;
          }
        } catch (e) {
          // Fallback generic notification
          showBrowserNotification('TaskAct', 'You have a new notification');
        }
      }
      
      previousUnreadCount.current = newCount;
      setUnreadCount(newCount);
    } catch (error) {
      console.error('Error fetching unread count:', error);
    }
  }, [user, showBrowserNotification]);

  const requestNotificationPermission = async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      const permission = await Notification.requestPermission();
      setNotificationPermission(permission);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.put(`${API}/notifications/${notificationId}/read`);
      
      // Update local state
      setNotifications(prev => 
        prev.map(notif => 
          notif.id === notificationId 
            ? { ...notif, read: true }
            : notif
        )
      );
      
      // Update unread count
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  useEffect(() => {
    if (user) {
      fetchUnreadCount();
      
      // Poll for notifications every 30 seconds
      const interval = setInterval(() => {
        fetchUnreadCount();
      }, 30000);
      
      return () => clearInterval(interval);
    }
  }, [user, fetchUnreadCount]);

  const togglePanel = () => {
    if (!showPanel) {
      fetchNotifications();
    }
    setShowPanel(!showPanel);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)} hours ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <div className="relative">
      {/* Notification Bell */}
      <button
        onClick={togglePanel}
        className="relative p-2 text-gray-600 hover:text-gray-900 rounded-full hover:bg-gray-100"
        data-testid="notification-bell"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        
        {/* Unread Count Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notification Panel - Fixed for mobile */}
      {showPanel && (
        <>
          {/* Backdrop for mobile */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-25 z-40 md:hidden"
            onClick={() => setShowPanel(false)}
          />
          <div className="fixed right-2 left-2 top-16 md:absolute md:right-0 md:left-auto md:top-auto md:mt-2 md:w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-[80vh] md:max-h-96 overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Notifications</h3>
              <button
                onClick={() => setShowPanel(false)}
                className="text-gray-400 hover:text-gray-600 md:hidden"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Permission Request Banner */}
            {notificationPermission === 'default' && (
              <div className="px-4 py-3 bg-blue-50 border-b border-blue-100">
                <p className="text-sm text-blue-800 mb-2">Enable push notifications to stay updated</p>
                <button
                  onClick={requestNotificationPermission}
                  className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700 transition-colors"
                >
                  Enable Notifications
                </button>
              </div>
            )}

            {notificationPermission === 'denied' && (
              <div className="px-4 py-2 bg-yellow-50 border-b border-yellow-100">
                <p className="text-xs text-yellow-800">Push notifications are blocked. Enable them in your browser settings.</p>
              </div>
            )}
            
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="p-4 text-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-sm text-gray-600">Loading notifications...</p>
                </div>
              ) : notifications.length === 0 ? (
                <div className="p-4 text-center text-gray-500">
                  <p>No notifications yet</p>
                </div>
              ) : (
                notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={`p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${
                      !notification.read ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => !notification.read && markAsRead(notification.id)}
                    data-testid={`notification-${notification.id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="text-sm font-medium text-gray-900">
                          {notification.title}
                        </h4>
                        <p className="text-sm text-gray-600 mt-1">
                          {notification.message}
                        </p>
                        <p className="text-xs text-gray-500 mt-2">
                          {formatDate(notification.created_at)}
                        </p>
                      </div>
                      {!notification.read && (
                        <div className="w-2 h-2 bg-blue-600 rounded-full ml-2 mt-1"></div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
            
            {notifications.length > 0 && (
              <div className="px-4 py-3 border-t border-gray-200 text-center">
                <button
                  onClick={() => setShowPanel(false)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default NotificationPanel;