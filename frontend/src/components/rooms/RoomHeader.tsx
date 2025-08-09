import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRoom } from '../../contexts/RoomContext';
import {
  ArrowLeftIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  InformationCircleIcon,
  PhoneXMarkIcon,
  EllipsisVerticalIcon,
  LockClosedIcon,
  UsersIcon,
  TagIcon
} from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';
import { toast } from 'react-hot-toast';
import InviteParticipantsModal from './InviteParticipantsModal';
import RoomInfoModal from './RoomInfoModal';

interface RoomHeaderProps {
  onToggleParticipants?: () => void;
  showParticipants?: boolean;
}

const RoomHeader: React.FC<RoomHeaderProps> = ({ onToggleParticipants, showParticipants }) => {
  const navigate = useNavigate();
  const { room, participants, leaveRoom, isHost } = useRoom();
  const [showInfo, setShowInfo] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showRoomInfoModal, setShowRoomInfoModal] = useState(false);

  const handleLeaveRoom = async () => {
    if (window.confirm('Are you sure you want to leave this room?')) {
      await leaveRoom();
      navigate('/rooms');
    }
  };

  if (!room) return null;

  return (
    <>
      <header className="bg-white border-b border-gray-200 px-4 sm:px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left section */}
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/rooms')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Back to rooms"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-600" />
            </button>

            <div>
              <div className="flex items-center space-x-2">
                <h1 
                  className="text-xl font-semibold text-gray-900 cursor-pointer hover:text-gray-700 transition-colors"
                  onClick={() => setShowRoomInfoModal(true)}
                >
                  {room.name}
                </h1>
                {room.is_private && (
                  <LockClosedIcon className="h-4 w-4 text-gray-500" title="Private room" />
                )}
              </div>
              
              <div className="flex items-center mt-1 space-x-3">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                  room.status === 'active' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {room.status}
                </span>
                
                <span className="flex items-center text-sm text-gray-600">
                  <UsersIcon className="h-4 w-4 mr-1" />
                  {participants.length}
                  {room.max_participants && ` / ${room.max_participants}`}
                </span>

                {room.tags && room.tags.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <TagIcon className="h-4 w-4 text-gray-400" />
                    {room.tags.slice(0, 2).map((tag, index) => (
                      <span key={index} className="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                        {tag}
                      </span>
                    ))}
                    {room.tags.length > 2 && (
                      <span className="text-xs text-gray-500">+{room.tags.length - 2}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right section */}
          <div className="flex items-center space-x-2">
            {/* Info button */}
            <button
              onClick={() => setShowInfo(!showInfo)}
              className={`p-2 rounded-lg transition-colors ${
                showInfo ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Room information"
            >
              <InformationCircleIcon className="h-5 w-5" />
            </button>

            {/* Participants toggle */}
            {onToggleParticipants && (
              <button
                onClick={onToggleParticipants}
                className={`p-2 rounded-lg transition-colors ${
                  showParticipants ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-600'
                }`}
                title="Toggle participants"
              >
                <UserGroupIcon className="h-5 w-5" />
              </button>
            )}

            {/* Settings (host only) */}
            {isHost && (
              <button
                onClick={() => navigate(`/rooms/${room.room_id}/settings`)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
                title="Room settings"
              >
                <Cog6ToothIcon className="h-5 w-5" />
              </button>
            )}

            {/* More options */}
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
                title="More options"
              >
                <EllipsisVerticalIcon className="h-5 w-5" />
              </button>

              {showMenu && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50"
                >
                  <button
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(window.location.href);
                        toast.success('Room link copied to clipboard');
                      } catch (error) {
                        toast.error('Failed to copy link');
                      }
                      setShowMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Copy room link
                  </button>
                  <button
                    onClick={() => {
                      setShowInviteModal(true);
                      setShowMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Invite participants
                  </button>
                  {room.settings?.allow_recording && isHost && (
                    <button
                      onClick={() => {
                        // TODO: Implement recording
                        setShowMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Start recording
                    </button>
                  )}
                  <hr className="my-1" />
                  <button
                    onClick={() => {
                      // TODO: Implement report
                      setShowMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Report issue
                  </button>
                </motion.div>
              )}
            </div>

            {/* Leave room */}
            <button
              onClick={handleLeaveRoom}
              className="ml-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2"
            >
              <PhoneXMarkIcon className="h-4 w-4" />
              <span className="hidden sm:inline">Leave</span>
            </button>
          </div>
        </div>
      </header>

      {/* Room info panel */}
      {showInfo && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="bg-gray-50 border-b border-gray-200 px-4 sm:px-6 py-4"
        >
          <div className="max-w-3xl">
            <h3 className="text-sm font-medium text-gray-900 mb-2">Room Information</h3>
            {room.description && (
              <p className="text-sm text-gray-600 mb-3">{room.description}</p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Type:</span>
                <span className="ml-2 text-gray-900 capitalize">
                  {room.room_type.replace('_', ' ')}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Created:</span>
                <span className="ml-2 text-gray-900">
                  {new Date(room.created_at).toLocaleDateString()}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Host:</span>
                <span className="ml-2 text-gray-900">
                  {participants.find(p => p.user_id === room.host_id)?.username || 'Unknown'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Privacy:</span>
                <span className="ml-2 text-gray-900">
                  {room.is_private ? 'Private' : 'Public'}
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Invite Participants Modal */}
      {room && (
        <InviteParticipantsModal
          isOpen={showInviteModal}
          onClose={() => setShowInviteModal(false)}
          roomId={room.room_id}
          roomName={room.name}
        />
      )}
      
      {/* Room Info Modal */}
      {room && (
        <RoomInfoModal
          room={room}
          participants={participants}
          isOpen={showRoomInfoModal}
          onClose={() => setShowRoomInfoModal(false)}
        />
      )}
    </>
  );
};

export default RoomHeader;