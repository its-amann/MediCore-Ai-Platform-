import React, { useState } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  Stack,
  Alert,
  Snackbar,
  Dialog,
  DialogContent,
  IconButton,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Code as CodeIcon,
  ContentCopy as ContentCopyIcon,
  CheckCircle as CheckCircleIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import ModernReportsViewer from './components/ModernReportsViewer';
import ReportDetailPanel from './components/ReportDetailPanel';
import { MedicalReport } from './types';

const ModernReportsUsage: React.FC = () => {
  const theme = useTheme();
  const [selectedReport, setSelectedReport] = useState<MedicalReport | null>(null);
  const [showDetailPanel, setShowDetailPanel] = useState(false);
  const [copied, setCopied] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const handleReportSelect = (report: MedicalReport) => {
    setSelectedReport(report);
    setShowDetailPanel(true);
    setSnackbarOpen(true);
  };

  const copyCodeToClipboard = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const usageExample = `import React, { useState } from 'react';
import { ModernReportsViewer, ReportDetailPanel } from '@/components/MedicalImaging';
import { MedicalReport } from '@/components/MedicalImaging/types';

function MyMedicalApp() {
  const [selectedReport, setSelectedReport] = useState<MedicalReport | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  const handleReportSelect = (report: MedicalReport) => {
    setSelectedReport(report);
    setShowDetail(true);
  };

  return (
    <div>
      {/* Modern Reports Viewer with AI Insights */}
      <ModernReportsViewer
        patientId="patient-123"  // Optional: filter by patient
        onReportSelect={handleReportSelect}
        maxReports={50}  // Maximum number of reports to display
        compact={false}  // Full view with header
      />

      {/* Report Detail Panel */}
      {showDetail && selectedReport && (
        <Dialog open={showDetail} onClose={() => setShowDetail(false)} maxWidth="lg" fullWidth>
          <ReportDetailPanel
            report={selectedReport}
            onClose={() => setShowDetail(false)}
            fullScreen={false}
          />
        </Dialog>
      )}
    </div>
  );
}`;

  const features = [
    {
      title: 'AI-Powered Insights',
      description: 'View AI model predictions, confidence scores, and detailed analysis for each report',
    },
    {
      title: 'Advanced Filtering',
      description: 'Filter by date range, study type, AI model, confidence level, and more',
    },
    {
      title: 'Beautiful UI',
      description: 'Modern glassmorphism design with smooth animations and transitions',
    },
    {
      title: 'Grid & List Views',
      description: 'Toggle between grid and list layouts for optimal viewing experience',
    },
    {
      title: 'Real-time Search',
      description: 'Search across patient names, findings, and AI insights instantly',
    },
    {
      title: 'Detailed Reports',
      description: 'View comprehensive report details with findings, timeline, and recommendations',
    },
  ];

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(180deg, ${alpha(theme.palette.primary.main, 0.02)} 0%, ${theme.palette.background.default} 100%)`,
        py: 4,
      }}
    >
      <Container maxWidth="xl">
        {/* Header */}
        <Paper
          elevation={0}
          sx={{
            p: 4,
            mb: 4,
            background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.05)} 100%)`,
            borderRadius: 3,
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          }}
        >
          <Typography
            variant="h3"
            gutterBottom
            sx={{
              background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              color: 'transparent',
              fontWeight: 700,
              mb: 2,
            }}
          >
            Modern Reports Viewer Usage
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
            Learn how to integrate the modern medical reports viewer with AI insights into your application
          </Typography>

          {/* Features Grid */}
          <Box sx={{ mt: 4, mb: 4 }}>
            <Typography variant="h5" gutterBottom fontWeight={600}>
              Key Features
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' },
                gap: 2,
                mt: 2,
              }}
            >
              {features.map((feature, index) => (
                <Paper
                  key={index}
                  elevation={0}
                  sx={{
                    p: 3,
                    background: alpha(theme.palette.background.paper, 0.8),
                    border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                    borderRadius: 2,
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: `0 8px 24px ${alpha(theme.palette.common.black, 0.1)}`,
                      border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                    },
                  }}
                >
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {feature.description}
                  </Typography>
                </Paper>
              ))}
            </Box>
          </Box>

          {/* Code Example */}
          <Box sx={{ mt: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h5" fontWeight={600}>
                Implementation Example
              </Typography>
              <Button
                startIcon={copied ? <CheckCircleIcon /> : <ContentCopyIcon />}
                onClick={() => copyCodeToClipboard(usageExample)}
                color={copied ? 'success' : 'primary'}
                variant="outlined"
                size="small"
                sx={{ borderRadius: 2 }}
              >
                {copied ? 'Copied!' : 'Copy Code'}
              </Button>
            </Box>
            <Paper
              elevation={0}
              sx={{
                p: 3,
                background: alpha(theme.palette.common.black, 0.02),
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                borderRadius: 2,
                overflow: 'auto',
              }}
            >
              <Box
                component="pre"
                sx={{
                  margin: 0,
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  lineHeight: 1.6,
                  color: theme.palette.text.primary,
                }}
              >
                <code>{usageExample}</code>
              </Box>
            </Paper>
          </Box>

          {/* API Props */}
          <Box sx={{ mt: 4 }}>
            <Typography variant="h5" gutterBottom fontWeight={600}>
              Component Props
            </Typography>
            
            <Typography variant="h6" sx={{ mt: 3, mb: 2 }} fontWeight={600}>
              ModernReportsViewer Props
            </Typography>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                background: alpha(theme.palette.background.default, 0.5),
                border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                borderRadius: 2,
              }}
            >
              <Stack spacing={1}>
                <Typography variant="body2">
                  <strong>patientId?:</strong> string - Filter reports by patient ID
                </Typography>
                <Typography variant="body2">
                  <strong>onReportSelect?:</strong> (report: MedicalReport) =&gt; void - Callback when report is selected
                </Typography>
                <Typography variant="body2">
                  <strong>maxReports?:</strong> number - Maximum number of reports to display (default: 50)
                </Typography>
                <Typography variant="body2">
                  <strong>compact?:</strong> boolean - Show compact view without header (default: false)
                </Typography>
              </Stack>
            </Paper>

            <Typography variant="h6" sx={{ mt: 3, mb: 2 }} fontWeight={600}>
              ReportDetailPanel Props
            </Typography>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                background: alpha(theme.palette.background.default, 0.5),
                border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                borderRadius: 2,
              }}
            >
              <Stack spacing={1}>
                <Typography variant="body2">
                  <strong>report:</strong> ExtendedReport - The report object to display
                </Typography>
                <Typography variant="body2">
                  <strong>onClose?:</strong> () =&gt; void - Callback when panel is closed
                </Typography>
                <Typography variant="body2">
                  <strong>fullScreen?:</strong> boolean - Show in fullscreen mode (default: false)
                </Typography>
              </Stack>
            </Paper>
          </Box>
        </Paper>

        {/* Live Demo */}
        <Paper
          elevation={0}
          sx={{
            p: 4,
            background: alpha(theme.palette.background.paper, 0.95),
            borderRadius: 3,
            border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
          }}
        >
          <Typography variant="h5" gutterBottom fontWeight={600}>
            Live Demo
          </Typography>
          <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
            Click on any report card below to see the detailed view with AI insights
          </Alert>

          <ModernReportsViewer
            onReportSelect={handleReportSelect}
            compact={false}
          />
        </Paper>

        {/* Detail Panel Dialog */}
        <Dialog
          open={showDetailPanel}
          onClose={() => setShowDetailPanel(false)}
          maxWidth="lg"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: 3,
              overflow: 'hidden',
            },
          }}
        >
          <DialogContent sx={{ p: 0 }}>
            {selectedReport && (
              <ReportDetailPanel
                report={selectedReport as any}
                onClose={() => setShowDetailPanel(false)}
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Snackbar Notification */}
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={3000}
          onClose={() => setSnackbarOpen(false)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => setSnackbarOpen(false)}
            severity="success"
            sx={{ width: '100%', borderRadius: 2 }}
            action={
              <IconButton
                size="small"
                color="inherit"
                onClick={() => setSnackbarOpen(false)}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            }
          >
            Report opened in detail view
          </Alert>
        </Snackbar>
      </Container>
    </Box>
  );
};

export default ModernReportsUsage;