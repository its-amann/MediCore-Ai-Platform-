import React, { useRef, useEffect, useState } from 'react';
import {
  Box,
  IconButton,
  Tooltip,
  Typography,
  Paper,
  Chip,
  Stack,
  Button,
  Menu,
  MenuItem,
  Fade
} from '@mui/material';
import {
  Fullscreen as FullscreenIcon,
  FullscreenExit as FullscreenExitIcon,
  VolumeUp as VolumeUpIcon,
  VolumeOff as VolumeOffIcon,
  PictureInPicture as PipIcon,
  Settings as SettingsIcon,
  Person as PersonIcon,
  HighQuality as QualityIcon,
  Pause as PauseIcon,
  PlayArrow as PlayIcon
} from '@mui/icons-material';
import { ScreenShareSession, ScreenShareQuality } from '../../types/collaboration';

interface ScreenShareViewerProps {
  session: ScreenShareSession;
  stream?: MediaStream;
  isOwnShare: boolean;
  onRequestControl?: () => void;
  onQualityRequest?: (quality: ScreenShareQuality) => void;
  onStopViewing?: () => void;
}

export const ScreenShareViewer: React.FC<ScreenShareViewerProps> = ({
  session,
  stream,
  isOwnShare,
  onRequestControl,
  onQualityRequest,
  onStopViewing
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [isPiP, setIsPiP] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [settingsAnchor, setSettingsAnchor] = useState<null | HTMLElement>(null);
  const [showControls, setShowControls] = useState(true);
  const controlsTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(console.error);
    }

    return () => {
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [stream]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    const handleMouseMove = () => {
      setShowControls(true);
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    if (containerRef.current) {
      containerRef.current.addEventListener('mousemove', handleMouseMove);
    }

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      if (containerRef.current) {
        containerRef.current.removeEventListener('mousemove', handleMouseMove);
      }
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, []);

  const toggleFullscreen = async () => {
    if (!containerRef.current) return;

    try {
      if (!isFullscreen) {
        await containerRef.current.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (error) {
      console.error('Fullscreen error:', error);
    }
  };

  const togglePiP = async () => {
    if (!videoRef.current) return;

    try {
      if (!isPiP) {
        await videoRef.current.requestPictureInPicture();
        setIsPiP(true);
      } else {
        await document.exitPictureInPicture();
        setIsPiP(false);
      }
    } catch (error) {
      console.error('PiP error:', error);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const togglePause = () => {
    if (videoRef.current) {
      if (isPaused) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
      setIsPaused(!isPaused);
    }
  };

  const getQualityLabel = (quality: ScreenShareQuality) => {
    switch (quality) {
      case ScreenShareQuality.HIGH:
        return '1080p';
      case ScreenShareQuality.MEDIUM:
        return '720p';
      case ScreenShareQuality.LOW:
        return '480p';
      case ScreenShareQuality.AUTO:
        return 'Auto';
    }
  };

  return (
    <Paper
      ref={containerRef}
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        backgroundColor: 'black',
        overflow: 'hidden',
        cursor: showControls ? 'default' : 'none'
      }}
      elevation={3}
    >
      <video
        ref={videoRef}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain'
        }}
        autoPlay
        muted={isMuted}
        playsInline
      />

      {/* Top Info Bar */}
      <Fade in={showControls}>
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            p: 2,
            background: 'linear-gradient(to bottom, rgba(0,0,0,0.7), transparent)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <PersonIcon sx={{ color: 'white' }} />
            <Typography variant="body2" color="white">
              {isOwnShare ? 'Your Screen' : `Sharing: ${session.user_id}`}
            </Typography>
            <Chip
              size="small"
              label={getQualityLabel(session.quality)}
              icon={<QualityIcon />}
              sx={{ backgroundColor: 'rgba(255,255,255,0.2)', color: 'white' }}
            />
            {session.is_recording && (
              <Chip
                size="small"
                label="Recording"
                color="error"
                sx={{ 
                  '@keyframes pulse': {
                    '0%': { opacity: 1 },
                    '50%': { opacity: 0.5 },
                    '100%': { opacity: 1 }
                  },
                  animation: 'pulse 2s infinite' 
                }}
              />
            )}
          </Stack>

          <Stack direction="row" spacing={1}>
            {session.viewers.length > 0 && (
              <Chip
                size="small"
                label={`${session.viewers.length} viewers`}
                sx={{ backgroundColor: 'rgba(255,255,255,0.2)', color: 'white' }}
              />
            )}
          </Stack>
        </Box>
      </Fade>

      {/* Control Bar */}
      <Fade in={showControls}>
        <Box
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            p: 2,
            background: 'linear-gradient(to top, rgba(0,0,0,0.7), transparent)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 2
          }}
        >
          <IconButton onClick={togglePause} sx={{ color: 'white' }}>
            {isPaused ? <PlayIcon /> : <PauseIcon />}
          </IconButton>

          <IconButton onClick={toggleMute} sx={{ color: 'white' }}>
            {isMuted ? <VolumeOffIcon /> : <VolumeUpIcon />}
          </IconButton>

          {!isOwnShare && onRequestControl && (
            <Button
              variant="outlined"
              size="small"
              onClick={onRequestControl}
              sx={{
                color: 'white',
                borderColor: 'white',
                '&:hover': {
                  borderColor: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)'
                }
              }}
            >
              Request Control
            </Button>
          )}

          <IconButton onClick={togglePiP} sx={{ color: 'white' }}>
            <PipIcon />
          </IconButton>

          <IconButton
            onClick={(e: React.MouseEvent<HTMLButtonElement>) => setSettingsAnchor(e.currentTarget)}
            sx={{ color: 'white' }}
          >
            <SettingsIcon />
          </IconButton>

          <IconButton onClick={toggleFullscreen} sx={{ color: 'white' }}>
            {isFullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
          </IconButton>
        </Box>
      </Fade>

      {/* Settings Menu */}
      <Menu
        anchorEl={settingsAnchor}
        open={Boolean(settingsAnchor)}
        onClose={() => setSettingsAnchor(null)}
      >
        <MenuItem disabled>
          <Typography variant="caption">Quality</Typography>
        </MenuItem>
        {Object.values(ScreenShareQuality).map((quality) => (
          <MenuItem
            key={quality}
            onClick={() => {
              if (onQualityRequest) {
                onQualityRequest(quality);
              }
              setSettingsAnchor(null);
            }}
            selected={session.quality === quality}
          >
            {getQualityLabel(quality)}
          </MenuItem>
        ))}
        {onStopViewing && (
          <>
            <MenuItem divider />
            <MenuItem
              onClick={() => {
                onStopViewing();
                setSettingsAnchor(null);
              }}
            >
              Stop Viewing
            </MenuItem>
          </>
        )}
      </Menu>
    </Paper>
  );
};