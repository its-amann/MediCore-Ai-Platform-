/**
 * Token Management Service
 * Handles automatic token refresh and expiration monitoring
 */

import axios from 'axios';
import { toast } from 'react-hot-toast';

interface TokenStatus {
  valid: boolean;
  expired: boolean;
  inGracePeriod: boolean;
  expiresInSeconds: number;
  shouldRefresh: boolean;
}

class TokenManager {
  private checkInterval: NodeJS.Timeout | null = null;
  private refreshPromise: Promise<boolean> | null = null;
  private readonly CHECK_INTERVAL = 300000; // Check every 5 minutes (reduced from 1 minute)
  private readonly REFRESH_THRESHOLD = 600; // Refresh if expires in 10 minutes

  constructor() {
    this.startTokenMonitoring();
  }

  /**
   * Start monitoring token expiration
   */
  startTokenMonitoring(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
    }

    this.checkInterval = setInterval(async () => {
      await this.checkAndRefreshToken();
    }, this.CHECK_INTERVAL);
  }

  /**
   * Stop monitoring token expiration
   */
  stopTokenMonitoring(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  /**
   * Check token status and refresh if needed
   */
  async checkAndRefreshToken(): Promise<boolean> {
    const token = localStorage.getItem('access_token');
    if (!token) {
      return false;
    }

    try {
      const status = await this.getTokenStatus();
      
      if (status.shouldRefresh && !status.expired) {
        console.log('Token needs refresh, attempting refresh...');
        return await this.refreshToken();
      } else if (status.expired && !status.inGracePeriod) {
        console.warn('Token has expired and is not in grace period');
        this.handleTokenExpired();
        return false;
      }

      return status.valid;
    } catch (error) {
      console.error('Failed to check token status:', error);
      return false;
    }
  }

  /**
   * Get current token status locally without API call
   */
  async getTokenStatus(): Promise<TokenStatus> {
    // Check token status locally to avoid unnecessary API calls
    const token = localStorage.getItem('access_token');
    if (!token) {
      return {
        valid: false,
        expired: true,
        inGracePeriod: false,
        expiresInSeconds: 0,
        shouldRefresh: true
      };
    }

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expirationTime = payload.exp * 1000;
      const currentTime = Date.now();
      const expiresInSeconds = Math.max(0, Math.floor((expirationTime - currentTime) / 1000));
      
      const expired = expiresInSeconds <= 0;
      const shouldRefresh = expiresInSeconds < this.REFRESH_THRESHOLD;
      const inGracePeriod = expired && expiresInSeconds > -300; // 5 minute grace period
      
      return {
        valid: !expired,
        expired,
        inGracePeriod,
        expiresInSeconds,
        shouldRefresh
      };
    } catch (error) {
      // If we can't parse the token, assume it's invalid
      return {
        valid: false,
        expired: true,
        inGracePeriod: false,
        expiresInSeconds: 0,
        shouldRefresh: true
      };
    }
  }

  /**
   * Refresh the access token
   */
  async refreshToken(): Promise<boolean> {
    // Prevent multiple simultaneous refresh attempts
    if (this.refreshPromise) {
      return await this.refreshPromise;
    }

    this.refreshPromise = this.performTokenRefresh();
    const result = await this.refreshPromise;
    this.refreshPromise = null;
    
    return result;
  }

  /**
   * Perform the actual token refresh
   */
  private async performTokenRefresh(): Promise<boolean> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      this.handleTokenExpired();
      return false;
    }

    try {
      const response = await axios.post('/auth/refresh', {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token: newRefreshToken } = response.data;
      
      // Update stored tokens
      localStorage.setItem('access_token', access_token);
      if (newRefreshToken) {
        localStorage.setItem('refresh_token', newRefreshToken);
      }

      console.log('Token refreshed successfully');
      
      // Emit custom event for other parts of the app
      window.dispatchEvent(new CustomEvent('tokenRefreshed', {
        detail: { access_token, refresh_token: newRefreshToken }
      }));

      return true;
    } catch (error: any) {
      console.error('Token refresh failed:', error);
      
      if (error.response?.status === 401) {
        this.handleTokenExpired();
      }
      
      return false;
    }
  }

  /**
   * Handle token expiration - clear storage and redirect to login
   */
  private handleTokenExpired(): void {
    console.log('Token expired, logging out user');
    
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    
    toast.error('Your session has expired. Please log in again.');
    
    // Emit logout event
    window.dispatchEvent(new CustomEvent('tokenExpired'));
    
    // Redirect to login if not already there
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  /**
   * Check if token is close to expiring
   */
  isTokenNearExpiry(): boolean {
    const token = localStorage.getItem('access_token');
    if (!token) return true;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expirationTime = payload.exp * 1000;
      const currentTime = Date.now();
      const timeUntilExpiry = expirationTime - currentTime;

      return timeUntilExpiry < this.REFRESH_THRESHOLD * 1000;
    } catch (error) {
      console.error('Failed to parse token:', error);
      return true;
    }
  }

  /**
   * Get time until token expires (in seconds)
   */
  getTimeUntilExpiry(): number {
    const token = localStorage.getItem('access_token');
    if (!token) return 0;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expirationTime = payload.exp * 1000;
      const currentTime = Date.now();
      const timeUntilExpiry = Math.max(0, expirationTime - currentTime);

      return Math.floor(timeUntilExpiry / 1000);
    } catch (error) {
      console.error('Failed to parse token:', error);
      return 0;
    }
  }

  /**
   * Manually trigger token refresh
   */
  async forceRefresh(): Promise<boolean> {
    return await this.refreshToken();
  }

  /**
   * Cleanup when service is destroyed
   */
  destroy(): void {
    this.stopTokenMonitoring();
  }
}

// Create singleton instance
export const tokenManager = new TokenManager();

// Export class for testing
export { TokenManager };
export type { TokenStatus };