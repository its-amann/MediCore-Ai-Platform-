import React from 'react';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Typography,
  LinearProgress,
  Paper,
  Chip,
  styled,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Scanner as ScanIcon,
  Search as SearchIcon,
  Description as ReportIcon,
  CheckCircle as CheckIcon,
  Assessment as QualityIcon,
  Save as SaveIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { alpha, Theme } from '@mui/material/styles';

interface WorkflowStep {
  label: string;
  description: string;
  icon: React.ReactNode;
  status: 'waiting' | 'active' | 'completed' | 'error';
  progress?: number;
}

interface WorkflowProgressProps {
  currentStatus: string;
  progress: number;
  message?: string;
  totalImages?: number;
  currentImage?: number;
}

const StyledPaper = styled(Paper)(({ theme }: { theme: Theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  background: alpha(theme.palette.background.paper, 0.9),
  backdropFilter: 'blur(10px)',
  border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
}));

const ProgressChip = styled(Chip)(({ theme }: { theme: Theme }) => ({
  fontWeight: 600,
  backgroundColor: alpha(theme.palette.primary.main, 0.1),
  color: theme.palette.primary.main,
}));

const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
  currentStatus,
  progress,
  message,
  totalImages,
  currentImage,
}) => {
  const getStepFromStatus = (status: string): number => {
    const statusMap: { [key: string]: number } = {
      'upload_started': 0,
      'workflow_started': 0,
      'image_processing': 1,
      'literature_search': 2,
      'report_generation': 3,
      'quality_check': 4,
      'storing_results': 5,
      'completed': 6,
      'error': -1,
    };
    return statusMap[status] ?? 0;
  };

  const activeStep = getStepFromStatus(currentStatus);

  const steps: WorkflowStep[] = [
    {
      label: 'Upload Images',
      description: 'Medical images uploaded and ready for analysis',
      icon: <UploadIcon />,
      status: activeStep > 0 ? 'completed' : activeStep === 0 ? 'active' : 'waiting',
    },
    {
      label: 'Image Analysis',
      description: totalImages ? `Analyzing ${totalImages} medical images for abnormalities` : 'AI-powered medical image analysis',
      icon: <ScanIcon />,
      status: activeStep > 1 ? 'completed' : activeStep === 1 ? 'active' : 'waiting',
      progress: currentImage && totalImages ? (currentImage / totalImages) * 100 : undefined,
    },
    {
      label: 'Literature Search',
      description: 'Searching medical literature and research papers',
      icon: <SearchIcon />,
      status: activeStep > 2 ? 'completed' : activeStep === 2 ? 'active' : 'waiting',
    },
    {
      label: 'Report Generation',
      description: 'Creating comprehensive medical report with findings',
      icon: <ReportIcon />,
      status: activeStep > 3 ? 'completed' : activeStep === 3 ? 'active' : 'waiting',
    },
    {
      label: 'Quality Assessment',
      description: 'Verifying report accuracy and completeness',
      icon: <QualityIcon />,
      status: activeStep > 4 ? 'completed' : activeStep === 4 ? 'active' : 'waiting',
    },
    {
      label: 'Saving Results',
      description: 'Storing report and generating embeddings',
      icon: <SaveIcon />,
      status: activeStep > 5 ? 'completed' : activeStep === 5 ? 'active' : 'waiting',
    },
  ];

  if (currentStatus === 'error') {
    steps[Math.max(0, activeStep)].status = 'error';
  }

  return (
    <StyledPaper elevation={0}>
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Medical Imaging Analysis Progress
          </Typography>
          <ProgressChip 
            label={`${progress}% Complete`}
            size="small"
          />
        </Box>
        <LinearProgress 
          variant="determinate" 
          value={progress} 
          sx={{ 
            height: 8,
            borderRadius: 4,
            backgroundColor: (theme: Theme) => alpha(theme.palette.primary.main, 0.1),
            '& .MuiLinearProgress-bar': {
              borderRadius: 4,
              background: (theme: Theme) =>
                `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
            },
          }}
        />
        {message && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {message}
          </Typography>
        )}
      </Box>

      <Stepper activeStep={activeStep} orientation="vertical">
        {steps.map((step, index) => (
          <Step key={step.label} completed={step.status === 'completed'}>
            <StepLabel
              StepIconComponent={() => (
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 
                      step.status === 'completed' 
                        ? 'success.main'
                        : step.status === 'active'
                        ? 'primary.main'
                        : step.status === 'error'
                        ? 'error.main'
                        : 'action.disabledBackground',
                    color: 
                      step.status === 'waiting' 
                        ? 'text.disabled'
                        : 'background.paper',
                    transition: 'all 0.3s ease',
                  }}
                >
                  {step.status === 'completed' ? <CheckIcon /> : step.status === 'error' ? <ErrorIcon /> : step.icon}
                </Box>
              )}
              error={step.status === 'error'}
            >
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {step.label}
              </Typography>
            </StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary">
                {step.description}
              </Typography>
              {step.progress !== undefined && (
                <Box sx={{ mt: 1 }}>
                  <LinearProgress
                    variant="determinate"
                    value={step.progress}
                    sx={{ height: 4, borderRadius: 2 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                    {currentImage} of {totalImages} images processed
                  </Typography>
                </Box>
              )}
            </StepContent>
          </Step>
        ))}
      </Stepper>
    </StyledPaper>
  );
};

export default WorkflowProgress;
