import React, { useState, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Avatar,
  IconButton,
  Button,
  Menu,
  MenuItem,
  Chip,
  Stack,
  Tooltip,
  TextField,
  Collapse,
  Divider,
  ListItemIcon,
  ListItemText,
  Popover,
  Grid
} from '@mui/material';
import {
  MoreVert as MoreIcon,
  Reply as ReplyIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  EmojiEmotions as EmojiIcon,
  AttachFile as AttachIcon,
  Image as ImageIcon,
  Code as CodeIcon,
  Person as PersonIcon,
  FiberManualRecord as OnlineIcon,
  AccessTime as TimeIcon,
  Thread as ThreadIcon
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { ExtendedMessage, MessageReaction, UserProfile, UserType } from '../../types/collaboration';

interface EnhancedChatMessageProps {
  message: ExtendedMessage;
  currentUserId: string;
  users: UserProfile[];
  onReply: (messageId: string) => void;
  onEdit: (messageId: string, newContent: string) => void;
  onDelete: (messageId: string) => void;
  onReaction: (messageId: string, emoji: string) => void;
  onMentionClick: (userId: string) => void;
  onThreadClick: (messageId: string) => void;
  replyToMessage?: ExtendedMessage;
  showThread?: boolean;
}

const EMOJI_REACTIONS = ['👍', '❤️', '😂', '😮', '😢', '🎉', '🤔', '👏'];

export const EnhancedChatMessage: React.FC<EnhancedChatMessageProps> = ({
  message,
  currentUserId,
  users,
  onReply,
  onEdit,
  onDelete,
  onReaction,
  onMentionClick,
  onThreadClick,
  replyToMessage,
  showThread = false
}) => {
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [emojiAnchor, setEmojiAnchor] = useState<null | HTMLElement>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [showReactions, setShowReactions] = useState(false);

  const isOwnMessage = message.sender_id === currentUserId;
  const sender = users.find(u => u.user_id === message.sender_id);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleEmojiOpen = (event: React.MouseEvent<HTMLElement>) => {
    setEmojiAnchor(event.currentTarget);
  };

  const handleEmojiClose = () => {
    setEmojiAnchor(null);
  };

  const handleEdit = () => {
    setIsEditing(true);
    handleMenuClose();
  };

  const handleSaveEdit = () => {
    if (editContent.trim() && editContent !== message.content) {
      onEdit(message.id, editContent);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditContent(message.content);
    setIsEditing(false);
  };

  const handleDelete = () => {
    onDelete(message.id);
    handleMenuClose();
  };

  const handleReaction = (emoji: string) => {
    onReaction(message.id, emoji);
    handleEmojiClose();
  };

  const getUserTypeColor = (userType?: UserType) => {
    const colors: Record<UserType, string> = {
      [UserType.DOCTOR]: '#1976d2',
      [UserType.TEACHER]: '#9c27b0',
      [UserType.STUDENT]: '#4caf50',
      [UserType.PATIENT]: '#ff9800',
      [UserType.ADMIN]: '#f44336'
    };
    return userType ? colors[userType] : '#757575';
  };

  const renderContent = () => {
    if (message.is_deleted) {
      return (
        <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
          Message deleted
        </Typography>
      );
    }

    if (isEditing) {
      return (
        <Box>
          <TextField
            fullWidth
            multiline
            size="small"
            value={editContent}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditContent(e.target.value)}
            onKeyPress={(e: React.KeyboardEvent) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSaveEdit();
              }
            }}
            autoFocus
          />
          <Stack direction="row" spacing={1} mt={1}>
            <Button size="small" onClick={handleSaveEdit}>Save</Button>
            <Button size="small" onClick={handleCancelEdit}>Cancel</Button>
          </Stack>
        </Box>
      );
    }

    // Parse and render mentions
    const contentWithMentions = message.content.replace(
      /@(\w+)/g,
      (match, username) => {
        const mentionedUser = users.find(u => u.username === username);
        if (mentionedUser) {
          return `<span class="mention" data-user-id="${mentionedUser.user_id}">@${username}</span>`;
        }
        return match;
      }
    );

    return (
      <Box>
        {replyToMessage && (
          <Paper
            sx={{
              p: 1,
              mb: 1,
              bgcolor: 'action.hover',
              borderLeft: 3,
              borderColor: 'primary.main',
              cursor: 'pointer'
            }}
            onClick={() => onThreadClick(replyToMessage.id)}
          >
            <Typography variant="caption" color="text.secondary">
              Replying to {replyToMessage.sender_name}
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
              {replyToMessage.content.substring(0, 100)}
              {replyToMessage.content.length > 100 && '...'}
            </Typography>
          </Paper>
        )}

        <Typography
          variant="body2"
          dangerouslySetInnerHTML={{ __html: contentWithMentions }}
          onClick={(e: React.MouseEvent) => {
            const target = e.target as HTMLElement;
            if (target.classList.contains('mention')) {
              const userId = target.getAttribute('data-user-id');
              if (userId) onMentionClick(userId);
            }
          }}
          sx={{
            '& .mention': {
              color: 'primary.main',
              cursor: 'pointer',
              fontWeight: 500,
              '&:hover': {
                textDecoration: 'underline'
              }
            }
          }}
        />

        {message.attachments.length > 0 && (
          <Stack spacing={1} mt={1}>
            {message.attachments.map(attachment => (
              <Chip
                key={attachment.id}
                icon={attachment.file_type.startsWith('image/') ? <ImageIcon /> : <AttachIcon />}
                label={attachment.filename}
                size="small"
                onClick={() => window.open(attachment.url, '_blank')}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Stack>
        )}
      </Box>
    );
  };

  const renderReactions = () => {
    if (message.reactions.length === 0 && !showReactions) return null;

    return (
      <Box mt={1}>
        <Stack direction="row" spacing={0.5} flexWrap="wrap">
          {message.reactions.map((reaction, idx) => {
            const hasReacted = reaction.users.includes(currentUserId);
            return (
              <Chip
                key={idx}
                label={`${reaction.emoji} ${reaction.count}`}
                size="small"
                onClick={() => onReaction(message.id, reaction.emoji)}
                sx={{
                  cursor: 'pointer',
                  bgcolor: hasReacted ? 'primary.light' : 'action.hover',
                  color: hasReacted ? 'primary.contrastText' : 'text.primary',
                  '&:hover': {
                    bgcolor: hasReacted ? 'primary.main' : 'action.selected'
                  }
                }}
              />
            );
          })}
          
          <Tooltip title="Add reaction">
            <IconButton size="small" onClick={handleEmojiOpen}>
              <EmojiIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>
    );
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: isOwnMessage ? 'row-reverse' : 'row',
        mb: 2,
        px: 2,
        '&:hover': {
          '& .message-actions': {
            opacity: 1
          }
        }
      }}
    >
      <Avatar
        sx={{
          bgcolor: getUserTypeColor(sender?.user_type),
          width: 36,
          height: 36,
          mx: 1
        }}
      >
        {sender?.full_name?.[0] || <PersonIcon />}
      </Avatar>

      <Box sx={{ maxWidth: '70%' }}>
        <Stack
          direction={isOwnMessage ? 'row-reverse' : 'row'}
          spacing={1}
          alignItems="flex-start"
        >
          <Paper
            sx={{
              p: 1.5,
              bgcolor: isOwnMessage ? 'primary.light' : 'grey.100',
              color: isOwnMessage ? 'primary.contrastText' : 'text.primary',
              borderRadius: 2,
              borderTopLeftRadius: isOwnMessage ? 16 : 4,
              borderTopRightRadius: isOwnMessage ? 4 : 16
            }}
          >
            <Stack spacing={0.5}>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="subtitle2">
                  {sender?.full_name || message.sender_name}
                </Typography>
                {sender && (
                  <Chip
                    size="small"
                    label={sender.user_type}
                    sx={{
                      height: 16,
                      fontSize: '0.65rem',
                      bgcolor: getUserTypeColor(sender.user_type),
                      color: 'white'
                    }}
                  />
                )}
                <Typography variant="caption" color="text.secondary">
                  {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
                </Typography>
                {message.edited_at && (
                  <Typography variant="caption" sx={{ fontStyle: 'italic' }}>
                    (edited)
                  </Typography>
                )}
              </Box>

              {renderContent()}
              
              {message.thread_count && message.thread_count > 0 && (
                <Button
                  size="small"
                  startIcon={<ThreadIcon />}
                  onClick={() => onThreadClick(message.id)}
                  sx={{ mt: 1 }}
                >
                  {message.thread_count} {message.thread_count === 1 ? 'reply' : 'replies'}
                </Button>
              )}
            </Stack>
          </Paper>

          <Stack
            className="message-actions"
            direction="row"
            spacing={0.5}
            sx={{
              opacity: 0,
              transition: 'opacity 0.2s'
            }}
          >
            <Tooltip title="Reply">
              <IconButton size="small" onClick={() => onReply(message.id)}>
                <ReplyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="More">
              <IconButton size="small" onClick={handleMenuOpen}>
                <MoreIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>

        {renderReactions()}
      </Box>

      {/* Action Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => { onReply(message.id); handleMenuClose(); }}>
          <ListItemIcon>
            <ReplyIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Reply</ListItemText>
        </MenuItem>
        
        {isOwnMessage && !message.is_deleted && (
          <MenuItem onClick={handleEdit}>
            <ListItemIcon>
              <EditIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Edit</ListItemText>
          </MenuItem>
        )}
        
        {(isOwnMessage || sender?.user_type === UserType.ADMIN) && (
          <MenuItem onClick={handleDelete}>
            <ListItemIcon>
              <DeleteIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Delete</ListItemText>
          </MenuItem>
        )}
      </Menu>

      {/* Emoji Picker */}
      <Popover
        open={Boolean(emojiAnchor)}
        anchorEl={emojiAnchor}
        onClose={handleEmojiClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center'
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'center'
        }}
      >
        <Box p={1}>
          <Grid container spacing={0.5} sx={{ width: 200 }}>
            {EMOJI_REACTIONS.map(emoji => (
              <Grid item key={emoji}>
                <IconButton
                  size="small"
                  onClick={() => handleReaction(emoji)}
                  sx={{ fontSize: '1.5rem' }}
                >
                  {emoji}
                </IconButton>
              </Grid>
            ))}
          </Grid>
        </Box>
      </Popover>

    </Box>
  );
};