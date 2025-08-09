import React, { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import EnhancedMessageInput from './EnhancedMessageInput';
import TypingIndicator from './TypingIndicator';
import { useWebSocket } from '../../../contexts/WebSocketContext';

interface EnhancedChatAreaProps {
  roomId: string;
  currentUserId: string;
  isScreenSharing?: boolean;
  screenShareUserId?: string;
  screenShareUsername?: string;
}

const EnhancedChatArea: React.FC<EnhancedChatAreaProps> = ({ 
  roomId, 
  currentUserId,
  isScreenSharing = false,
  screenShareUserId,
  screenShareUsername
}) => {
  const { socket } = useWebSocket();
  const [screenShareState, setScreenShareState] = useState({
    isActive: isScreenSharing,
    userId: screenShareUserId,
    username: screenShareUsername
  });
  const messageHandlerRef = useRef<((event: MessageEvent) => void) | null>(null);

  // Update screen share state from props
  useEffect(() => {
    setScreenShareState({
      isActive: isScreenSharing,
      userId: screenShareUserId,
      username: screenShareUsername
    });
  }, [isScreenSharing, screenShareUserId, screenShareUsername]);

  useEffect(() => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    // Create message handler
    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'screen_share_started' && message.data?.room_id === roomId) {
          setScreenShareState({
            isActive: true,
            userId: message.data.user_id,
            username: message.data.username
          });
        } else if (message.type === 'screen_share_stopped' && message.data?.room_id === roomId) {
          setScreenShareState({
            isActive: false,
            userId: undefined,
            username: undefined
          });
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    // Store handler reference
    messageHandlerRef.current = handleMessage;

    // Add event listener
    socket.addEventListener('message', handleMessage);

    return () => {
      // Remove event listener on cleanup
      if (socket && messageHandlerRef.current) {
        socket.removeEventListener('message', messageHandlerRef.current);
      }
    };
  }, [socket, roomId]);

  const handleScreenshotCapture = (screenshot: Blob) => {
    console.log('Screenshot captured:', screenshot);
    // Additional handling if needed
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Screen share notification banner */}
      {screenShareState.isActive && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-2">
          <p className="text-sm text-blue-800">
            {screenShareState.username} is sharing their screen. 
            Click the camera icon below to capture a screenshot.
          </p>
        </div>
      )}
      
      {/* Messages area - takes remaining space */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      
      {/* Typing indicator */}
      <TypingIndicator />
      
      {/* Message input */}
      <EnhancedMessageInput 
        onScreenshotCapture={handleScreenshotCapture}
        isScreenSharing={screenShareState.isActive}
        screenShareUserId={screenShareState.userId}
        screenShareUsername={screenShareState.username}
      />
    </div>
  );
};

export default EnhancedChatArea;