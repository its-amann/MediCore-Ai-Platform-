import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Switch,
  FormControlLabel,
  Divider,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  Notifications as NotificationsIcon,
  Email as EmailIcon,
  PhoneIphone as PhoneIcon,
  DoNotDisturb as QuietIcon,
  Save as SaveIcon,
  Restore as RestoreIcon,
  Info as InfoIcon,
  NotificationsActive as ActiveIcon,
  NotificationsOff as OffIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { NotificationPreferences as NotificationPrefsType, NotificationType } from '../../types/collaboration';
import collaborationService from '../../services/collaborationService';

interface NotificationPreferencesProps {
  userId: string;
  initialPreferences?: NotificationPrefsType;
  onSave?: (preferences: NotificationPrefsType) => void;
}

export const NotificationPreferences: React.FC<NotificationPreferencesProps> = ({
  userId,
  initialPreferences,
  onSave
}) => {
  const [preferences, setPreferences] = useState<NotificationPrefsType>(
    initialPreferences || {
      user_id: userId,
      email_enabled: true,
      push_enabled: true,
      urgent_only: false,
      quiet_hours_start: null,
      quiet_hours_end: null,
      join_requests: true,
      room_invitations: true,
      mentions: true,
      messages: false,
      ai_responses: true,
      teaching_reminders: true,
      room_updates: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  );

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [showTestDialog, setShowTestDialog] = useState(false);
  const [quietHoursStart, setQuietHoursStart] = useState<Date | null>(null);
  const [quietHoursEnd, setQuietHoursEnd] = useState<Date | null>(null);

  useEffect(() => {
    if (preferences.quiet_hours_start !== null && preferences.quiet_hours_start !== undefined) {
      const [hours, minutes] = [Math.floor(preferences.quiet_hours_start / 60), preferences.quiet_hours_start % 60];
      const date = new Date();
      date.setHours(hours, minutes, 0, 0);
      setQuietHoursStart(date);
    }

    if (preferences.quiet_hours_end !== null && preferences.quiet_hours_end !== undefined) {
      const [hours, minutes] = [Math.floor(preferences.quiet_hours_end / 60), preferences.quiet_hours_end % 60];
      const date = new Date();
      date.setHours(hours, minutes, 0, 0);
      setQuietHoursEnd(date);
    }
  }, [preferences.quiet_hours_start, preferences.quiet_hours_end]);

  const handleToggle = (field: keyof NotificationPrefsType) => {
    setPreferences(prev => ({
      ...prev,
      [field]: !prev[field as keyof NotificationPrefsType]
    }));
    setHasChanges(true);
  };

  const handleQuietHoursToggle = (enabled: boolean) => {
    if (enabled) {
      setPreferences(prev => ({
        ...prev,
        quiet_hours_start: 22 * 60, // 10 PM
        quiet_hours_end: 8 * 60 // 8 AM
      }));
    } else {
      setPreferences(prev => ({
        ...prev,
        quiet_hours_start: null,
        quiet_hours_end: null
      }));
    }
    setHasChanges(true);
  };

  const handleQuietHoursChange = (type: 'start' | 'end', time: Date | null) => {
    if (time) {
      const minutes = time.getHours() * 60 + time.getMinutes();
      setPreferences(prev => ({
        ...prev,
        [`quiet_hours_${type}`]: minutes
      }));
      
      if (type === 'start') {
        setQuietHoursStart(time);
      } else {
        setQuietHoursEnd(time);
      }
      setHasChanges(true);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // In a real implementation, this would call the API
      // await collaborationService.updateNotificationPreferences(userId, preferences);
      
      if (onSave) {
        onSave(preferences);
      }
      
      toast.success('Notification preferences saved');
      setHasChanges(false);
    } catch (error) {
      toast.error('Failed to save preferences');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (initialPreferences) {
      setPreferences(initialPreferences);
      setHasChanges(false);
    }
  };

  const handleTestNotification = async (type: NotificationType) => {
    try {
      // In a real implementation, this would send a test notification
      toast.success(`Test ${type} notification sent`);
      setShowTestDialog(false);
    } catch (error) {
      toast.error('Failed to send test notification');
    }
  };

  const getNotificationTypeInfo = (type: string) => {
    const info: Record<string, { label: string; description: string }> = {
      join_requests: {
        label: 'Join Requests',
        description: 'When someone requests to join your private room'
      },
      room_invitations: {
        label: 'Room Invitations',
        description: 'When you are invited to join a room'
      },
      mentions: {
        label: 'Mentions',
        description: 'When someone mentions you in a message'
      },
      messages: {
        label: 'All Messages',
        description: 'Receive notifications for all messages (can be noisy)'
      },
      ai_responses: {
        label: 'AI Responses',
        description: 'When AI assistant responds to your questions'
      },
      teaching_reminders: {
        label: 'Teaching Reminders',
        description: 'Reminders for upcoming teaching sessions'
      },
      room_updates: {
        label: 'Room Updates',
        description: 'Important room status changes and announcements'
      }
    };

    return info[type] || { label: type, description: '' };
  };

  const isQuietHoursActive = () => {
    if (preferences.quiet_hours_start === null || preferences.quiet_hours_end === null ||
        preferences.quiet_hours_start === undefined || preferences.quiet_hours_end === undefined) {
      return false;
    }

    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    
    if (preferences.quiet_hours_start <= preferences.quiet_hours_end) {
      return currentMinutes >= preferences.quiet_hours_start && currentMinutes < preferences.quiet_hours_end;
    } else {
      // Handles overnight quiet hours (e.g., 10 PM to 8 AM)
      return currentMinutes >= preferences.quiet_hours_start || currentMinutes < preferences.quiet_hours_end;
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        <Paper sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Box display="flex" alignItems="center" gap={2}>
              <NotificationsIcon color="primary" />
              <Typography variant="h5">Notification Preferences</Typography>
              {isQuietHoursActive() && (
                <Chip
                  icon={<QuietIcon />}
                  label="Quiet Hours Active"
                  size="small"
                  color="warning"
                />
              )}
            </Box>
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                size="small"
                onClick={() => setShowTestDialog(true)}
              >
                Test
              </Button>
              {hasChanges && (
                <>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<RestoreIcon />}
                    onClick={handleReset}
                  >
                    Reset
                  </Button>
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<SaveIcon />}
                    onClick={handleSave}
                    disabled={isSaving}
                  >
                    {isSaving ? <CircularProgress size={20} /> : 'Save'}
                  </Button>
                </>
              )}
            </Stack>
          </Box>

          {/* Master Controls */}
          <Alert severity="info" sx={{ mb: 3 }}>
            Control how and when you receive notifications across all devices
          </Alert>

          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Typography variant="h6">Delivery Methods</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <List>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <EmailIcon />
                        <Typography>Email Notifications</Typography>
                      </Box>
                    }
                    secondary="Receive notifications via email for important events"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={preferences.email_enabled}
                      onChange={() => handleToggle('email_enabled')}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <PhoneIcon />
                        <Typography>Push Notifications</Typography>
                      </Box>
                    }
                    secondary="Receive push notifications on your mobile device"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={preferences.push_enabled}
                      onChange={() => handleToggle('push_enabled')}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <ActiveIcon />
                        <Typography>Urgent Only</Typography>
                      </Box>
                    }
                    secondary="Only receive notifications for urgent matters"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={preferences.urgent_only}
                      onChange={() => handleToggle('urgent_only')}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </AccordionDetails>
          </Accordion>

          {/* Quiet Hours */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Typography variant="h6">Quiet Hours</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <FormControlLabel
                control={
                  <Switch
                    checked={preferences.quiet_hours_start !== null}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleQuietHoursToggle(e.target.checked)}
                  />
                }
                label="Enable quiet hours"
              />
              
              {preferences.quiet_hours_start !== null && (
                <Box mt={2}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <TimePicker
                      label="Start time"
                      value={quietHoursStart}
                      onChange={(time) => handleQuietHoursChange('start', time)}
                      slotProps={{
                        textField: {
                          size: 'small',
                          fullWidth: false
                        }
                      }}
                    />
                    <Typography>to</Typography>
                    <TimePicker
                      label="End time"
                      value={quietHoursEnd}
                      onChange={(time) => handleQuietHoursChange('end', time)}
                      slotProps={{
                        textField: {
                          size: 'small',
                          fullWidth: false
                        }
                      }}
                    />
                  </Stack>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    During quiet hours, only urgent notifications will be delivered
                  </Typography>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>

          {/* Notification Types */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Typography variant="h6">Notification Types</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <List>
                {[
                  'join_requests',
                  'room_invitations',
                  'mentions',
                  'messages',
                  'ai_responses',
                  'teaching_reminders',
                  'room_updates'
                ].map((type) => {
                  const info = getNotificationTypeInfo(type);
                  return (
                    <ListItem key={type}>
                      <ListItemText
                        primary={info.label}
                        secondary={info.description}
                      />
                      <ListItemSecondaryAction>
                        <Switch
                          checked={preferences[type as keyof NotificationPrefsType] as boolean}
                          onChange={() => handleToggle(type as keyof NotificationPrefsType)}
                        />
                      </ListItemSecondaryAction>
                    </ListItem>
                  );
                })}
              </List>
            </AccordionDetails>
          </Accordion>
        </Paper>

        {/* Test Notification Dialog */}
        <Dialog open={showTestDialog} onClose={() => setShowTestDialog(false)}>
          <DialogTitle>Send Test Notification</DialogTitle>
          <DialogContent>
            <Typography variant="body2" sx={{ mb: 2 }}>
              Select a notification type to test:
            </Typography>
            <Stack spacing={1}>
              {Object.values(NotificationType).map((type) => (
                <Button
                  key={type}
                  variant="outlined"
                  fullWidth
                  onClick={() => handleTestNotification(type)}
                >
                  {type.replace(/_/g, ' ').toLowerCase()}
                </Button>
              ))}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowTestDialog(false)}>Cancel</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};