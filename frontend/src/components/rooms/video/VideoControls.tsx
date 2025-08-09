import React, { useState } from 'react';
import { useRoom } from '../../../contexts/RoomContext';
import { useAuthStore } from '../../../store/authStore';
import {
  MicrophoneIcon,
  VideoCameraIcon,
  ComputerDesktopIcon,
  PhoneXMarkIcon,
  ChatBubbleLeftIcon,
  UserGroupIcon,
  HandRaisedIcon,
  Cog6ToothIcon,
  SpeakerXMarkIcon,
  VideoCameraSlashIcon,
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';

interface VideoControlsProps {
  onToggleChat: () => void;
  onToggleParticipants: () => void;
  onToggleAI?: () => void;
  showChat: boolean;
  showParticipants: boolean;
  showAI?: boolean;
}

const VideoControls: React.FC<VideoControlsProps> = ({
  onToggleChat,
  onToggleParticipants,
  onToggleAI,
  showChat,
  showParticipants,
  showAI
}) => {
  const { 
    room,
    isMuted, 
    isVideoOn, 
    isScreenSharing,
    toggleMute,
    toggleVideo,
    toggleScreenShare,
    leaveRoom,
    unreadCount
  } = useRoom();
  const { user } = useAuthStore();
  
  const [hasRaisedHand, setHasRaisedHand] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  const isHost = room?.host_id === user?.user_id;

  const handleRaiseHand = () => {
    setHasRaisedHand(!hasRaisedHand);
    // TODO: Send hand raise notification via WebSocket
  };

  const handleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleLeave = async () => {
    if (window.confirm('Are you sure you want to leave the meeting?')) {
      await leaveRoom();
    }
  };

  return (
    <div className="bg-gray-900 border-t border-gray-800">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          {/* Left controls */}
          <div className="flex items-center space-x-2">
            {/* Microphone */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={toggleMute}
              className={`p-3 rounded-lg transition-colors ${
                isMuted 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-gray-700 hover:bg-gray-600 text-white'
              }`}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? (
                <SpeakerXMarkIcon className="h-5 w-5" />
              ) : (
                <MicrophoneIcon className="h-5 w-5" />
              )}
            </motion.button>

            {/* Camera */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={toggleVideo}
              className={`p-3 rounded-lg transition-colors ${
                !isVideoOn 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-gray-700 hover:bg-gray-600 text-white'
              }`}
              title={isVideoOn ? 'Turn off camera' : 'Turn on camera'}
            >
              {!isVideoOn ? (
                <VideoCameraSlashIcon className="h-5 w-5" />
              ) : (
                <VideoCameraIcon className="h-5 w-5" />
              )}
            </motion.button>

            {/* Screen share */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={toggleScreenShare}
              className={`p-3 rounded-lg transition-colors ${
                isScreenSharing 
                  ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                  : 'bg-gray-700 hover:bg-gray-600 text-white'
              }`}
              title={isScreenSharing ? 'Stop sharing' : 'Share screen'}
            >
              <ComputerDesktopIcon className="h-5 w-5" />
            </motion.button>
          </div>

          {/* Center controls */}
          <div className="flex items-center space-x-2">
            {/* Raise hand */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={handleRaiseHand}
              className={`p-3 rounded-lg transition-colors ${
                hasRaisedHand 
                  ? 'bg-yellow-600 hover:bg-yellow-700 text-white' 
                  : 'bg-gray-700 hover:bg-gray-600 text-white'
              }`}
              title={hasRaisedHand ? 'Lower hand' : 'Raise hand'}
            >
              <HandRaisedIcon className="h-5 w-5" />
            </motion.button>

            {/* Chat */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={onToggleChat}
              className={`relative p-3 rounded-lg transition-colors ${
                showChat 
                  ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                  : 'bg-gray-700 hover:bg-gray-600 text-white'
              }`}
              title="Toggle chat"
            >
              <ChatBubbleLeftIcon className="h-5 w-5" />
              {unreadCount > 0 && !showChat && (
                <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </motion.button>

            {/* Participants - Only show for hosts */}
            {isHost && (
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={onToggleParticipants}
                className={`p-3 rounded-lg transition-colors ${
                  showParticipants 
                    ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                    : 'bg-gray-700 hover:bg-gray-600 text-white'
                }`}
                title="Toggle participants"
              >
                <UserGroupIcon className="h-5 w-5" />
              </motion.button>
            )}

            {/* AI Assistant - Only show if onToggleAI is provided (teaching rooms) */}
            {onToggleAI && (
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={onToggleAI}
                className={`p-3 rounded-lg transition-colors ${
                  showAI 
                    ? 'bg-purple-600 hover:bg-purple-700 text-white' 
                    : 'bg-gray-700 hover:bg-gray-600 text-white'
                }`}
                title="Toggle AI assistant"
              >
                <CpuChipIcon className="h-5 w-5" />
              </motion.button>
            )}

            {/* Settings */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowSettings(!showSettings)}
              className="p-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              title="Settings"
            >
              <Cog6ToothIcon className="h-5 w-5" />
            </motion.button>

            {/* Fullscreen */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={handleFullscreen}
              className="p-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              {isFullscreen ? (
                <ArrowsPointingInIcon className="h-5 w-5" />
              ) : (
                <ArrowsPointingOutIcon className="h-5 w-5" />
              )}
            </motion.button>
          </div>

          {/* Right controls */}
          <div>
            {/* Leave meeting */}
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={handleLeave}
              className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center space-x-2"
            >
              <PhoneXMarkIcon className="h-5 w-5" />
              <span>Leave</span>
            </motion.button>
          </div>
        </div>
      </div>

      {/* Settings dropdown */}
      {showSettings && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="absolute bottom-full mb-2 right-4 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2"
        >
          <div className="px-4 py-2">
            <h3 className="text-sm font-medium text-gray-900 mb-2">Audio & Video Settings</h3>
            
            {/* Microphone selection */}
            <div className="mb-3">
              <label className="text-xs text-gray-600">Microphone</label>
              <select className="w-full mt-1 px-2 py-1 text-sm border border-gray-300 rounded">
                <option>Default Microphone</option>
              </select>
            </div>

            {/* Camera selection */}
            <div className="mb-3">
              <label className="text-xs text-gray-600">Camera</label>
              <select className="w-full mt-1 px-2 py-1 text-sm border border-gray-300 rounded">
                <option>Default Camera</option>
              </select>
            </div>

            {/* Speaker selection */}
            <div className="mb-3">
              <label className="text-xs text-gray-600">Speaker</label>
              <select className="w-full mt-1 px-2 py-1 text-sm border border-gray-300 rounded">
                <option>Default Speaker</option>
              </select>
            </div>

            {/* Video quality */}
            <div>
              <label className="text-xs text-gray-600">Video Quality</label>
              <select className="w-full mt-1 px-2 py-1 text-sm border border-gray-300 rounded">
                <option>HD (720p)</option>
                <option>SD (480p)</option>
                <option>LD (360p)</option>
              </select>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default VideoControls;