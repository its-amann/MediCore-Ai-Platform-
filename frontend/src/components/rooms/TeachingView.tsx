import React, { useState, useEffect } from 'react';
import { useRoom } from '../../contexts/RoomContext';
import { useAuthStore } from '../../store/authStore';
import RoomHeader from './RoomHeader';
import ParticipantsList from './ParticipantsList';
import ChatArea from './chat/ChatArea';
import VideoGrid from './video/VideoGrid';
import VideoControls from './video/VideoControls';
import AIAssistantPanel from '../ai/AIAssistantPanel';
import { motion } from 'framer-motion';

const TeachingView: React.FC = () => {
  const { room, participants, markMessagesAsRead } = useRoom();
  const { user } = useAuthStore();
  const [showParticipants, setShowParticipants] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showAI, setShowAI] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

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

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      <RoomHeader />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Main video area */}
        <div className={`flex-1 flex flex-col ${
          (showParticipants || showChat || showAI) && !isMobile ? 'mr-80' : ''
        }`}>
          <VideoGrid />
          <VideoControls
            onToggleChat={() => setShowChat(!showChat)}
            onToggleParticipants={() => setShowParticipants(!showParticipants)}
            onToggleAI={() => setShowAI(!showAI)}
            showChat={showChat}
            showParticipants={showParticipants}
            showAI={showAI}
          />
        </div>

        {/* Sidebar - Participants, Chat or AI */}
        {(showParticipants || showChat || showAI) && (
          <motion.div
            initial={{ x: 300 }}
            animate={{ x: 0 }}
            exit={{ x: 300 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={`${
              isMobile 
                ? 'fixed inset-0 z-40 bg-white' 
                : 'w-80 border-l border-gray-700 bg-gray-800'
            }`}
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
            {!isMobile && (showParticipants || showChat || showAI) && (
              <div className="flex border-b border-gray-700">
                {room?.host_id === user?.user_id && (
                  <button
                    onClick={() => {
                      setShowParticipants(true);
                      setShowChat(false);
                      setShowAI(false);
                    }}
                    className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                      showParticipants && !showChat && !showAI
                        ? 'bg-gray-700 text-white'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    Participants
                  </button>
                )}
                <button
                  onClick={() => {
                    setShowChat(true);
                    setShowParticipants(false);
                    setShowAI(false);
                  }}
                  className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                    showChat && !showParticipants && !showAI
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-400 hover:text-white'
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
                  className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                    showAI && !showParticipants && !showChat
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  AI Assistant
                </button>
              </div>
            )}

            {/* Content */}
            <div className="h-full overflow-hidden">
              {showParticipants && !showChat && !showAI && (
                <ParticipantsList 
                  participants={participants || []}
                  currentUserId={user?.user_id || ''}
                  isHost={room?.host_id === user?.user_id}
                />
              )}
              {showChat && !showParticipants && !showAI && (
                <ChatArea 
                  roomId={room?.room_id || ''} 
                  currentUserId={user?.user_id || ''} 
                />
              )}
              {showAI && !showParticipants && !showChat && (
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

export default TeachingView;