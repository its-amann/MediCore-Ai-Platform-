import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Button,
  TextField,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Chip,
  Divider,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Stack,
  Tooltip,
  Collapse,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  LinearProgress
} from '@mui/material';
import {
  SmartToy as AIIcon,
  Send as SendIcon,
  Mic as MicIcon,
  MicOff as MicOffIcon,
  ScreenShare as ScreenIcon,
  School as TeachingIcon,
  MedicalServices as MedicalIcon,
  Forum as DiscussionIcon,
  Psychology as AnalysisIcon,
  Close as CloseIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  ContentCopy as CopyIcon,
  BookmarkBorder as BookmarkIcon,
  VolumeUp as SpeakIcon
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import {
  GeminiLiveMode,
  GeminiLiveSession,
  AIResponse,
  UserType
} from '../../types/collaboration';

interface AIAssistantPanelProps {
  roomId: string;
  roomType: 'teaching' | 'case_discussion';
  session?: GeminiLiveSession;
  userType: UserType;
  onStartSession: (mode: GeminiLiveMode) => Promise<void>;
  onEndSession: () => Promise<void>;
  onSendMessage: (message: string, mode: GeminiLiveMode) => Promise<AIResponse>;
  onToggleVoice?: (enabled: boolean) => void;
  isLoading?: boolean;
}

interface AIMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  mode: GeminiLiveMode;
  timestamp: Date;
  metadata?: {
    confidence?: number;
    references?: string[];
    suggestions?: string[];
  };
}

export const AIAssistantPanel: React.FC<AIAssistantPanelProps> = ({
  roomId,
  roomType,
  session,
  userType,
  onStartSession,
  onEndSession,
  onSendMessage,
  onToggleVoice,
  isLoading = false
}) => {
  const [selectedMode, setSelectedMode] = useState<GeminiLiveMode>(
    roomType === 'teaching' 
      ? GeminiLiveMode.TEACHING_ASSISTANT 
      : GeminiLiveMode.CASE_DISCUSSION
  );
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getModeInfo = (mode: GeminiLiveMode) => {
    const modeInfoMap = {
      [GeminiLiveMode.VOICE_CONVERSATION]: {
        icon: <MicIcon />,
        label: 'Voice Chat',
        description: 'Real-time voice conversation',
        color: '#4caf50'
      },
      [GeminiLiveMode.SCREEN_UNDERSTANDING]: {
        icon: <ScreenIcon />,
        label: 'Screen Analysis',
        description: 'Understand shared screen content',
        color: '#2196f3'
      },
      [GeminiLiveMode.MEDICAL_ANALYSIS]: {
        icon: <MedicalIcon />,
        label: 'Medical Analysis',
        description: 'Analyze medical data and cases',
        color: '#f44336'
      },
      [GeminiLiveMode.TEACHING_ASSISTANT]: {
        icon: <TeachingIcon />,
        label: 'Teaching Assistant',
        description: 'Help with medical education',
        color: '#9c27b0'
      },
      [GeminiLiveMode.CASE_DISCUSSION]: {
        icon: <DiscussionIcon />,
        label: 'Case Discussion',
        description: 'Participate in case analysis',
        color: '#ff9800'
      }
    };

    return modeInfoMap[mode];
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isSending) return;

    const userMessage: AIMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      mode: selectedMode,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsSending(true);

    try {
      const response = await onSendMessage(inputMessage, selectedMode);
      
      const aiMessage: AIMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        mode: selectedMode,
        timestamp: new Date(),
        metadata: response.metadata
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error: any) {
      toast.error(error.message || 'Failed to get AI response');
    } finally {
      setIsSending(false);
    }
  };

  const handleStartSession = async () => {
    try {
      await onStartSession(selectedMode);
      toast.success(`Started ${getModeInfo(selectedMode).label} session`);
    } catch (error: any) {
      toast.error(error.message || 'Failed to start AI session');
    }
  };

  const handleEndSession = async () => {
    try {
      await onEndSession();
      toast.success('AI session ended');
    } catch (error: any) {
      toast.error(error.message || 'Failed to end AI session');
    }
  };

  const toggleVoice = () => {
    const newState = !isVoiceEnabled;
    setIsVoiceEnabled(newState);
    if (onToggleVoice) {
      onToggleVoice(newState);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const speakText = (text: string) => {
    const utterance = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(utterance);
  };

  const renderMessage = (message: AIMessage) => {
    const isUser = message.role === 'user';
    const modeInfo = getModeInfo(message.mode);

    return (
      <ListItem key={message.id} sx={{ alignItems: 'flex-start', px: 1 }}>
        <ListItemAvatar>
          <Avatar
            sx={{
              bgcolor: isUser ? '#1976d2' : modeInfo.color,
              width: 32,
              height: 32
            }}
          >
            {isUser ? userType[0].toUpperCase() : <AIIcon />}
          </Avatar>
        </ListItemAvatar>
        <ListItemText
          primary={
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="subtitle2">
                {isUser ? 'You' : 'AI Assistant'}
              </Typography>
              <Chip
                size="small"
                label={modeInfo.label}
                sx={{
                  height: 20,
                  fontSize: '0.7rem',
                  bgcolor: `${modeInfo.color}20`,
                  color: modeInfo.color
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {message.timestamp.toLocaleTimeString()}
              </Typography>
            </Box>
          }
          secondary={
            <Box mt={1}>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {message.content}
              </Typography>
              
              {message.metadata && (
                <Box mt={2}>
                  {message.metadata.confidence && (
                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                      <Typography variant="caption" color="text.secondary">
                        Confidence:
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={message.metadata.confidence * 100}
                        sx={{ width: 100, height: 6, borderRadius: 3 }}
                      />
                      <Typography variant="caption">
                        {Math.round(message.metadata.confidence * 100)}%
                      </Typography>
                    </Box>
                  )}
                  
                  {message.metadata.suggestions && message.metadata.suggestions.length > 0 && (
                    <Box mb={1}>
                      <Typography variant="caption" color="text.secondary">
                        Suggestions:
                      </Typography>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" mt={0.5}>
                        {message.metadata.suggestions.map((suggestion, idx) => (
                          <Chip
                            key={idx}
                            label={suggestion}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}
                  
                  {message.metadata.references && message.metadata.references.length > 0 && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        References:
                      </Typography>
                      {message.metadata.references.map((ref, idx) => (
                        <Typography key={idx} variant="caption" display="block">
                          [{idx + 1}] {ref}
                        </Typography>
                      ))}
                    </Box>
                  )}
                </Box>
              )}
              
              {!isUser && (
                <Stack direction="row" spacing={1} mt={1}>
                  <IconButton
                    size="small"
                    onClick={() => copyToClipboard(message.content)}
                  >
                    <CopyIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => speakText(message.content)}
                  >
                    <SpeakIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small">
                    <BookmarkIcon fontSize="small" />
                  </IconButton>
                </Stack>
              )}
            </Box>
          }
        />
      </ListItem>
    );
  };

  return (
    <Paper
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s ease'
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <AIIcon color="primary" />
          <Typography variant="h6">AI Assistant</Typography>
          {session && (
            <Chip
              size="small"
              label="Active"
              color="success"
              sx={{ animation: 'pulse 2s infinite' }}
            />
          )}
        </Box>
        <IconButton onClick={() => setIsExpanded(!isExpanded)}>
          {isExpanded ? <CollapseIcon /> : <ExpandIcon />}
        </IconButton>
      </Box>

      <Collapse in={isExpanded}>
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Mode Selection */}
          {!session && (
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <FormControl fullWidth size="small">
                <InputLabel>AI Mode</InputLabel>
                <Select
                  value={selectedMode}
                  onChange={(e: React.ChangeEvent<{ value: unknown }>) => setSelectedMode(e.target.value as GeminiLiveMode)}
                  label="AI Mode"
                >
                  {Object.values(GeminiLiveMode).map(mode => {
                    const info = getModeInfo(mode);
                    return (
                      <MenuItem key={mode} value={mode}>
                        <Box display="flex" alignItems="center" gap={1}>
                          {info.icon}
                          <Box>
                            <Typography variant="body2">{info.label}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {info.description}
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                    );
                  })}
                </Select>
              </FormControl>
              
              <Button
                fullWidth
                variant="contained"
                startIcon={<AIIcon />}
                onClick={handleStartSession}
                disabled={isLoading}
                sx={{ mt: 2 }}
              >
                Start AI Session
              </Button>
            </Box>
          )}

          {/* Active Session Info */}
          {session && (
            <Alert
              severity="info"
              action={
                <Button size="small" color="inherit" onClick={handleEndSession}>
                  End Session
                </Button>
              }
              sx={{ mx: 2, mt: 2 }}
            >
              {getModeInfo(session.mode).label} session active
            </Alert>
          )}

          {/* Messages */}
          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
            {messages.length === 0 ? (
              <Box textAlign="center" py={4}>
                <AIIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Start a conversation with the AI assistant
                </Typography>
              </Box>
            ) : (
              <List>
                {messages.map(renderMessage)}
                <div ref={messagesEndRef} />
              </List>
            )}
          </Box>

          {/* Input Area */}
          {session && (
            <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
              <Box display="flex" gap={1}>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Ask AI assistant..."
                  value={inputMessage}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputMessage(e.target.value)}
                  onKeyPress={(e: React.KeyboardEvent) => e.key === 'Enter' && handleSendMessage()}
                  disabled={isSending}
                  InputProps={{
                    endAdornment: (
                      <>
                        {selectedMode === GeminiLiveMode.VOICE_CONVERSATION && (
                          <IconButton onClick={toggleVoice} size="small">
                            {isVoiceEnabled ? <MicIcon /> : <MicOffIcon />}
                          </IconButton>
                        )}
                        <IconButton
                          onClick={handleSendMessage}
                          disabled={!inputMessage.trim() || isSending}
                          size="small"
                        >
                          {isSending ? <CircularProgress size={20} /> : <SendIcon />}
                        </IconButton>
                      </>
                    )
                  }}
                />
              </Box>
            </Box>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};