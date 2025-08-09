import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { RoomProvider, useRoom } from '../contexts/RoomContext';
import CaseDiscussionView from '../components/rooms/CaseDiscussionView';
import TeachingView from '../components/rooms/TeachingView';
import ModernVideoRoom from '../components/collaboration/ModernVideoRoom';
import JoinRequests from '../components/collaboration/JoinRequests';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { ArrowLeftIcon, VideoCameraIcon } from '@heroicons/react/24/outline';
import { RoomType } from '../services/collaborationService';
import { Box, Button, Tabs, Tab } from '@mui/material';

const RoomDetailContent: React.FC = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const { room, isLoading, error, loadRoom } = useRoom();
  const [showVideo, setShowVideo] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  
  const currentUserId = localStorage.getItem('userId') || '';
  const isHost = room?.host_id === currentUserId;

  useEffect(() => {
    if (roomId) {
      loadRoom(roomId);
    }
  }, [roomId, loadRoom]);

  const handleLeaveVideo = () => {
    setShowVideo(false);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !room) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">
            {error || 'Room not found'}
          </h2>
          <p className="text-gray-600 mb-6">
            The room you're looking for doesn't exist or you don't have access to it.
          </p>
          <button
            onClick={() => navigate('/rooms')}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Rooms
          </button>
        </div>
      </div>
    );
  }

  // If in video mode, show ModernVideoRoom component
  if (showVideo) {
    return (
      <ModernVideoRoom
        room={room}
        currentUserId={currentUserId}
        onLeave={handleLeaveVideo}
      />
    );
  }

  // Show tabs for room host
  if (isHost) {
    return (
      <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', px: 3, py: 2 }}>
            <Box display="flex" alignItems="center">
              <Button
                startIcon={<ArrowLeftIcon className="h-4 w-4" />}
                onClick={() => navigate('/rooms')}
                sx={{ mr: 2 }}
              >
                Back
              </Button>
              <h2 className="text-xl font-semibold">{room.name}</h2>
            </Box>
            {(room.room_type === RoomType.TEACHING || room.settings?.allow_video) && (
              <Button
                variant="contained"
                startIcon={<VideoCameraIcon />}
                onClick={() => setShowVideo(true)}
              >
                Start Video
              </Button>
            )}
          </Box>
          <Tabs value={tabValue} onChange={(_: React.SyntheticEvent, newValue: number) => setTabValue(newValue)} sx={{ px: 3 }}>
            <Tab label="Room" />
            <Tab label="Join Requests" />
          </Tabs>
        </Box>
        
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          {tabValue === 0 && (
            room.room_type === 'teaching' ? <TeachingView /> : <CaseDiscussionView />
          )}
          {tabValue === 1 && (
            <Box sx={{ p: 3 }}>
              <JoinRequests roomId={room.room_id} roomName={room.name} />
            </Box>
          )}
        </Box>
      </Box>
    );
  }

  // Regular view for participants
  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper', px: 3, py: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box display="flex" alignItems="center">
            <Button
              startIcon={<ArrowLeftIcon className="h-4 w-4" />}
              onClick={() => navigate('/rooms')}
              sx={{ mr: 2 }}
            >
              Back
            </Button>
            <h2 className="text-xl font-semibold">{room.name}</h2>
          </Box>
          {(room.room_type === RoomType.TEACHING || room.settings?.allow_video) && (
            <Button
              variant="contained"
              startIcon={<VideoCameraIcon />}
              onClick={() => setShowVideo(true)}
            >
              Join Video
            </Button>
          )}
        </Box>
      </Box>
      
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {room.room_type === 'teaching' ? <TeachingView /> : <CaseDiscussionView />}
      </Box>
    </Box>
  );
};

const RoomDetailNew: React.FC = () => {
  const { roomId } = useParams<{ roomId: string }>();

  if (!roomId) {
    return <div>Invalid room ID</div>;
  }

  return (
    <RoomProvider roomId={roomId}>
      <RoomDetailContent />
    </RoomProvider>
  );
};

export default RoomDetailNew;