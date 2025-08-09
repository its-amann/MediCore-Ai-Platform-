import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  Avatar,
  Chip,
  CircularProgress,
  // Divider,
  // List,
  // ListItem,
  // ListItemAvatar,
  // ListItemText,
  Tooltip,
  useTheme,
} from '@mui/material';
import {
  Send as SendIcon,
  SmartToy as AIIcon,
  Person as PersonIcon,
  AttachFile as AttachFileIcon,
  Image as ImageIcon,
  Description as ReportIcon,
  QuestionAnswer as QuestionIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  attachments?: {
    type: 'image' | 'report';
    name: string;
    url?: string;
    reportId?: string;
  }[];
  isLoading?: boolean;
}

interface MedicalReportChatProps {
  reportId?: string;
  caseId?: string;
  onSendMessage?: (message: string, attachments?: any[]) => Promise<string>;
  initialContext?: string;
}

export const MedicalReportChat: React.FC<MedicalReportChatProps> = ({
  reportId,
  caseId,
  onSendMessage,
  initialContext,
}) => {
  const theme = useTheme();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [attachments, setAttachments] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeMessage: Message = {
        id: 'welcome',
        content: initialContext || 
          `Hello! I'm your medical AI assistant. I can help you understand medical reports, answer questions about imaging results, and provide insights about findings. 
          
How can I assist you today?`,
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);
    }
  }, [initialContext]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() && attachments.length === 0) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      sender: 'user',
      timestamp: new Date(),
      attachments: attachments.map(att => ({
        type: att.type,
        name: att.name,
        url: att.url,
        reportId: att.reportId,
      })),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    // Add loading message
    const loadingMessage: Message = {
      id: 'loading-' + Date.now(),
      content: '',
      sender: 'ai',
      timestamp: new Date(),
      isLoading: true,
    };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      let response: string;
      
      if (onSendMessage) {
        response = await onSendMessage(inputMessage, attachments);
      } else {
        // Mock response for demo
        await new Promise(resolve => setTimeout(resolve, 1500));
        response = generateMockResponse(inputMessage, reportId);
      }

      // Remove loading message and add actual response
      setMessages(prev => {
        const filtered = prev.filter(msg => !msg.isLoading);
        return [...filtered, {
          id: Date.now().toString(),
          content: response,
          sender: 'ai',
          timestamp: new Date(),
        }];
      });
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => {
        const filtered = prev.filter(msg => !msg.isLoading);
        return [...filtered, {
          id: Date.now().toString(),
          content: 'I apologize, but I encountered an error processing your request. Please try again.',
          sender: 'ai',
          timestamp: new Date(),
        }];
      });
    } finally {
      setIsLoading(false);
      setAttachments([]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileAttach = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const newAttachments = Array.from(files).map(file => ({
        type: file.type.startsWith('image/') ? 'image' : 'report',
        name: file.name,
        url: URL.createObjectURL(file),
        file,
      }));
      setAttachments(prev => [...prev, ...newAttachments]);
    }
  };

  const generateMockResponse = (question: string, reportId?: string): string => {
    const lowerQuestion = question.toLowerCase();
    
    if (lowerQuestion.includes('finding') || lowerQuestion.includes('what')) {
      return `Based on the medical imaging analysis, I've identified several key findings:

1. **Primary Observation**: The scan shows a well-defined area of interest in the specified region
2. **Measurements**: The identified structure measures approximately 2.3 x 1.8 cm
3. **Characteristics**: The imaging pattern suggests benign characteristics with regular borders
4. **Comparison**: When compared to previous studies, there appears to be minimal change

Would you like me to elaborate on any specific aspect of these findings?`;
    }
    
    if (lowerQuestion.includes('normal') || lowerQuestion.includes('concern')) {
      return `The findings in this report show characteristics that are generally within normal limits for this type of imaging study. However, I'd like to highlight:

- The identified structures appear to have typical morphology
- Signal intensity/density is within expected ranges
- No significant abnormalities are detected

It's important to note that clinical correlation is always recommended, and your physician will consider these findings in context with your symptoms and medical history.`;
    }
    
    if (lowerQuestion.includes('recommend') || lowerQuestion.includes('next')) {
      return `Based on the imaging findings, here are the typical recommendations:

1. **Follow-up**: A follow-up scan in 6-12 months may be recommended to monitor any changes
2. **Clinical Correlation**: Discuss these findings with your referring physician
3. **Additional Testing**: Depending on clinical symptoms, complementary tests might be considered

Please consult with your healthcare provider for personalized recommendations based on your specific case.`;
    }
    
    return `I understand you're asking about "${question}". While I can provide general information about medical imaging findings, it's important to discuss specific interpretations with your healthcare provider who has access to your complete medical history and can provide personalized guidance.

Is there a specific aspect of the report you'd like me to help clarify?`;
  };

  return (
    <Paper
      elevation={0}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: theme.palette.mode === 'dark' 
          ? 'linear-gradient(135deg, #1a1a2e 0%, #0f0f1e 100%)'
          : 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        borderRadius: 3,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          background: theme.palette.mode === 'dark'
            ? 'rgba(255, 255, 255, 0.05)'
            : 'rgba(0, 0, 0, 0.05)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            sx={{
              bgcolor: theme.palette.primary.main,
              width: 40,
              height: 40,
            }}
          >
            <QuestionIcon />
          </Avatar>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Medical Report Assistant
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.7 }}>
              Ask questions about your medical reports and imaging results
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Messages Area */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
                  mb: 1,
                }}
              >
                <Box
                  sx={{
                    maxWidth: '70%',
                    display: 'flex',
                    gap: 1,
                    flexDirection: message.sender === 'user' ? 'row-reverse' : 'row',
                  }}
                >
                  <Avatar
                    sx={{
                      width: 32,
                      height: 32,
                      bgcolor: message.sender === 'user' 
                        ? theme.palette.secondary.main 
                        : theme.palette.primary.main,
                    }}
                  >
                    {message.sender === 'user' ? <PersonIcon /> : <AIIcon />}
                  </Avatar>
                  
                  <Paper
                    elevation={1}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      background: message.sender === 'user'
                        ? theme.palette.mode === 'dark'
                          ? 'rgba(103, 126, 234, 0.2)'
                          : theme.palette.primary.light
                        : theme.palette.mode === 'dark'
                          ? 'rgba(255, 255, 255, 0.05)'
                          : 'rgba(0, 0, 0, 0.05)',
                    }}
                  >
                    {message.isLoading ? (
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <CircularProgress size={16} />
                        <Typography variant="body2" sx={{ opacity: 0.7 }}>
                          Thinking...
                        </Typography>
                      </Box>
                    ) : (
                      <>
                        {message.attachments && message.attachments.length > 0 && (
                          <Box sx={{ mb: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            {message.attachments.map((att, idx) => (
                              <Chip
                                key={idx}
                                icon={att.type === 'image' ? <ImageIcon /> : <ReportIcon />}
                                label={att.name}
                                size="small"
                                variant="outlined"
                              />
                            ))}
                          </Box>
                        )}
                        <Box sx={{ 
                          '& p': { margin: 0, marginBottom: 1 },
                          '& p:last-child': { marginBottom: 0 },
                          '& ul, & ol': { marginTop: 0.5, marginBottom: 1 },
                          '& li': { marginBottom: 0.5 },
                          '& strong': { fontWeight: 600 },
                        }}>
                          <ReactMarkdown>
                            {message.content}
                          </ReactMarkdown>
                        </Box>
                      </>
                    )}
                    <Typography
                      variant="caption"
                      sx={{
                        display: 'block',
                        mt: 1,
                        opacity: 0.5,
                        textAlign: message.sender === 'user' ? 'right' : 'left',
                      }}
                    >
                      {message.timestamp.toLocaleTimeString()}
                    </Typography>
                  </Paper>
                </Box>
              </Box>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box
        sx={{
          p: 2,
          borderTop: `1px solid ${theme.palette.divider}`,
          background: theme.palette.mode === 'dark'
            ? 'rgba(255, 255, 255, 0.05)'
            : 'rgba(0, 0, 0, 0.05)',
        }}
      >
        {attachments.length > 0 && (
          <Box sx={{ mb: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {attachments.map((att, idx) => (
              <Chip
                key={idx}
                icon={att.type === 'image' ? <ImageIcon /> : <ReportIcon />}
                label={att.name}
                onDelete={() => setAttachments(prev => prev.filter((_, i) => i !== idx))}
                size="small"
              />
            ))}
          </Box>
        )}
        
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileAttach}
            style={{ display: 'none' }}
            multiple
            accept="image/*,.pdf,.doc,.docx"
          />
          
          <Tooltip title="Attach file">
            <IconButton
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              size="small"
            >
              <AttachFileIcon />
            </IconButton>
          </Tooltip>
          
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={inputMessage}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about your medical report..."
            disabled={isLoading}
            variant="outlined"
            size="small"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />
          
          <IconButton
            color="primary"
            onClick={handleSendMessage}
            disabled={isLoading || (!inputMessage.trim() && attachments.length === 0)}
            sx={{
              bgcolor: theme.palette.primary.main,
              color: 'white',
              '&:hover': {
                bgcolor: theme.palette.primary.dark,
              },
            }}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );
};

export default MedicalReportChat;