import { useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { RoomWebSocketMessage } from '../types/websocket';
import { Message } from '../types/room';
import toast from 'react-hot-toast';

interface UseRoomWebSocketProps {
  roomId: string;
  onMessage?: (message: Message) => void;
  onParticipantJoined?: (participant: any) => void;
  onParticipantLeft?: (userId: string, username: string) => void;
  onMediaStateChange?: (userId: string, state: any) => void;
  onHandRaise?: (userId: string, raised: boolean) => void;
  onRoomStatusUpdate?: (status: string) => void;
  onParticipantsUpdate?: (participants: any[]) => void;
}

export const useRoomWebSocket = ({
  roomId,
  onMessage,
  onParticipantJoined,
  onParticipantLeft,
  onMediaStateChange,
  onHandRaise,
  onRoomStatusUpdate,
  onParticipantsUpdate
}: UseRoomWebSocketProps) => {
  const { onMessage: wsOnMessage, sendMessage: wsSendMessage } = useWebSocket();
  const handlersRef = useRef({
    onMessage,
    onParticipantJoined,
    onParticipantLeft,
    onMediaStateChange,
    onHandRaise,
    onRoomStatusUpdate,
    onParticipantsUpdate
  });

  // Update handlers ref
  useEffect(() => {
    handlersRef.current = {
      onMessage,
      onParticipantJoined,
      onParticipantLeft,
      onMediaStateChange,
      onHandRaise,
      onRoomStatusUpdate,
      onParticipantsUpdate
    };
  });

  // Send room-specific message
  const sendRoomMessage = useCallback((message: Partial<RoomWebSocketMessage>) => {
    wsSendMessage({
      ...message,
      room_id: roomId
    });
  }, [roomId, wsSendMessage]);

  // Handle incoming messages
  useEffect(() => {
    const unsubscribe = wsOnMessage((message: any) => {
      // Only handle messages for this room
      if (message.room_id && message.room_id !== roomId) return;

      const wsMessage = message as RoomWebSocketMessage;

      switch (wsMessage.type) {
        case 'chat_message':
          if (handlersRef.current.onMessage) {
            const chatMessage: Message = {
              id: message.id || Date.now().toString(),
              content: message.content,
              sender_id: message.sender_id,
              sender_name: message.sender_name,
              sender_type: message.sender_type || 'user',
              timestamp: message.timestamp || new Date().toISOString(),
              room_id: roomId,
              status: 'delivered',
              metadata: message.metadata
            };
            handlersRef.current.onMessage(chatMessage);
          }
          break;

        case 'user_joined':
          if (handlersRef.current.onParticipantJoined) {
            handlersRef.current.onParticipantJoined({
              user_id: wsMessage.user_id,
              username: wsMessage.username,
              role: wsMessage.role,
              joined_at: new Date().toISOString()
            });
          }
          toast(`${wsMessage.username} joined the room`);
          break;

        case 'user_left':
          if (handlersRef.current.onParticipantLeft) {
            handlersRef.current.onParticipantLeft(wsMessage.user_id, wsMessage.username);
          }
          toast(`${wsMessage.username} left the room`);
          break;

        case 'media_state_change':
          if (handlersRef.current.onMediaStateChange) {
            handlersRef.current.onMediaStateChange(wsMessage.user_id, {
              is_muted: wsMessage.is_muted,
              is_video_on: wsMessage.is_video_on,
              is_screen_sharing: wsMessage.is_screen_sharing
            });
          }
          break;

        case 'hand_raise':
          if (handlersRef.current.onHandRaise) {
            handlersRef.current.onHandRaise(wsMessage.user_id, wsMessage.raised);
          }
          break;

        case 'room_status_update':
          if (handlersRef.current.onRoomStatusUpdate) {
            handlersRef.current.onRoomStatusUpdate(wsMessage.status);
          }
          break;

        case 'participants_update':
          if (handlersRef.current.onParticipantsUpdate) {
            handlersRef.current.onParticipantsUpdate(wsMessage.participants);
          }
          break;
      }
    });

    return unsubscribe;
  }, [roomId, wsOnMessage]);

  // WebRTC signaling helpers
  const sendOffer = useCallback((toUserId: string, offer: RTCSessionDescriptionInit) => {
    sendRoomMessage({
      type: 'webrtc_offer',
      to_user_id: toUserId,
      offer
    });
  }, [sendRoomMessage]);

  const sendAnswer = useCallback((toUserId: string, answer: RTCSessionDescriptionInit) => {
    sendRoomMessage({
      type: 'webrtc_answer',
      to_user_id: toUserId,
      answer
    });
  }, [sendRoomMessage]);

  const sendIceCandidate = useCallback((toUserId: string, candidate: RTCIceCandidateInit) => {
    sendRoomMessage({
      type: 'webrtc_ice_candidate',
      to_user_id: toUserId,
      candidate
    });
  }, [sendRoomMessage]);

  return {
    sendRoomMessage,
    sendOffer,
    sendAnswer,
    sendIceCandidate
  };
};