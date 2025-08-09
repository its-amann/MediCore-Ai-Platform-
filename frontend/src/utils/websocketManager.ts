/**
 * WebSocket Manager with automatic reconnection, token refresh, and message queuing
 */

import axios from 'axios';
import { getWebSocketEnvironment } from './websocketUtils';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

interface WebSocketConfig {
  url: string;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: any) => void;
  onStateChange?: (state: ConnectionState) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableMessageQueue?: boolean;
  maxQueueSize?: number;
}

export enum ConnectionState {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  RECONNECTING = 'RECONNECTING',
  DISCONNECTED = 'DISCONNECTED',
  ERROR = 'ERROR',
  CLOSED = 'CLOSED'
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private connectionState: ConnectionState = ConnectionState.DISCONNECTED;
  private messageQueue: any[] = [];
  private tokenExpiryTimer: NodeJS.Timeout | null = null;
  private isRefreshingToken = false;

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
      enableMessageQueue: true,
      maxQueueSize: 100,
      ...config,
    };
  }

  /**
   * Get current connection state
   */
  getState(): ConnectionState {
    return this.connectionState;
  }

  /**
   * Set connection state and notify listeners
   */
  private setState(state: ConnectionState): void {
    if (this.connectionState !== state) {
      this.connectionState = state;
      this.config.onStateChange?.(state);
    }
  }

  /**
   * Get current access token, refreshing if needed
   */
  private async getValidToken(): Promise<string | null> {
    try {
      let token = localStorage.getItem('access_token');
      
      // Check if token exists
      if (!token) {
        return null;
      }

      // Try to decode token to check expiration
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expirationTime = payload.exp * 1000; // Convert to milliseconds
        const currentTime = Date.now();
        const bufferTime = 60000; // 1 minute buffer

        // If token will expire soon, refresh it
        if (expirationTime - currentTime < bufferTime) {
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken,
            });

            const { access_token, refresh_token: newRefreshToken } = response.data;
            localStorage.setItem('access_token', access_token);
            
            if (newRefreshToken) {
              localStorage.setItem('refresh_token', newRefreshToken);
            }

            token = access_token;
          }
        }
      } catch (e) {
        console.error('Error checking token expiration:', e);
      }

      return token;
    } catch (error) {
      console.error('Error getting valid token:', error);
      // If refresh fails, clear tokens and redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      return null;
    }
  }

  /**
   * Connect to WebSocket with authentication
   */
  async connect(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    
    try {
      const token = await this.getValidToken();
      if (!token) {
        throw new Error('No valid authentication token');
      }

      // Build WebSocket URL (without token for security)
      const wsUrl = new URL(this.config.url, WS_BASE_URL);

      // Pass token via Sec-WebSocket-Protocol header for security
      // This prevents tokens from being logged in server access logs
      this.ws = new WebSocket(wsUrl.toString(), ['bearer', token]);
      this.setState(ConnectionState.CONNECTING);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.setState(ConnectionState.CONNECTED);
        this.config.onOpen?.();
        this.startHeartbeat();
        this.setupTokenExpiryTimer(token);
        this.flushMessageQueue();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle server-side ping messages
          if (data.type === 'ping') {
            // Respond with pong
            this.send({ type: 'pong', timestamp: new Date().toISOString() });
            return;
          }
          
          // Handle pong messages for heartbeat
          if (data.type === 'pong') {
            return;
          }
          
          // Handle authentication warnings
          if (data.type === 'auth_warning') {
            console.warn('Authentication warning:', data.message);
            if (data.should_refresh) {
              // Try to refresh token
              this.handleTokenRefresh();
            }
            return;
          }

          this.config.onMessage?.(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.stopHeartbeat();
        this.clearTokenExpiryTimer();
        
        if (this.isIntentionallyClosed) {
          this.setState(ConnectionState.CLOSED);
        } else {
          this.setState(ConnectionState.DISCONNECTED);
        }
        
        this.config.onClose?.();

        // Handle authentication errors
        if (event.code === 4003 || event.code === 4001) {
          // Authentication failed, try to refresh token and reconnect
          this.handleAuthError();
        } else if (!this.isIntentionallyClosed) {
          // Attempt to reconnect for other errors
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.setState(ConnectionState.ERROR);
        this.config.onError?.(error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Handle authentication errors by refreshing token and reconnecting
   */
  private async handleAuthError(): Promise<void> {
    try {
      const token = await this.getValidToken();
      if (token) {
        // Token refreshed successfully, try to reconnect
        this.scheduleReconnect(1000); // Reconnect quickly after auth refresh
      }
    } catch (error) {
      console.error('Failed to handle auth error:', error);
    }
  }

  /**
   * Handle token refresh requests from server
   */
  private async handleTokenRefresh(): Promise<void> {
    try {
      console.log('Refreshing token due to server request...');
      const token = await this.getValidToken();
      if (token) {
        console.log('Token refreshed successfully');
        // Optionally reconnect with new token if needed
        // For now, just continue using current connection
      } else {
        console.error('Failed to refresh token, user needs to re-login');
        // Disconnect and redirect to login
        this.disconnect();
      }
    } catch (error) {
      console.error('Failed to refresh token:', error);
      this.disconnect();
    }
  }

  /**
   * Setup token expiry timer
   */
  private setupTokenExpiryTimer(token: string): void {
    this.clearTokenExpiryTimer();
    
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expiryTime = payload.exp * 1000;
      const now = Date.now();
      const timeUntilExpiry = expiryTime - now;
      
      // Refresh token 5 minutes before it expires
      const refreshTime = timeUntilExpiry - (5 * 60 * 1000);
      
      if (refreshTime > 0) {
        this.tokenExpiryTimer = setTimeout(() => {
          console.log('Token expiry approaching - refreshing');
          this.refreshTokenAndReconnect();
        }, refreshTime);
      }
    } catch (error) {
      console.error('Failed to set up token expiry timer:', error);
    }
  }

  /**
   * Clear token expiry timer
   */
  private clearTokenExpiryTimer(): void {
    if (this.tokenExpiryTimer) {
      clearTimeout(this.tokenExpiryTimer);
      this.tokenExpiryTimer = null;
    }
  }

  /**
   * Refresh token and reconnect with new token
   */
  private async refreshTokenAndReconnect(): Promise<void> {
    if (this.isRefreshingToken) return;
    
    this.isRefreshingToken = true;
    
    try {
      const token = await this.getValidToken();
      
      if (token) {
        // Close current connection and reconnect with new token
        if (this.ws) {
          this.ws.close(1000, 'Token refresh');
        }
        await this.connect();
      }
    } catch (error) {
      console.error('Failed to refresh token and reconnect:', error);
    } finally {
      this.isRefreshingToken = false;
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(delay?: number): void {
    if (this.reconnectAttempts >= (this.config.maxReconnectAttempts || 10)) {
      console.error('Max reconnection attempts reached');
      this.setState(ConnectionState.CLOSED);
      return;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    // Exponential backoff with jitter
    const baseDelay = delay || this.config.reconnectInterval || 5000;
    const exponentialDelay = Math.min(baseDelay * Math.pow(2, this.reconnectAttempts), 30000);
    const jitter = Math.random() * 1000;
    const reconnectDelay = exponentialDelay + jitter;
    
    this.reconnectAttempts++;
    this.setState(ConnectionState.RECONNECTING);

    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${Math.round(reconnectDelay)}ms`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, reconnectDelay);
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Send ping every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Send data through WebSocket with queuing support
   */
  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else if (this.config.enableMessageQueue && this.messageQueue.length < (this.config.maxQueueSize || 100)) {
      console.log('WebSocket not connected, queuing message');
      this.messageQueue.push(data);
    } else {
      console.warn('WebSocket is not connected and queue is full or disabled');
    }
  }

  /**
   * Flush queued messages
   */
  private flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;
    
    console.log(`Flushing ${this.messageQueue.length} queued messages`);
    const messages = [...this.messageQueue];
    this.messageQueue = [];
    
    messages.forEach(message => {
      this.send(message);
    });
  }

  /**
   * Get number of queued messages
   */
  getQueuedMessagesCount(): number {
    return this.messageQueue.length;
  }

  /**
   * Clear message queue
   */
  clearMessageQueue(): void {
    this.messageQueue = [];
  }

  /**
   * Close WebSocket connection
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();
    this.clearTokenExpiryTimer();
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.clearMessageQueue();
    this.setState(ConnectionState.CLOSED);
  }

  /**
   * Get connection state
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export default WebSocketManager;