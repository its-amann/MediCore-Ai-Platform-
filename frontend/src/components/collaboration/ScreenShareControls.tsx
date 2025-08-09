import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  IconButton,
  Switch,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Divider,
  Alert,
  Stack,
  Tooltip
} from '@mui/material';
import {
  Person as PersonIcon,
  ScreenShare as ScreenIcon,
  RemoveRedEye as ViewIcon,
  TouchApp as ControlIcon,
  FiberManualRecord as RecordIcon,
  Block as BlockIcon,
  Settings as SettingsIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import {
  ScreenShareSession,
  ScreenSharePermissions,
  UserProfile,
  UserType
} from '../../types/collaboration';

interface ScreenShareControlsProps {
  session: ScreenShareSession;
  participants: UserProfile[];
  isHost: boolean;
  permissions: Record<string, ScreenSharePermissions>;
  onPermissionChange: (userId: string, permissions: Partial<ScreenSharePermissions>) => void;
  onKickViewer: (userId: string) => void;
  onEndSession: () => void;
}

export const ScreenShareControls: React.FC<ScreenShareControlsProps> = ({
  session,
  participants,
  isHost,
  permissions,
  onPermissionChange,
  onKickViewer,
  onEndSession
}) => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  const getParticipantInfo = (userId: string) => {
    return participants.find(p => p.user_id === userId);
  };

  const getUserTypeColor = (userType: UserType) => {
    const colors: Record<UserType, string> = {
      [UserType.DOCTOR]: '#1976d2',
      [UserType.TEACHER]: '#9c27b0',
      [UserType.STUDENT]: '#4caf50',
      [UserType.PATIENT]: '#ff9800',
      [UserType.ADMIN]: '#f44336'
    };
    return colors[userType] || '#757575';
  };

  const handlePermissionToggle = (userId: string, permission: keyof ScreenSharePermissions) => {
    const userPerms = permissions[userId] || {
      can_share: false,
      can_view: true,
      can_control: false,
      can_record: false
    };

    onPermissionChange(userId, {
      ...userPerms,
      [permission]: !userPerms[permission]
    });
  };

  const openUserSettings = (userId: string) => {
    setSelectedUser(userId);
    setSettingsOpen(true);
  };

  const closeSettings = () => {
    setSelectedUser(null);
    setSettingsOpen(false);
  };

  const renderPermissionIcon = (userId: string) => {
    const userPerms = permissions[userId];
    if (!userPerms) return null;

    const icons = [];
    if (userPerms.can_control) {
      icons.push(
        <Tooltip key="control" title="Can control">
          <ControlIcon fontSize="small" sx={{ color: '#4caf50' }} />
        </Tooltip>
      );
    }
    if (userPerms.can_record) {
      icons.push(
        <Tooltip key="record" title="Can record">
          <RecordIcon fontSize="small" sx={{ color: '#f44336' }} />
        </Tooltip>
      );
    }
    if (!userPerms.can_view) {
      icons.push(
        <Tooltip key="blocked" title="Blocked">
          <BlockIcon fontSize="small" sx={{ color: '#ff5722' }} />
        </Tooltip>
      );
    }

    return <Stack direction="row" spacing={0.5}>{icons}</Stack>;
  };

  return (
    <>
      <Paper sx={{ p: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">Screen Share Controls</Typography>
          {isHost && (
            <Button
              color="error"
              variant="outlined"
              size="small"
              onClick={onEndSession}
              startIcon={<CloseIcon />}
            >
              End Share
            </Button>
          )}
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          {session.user_id === 'current_user' ? (
            'You are sharing your screen'
          ) : (
            `${getParticipantInfo(session.user_id)?.full_name || session.user_id} is sharing`
          )}
        </Alert>

        <Typography variant="subtitle2" gutterBottom>
          Viewers ({session.viewers.length}/{session.max_viewers})
        </Typography>

        <List>
          {session.viewers.map((viewerId) => {
            const participant = getParticipantInfo(viewerId);
            const userPerms = permissions[viewerId];

            return (
              <ListItem key={viewerId} divider>
                <ListItemAvatar>
                  <Avatar
                    sx={{
                      bgcolor: participant ? getUserTypeColor(participant.user_type) : '#757575'
                    }}
                  >
                    {participant?.full_name?.[0] || <PersonIcon />}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2">
                        {participant?.full_name || viewerId}
                      </Typography>
                      {participant && (
                        <Chip
                          size="small"
                          label={participant.user_type}
                          sx={{
                            bgcolor: getUserTypeColor(participant.user_type),
                            color: 'white',
                            fontSize: '0.7rem'
                          }}
                        />
                      )}
                    </Box>
                  }
                  secondary={renderPermissionIcon(viewerId)}
                />
                {isHost && (
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => openUserSettings(viewerId)}
                    >
                      <SettingsIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                )}
              </ListItem>
            );
          })}
        </List>

        {session.viewers.length === 0 && (
          <Box textAlign="center" py={3}>
            <Typography variant="body2" color="text.secondary">
              No viewers yet
            </Typography>
          </Box>
        )}
      </Paper>

      {/* User Settings Dialog */}
      {selectedUser && (
        <Dialog open={settingsOpen} onClose={closeSettings} maxWidth="sm" fullWidth>
          <DialogTitle>
            Viewer Settings
            <IconButton
              onClick={closeSettings}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent>
            {(() => {
              const participant = getParticipantInfo(selectedUser);
              const userPerms = permissions[selectedUser] || {
                can_share: false,
                can_view: true,
                can_control: false,
                can_record: false
              };

              return (
                <>
                  <Box display="flex" alignItems="center" gap={2} mb={3}>
                    <Avatar
                      sx={{
                        bgcolor: participant ? getUserTypeColor(participant.user_type) : '#757575',
                        width: 56,
                        height: 56
                      }}
                    >
                      {participant?.full_name?.[0] || <PersonIcon />}
                    </Avatar>
                    <Box>
                      <Typography variant="h6">
                        {participant?.full_name || selectedUser}
                      </Typography>
                      {participant && (
                        <Typography variant="body2" color="text.secondary">
                          {participant.user_type} • {participant.institution}
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  <Typography variant="subtitle2" gutterBottom>
                    Permissions
                  </Typography>

                  <List>
                    <ListItem>
                      <ListItemText
                        primary="View Screen"
                        secondary="Allow viewing the shared screen"
                      />
                      <Switch
                        checked={userPerms.can_view}
                        onChange={() => handlePermissionToggle(selectedUser, 'can_view')}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Remote Control"
                        secondary="Allow controlling the shared screen"
                      />
                      <Switch
                        checked={userPerms.can_control}
                        onChange={() => handlePermissionToggle(selectedUser, 'can_control')}
                        disabled={!userPerms.can_view}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Record Screen"
                        secondary="Allow recording the shared screen"
                      />
                      <Switch
                        checked={userPerms.can_record}
                        onChange={() => handlePermissionToggle(selectedUser, 'can_record')}
                        disabled={!userPerms.can_view}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Share Own Screen"
                        secondary="Allow sharing their own screen"
                      />
                      <Switch
                        checked={userPerms.can_share}
                        onChange={() => handlePermissionToggle(selectedUser, 'can_share')}
                      />
                    </ListItem>
                  </List>
                </>
              );
            })()}
          </DialogContent>
          <DialogActions>
            <Button
              color="error"
              onClick={() => {
                onKickViewer(selectedUser);
                closeSettings();
              }}
            >
              Remove Viewer
            </Button>
            <Button onClick={closeSettings}>Done</Button>
          </DialogActions>
        </Dialog>
      )}
    </>
  );
};