import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  IconButton,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  ListItemAvatar,
} from '@mui/material';
import {
  Close as CloseIcon,
  Archive as ArchiveIcon,
  School as SchoolIcon,
  Delete as DeleteIcon,
  Person as PersonIcon,
  CalendarToday as CalendarIcon,
  Book as BookIcon,
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import collaborationService, { Room, RoomType, RoomStatus } from '../../services/collaborationService';

interface RoomSettingsModalProps {
  open: boolean;
  onClose: () => void;
  room: Room;
}

const RoomSettingsModal: React.FC<RoomSettingsModalProps> = ({ open, onClose, room }) => {
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState({
    name: room.name,
    description: room.description || '',
    max_participants: room.max_participants || 10,
    is_private: room.is_private,
    allow_recording: room.settings?.allow_recording || false,
    allow_screen_share: room.settings?.allow_screen_share ?? true,
    allow_file_share: room.settings?.allow_file_share ?? true,
    mute_participants_on_join: room.settings?.mute_participants_on_join || false,
    require_permission_to_speak: room.settings?.require_permission_to_speak || false,
    enable_waiting_room: room.settings?.enable_waiting_room || false,
    enable_chat: room.settings?.enable_chat ?? true,
    enable_reactions: room.settings?.enable_reactions ?? true,
  });
  const [participants, setParticipants] = useState<any[]>([]);
  const [schedule, setSchedule] = useState({
    subject: room.metadata?.subject || '',
    topic: room.metadata?.topic || '',
    schedule_time: room.metadata?.schedule_time || '',
    duration: room.metadata?.duration || 60,
    materials_url: room.metadata?.materials_url || '',
  });

  useEffect(() => {
    if (open) {
      fetchParticipants();
    }
  }, [open]);

  const fetchParticipants = async () => {
    try {
      const response = await collaborationService.getRoomParticipants(room.room_id);
      setParticipants(response.participants || []);
    } catch (error) {
      console.error('Failed to fetch participants:', error);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const updateData: any = {
        name: settings.name,
        description: settings.description,
        max_participants: settings.max_participants,
        is_private: settings.is_private,
        settings: {
          allow_recording: settings.allow_recording,
          allow_screen_share: settings.allow_screen_share,
          allow_file_share: settings.allow_file_share,
          mute_participants_on_join: settings.mute_participants_on_join,
          require_permission_to_speak: settings.require_permission_to_speak,
          enable_waiting_room: settings.enable_waiting_room,
          enable_chat: settings.enable_chat,
          enable_reactions: settings.enable_reactions,
        },
      };

      // Add teaching-specific metadata
      if (room.room_type === RoomType.TEACHING) {
        updateData.metadata = {
          ...room.metadata,
          subject: schedule.subject,
          topic: schedule.topic,
          schedule_time: schedule.schedule_time,
          duration: schedule.duration,
          materials_url: schedule.materials_url,
        };
      }

      await collaborationService.updateRoom(room.room_id, updateData);
      toast.success('Room settings updated successfully');
      onClose();
    } catch (error) {
      console.error('Failed to update room settings:', error);
      toast.error('Failed to update room settings');
    } finally {
      setLoading(false);
    }
  };

  const handleArchive = async () => {
    if (window.confirm('Are you sure you want to archive this room? Participants will no longer be able to access it.')) {
      setLoading(true);
      try {
        await collaborationService.updateRoom(room.room_id, {
          status: RoomStatus.ARCHIVED
        } as any);
        toast.success('Room archived successfully');
        onClose();
      } catch (error) {
        console.error('Failed to archive room:', error);
        toast.error('Failed to archive room');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleRemoveParticipant = async (userId: string) => {
    if (window.confirm('Are you sure you want to remove this participant?')) {
      try {
        await collaborationService.removeParticipant(room.room_id, userId);
        toast.success('Participant removed successfully');
        fetchParticipants();
      } catch (error) {
        console.error('Failed to remove participant:', error);
        toast.error('Failed to remove participant');
      }
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Room Settings</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          {/* Basic Information */}
          <Typography variant="subtitle1" gutterBottom fontWeight="bold">
            Basic Information
          </Typography>
          <Box mb={3}>
            <TextField
              fullWidth
              label="Room Name"
              value={settings.name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, name: e.target.value })}
              margin="normal"
            />
            <TextField
              fullWidth
              label="Description"
              value={settings.description}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, description: e.target.value })}
              margin="normal"
              multiline
              rows={3}
            />
            <TextField
              fullWidth
              label="Max Participants"
              type="number"
              value={settings.max_participants}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, max_participants: parseInt(e.target.value) })}
              margin="normal"
              InputProps={{ inputProps: { min: 2, max: 100 } }}
            />
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Teaching Room Settings */}
          {room.room_type === RoomType.TEACHING && (
            <>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                <SchoolIcon sx={{ mr: 1, verticalAlign: 'bottom' }} />
                Teaching Session Details
              </Typography>
              <Box mb={3}>
                <TextField
                  fullWidth
                  label="Subject"
                  value={schedule.subject}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSchedule({ ...schedule, subject: e.target.value })}
                  margin="normal"
                />
                <TextField
                  fullWidth
                  label="Topic"
                  value={schedule.topic}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSchedule({ ...schedule, topic: e.target.value })}
                  margin="normal"
                />
                <TextField
                  fullWidth
                  label="Schedule Time"
                  type="datetime-local"
                  value={schedule.schedule_time}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSchedule({ ...schedule, schedule_time: e.target.value })}
                  margin="normal"
                  InputLabelProps={{ shrink: true }}
                />
                <TextField
                  fullWidth
                  label="Duration (minutes)"
                  type="number"
                  value={schedule.duration}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSchedule({ ...schedule, duration: parseInt(e.target.value) })}
                  margin="normal"
                  InputProps={{ inputProps: { min: 15, max: 240 } }}
                />
                <TextField
                  fullWidth
                  label="Materials URL"
                  value={schedule.materials_url}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSchedule({ ...schedule, materials_url: e.target.value })}
                  margin="normal"
                  placeholder="Link to presentation or materials"
                />
              </Box>
              <Divider sx={{ my: 3 }} />
            </>
          )}

          {/* Privacy & Security */}
          <Typography variant="subtitle1" gutterBottom fontWeight="bold">
            Privacy & Security
          </Typography>
          <Box mb={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.is_private}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, is_private: e.target.checked })}
                />
              }
              label="Private Room (Requires password or approval)"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enable_waiting_room}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, enable_waiting_room: e.target.checked })}
                />
              }
              label="Enable Waiting Room"
            />
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Permissions */}
          <Typography variant="subtitle1" gutterBottom fontWeight="bold">
            Permissions
          </Typography>
          <Box mb={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.allow_recording}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, allow_recording: e.target.checked })}
                />
              }
              label="Allow Recording"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.allow_screen_share || false}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, allow_screen_share: e.target.checked })}
                />
              }
              label="Allow Screen Sharing"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.allow_file_share}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, allow_file_share: e.target.checked })}
                />
              }
              label="Allow File Sharing"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enable_chat}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, enable_chat: e.target.checked })}
                />
              }
              label="Enable Chat"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enable_reactions}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, enable_reactions: e.target.checked })}
                />
              }
              label="Enable Reactions"
            />
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Audio Settings */}
          <Typography variant="subtitle1" gutterBottom fontWeight="bold">
            Audio Settings
          </Typography>
          <Box mb={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.mute_participants_on_join}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, mute_participants_on_join: e.target.checked })}
                />
              }
              label="Mute Participants on Join"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.require_permission_to_speak}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, require_permission_to_speak: e.target.checked })}
                />
              }
              label="Require Permission to Speak"
            />
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Participants */}
          <Typography variant="subtitle1" gutterBottom fontWeight="bold">
            Participants ({participants.length})
          </Typography>
          <List>
            {participants.map((participant) => (
              <ListItem key={participant.user_id}>
                <ListItemAvatar>
                  <Avatar>
                    <PersonIcon />
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={participant.username}
                  secondary={
                    <Box>
                      <Chip
                        label={participant.role}
                        size="small"
                        color={participant.role === 'host' ? 'primary' : 'default'}
                        sx={{ mr: 1 }}
                      />
                      <Typography variant="caption" color="textSecondary">
                        Joined {new Date(participant.joined_at).toLocaleString()}
                      </Typography>
                    </Box>
                  }
                />
                {participant.role !== 'host' && (
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => handleRemoveParticipant(participant.user_id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                )}
              </ListItem>
            ))}
          </List>

          <Divider sx={{ my: 3 }} />

          {/* Danger Zone */}
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom fontWeight="bold">
              Danger Zone
            </Typography>
            <Typography variant="body2" gutterBottom>
              Archiving this room will make it inaccessible to all participants.
            </Typography>
            <Button
              variant="outlined"
              color="error"
              startIcon={<ArchiveIcon />}
              onClick={handleArchive}
              sx={{ mt: 1 }}
            >
              Archive Room
            </Button>
          </Alert>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={loading || !settings.name}
        >
          Save Changes
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RoomSettingsModal;