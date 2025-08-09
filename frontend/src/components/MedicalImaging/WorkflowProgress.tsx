import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Collapse,
  Button,
  Alert,
  CircularProgress,
  Fade,
  Paper,
  Tooltip,
  Stack,
  useTheme,
  alpha,
} from '@mui/material';
import { useAuthStore } from '../../store/authStore';
import api from '../../services/api';
import medicalImagingApi from '../../services/medicalImagingApi';
import {
  CheckCircle,
  RadioButtonUnchecked,
  Error,
  ExpandMore,
  ExpandLess,
  Refresh,
  CloudUpload,
  Assessment,
  Psychology,
  Groups,
  Storage,
  Description,
  WifiTethering,
  WifiTetheringOff,
  Download,
  Share,
  AccessTime,
  Speed,
} from '@mui/icons-material';
import { styled, keyframes } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';

// Types
interface WorkflowStage {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  progress: number;
  startTime?: number;
  endTime?: number;
  error?: string;
  details?: any;
  icon: React.ReactNode;
}

interface AIAgent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'working' | 'completed';
  currentTask?: string;
}

interface WorkflowProgressProps {
  caseId: string;
  onComplete?: (result: any) => void;
  onError?: (error: any) => void;
}

interface WebSocketMessage {
  type: 'status' | 'progress' | 'complete' | 'error' | 'agent_update' | 'log';
  stage?: string;
  progress?: number;
  data?: any;
  error?: string;
  agent?: string;
  message?: string;
  timestamp?: number;
}

// Styled Components
const pulse = keyframes`
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
  100% { opacity: 1; transform: scale(1); }
`;

const rotate = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

const GlassCard = styled(Paper)(({ theme }) => ({
  background: alpha(theme.palette.background.paper, 0.8),
  backdropFilter: 'blur(20px)',
  borderRadius: theme.spacing(2),
  border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  padding: theme.spacing(3),
  transition: 'all 0.3s ease',
  '&:hover': {
    boxShadow: theme.shadows[8],
  },
}));

const StageCard = styled(Box)<{ active?: boolean; completed?: boolean; error?: boolean }>(
  ({ theme, active, completed, error }) => ({
    background: alpha(
      error
        ? theme.palette.error.main
        : completed
        ? theme.palette.success.main
        : active
        ? theme.palette.primary.main
        : theme.palette.action.hover,
      0.1
    ),
    borderRadius: theme.spacing(2),
    padding: theme.spacing(2),
    marginBottom: theme.spacing(2),
    border: `1px solid ${alpha(
      error
        ? theme.palette.error.main
        : completed
        ? theme.palette.success.main
        : active
        ? theme.palette.primary.main
        : theme.palette.divider,
      0.3
    )}`,
    transition: 'all 0.3s ease',
    animation: active ? `${pulse} 2s infinite` : 'none',
    cursor: 'pointer',
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: theme.shadows[4],
    },
  })
);

const ConnectionIndicator = styled(Box)<{ connected: boolean }>(({ theme, connected }) => ({
  width: 12,
  height: 12,
  borderRadius: '50%',
  backgroundColor: connected ? theme.palette.success.main : theme.palette.error.main,
  animation: connected ? `${pulse} 2s infinite` : 'none',
  marginRight: theme.spacing(1),
}));

const AgentChip = styled(Chip)<{ working?: boolean }>(({ theme, working }) => ({
  margin: theme.spacing(0.5),
  animation: working ? `${rotate} 2s linear infinite` : 'none',
  background: working
    ? `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`
    : 'default',
  color: working ? theme.palette.common.white : 'default',
}));

const LogContainer = styled(Box)(({ theme }) => ({
  maxHeight: 300,
  overflowY: 'auto',
  background: alpha(theme.palette.background.default, 0.5),
  borderRadius: theme.spacing(1),
  padding: theme.spacing(2),
  fontFamily: 'monospace',
  fontSize: '0.85rem',
  '&::-webkit-scrollbar': {
    width: 8,
  },
  '&::-webkit-scrollbar-track': {
    background: alpha(theme.palette.divider, 0.1),
  },
  '&::-webkit-scrollbar-thumb': {
    background: alpha(theme.palette.primary.main, 0.3),
    borderRadius: 4,
  },
}));

// Main Component
export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
  caseId,
  onComplete,
  onError,
}) => {
  const theme = useTheme();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const [wsConnected, setWsConnected] = useState(false);
  const [expandedStage, setExpandedStage] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [estimatedTime] = useState(180); // 3 minutes estimated
  const [isRefreshingToken, setIsRefreshingToken] = useState(false);
  const [workflowTimeout, setWorkflowTimeout] = useState<NodeJS.Timeout | null>(null);
  const [isPollingStatus, setIsPollingStatus] = useState(false);
  const statusPollingRef = useRef<NodeJS.Timeout | null>(null);
  const initializationTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { checkAuth } = useAuthStore();

  // Workflow stages
  const [stages, setStages] = useState<WorkflowStage[]>([
    {
      id: 'upload',
      name: 'Image Upload & Preprocessing',
      description: 'Uploading and normalizing medical images',
      status: 'pending',
      progress: 0,
      icon: <CloudUpload />,
    },
    {
      id: 'analysis',
      name: 'AI Analysis & Detection',
      description: 'Analyzing images and detecting coordinates',
      status: 'pending',
      progress: 0,
      icon: <Assessment />,
    },
    {
      id: 'annotation',
      name: 'Heatmap & Annotation Generation',
      description: 'Creating visual annotations and heatmaps',
      status: 'pending',
      progress: 0,
      icon: <Psychology />,
    },
    {
      id: 'report',
      name: 'Multi-Agent Report Generation',
      description: 'AI agents collaborating to generate comprehensive report',
      status: 'pending',
      progress: 0,
      icon: <Groups />,
    },
    {
      id: 'embedding',
      name: 'Embedding Generation & Storage',
      description: 'Creating embeddings and storing in Neo4j',
      status: 'pending',
      progress: 0,
      icon: <Storage />,
    },
    {
      id: 'finalize',
      name: 'Finalize & Compile Report',
      description: 'Compiling final report with all findings',
      status: 'pending',
      progress: 0,
      icon: <Description />,
    },
  ]);

  // AI Agents
  const [agents, setAgents] = useState<AIAgent[]>([
    { id: 'radiologist', name: 'Radiologist AI', role: 'Image Analysis', status: 'idle' },
    { id: 'researcher', name: 'Researcher AI', role: 'Literature Review', status: 'idle' },
    { id: 'clinical', name: 'Clinical Advisor AI', role: 'Clinical Context', status: 'idle' },
    { id: 'writer', name: 'Report Writer AI', role: 'Report Compilation', status: 'idle' },
    { id: 'quality', name: 'Quality Checker AI', role: 'Quality Assurance', status: 'idle' },
  ]);

  // Check workflow status via API
  const checkWorkflowStatus = async () => {
    try {
      setIsPollingStatus(true);
      const token = localStorage.getItem('access_token');
      
      if (!token || !caseId || caseId.trim() === '') {
        return;
      }
      
      // Use the caseId directly as it should already be the workflow ID from backend
      const response = await medicalImagingApi.get(`/medical-imaging/workflow/status/${caseId}`);
      
      if (response.data) {
        const { status, details } = response.data;
        addLog(`Workflow status: ${status}`);
        
        // Update UI based on status
        if (status === 'running' || status === 'active') {
          // Workflow is active, ensure we're showing progress
          if (!startTime) {
            setStartTime(Date.now());
          }
          
          // Update first stage to active if nothing is active
          const hasActiveStage = stages.some(s => s.status === 'active');
          if (!hasActiveStage) {
            updateStageStatus('upload', 'active');
          }
        } else if (status === 'completed') {
          // Workflow completed, update all stages
          stages.forEach(stage => {
            if (stage.status !== 'completed') {
              updateStageStatus(stage.id, 'completed');
            }
          });
          handleWorkflowComplete(details);
        } else if (status === 'failed' || status === 'error') {
          // Workflow failed
          const activeStage = stages.find(s => s.status === 'active');
          if (activeStage) {
            updateStageStatus(activeStage.id, 'error', null, details?.error || 'Workflow failed');
          }
          onError?.(details?.error || 'Workflow failed');
        }
      }
    } catch (error: any) {
      // Don't log 404 errors as they're expected when workflow hasn't started yet
      if (error.response?.status !== 404) {
        console.error('Error checking workflow status:', error);
        addLog(`Error checking workflow status: ${error.message}`);
      }
    } finally {
      setIsPollingStatus(false);
    }
  };

  // Start polling for workflow status
  const startStatusPolling = () => {
    // Clear any existing polling
    if (statusPollingRef.current) {
      clearInterval(statusPollingRef.current);
    }
    
    // Poll every 15 seconds (reduced from 3 seconds to minimize API calls)
    statusPollingRef.current = setInterval(() => {
      if (!wsConnected) {
        checkWorkflowStatus();
      }
    }, 15000);
    
    // Initial check
    checkWorkflowStatus();
  };

  // Token refresh helper
  const refreshAccessToken = async (): Promise<string | null> => {
    try {
      setIsRefreshingToken(true);
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (!refreshToken) {
        addLog('No refresh token found');
        return null;
      }
      
      const response = await api.post('/auth/refresh', {
        refresh_token: refreshToken
      });
      
      const { access_token } = response.data;
      localStorage.setItem('access_token', access_token);
      
      // Update auth store
      checkAuth();
      
      addLog('Token refreshed successfully');
      return access_token;
    } catch (error) {
      console.error('Failed to refresh token:', error);
      addLog('Failed to refresh token - please login again');
      return null;
    } finally {
      setIsRefreshingToken(false);
    }
  };

  // WebSocket connection
  useEffect(() => {
    // Only connect if we have a valid caseId
    if (caseId && caseId.trim() !== '') {
      // Add a small delay to ensure the backend is ready
      const timer = setTimeout(() => {
        connectWebSocket();
        
        // Start status polling as backup
        startStatusPolling();
        
        // Set initialization timeout - if no progress after 30 seconds, show warning
        initializationTimeoutRef.current = setTimeout(() => {
          const hasProgress = stages.some(s => s.status !== 'pending');
          if (!hasProgress) {
            addLog('⚠️ Workflow initialization is taking longer than expected...');
            // Try to manually trigger workflow recovery
            handleWorkflowRecovery();
          }
        }, 30000);
      }, 500);
      
      return () => {
        clearTimeout(timer);
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        if (statusPollingRef.current) {
          clearInterval(statusPollingRef.current);
        }
        if (initializationTimeoutRef.current) {
          clearTimeout(initializationTimeoutRef.current);
        }
        if (wsRef.current) {
          wsRef.current.close(1000, 'Component unmounting');
          wsRef.current = null;
        }
      };
    }
  }, [caseId]);

  const connectWebSocket = useCallback(async (forceRefresh = false) => {
    try {
      // Close any existing connection first
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      let token = localStorage.getItem('access_token');
      
      // If forced refresh or no token, try to refresh
      if (forceRefresh || !token) {
        addLog('Refreshing authentication token...');
        token = await refreshAccessToken();
        
        if (!token) {
          addLog('Authentication required - please login');
          onError?.('Authentication required');
          return;
        }
      }
      
      // Validate caseId
      if (!caseId || caseId.trim() === '') {
        addLog('Invalid case ID');
        onError?.('Invalid case ID');
        return;
      }
      
      // Don't connect with temporary UUIDs - wait for real workflow ID
      if (caseId.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i) && 
          !caseId.includes('workflow_') && !caseId.includes('report_') && !caseId.includes('case_')) {
        addLog('Waiting for valid workflow ID from server');
        return;
      }
      
      // Use secure WebSocket if on HTTPS
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = process.env.REACT_APP_WS_URL || 'localhost:8000';
      
      // Get user info from localStorage
      const userId = localStorage.getItem('user_id') || '';
      const username = localStorage.getItem('username') || '';
      
      // Connect to unified WebSocket endpoint with full authentication
      const wsUrl = `${protocol}//${host}/api/v1/ws/unified?token=${encodeURIComponent(token)}&service=medical_imaging&user_id=${encodeURIComponent(userId)}&username=${encodeURIComponent(username)}`;
      
      addLog(`Connecting to WebSocket for case: ${caseId}`);
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setWsConnected(true);
        addLog('✅ WebSocket connected successfully');
        
        // Send registration message for medical imaging updates
        const registrationMessage = {
          type: 'register_medical_imaging',
          case_id: caseId,
          user_id: userId,
          service: 'medical_imaging'
        };
        
        ws.send(JSON.stringify(registrationMessage));
        addLog(`Registered for medical imaging updates for case: ${caseId}`);
      };

      ws.onclose = (event) => {
        setWsConnected(false);
        addLog(`WebSocket disconnected: ${event.code} ${event.reason}`);
        
        // Handle different close codes
        if (event.code === 1000) {
          // Normal closure
          reconnectAttemptsRef.current = 0;
          return;
        }
        
        if (event.code === 1006 || event.code === 1001) {
          // Abnormal closure or going away - component might be unmounting
          if (wsRef.current === ws) {
            handleReconnection(false);
          }
          return;
        }
        
        if (event.code === 403 || event.reason?.includes('JWT') || event.reason?.includes('expired')) {
          // Authentication error - try refreshing token
          addLog('Authentication error detected - refreshing token...');
          if (wsRef.current === ws) {
            handleReconnection(true);
          }
          return;
        }
        
        // Other errors - try reconnecting
        if (wsRef.current === ws && reconnectAttemptsRef.current < maxReconnectAttempts) {
          handleReconnection(false);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        addLog(`❌ WebSocket error occurred`);
        setWsConnected(false);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      addLog(`Failed to connect: ${error}`);
      
      // Try reconnecting if we haven't exceeded max attempts
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        handleReconnection(false);
      }
    }
  }, [caseId, onError]);

  const handleReconnection = useCallback((needsTokenRefresh: boolean) => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    reconnectAttemptsRef.current += 1;
    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current - 1), 30000); // Exponential backoff
    
    addLog(`Reconnecting in ${delay / 1000}s (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.CLOSED || wsRef.current?.readyState === WebSocket.CLOSING) {
        connectWebSocket(needsTokenRefresh);
      }
    }, delay);
  }, [connectWebSocket]);

  const handleWebSocketMessage = (message: WebSocketMessage | any) => {
    // Clear initialization timeout on any progress
    if (initializationTimeoutRef.current && (message.type === 'status' || message.type === 'progress' || message.type === 'medical_imaging_progress')) {
      clearTimeout(initializationTimeoutRef.current);
      initializationTimeoutRef.current = null;
    }
    
    // Handle medical imaging specific messages
    if (message.type === 'medical_imaging_progress') {
      const status = message.status;
      addLog(`Medical imaging progress: ${status}`);
      
      // Map status to stages
      if (status.includes('upload') || status.includes('preprocessing')) {
        updateStageStatus('upload', 'active');
        if (message.progress !== undefined) {
          updateStageProgress('upload', message.progress);
        }
      } else if (status.includes('analysis') || status.includes('detection')) {
        updateStageStatus('upload', 'completed');
        updateStageStatus('analysis', 'active');
        if (message.progress !== undefined) {
          updateStageProgress('analysis', message.progress);
        }
      } else if (status.includes('annotation') || status.includes('heatmap')) {
        updateStageStatus('analysis', 'completed');
        updateStageStatus('annotation', 'active');
        if (message.progress !== undefined) {
          updateStageProgress('annotation', message.progress);
        }
      } else if (status.includes('report') || status.includes('agent')) {
        updateStageStatus('annotation', 'completed');
        updateStageStatus('report', 'active');
        if (message.progress !== undefined) {
          updateStageProgress('report', message.progress);
        }
      } else if (status.includes('embedding')) {
        updateStageStatus('report', 'completed');
        updateStageStatus('embedding', 'active');
        if (message.progress !== undefined) {
          updateStageProgress('embedding', message.progress);
        }
      } else if (status.includes('finalize') || status.includes('complete')) {
        updateStageStatus('embedding', 'completed');
        updateStageStatus('finalize', 'active');
        if (message.progress !== undefined) {
          updateStageProgress('finalize', message.progress);
        }
        if (message.progress === 100) {
          updateStageStatus('finalize', 'completed');
          if (message.report_id) {
            handleWorkflowComplete({ report_id: message.report_id });
          }
        }
      }
      
      if (!startTime) {
        setStartTime(Date.now());
      }
      return;
    }
    
    // Handle registration confirmation
    if (message.type === 'registration_confirmed') {
      addLog(`✅ ${message.message}`);
      return;
    }
    
    // Handle original message types
    switch (message.type) {
      case 'status':
        if (message.stage) {
          updateStageStatus(message.stage, 'active');
          if (!startTime) {
            setStartTime(Date.now());
          }
        }
        break;

      case 'progress':
        if (message.stage && message.progress !== undefined) {
          updateStageProgress(message.stage, message.progress);
        }
        break;

      case 'complete':
        if (message.stage) {
          updateStageStatus(message.stage, 'completed', message.data);
        }
        if (message.data?.final) {
          handleWorkflowComplete(message.data);
        }
        break;

      case 'error':
        if (message.stage) {
          updateStageStatus(message.stage, 'error', null, message.error);
        }
        break;

      case 'agent_update':
        if (message.agent && message.data) {
          updateAgentStatus(message.agent, message.data.status, message.data.task);
        }
        break;

      case 'log':
        if (message.message) {
          addLog(message.message);
        }
        break;
    }
  };

  const updateStageStatus = (
    stageId: string,
    status: WorkflowStage['status'],
    details?: any,
    error?: string
  ) => {
    setStages((prev) =>
      prev.map((stage) => {
        if (stage.id === stageId) {
          return {
            ...stage,
            status,
            details,
            error,
            startTime: status === 'active' ? Date.now() : stage.startTime,
            endTime: status === 'completed' || status === 'error' ? Date.now() : stage.endTime,
          };
        }
        return stage;
      })
    );
  };

  const updateStageProgress = (stageId: string, progress: number) => {
    setStages((prev) =>
      prev.map((stage) => {
        if (stage.id === stageId) {
          return { ...stage, progress };
        }
        return stage;
      })
    );
  };

  const updateAgentStatus = (agentId: string, status: AIAgent['status'], task?: string) => {
    setAgents((prev) =>
      prev.map((agent) => {
        if (agent.id === agentId) {
          return { ...agent, status, currentTask: task };
        }
        return agent;
      })
    );
  };

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${timestamp}] ${message}`]);
  };

  const handleWorkflowComplete = (result: any) => {
    addLog('Workflow completed successfully!');
    if (onComplete) {
      onComplete(result);
    }
  };

  const handleRetry = (stageId: string) => {
    // Send retry request via WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'retry',
          stage: stageId,
        })
      );
    } else {
      addLog('WebSocket not connected - attempting to reconnect...');
      connectWebSocket(true);
    }
  };

  const handleManualReconnect = () => {
    addLog('Manual reconnection requested...');
    reconnectAttemptsRef.current = 0;
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual reconnect');
    }
    connectWebSocket(true);
  };

  const handleWorkflowRecovery = async () => {
    try {
      addLog('Attempting workflow recovery...');
      const token = localStorage.getItem('access_token');
      
      if (!token || !caseId) {
        addLog('Cannot recover workflow: missing token or case ID');
        return;
      }
      
      // Try to recover or restart the workflow
      const response = await medicalImagingApi.post(`/medical-imaging/workflow/recover`, {
        case_id: caseId,
        action: 'check_or_restart'
      });
      
      if (response.data.status === 'recovered') {
        addLog('✅ Workflow recovered successfully');
        // Reset stages and start fresh
        setStages(prev => prev.map(stage => ({ ...stage, status: 'pending', progress: 0 })));
        setStartTime(Date.now());
      } else if (response.data.status === 'restarted') {
        addLog('🔄 Workflow restarted');
        setStartTime(Date.now());
      }
      
      // Reconnect WebSocket
      if (!wsConnected) {
        connectWebSocket(true);
      }
    } catch (error: any) {
      console.error('Workflow recovery failed:', error);
      addLog(`❌ Workflow recovery failed: ${error.message}`);
      
      // Show recovery options to user
      if (onError) {
        onError({
          message: 'Workflow initialization failed',
          recoverable: true,
          error
        });
      }
    }
  };

  const handleExportLogs = () => {
    const content = logs.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-logs-${caseId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getElapsedTime = () => {
    if (!startTime) return '0:00';
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getOverallProgress = () => {
    const totalProgress = stages.reduce((sum, stage) => sum + stage.progress, 0);
    return Math.round(totalProgress / stages.length);
  };

  return (
    <GlassCard elevation={0}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h5" fontWeight="bold" gutterBottom>
            Workflow Progress
          </Typography>
          <Box display="flex" alignItems="center" gap={2}>
            <Box display="flex" alignItems="center" gap={1}>
              <ConnectionIndicator connected={wsConnected} />
              <Typography variant="caption" color="text.secondary">
                {wsConnected ? 'Connected' : isRefreshingToken ? 'Refreshing token...' : 'Disconnected'}
              </Typography>
              {!wsConnected && !isRefreshingToken && (
                <Button
                  size="small"
                  variant="text"
                  onClick={handleManualReconnect}
                  sx={{ minWidth: 'auto', padding: '2px 8px', fontSize: '0.75rem' }}
                >
                  Reconnect
                </Button>
              )}
            </Box>
            <Chip
              icon={<AccessTime />}
              label={`Elapsed: ${getElapsedTime()}`}
              size="small"
              color="primary"
              variant="outlined"
            />
            <Chip
              icon={<Speed />}
              label={`Progress: ${getOverallProgress()}%`}
              size="small"
              color="success"
              variant="outlined"
            />
          </Box>
        </Box>
        <Box>
          <IconButton onClick={() => setShowLogs(!showLogs)} size="small">
            {showLogs ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
          <Tooltip title="Export Logs">
            <IconButton onClick={handleExportLogs} size="small">
              <Download />
            </IconButton>
          </Tooltip>
          <Tooltip title="Share Progress">
            <IconButton size="small">
              <Share />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Connection Status Alert */}
      {!wsConnected && reconnectAttemptsRef.current > 0 && (
        <Alert 
          severity="warning" 
          sx={{ mb: 2 }}
          action={
            <Stack direction="row" spacing={1}>
              <Button color="inherit" size="small" onClick={handleManualReconnect}>
                Retry Connection
              </Button>
              <Button color="inherit" size="small" onClick={handleWorkflowRecovery}>
                Recover Workflow
              </Button>
            </Stack>
          }
        >
          Workflow progress disconnected. {isRefreshingToken ? 'Refreshing authentication...' : `Reconnecting (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`}
        </Alert>
      )}
      
      {/* Workflow Stuck Alert */}
      {stages.every(s => s.status === 'pending') && startTime && (Date.now() - startTime > 30000) && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={handleWorkflowRecovery}>
              Restart Workflow
            </Button>
          }
        >
          Workflow appears to be stuck. The server may have restarted. Click "Restart Workflow" to try again.
        </Alert>
      )}

      {/* Overall Progress */}
      <Box mb={3}>
        <LinearProgress
          variant="determinate"
          value={getOverallProgress()}
          sx={{
            height: 8,
            borderRadius: 4,
            background: alpha(theme.palette.primary.main, 0.1),
            '& .MuiLinearProgress-bar': {
              background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
              borderRadius: 4,
            },
          }}
        />
      </Box>

      {/* Workflow Stages */}
      <AnimatePresence>
        {stages.map((stage, index) => (
          <motion.div
            key={stage.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <StageCard
              active={stage.status === 'active'}
              completed={stage.status === 'completed'}
              error={stage.status === 'error'}
              onClick={() => setExpandedStage(expandedStage === stage.id ? null : stage.id)}
            >
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box display="flex" alignItems="center" gap={2}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 40,
                      height: 40,
                      borderRadius: '50%',
                      background: alpha(
                        stage.status === 'error'
                          ? theme.palette.error.main
                          : stage.status === 'completed'
                          ? theme.palette.success.main
                          : stage.status === 'active'
                          ? theme.palette.primary.main
                          : theme.palette.action.hover,
                        0.2
                      ),
                    }}
                  >
                    {stage.status === 'completed' ? (
                      <CheckCircle color="success" />
                    ) : stage.status === 'error' ? (
                      <Error color="error" />
                    ) : stage.status === 'active' ? (
                      <CircularProgress size={24} />
                    ) : (
                      <RadioButtonUnchecked />
                    )}
                  </Box>
                  <Box flex={1}>
                    <Typography variant="subtitle1" fontWeight="medium">
                      {stage.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {stage.description}
                    </Typography>
                  </Box>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  {stage.status === 'active' && (
                    <Typography variant="body2" color="primary">
                      {stage.progress}%
                    </Typography>
                  )}
                  {stage.status === 'error' && (
                    <IconButton size="small" onClick={() => handleRetry(stage.id)}>
                      <Refresh />
                    </IconButton>
                  )}
                  <IconButton size="small">
                    {expandedStage === stage.id ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                </Box>
              </Box>

              {stage.status === 'active' && (
                <Box mt={2}>
                  <LinearProgress
                    variant="determinate"
                    value={stage.progress}
                    sx={{
                      height: 4,
                      borderRadius: 2,
                      background: alpha(theme.palette.primary.main, 0.1),
                    }}
                  />
                </Box>
              )}

              <Collapse in={expandedStage === stage.id}>
                <Box mt={2} pl={7}>
                  {stage.error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      {stage.error}
                    </Alert>
                  )}
                  {stage.details && (
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        {JSON.stringify(stage.details, null, 2)}
                      </Typography>
                    </Box>
                  )}
                  {stage.startTime && (
                    <Typography variant="caption" color="text.secondary">
                      Duration:{' '}
                      {stage.endTime
                        ? `${Math.round((stage.endTime - stage.startTime) / 1000)}s`
                        : 'In progress...'}
                    </Typography>
                  )}
                </Box>
              </Collapse>
            </StageCard>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* AI Agents Section */}
      <Box mt={4}>
        <Typography variant="h6" gutterBottom>
          AI Agents
        </Typography>
        <Box display="flex" flexWrap="wrap" gap={1}>
          {agents.map((agent) => (
            <AgentChip
              key={agent.id}
              label={
                <Box>
                  <Typography variant="caption" fontWeight="bold">
                    {agent.name}
                  </Typography>
                  {agent.currentTask && (
                    <Typography variant="caption" display="block">
                      {agent.currentTask}
                    </Typography>
                  )}
                </Box>
              }
              working={agent.status === 'working'}
              color={agent.status === 'completed' ? 'success' : 'default'}
              variant={agent.status === 'working' ? 'filled' : 'outlined'}
            />
          ))}
        </Box>
      </Box>

      {/* Logs Section */}
      <Collapse in={showLogs}>
        <Box mt={3}>
          <Typography variant="subtitle2" gutterBottom>
            Workflow Logs
          </Typography>
          <LogContainer>
            {logs.map((log, index) => (
              <Box key={index} mb={0.5}>
                {log}
              </Box>
            ))}
          </LogContainer>
        </Box>
      </Collapse>
    </GlassCard>
  );
};

export default WorkflowProgress;