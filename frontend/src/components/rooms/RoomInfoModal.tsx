import React from 'react';
import { Room } from '../../types/room';
import { XMarkIcon, UserGroupIcon, CalendarIcon, TagIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';

interface RoomInfoModalProps {
  room: Room;
  participants: any[];
  isOpen: boolean;
  onClose: () => void;
}

const RoomInfoModal: React.FC<RoomInfoModalProps> = ({ room, participants, isOpen, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black bg-opacity-50 z-50"
          />
          
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed inset-0 flex items-center justify-center z-50 p-4"
          >
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[80vh] overflow-hidden">
              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">Room Information</h2>
                <button
                  onClick={onClose}
                  className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <XMarkIcon className="h-5 w-5 text-gray-500" />
                </button>
              </div>
              
              {/* Content */}
              <div className="px-6 py-4 space-y-4 overflow-y-auto">
                {/* Room Name */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-1">{room.name}</h3>
                  {room.description && (
                    <p className="text-sm text-gray-600">{room.description}</p>
                  )}
                </div>
                
                {/* Room Details */}
                <div className="space-y-3">
                  {/* Room Type */}
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-24">Type:</span>
                    <span className="text-gray-900 capitalize">{room.room_type.replace('_', ' ')}</span>
                  </div>
                  
                  {/* Privacy */}
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-24">Privacy:</span>
                    <div className="flex items-center">
                      {room.is_private && <LockClosedIcon className="h-4 w-4 mr-1 text-gray-400" />}
                      <span className="text-gray-900">{room.is_private ? 'Private' : 'Public'}</span>
                    </div>
                  </div>
                  
                  {/* Created Date */}
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-24">Created:</span>
                    <div className="flex items-center">
                      <CalendarIcon className="h-4 w-4 mr-1 text-gray-400" />
                      <span className="text-gray-900">
                        {new Date(room.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  
                  {/* Host */}
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-24">Host:</span>
                    <span className="text-gray-900">
                      {participants.find(p => p.user_id === room.host_id)?.username || 'Unknown'}
                    </span>
                  </div>
                  
                  {/* Participants */}
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-24">Participants:</span>
                    <div className="flex items-center">
                      <UserGroupIcon className="h-4 w-4 mr-1 text-gray-400" />
                      <span className="text-gray-900">
                        {participants.length}
                        {room.max_participants && ` / ${room.max_participants}`}
                      </span>
                    </div>
                  </div>
                  
                  {/* Tags */}
                  {room.tags && room.tags.length > 0 && (
                    <div className="flex items-start text-sm">
                      <span className="text-gray-500 w-24">Tags:</span>
                      <div className="flex flex-wrap gap-1">
                        {room.tags.map((tag, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
                          >
                            <TagIcon className="h-3 w-3 mr-0.5" />
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Participants List */}
                <div className="pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">
                    Current Participants ({participants.length})
                  </h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {participants.map((participant) => (
                      <div
                        key={participant.user_id}
                        className="flex items-center justify-between text-sm"
                      >
                        <span className="text-gray-700">{participant.username}</span>
                        {participant.user_id === room.host_id && (
                          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                            Host
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              {/* Footer */}
              <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                <button
                  onClick={onClose}
                  className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default RoomInfoModal;