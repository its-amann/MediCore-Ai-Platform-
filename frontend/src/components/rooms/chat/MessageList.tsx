import React, { useRef, useEffect } from 'react';
import { useRoom } from '../../../contexts/RoomContext';
import { useAuthStore } from '../../../store/authStore';
import { Message } from '../../../types/room';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  PhotoIcon,
  DocumentIcon,
  SpeakerWaveIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

interface MessageItemProps {
  message: Message;
  isOwn: boolean;
}

const MessageItem: React.FC<MessageItemProps> = ({ message, isOwn }) => {
  const getStatusIcon = () => {
    switch (message.status) {
      case 'sending':
        return <ArrowPathIcon className="h-3 w-3 text-gray-400 animate-spin" />;
      case 'sent':
        return <CheckIcon className="h-3 w-3 text-gray-400" />;
      case 'delivered':
      case 'read':
        return <CheckCircleIcon className="h-3 w-3 text-blue-400" />;
      case 'failed':
        return <ExclamationCircleIcon className="h-3 w-3 text-red-400" />;
      default:
        return null;
    }
  };

  const getFileIcon = () => {
    const fileType = message.metadata?.message_type;
    switch (fileType) {
      case 'image':
        return <PhotoIcon className="h-4 w-4" />;
      case 'audio':
        return <SpeakerWaveIcon className="h-4 w-4" />;
      case 'document':
        return <DocumentIcon className="h-4 w-4" />;
      default:
        return <DocumentIcon className="h-4 w-4" />;
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + 
        ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`mb-4 flex ${isOwn ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-xs lg:max-w-md xl:max-w-lg ${isOwn ? 'order-2' : 'order-1'}`}>
        {/* Sender name for others' messages */}
        {!isOwn && message.sender_name && (
          <div className="text-xs text-gray-600 mb-1 px-1">
            {message.sender_name}
            {message.sender_type === 'doctor' && message.metadata?.doctor_specialty && (
              <span className="ml-1 text-blue-600">
                ({message.metadata.doctor_specialty})
              </span>
            )}
          </div>
        )}

        {/* Message bubble */}
        <div className={`relative rounded-2xl px-4 py-2 ${
          isOwn 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-100 text-gray-900'
        }`}>
          {/* Reply indicator */}
          {message.metadata?.reply_to && (
            <div className={`text-xs mb-2 pb-2 border-b ${
              isOwn ? 'border-blue-500' : 'border-gray-300'
            }`}>
              Replying to a message
            </div>
          )}

          {/* Message content */}
          {message.metadata?.message_type === 'image' && message.metadata.file_url ? (
            <div className="space-y-2">
              <img 
                src={message.metadata.file_url} 
                alt="Shared image"
                className="rounded-lg max-w-full cursor-pointer hover:opacity-90 transition-opacity"
                onClick={() => window.open(message.metadata?.file_url || '', '_blank')}
              />
              {message.content && (
                <p className={isOwn ? 'text-white' : 'text-gray-900'}>{message.content}</p>
              )}
            </div>
          ) : message.metadata?.file_url ? (
            <div className="space-y-2">
              <a
                href={message.metadata.file_url}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex items-center space-x-2 px-3 py-2 rounded-lg ${
                  isOwn 
                    ? 'bg-blue-700 hover:bg-blue-800' 
                    : 'bg-gray-200 hover:bg-gray-300'
                } transition-colors`}
              >
                {getFileIcon()}
                <span className="text-sm font-medium">
                  {message.metadata.file_name || 'File'}
                </span>
                {message.metadata.file_size && (
                  <span className={`text-xs ${isOwn ? 'text-blue-200' : 'text-gray-500'}`}>
                    ({(message.metadata.file_size / 1024).toFixed(1)} KB)
                  </span>
                )}
              </a>
              {message.content && (
                <p className={isOwn ? 'text-white' : 'text-gray-900'}>{message.content}</p>
              )}
            </div>
          ) : (
            <p className={`whitespace-pre-wrap break-words ${
              isOwn ? 'text-white' : 'text-gray-900'
            }`}>
              {message.content}
            </p>
          )}

          {/* Reactions */}
          {message.reactions && message.reactions.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {message.reactions.map((reaction, index) => (
                <span
                  key={index}
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs ${
                    isOwn ? 'bg-blue-700' : 'bg-gray-200'
                  }`}
                >
                  <span className="mr-1">{reaction.emoji}</span>
                  <span>{reaction.users.length}</span>
                </span>
              ))}
            </div>
          )}

          {/* Edited indicator */}
          {message.metadata?.edited && (
            <span className={`text-xs ${isOwn ? 'text-blue-200' : 'text-gray-500'}`}>
              (edited)
            </span>
          )}
        </div>

        {/* Message footer */}
        <div className={`flex items-center mt-1 px-1 space-x-2 ${
          isOwn ? 'justify-end' : 'justify-start'
        }`}>
          <span className="text-xs text-gray-500">
            {formatTime(message.timestamp)}
          </span>
          {isOwn && getStatusIcon()}
        </div>
      </div>
    </motion.div>
  );
};

const MessageList: React.FC = () => {
  const { messages } = useRoom();
  const { user } = useAuthStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Group messages by date
  const groupedMessages = messages.reduce((groups, message) => {
    const date = new Date(message.timestamp).toDateString();
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(message);
    return groups;
  }, {} as Record<string, Message[]>);

  const formatDateHeader = (dateString: string) => {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString([], { 
        weekday: 'long', 
        month: 'long', 
        day: 'numeric',
        year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
      });
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      <AnimatePresence>
        {Object.entries(groupedMessages).map(([date, dateMessages]) => (
          <div key={date}>
            {/* Date separator */}
            <div className="flex items-center my-4">
              <div className="flex-1 border-t border-gray-200" />
              <span className="px-3 text-xs text-gray-500 bg-gray-50">
                {formatDateHeader(date)}
              </span>
              <div className="flex-1 border-t border-gray-200" />
            </div>

            {/* Messages for this date */}
            {dateMessages.map((message) => (
              <MessageItem
                key={message.id}
                message={message}
                isOwn={message.sender_id === user?.user_id}
              />
            ))}
          </div>
        ))}
      </AnimatePresence>

      {/* Empty state */}
      {messages.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">No messages yet. Start the conversation!</p>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;