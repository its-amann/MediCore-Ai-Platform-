import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Room, RoomParticipant, Message, RoomStatus, RoomType } from '../types/room';
import { collaborationService, CreateRoomRequest } from '../services/collaborationService';
import { useWebSocket } from './WebSocketContext';
import toast from 'react-hot-toast';

interface RoomContextType {
  // Room state
  room: Room | null;
  participants: RoomParticipant[];
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  
  // Participant state
  isHost: boolean;
  isModerator: boolean;
  
  // Chat state
  typingUsers: string[];
  unreadCount: number;
  
  // Video state (for teaching rooms)
  localStream: MediaStream | null;
  remoteStreams: Map<string, MediaStream>;
  isMuted: boolean;
  isVideoOn: boolean;
  isScreenSharing: boolean;
  
  // Actions
  loadRoom: (roomId: string) => Promise<void>;
  sendMessage: (content: string, attachments?: any[]) => Promise<void>;
  toggleMute: () => void;
  toggleVideo: () => void;
  toggleScreenShare: () => void;
  leaveRoom: () => Promise<void>;
  kickParticipant: (userId: string) => Promise<void>;
  updateRoomSettings: (settings: Partial<Room>) => Promise<void>;
  markMessagesAsRead: () => void;
}

const RoomContext = createContext<RoomContextType | null>(null);

export const useRoom = () => {
  const context = useContext(RoomContext);
  if (!context) {
    throw new Error('useRoom must be used within a RoomProvider');
  }
  return context;
};

interface RoomProviderProps {
  children: ReactNode;
  roomId: string;
}

export const RoomProvider: React.FC<RoomProviderProps> = ({ children, roomId }) => {
  const { 
    joinRoom: wsJoinRoom, 
    leaveRoom: wsLeaveRoom, 
    sendMessage: wsSendMessage,
    onMessage,
    startTyping,
    stopTyping,
    typingUsers: wsTypingUsers
  } = useWebSocket();
  
  const [room, setRoom] = useState<Room | null>(null);
  const [participants, setParticipants] = useState<RoomParticipant[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  
  // Video state
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteStreams, setRemoteStreams] = useState<Map<string, MediaStream>>(new Map());
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  
  // Get current user from localStorage (you might want to get this from auth context)
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isHost = room?.host_id === currentUser.user_id;
  const isModerator = participants.find(p => p.user_id === currentUser.user_id)?.role === 'moderator' || isHost;
  
  // Filter typing users for current room
  const typingUsers = wsTypingUsers
    .filter(u => u.room_id === roomId && u.user_id !== currentUser.user_id)
    .map(u => u.username);
  
  // Load room data
  const loadRoom = useCallback(async (roomId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Load room details
      const roomData = await collaborationService.getRoom(roomId);
      setRoom(roomData);
      
      // Load participants
      const participantsData = await collaborationService.getRoomParticipants(roomId);
      setParticipants(participantsData);
      
      // Load messages
      const messagesData = await collaborationService.getRoomMessages(roomId);
      setMessages(messagesData);
      
      // Join room via WebSocket
      wsJoinRoom(roomId);
      
      // For teaching rooms, initialize media
      if (roomData.room_type === 'teaching') {
        await initializeMedia();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load room');
      toast.error('Failed to load room');
    } finally {
      setIsLoading(false);
    }
  }, [wsJoinRoom]);
  
  // Initialize media for teaching rooms
  const initializeMedia = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });
      setLocalStream(stream);
    } catch (err) {
      console.error('Failed to get media devices:', err);
      toast.error('Failed to access camera/microphone');
    }
  };
  
  // Send message
  const sendMessage = useCallback(async (content: string, attachments?: any[]) => {
    try {
      const message = await collaborationService.sendMessage(roomId, content, attachments);
      
      // Send via WebSocket for real-time delivery
      wsSendMessage({
        type: 'chat_message',
        room_id: roomId,
        content,
        attachments
      });
      
      // Optimistically add to messages
      setMessages(prev => [...prev, {
        id: message.message_id,
        content,
        sender_id: currentUser.user_id,
        sender_name: currentUser.username,
        sender_type: 'user',
        timestamp: new Date().toISOString(),
        room_id: roomId,
        status: 'sent'
      }]);
    } catch (err) {
      toast.error('Failed to send message');
    }
  }, [roomId, currentUser, wsSendMessage]);
  
  // Toggle mute
  const toggleMute = useCallback(() => {
    if (localStream) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMuted(!audioTrack.enabled);
        
        // Notify other participants
        wsSendMessage({
          type: 'media_state_change',
          room_id: roomId,
          is_muted: !audioTrack.enabled
        });
      }
    }
  }, [localStream, roomId, wsSendMessage]);
  
  // Toggle video
  const toggleVideo = useCallback(() => {
    if (localStream) {
      const videoTrack = localStream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoOn(videoTrack.enabled);
        
        // Notify other participants
        wsSendMessage({
          type: 'media_state_change',
          room_id: roomId,
          is_video_on: videoTrack.enabled
        });
      }
    }
  }, [localStream, roomId, wsSendMessage]);
  
  // Toggle screen share
  const toggleScreenShare = useCallback(async () => {
    if (!isScreenSharing) {
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false
        });
        
        // Replace video track with screen share
        const videoTrack = screenStream.getVideoTracks()[0];
        const sender = localStream?.getVideoTracks()[0];
        
        if (sender) {
          // Store original video track and replace with screen share
          // This is a simplified version - you'd need WebRTC peer connection handling
          setIsScreenSharing(true);
          
          videoTrack.onended = () => {
            setIsScreenSharing(false);
            // Restore original video
          };
        }
      } catch (err) {
        console.error('Failed to share screen:', err);
        toast.error('Failed to share screen');
      }
    } else {
      // Stop screen sharing
      setIsScreenSharing(false);
      // Restore original video track
    }
  }, [isScreenSharing, localStream]);
  
  // Leave room
  const leaveRoom = useCallback(async () => {
    try {
      await collaborationService.leaveRoom(roomId);
      wsLeaveRoom(roomId);
      
      // Clean up media streams
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        setLocalStream(null);
      }
      
      remoteStreams.forEach(stream => {
        stream.getTracks().forEach(track => track.stop());
      });
      setRemoteStreams(new Map());
    } catch (err) {
      toast.error('Failed to leave room');
    }
  }, [roomId, localStream, remoteStreams, wsLeaveRoom]);
  
  // Kick participant (moderator only)
  const kickParticipant = useCallback(async (userId: string) => {
    if (!isModerator) {
      toast.error('Only moderators can remove participants');
      return;
    }
    
    try {
      await collaborationService.removeParticipant(roomId, userId);
      setParticipants(prev => prev.filter(p => p.user_id !== userId));
    } catch (err) {
      toast.error('Failed to remove participant');
    }
  }, [roomId, isModerator]);
  
  // Update room settings (host only)
  const updateRoomSettings = useCallback(async (settings: Partial<Room>) => {
    if (!isHost) {
      toast.error('Only the host can update room settings');
      return;
    }
    
    try {
      // Convert Room settings to CreateRoomRequest format
      const updateData: Partial<CreateRoomRequest> = {
        name: settings.name,
        description: settings.description,
        room_type: settings.room_type as RoomType,
        max_participants: settings.max_participants,
        is_private: settings.is_private,
        tags: settings.tags
      };
      
      const updatedRoom = await collaborationService.updateRoom(roomId, updateData);
      setRoom(updatedRoom);
    } catch (err) {
      toast.error('Failed to update room settings');
    }
  }, [roomId, isHost]);
  
  // Mark messages as read
  const markMessagesAsRead = useCallback(() => {
    setUnreadCount(0);
  }, []);
  
  // Handle incoming WebSocket messages
  React.useEffect(() => {
    const unsubscribe = onMessage((message) => {
      if (message.room_id !== roomId) return;
      
      switch (message.type) {
        case 'chat':
          setMessages(prev => [...prev, message]);
          if (message.sender_id !== currentUser.user_id) {
            setUnreadCount(prev => prev + 1);
          }
          break;
          
        case 'notification':
          // Handle room notifications
          if (message.metadata?.notification_type === 'user_joined') {
            const newParticipant = message.metadata.participant;
            setParticipants(prev => [...prev, newParticipant]);
            toast(`${newParticipant.username} joined the room`);
          } else if (message.metadata?.notification_type === 'user_left') {
            const userId = message.metadata.user_id;
            setParticipants(prev => prev.filter(p => p.user_id !== userId));
            toast(`${message.metadata.username} left the room`);
          }
          break;
      }
    });
    
    return unsubscribe;
  }, [roomId, currentUser.user_id, onMessage]);
  
  const value: RoomContextType = {
    room,
    participants,
    messages,
    isLoading,
    error,
    isHost,
    isModerator,
    typingUsers,
    unreadCount,
    localStream,
    remoteStreams,
    isMuted,
    isVideoOn,
    isScreenSharing,
    loadRoom,
    sendMessage,
    toggleMute,
    toggleVideo,
    toggleScreenShare,
    leaveRoom,
    kickParticipant,
    updateRoomSettings,
    markMessagesAsRead
  };
  
  return (
    <RoomContext.Provider value={value}>
      {children}
    </RoomContext.Provider>
  );
};

export default RoomContext;