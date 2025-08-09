import React, { useRef, useEffect, useState } from 'react';
import { useRoom } from '../../../contexts/RoomContext';
import { useAuthStore } from '../../../store/authStore';
import { VideoParticipant } from '../../../types/room';
import {
  MicrophoneIcon,
  VideoCameraIcon,
  SpeakerXMarkIcon,
  VideoCameraSlashIcon,
  ComputerDesktopIcon,
  HandRaisedIcon,
  ChatBubbleLeftIcon,
  UserIcon
} from '@heroicons/react/24/outline';
import { MicrophoneIcon as MicrophoneSolidIcon } from '@heroicons/react/24/solid';
import { motion } from 'framer-motion';

interface VideoTileProps {
  participant: VideoParticipant;
  isLocal: boolean;
  isFocused: boolean;
  onFocus: () => void;
}

const VideoTile: React.FC<VideoTileProps> = ({ participant, isLocal, isFocused, onFocus }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  useEffect(() => {
    if (videoRef.current && participant.stream) {
      videoRef.current.srcObject = participant.stream;
    }
  }, [participant.stream]);

  const getQualityColor = () => {
    switch (participant.connection_quality) {
      case 'excellent': return 'bg-green-500';
      case 'good': return 'bg-yellow-500';
      case 'poor': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <motion.div
      layoutId={`video-${participant.user_id}`}
      className={`relative bg-gray-900 rounded-lg overflow-hidden cursor-pointer ${
        isFocused ? 'col-span-2 row-span-2' : ''
      }`}
      onClick={onFocus}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      {participant.is_video_on && participant.stream ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={isLocal}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-gray-800">
          <div className="text-center">
            <div className="h-20 w-20 mx-auto mb-3 rounded-full bg-gray-700 flex items-center justify-center">
              {participant.avatar_url ? (
                <img 
                  src={participant.avatar_url} 
                  alt={participant.username}
                  className="h-full w-full rounded-full object-cover"
                />
              ) : (
                <UserIcon className="h-10 w-10 text-gray-500" />
              )}
            </div>
            <p className="text-white font-medium">{participant.username}</p>
          </div>
        </div>
      )}

      {/* Overlay info */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
      
      {/* Bottom bar */}
      <div className="absolute bottom-0 left-0 right-0 p-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-white text-sm font-medium bg-black/50 px-2 py-1 rounded">
              {participant.username}
              {isLocal && ' (You)'}
            </span>
            
            {/* Connection quality */}
            <div className={`h-2 w-2 rounded-full ${getQualityColor()}`} />
          </div>

          {/* Status icons */}
          <div className="flex items-center space-x-1">
            {participant.has_raised_hand && (
              <HandRaisedIcon className="h-4 w-4 text-yellow-400" />
            )}
            
            {participant.is_screen_sharing && (
              <ComputerDesktopIcon className="h-4 w-4 text-blue-400" />
            )}
            
            {participant.is_speaking ? (
              <MicrophoneSolidIcon className="h-4 w-4 text-green-400" />
            ) : participant.is_muted ? (
              <SpeakerXMarkIcon className="h-4 w-4 text-red-400" />
            ) : (
              <MicrophoneIcon className="h-4 w-4 text-gray-400" />
            )}
            
            {!participant.is_video_on && (
              <VideoCameraSlashIcon className="h-4 w-4 text-red-400" />
            )}
          </div>
        </div>
      </div>

      {/* Audio level indicator */}
      {participant.audio_level && participant.audio_level > 0 && !participant.is_muted && (
        <div className="absolute top-2 right-2">
          <div className="flex space-x-0.5">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className={`w-1 h-3 rounded-full transition-all ${
                  i < Math.ceil((participant.audio_level || 0) * 5)
                    ? 'bg-green-400'
                    : 'bg-gray-600'
                }`}
              />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
};

const VideoGrid: React.FC = () => {
  const { participants, localStream, remoteStreams } = useRoom();
  const { user } = useAuthStore();
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [gridLayout, setGridLayout] = useState<string>('');

  // Create video participants from room participants
  const videoParticipants: VideoParticipant[] = participants.map(p => {
    const stream = p.user_id === user?.user_id ? localStream : remoteStreams.get(p.user_id);
    return {
      ...p,
      stream: stream || undefined, // Convert null to undefined
      audio_level: 0 // This would be updated by WebRTC audio level API
    };
  });

  // Filter to only show participants with active video or screen share
  const activeParticipants = videoParticipants.filter(p => 
    p.is_video_on || p.is_screen_sharing || p.user_id === user?.user_id
  );

  // Calculate grid layout based on number of participants
  useEffect(() => {
    const count = activeParticipants.length;
    if (count <= 1) {
      setGridLayout('grid-cols-1');
    } else if (count <= 4) {
      setGridLayout('grid-cols-2');
    } else if (count <= 9) {
      setGridLayout('grid-cols-3');
    } else if (count <= 16) {
      setGridLayout('grid-cols-4');
    } else {
      setGridLayout('grid-cols-5');
    }
  }, [activeParticipants.length]);

  // Auto-focus on screen share
  useEffect(() => {
    const screenSharer = activeParticipants.find(p => p.is_screen_sharing);
    if (screenSharer) {
      setFocusedId(screenSharer.user_id);
    }
  }, [activeParticipants]);

  return (
    <div className="h-full bg-gray-900 p-4">
      <div className={`h-full grid ${gridLayout} gap-4 auto-rows-fr`}>
        {activeParticipants.map(participant => (
          <VideoTile
            key={participant.user_id}
            participant={participant}
            isLocal={participant.user_id === user?.user_id}
            isFocused={participant.user_id === focusedId}
            onFocus={() => setFocusedId(
              focusedId === participant.user_id ? null : participant.user_id
            )}
          />
        ))}
      </div>

      {/* Empty state */}
      {activeParticipants.length === 0 && (
        <div className="h-full flex items-center justify-center">
          <div className="text-center">
            <VideoCameraSlashIcon className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No active video streams</p>
            <p className="text-gray-500 text-sm mt-2">
              Turn on your camera to start the video session
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoGrid;