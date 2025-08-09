import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  IconButton,
  Button,
  Paper,
  Typography,
  Grid,
  Avatar,
  Chip,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Videocam as VideocamIcon,
  VideocamOff as VideocamOffIcon,
  ScreenShare as ScreenShareIcon,
  StopScreenShare as StopScreenShareIcon,
  CallEnd as CallEndIcon,
  Chat as ChatIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  MoreVert as MoreVertIcon,
  RecordVoiceOver as RecordIcon,
  School as SchoolIcon,
  PanTool as HandIcon,
} from '@mui/icons-material';
import { Room, RoomType } from '../../services/collaborationService';
import { VideoParticipant } from '../../types/room';
import { useWebSocket, useWebSocketConnection } from '../../contexts/WebSocketContext';
import ChatArea from '../rooms/chat/ChatArea';
import ParticipantsList from '../rooms/ParticipantsList';
import { toast } from 'react-hot-toast';

interface VideoRoomProps {
  room: Room;
  currentUserId: string;
  onLeave: () => void;
}

interface MediaState {
  audio: boolean;
  video: boolean;
  screen: boolean;
}

const VideoRoom: React.FC<VideoRoomProps> = ({ room, currentUserId, onLeave }) => {
  const { socket, sendMessage } = useWebSocket();
  
  // Explicitly connect WebSocket when video room is used
  useWebSocketConnection();
  
  const [participants, setParticipants] = useState<VideoParticipant[]>([]);
  const [mediaState, setMediaState] = useState<MediaState>({
    audio: true,
    video: true,
    screen: false,
  });
  const [showChat, setShowChat] = useState(true);
  const [showParticipants, setShowParticipants] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [hasRaisedHand, setHasRaisedHand] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedParticipant, setSelectedParticipant] = useState<VideoParticipant | null>(null);
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const peersRef = useRef<Map<string, RTCPeerConnection>>(new Map());
  const remoteStreamsRef = useRef<Map<string, MediaStream>>(new Map());

  const isHost = room.host_id === currentUserId;
  const isTeachingRoom = room.room_type === RoomType.TEACHING;

  useEffect(() => {
    initializeMedia();
    return () => {
      cleanup();
    };
  }, []);

  const initializeMedia = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: mediaState.video,
        audio: mediaState.audio,
      });
      
      localStreamRef.current = stream;
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }

      // Notify others that we joined
      sendMessage({
        type: 'room_participant_joined',
        room_id: room.room_id,
        user_id: currentUserId,
        media_state: mediaState,
      });
    } catch (error) {
      console.error('Failed to access media devices:', error);
      toast.error('Failed to access camera/microphone');
    }
  };

  const cleanup = () => {
    // Stop all tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
    }

    // Close all peer connections
    peersRef.current.forEach(peer => peer.close());
    peersRef.current.clear();
    remoteStreamsRef.current.clear();
  };

  const toggleAudio = () => {
    if (localStreamRef.current) {
      const audioTracks = localStreamRef.current.getAudioTracks();
      audioTracks.forEach(track => {
        track.enabled = !mediaState.audio;
      });
      setMediaState(prev => ({ ...prev, audio: !prev.audio }));
      
      // Notify others
      sendMessage({
        type: 'media_state_changed',
        room_id: room.room_id,
        user_id: currentUserId,
        media_state: { ...mediaState, audio: !mediaState.audio },
      });
    }
  };

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTracks = localStreamRef.current.getVideoTracks();
      videoTracks.forEach(track => {
        track.enabled = !mediaState.video;
      });
      setMediaState(prev => ({ ...prev, video: !prev.video }));
      
      // Notify others
      sendMessage({
        type: 'media_state_changed',
        room_id: room.room_id,
        user_id: currentUserId,
        media_state: { ...mediaState, video: !mediaState.video },
      });
    }
  };

  const toggleScreenShare = async () => {
    if (!mediaState.screen) {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false,
        });
        
        screenStreamRef.current = stream;
        setMediaState(prev => ({ ...prev, screen: true }));
        
        // Handle screen share ending
        stream.getVideoTracks()[0].onended = () => {
          setMediaState(prev => ({ ...prev, screen: false }));
          screenStreamRef.current = null;
        };

        // Notify others
        sendMessage({
          type: 'screen_share_started',
          room_id: room.room_id,
          user_id: currentUserId,
        });
      } catch (error) {
        console.error('Failed to share screen:', error);
        toast.error('Failed to share screen');
      }
    } else {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
        screenStreamRef.current = null;
      }
      setMediaState(prev => ({ ...prev, screen: false }));
      
      // Notify others
      sendMessage({
        type: 'screen_share_stopped',
        room_id: room.room_id,
        user_id: currentUserId,
      });
    }
  };

  const handleStartClass = () => {
    if (isHost && isTeachingRoom) {
      sendMessage({
        type: 'class_started',
        room_id: room.room_id,
        teacher_id: currentUserId,
      });
      toast.success('Class has started!');
    }
  };

  const handleRaiseHand = () => {
    setHasRaisedHand(!hasRaisedHand);
    sendMessage({
      type: 'hand_raised',
      room_id: room.room_id,
      user_id: currentUserId,
      raised: !hasRaisedHand,
    });
  };

  const handleParticipantMenu = (event: React.MouseEvent<HTMLElement>, participant: VideoParticipant) => {
    setAnchorEl(event.currentTarget);
    setSelectedParticipant(participant);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedParticipant(null);
  };

  const handleMuteParticipant = () => {
    if (selectedParticipant && isHost) {
      sendMessage({
        type: 'mute_participant',
        room_id: room.room_id,
        participant_id: selectedParticipant.user_id,
      });
      toast.success(`Muted ${selectedParticipant.username}`);
    }
    handleMenuClose();
  };

  const handleRemoveParticipant = () => {
    if (selectedParticipant && isHost) {
      sendMessage({
        type: 'remove_participant',
        room_id: room.room_id,
        participant_id: selectedParticipant.user_id,
      });
      toast.success(`Removed ${selectedParticipant.username}`);
    }
    handleMenuClose();
  };

  const getVideoGridColumns = () => {
    const participantCount = participants.length + 1; // +1 for local video
    if (participantCount <= 2) return 2;
    if (participantCount <= 4) return 2;
    if (participantCount <= 9) return 3;
    return 4;
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', bgcolor: '#1a1a1a', overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.1)', flexShrink: 0 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6" color="white">
              {room.name}
            </Typography>
            {isTeachingRoom && (
              <Chip
                icon={<SchoolIcon />}
                label="Teaching Session"
                color="secondary"
                size="small"
              />
            )}
            {isRecording && (
              <Chip
                icon={<RecordIcon />}
                label="Recording"
                color="error"
                size="small"
              />
            )}
          </Box>
          {isHost && isTeachingRoom && (
            <Button
              variant="contained"
              color="primary"
              startIcon={<SchoolIcon />}
              onClick={handleStartClass}
            >
              Start Class
            </Button>
          )}
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {/* Video Grid */}
        <Box sx={{ flex: 1, p: 2, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Grid container spacing={2} sx={{ flex: 1, overflow: 'auto' }}>
            {/* Local Video */}
            <Grid item xs={12 / getVideoGridColumns()}>
              <Paper
                sx={{
                  height: '100%',
                  minHeight: '200px',
                  position: 'relative',
                  bgcolor: 'black',
                  overflow: 'hidden',
                }}
              >
                <video
                  ref={localVideoRef}
                  autoPlay
                  muted
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                />
                <Box
                  sx={{
                    position: 'absolute',
                    bottom: 8,
                    left: 8,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                  }}
                >
                  <Chip
                    label="You"
                    size="small"
                    sx={{ bgcolor: 'rgba(0,0,0,0.5)', color: 'white' }}
                  />
                  {!mediaState.audio && (
                    <MicOffIcon sx={{ color: 'red', fontSize: 20 }} />
                  )}
                </Box>
              </Paper>
            </Grid>

            {/* Remote Videos */}
            {participants.map((participant) => (
              <Grid item xs={12 / getVideoGridColumns()} key={participant.user_id}>
                <Paper
                  sx={{
                    height: '100%',
                    position: 'relative',
                    bgcolor: 'black',
                    overflow: 'hidden',
                  }}
                >
                  {participant.is_video_on ? (
                    <video
                      autoPlay
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                      }}
                    />
                  ) : (
                    <Box
                      sx={{
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Avatar sx={{ width: 80, height: 80 }}>
                        {participant.username[0].toUpperCase()}
                      </Avatar>
                    </Box>
                  )}
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: 8,
                      left: 8,
                      right: 8,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={participant.username}
                        size="small"
                        sx={{ bgcolor: 'rgba(0,0,0,0.5)', color: 'white' }}
                      />
                      {participant.has_raised_hand && (
                        <HandIcon sx={{ color: 'yellow', fontSize: 20 }} />
                      )}
                      {!participant.is_muted && (
                        <MicOffIcon sx={{ color: 'red', fontSize: 20 }} />
                      )}
                    </Box>
                    {isHost && (
                      <IconButton
                        size="small"
                        onClick={(e: React.MouseEvent<HTMLElement>) => handleParticipantMenu(e, participant)}
                        sx={{ color: 'white' }}
                      >
                        <MoreVertIcon />
                      </IconButton>
                    )}
                  </Box>
                </Paper>
              </Grid>
            ))}
          </Grid>

          {/* Controls */}
          <Box
            sx={{
              mt: 'auto',
              p: 2,
              bgcolor: 'rgba(0,0,0,0.8)',
              borderRadius: 2,
              display: 'flex',
              justifyContent: 'center',
              gap: 2,
              flexShrink: 0,
            }}
          >
            <Tooltip title={mediaState.audio ? 'Mute' : 'Unmute'}>
              <IconButton
                onClick={toggleAudio}
                sx={{
                  bgcolor: mediaState.audio ? 'rgba(255,255,255,0.1)' : 'error.main',
                  color: 'white',
                  '&:hover': {
                    bgcolor: mediaState.audio ? 'rgba(255,255,255,0.2)' : 'error.dark',
                  },
                }}
              >
                {mediaState.audio ? <MicIcon /> : <MicOffIcon />}
              </IconButton>
            </Tooltip>

            <Tooltip title={mediaState.video ? 'Turn off camera' : 'Turn on camera'}>
              <IconButton
                onClick={toggleVideo}
                sx={{
                  bgcolor: mediaState.video ? 'rgba(255,255,255,0.1)' : 'error.main',
                  color: 'white',
                  '&:hover': {
                    bgcolor: mediaState.video ? 'rgba(255,255,255,0.2)' : 'error.dark',
                  },
                }}
              >
                {mediaState.video ? <VideocamIcon /> : <VideocamOffIcon />}
              </IconButton>
            </Tooltip>

            <Tooltip title={mediaState.screen ? 'Stop sharing' : 'Share screen'}>
              <IconButton
                onClick={toggleScreenShare}
                sx={{
                  bgcolor: mediaState.screen ? 'primary.main' : 'rgba(255,255,255,0.1)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: mediaState.screen ? 'primary.dark' : 'rgba(255,255,255,0.2)',
                  },
                }}
              >
                {mediaState.screen ? <StopScreenShareIcon /> : <ScreenShareIcon />}
              </IconButton>
            </Tooltip>

            {!isHost && (
              <Tooltip title={hasRaisedHand ? 'Lower hand' : 'Raise hand'}>
                <IconButton
                  onClick={handleRaiseHand}
                  sx={{
                    bgcolor: hasRaisedHand ? 'warning.main' : 'rgba(255,255,255,0.1)',
                    color: 'white',
                    '&:hover': {
                      bgcolor: hasRaisedHand ? 'warning.dark' : 'rgba(255,255,255,0.2)',
                    },
                  }}
                >
                  <HandIcon />
                </IconButton>
              </Tooltip>
            )}

            <Box sx={{ mx: 2, borderLeft: '1px solid rgba(255,255,255,0.3)', height: 40 }} />

            <Tooltip title="Chat">
              <IconButton
                onClick={() => setShowChat(!showChat)}
                sx={{
                  bgcolor: showChat ? 'primary.main' : 'rgba(255,255,255,0.1)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: showChat ? 'primary.dark' : 'rgba(255,255,255,0.2)',
                  },
                }}
              >
                <ChatIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="Participants">
              <IconButton
                onClick={() => setShowParticipants(!showParticipants)}
                sx={{
                  bgcolor: showParticipants ? 'primary.main' : 'rgba(255,255,255,0.1)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: showParticipants ? 'primary.dark' : 'rgba(255,255,255,0.2)',
                  },
                }}
              >
                <PeopleIcon />
              </IconButton>
            </Tooltip>

            <Box sx={{ mx: 2, borderLeft: '1px solid rgba(255,255,255,0.3)', height: 40 }} />

            <Tooltip title="Leave">
              <IconButton
                onClick={onLeave}
                sx={{
                  bgcolor: 'error.main',
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'error.dark',
                  },
                }}
              >
                <CallEndIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Side Panel */}
        {(showChat || showParticipants) && (
          <Box
            sx={{
              width: 320,
              borderLeft: '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {showChat && !showParticipants && (
              <ChatArea roomId={room.room_id} currentUserId={currentUserId} />
            )}
            {showParticipants && !showChat && (
              <ParticipantsList
                participants={participants}
                currentUserId={currentUserId}
                isHost={isHost}
              />
            )}
          </Box>
        )}
      </Box>

      {/* Participant Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMuteParticipant}>
          <ListItemIcon>
            <MicOffIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Mute Participant</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleRemoveParticipant}>
          <ListItemIcon>
            <CallEndIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Remove from Room</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default VideoRoom;