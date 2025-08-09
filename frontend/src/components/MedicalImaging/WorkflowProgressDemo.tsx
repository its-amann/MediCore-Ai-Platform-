import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Container,
  Grid,
  Paper,
  IconButton,
  Tabs,
  Tab,
  Chip,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Refresh,
  Settings,
  Speed,
  SlowMotionVideo,
  BugReport,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import WorkflowProgress from './components/WorkflowProgress';

const DemoContainer = styled(Box)(({ theme }) => ({
  minHeight: '100vh',
  background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%)',
  padding: theme.spacing(4),
  position: 'relative',
  overflow: 'hidden',
}));

const GlassCard = styled(Paper)(({ theme }) => ({
  background: 'rgba(255, 255, 255, 0.05)',
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  borderRadius: '24px',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
  padding: theme.spacing(3),
  position: 'relative',
  overflow: 'hidden',
}));

const ControlButton = styled(Button)(({ theme }) => ({
  background: 'rgba(255, 255, 255, 0.1)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  color: 'white',
  '&:hover': {
    background: 'rgba(255, 255, 255, 0.15)',
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
}));

interface SimulationConfig {
  speed: 'slow' | 'normal' | 'fast';
  includeErrors: boolean;
  autoRestart: boolean;
}

const WorkflowProgressDemo: React.FC = () => {
  const [isSimulating, setIsSimulating] = useState(false);
  const [currentReportId, setCurrentReportId] = useState<string | null>(null);
  const [simulationConfig, setSimulationConfig] = useState<SimulationConfig>({
    speed: 'normal',
    includeErrors: false,
    autoRestart: false,
  });
  const [selectedTab, setSelectedTab] = useState(0);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  // Workflow state for WorkflowProgress component
  const [workflowState, setWorkflowState] = useState({
    currentStatus: 'waiting',
    progress: 0,
    message: 'Ready to start workflow',
    totalImages: 3,
    currentImage: 0,
  });

  // Simulate WebSocket messages
  useEffect(() => {
    if (isSimulating && currentReportId) {
      // This would normally connect to a real WebSocket
      // For demo purposes, we'll simulate the workflow progression
      simulateWorkflow();
    }
  }, [isSimulating, currentReportId]);

  const simulateWorkflow = () => {
    // Workflow simulation logic
    const stages = [
      { 
        id: 'workflow_started', 
        duration: 2000,
        status: 'workflow_started',
        progress: 5,
        message: 'Starting medical imaging analysis workflow',
      },
      { 
        id: 'image_processing', 
        duration: 8000,
        status: 'image_processing',
        progress: 20,
        message: 'Analyzing medical images for abnormalities',
        updateImages: true,
      },
      { 
        id: 'literature_search', 
        duration: 6000,
        status: 'literature_search',
        progress: 40,
        message: 'Searching medical literature and research papers',
      },
      { 
        id: 'report_generation', 
        duration: 10000,
        status: 'report_generation',
        progress: 60,
        message: 'Creating comprehensive medical report with findings',
      },
      { 
        id: 'quality_check', 
        duration: 5000,
        status: 'quality_check',
        progress: 80,
        message: 'Verifying report accuracy and completeness',
      },
      { 
        id: 'storing_results', 
        duration: 3000,
        status: 'storing_results',
        progress: 95,
        message: 'Storing report and generating embeddings',
      },
      { 
        id: 'completed', 
        duration: 1000,
        status: 'completed',
        progress: 100,
        message: 'Medical imaging analysis completed successfully',
      },
    ];

    const speedMultiplier = {
      slow: 2,
      normal: 1,
      fast: 0.5,
    }[simulationConfig.speed];

    // Simulate stage progression
    let currentStageIndex = 0;
    let imageProgress = 0;
    
    const progressStage = () => {
      if (currentStageIndex >= stages.length) {
        handleWorkflowComplete();
        return;
      }

      const stage = stages[currentStageIndex];
      const duration = stage.duration * speedMultiplier;

      // Update workflow state
      setWorkflowState({
        currentStatus: stage.status,
        progress: stage.progress,
        message: stage.message,
        totalImages: 3,
        currentImage: stage.updateImages ? Math.min(imageProgress + 1, 3) : imageProgress,
      });
      
      if (stage.updateImages) {
        imageProgress++;
      }

      // Simulate error on report generation stage if configured
      if (simulationConfig.includeErrors && stage.id === 'report_generation' && Math.random() > 0.5) {
        setWorkflowState(prev => ({
          ...prev,
          currentStatus: 'error',
          message: 'Error during report generation: AI analysis failed',
        }));
        handleWorkflowError('AI analysis failed: Unable to generate report');
        return;
      }

      // Progress through the stage
      setTimeout(() => {
        currentStageIndex++;
        progressStage();
      }, duration);
    };

    progressStage();
  };

  const startSimulation = () => {
    const reportId = `demo-${Date.now()}`;
    setCurrentReportId(reportId);
    setIsSimulating(true);
    // Reset workflow state
    setWorkflowState({
      currentStatus: 'workflow_started',
      progress: 0,
      message: 'Starting medical imaging analysis workflow',
      totalImages: 3,
      currentImage: 0,
    });
  };

  const stopSimulation = () => {
    setIsSimulating(false);
    setCurrentReportId(null);
    // Reset workflow state
    setWorkflowState({
      currentStatus: 'waiting',
      progress: 0,
      message: 'Ready to start workflow',
      totalImages: 3,
      currentImage: 0,
    });
  };

  const handleWorkflowComplete = (report?: any) => {
    setShowSuccess(true);
    if (simulationConfig.autoRestart) {
      setTimeout(() => {
        stopSimulation();
        startSimulation();
      }, 3000);
    } else {
      stopSimulation();
    }
  };

  const handleWorkflowError = (error: string) => {
    setErrorMessage(error);
    setShowError(true);
    stopSimulation();
  };

  const renderControls = () => (
    <GlassCard elevation={0}>
      <Typography
        variant="h6"
        sx={{
          color: 'rgba(255, 255, 255, 0.9)',
          fontWeight: 600,
          mb: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <Settings />
        Demo Controls
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', gap: 2 }}>
            {!isSimulating ? (
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={startSimulation}
                sx={{
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
                  },
                }}
              >
                Start Workflow
              </Button>
            ) : (
              <Button
                variant="contained"
                startIcon={<Stop />}
                onClick={stopSimulation}
                sx={{
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)',
                  },
                }}
              >
                Stop Workflow
              </Button>
            )}
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={() => {
                stopSimulation();
                setShowSuccess(false);
                setShowError(false);
              }}
              sx={{
                borderColor: 'rgba(255, 255, 255, 0.3)',
                color: 'rgba(255, 255, 255, 0.8)',
                '&:hover': {
                  borderColor: 'rgba(255, 255, 255, 0.5)',
                  background: 'rgba(255, 255, 255, 0.05)',
                },
              }}
            >
              Reset
            </Button>
          </Box>
        </Grid>

        <Grid item xs={12} md={4}>
          <Typography
            variant="subtitle2"
            sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}
          >
            Simulation Speed
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip
              icon={<SlowMotionVideo />}
              label="Slow"
              clickable
              onClick={() => setSimulationConfig({ ...simulationConfig, speed: 'slow' })}
              sx={{
                background:
                  simulationConfig.speed === 'slow'
                    ? 'rgba(99, 102, 241, 0.3)'
                    : 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                border: `1px solid ${
                  simulationConfig.speed === 'slow'
                    ? 'rgba(99, 102, 241, 0.5)'
                    : 'rgba(255, 255, 255, 0.2)'
                }`,
              }}
            />
            <Chip
              label="Normal"
              clickable
              onClick={() => setSimulationConfig({ ...simulationConfig, speed: 'normal' })}
              sx={{
                background:
                  simulationConfig.speed === 'normal'
                    ? 'rgba(99, 102, 241, 0.3)'
                    : 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                border: `1px solid ${
                  simulationConfig.speed === 'normal'
                    ? 'rgba(99, 102, 241, 0.5)'
                    : 'rgba(255, 255, 255, 0.2)'
                }`,
              }}
            />
            <Chip
              icon={<Speed />}
              label="Fast"
              clickable
              onClick={() => setSimulationConfig({ ...simulationConfig, speed: 'fast' })}
              sx={{
                background:
                  simulationConfig.speed === 'fast'
                    ? 'rgba(99, 102, 241, 0.3)'
                    : 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                border: `1px solid ${
                  simulationConfig.speed === 'fast'
                    ? 'rgba(99, 102, 241, 0.5)'
                    : 'rgba(255, 255, 255, 0.2)'
                }`,
              }}
            />
          </Box>
        </Grid>

        <Grid item xs={12} md={4}>
          <Typography
            variant="subtitle2"
            sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}
          >
            Simulation Options
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip
              icon={<BugReport />}
              label="Include Errors"
              clickable
              onClick={() =>
                setSimulationConfig({
                  ...simulationConfig,
                  includeErrors: !simulationConfig.includeErrors,
                })
              }
              sx={{
                background: simulationConfig.includeErrors
                  ? 'rgba(239, 68, 68, 0.3)'
                  : 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                border: `1px solid ${
                  simulationConfig.includeErrors
                    ? 'rgba(239, 68, 68, 0.5)'
                    : 'rgba(255, 255, 255, 0.2)'
                }`,
              }}
            />
            <Chip
              icon={<Refresh />}
              label="Auto Restart"
              clickable
              onClick={() =>
                setSimulationConfig({
                  ...simulationConfig,
                  autoRestart: !simulationConfig.autoRestart,
                })
              }
              sx={{
                background: simulationConfig.autoRestart
                  ? 'rgba(16, 185, 129, 0.3)'
                  : 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                border: `1px solid ${
                  simulationConfig.autoRestart
                    ? 'rgba(16, 185, 129, 0.5)'
                    : 'rgba(255, 255, 255, 0.2)'
                }`,
              }}
            />
          </Box>
        </Grid>

        <Grid item xs={12} md={4}>
          <Typography
            variant="subtitle2"
            sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}
          >
            Demo Status
          </Typography>
          <Chip
            label={isSimulating ? 'Running' : 'Idle'}
            icon={isSimulating ? <PlayArrow /> : <Stop />}
            sx={{
              background: isSimulating
                ? 'rgba(16, 185, 129, 0.3)'
                : 'rgba(255, 255, 255, 0.1)',
              color: 'white',
              border: `1px solid ${
                isSimulating ? 'rgba(16, 185, 129, 0.5)' : 'rgba(255, 255, 255, 0.2)'
              }`,
            }}
          />
        </Grid>
      </Grid>
    </GlassCard>
  );

  const renderInfo = () => (
    <GlassCard elevation={0}>
      <Tabs
        value={selectedTab}
        onChange={(_e: any, v: number) => setSelectedTab(v)}
        sx={{
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          mb: 3,
          '& .MuiTab-root': {
            color: 'rgba(255, 255, 255, 0.6)',
            '&.Mui-selected': {
              color: '#6366f1',
            },
          },
          '& .MuiTabs-indicator': {
            backgroundColor: '#6366f1',
          },
        }}
      >
        <Tab label="Overview" />
        <Tab label="Features" />
        <Tab label="Integration" />
      </Tabs>

      {selectedTab === 0 && (
        <Box>
          <Typography variant="h6" sx={{ color: 'rgba(255, 255, 255, 0.9)', mb: 2 }}>
            Medical Imaging Workflow Progress
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 2 }}>
            This demo showcases a real-time workflow progress visualization for medical imaging
            analysis. The system provides live updates through WebSocket connections, showing each
            stage of the AI-powered analysis pipeline.
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>
            Use the controls above to start a simulation and see how the workflow progresses through
            different stages, from image upload to final report compilation.
          </Typography>
        </Box>
      )}

      {selectedTab === 1 && (
        <Box>
          <Typography variant="h6" sx={{ color: 'rgba(255, 255, 255, 0.9)', mb: 2 }}>
            Key Features
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {[
              'Real-time WebSocket status updates',
              'Live progress tracking for each stage',
              'Multi-agent AI visualization',
              'Time estimates and elapsed time tracking',
              'Detailed logs with export capability',
              'Error handling and retry options',
              'Preview of processing results',
              'Responsive design for all devices',
            ].map((feature, index) => (
              <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CheckCircle sx={{ fontSize: 16, color: '#10b981' }} />
                <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                  {feature}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {selectedTab === 2 && (
        <Box>
          <Typography variant="h6" sx={{ color: 'rgba(255, 255, 255, 0.9)', mb: 2 }}>
            Integration Guide
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 2 }}>
            To integrate this workflow progress component into your application:
          </Typography>
          <Box
            component="pre"
            sx={{
              background: 'rgba(0, 0, 0, 0.3)',
              borderRadius: 1,
              p: 2,
              overflow: 'auto',
              fontSize: '0.875rem',
              color: 'rgba(255, 255, 255, 0.8)',
            }}
          >
            {`import WorkflowProgress from './WorkflowProgress';

// In your component
<WorkflowProgress
  reportId={reportId}
  onComplete={(report) => {
    console.log('Workflow completed:', report);
  }}
  onError={(error) => {
    console.error('Workflow error:', error);
  }}
/>`}
          </Box>
        </Box>
      )}
    </GlassCard>
  );

  return (
    <DemoContainer>
      <Container maxWidth="xl">
        <Box sx={{ mb: 4 }}>
          <Typography
            variant="h3"
            sx={{
              color: 'white',
              fontWeight: 700,
              mb: 2,
              textAlign: 'center',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Workflow Progress Demo
          </Typography>
          <Typography
            variant="h6"
            sx={{
              color: 'rgba(255, 255, 255, 0.7)',
              textAlign: 'center',
              mb: 4,
            }}
          >
            Experience real-time medical imaging analysis workflow visualization
          </Typography>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <GlassCard elevation={0} sx={{ minHeight: 600 }}>
              {currentReportId ? (
                <WorkflowProgress
                  currentStatus={workflowState.currentStatus}
                  progress={workflowState.progress}
                  message={workflowState.message}
                  totalImages={workflowState.totalImages}
                  currentImage={workflowState.currentImage}
                />
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: 500,
                    flexDirection: 'column',
                    gap: 2,
                  }}
                >
                  <Typography
                    variant="h6"
                    sx={{ color: 'rgba(255, 255, 255, 0.5)', textAlign: 'center' }}
                  >
                    Click "Start Workflow" to begin the demo
                  </Typography>
                  <PlayArrow sx={{ fontSize: 60, color: 'rgba(255, 255, 255, 0.3)' }} />
                </Box>
              )}
            </GlassCard>
          </Grid>
          <Grid item xs={12} lg={4}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {renderControls()}
              {renderInfo()}
            </Box>
          </Grid>
        </Grid>
      </Container>

      {/* Success Notification */}
      <Snackbar
        open={showSuccess}
        autoHideDuration={6000}
        onClose={() => setShowSuccess(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setShowSuccess(false)}
          severity="success"
          sx={{ width: '100%' }}
          icon={<CheckCircle />}
        >
          Workflow completed successfully! Report is ready for download.
        </Alert>
      </Snackbar>

      {/* Error Notification */}
      <Snackbar
        open={showError}
        autoHideDuration={6000}
        onClose={() => setShowError(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setShowError(false)}
          severity="error"
          sx={{ width: '100%' }}
          icon={<Error />}
        >
          {errorMessage || 'An error occurred during workflow processing'}
        </Alert>
      </Snackbar>
    </DemoContainer>
  );
};

export default WorkflowProgressDemo;