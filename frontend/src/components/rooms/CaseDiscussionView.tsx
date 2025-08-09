import React, { useState, useEffect } from 'react';
import { useRoom } from '../../contexts/RoomContext';
import { useAuthStore } from '../../store/authStore';
import RoomHeader from './RoomHeader';
import ParticipantsList from './ParticipantsList';
import ChatArea from './chat/ChatArea';
import { motion } from 'framer-motion';

const CaseDiscussionView: React.FC = () => {
  const { room, participants, markMessagesAsRead } = useRoom();
  const { user } = useAuthStore();
  const [showParticipants, setShowParticipants] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  // Check if mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setShowParticipants(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Mark messages as read when component mounts
  useEffect(() => {
    markMessagesAsRead();
  }, [markMessagesAsRead]);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <RoomHeader 
        onToggleParticipants={() => setShowParticipants(!showParticipants)}
        showParticipants={showParticipants}
      />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Main chat area */}
        <div className={`flex-1 flex flex-col ${
          showParticipants && !isMobile ? 'mr-80' : ''
        }`}>
          <ChatArea roomId={room?.room_id || ''} currentUserId={user?.user_id || ''} />
        </div>

        {/* Participants sidebar */}
        {showParticipants && (
          <motion.div
            initial={{ x: 300 }}
            animate={{ x: 0 }}
            exit={{ x: 300 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={`${
              isMobile 
                ? 'fixed inset-0 z-40 bg-white' 
                : 'w-80 border-l border-gray-200'
            }`}
          >
            {isMobile && (
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold">Participants</h2>
                <button
                  onClick={() => setShowParticipants(false)}
                  className="p-2 hover:bg-gray-100 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
            <ParticipantsList 
              participants={participants || []}
              currentUserId={user?.user_id || ''}
              isHost={room?.host_id === user?.user_id}
            />
          </motion.div>
        )}

        {/* Mobile overlay */}
        {isMobile && showParticipants && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-30"
            onClick={() => setShowParticipants(false)}
          />
        )}
      </div>
    </div>
  );
};

export default CaseDiscussionView;