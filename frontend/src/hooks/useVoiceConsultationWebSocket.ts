/**
 * WebSocket Hook for Voice Consultation
 * Manages real-time communication with the voice consultation service
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import toast from 'react-hot-toast';

export type MessageType = 
  | 'audio'
  | 'text'
  | 'set_mode'
  | 'get_info'
  | 'end_session'
  | 'enable_camera'
  | 'enable_screen_share'
  | 'ping';

export type ResponseType = 
  | 'session_started'
  | 'processing'
  | 'response'
  | 'mode_changed'
  | 'session_info'
  | 'session_ended'
  | 'pong'
  | 'error'
  | 'connection_established'
  | 'transcription'
  | 'ai_response'
  | 'audio_response'
  | 'mode_switched'
  | 'camera_status'
  | 'screen_share_status'
  | 'system_message'
  | 'chat_history';

export interface WebSocketMessage {
  type: MessageType;
  audio?: string;
  format?: string;
  text?: string;
  mode?: 'audio' | 'video' | 'screen_share';  // Backend uses 'audio' not 'voice'
  enabled?: boolean;  // For camera/screen share toggles
  timestamp?: number;
}

export interface WebSocketResponse {
  type: ResponseType;
  data?: any;
  message?: string;
  timestamp?: number;
}

interface UseVoiceConsultationWebSocketProps {
  sessionId: string | null;
  userId?: string | null;
  onMessage?: (response: WebSocketResponse) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: any) => void;
}

export const useVoiceConsultationWebSocket = ({
  sessionId,
  userId,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
}: UseVoiceConsultationWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!sessionId || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    const userIdParam = userId ? `?user_id=${userId}` : '';
    const wsUrl = `${baseUrl}/api/v1/voice/consultation/ws/${sessionId}${userIdParam}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Voice WebSocket connected');
        setIsConnected(true);
        onConnect?.();

        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          sendMessage({ type: 'ping', timestamp: Date.now() });
        }, 30000); // Ping every 30 seconds
      };

      ws.onmessage = (event) => {
        try {
          const response: WebSocketResponse = JSON.parse(event.data);
          
          // Handle processing state
          if (response.type === 'processing') {
            setIsProcessing(true);
          } else if (response.type === 'response' || response.type === 'error') {
            setIsProcessing(false);
          }

          onMessage?.(response);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          onError?.(error);
        }
      };

      ws.onerror = (error) => {
        console.error('Voice WebSocket error:', error);
        onError?.(error);
        toast.error('Connection error occurred');
      };

      ws.onclose = (event) => {
        console.log('Voice WebSocket disconnected', event);
        setIsConnected(false);
        setIsProcessing(false);
        onDisconnect?.();

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Only attempt to reconnect if it was an abnormal closure (not user-initiated)
        // and we still have a valid session
        if (sessionId && event.code !== 1000 && event.code !== 1001) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connect();
          }, 3000);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      onError?.(error);
      toast.error('Failed to establish connection');
    }
  }, [sessionId, userId, onConnect, onDisconnect, onError, onMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsProcessing(false);
  }, []);

  // Send message through WebSocket
  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      toast.error('Connection not established');
      return false;
    }

    try {
      wsRef.current.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
      return false;
    }
  }, []);

  // Send audio data
  const sendAudio = useCallback((audioData: string, format: string = 'webm') => {
    return sendMessage({
      type: 'audio',
      audio: audioData,
      format,
    });
  }, [sendMessage]);

  // Send text message
  const sendText = useCallback((text: string) => {
    return sendMessage({
      type: 'text',
      text,
    });
  }, [sendMessage]);

  // Change consultation mode
  const setMode = useCallback((mode: 'audio' | 'video' | 'screen_share') => {
    return sendMessage({
      type: 'set_mode',
      mode,
    });
  }, [sendMessage]);

  // Get session information
  const getSessionInfo = useCallback(() => {
    return sendMessage({
      type: 'get_info',
    });
  }, [sendMessage]);

  // End session
  const endSession = useCallback(() => {
    // Notify backend to end the session, then disconnect
    sendMessage({ type: 'end_session' });
    disconnect();
    return true;
  }, [disconnect, sendMessage]);

  // Connect when sessionId is available
  useEffect(() => {
    if (sessionId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [sessionId]); // Only depend on sessionId to avoid reconnection loops
  
  // Suppress eslint warnings for missing dependencies since we intentionally
  // want this effect to only run when sessionId changes
  // eslint-disable-next-line react-hooks/exhaustive-deps

  return {
    isConnected,
    isProcessing,
    connect,
    disconnect,
    sendMessage,
    sendAudio,
    sendText,
    setMode,
    getSessionInfo,
    endSession,
  };
};