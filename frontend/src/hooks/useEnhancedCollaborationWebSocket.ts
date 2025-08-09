import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { toast } from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import {
  ExtendedMessage,
  WebRTCSignal,
  ScreenShareSession,
  ScreenShareEvent,
  GeminiLiveSession,
  AIResponse,
  Notification,
  UserProfile,
  MediaState,
  MessageReaction,
  ScreenShareStatus,
  CollaborationWebSocketEvent
} from '../types/collaboration';

interface UseEnhancedCollaborationWebSocketProps {
  roomId: string;
  onMessageReceived?: (message: ExtendedMessage) => void;
  onScreenShareUpdate?: (session: ScreenShareSession) => void;
  onAIResponse?: (response: AIResponse) => void;
  onNotification?: (notification: Notification) => void;
  onUserTyping?: (userId: string, isTyping: boolean) => void;
  onParticipantUpdate?: (participants: UserProfile[]) => void;
  onWebRTCSignal?: (signal: WebRTCSignal) => void;
  onMediaStateChange?: (userId: string, state: MediaState) => void;
}

interface WebSocketState {
  isConnected: boolean;
  isReconnecting: boolean;
  error: string | null;
  latency: number;
}

export const useEnhancedCollaborationWebSocket = ({
  roomId,
  onMessageReceived,
  onScreenShareUpdate,
  onAIResponse,
  onNotification,
  onUserTyping,
  onParticipantUpdate,
  onWebRTCSignal,
  onMediaStateChange
}: UseEnhancedCollaborationWebSocketProps) => {
  const { user, token } = useAuthStore();
  const socketRef = useRef<Socket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const pingIntervalRef = useRef<NodeJS.Timeout>();
  
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isReconnecting: false,
    error: null,
    latency: 0
  });

  const [typingUsers, setTypingUsers] = useState<Map<string, NodeJS.Timeout>>(new Map());

  // Initialize WebSocket connection
  useEffect(() => {
    if (!user || !token || !roomId) return;

    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    
    socketRef.current = io(wsUrl, {
      path: '/ws/collaboration',
      auth: { token },
      query: { roomId },
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000
    });

    const socket = socketRef.current;

    // Connection events
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setState(prev => ({ ...prev, isConnected: true, isReconnecting: false, error: null }));
      
      // Join room
      socket.emit('join:room', { roomId, userId: user.user_id });
      
      // Start ping interval for latency measurement
      pingIntervalRef.current = setInterval(() => {
        const start = Date.now();
        socket.emit('ping', {}, () => {
          setState(prev => ({ ...prev, latency: Date.now() - start }));
        });
      }, 5000);
    });

    socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setState(prev => ({ ...prev, isConnected: false }));
      
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    });

    socket.on('reconnecting', (attemptNumber) => {
      console.log('WebSocket reconnecting:', attemptNumber);
      setState(prev => ({ ...prev, isReconnecting: true }));
    });

    socket.on('error', (error) => {
      console.error('WebSocket error:', error);
      setState(prev => ({ ...prev, error: error.message || 'Connection error' }));
      toast.error('Connection error. Please check your network.');
    });

    // Clean up on unmount
    return () => {
      if (socket) {
        socket.emit('leave:room', { roomId, userId: user.user_id });
        socket.disconnect();
      }
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      
      // Clear typing timeouts
      typingUsers.forEach(timeout => clearTimeout(timeout));
    };
  }, [user, token, roomId]);

  // Message events
  useEffect(() => {
    if (!socketRef.current) return;
    const socket = socketRef.current;

    // Standard message events
    socket.on('message:receive', (message: ExtendedMessage) => {
      if (onMessageReceived) {
        onMessageReceived(message);
      }
    });

    socket.on('message:edit', (data: { messageId: string; newContent: string; editedAt: string }) => {
      // Handle message edit - update local state in parent component
      console.log('Message edited:', data);
    });

    socket.on('message:delete', (data: { messageId: string }) => {
      // Handle message deletion - update local state in parent component
      console.log('Message deleted:', data);
    });

    socket.on('message:reaction:add', (data: { messageId: string; emoji: string; userId: string }) => {
      // Handle reaction addition
      console.log('Reaction added:', data);
    });

    socket.on('message:reaction:remove', (data: { messageId: string; emoji: string; userId: string }) => {
      // Handle reaction removal
      console.log('Reaction removed:', data);
    });

    socket.on('user:typing', (data: { userId: string; isTyping: boolean }) => {
      if (onUserTyping) {
        onUserTyping(data.userId, data.isTyping);
      }

      // Manage typing indicators with timeout
      if (data.isTyping) {
        // Clear existing timeout for this user
        const existingTimeout = typingUsers.get(data.userId);
        if (existingTimeout) {
          clearTimeout(existingTimeout);
        }

        // Set new timeout to clear typing after 3 seconds
        const timeout = setTimeout(() => {
          if (onUserTyping) {
            onUserTyping(data.userId, false);
          }
          typingUsers.delete(data.userId);
        }, 3000);

        setTypingUsers(new Map(typingUsers.set(data.userId, timeout)));
      } else {
        // Clear typing immediately
        const timeout = typingUsers.get(data.userId);
        if (timeout) {
          clearTimeout(timeout);
          typingUsers.delete(data.userId);
        }
      }
    });

    return () => {
      socket.off('message:receive');
      socket.off('message:edit');
      socket.off('message:delete');
      socket.off('message:reaction:add');
      socket.off('message:reaction:remove');
      socket.off('user:typing');
    };
  }, [onMessageReceived, onUserTyping, typingUsers]);

  // Screen share events
  useEffect(() => {
    if (!socketRef.current) return;
    const socket = socketRef.current;

    socket.on('screen:share:start', (session: ScreenShareSession) => {
      if (onScreenShareUpdate) {
        onScreenShareUpdate(session);
      }
      toast(`${session.user_id} started screen sharing`, { icon: 'ℹ️' });
    });

    socket.on('screen:share:stop', (data: { sessionId: string; userId: string }) => {
      toast('Screen sharing ended', { icon: 'ℹ️' });
    });

    socket.on('screen:quality:change', (data: { sessionId: string; quality: string }) => {
      console.log('Screen share quality changed:', data);
    });

    socket.on('screen:control:request', (data: { sessionId: string; userId: string; userName: string }) => {
      // Show notification for control request
      toast(`${data.userName} requested screen control`, { icon: 'ℹ️' });
    });

    socket.on('screen:control:grant', (data: { sessionId: string; userId: string }) => {
      toast.success('Screen control granted');
    });

    return () => {
      socket.off('screen:share:start');
      socket.off('screen:share:stop');
      socket.off('screen:quality:change');
      socket.off('screen:control:request');
      socket.off('screen:control:grant');
    };
  }, [onScreenShareUpdate]);

  // AI assistant events
  useEffect(() => {
    if (!socketRef.current) return;
    const socket = socketRef.current;

    socket.on('ai:response', (response: AIResponse) => {
      if (onAIResponse) {
        onAIResponse(response);
      }
    });

    socket.on('ai:session:start', (session: GeminiLiveSession) => {
      toast.success(`AI ${session.mode} session started`);
    });

    socket.on('ai:session:end', (data: { sessionId: string }) => {
      toast('AI session ended', { icon: 'ℹ️' });
    });

    return () => {
      socket.off('ai:response');
      socket.off('ai:session:start');
      socket.off('ai:session:end');
    };
  }, [onAIResponse]);

  // Notification events
  useEffect(() => {
    if (!socketRef.current) return;
    const socket = socketRef.current;

    socket.on('notification:new', (notification: Notification) => {
      if (onNotification) {
        onNotification(notification);
      }

      // Show toast for urgent notifications
      if (notification.priority === 'urgent') {
        toast.error(notification.message, { duration: 5000 });
      }
    });

    return () => {
      socket.off('notification:new');
    };
  }, [onNotification]);

  // Participant events
  useEffect(() => {
    if (!socketRef.current) return;
    const socket = socketRef.current;

    socket.on('participants:update', (participants: UserProfile[]) => {
      if (onParticipantUpdate) {
        onParticipantUpdate(participants);
      }
    });

    socket.on('participant:joined', (user: UserProfile) => {
      toast(`${user.full_name || user.username} joined the room`, { icon: 'ℹ️' });
    });

    socket.on('participant:left', (user: UserProfile) => {
      toast(`${user.full_name || user.username} left the room`, { icon: 'ℹ️' });
    });

    return () => {
      socket.off('participants:update');
      socket.off('participant:joined');
      socket.off('participant:left');
    };
  }, [onParticipantUpdate]);

  // WebRTC signaling events
  useEffect(() => {
    if (!socketRef.current) return;
    const socket = socketRef.current;

    const webRTCEvents = [
      'video:offer',
      'video:answer',
      'video:ice-candidate',
      'screen:share:offer',
      'screen:share:answer',
      'screen:share:candidate'
    ];

    webRTCEvents.forEach(event => {
      socket.on(event, (signal: WebRTCSignal) => {
        if (onWebRTCSignal) {
          onWebRTCSignal(signal);
        }
      });
    });

    socket.on('media:state:change', (data: { userId: string; state: MediaState }) => {
      if (onMediaStateChange) {
        onMediaStateChange(data.userId, data.state);
      }
    });

    return () => {
      webRTCEvents.forEach(event => socket.off(event));
      socket.off('media:state:change');
    };
  }, [onWebRTCSignal, onMediaStateChange]);

  // Emit functions
  const sendMessage = useCallback((content: string, mentions: string[] = [], replyToId?: string, attachments?: File[]) => {
    if (!socketRef.current || !state.isConnected) return;

    const message = {
      roomId,
      content,
      mentions,
      replyToId,
      attachments: attachments?.map(f => ({
        filename: f.name,
        file_type: f.type,
        file_size: f.size
      }))
    };

    socketRef.current.emit('message:send', message);
  }, [roomId, state.isConnected]);

  const sendReaction = useCallback((messageId: string, emoji: string) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('message:reaction:toggle', {
      roomId,
      messageId,
      emoji
    });
  }, [roomId, state.isConnected]);

  const editMessage = useCallback((messageId: string, newContent: string) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('message:edit', {
      roomId,
      messageId,
      newContent
    });
  }, [roomId, state.isConnected]);

  const deleteMessage = useCallback((messageId: string) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('message:delete', {
      roomId,
      messageId
    });
  }, [roomId, state.isConnected]);

  const sendTypingIndicator = useCallback((isTyping: boolean) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('user:typing', {
      roomId,
      isTyping
    });
  }, [roomId, state.isConnected]);

  const startScreenShare = useCallback((sourceType: string, quality: string) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('screen:share:start', {
      roomId,
      sourceType,
      quality
    });
  }, [roomId, state.isConnected]);

  const stopScreenShare = useCallback(() => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('screen:share:stop', {
      roomId
    });
  }, [roomId, state.isConnected]);

  const updateScreenShareQuality = useCallback((quality: string) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('screen:quality:change', {
      roomId,
      quality
    });
  }, [roomId, state.isConnected]);

  const requestScreenControl = useCallback(() => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('screen:control:request', {
      roomId
    });
  }, [roomId, state.isConnected]);

  const sendWebRTCSignal = useCallback((signal: WebRTCSignal) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit(`video:${signal.type}`, signal);
  }, [state.isConnected]);

  const updateMediaState = useCallback((mediaState: MediaState) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('media:state:update', {
      roomId,
      state: mediaState
    });
  }, [roomId, state.isConnected]);

  const startAISession = useCallback((mode: string) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('ai:session:start', {
      roomId,
      mode
    });
  }, [roomId, state.isConnected]);

  const sendAIMessage = useCallback((message: string, mode: string) => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('ai:message', {
      roomId,
      message,
      mode
    });
  }, [roomId, state.isConnected]);

  const endAISession = useCallback(() => {
    if (!socketRef.current || !state.isConnected) return;
    
    socketRef.current.emit('ai:session:end', {
      roomId
    });
  }, [roomId, state.isConnected]);

  return {
    // Connection state
    ...state,
    
    // Message functions
    sendMessage,
    sendReaction,
    editMessage,
    deleteMessage,
    sendTypingIndicator,
    
    // Screen share functions
    startScreenShare,
    stopScreenShare,
    updateScreenShareQuality,
    requestScreenControl,
    
    // WebRTC functions
    sendWebRTCSignal,
    updateMediaState,
    
    // AI functions
    startAISession,
    sendAIMessage,
    endAISession
  };
};