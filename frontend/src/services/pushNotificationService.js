// Push Notification Service for TaskAct PWA
// Handles service worker registration and push subscription management

const VAPID_PUBLIC_KEY = process.env.REACT_APP_VAPID_PUBLIC_KEY;

class PushNotificationService {
  constructor() {
    this.swRegistration = null;
    this.subscription = null;
    this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
  }

  // Check if notifications are supported
  isNotificationSupported() {
    return this.isSupported;
  }

  // Check current permission status
  getPermissionStatus() {
    if (!this.isSupported) return 'unsupported';
    return Notification.permission;
  }

  // Register service worker
  async registerServiceWorker() {
    if (!this.isSupported) {
      console.log('[Push] Service Worker not supported');
      return null;
    }

    try {
      const registration = await navigator.serviceWorker.register('/service-worker.js', {
        scope: '/'
      });
      
      console.log('[Push] Service Worker registered:', registration.scope);
      this.swRegistration = registration;

      // Check for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        console.log('[Push] New service worker installing...');
        
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('[Push] New content available, please refresh');
            // Optionally show update notification to user
            this.notifyUpdateAvailable();
          }
        });
      });

      return registration;
    } catch (error) {
      console.error('[Push] Service Worker registration failed:', error);
      return null;
    }
  }

  // Request notification permission
  async requestPermission() {
    if (!this.isSupported) {
      return { success: false, error: 'Notifications not supported' };
    }

    try {
      const permission = await Notification.requestPermission();
      console.log('[Push] Permission result:', permission);
      
      if (permission === 'granted') {
        return { success: true, permission };
      } else {
        return { success: false, permission, error: 'Permission denied' };
      }
    } catch (error) {
      console.error('[Push] Permission request failed:', error);
      return { success: false, error: error.message };
    }
  }

  // Subscribe to push notifications
  async subscribeToPush(token) {
    if (!this.swRegistration) {
      await this.registerServiceWorker();
    }

    if (!this.swRegistration) {
      return { success: false, error: 'Service Worker not registered' };
    }

    try {
      // Check existing subscription
      let subscription = await this.swRegistration.pushManager.getSubscription();
      
      if (subscription) {
        console.log('[Push] Existing subscription found');
        this.subscription = subscription;
      } else {
        // Create new subscription
        console.log('[Push] Creating new subscription');
        
        // For now, use a placeholder VAPID key since we don't have a push server
        // In production, this would be your VAPID public key
        const applicationServerKey = this.urlBase64ToUint8Array(
          VAPID_PUBLIC_KEY || 'BNDxrLsyT-BTNT9Xl-r5MjAXTREeLfVe-cjH3q_r4mFLqJMzL5pCqGe9E3GQ1C_4LFqT1'
        );
        
        subscription = await this.swRegistration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey
        });
        
        console.log('[Push] New subscription created');
        this.subscription = subscription;
      }

      // Send subscription to backend (if we have a backend endpoint)
      // await this.sendSubscriptionToServer(subscription, token);

      return { success: true, subscription };
    } catch (error) {
      console.error('[Push] Subscription failed:', error);
      return { success: false, error: error.message };
    }
  }

  // Unsubscribe from push notifications
  async unsubscribeFromPush() {
    if (!this.subscription) {
      return { success: true, message: 'No subscription found' };
    }

    try {
      await this.subscription.unsubscribe();
      this.subscription = null;
      console.log('[Push] Unsubscribed successfully');
      return { success: true };
    } catch (error) {
      console.error('[Push] Unsubscribe failed:', error);
      return { success: false, error: error.message };
    }
  }

  // Show a local notification (for browser-based notifications)
  async showLocalNotification(title, options = {}) {
    if (!this.swRegistration) {
      await this.registerServiceWorker();
    }

    if (!this.swRegistration) {
      // Fallback to native notification
      if (Notification.permission === 'granted') {
        new Notification(title, options);
        return { success: true };
      }
      return { success: false, error: 'Cannot show notification' };
    }

    try {
      await this.swRegistration.showNotification(title, {
        body: options.body || '',
        icon: options.icon || '/taskact-logo.svg',
        badge: options.badge || '/taskact-badge.png',
        tag: options.tag || `local-${Date.now()}`,
        data: options.data || {},
        actions: options.actions || [],
        vibrate: options.vibrate || [200, 100, 200],
        requireInteraction: options.requireInteraction || false
      });
      
      console.log('[Push] Local notification shown');
      return { success: true };
    } catch (error) {
      console.error('[Push] Show notification failed:', error);
      return { success: false, error: error.message };
    }
  }

  // Helper to convert VAPID key
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // Notify user about available update
  notifyUpdateAvailable() {
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new CustomEvent('sw-update-available'));
    }
  }

  // Get current subscription
  async getSubscription() {
    if (!this.swRegistration) {
      await this.registerServiceWorker();
    }
    
    if (this.swRegistration) {
      return await this.swRegistration.pushManager.getSubscription();
    }
    return null;
  }

  // Check if currently subscribed
  async isSubscribed() {
    const subscription = await this.getSubscription();
    return !!subscription;
  }
}

// Singleton instance
const pushService = new PushNotificationService();

export default pushService;

// Export individual functions for convenience
export const registerServiceWorker = () => pushService.registerServiceWorker();
export const requestPermission = () => pushService.requestPermission();
export const subscribeToPush = (token) => pushService.subscribeToPush(token);
export const unsubscribeFromPush = () => pushService.unsubscribeFromPush();
export const showLocalNotification = (title, options) => pushService.showLocalNotification(title, options);
export const isNotificationSupported = () => pushService.isNotificationSupported();
export const getPermissionStatus = () => pushService.getPermissionStatus();
