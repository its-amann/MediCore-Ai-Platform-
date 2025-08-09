import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Container,
  Typography,
  IconButton,
  Button,
  Avatar,
  CircularProgress,
  Stack,
  Alert,
  Snackbar,
  useTheme,
  styled,
  keyframes,
  Fade
} from '@mui/material';
import {
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Videocam as VideocamIcon,
  VideocamOff as VideocamOffIcon,
  Psychology as PsychologyIcon,
  Call as CallIcon,
  CallEnd as CallEndIcon,
  FlipCameraIos as FlipCameraIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

// Wave animation keyframes
const waveAnimation = keyframes`
  0% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(2);
  }
  100% {
    transform: scaleY(1);
  }
`;

const shimmerAnimation = keyframes`
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
`;

// Styled components
const ConsultationContainer = styled(Box)(({ theme }: any) => ({
  height: '100vh',
  width: '100vw',
  position: 'relative',
  overflow: 'hidden',
  background: theme.palette.mode === 'dark'
    ? 'radial-gradient(circle at center, #1a1a2e 0%, #0f0f1e 100%)'
    : 'radial-gradient(circle at center, #f5f5f5 0%, #e0e0e0 100%)',
}));

const VideoContainer = styled(Box)({
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  '& video': {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
});

const ControlsOverlay = styled(Box)(({ theme }: any) => ({
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  padding: theme.spacing(3),
  background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: theme.spacing(2),
}));

const WaveContainer = styled(Box)({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '8px',
  height: '120px',
  position: 'relative',
});

interface WaveBarProps {
  index: number;
  isActive: boolean;
  amplitude: number;
}

const WaveBar: React.FC<WaveBarProps> = ({ index, isActive, amplitude }) => {
  const theme = useTheme();
  
  return (
    <Box
      sx={{
        width: '6px',
        height: '40px',
        backgroundColor: theme.palette.primary.main,
        borderRadius: '3px',
        transition: 'all 0.15s ease',
        transform: isActive ? `scaleY(${1 + amplitude})` : 'scaleY(1)',
        animation: isActive ? `${waveAnimation} ${0.8 + index * 0.1}s ease-in-out infinite` : 'none',
        animationDelay: `${index * 0.05}s`,
        opacity: isActive ? 1 : 0.3,
      }}
    />
  );
};

const StartButton = styled(Button)(({ theme }: any) => ({
  borderRadius: '50px',
  padding: '16px 32px',
  fontSize: '1.2rem',
  fontWeight: 600,
  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
  color: 'white',
  boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
  transition: 'all 0.3s ease',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 6px 30px rgba(0,0,0,0.3)',
  },
}));

interface CallButtonProps {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

const CallButton: React.FC<CallButtonProps> = ({ active = false, onClick, children }) => {
  const theme = useTheme();
  
  return (
    <IconButton
      onClick={onClick}
      sx={{
        width: '80px',
        height: '80px',
        backgroundColor: active ? theme.palette.error.main : theme.palette.primary.main,
        color: 'white',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        transition: 'all 0.3s ease',
        '&:hover': {
          backgroundColor: active ? theme.palette.error.dark : theme.palette.primary.dark,
          transform: 'scale(1.1)',
        },
      }}
    >
      {children}
    </IconButton>
  );
};

const ControlButton = styled(IconButton)(({ theme }: any) => ({
  backgroundColor: 'rgba(255,255,255,0.2)',
  backdropFilter: 'blur(10px)',
  color: 'white',
  '&:hover': {
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
}));

interface ConsultationState {
  isActive: boolean;
  isVideoEnabled: boolean;
  isMicEnabled: boolean;
  isConnecting: boolean;
  isThinking: boolean;
  audioLevel: number;
  sessionId: string | null;
  error: string | null;
  cameraFacing: 'user' | 'environment';
}

const VoiceConsultationGeminiLive: React.FC = () => {
  const theme = useTheme();
  const [state, setState] = useState<ConsultationState>({
    isActive: false,
    isVideoEnabled: false,
    isMicEnabled: true,
    isConnecting: false,
    isThinking: false,
    audioLevel: 0,
    sessionId: null,
    error: null,
    cameraFacing: 'user',
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const webSocketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Generate wave bars with different heights
  const waveBars = Array.from({ length: 40 }, (_, i) => ({
    index: i,
    baseHeight: 20 + Math.random() * 40,
  }));

  // Audio level detection
  const detectAudioLevel = useCallback(() => {
    if (!analyserRef.current || !state.isActive) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average audio level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    const normalizedLevel = average / 255;

    setState(prev => ({ ...prev, audioLevel: normalizedLevel }));

    animationFrameRef.current = requestAnimationFrame(detectAudioLevel);
  }, [state.isActive]);

  // Initialize audio context and analyser
  const initializeAudioAnalyser = useCallback(async (stream: MediaStream) => {
    try {
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;

      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      detectAudioLevel();
    } catch (error) {
      console.error('Failed to initialize audio analyser:', error);
    }
  }, [detectAudioLevel]);

  // Start consultation
  const startConsultation = async () => {
    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      // Request microphone permission
      const audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      localStreamRef.current = audioStream;
      await initializeAudioAnalyser(audioStream);

      // Create session through API
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/voice/gemini-live/session', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({
          mode: 'voice_only',
          specialization: 'general',
          doctor_specialization: 'general',
          session_type: 'voice',
          language: 'en'
        }),
      });

      const data = await response.json();
      
      // Connect WebSocket for Gemini Live
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/v1/voice/gemini-live/ws/${data.session_id}`;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('Connected to Gemini Live');
        setState(prev => ({
          ...prev,
          isActive: true,
          isConnecting: false,
          sessionId: data.session_id,
        }));
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ ...prev, error: 'Connection failed' }));
      };

      ws.onclose = () => {
        console.log('Disconnected from Gemini Live');
        endConsultation();
      };

      webSocketRef.current = ws;
    } catch (error) {
      console.error('Failed to start consultation:', error);
      setState(prev => ({
        ...prev,
        isConnecting: false,
        error: 'Failed to start consultation',
      }));
    }
  };

  // End consultation
  const endConsultation = () => {
    // Stop audio animation
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    // Close WebSocket
    if (webSocketRef.current) {
      webSocketRef.current.close();
      webSocketRef.current = null;
    }

    // Stop media streams
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setState({
      isActive: false,
      isVideoEnabled: false,
      isMicEnabled: true,
      isConnecting: false,
      isThinking: false,
      audioLevel: 0,
      sessionId: null,
      error: null,
      cameraFacing: 'user',
    });
  };

  // Toggle video
  const toggleVideo = async () => {
    if (!state.isVideoEnabled) {
      try {
        const videoStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: state.cameraFacing,
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
        });

        if (videoRef.current) {
          videoRef.current.srcObject = videoStream;
        }

        // Add video track to existing stream
        if (localStreamRef.current) {
          const videoTrack = videoStream.getVideoTracks()[0];
          localStreamRef.current.addTrack(videoTrack);
        } else {
          localStreamRef.current = videoStream;
        }

        setState(prev => ({ ...prev, isVideoEnabled: true }));

        // Notify server about video mode
        if (webSocketRef.current) {
          webSocketRef.current.send(JSON.stringify({
            type: 'enable_video',
            session_id: state.sessionId,
          }));
        }
      } catch (error) {
        console.error('Failed to enable video:', error);
        setState(prev => ({ ...prev, error: 'Camera access denied' }));
      }
    } else {
      // Stop video tracks
      if (localStreamRef.current) {
        localStreamRef.current.getVideoTracks().forEach(track => {
          track.stop();
          localStreamRef.current?.removeTrack(track);
        });
      }

      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }

      setState(prev => ({ ...prev, isVideoEnabled: false }));

      // Notify server about disabling video
      if (webSocketRef.current) {
        webSocketRef.current.send(JSON.stringify({
          type: 'disable_video',
          session_id: state.sessionId,
        }));
      }
    }
  };

  // Toggle microphone
  const toggleMic = () => {
    if (localStreamRef.current) {
      const audioTracks = localStreamRef.current.getAudioTracks();
      audioTracks.forEach(track => {
        track.enabled = !state.isMicEnabled;
      });
      setState(prev => ({ ...prev, isMicEnabled: !prev.isMicEnabled }));
    }
  };

  // Flip camera
  const flipCamera = async () => {
    if (!state.isVideoEnabled) return;

    const newFacing = state.cameraFacing === 'user' ? 'environment' : 'user';
    
    try {
      const videoStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: newFacing,
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });

      // Stop old video tracks
      if (localStreamRef.current) {
        localStreamRef.current.getVideoTracks().forEach(track => {
          track.stop();
          localStreamRef.current?.removeTrack(track);
        });
      }

      // Add new video track
      const videoTrack = videoStream.getVideoTracks()[0];
      if (localStreamRef.current) {
        localStreamRef.current.addTrack(videoTrack);
      }

      if (videoRef.current) {
        videoRef.current.srcObject = localStreamRef.current;
      }

      setState(prev => ({ ...prev, cameraFacing: newFacing }));
    } catch (error) {
      console.error('Failed to flip camera:', error);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      endConsultation();
    };
  }, []);

  return (
    <ConsultationContainer>
      {/* Video Background */}
      {state.isVideoEnabled && (
        <VideoContainer>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ transform: state.cameraFacing === 'user' ? 'scaleX(-1)' : 'none' }}
          />
        </VideoContainer>
      )}

      {/* Main Content */}
      <Container maxWidth="md" sx={{ height: '100%', position: 'relative', zIndex: 1 }}>
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          height="100%"
          gap={4}
        >
          {!state.isActive ? (
            // Start Screen
            <Fade in timeout={1000}>
              <Box textAlign="center">
                <Typography
                  variant="h2"
                  fontWeight="bold"
                  gutterBottom
                  sx={{
                    background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  AI Medical Consultation
                </Typography>
                <Typography variant="h5" color="text.secondary" mb={4}>
                  Powered by Gemini Live
                </Typography>
                <StartButton
                  onClick={startConsultation}
                  disabled={state.isConnecting}
                  startIcon={state.isConnecting ? <CircularProgress size={20} /> : <CallIcon />}
                >
                  {state.isConnecting ? 'Connecting...' : 'Start Consultation'}
                </StartButton>
              </Box>
            </Fade>
          ) : (
            // Active Consultation
            <AnimatePresence>
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.3 }}
              >
                {/* AI Assistant Avatar */}
                <Box textAlign="center" mb={4}>
                  <Avatar
                    sx={{
                      width: 120,
                      height: 120,
                      margin: '0 auto',
                      mb: 2,
                      background: state.isThinking
                        ? `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`
                        : theme.palette.primary.main,
                      animation: state.isThinking ? `${shimmerAnimation} 2s linear infinite` : 'none',
                      backgroundSize: state.isThinking ? '200% 100%' : 'auto',
                    }}
                  >
                    <PsychologyIcon sx={{ fontSize: 60 }} />
                  </Avatar>
                  <Typography variant="h5" fontWeight="bold">
                    {state.isThinking ? 'Processing...' : 'Listening...'}
                  </Typography>
                </Box>

                {/* Wave Visualization */}
                <WaveContainer>
                  {waveBars.map((bar, index) => (
                    <WaveBar
                      key={index}
                      index={bar.index}
                      isActive={state.isActive && (state.isMicEnabled || state.isThinking)}
                      amplitude={state.audioLevel * (1 + Math.sin(index * 0.2) * 0.5)}
                    />
                  ))}
                </WaveContainer>
              </motion.div>
            </AnimatePresence>
          )}
        </Box>
      </Container>

      {/* Controls Overlay */}
      {state.isActive && (
        <ControlsOverlay>
          <Stack direction="row" spacing={2}>
            {/* Mic Toggle */}
            <ControlButton onClick={toggleMic}>
              {state.isMicEnabled ? <MicIcon /> : <MicOffIcon />}
            </ControlButton>

            {/* Video Toggle */}
            <ControlButton onClick={toggleVideo}>
              {state.isVideoEnabled ? <VideocamIcon /> : <VideocamOffIcon />}
            </ControlButton>

            {/* End Call Button */}
            <CallButton active onClick={endConsultation}>
              <CallEndIcon sx={{ fontSize: 40 }} />
            </CallButton>

            {/* Flip Camera (only when video is on) */}
            {state.isVideoEnabled && (
              <ControlButton onClick={flipCamera}>
                <FlipCameraIcon />
              </ControlButton>
            )}

            {/* Settings */}
            <ControlButton>
              <SettingsIcon />
            </ControlButton>
          </Stack>
        </ControlsOverlay>
      )}

      {/* Error Snackbar */}
      <Snackbar
        open={!!state.error}
        autoHideDuration={6000}
        onClose={() => setState(prev => ({ ...prev, error: null }))}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity="error" onClose={() => setState(prev => ({ ...prev, error: null }))}>
          {state.error}
        </Alert>
      </Snackbar>
    </ConsultationContainer>
  );
};

export default VoiceConsultationGeminiLive;