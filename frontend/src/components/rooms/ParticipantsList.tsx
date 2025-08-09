import React, { useState } from 'react';
import { useRoom } from '../../contexts/RoomContext';
import { useAuthStore } from '../../store/authStore';
import {
  MicrophoneIcon,
  VideoCameraIcon,
  ComputerDesktopIcon,
  HandRaisedIcon,
  EllipsisVerticalIcon,
  ShieldCheckIcon,
  UserIcon,
  SpeakerXMarkIcon,
  VideoCameraSlashIcon
} from '@heroicons/react/24/outline';
import { MicrophoneIcon as MicrophoneSolidIcon } from '@heroicons/react/24/solid';
import { motion, AnimatePresence } from 'framer-motion';

interface ParticipantMenuProps {
  participant: any;
  onClose: () => void;
}

const ParticipantMenu: React.FC<ParticipantMenuProps> = ({ participant, onClose }) => {
  const { kickParticipant, isModerator } = useRoom();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50"
    >
      <button
        onClick={() => {
          // TODO: Implement private message
          onClose();
        }}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
      >
        Send message
      </button>
      
      {isModerator && (
        <>
          <hr className="my-1" />
          <button
            onClick={() => {
              // TODO: Implement mute participant
              onClose();
            }}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Mute participant
          </button>
          <button
            onClick={() => {
              // TODO: Implement make moderator
              onClose();
            }}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Make moderator
          </button>
          <button
            onClick={async () => {
              if (window.confirm(`Remove ${participant.username} from the room?`)) {
                await kickParticipant(participant.user_id);
                onClose();
              }
            }}
            className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
          >
            Remove from room
          </button>
        </>
      )}
    </motion.div>
  );
};

interface ParticipantsListProps {
  participants: any[];
  currentUserId: string;
  isHost: boolean;
}

const ParticipantsList: React.FC<ParticipantsListProps> = ({ participants = [], currentUserId, isHost }) => {
  const { room, typingUsers } = useRoom();
  const { user } = useAuthStore();
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter participants based on search
  const filteredParticipants = participants.filter(p =>
    p.username && p.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Sort participants: host first, then moderators, then others
  const sortedParticipants = [...filteredParticipants].sort((a, b) => {
    if (a.user_id === room?.host_id) return -1;
    if (b.user_id === room?.host_id) return 1;
    if (a.role === 'moderator' && b.role !== 'moderator') return -1;
    if (b.role === 'moderator' && a.role !== 'moderator') return 1;
    return 0;
  });

  const getRoleBadge = (participant: any) => {
    if (participant.user_id === room?.host_id) {
      return (
        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
          Host
        </span>
      );
    }
    if (participant.role === 'moderator') {
      return (
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
          Mod
        </span>
      );
    }
    return null;
  };

  const getConnectionQualityColor = (quality?: string) => {
    switch (quality) {
      case 'excellent': return 'bg-green-500';
      case 'good': return 'bg-yellow-500';
      case 'poor': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">
          Participants ({participants.length})
        </h3>
        
        {/* Search */}
        <div className="mt-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search participants..."
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Participants list */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4 py-2">
          <AnimatePresence>
            {sortedParticipants.map((participant) => {
              const isTyping = participant.username && typingUsers.includes(participant.username);
              const isCurrentUser = participant.user_id === user?.user_id;

              return (
                <motion.div
                  key={participant.user_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="mb-3 flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    {/* Avatar */}
                    <div className="relative">
                      <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium">
                        {participant.avatar_url ? (
                          <img 
                            src={participant.avatar_url} 
                            alt={participant.username || 'User'}
                            className="h-full w-full rounded-full object-cover"
                          />
                        ) : (
                          participant.username ? participant.username.charAt(0).toUpperCase() : '?'
                        )}
                      </div>
                      
                      {/* Connection quality indicator */}
                      <div className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white ${
                        getConnectionQualityColor(participant.connection_quality)
                      }`} />
                    </div>

                    {/* User info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium text-gray-900 truncate max-w-[150px]">
                          {participant.username || 'Unknown User'}
                          {isCurrentUser && ' (You)'}
                        </span>
                        {getRoleBadge(participant)}
                      </div>
                      
                      {isTyping && (
                        <span className="text-xs text-gray-500 italic">typing...</span>
                      )}
                    </div>
                  </div>

                  {/* Status icons and menu */}
                  <div className="flex items-center space-x-2">
                    {/* Status icons */}
                    <div className="flex items-center space-x-1">
                      {participant.has_raised_hand && (
                        <HandRaisedIcon className="h-4 w-4 text-yellow-500" title="Hand raised" />
                      )}
                      
                      {participant.is_screen_sharing && (
                        <ComputerDesktopIcon className="h-4 w-4 text-blue-500" title="Screen sharing" />
                      )}
                      
                      {room?.room_type === 'teaching' && (
                        <>
                          {participant.is_speaking ? (
                            <MicrophoneSolidIcon className="h-4 w-4 text-green-500" title="Speaking" />
                          ) : participant.is_muted ? (
                            <SpeakerXMarkIcon className="h-4 w-4 text-gray-400" title="Muted" />
                          ) : (
                            <MicrophoneIcon className="h-4 w-4 text-gray-400" title="Microphone on" />
                          )}
                          
                          {participant.is_video_on ? (
                            <VideoCameraIcon className="h-4 w-4 text-gray-400" title="Video on" />
                          ) : (
                            <VideoCameraSlashIcon className="h-4 w-4 text-gray-400" title="Video off" />
                          )}
                        </>
                      )}
                    </div>

                    {/* Menu button */}
                    {!isCurrentUser && (
                      <div className="relative">
                        <button
                          onClick={() => setOpenMenuId(
                            openMenuId === participant.user_id ? null : participant.user_id
                          )}
                          className="p-1 hover:bg-gray-200 rounded transition-colors"
                        >
                          <EllipsisVerticalIcon className="h-4 w-4 text-gray-500" />
                        </button>
                        
                        {openMenuId === participant.user_id && (
                          <ParticipantMenu
                            participant={participant}
                            onClose={() => setOpenMenuId(null)}
                          />
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>

      {/* Footer stats */}
      <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>{participants.filter(p => p.is_video_on).length} with video</span>
          <span>{participants.filter(p => !p.is_muted).length} unmuted</span>
        </div>
      </div>
    </div>
  );
};

export default ParticipantsList;