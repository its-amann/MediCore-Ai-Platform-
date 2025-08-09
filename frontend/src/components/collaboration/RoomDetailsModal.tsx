import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Avatar,
  Chip,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Close as CloseIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  School as SchoolIcon,
  Lock as LockIcon,
  CalendarToday as CalendarIcon,
  AccessTime as AccessTimeIcon,
  Description as DescriptionIcon,
  Tag as TagIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import { Room, RoomType } from '../../services/collaborationService';

interface RoomDetailsModalProps {
  open: boolean;
  onClose: () => void;
  room: Room;
  onJoinRequest: (roomId: string, message?: string) => void;
}

const RoomDetailsModal: React.FC<RoomDetailsModalProps> = ({
  open,
  onClose,
  room,
  onJoinRequest,
}) => {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSendRequest = async () => {
    setLoading(true);
    try {
      await onJoinRequest(room.room_id, message);
      setMessage('');
    } finally {
      setLoading(false);
    }
  };

  const getRoomIcon = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return <SchoolIcon />;
      case RoomType.CASE_DISCUSSION:
      default:
        return <GroupIcon />;
    }
  };

  const getRoomTypeLabel = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return 'Teaching Session';
      case RoomType.CASE_DISCUSSION:
        return 'Case Discussion';
      default:
        return type;
    }
  };

  const getRoomTypeColor = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return 'secondary';
      case RoomType.CASE_DISCUSSION:
      default:
        return 'primary';
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Room Details</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          {/* Room Header */}
          <Box display="flex" alignItems="center" mb={3}>
            <Avatar
              sx={{
                bgcolor: `${getRoomTypeColor(room.room_type)}.main`,
                width: 56,
                height: 56,
                mr: 2,
              }}
            >
              {getRoomIcon(room.room_type)}
            </Avatar>
            <Box flex={1}>
              <Typography variant="h5" gutterBottom>
                {room.name}
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                <Chip
                  label={getRoomTypeLabel(room.room_type)}
                  color={getRoomTypeColor(room.room_type)}
                  size="small"
                />
                {room.is_private && (
                  <Chip
                    icon={<LockIcon />}
                    label="Private"
                    variant="outlined"
                    size="small"
                  />
                )}
              </Box>
            </Box>
          </Box>

          {/* Room Info */}
          <List>
            {room.description && (
              <ListItem>
                <ListItemIcon>
                  <DescriptionIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Description"
                  secondary={room.description}
                />
              </ListItem>
            )}

            <ListItem>
              <ListItemIcon>
                <PersonIcon />
              </ListItemIcon>
              <ListItemText
                primary="Creator"
                secondary="Dr. Smith" // This would come from user data
              />
            </ListItem>

            <ListItem>
              <ListItemIcon>
                <GroupIcon />
              </ListItemIcon>
              <ListItemText
                primary="Participants"
                secondary={`${room.participant_count || 0} / ${room.max_participants || 'unlimited'}`}
              />
            </ListItem>

            <ListItem>
              <ListItemIcon>
                <CalendarIcon />
              </ListItemIcon>
              <ListItemText
                primary="Created"
                secondary={new Date(room.created_at).toLocaleDateString()}
              />
            </ListItem>

            {/* Teaching-specific info */}
            {room.room_type === RoomType.TEACHING && room.metadata && (
              <>
                {room.metadata.subject && (
                  <ListItem>
                    <ListItemIcon>
                      <SchoolIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary="Subject"
                      secondary={room.metadata.subject}
                    />
                  </ListItem>
                )}
                {room.metadata.schedule_time && (
                  <ListItem>
                    <ListItemIcon>
                      <AccessTimeIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary="Schedule"
                      secondary={new Date(room.metadata.schedule_time).toLocaleString()}
                    />
                  </ListItem>
                )}
              </>
            )}
          </List>

          {/* Tags */}
          {room.tags && room.tags.length > 0 && (
            <Box mt={2}>
              <Box display="flex" alignItems="center" mb={1}>
                <TagIcon sx={{ mr: 1 }} />
                <Typography variant="subtitle2">Tags</Typography>
              </Box>
              <Box display="flex" flexWrap="wrap" gap={0.5}>
                {room.tags.map((tag: string, index: number) => (
                  <Chip
                    key={index}
                    label={tag}
                    size="small"
                    color={getRoomTypeColor(room.room_type)}
                  />
                ))}
              </Box>
            </Box>
          )}

          <Divider sx={{ my: 3 }} />

          {/* Join Request Message */}
          <Typography variant="subtitle1" gutterBottom>
            Request to Join
          </Typography>
          <Typography variant="body2" color="textSecondary" mb={2}>
            This is a private room. Send a message to the room creator explaining why you'd like to join.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            placeholder="Hi, I'm interested in joining this room because..."
            value={message}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMessage(e.target.value)}
            variant="outlined"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSendRequest}
          disabled={loading || !message.trim()}
          startIcon={<SendIcon />}
        >
          Send Request
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RoomDetailsModal;