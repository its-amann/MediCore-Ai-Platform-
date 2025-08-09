import { useEffect, useCallback } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import toast from 'react-hot-toast';

interface CollaborationMessage {
  type: 'room_created' | 'room_updated' | 'room_deleted' | 'participant_joined' | 'participant_left' | 'message' | 'typing' | 'stop_typing';
  room_id?: string;
  data: any;
}

interface UseCollaborationWebSocketProps {
  roomId?: string;
  onRoomUpdate?: (data: any) => void;
  onParticipantUpdate?: (data: any) => void;
  onMessage?: (message: any) => void;
  onTyping?: (userId: string, isTyping: boolean) => void;
}

export const useCollaborationWebSocket = ({
  roomId,
  onRoomUpdate,
  onParticipantUpdate,
  onMessage,
  onTyping
}: UseCollaborationWebSocketProps) => {
  const { socket, isConnected, sendMessage, joinRoom, leaveRoom, startTyping, stopTyping, onMessage: subscribeToMessage } = useWebSocket();

  // Handle incoming messages
  useEffect(() => {
    if (!isConnected) return;

    const unsubscribe = subscribeToMessage((message: any) => {
      if (message.type === 'collaboration') {
        const collabMessage = message.data as CollaborationMessage;
        
        switch (collabMessage.type) {
          case 'room_created':
          case 'room_updated':
          case 'room_deleted':
            onRoomUpdate?.(collabMessage.data);
            break;
            
          case 'participant_joined':
          case 'participant_left':
            onParticipantUpdate?.(collabMessage.data);
            break;
            
          case 'message':
            if (collabMessage.room_id === roomId) {
              onMessage?.(collabMessage.data);
            }
            break;
            
          case 'typing':
          case 'stop_typing':
            if (collabMessage.room_id === roomId) {
              onTyping?.(collabMessage.data.user_id, collabMessage.type === 'typing');
            }
            break;
        }
      }
    });

    return unsubscribe;
  }, [isConnected, roomId, onRoomUpdate, onParticipantUpdate, onMessage, onTyping, subscribeToMessage]);

  // Join room when component mounts
  useEffect(() => {
    if (roomId && isConnected) {
      joinRoom(roomId);
      
      return () => {
        leaveRoom(roomId);
      };
    }
  }, [roomId, isConnected, joinRoom, leaveRoom]);

  // Send collaboration message
  const sendCollaborationMessage = useCallback((type: string, data: any) => {
    if (!isConnected) {
      toast.error('Not connected to server');
      return;
    }

    sendMessage({
      type: 'collaboration',
      action: type,
      room_id: roomId,
      data
    });
  }, [isConnected, roomId, sendMessage]);

  // Send chat message
  const sendChatMessage = useCallback((content: string, attachments?: any[]) => {
    sendCollaborationMessage('send_message', {
      content,
      attachments
    });
  }, [sendCollaborationMessage]);

  // Typing indicators
  const handleStartTyping = useCallback(() => {
    if (roomId) {
      startTyping(roomId);
    }
  }, [roomId, startTyping]);

  const handleStopTyping = useCallback(() => {
    if (roomId) {
      stopTyping(roomId);
    }
  }, [roomId, stopTyping]);

  return {
    isConnected,
    sendChatMessage,
    startTyping: handleStartTyping,
    stopTyping: handleStopTyping,
    sendCollaborationMessage
  };
};