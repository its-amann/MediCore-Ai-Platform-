import React, { useState, useEffect, useRef, useCallback, ChangeEvent, KeyboardEvent } from 'react';
import { buildMedicalChatWebSocketUrl } from '../../../utils/websocketUtils';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  Avatar,
  Chip,
  Button,
  CircularProgress,
  Divider,
  Tooltip,
  Fade,
  Grow,
  Alert,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Send as SendIcon,
  Clear as ClearIcon,
  Refresh as RefreshIcon,
  Person as PersonIcon,
  SmartToy as SmartToyIcon,
  AttachFile as AttachFileIcon,
  Image as ImageIcon,
  Description as DescriptionIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { ChatMessage, ChatSession, MedicalReport } from '../types';
import { format } from 'date-fns';

interface ReportChatProps {
  report: MedicalReport;
  position?: 'right' | 'bottom';
  onClose?: () => void;
  wsUrl?: string;
}

const ReportChat: React.FC<ReportChatProps> = ({
  report,
  position = 'right',
  onClose,
  wsUrl = buildMedicalChatWebSocketUrl(),
}) => {
  const theme = useTheme();
  const [session, setSession] = useState<ChatSession>({
    id: `session-${Date.now()}`,
    reportId: report.id || 'unknown',
    messages: [],
    createdAt: new Date(),
    lastMessageAt: new Date(),
  });
  const [inputMessage, setInputMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket connection management
  const connectWebSocket = useCallback(() => {
    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        
        // Send initial context
        wsRef.current?.send(JSON.stringify({
          type: 'init',
          reportId: report.id || 'unknown',
          context: {
            patientId: report.patientId || 'N/A',
            studyType: report.studyType || 'N/A',
            findingsCount: report.findings?.length || 0,
            summary: report.summary ? report.summary.substring(0, 200) + '...' : 'No summary available',
          },
        }));

        // Add system message
        addMessage({
          id: `msg-${Date.now()}`,
          role: 'system',
          content: `Connected to medical AI assistant. I have access to the ${report.studyType || 'medical'} report for patient ${report.patientName || 'the patient'}. How can I help you understand the findings?`,
          timestamp: new Date(),
        });
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'message':
            addMessage({
              id: data.id || `msg-${Date.now()}`,
              role: 'assistant',
              content: data.content,
              timestamp: new Date(data.timestamp || Date.now()),
              reportContext: data.reportContext,
            });
            setIsTyping(false);
            break;
            
          case 'typing':
            setIsTyping(true);
            if (typingTimeoutRef.current) {
              clearTimeout(typingTimeoutRef.current);
            }
            typingTimeoutRef.current = setTimeout(() => {
              setIsTyping(false);
            }, 3000);
            break;
            
          case 'error':
            setError(data.message);
            setIsTyping(false);
            break;
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error. Please try again.');
        setIsConnected(false);
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        
        // Attempt to reconnect after 3 seconds
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connectWebSocket();
          }, 3000);
        }
      };
    } catch (error) {
      console.error('Failed to connect:', error);
      setError('Failed to connect to chat service.');
      setIsConnected(false);
    }
  }, [wsUrl, report]);

  // Initialize WebSocket connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [connectWebSocket]);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session.messages]);

  const addMessage = (message: ChatMessage) => {
    setSession((prev) => ({
      ...prev,
      messages: [...prev.messages, message],
      lastMessageAt: new Date(),
    }));
  };

  const sendMessage = () => {
    if (!inputMessage.trim() || !isConnected) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
      reportContext: {
        reportId: report.id || 'unknown',
      },
    };

    addMessage(userMessage);
    
    // Send to WebSocket
    wsRef.current?.send(JSON.stringify({
      type: 'message',
      content: inputMessage,
      reportContext: {
        reportId: report.id || 'unknown',
        findingIds: report.findings?.map(f => f.id) || [],
        imageIds: report.images?.map(img => img.id) || [],
      },
    }));

    setInputMessage('');
  };

  const clearConversation = () => {
    setSession((prev) => ({
      ...prev,
      messages: [],
      lastMessageAt: new Date(),
    }));
    
    // Notify server
    wsRef.current?.send(JSON.stringify({
      type: 'clear',
      sessionId: session.id,
    }));

    // Add system message
    addMessage({
      id: `msg-${Date.now()}`,
      role: 'system',
      content: 'Conversation cleared. How can I help you with this medical report?',
      timestamp: new Date(),
    });
  };

  const newConversation = () => {
    const newSessionId = `session-${Date.now()}`;
    setSession({
      id: newSessionId,
      reportId: report.id || 'unknown',
      messages: [],
      createdAt: new Date(),
      lastMessageAt: new Date(),
    });

    // Notify server
    wsRef.current?.send(JSON.stringify({
      type: 'new_session',
      sessionId: newSessionId,
      reportId: report.id || 'unknown',
    }));

    // Add welcome message
    addMessage({
      id: `msg-${Date.now()}`,
      role: 'system',
      content: `New conversation started. I'm here to help you understand the ${report.studyType || 'medical'} report.`,
      timestamp: new Date(),
    });
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';

    return (
      <Grow in key={message.id}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            mb: 2,
          }}
        >
          <Box
            sx={{
              display: 'flex',
              gap: 1,
              maxWidth: '80%',
              flexDirection: isUser ? 'row-reverse' : 'row',
            }}
          >
            <Avatar
              sx={{
                bgcolor: isUser
                  ? theme.palette.primary.main
                  : isSystem
                  ? theme.palette.info.main
                  : theme.palette.secondary.main,
                width: 32,
                height: 32,
              }}
            >
              {isUser ? <PersonIcon fontSize="small" /> : <SmartToyIcon fontSize="small" />}
            </Avatar>
            
            <Paper
              elevation={0}
              sx={{
                p: 2,
                backgroundColor: isUser
                  ? alpha(theme.palette.primary.main, 0.1)
                  : isSystem
                  ? alpha(theme.palette.info.main, 0.1)
                  : alpha(theme.palette.background.paper, 0.8),
                borderRadius: 2,
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              }}
            >
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {message.content}
              </Typography>
              
              {message.reportContext && (message.reportContext.findingIds || message.reportContext.imageIds) && (
                <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {message.reportContext.findingIds?.map((id) => (
                    <Chip
                      key={id}
                      label={`Finding ${id}`}
                      size="small"
                      icon={<DescriptionIcon />}
                      variant="outlined"
                      sx={{ fontSize: '0.7rem' }}
                    />
                  ))}
                  {message.reportContext.imageIds?.map((id) => (
                    <Chip
                      key={id}
                      label={`Image ${id}`}
                      size="small"
                      icon={<ImageIcon />}
                      variant="outlined"
                      sx={{ fontSize: '0.7rem' }}
                    />
                  ))}
                </Box>
              )}
              
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: 'block', mt: 0.5 }}
              >
                {format(message.timestamp, 'HH:mm')}
              </Typography>
            </Paper>
          </Box>
        </Box>
      </Grow>
    );
  };

  const chatStyles = {
    right: {
      position: 'fixed' as const,
      right: 20,
      bottom: 20,
      width: 380,
      height: isMinimized ? 60 : 600,
      maxHeight: '80vh',
      transition: 'height 0.3s ease',
    },
    bottom: {
      position: 'fixed' as const,
      bottom: 0,
      left: '50%',
      transform: 'translateX(-50%)',
      width: '90%',
      maxWidth: 800,
      height: isMinimized ? 60 : 400,
      transition: 'height 0.3s ease',
    },
  };

  return (
    <Paper
      elevation={3}
      sx={{
        ...chatStyles[position],
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: alpha(theme.palette.background.paper, 0.95),
        backdropFilter: 'blur(10px)',
        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        borderRadius: 2,
        overflow: 'hidden',
        zIndex: 1300,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          backgroundColor: alpha(theme.palette.primary.main, 0.1),
          borderBottom: !isMinimized ? `1px solid ${alpha(theme.palette.divider, 0.1)}` : 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: isMinimized ? 'pointer' : 'default',
        }}
        onClick={isMinimized ? () => setIsMinimized(false) : undefined}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SmartToyIcon color="primary" />
          <Typography variant="subtitle1" fontWeight={600}>
            Medical AI Assistant
          </Typography>
          {!isMinimized && isConnected ? (
            <Chip
              label="Connected"
              size="small"
              color="success"
              variant="outlined"
              sx={{ height: 20 }}
            />
          ) : !isMinimized ? (
            <Chip
              label="Connecting..."
              size="small"
              color="warning"
              variant="outlined"
              sx={{ height: 20 }}
            />
          ) : null}
          {isMinimized && session.messages.length > 0 && (
            <Chip
              label={session.messages.length}
              size="small"
              color="primary"
              sx={{ height: 20 }}
            />
          )}
        </Box>
        
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <Tooltip title={isMinimized ? 'Expand' : 'Minimize'}>
            <IconButton size="small" onClick={() => setIsMinimized(!isMinimized)}>
              {isMinimized ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Tooltip>
          {onClose && (
            <Tooltip title="Close">
              <IconButton size="small" onClick={onClose}>
                <CloseIcon />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>

      {!isMinimized && (
        <>
          {/* Messages Area */}
          <Box
            sx={{
              flex: 1,
              overflowY: 'auto',
              p: 2,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {error && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
            
            {session.messages.length === 0 && (
              <Box
                sx={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                }}
              >
                <Box>
                  <SmartToyIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="body1" color="text.secondary">
                    Ask me anything about this medical report
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    I can help explain findings, terms, or recommendations
                  </Typography>
                </Box>
              </Box>
            )}
            
            {session.messages.map(renderMessage)}
            
            {isTyping && (
              <Fade in>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Avatar
                    sx={{
                      bgcolor: theme.palette.secondary.main,
                      width: 32,
                      height: 32,
                    }}
                  >
                    <SmartToyIcon fontSize="small" />
                  </Avatar>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <CircularProgress size={8} />
                    <CircularProgress size={8} />
                    <CircularProgress size={8} />
                  </Box>
                </Box>
              </Fade>
            )}
            
            <div ref={messagesEndRef} />
          </Box>

          {/* Actions */}
          <Box
            sx={{
              p: 1,
              borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              display: 'flex',
              gap: 1,
              justifyContent: 'center',
            }}
          >
            <Button
              size="small"
              startIcon={<ClearIcon />}
              onClick={clearConversation}
              disabled={session.messages.length === 0}
            >
              Clear
            </Button>
            <Button
              size="small"
              startIcon={<RefreshIcon />}
              onClick={newConversation}
            >
              New Chat
            </Button>
          </Box>

          {/* Input Area */}
          <Box
            sx={{
              p: 2,
              borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              display: 'flex',
              gap: 1,
            }}
          >
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Ask about the report..."
              value={inputMessage}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setInputMessage(e.target.value)}
              onKeyPress={(e: KeyboardEvent<HTMLInputElement>) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              disabled={!isConnected}
              size="small"
              multiline
              maxRows={3}
              sx={{
                '& .MuiOutlinedInput-root': {
                  backgroundColor: alpha(theme.palette.background.default, 0.5),
                },
              }}
            />
            <IconButton
              color="primary"
              onClick={sendMessage}
              disabled={!inputMessage.trim() || !isConnected}
              sx={{
                backgroundColor: alpha(theme.palette.primary.main, 0.1),
                '&:hover': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.2),
                },
              }}
            >
              <SendIcon />
            </IconButton>
          </Box>
        </>
      )}
    </Paper>
  );
};

export default ReportChat;