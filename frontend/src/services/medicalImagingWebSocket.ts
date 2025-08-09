import { EventEmitter } from 'events';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export enum ConnectionState {
  DISCONNECTED = 'DISCONNECTED',
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
  CLOSED = 'CLOSED'
}

export interface WebSocketMessage {
  type: string;
  data?: any;
  status?: string;
  progress?: number;
  message?: string;
  error?: string;
  should_refresh?: boolean;
  in_grace_period?: boolean;
}

export interface WebSocketConfig {
  url: string;
  token: string;
  clientId: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class MedicalImagingWebSocket extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;
  private messageQueue: WebSocketMessage[] = [];
  private maxQueueSize = 50;
  private connectionState: ConnectionState = ConnectionState.DISCONNECTED;

  constructor(config: WebSocketConfig) {
    super();
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      ...config
    };
  }

  /**
   * Get current connection state
   */
  getConnectionState(): ConnectionState {
    return this.connectionState;
  }

  /**
   * Set connection state and emit state change event
   */
  private setState(state: ConnectionState): void {
    if (this.connectionState !== state) {
      const previousState = this.connectionState;
      this.connectionState = state;
      this.emit('stateChanged', { previousState, currentState: state });
    }
  }

  /**
   * Get valid token, refreshing if needed
   */
  private async getValidToken(): Promise<string | null> {
    try {
      let token = this.config.token || localStorage.getItem('access_token');
      
      if (!token) {
        return null;
      }

      // Check if token is expired or about to expire
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expirationTime = payload.exp * 1000;
        const currentTime = Date.now();
        const bufferTime = 60000; // 1 minute buffer

        if (expirationTime - currentTime < bufferTime) {
          // Token is expired or about to expire, refresh it
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
            this.config.token = access_token; // Update config with new token
          }
        }
      } catch (e) {
        console.error('Error checking token expiration:', e);
      }

      return token;
    } catch (error) {
      console.error('Error getting valid token:', error);
      // If refresh fails, emit auth error
      this.emit('authError', 'Failed to refresh authentication token');
      return null;
    }
  }

  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.isIntentionallyClosed = false;
    this.setState(ConnectionState.CONNECTING);
    
    try {
      // Get valid token before connecting
      const token = await this.getValidToken();
      if (!token) {
        throw new Error('No valid authentication token');
      }

      // Create WebSocket connection without token in URL for security
      console.log('Connecting to WebSocket:', this.config.url);
      
      // Pass token via Sec-WebSocket-Protocol header for security
      // This prevents token from being logged in server access logs
      this.ws = new WebSocket(this.config.url, ['bearer', token]);
      
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.emit('error', error);
      this.scheduleReconnect();
    }
  }

  private handleOpen(): void {
    console.log('WebSocket connected');
    this.reconnectAttempts = 0;
    this.setState(ConnectionState.CONNECTED);
    this.emit('connected');
    
    // Start ping interval to keep connection alive
    this.startPingInterval();
    
    // Flush any queued messages
    this.flushMessageQueue();
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      console.log('WebSocket message received:', message);
      
      // Emit specific events based on message type
      this.emit('message', message);
      this.emit(message.type, message);
      
      // Handle specific message types
      switch (message.type) {
        case 'analysis_update':
          this.emit('analysisUpdate', {
            status: message.status,
            progress: message.progress,
            message: message.message
          });
          break;
        case 'analysis_complete':
          this.emit('analysisComplete', message.data);
          break;
        case 'error':
          this.emit('analysisError', message.error);
          break;
        case 'auth_warning':
          console.warn('WebSocket auth warning:', message.message);
          this.emit('authWarning', {
            message: message.message,
            shouldRefresh: message.should_refresh,
            inGracePeriod: message.in_grace_period
          });
          
          // Proactively refresh token if needed
          if (message.should_refresh) {
            this.getValidToken(); // This will trigger refresh if needed
          }
          break;
        case 'pong':
          // Keep-alive response
          break;
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      this.emit('error', error);
    }
  }

  private handleError(event: Event): void {
    console.error('WebSocket error:', event);
    this.setState(ConnectionState.ERROR);
    this.emit('error', new Error('WebSocket connection error'));
  }

  private async handleClose(event: CloseEvent): Promise<void> {
    console.log('WebSocket closed:', event.code, event.reason);
    this.ws = null;
    this.stopPingInterval();
    
    if (this.isIntentionallyClosed) {
      this.setState(ConnectionState.CLOSED);
    } else {
      this.setState(ConnectionState.DISCONNECTED);
    }
    
    if (!this.isIntentionallyClosed) {
      this.emit('disconnected', { code: event.code, reason: event.reason });
      
      // Handle authentication errors with specific codes
      if (event.code === 4003) {
        // Token expired - try to refresh
        console.log('WebSocket closed due to token expiration, attempting refresh...');
        const token = await this.getValidToken();
        if (token) {
          this.emit('tokenRefreshed', { newToken: token });
          this.scheduleReconnect(1000); // Quick reconnect after auth refresh
        } else {
          this.emit('authError', 'Token expired and refresh failed');
        }
        return;
      } else if (event.code === 4001) {
        // Invalid token
        this.emit('authError', 'Invalid authentication token');
        return;
      } else if (event.code === 4002) {
        // Authentication failed
        this.emit('authError', 'Authentication failed');
        return;
      } else if (event.code === 1008) {
        // Policy violation (often auth related)
        const token = await this.getValidToken();
        if (token) {
          this.scheduleReconnect(1000);
        } else {
          this.emit('authError', 'Authentication policy violation');
        }
        return;
      }
      
      // Attempt reconnection for other errors
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(delay?: number): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts!) {
      console.error('Max reconnection attempts reached');
      this.setState(ConnectionState.CLOSED);
      this.emit('maxReconnectAttemptsReached');
      return;
    }

    this.reconnectAttempts++;
    this.setState(ConnectionState.RECONNECTING);
    const reconnectDelay = delay || this.config.reconnectInterval;
    console.log(`Scheduling reconnection attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${reconnectDelay}ms`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, reconnectDelay);
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    
    // Send ping every 30 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  send(message: WebSocketMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // Queue the message if not connected
      if (this.messageQueue.length < this.maxQueueSize) {
        console.log('WebSocket not connected, queuing message');
        this.messageQueue.push(message);
        this.emit('messageQueued', { message, queueSize: this.messageQueue.length });
      } else {
        console.error('WebSocket is not connected and message queue is full');
        this.emit('error', new Error('WebSocket is not connected and message queue is full'));
      }
      return;
    }

    try {
      this.ws.send(JSON.stringify(message));
      this.emit('messageSent', message);
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      this.emit('error', error);
      
      // Try to queue the message for retry
      if (this.messageQueue.length < this.maxQueueSize) {
        this.messageQueue.push(message);
      }
    }
  }

  private flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;
    
    console.log(`Flushing ${this.messageQueue.length} queued messages`);
    const messages = [...this.messageQueue];
    this.messageQueue = [];
    
    messages.forEach(message => {
      this.send(message);
    });
  }

  getQueuedMessagesCount(): number {
    return this.messageQueue.length;
  }

  clearMessageQueue(): void {
    const count = this.messageQueue.length;
    this.messageQueue = [];
    console.log(`Cleared ${count} messages from queue`);
    this.emit('queueCleared', count);
  }

  sendAnalysisRequest(caseId: string, imageIds: string[]): void {
    this.send({
      type: 'analysis_request',
      data: {
        caseId,
        imageIds
      }
    });
  }

  sendCleanupRequest(): void {
    this.send({
      type: 'cleanup_request'
    });
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopPingInterval();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    // Clear message queue on disconnect
    this.clearMessageQueue();
    
    this.setState(ConnectionState.CLOSED);
    this.emit('disconnected', { code: 1000, reason: 'Client disconnect' });
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// Singleton instance management
let wsInstance: MedicalImagingWebSocket | null = null;

export function getMedicalImagingWebSocket(config?: WebSocketConfig): MedicalImagingWebSocket {
  if (!wsInstance && config) {
    wsInstance = new MedicalImagingWebSocket(config);
  } else if (!wsInstance) {
    throw new Error('WebSocket not initialized. Please provide configuration.');
  }
  
  return wsInstance;
}

export function closeMedicalImagingWebSocket(): void {
  if (wsInstance) {
    wsInstance.disconnect();
    wsInstance = null;
  }
}