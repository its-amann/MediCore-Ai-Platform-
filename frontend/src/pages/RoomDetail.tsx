import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { buildRoomWebSocketUrl, buildVoiceWebSocketUrl } from '../utils/websocketUtils';
import {
  UserGroupIcon,
  PaperAirplaneIcon,
  MicrophoneIcon,
  PhoneXMarkIcon,
  ArrowLeftIcon,
  PaperClipIcon,
  EllipsisVerticalIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ComputerDesktopIcon,
  HandRaisedIcon
} from '@heroicons/react/24/outline';
import { MicrophoneIcon as MicrophoneSolidIcon } from '@heroicons/react/24/solid';
import api from '../api/axios';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

interface Message {
  message_id: string;
  user_id: string;
  username: string;
  content: string;
  timestamp: string;
  type: 'text' | 'system' | 'file';
  metadata?: {
    filename?: string;
    file_url?: string;
  };
}

interface Participant {
  user_id: string;
  username: string;
  role: string;
  joined_at: string;
  is_speaking?: boolean;
  is_muted?: boolean;
  has_raised_hand?: boolean;
}

interface RoomDetails {
  room_id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  voice_enabled: boolean;
  screen_sharing: boolean;
  created_by: {
    user_id: string;
    username: string;
  };
  participants: Participant[];
  moderators: string[];
}

const RoomDetail: React.FC = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [room, setRoom] = useState<RoomDetails | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [hasRaisedHand, setHasRaisedHand] = useState(false);
  const [showParticipants, setShowParticipants] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const voiceWsRef = useRef<WebSocket | null>(null);
  const messageInputRef = useRef<HTMLInputElement>(null);

  // Fetch room details
  const fetchRoomDetails = useCallback(async () => {
    if (!roomId) {
      console.error('Room ID is required');
      toast.error('Invalid room ID');
      navigate('/rooms');
      return;
    }
    
    try {
      const response = await api.get(`/rooms/${roomId}`);
      setRoom(response.data);
      
      // Fetch participants separately
      try {
        const participantsResponse = await api.get(`/rooms/${roomId}/participants`);
        setParticipants(participantsResponse.data || []);
      } catch (error) {
        console.error('Failed to fetch participants:', error);
        setParticipants([]);
      }
    } catch (error) {
      console.error('Failed to fetch room details:', error);
      toast.error('Failed to load room details');
      navigate('/rooms');
    }
  }, [roomId, navigate]);

  // Fetch message history
  const fetchMessages = useCallback(async () => {
    if (!roomId) {
      console.error('Room ID is required for fetching messages');
      return;
    }
    
    try {
      const response = await api.get(`/rooms/${roomId}/messages`);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  }, [roomId]);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (!roomId) {
      console.error('Room ID is required for WebSocket connection');
      toast.error('Invalid room ID');
      navigate('/rooms');
      return;
    }
    
    const wsUrl = buildRoomWebSocketUrl(roomId);
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      wsRef.current?.send(JSON.stringify({
        type: 'join',
        data: {
          user_id: user?.user_id,
          username: user?.username
        }
      }));
    };

    wsRef.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      toast.error('Connection error');
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          connectWebSocket();
        }
      }, 3000);
    };
  }, [roomId, user, navigate]);

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'message':
        setMessages(prev => [...prev, message.data]);
        break;
      case 'user_joined':
        setParticipants(prev => [...prev, message.data]);
        toast(`${message.data.username} joined the room`);
        break;
      case 'user_left':
        setParticipants(prev => prev.filter(p => p.user_id !== message.data.user_id));
        toast(`${message.data.username} left the room`);
        break;
      case 'participants_update':
        setParticipants(message.data.participants);
        break;
      case 'room_status_update':
        setRoom(prev => prev ? { ...prev, status: message.data.status } : null);
        break;
    }
  };

  // Send message
  const sendMessage = () => {
    if (!newMessage.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'message',
      data: {
        content: newMessage.trim()
      }
    }));

    setNewMessage('');
  };

  // Toggle voice
  const toggleVoice = () => {
    if (!room?.voice_enabled) {
      toast.error('Voice is not enabled for this room');
      return;
    }

    if (isVoiceEnabled) {
      // Disconnect voice
      if (voiceWsRef.current) {
        voiceWsRef.current.close();
        voiceWsRef.current = null;
      }
      setIsVoiceEnabled(false);
      setIsMuted(true);
    } else {
      // Connect voice
      if (!roomId) {
        toast.error('Invalid room ID for voice connection');
        return;
      }
      
      const voiceWsUrl = buildVoiceWebSocketUrl(roomId);
      voiceWsRef.current = new WebSocket(voiceWsUrl);
      
      voiceWsRef.current.onopen = () => {
        setIsVoiceEnabled(true);
        toast.success('Voice connected');
      };

      voiceWsRef.current.onerror = () => {
        toast.error('Failed to connect voice');
        setIsVoiceEnabled(false);
      };
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (!isVoiceEnabled) return;
    
    setIsMuted(!isMuted);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'voice_status',
        data: {
          is_muted: !isMuted
        }
      }));
    }
  };

  // Toggle hand raise
  const toggleHandRaise = () => {
    setHasRaisedHand(!hasRaisedHand);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'hand_raise',
        data: {
          raised: !hasRaisedHand
        }
      }));
    }
  };

  // Leave room
  const leaveRoom = async () => {
    if (!roomId) {
      console.error('Room ID is required to leave room');
      navigate('/rooms');
      return;
    }
    
    try {
      await api.post(`/rooms/${roomId}/leave`);
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (voiceWsRef.current) {
        voiceWsRef.current.close();
      }
      navigate('/rooms');
    } catch (error) {
      console.error('Failed to leave room:', error);
    }
  };

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    fetchRoomDetails();
    fetchMessages();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (voiceWsRef.current) {
        voiceWsRef.current.close();
      }
    };
  }, [fetchRoomDetails, fetchMessages, connectWebSocket]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    setLoading(false);
  }, [room]);

  // Early return if roomId is undefined
  if (!roomId) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-red-600 mb-4">Invalid room ID</p>
          <button
            onClick={() => navigate('/rooms')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Rooms
          </button>
        </div>
      </div>
    );
  }

  if (loading || !room) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }


  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Room Header */}
        <div className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => navigate('/rooms')}
                className="mr-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeftIcon className="h-5 w-5 text-gray-600" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{room.name}</h1>
                <div className="flex items-center mt-1">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    room.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {room.status}
                  </span>
                  <span className="ml-3 text-sm text-gray-600">
                    {participants.length} participants
                  </span>
                  {!isConnected && (
                    <span className="ml-3 text-sm text-red-600">Reconnecting...</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {/* Voice Controls */}
              {room.voice_enabled && (
                <>
                  <button
                    onClick={toggleVoice}
                    className={`p-2 rounded-lg transition-colors ${
                      isVoiceEnabled 
                        ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                    title={isVoiceEnabled ? 'Leave voice' : 'Join voice'}
                  >
                    {isVoiceEnabled ? <PhoneXMarkIcon className="h-5 w-5" /> : <MicrophoneIcon className="h-5 w-5" />}
                  </button>

                  {isVoiceEnabled && (
                    <button
                      onClick={toggleMute}
                      className={`p-2 rounded-lg transition-colors ${
                        isMuted 
                          ? 'bg-gray-100 text-gray-600 hover:bg-gray-200' 
                          : 'bg-green-100 text-green-600 hover:bg-green-200'
                      }`}
                      title={isMuted ? 'Unmute' : 'Mute'}
                    >
                      {isMuted ? <SpeakerXMarkIcon className="h-5 w-5" /> : <SpeakerWaveIcon className="h-5 w-5" />}
                    </button>
                  )}
                </>
              )}

              {/* Screen Share */}
              {room.screen_sharing && (
                <button
                  className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                  title="Share screen"
                >
                  <ComputerDesktopIcon className="h-5 w-5" />
                </button>
              )}

              {/* Hand Raise */}
              <button
                onClick={toggleHandRaise}
                className={`p-2 rounded-lg transition-colors ${
                  hasRaisedHand 
                    ? 'bg-yellow-100 text-yellow-600 hover:bg-yellow-200' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title={hasRaisedHand ? 'Lower hand' : 'Raise hand'}
              >
                <HandRaisedIcon className="h-5 w-5" />
              </button>

              {/* Toggle Participants */}
              <button
                onClick={() => setShowParticipants(!showParticipants)}
                className={`p-2 rounded-lg transition-colors ${
                  showParticipants 
                    ? 'bg-blue-100 text-blue-600 hover:bg-blue-200' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title="Toggle participants"
              >
                <UserGroupIcon className="h-5 w-5" />
              </button>

              {/* More Options */}
              <button
                className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                title="More options"
              >
                <EllipsisVerticalIcon className="h-5 w-5" />
              </button>

              {/* Leave Room */}
              <button
                onClick={leaveRoom}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Leave Room
              </button>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.message_id}
              className={`flex ${message.user_id === user?.user_id ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-xs lg:max-w-md ${
                message.user_id === user?.user_id 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white border border-gray-200'
              } rounded-lg px-4 py-2 shadow-sm`}>
                {message.user_id !== user?.user_id && (
                  <p className={`text-xs font-medium mb-1 ${
                    message.user_id === user?.user_id ? 'text-blue-100' : 'text-gray-600'
                  }`}>
                    {message.username}
                  </p>
                )}
                <p className={message.user_id === user?.user_id ? 'text-white' : 'text-gray-900'}>
                  {message.content}
                </p>
                <p className={`text-xs mt-1 ${
                  message.user_id === user?.user_id ? 'text-blue-100' : 'text-gray-500'
                }`}>
                  {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className="bg-white border-t border-gray-200 px-6 py-4">
          <div className="flex items-center space-x-4">
            <button className="p-2 text-gray-500 hover:text-gray-700 transition-colors">
              <PaperClipIcon className="h-5 w-5" />
            </button>
            <input
              ref={messageInputRef}
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type a message..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={!isConnected}
            />
            <button
              onClick={sendMessage}
              disabled={!newMessage.trim() || !isConnected}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <PaperAirplaneIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Participants Sidebar */}
      {showParticipants && (
        <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Participants ({participants.length})
            </h2>
            <div className="space-y-3">
              {participants.map((participant) => (
                <div key={participant.user_id} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                      <span className="text-sm font-medium text-gray-700">
                        {participant.username.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-900">
                        {participant.username}
                        {participant.user_id === user?.user_id && ' (You)'}
                      </p>
                      <p className="text-xs text-gray-500">{participant.role}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {participant.has_raised_hand && (
                      <HandRaisedIcon className="h-4 w-4 text-yellow-500" />
                    )}
                    {participant.is_speaking && (
                      <MicrophoneSolidIcon className="h-4 w-4 text-green-500" />
                    )}
                    {participant.is_muted && (
                      <SpeakerXMarkIcon className="h-4 w-4 text-gray-400" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoomDetail;