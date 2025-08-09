import React, { createContext, useContext, useEffect, useState, useRef, ReactNode, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';
import { Message, TypingUser, OnlineUser } from '../types/common';

interface WebSocketContextType {
  socket: WebSocket | null;
  isConnected: boolean;
  onlineUsers: OnlineUser[];
  typingUsers: TypingUser[];
  
  // Connection management
  connect: () => void;
  disconnect: () => void;
  
  // Message handling
  sendMessage: (message: any) => void;
  onMessage: (callback: (message: Message) => void) => () => void;
  
  // Room management
  joinRoom: (roomId: string) => void;
  leaveRoom: (roomId: string) => void;
  
  // Typing indicators
  startTyping: (roomId?: string) => void;
  stopTyping: (roomId?: string) => void;
  
  // Notifications
  onNotification: (callback: (notification: any) => void) => () => void;
  
  // Status updates
  updateStatus: (status: 'online' | 'away' | 'busy') => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user, token } = useAuthStore();
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState<OnlineUser[]>([]);
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([]);
  
  const messageCallbacks = useRef<Set<(message: Message) => void>>(new Set());
  const notificationCallbacks = useRef<Set<(notification: any) => void>>(new Set());
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const typingTimeouts = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!user || !token || socket?.readyState === WebSocket.OPEN) return;

    // Skip WebSocket connection for medical imaging pages - they use their own WebSocket
    if (window.location.pathname.includes('/imaging') || window.location.pathname.includes('/reports/')) {
      return;
    }

    // Clean up existing socket if any
    if (socket) {
      socket.close();
    }

    // Determine which WebSocket to connect to based on context
    const isCollaborationContext = window.location.pathname.includes('/rooms');
    const wsUrl = new URL(process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000');
    wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    
    if (isCollaborationContext) {
      // For collaboration features, use the collaboration WebSocket endpoint
      const roomId = window.location.pathname.split('/rooms/')[1]?.split('/')[0];
      // Only connect to room-specific WebSocket if we have a valid room ID (not 'new', 'create', etc.)
      if (roomId && roomId !== 'new' && roomId !== 'create' && roomId.length > 3) {
        wsUrl.pathname = `/collaboration/ws/chat/${roomId}`;
      } else {
        // For room creation pages or general collaboration, use main WebSocket
        wsUrl.pathname = '/api/v1/ws';
      }
    } else {
      wsUrl.pathname = '/api/v1/ws';
    }
    
    wsUrl.searchParams.append('token', token);
    wsUrl.searchParams.append('user_id', user.user_id);
    wsUrl.searchParams.append('username', user.username);

    const newSocket = new WebSocket(wsUrl.toString());

    // Connection events
    newSocket.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      reconnectAttempts.current = 0;
      toast.success('Connected to real-time updates');
    };

    newSocket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      setIsConnected(false);
      setOnlineUsers([]);
      setTypingUsers([]);
      
      // Handle different close codes
      if (event.code === 4003) {
        // Token expired
        toast.error('Session expired. Please refresh the page to continue.');
        // Don't attempt reconnection for expired tokens
        return;
      } else if (event.code === 4001) {
        // Authentication failed
        toast.error('Authentication failed. Please log in again.');
        // Don't attempt reconnection for auth failures
        return;
      }
      
      // Auto-reconnect logic for other errors
      if (!event.wasClean && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        
        console.log(`WebSocket reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts} in ${delay}ms`);
        
        reconnectTimeout.current = setTimeout(() => {
          console.log(`Attempting to reconnect... (${reconnectAttempts.current}/${maxReconnectAttempts})`);
          connect();
        }, delay);
      } else if (reconnectAttempts.current >= maxReconnectAttempts) {
        toast.error('Failed to connect to real-time updates. Please refresh the page.');
      }
    };

    newSocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    newSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);

        switch (data.type) {
          case 'connection_success':
            console.log('Connection established:', data);
            break;

          case 'chat_message':
            messageCallbacks.current.forEach(callback => callback(data));
            break;

          case 'user_typing':
            if (data.user_id !== user.user_id) {
              setTypingUsers(prev => {
                const exists = prev.find(u => u.user_id === data.user_id && u.room_id === data.room_id);
                if (exists) return prev;
                return [...prev, { user_id: data.user_id, username: data.username, room_id: data.room_id }];
              });

              // Auto-remove typing indicator after 3 seconds
              const key = `${data.user_id}-${data.room_id || 'global'}`;
              if (typingTimeouts.current.has(key)) {
                clearTimeout(typingTimeouts.current.get(key)!);
              }
              
              const timeout = setTimeout(() => {
                setTypingUsers(prev => 
                  prev.filter(u => !(u.user_id === data.user_id && u.room_id === data.room_id))
                );
                typingTimeouts.current.delete(key);
              }, 3000);
              
              typingTimeouts.current.set(key, timeout);
            }
            break;

          case 'user_stopped_typing':
            if (data.user_id !== user.user_id) {
              setTypingUsers(prev => 
                prev.filter(u => !(u.user_id === data.user_id && u.room_id === data.room_id))
              );
              
              const key = `${data.user_id}-${data.room_id || 'global'}`;
              if (typingTimeouts.current.has(key)) {
                clearTimeout(typingTimeouts.current.get(key)!);
                typingTimeouts.current.delete(key);
              }
            }
            break;

          case 'user_joined':
          case 'user_left':
            // Handle room join/leave notifications
            if (data.user_id !== user.user_id) {
              toast(`${data.username} ${data.type === 'user_joined' ? 'joined' : 'left'} the room`);
            }
            break;

          case 'notification':
            notificationCallbacks.current.forEach(callback => callback(data));
            
            // Show toast notification
            if (data.notification_type === 'info') {
              toast(data.message || data.content, { icon: 'ℹ️' });
            } else if (data.notification_type === 'success') {
              toast.success(data.message || data.content);
            } else if (data.notification_type === 'warning') {
              toast(data.message || data.content, { icon: '⚠️' });
            } else if (data.notification_type === 'error') {
              toast.error(data.message || data.content);
            } else {
              toast(data.message || data.content);
            }
            break;

          case 'error':
            console.error('WebSocket error message:', data.error);
            toast.error(data.error);
            break;

          case 'ping':
            // Server ping - respond with pong
            newSocket.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
            break;

          case 'heartbeat':
            // Echo heartbeat back
            newSocket.send(JSON.stringify({ type: 'heartbeat' }));
            break;
            
          case 'auth_warning':
            console.warn('Authentication warning:', data.message);
            if (data.should_refresh) {
              toast('Token refresh recommended - please refresh your browser if you experience issues', {
                icon: '⚠️',
                duration: 5000
              });
            }
            break;

          case 'mcp_analysis_started':
          case 'mcp_analysis_completed':
          case 'mcp_analysis_failed':
            // Pass these through to message callbacks for handling in components
            messageCallbacks.current.forEach(callback => callback(data));
            break;

          default:
            console.log('Unhandled message type:', data.type);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    setSocket(newSocket);
  }, [user, token, socket]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    
    if (socket) {
      socket.close(1000, 'User disconnected');
      setSocket(null);
      setIsConnected(false);
      setOnlineUsers([]);
      setTypingUsers([]);
    }
  }, [socket]);

  const sendMessage = useCallback((message: any) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }
    
    socket.send(JSON.stringify(message));
  }, [socket]);

  const onMessage = (callback: (message: Message) => void) => {
    messageCallbacks.current.add(callback);
    
    return () => {
      messageCallbacks.current.delete(callback);
    };
  };

  const onNotification = (callback: (notification: any) => void) => {
    notificationCallbacks.current.add(callback);
    
    return () => {
      notificationCallbacks.current.delete(callback);
    };
  };

  const joinRoom = useCallback((roomId: string) => {
    sendMessage({ type: 'join_room', room_id: roomId });
  }, [sendMessage]);

  const leaveRoom = useCallback((roomId: string) => {
    sendMessage({ type: 'leave_room', room_id: roomId });
  }, [sendMessage]);

  const startTyping = useCallback((roomId?: string) => {
    sendMessage({ type: 'user_typing', room_id: roomId });
  }, [sendMessage]);

  const stopTyping = useCallback((roomId?: string) => {
    sendMessage({ type: 'user_stopped_typing', room_id: roomId });
  }, [sendMessage]);

  const updateStatus = useCallback((status: 'online' | 'away' | 'busy') => {
    sendMessage({ type: 'update_status', status });
  }, [sendMessage]);

  // Remove auto-connect - connections should be established only when needed
  // This prevents WebSocket connections on landing page and other non-interactive pages
  useEffect(() => {
    // Only disconnect if user logs out
    if (!user || !token) {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user, token, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    const currentTypingTimeouts = typingTimeouts.current;
    const currentMessageCallbacks = messageCallbacks.current;
    const currentNotificationCallbacks = notificationCallbacks.current;
    
    return () => {
      // Clear all typing timeouts
      currentTypingTimeouts.forEach(timeout => clearTimeout(timeout));
      currentTypingTimeouts.clear();
      
      // Clear callbacks
      currentMessageCallbacks.clear();
      currentNotificationCallbacks.clear();
      
      // Clear reconnect timeout
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      
      disconnect();
    };
  }, [disconnect]);

  // Handle page visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (socket && isConnected) {
        if (document.hidden) {
          updateStatus('away');
        } else {
          updateStatus('online');
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [socket, isConnected, updateStatus]);

  const contextValue: WebSocketContextType = {
    socket,
    isConnected,
    onlineUsers,
    typingUsers,
    connect,
    disconnect,
    sendMessage,
    onMessage,
    joinRoom,
    leaveRoom,
    startTyping,
    stopTyping,
    onNotification,
    updateStatus
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

// Hook to automatically connect when component mounts
export const useWebSocketConnection = () => {
  const { connect, disconnect, isConnected } = useWebSocket();
  const { user, token } = useAuthStore();

  useEffect(() => {
    // Only connect if authenticated and not already connected
    if (user && token && !isConnected) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      // Only disconnect if this was the component that initiated the connection
      // This prevents disconnecting when navigating between pages that both need WebSocket
    };
  }, [user, token, isConnected, connect]);

  return { isConnected };
};

export default WebSocketProvider;