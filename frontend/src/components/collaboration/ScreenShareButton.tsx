import React, { useState, useCallback } from 'react';
import {
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Badge,
  Box
} from '@mui/material';
import {
  ScreenShare as ScreenShareIcon,
  StopScreenShare as StopScreenShareIcon,
  Monitor as MonitorIcon,
  Window as WindowIcon,
  Tab as TabIcon,
  HighQuality as HighQualityIcon,
  Hd as HdIcon,
  SdCard as SdIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { 
  ScreenShareSourceType, 
  ScreenShareQuality,
  ScreenShareStatus 
} from '../../types/collaboration';

interface ScreenShareButtonProps {
  roomId: string;
  isSharing: boolean;
  currentQuality?: ScreenShareQuality;
  viewerCount?: number;
  onStartShare: (sourceType: ScreenShareSourceType, quality: ScreenShareQuality) => Promise<void>;
  onStopShare: () => Promise<void>;
  onQualityChange?: (quality: ScreenShareQuality) => void;
  disabled?: boolean;
}

export const ScreenShareButton: React.FC<ScreenShareButtonProps> = ({
  roomId,
  isSharing,
  currentQuality = ScreenShareQuality.AUTO,
  viewerCount = 0,
  onStartShare,
  onStopShare,
  onQualityChange,
  disabled
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [qualityAnchorEl, setQualityAnchorEl] = useState<null | HTMLElement>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    if (isSharing) {
      handleStopShare();
    } else {
      setAnchorEl(event.currentTarget);
    }
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleQualityMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setQualityAnchorEl(event.currentTarget);
  };

  const handleQualityMenuClose = () => {
    setQualityAnchorEl(null);
  };

  const handleStartShare = async (sourceType: ScreenShareSourceType) => {
    handleClose();
    setIsLoading(true);
    
    try {
      await onStartShare(sourceType, currentQuality);
      toast.success(`Started sharing ${sourceType}`);
    } catch (error: any) {
      toast.error(error.message || 'Failed to start screen sharing');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopShare = async () => {
    setIsLoading(true);
    
    try {
      await onStopShare();
      toast.success('Screen sharing stopped');
    } catch (error: any) {
      toast.error(error.message || 'Failed to stop screen sharing');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQualityChange = (quality: ScreenShareQuality) => {
    handleQualityMenuClose();
    if (onQualityChange) {
      onQualityChange(quality);
      toast.success(`Quality changed to ${quality}`);
    }
  };

  const getQualityIcon = (quality: ScreenShareQuality) => {
    switch (quality) {
      case ScreenShareQuality.HIGH:
        return <HighQualityIcon fontSize="small" />;
      case ScreenShareQuality.MEDIUM:
        return <HdIcon fontSize="small" />;
      case ScreenShareQuality.LOW:
        return <SdIcon fontSize="small" />;
      default:
        return <SettingsIcon fontSize="small" />;
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
    <>
      <Box position="relative" display="inline-flex">
        <Tooltip title={isSharing ? 'Stop sharing' : 'Share screen'}>
          <span>
            <IconButton
              color={isSharing ? 'error' : 'default'}
              onClick={handleClick}
              disabled={disabled || isLoading}
              size="large"
            >
              {isLoading ? (
                <CircularProgress size={24} />
              ) : isSharing ? (
                <Badge badgeContent={viewerCount} color="primary">
                  <StopScreenShareIcon />
                </Badge>
              ) : (
                <ScreenShareIcon />
              )}
            </IconButton>
          </span>
        </Tooltip>
        
        {isSharing && onQualityChange && (
          <IconButton
            size="small"
            onClick={handleQualityMenuOpen}
            sx={{
              position: 'absolute',
              bottom: -5,
              right: -5,
              backgroundColor: 'background.paper',
              border: 1,
              borderColor: 'divider',
              padding: 0.5,
              '&:hover': {
                backgroundColor: 'action.hover'
              }
            }}
          >
            {getQualityIcon(currentQuality)}
          </IconButton>
        )}
      </Box>

      {/* Source Selection Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center'
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'center'
        }}
      >
        <MenuItem onClick={() => handleStartShare(ScreenShareSourceType.SCREEN)}>
          <ListItemIcon>
            <MonitorIcon />
          </ListItemIcon>
          <ListItemText 
            primary="Entire Screen" 
            secondary="Share your entire screen"
          />
        </MenuItem>
        <MenuItem onClick={() => handleStartShare(ScreenShareSourceType.WINDOW)}>
          <ListItemIcon>
            <WindowIcon />
          </ListItemIcon>
          <ListItemText 
            primary="Window" 
            secondary="Share a specific window"
          />
        </MenuItem>
        <MenuItem onClick={() => handleStartShare(ScreenShareSourceType.TAB)}>
          <ListItemIcon>
            <TabIcon />
          </ListItemIcon>
          <ListItemText 
            primary="Browser Tab" 
            secondary="Share a browser tab"
          />
        </MenuItem>
      </Menu>

      {/* Quality Selection Menu */}
      <Menu
        anchorEl={qualityAnchorEl}
        open={Boolean(qualityAnchorEl)}
        onClose={handleQualityMenuClose}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'right'
        }}
        transformOrigin={{
          vertical: 'bottom',
          horizontal: 'right'
        }}
      >
        {Object.values(ScreenShareQuality).map((quality) => (
          <MenuItem
            key={quality}
            onClick={() => handleQualityChange(quality)}
            selected={currentQuality === quality}
          >
            <ListItemIcon>
              {getQualityIcon(quality)}
            </ListItemIcon>
            <ListItemText primary={getQualityLabel(quality)} />
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};