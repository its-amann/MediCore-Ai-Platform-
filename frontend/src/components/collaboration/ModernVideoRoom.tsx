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
  Slide,
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
  SmartToy as AIIcon,
} from '@mui/icons-material';
import { Room, RoomType } from '../../services/collaborationService';
import { VideoParticipant } from '../../types/room';
import { useWebSocket } from '../../contexts/WebSocketContext';
import EnhancedChatArea from '../rooms/chat/EnhancedChatArea';
import ParticipantsList from '../rooms/ParticipantsList';
import AIAssistantPanel from '../ai/AIAssistantPanel';
import { toast } from 'react-hot-toast';

interface ModernVideoRoomProps {
  room: Room;
  currentUserId: string;
  onLeave: () => void;
}

interface MediaState {
  audio: boolean;
  video: boolean;
  screen: boolean;
}

const ModernVideoRoom: React.FC<ModernVideoRoomProps> = ({ room, currentUserId, onLeave }) => {
  const { socket, sendMessage } = useWebSocket();
  const [participants, setParticipants] = useState<VideoParticipant[]>([]);
  const [mediaState, setMediaState] = useState<MediaState>({
    audio: true,
    video: true,
    screen: false,
  });
  const [showChat, setShowChat] = useState(false);
  const [showParticipants, setShowParticipants] = useState(false);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [hasRaisedHand, setHasRaisedHand] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedParticipant, setSelectedParticipant] = useState<VideoParticipant | null>(null);
  const [screenShareUser, setScreenShareUser] = useState<{ id: string; username: string } | null>(null);
  
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
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
    }

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
        setScreenShareUser({ id: currentUserId, username: 'You' });
        
        stream.getVideoTracks()[0].onended = () => {
          setMediaState(prev => ({ ...prev, screen: false }));
          screenStreamRef.current = null;
          setScreenShareUser(null);
        };

        sendMessage({
          type: 'screen_share_started',
          room_id: room.room_id,
          user_id: currentUserId,
          username: 'You',
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
      setScreenShareUser(null);
      
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
    const participantCount = participants.length + 1;
    if (participantCount <= 2) return 2;
    if (participantCount <= 4) return 2;
    if (participantCount <= 9) return 3;
    return 4;
  };

  // Calculate if panels are open
  const rightPanelOpen = showChat || showParticipants || showAIAssistant;
  const activeRightPanel = showChat ? 'chat' : showParticipants ? 'participants' : showAIAssistant ? 'ai' : null;

  return (
    <Box sx={{ 
      height: '100vh', 
      display: 'grid',
      gridTemplateRows: 'auto 1fr',
      bgcolor: '#0F1419',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <Box sx={{ 
        p: 2, 
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        background: 'linear-gradient(180deg, #1a1f2e 0%, #0F1419 100%)'
      }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6" sx={{ color: 'white', fontWeight: 600 }}>
              {room.name}
            </Typography>
            {isTeachingRoom && (
              <Chip
                icon={<SchoolIcon />}
                label="Teaching Session"
                sx={{ 
                  bgcolor: 'rgba(29, 155, 240, 0.1)',
                  color: '#1D9BF0',
                  borderColor: '#1D9BF0',
                  border: '1px solid'
                }}
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
              startIcon={<SchoolIcon />}
              onClick={handleStartClass}
              sx={{
                bgcolor: '#1D9BF0',
                '&:hover': { bgcolor: '#1A8CD8' }
              }}
            >
              Start Class
            </Button>
          )}
        </Box>
      </Box>

      {/* Main Content Area */}
      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: rightPanelOpen ? '1fr 400px' : '1fr',
        gap: 0,
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Video Grid */}
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden',
          transition: 'all 0.3s ease'
        }}>
          <Box sx={{ flex: 1, p: 2, overflow: 'auto' }}>
            <Grid container spacing={2}>
              {/* Local Video */}
              <Grid item xs={12 / getVideoGridColumns()}>
                <Paper
                  sx={{
                    aspectRatio: '16/9',
                    position: 'relative',
                    bgcolor: '#1a1f2e',
                    overflow: 'hidden',
                    borderRadius: 2,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
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
                      sx={{ 
                        bgcolor: 'rgba(0,0,0,0.7)', 
                        color: 'white',
                        fontWeight: 500
                      }}
                    />
                    {!mediaState.audio && (
                      <MicOffIcon sx={{ color: '#F44336', fontSize: 20 }} />
                    )}
                  </Box>
                </Paper>
              </Grid>

              {/* Remote Videos */}
              {participants.map((participant) => (
                <Grid item xs={12 / getVideoGridColumns()} key={participant.user_id}>
                  <Paper
                    sx={{
                      aspectRatio: '16/9',
                      position: 'relative',
                      bgcolor: '#1a1f2e',
                      overflow: 'hidden',
                      borderRadius: 2,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                    }}
                  >
                    {participant.is_video_on ? (
                      <video
                        autoPlay
                        data-user-id={participant.user_id}
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
                          background: 'linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%)'
                        }}
                      >
                        <Avatar sx={{ 
                          width: 80, 
                          height: 80,
                          bgcolor: '#1D9BF0',
                          fontSize: '2rem'
                        }}>
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
                          sx={{ 
                            bgcolor: 'rgba(0,0,0,0.7)', 
                            color: 'white',
                            fontWeight: 500
                          }}
                        />
                        {participant.has_raised_hand && (
                          <HandIcon sx={{ color: '#FFC107', fontSize: 20 }} />
                        )}
                        {!participant.is_muted && (
                          <MicOffIcon sx={{ color: '#F44336', fontSize: 20 }} />
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
          </Box>

          {/* Controls */}
          <Box
            sx={{
              p: 2,
              bgcolor: 'rgba(26, 31, 46, 0.95)',
              backdropFilter: 'blur(10px)',
              borderTop: '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              justifyContent: 'center',
              gap: 2,
            }}
          >
            <Tooltip title={mediaState.audio ? 'Mute' : 'Unmute'}>
              <IconButton
                onClick={toggleAudio}
                sx={{
                  bgcolor: mediaState.audio ? 'rgba(255,255,255,0.1)' : '#F44336',
                  color: 'white',
                  '&:hover': {
                    bgcolor: mediaState.audio ? 'rgba(255,255,255,0.2)' : '#D32F2F',
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
                  bgcolor: mediaState.video ? 'rgba(255,255,255,0.1)' : '#F44336',
                  color: 'white',
                  '&:hover': {
                    bgcolor: mediaState.video ? 'rgba(255,255,255,0.2)' : '#D32F2F',
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
                  bgcolor: mediaState.screen ? '#1D9BF0' : 'rgba(255,255,255,0.1)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: mediaState.screen ? '#1A8CD8' : 'rgba(255,255,255,0.2)',
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
                    bgcolor: hasRaisedHand ? '#FFC107' : 'rgba(255,255,255,0.1)',
                    color: hasRaisedHand ? 'black' : 'white',
                    '&:hover': {
                      bgcolor: hasRaisedHand ? '#FFB300' : 'rgba(255,255,255,0.2)',
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
                onClick={() => {
                  setShowChat(!showChat);
                  setShowParticipants(false);
                  setShowAIAssistant(false);
                }}
                sx={{
                  bgcolor: showChat ? '#1D9BF0' : 'rgba(255,255,255,0.1)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: showChat ? '#1A8CD8' : 'rgba(255,255,255,0.2)',
                  },
                }}
              >
                <ChatIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="Participants">
              <IconButton
                onClick={() => {
                  setShowParticipants(!showParticipants);
                  setShowChat(false);
                  setShowAIAssistant(false);
                }}
                sx={{
                  bgcolor: showParticipants ? '#1D9BF0' : 'rgba(255,255,255,0.1)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: showParticipants ? '#1A8CD8' : 'rgba(255,255,255,0.2)',
                  },
                }}
              >
                <PeopleIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="AI Assistant">
              <IconButton
                onClick={() => {
                  setShowAIAssistant(!showAIAssistant);
                  setShowChat(false);
                  setShowParticipants(false);
                }}
                sx={{
                  bgcolor: showAIAssistant ? '#1D9BF0' : 'rgba(255,255,255,0.1)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: showAIAssistant ? '#1A8CD8' : 'rgba(255,255,255,0.2)',
                  },
                }}
              >
                <AIIcon />
              </IconButton>
            </Tooltip>

            <Box sx={{ mx: 2, borderLeft: '1px solid rgba(255,255,255,0.3)', height: 40 }} />

            <Tooltip title="Leave">
              <IconButton
                onClick={onLeave}
                sx={{
                  bgcolor: '#F44336',
                  color: 'white',
                  '&:hover': {
                    bgcolor: '#D32F2F',
                  },
                }}
              >
                <CallEndIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Right Panel */}
        <Slide direction="left" in={rightPanelOpen} mountOnEnter unmountOnExit>
          <Box
            sx={{
              borderLeft: '1px solid rgba(255,255,255,0.1)',
              bgcolor: '#1a1f2e',
              display: 'flex',
              flexDirection: 'column',
              height: '100%',
              overflow: 'hidden'
            }}
          >
            {activeRightPanel === 'chat' && (
              <EnhancedChatArea 
                roomId={room.room_id} 
                currentUserId={currentUserId}
                isScreenSharing={!!screenShareUser}
                screenShareUserId={screenShareUser?.id}
                screenShareUsername={screenShareUser?.username}
              />
            )}
            {activeRightPanel === 'participants' && (
              <ParticipantsList
                participants={participants}
                currentUserId={currentUserId}
                isHost={isHost}
              />
            )}
            {activeRightPanel === 'ai' && (
              <AIAssistantPanel 
                roomId={room.room_id} 
                roomType={isTeachingRoom ? 'teaching' : 'case_discussion'}
                subject={room.metadata?.subject}
              />
            )}
          </Box>
        </Slide>
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

export default ModernVideoRoom;