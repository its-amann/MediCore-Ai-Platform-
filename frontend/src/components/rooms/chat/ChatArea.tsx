import React from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';

interface ChatAreaProps {
  roomId: string;
  currentUserId: string;
}

const ChatArea: React.FC<ChatAreaProps> = ({ roomId, currentUserId }) => {
  return (
    <div className="flex flex-col h-full bg-gray-50">
      <MessageList />
      <TypingIndicator />
      <MessageInput />
    </div>
  );
};

export default ChatArea;