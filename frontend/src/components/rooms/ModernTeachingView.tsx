import React, { useState, useEffect } from 'react';
import { useRoom } from '../../contexts/RoomContext';
import { useAuthStore } from '../../store/authStore';
import RoomHeader from './RoomHeader';
import ParticipantsList from './ParticipantsList';
import EnhancedChatArea from './chat/EnhancedChatArea';
import VideoGrid from './video/VideoGrid';
import VideoControls from './video/VideoControls';
import AIAssistantPanel from '../ai/AIAssistantPanel';
import { motion } from 'framer-motion';

const ModernTeachingView: React.FC = () => {
  const { room, participants, markMessagesAsRead } = useRoom();
  const { user } = useAuthStore();
  const [showParticipants, setShowParticipants] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showAI, setShowAI] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [screenShareState, setScreenShareState] = useState<{
    isActive: boolean;
    userId?: string;
    username?: string;
  }>({ isActive: false });

  // Check if mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Mark messages as read when chat is shown
  useEffect(() => {
    if (showChat) {
      markMessagesAsRead();
    }
  }, [showChat, markMessagesAsRead]);

  // Track screen share state from participants
  useEffect(() => {
    const screenSharer = participants?.find(p => p.is_screen_sharing);
    if (screenSharer) {
      setScreenShareState({
        isActive: true,
        userId: screenSharer.user_id,
        username: screenSharer.username
      });
    } else {
      setScreenShareState({ isActive: false });
    }
  }, [participants]);

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      <RoomHeader />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Main video area */}
        <div className={`flex-1 flex flex-col transition-all duration-300 ${
          (showParticipants || showChat || showAI) && !isMobile ? '' : ''
        }`}>
          <VideoGrid />
          <VideoControls
            onToggleChat={() => {
              setShowChat(!showChat);
              setShowParticipants(false);
              setShowAI(false);
            }}
            onToggleParticipants={() => {
              setShowParticipants(!showParticipants);
              setShowChat(false);
              setShowAI(false);
            }}
            onToggleAI={() => {
              setShowAI(!showAI);
              setShowChat(false);
              setShowParticipants(false);
            }}
            showChat={showChat}
            showParticipants={showParticipants}
            showAI={showAI}
          />
        </div>

        {/* Sidebar - Fixed width, no squashing */}
        {(showParticipants || showChat || showAI) && (
          <motion.div
            initial={{ x: 400 }}
            animate={{ x: 0 }}
            exit={{ x: 400 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={`${
              isMobile 
                ? 'fixed inset-0 z-40 bg-white' 
                : 'w-[400px] flex-shrink-0 border-l border-gray-700 bg-gray-800'
            } flex flex-col h-full`}
          >
            {isMobile && (
              <div className="flex items-center justify-between p-4 border-b border-gray-700">
                <h2 className="text-lg font-semibold text-white">
                  {showAI ? 'AI Assistant' : showChat ? 'Chat' : 'Participants'}
                </h2>
                <button
                  onClick={() => {
                    setShowChat(false);
                    setShowParticipants(false);
                    setShowAI(false);
                  }}
                  className="p-2 hover:bg-gray-700 rounded-lg text-white"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            {/* Tab switcher for desktop */}
            {!isMobile && (
              <div className="flex border-b border-gray-700 bg-gray-850">
                <button
                  onClick={() => {
                    setShowParticipants(true);
                    setShowChat(false);
                    setShowAI(false);
                  }}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-all ${
                    showParticipants
                      ? 'bg-gray-700 text-white border-b-2 border-blue-500'
                      : 'text-gray-400 hover:text-white hover:bg-gray-750'
                  }`}
                >
                  Participants ({participants?.length || 0})
                </button>
                <button
                  onClick={() => {
                    setShowChat(true);
                    setShowParticipants(false);
                    setShowAI(false);
                  }}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-all ${
                    showChat
                      ? 'bg-gray-700 text-white border-b-2 border-blue-500'
                      : 'text-gray-400 hover:text-white hover:bg-gray-750'
                  }`}
                >
                  Chat
                </button>
                <button
                  onClick={() => {
                    setShowAI(true);
                    setShowParticipants(false);
                    setShowChat(false);
                  }}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-all ${
                    showAI
                      ? 'bg-gray-700 text-white border-b-2 border-blue-500'
                      : 'text-gray-400 hover:text-white hover:bg-gray-750'
                  }`}
                >
                  AI Assistant
                </button>
              </div>
            )}

            {/* Content - Full height */}
            <div className="flex-1 overflow-hidden flex flex-col">
              {showParticipants && (
                <ParticipantsList 
                  participants={participants || []}
                  currentUserId={user?.user_id || ''}
                  isHost={room?.host_id === user?.user_id}
                />
              )}
              {showChat && (
                <EnhancedChatArea 
                  roomId={room?.room_id || ''} 
                  currentUserId={user?.user_id || ''}
                  isScreenSharing={screenShareState.isActive}
                  screenShareUserId={screenShareState.userId}
                  screenShareUsername={screenShareState.username}
                />
              )}
              {showAI && (
                <AIAssistantPanel 
                  roomId={room?.room_id || ''} 
                  roomType="teaching"
                  subject={room?.metadata?.subject}
                />
              )}
            </div>
          </motion.div>
        )}

        {/* Mobile overlay */}
        {isMobile && (showParticipants || showChat || showAI) && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-30"
            onClick={() => {
              setShowParticipants(false);
              setShowChat(false);
              setShowAI(false);
            }}
          />
        )}
      </div>
    </div>
  );
};

export default ModernTeachingView;