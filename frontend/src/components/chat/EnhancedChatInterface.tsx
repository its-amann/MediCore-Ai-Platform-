import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  PaperAirplaneIcon,
  PhotoIcon,
  MicrophoneIcon,
  StopIcon,
  DocumentIcon,
  UserIcon,
  ComputerDesktopIcon,
  EllipsisHorizontalIcon,
  CheckIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { useWebSocket, useWebSocketConnection } from '../../contexts/WebSocketContext';
import { useAuthStore } from '../../store/authStore';
import { Message } from '../../types/common';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface TypingIndicatorProps {
  typingUsers: Array<{ user_id: string; username: string; room_id?: string }>;
  currentRoomId?: string;
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ typingUsers, currentRoomId }) => {
  const relevantTypers = typingUsers.filter(user => 
    !currentRoomId || user.room_id === currentRoomId
  );

  if (relevantTypers.length === 0) return null;

  return (
    <div className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-500">
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span>
        {relevantTypers.length === 1 
          ? `${relevantTypers[0].username} is typing...`
          : `${relevantTypers.length} people are typing...`
        }
      </span>
    </div>
  );
};

interface MessageBubbleProps {
  message: Message;
  isOwn: boolean;
  showAvatar: boolean;
  onRetry?: (messageId: string) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isOwn, showAvatar, onRetry }) => {
  const getSenderIcon = () => {
    if (message.sender_type === 'doctor') {
      return <ComputerDesktopIcon className="h-5 w-5 text-blue-500" />;
    }
    return <UserIcon className="h-5 w-5 text-gray-500" />;
  };

  const renderMessageContent = () => {
    switch (message.type) {
      case 'image':
        return (
          <div className="space-y-2">
            {message.content && <p>{message.content}</p>}
            {message.metadata?.file_url && (
              <img
                src={message.metadata.file_url}
                alt="Shared image"
                className="max-w-xs rounded-lg cursor-pointer hover:opacity-90"
              />
            )}
          </div>
        );
      
      case 'audio':
        return (
          <div className="space-y-2">
            {message.content && <p>{message.content}</p>}
            {message.metadata?.file_url && (
              <audio controls className="w-full max-w-xs">
                <source src={message.metadata.file_url} type="audio/mpeg" />
                Your browser does not support the audio element.
              </audio>
            )}
          </div>
        );
      
      case 'file':
        return (
          <div className="space-y-2">
            {message.content && <p>{message.content}</p>}
            {message.metadata?.file_url && (
              <div className="flex items-center space-x-2 p-3 bg-gray-100 rounded-lg max-w-xs">
                <DocumentIcon className="h-6 w-6 text-gray-500" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {message.metadata.file_name || 'Document'}
                  </p>
                  {message.metadata.file_size && (
                    <p className="text-xs text-gray-500">
                      {(message.metadata.file_size / 1024 / 1024).toFixed(1)} MB
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      
      case 'system':
        return (
          <div className="text-center">
            <p className="text-sm text-gray-500 italic">{message.content}</p>
          </div>
        );
      
      default:
        return (
          <div className="space-y-2">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  // Custom component overrides for better styling
                  p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul: ({children}) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                  ol: ({children}) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                  li: ({children}) => <li className="mb-1">{children}</li>,
                  strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                  em: ({children}) => <em className="italic">{children}</em>,
                  h1: ({children}) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                  h2: ({children}) => <h2 className="text-base font-bold mb-2">{children}</h2>,
                  h3: ({children}) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
                  code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{children}</code>,
                  pre: ({children}) => <pre className="bg-gray-100 p-2 rounded overflow-x-auto text-sm">{children}</pre>,
                  blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-3 italic">{children}</blockquote>,
                  a: ({children, href}) => <a href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                  hr: () => <hr className="my-2 border-gray-300" />
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
            {message.metadata?.analysis_result && (
              <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm font-medium text-blue-900 mb-1">AI Analysis:</p>
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({children}) => <p className="text-sm text-blue-800">{children}</p>,
                      ul: ({children}) => <ul className="list-disc pl-4 text-sm text-blue-800">{children}</ul>,
                      ol: ({children}) => <ol className="list-decimal pl-4 text-sm text-blue-800">{children}</ol>,
                      li: ({children}) => <li className="mb-1">{children}</li>,
                      strong: ({children}) => <strong className="font-semibold">{children}</strong>
                    }}
                  >
                    {message.metadata.analysis_result}
                  </ReactMarkdown>
                </div>
                {message.metadata.confidence_score && (
                  <p className="text-xs text-blue-600 mt-1">
                    Confidence: {Math.round(message.metadata.confidence_score * 100)}%
                  </p>
                )}
              </div>
            )}
          </div>
        );
    }
  };

  if (message.type === 'system') {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-gray-100 rounded-full px-4 py-2">
          {renderMessageContent()}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-end space-x-2 mb-3 sm:mb-4 ${isOwn ? 'flex-row-reverse space-x-reverse' : ''}`}>
      {/* Avatar */}
      {showAvatar && !isOwn && (
        <div className="flex-shrink-0 w-6 h-6 sm:w-8 sm:h-8 bg-gray-200 rounded-full flex items-center justify-center">
          {getSenderIcon()}
        </div>
      )}
      
      {/* Message */}
      <div className={`max-w-[85%] sm:max-w-xs lg:max-w-md ${isOwn ? 'ml-8 sm:ml-12' : 'mr-8 sm:mr-12'}`}>
        {/* Sender name for non-own messages */}
        {!isOwn && showAvatar && (
          <p className="text-xs text-gray-500 mb-1 px-1">
            {message.sender_name}
            {message.metadata?.doctor_specialty && (
              <span className="text-blue-500 ml-1">
                ({message.metadata.doctor_specialty})
              </span>
            )}
          </p>
        )}
        
        {/* Message bubble */}
        <div
          className={`px-3 sm:px-4 py-2 rounded-2xl text-sm sm:text-base ${
            isOwn 
              ? 'bg-blue-500 text-white' 
              : message.sender_type === 'doctor'
              ? 'bg-green-100 text-green-900'
              : 'bg-gray-100 text-gray-900'
          } ${message.status === 'failed' ? 'border-2 border-red-300' : ''}`}
        >
          {renderMessageContent()}
        </div>
        
        {/* Message status and timestamp */}
        <div className={`flex items-center space-x-2 mt-1 px-1 ${isOwn ? 'justify-end' : 'justify-start'}`}>
          <span className="text-xs text-gray-500">
            {formatDistanceToNow(parseISO(message.timestamp), { addSuffix: true })}
          </span>
          
          {isOwn && (
            <div className="flex items-center space-x-1">
              {message.status === 'sending' && (
                <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              )}
              {message.status === 'sent' && (
                <CheckIcon className="h-4 w-4 text-gray-400" />
              )}
              {message.status === 'delivered' && (
                <div className="flex">
                  <CheckIcon className="h-4 w-4 text-blue-500" />
                  <CheckIcon className="h-4 w-4 text-blue-500 -ml-2" />
                </div>
              )}
              {message.status === 'failed' && (
                <button
                  onClick={() => onRetry?.(message.id)}
                  className="flex items-center space-x-1 text-red-500 hover:text-red-600"
                  title="Retry sending"
                >
                  <ExclamationTriangleIcon className="h-4 w-4" />
                  <span className="text-xs">Retry</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface EnhancedChatInterfaceProps {
  caseId?: string;
  roomId?: string;
  doctorId?: string;
  onMessageSent?: (message: Message) => void;
  className?: string;
}

const EnhancedChatInterface: React.FC<EnhancedChatInterfaceProps> = ({
  caseId,
  roomId,
  doctorId,
  onMessageSent,
  className = ''
}) => {
  const { user } = useAuthStore();
  const { sendMessage, onMessage, typingUsers, startTyping, stopTyping, joinRoom, leaveRoom } = useWebSocket();
  
  // Explicitly connect WebSocket when this chat interface is used
  useWebSocketConnection();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Join room on mount
  useEffect(() => {
    if (roomId) {
      joinRoom(roomId);
      return () => leaveRoom(roomId);
    }
  }, [roomId, joinRoom, leaveRoom]);

  // Listen for incoming messages
  useEffect(() => {
    const unsubscribe = onMessage((message) => {
      // Only show messages for current room/case
      if (
        (!roomId || message.room_id === roomId) &&
        (!caseId || message.case_id === caseId)
      ) {
        setMessages(prev => {
          // Avoid duplicates
          if (prev.find(m => m.id === message.id)) return prev;
          return [...prev, message];
        });
      }
    });

    return unsubscribe;
  }, [onMessage, roomId, caseId]);

  // Handle typing indicators
  const handleInputChange = (value: string) => {
    setInputValue(value);
    
    // Start typing indicator
    if (value.trim() && !typingTimeoutRef.current) {
      startTyping(roomId);
    }
    
    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    // Stop typing after 1 second of inactivity
    typingTimeoutRef.current = setTimeout(() => {
      stopTyping(roomId);
      typingTimeoutRef.current = null;
    }, 1000);
  };

  const sendTextMessage = async () => {
    if (!inputValue.trim() || !user) return;

    const message: Omit<Message, 'id' | 'timestamp' | 'sender_id'> = {
      type: 'text',
      content: inputValue.trim(),
      sender_name: user.username,
      sender_type: 'user',
      room_id: roomId,
      case_id: caseId,
      status: 'sending'
    };

    // Add to local messages immediately
    const localMessage: Message = {
      ...message,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      sender_id: user.user_id
    };

    setMessages(prev => [...prev, localMessage]);
    setInputValue('');
    stopTyping(roomId);

    // Send via WebSocket
    try {
      sendMessage(message);
      
      // Update status to sent
      setMessages(prev => prev.map(m => 
        m.id === localMessage.id ? { ...m, status: 'sent' } : m
      ));

      onMessageSent?.(localMessage);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => prev.map(m => 
        m.id === localMessage.id ? { ...m, status: 'failed' } : m
      ));
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/wav' });
        setRecordingBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      toast.error('Failed to access microphone');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      setMediaRecorder(null);
    }
  };

  const sendAudioMessage = async () => {
    if (!recordingBlob || !user) return;

    // Create form data for audio upload
    const formData = new FormData();
    formData.append('audio', recordingBlob, 'voice-message.wav');
    if (caseId) formData.append('case_id', caseId);

    try {
      // In a real implementation, you'd upload the audio file first
      // const uploadResponse = await api.post('/media/upload', formData);
      
      const message: Omit<Message, 'id' | 'timestamp' | 'sender_id'> = {
        type: 'audio',
        content: 'Voice message',
        sender_name: user.username,
        sender_type: 'user',
        room_id: roomId,
        case_id: caseId,
        metadata: {
          // file_url: uploadResponse.data.url,
          file_url: URL.createObjectURL(recordingBlob), // Temporary for demo
          file_name: 'voice-message.wav',
          file_size: recordingBlob.size
        }
      };

      sendMessage(message);
      setRecordingBlob(null);
      toast.success('Voice message sent');
    } catch (error) {
      console.error('Failed to send audio message:', error);
      toast.error('Failed to send voice message');
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !user) return;

    // Add file message to chat
    const message: Omit<Message, 'id' | 'timestamp' | 'sender_id'> = {
      type: file.type.startsWith('image/') ? 'image' : 'file',
      content: `Shared ${file.type.startsWith('image/') ? 'image' : 'file'}: ${file.name}`,
      sender_name: user.username,
      sender_type: 'user',
      room_id: roomId,
      case_id: caseId,
      metadata: {
        file_url: URL.createObjectURL(file), // Temporary for demo
        file_name: file.name,
        file_size: file.size
      }
    };

    sendMessage(message);
    toast.success('File shared');
  };

  const retryMessage = (messageId: string) => {
    const message = messages.find(m => m.id === messageId);
    if (!message) return;

    // Update status to sending
    setMessages(prev => prev.map(m => 
      m.id === messageId ? { ...m, status: 'sending' } : m
    ));

    try {
      sendMessage(message);
      
      // Update status to sent
      setMessages(prev => prev.map(m => 
        m.id === messageId ? { ...m, status: 'sent' } : m
      ));
    } catch (error) {
      setMessages(prev => prev.map(m => 
        m.id === messageId ? { ...m, status: 'failed' } : m
      ));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  };

  return (
    <div className={`flex flex-col h-full bg-white rounded-lg shadow ${className}`}>
      {/* Chat Header */}
      <div className="flex items-center justify-between p-3 sm:p-4 border-b border-gray-200 bg-white">
        <div className="min-w-0 flex-1">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 truncate">
            {roomId ? `Room Chat` : 'AI Medical Consultation'}
          </h3>
          <p className="text-xs sm:text-sm text-gray-600 truncate">
            {doctorId ? 'AI Doctor Available' : 'Secure Medical Chat'}
          </p>
        </div>
        <div className="flex items-center space-x-2 flex-shrink-0">
          <div className="w-2 h-2 sm:w-3 sm:h-3 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-xs sm:text-sm text-gray-600 hidden sm:inline">Online</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-2 sm:p-4 space-y-3 sm:space-y-4 bg-gray-50">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8 px-4">
            <ComputerDesktopIcon className="mx-auto h-10 w-10 sm:h-12 sm:w-12 text-gray-300" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No messages yet</h3>
            <p className="mt-1 text-xs sm:text-sm text-gray-500">
              Start a conversation with the AI doctor for medical guidance
            </p>
          </div>
        ) : (
          messages.map((message, index) => {
            const isOwn = message.sender_id === user?.user_id;
            const showAvatar = !isOwn && (
              index === 0 || 
              messages[index - 1].sender_id !== message.sender_id ||
              new Date(message.timestamp).getTime() - new Date(messages[index - 1].timestamp).getTime() > 300000 // 5 minutes
            );

            return (
              <MessageBubble
                key={message.id}
                message={message}
                isOwn={isOwn}
                showAvatar={showAvatar}
                onRetry={retryMessage}
              />
            );
          })
        )}
        
        <TypingIndicator 
          typingUsers={typingUsers} 
          currentRoomId={roomId}
        />
        
        <div ref={messagesEndRef} />
      </div>

      {/* Recording Indicator */}
      {recordingBlob && (
        <div className="px-4 py-2 bg-blue-50 border-t border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-700">Voice message recorded</span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setRecordingBlob(null)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={sendAudioMessage}
                className="btn-primary text-sm py-1 px-3"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="p-3 sm:p-4 border-t border-gray-200 bg-white">
        <div className="flex items-end space-x-1 sm:space-x-2">
          {/* File Upload */}
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileUpload}
            className="hidden"
            accept="image/*,.pdf,.doc,.docx,audio/*"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            title="Attach file"
            aria-label="Attach file"
          >
            <DocumentIcon className="h-4 w-4 sm:h-5 sm:w-5" />
          </button>

          {/* Image Upload */}
          <button
            onClick={() => {
              const input = document.createElement('input');
              input.type = 'file';
              input.accept = 'image/*';
              input.onchange = (e) => handleFileUpload(e as any);
              input.click();
            }}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            title="Upload image"
            aria-label="Upload image"
          >
            <PhotoIcon className="h-4 w-4 sm:h-5 sm:w-5" />
          </button>

          {/* Text Input */}
          <div className="flex-1 min-w-0">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => handleInputChange(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your medical question..."
              className="w-full px-3 sm:px-4 py-2 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm sm:text-base"
              rows={1}
              style={{ minHeight: '36px', maxHeight: '100px' }}
            />
          </div>

          {/* Voice Recording */}
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onMouseLeave={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            className={`p-2 rounded-lg transition-colors flex-shrink-0 ${
              isRecording 
                ? 'bg-red-100 text-red-600' 
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
            title={isRecording ? 'Release to stop recording' : 'Hold to record voice message'}
            aria-label={isRecording ? 'Stop recording' : 'Start voice recording'}
          >
            {isRecording ? (
              <StopIcon className="h-4 w-4 sm:h-5 sm:w-5" />
            ) : (
              <MicrophoneIcon className="h-4 w-4 sm:h-5 sm:w-5" />
            )}
          </button>

          {/* Send Button */}
          <button
            onClick={sendTextMessage}
            disabled={!inputValue.trim()}
            className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            title="Send message"
            aria-label="Send message"
          >
            <PaperAirplaneIcon className="h-4 w-4 sm:h-5 sm:w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default EnhancedChatInterface;