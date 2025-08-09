import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Button,
  Stack,
  Chip,
  Menu,
  MenuItem,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Typography,
  Divider,
  CircularProgress,
  Popover,
  Tooltip,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachIcon,
  EmojiEmotions as EmojiIcon,
  Code as CodeIcon,
  Image as ImageIcon,
  FormatBold as BoldIcon,
  FormatItalic as ItalicIcon,
  Link as LinkIcon,
  Close as CloseIcon,
  Reply as ReplyIcon,
  AlternateEmail as MentionIcon
} from '@mui/icons-material';
import { UserProfile, ExtendedMessage, UserType } from '../../types/collaboration';

interface EnhancedChatInputProps {
  roomId: string;
  users: UserProfile[];
  currentUserId: string;
  replyTo?: ExtendedMessage;
  onSend: (content: string, mentions: string[], replyToId?: string, attachments?: File[]) => void;
  onCancelReply?: () => void;
  onTyping?: (isTyping: boolean) => void;
  disabled?: boolean;
}

export const EnhancedChatInput: React.FC<EnhancedChatInputProps> = ({
  roomId,
  users,
  currentUserId,
  replyTo,
  onSend,
  onCancelReply,
  onTyping,
  disabled = false
}) => {
  const [message, setMessage] = useState('');
  const [mentions, setMentions] = useState<string[]>([]);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState('');
  const [mentionAnchor, setMentionAnchor] = useState<{ top: number; left: number } | null>(null);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const [sendOnEnter, setSendOnEnter] = useState(true);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart || 0;
    setMessage(value);
    setCursorPosition(cursorPos);

    // Check for @ mentions
    const lastAtSymbol = value.lastIndexOf('@', cursorPos);
    if (lastAtSymbol !== -1 && lastAtSymbol === cursorPos - 1) {
      // Just typed @
      setShowMentions(true);
      setMentionSearch('');
      const input = inputRef.current;
      if (input) {
        const rect = input.getBoundingClientRect();
        setMentionAnchor({ top: rect.bottom, left: rect.left });
      }
    } else if (lastAtSymbol !== -1 && value[lastAtSymbol] === '@') {
      // Typing after @
      const spaceAfterAt = value.indexOf(' ', lastAtSymbol);
      const endPos = spaceAfterAt === -1 ? cursorPos : Math.min(spaceAfterAt, cursorPos);
      const searchTerm = value.substring(lastAtSymbol + 1, endPos);
      setMentionSearch(searchTerm);
      setShowMentions(true);
    } else {
      setShowMentions(false);
      setMentionSearch('');
    }

    // Handle typing indicator
    if (!isTyping) {
      setIsTyping(true);
      if (onTyping) onTyping(true);
    }

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      if (onTyping) onTyping(false);
    }, 1000);
  };

  const handleMentionSelect = (user: UserProfile) => {
    const lastAtSymbol = message.lastIndexOf('@', cursorPosition);
    if (lastAtSymbol !== -1) {
      const beforeMention = message.substring(0, lastAtSymbol);
      const afterMention = message.substring(cursorPosition);
      const newMessage = `${beforeMention}@${user.username} ${afterMention}`;
      setMessage(newMessage);
      setMentions([...mentions, user.user_id]);
      setShowMentions(false);
      
      // Set cursor position after the mention
      setTimeout(() => {
        if (inputRef.current) {
          const newPosition = lastAtSymbol + user.username.length + 2;
          inputRef.current.setSelectionRange(newPosition, newPosition);
          inputRef.current.focus();
        }
      }, 0);
    }
  };

  const handleSend = () => {
    if (message.trim() || attachments.length > 0) {
      onSend(
        message.trim(),
        mentions,
        replyTo?.id,
        attachments.length > 0 ? attachments : undefined
      );
      setMessage('');
      setMentions([]);
      setAttachments([]);
      if (onCancelReply && replyTo) {
        onCancelReply();
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (sendOnEnter && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      } else if (!sendOnEnter && e.ctrlKey) {
        e.preventDefault();
        handleSend();
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setAttachments([...attachments, ...files]);
  };

  const removeAttachment = (index: number) => {
    setAttachments(attachments.filter((_, i) => i !== index));
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

  const filteredUsers = users.filter(user => 
    user.user_id !== currentUserId &&
    user.username.toLowerCase().includes(mentionSearch.toLowerCase())
  );

  return (
    <Box>
      {/* Reply Preview */}
      {replyTo && (
        <Paper
          sx={{
            p: 1.5,
            mx: 2,
            mb: 1,
            bgcolor: 'action.hover',
            borderLeft: 3,
            borderColor: 'primary.main',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <Box>
            <Typography variant="caption" color="text.secondary">
              <ReplyIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
              Replying to {replyTo.sender_name}
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
              {replyTo.content.substring(0, 100)}
              {replyTo.content.length > 100 && '...'}
            </Typography>
          </Box>
          <IconButton size="small" onClick={onCancelReply}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Paper>
      )}

      {/* Attachments Preview */}
      {attachments.length > 0 && (
        <Box sx={{ px: 2, pb: 1 }}>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {attachments.map((file, index) => (
              <Chip
                key={index}
                icon={file.type.startsWith('image/') ? <ImageIcon /> : <AttachIcon />}
                label={file.name}
                onDelete={() => removeAttachment(index)}
                size="small"
              />
            ))}
          </Stack>
        </Box>
      )}

      {/* Input Area */}
      <Box sx={{ p: 2, pt: 1, borderTop: 1, borderColor: 'divider' }}>
        <Stack direction="row" spacing={1} alignItems="flex-end">
          <Box sx={{ flex: 1, position: 'relative' }}>
            <TextField
              ref={inputRef}
              fullWidth
              multiline
              maxRows={4}
              placeholder="Type a message..."
              value={message}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              disabled={disabled}
              sx={{
                '& .MuiOutlinedInput-root': {
                  paddingRight: '100px'
                }
              }}
              InputProps={{
                endAdornment: (
                  <Stack direction="row" spacing={0.5} sx={{ position: 'absolute', right: 8, bottom: 8 }}>
                    <Tooltip title="Attach file">
                      <IconButton size="small" onClick={() => fileInputRef.current?.click()}>
                        <AttachIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Add emoji">
                      <IconButton size="small">
                        <EmojiIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Code block">
                      <IconButton size="small">
                        <CodeIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                )
              }}
            />
          </Box>

          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={disabled || (!message.trim() && attachments.length === 0)}
          >
            <SendIcon />
          </IconButton>
        </Stack>

        <Box display="flex" justifyContent="space-between" alignItems="center" mt={1}>
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={sendOnEnter}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSendOnEnter(e.target.checked)}
              />
            }
            label={
              <Typography variant="caption">
                Send on Enter {!sendOnEnter && '(Ctrl+Enter to send)'}
              </Typography>
            }
          />
          
          {mentions.length > 0 && (
            <Stack direction="row" spacing={0.5}>
              <MentionIcon fontSize="small" color="action" />
              <Typography variant="caption" color="text.secondary">
                {mentions.length} mention{mentions.length > 1 ? 's' : ''}
              </Typography>
            </Stack>
          )}
        </Box>
      </Box>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {/* Mentions Dropdown */}
      <Popover
        open={showMentions && filteredUsers.length > 0}
        anchorReference="anchorPosition"
        anchorPosition={mentionAnchor || { top: 0, left: 0 }}
        onClose={() => setShowMentions(false)}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'left'
        }}
        transformOrigin={{
          vertical: 'bottom',
          horizontal: 'left'
        }}
        disableAutoFocus
        disableEnforceFocus
      >
        <List sx={{ maxHeight: 200, overflow: 'auto' }}>
          {filteredUsers.map(user => (
            <ListItem
              key={user.user_id}
              button
              onClick={() => handleMentionSelect(user)}
            >
              <ListItemAvatar>
                <Avatar
                  sx={{
                    bgcolor: getUserTypeColor(user.user_type),
                    width: 32,
                    height: 32
                  }}
                >
                  {user.full_name?.[0] || user.username[0]}
                </Avatar>
              </ListItemAvatar>
              <ListItemText
                primary={user.full_name || user.username}
                secondary={`@${user.username} • ${user.user_type}`}
              />
            </ListItem>
          ))}
        </List>
      </Popover>
    </Box>
  );
};