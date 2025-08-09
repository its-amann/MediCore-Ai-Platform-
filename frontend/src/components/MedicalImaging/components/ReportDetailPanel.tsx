import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Chip,
  Button,
  Divider,
  Avatar,
  LinearProgress,
  Card,
  CardContent,
  Grid,
  Tooltip,
  Stack,
  Alert,
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  Fade,
  Zoom,
} from '@mui/material';
import { useTheme, alpha, styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Close as CloseIcon,
  SmartToy as SmartToyIcon,
  Psychology as PsychologyIcon,
  Analytics as AnalyticsIcon,
  Security as SecurityIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  Print as PrintIcon,
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon,
  AccessTime as AccessTimeIcon,
  LocalHospital as LocalHospitalIcon,
  BioTech as BioTechIcon,
  Timeline as TimelineIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Language as LanguageIcon,
  Science as ScienceIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { MedicalReport, Finding } from '../types';

// Styled Components
const GlassCard = styled(Card)(({ theme }) => ({
  background: alpha(theme.palette.background.paper, 0.8),
  backdropFilter: 'blur(20px)',
  border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  borderRadius: theme.spacing(2),
  transition: 'all 0.3s ease',
  '&:hover': {
    border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
    boxShadow: `0 8px 32px ${alpha(theme.palette.primary.main, 0.1)}`,
  },
}));

const MetricCard = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: theme.spacing(2),
  background: `linear-gradient(135deg, ${alpha(theme.palette.background.paper, 0.9)} 0%, ${alpha(theme.palette.background.paper, 0.7)} 100%)`,
  border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
  textAlign: 'center',
  transition: 'all 0.3s ease',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: `0 12px 24px ${alpha(theme.palette.common.black, 0.1)}`,
  },
}));

const InsightCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2.5),
  borderRadius: theme.spacing(1.5),
  background: alpha(theme.palette.background.paper, 0.6),
  border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
  transition: 'all 0.3s ease',
  position: 'relative',
  overflow: 'hidden',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    width: '4px',
    height: '100%',
    background: theme.palette.primary.main,
    transition: 'width 0.3s ease',
  },
  '&:hover': {
    transform: 'translateX(4px)',
    boxShadow: `0 4px 16px ${alpha(theme.palette.primary.main, 0.15)}`,
    '&::before': {
      width: '6px',
    },
  },
}));

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

interface ExtendedReport extends MedicalReport {
  aiModel?: string;
  confidenceScore?: number;
  processingTime?: number;
  aiInsights?: {
    category: string;
    insights: string[];
    confidence: number;
  }[];
  relatedStudies?: {
    id: string;
    date: Date;
    type: string;
    similarity: number;
  }[];
}

interface ReportDetailPanelProps {
  report: ExtendedReport;
  onClose?: () => void;
  fullScreen?: boolean;
}

const ReportDetailPanel: React.FC<ReportDetailPanelProps> = ({
  report,
  onClose,
  fullScreen = false,
}) => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [bookmarked, setBookmarked] = useState(false);
  const [showSensitive, setShowSensitive] = useState(false);

  // Mock AI insights for demonstration
  const mockAiInsights = [
    {
      category: 'Primary Findings',
      insights: [
        'Identified area of increased density in upper right quadrant',
        'Pattern consistent with previous studies from similar cases',
        'No significant changes compared to baseline scan',
      ],
      confidence: 0.92,
    },
    {
      category: 'Differential Diagnosis',
      insights: [
        'Most likely: Benign nodule (78% probability)',
        'Consider: Follow-up imaging in 6 months',
        'Low probability of malignancy based on imaging characteristics',
      ],
      confidence: 0.85,
    },
    {
      category: 'Technical Quality',
      insights: [
        'Excellent image quality with minimal artifacts',
        'All required sequences completed successfully',
        'Contrast enhancement adequate for diagnosis',
      ],
      confidence: 0.95,
    },
  ];

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'critical':
        return theme.palette.error.main;
      case 'high':
        return theme.palette.warning.main;
      case 'medium':
        return theme.palette.info.main;
      case 'low':
        return theme.palette.success.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.9) return <CheckCircleIcon color="success" />;
    if (confidence >= 0.7) return <InfoIcon color="info" />;
    return <WarningIcon color="warning" />;
  };

  return (
    <Box
      sx={{
        height: fullScreen ? '100vh' : 'auto',
        display: 'flex',
        flexDirection: 'column',
        background: `linear-gradient(180deg, ${alpha(theme.palette.background.default, 0.95)} 0%, ${theme.palette.background.paper} 100%)`,
      }}
    >
      {/* Header */}
      <Paper
        elevation={0}
        sx={{
          p: 3,
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.05)} 0%, ${alpha(theme.palette.primary.main, 0.02)} 100%)`,
          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h5" fontWeight={600} gutterBottom>
              {report.studyType || 'Medical'} Report
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <Chip
                icon={<LocalHospitalIcon />}
                label={report.patientName || 'Unknown'}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<AccessTimeIcon />}
                label={(report.studyDate || report.createdAt) ? format(new Date(report.studyDate || report.createdAt || Date.now()), 'MMM dd, yyyy') : 'N/A'}
                size="small"
                variant="outlined"
              />
              {report.aiModel && (
                <Chip
                  icon={<SmartToyIcon />}
                  label={report.aiModel}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              )}
              {report.severity && (
                <Chip
                  label={report.severity.toUpperCase()}
                  size="small"
                  sx={{
                    backgroundColor: alpha(getSeverityColor(report.severity), 0.1),
                    color: getSeverityColor(report.severity),
                    border: `1px solid ${alpha(getSeverityColor(report.severity), 0.3)}`,
                  }}
                />
              )}
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title={bookmarked ? "Remove bookmark" : "Bookmark"}>
              <IconButton onClick={() => setBookmarked(!bookmarked)}>
                {bookmarked ? <BookmarkIcon color="primary" /> : <BookmarkBorderIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Share">
              <IconButton>
                <ShareIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Print">
              <IconButton>
                <PrintIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Download">
              <IconButton>
                <DownloadIcon />
              </IconButton>
            </Tooltip>
            {onClose && (
              <IconButton onClick={onClose}>
                <CloseIcon />
              </IconButton>
            )}
          </Box>
        </Box>
      </Paper>

      {/* AI Metrics Bar */}
      <Box sx={{ p: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <MetricCard>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  mx: 'auto',
                  mb: 2,
                }}
              >
                <PsychologyIcon color="primary" />
              </Avatar>
              <Typography variant="h6" fontWeight={600}>
                {report.confidenceScore ? `${(report.confidenceScore * 100).toFixed(0)}%` : 'N/A'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                AI Confidence
              </Typography>
            </MetricCard>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <MetricCard>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  bgcolor: alpha(theme.palette.success.main, 0.1),
                  mx: 'auto',
                  mb: 2,
                }}
              >
                <TrendingUpIcon color="success" />
              </Avatar>
              <Typography variant="h6" fontWeight={600}>
                {report.findings?.length || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total Findings
              </Typography>
            </MetricCard>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <MetricCard>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  bgcolor: alpha(theme.palette.warning.main, 0.1),
                  mx: 'auto',
                  mb: 2,
                }}
              >
                <AccessTimeIcon color="warning" />
              </Avatar>
              <Typography variant="h6" fontWeight={600}>
                {report.processingTime ? `${report.processingTime}s` : 'N/A'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Processing Time
              </Typography>
            </MetricCard>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <MetricCard>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  bgcolor: alpha(theme.palette.info.main, 0.1),
                  mx: 'auto',
                  mb: 2,
                }}
              >
                <AnalyticsIcon color="info" />
              </Avatar>
              <Typography variant="h6" fontWeight={600}>
                {mockAiInsights.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                AI Insights
              </Typography>
            </MetricCard>
          </Grid>
        </Grid>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_: React.SyntheticEvent, newValue: number) => setActiveTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Overview" icon={<VisibilityIcon />} iconPosition="start" />
          <Tab label="AI Insights" icon={<PsychologyIcon />} iconPosition="start" />
          <Tab label="Findings" icon={<BioTechIcon />} iconPosition="start" />
          <Tab label="Timeline" icon={<TimelineIcon />} iconPosition="start" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ flex: 1, overflow: 'auto', px: 3 }}>
        <TabPanel value={activeTab} index={0}>
          {/* Overview Tab */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <GlassCard>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    Summary
                  </Typography>
                  <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                    {report.summary || 'No summary available'}
                  </Typography>
                  
                  {report.conclusion && (
                    <>
                      <Divider sx={{ my: 3 }} />
                      <Typography variant="h6" gutterBottom fontWeight={600}>
                        Conclusion
                      </Typography>
                      <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                        {report.conclusion}
                      </Typography>
                    </>
                  )}
                  
                  {report.recommendations && report.recommendations.length > 0 && (
                    <>
                      <Divider sx={{ my: 3 }} />
                      <Typography variant="h6" gutterBottom fontWeight={600}>
                        Recommendations
                      </Typography>
                      <Stack spacing={2}>
                        {(report.recommendations || []).map((rec, index) => (
                          <Alert
                            key={index}
                            severity="info"
                            icon={<CheckCircleIcon />}
                            sx={{
                              borderRadius: 2,
                              background: alpha(theme.palette.info.main, 0.05),
                              border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                            }}
                          >
                            {rec}
                          </Alert>
                        ))}
                      </Stack>
                    </>
                  )}
                </CardContent>
              </GlassCard>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Stack spacing={3}>
                {/* Clinical Impression */}
                {report.clinicalImpression && (
                  <GlassCard>
                    <CardContent>
                      <Typography variant="h6" gutterBottom fontWeight={600}>
                        Clinical Impression
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <IconButton
                          size="small"
                          onClick={() => setShowSensitive(!showSensitive)}
                        >
                          {showSensitive ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                        <Typography variant="caption" color="text.secondary">
                          {showSensitive ? 'Hide sensitive info' : 'Show sensitive info'}
                        </Typography>
                      </Box>
                      <Typography
                        variant="body2"
                        sx={{
                          filter: showSensitive ? 'none' : 'blur(4px)',
                          transition: 'filter 0.3s ease',
                          userSelect: showSensitive ? 'text' : 'none',
                        }}
                      >
                        {report.clinicalImpression}
                      </Typography>
                    </CardContent>
                  </GlassCard>
                )}
                
                {/* Related Studies */}
                {report.relatedStudies && report.relatedStudies.length > 0 && (
                  <GlassCard>
                    <CardContent>
                      <Typography variant="h6" gutterBottom fontWeight={600}>
                        Related Studies
                      </Typography>
                      <Stack spacing={2}>
                        {report.relatedStudies.slice(0, 3).map((study) => (
                          <Box
                            key={study.id}
                            sx={{
                              p: 2,
                              borderRadius: 2,
                              background: alpha(theme.palette.background.default, 0.5),
                              border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                              cursor: 'pointer',
                              transition: 'all 0.3s ease',
                              '&:hover': {
                                background: alpha(theme.palette.primary.main, 0.05),
                                transform: 'translateX(4px)',
                              },
                            }}
                          >
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                              <Typography variant="subtitle2" fontWeight={600}>
                                {study.type}
                              </Typography>
                              <Chip
                                label={`${(study.similarity * 100).toFixed(0)}% match`}
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                              {format(new Date(study.date), 'MMM dd, yyyy')}
                            </Typography>
                          </Box>
                        ))}
                      </Stack>
                    </CardContent>
                  </GlassCard>
                )}
              </Stack>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          {/* AI Insights Tab */}
          <Grid container spacing={3}>
            {mockAiInsights.map((insight, index) => (
              <Grid item xs={12} md={6} key={index}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <GlassCard>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6" fontWeight={600}>
                          {insight.category}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getConfidenceIcon(insight.confidence)}
                          <Typography variant="body2" color="text.secondary">
                            {(insight.confidence * 100).toFixed(0)}% confidence
                          </Typography>
                        </Box>
                      </Box>
                      
                      <Stack spacing={2}>
                        {insight.insights.map((item, idx) => (
                          <InsightCard key={idx} elevation={0}>
                            <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                              {item}
                            </Typography>
                          </InsightCard>
                        ))}
                      </Stack>
                    </CardContent>
                  </GlassCard>
                </motion.div>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          {/* Findings Tab */}
          <Grid container spacing={3}>
            {(report.findings || []).map((finding, index) => (
              <Grid item xs={12} md={6} key={finding.id}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <GlassCard>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box>
                          <Typography variant="h6" fontWeight={600}>
                            Finding #{index + 1}
                          </Typography>
                          <Chip
                            label={finding.type.replace('_', ' ').toUpperCase()}
                            size="small"
                            sx={{
                              mt: 1,
                              backgroundColor: finding.type === 'anomaly' 
                                ? alpha(theme.palette.error.main, 0.1)
                                : finding.type === 'attention_required'
                                ? alpha(theme.palette.warning.main, 0.1)
                                : alpha(theme.palette.success.main, 0.1),
                              color: finding.type === 'anomaly' 
                                ? theme.palette.error.main
                                : finding.type === 'attention_required'
                                ? theme.palette.warning.main
                                : theme.palette.success.main,
                            }}
                          />
                        </Box>
                        {finding.severity && (
                          <Chip
                            label={finding.severity.toUpperCase()}
                            size="small"
                            sx={{
                              backgroundColor: alpha(getSeverityColor(finding.severity), 0.1),
                              color: getSeverityColor(finding.severity),
                              border: `1px solid ${alpha(getSeverityColor(finding.severity), 0.3)}`,
                            }}
                          />
                        )}
                      </Box>
                      
                      <Typography variant="body2" paragraph sx={{ lineHeight: 1.6 }}>
                        {finding.description}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <LinearProgress
                          variant="determinate"
                          value={finding.confidence * 100}
                          sx={{
                            flex: 1,
                            height: 6,
                            borderRadius: 3,
                            backgroundColor: alpha(theme.palette.divider, 0.1),
                            '& .MuiLinearProgress-bar': {
                              borderRadius: 3,
                              backgroundColor: finding.confidence >= 0.8 
                                ? theme.palette.success.main
                                : theme.palette.warning.main,
                            },
                          }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {(finding.confidence * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                      
                      {finding.recommendations && finding.recommendations.length > 0 && (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                            Recommendations:
                          </Typography>
                          {finding.recommendations.map((rec, idx) => (
                            <Typography key={idx} variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                              • {rec}
                            </Typography>
                          ))}
                        </Box>
                      )}
                    </CardContent>
                  </GlassCard>
                </motion.div>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          {/* Timeline Tab */}
          <Timeline position="alternate">
            <TimelineItem>
              <TimelineSeparator>
                <TimelineDot color="primary">
                  <LocalHospitalIcon />
                </TimelineDot>
                <TimelineConnector />
              </TimelineSeparator>
              <TimelineContent>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    background: alpha(theme.palette.primary.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                  }}
                >
                  <Typography variant="h6" component="h1" fontWeight={600}>
                    Study Initiated
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {report.createdAt ? format(new Date(report.createdAt), 'MMM dd, yyyy h:mm a') : 'N/A'}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {report.studyType || 'Medical'} examination started
                  </Typography>
                </Paper>
              </TimelineContent>
            </TimelineItem>

            <TimelineItem>
              <TimelineSeparator>
                <TimelineDot color="secondary">
                  <SmartToyIcon />
                </TimelineDot>
                <TimelineConnector />
              </TimelineSeparator>
              <TimelineContent>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    background: alpha(theme.palette.secondary.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
                  }}
                >
                  <Typography variant="h6" component="h1" fontWeight={600}>
                    AI Analysis Started
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {report.aiModel || 'Advanced AI Model'}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Processing time: {report.processingTime || '45'}s
                  </Typography>
                </Paper>
              </TimelineContent>
            </TimelineItem>

            <TimelineItem>
              <TimelineSeparator>
                <TimelineDot color="success">
                  <CheckCircleIcon />
                </TimelineDot>
              </TimelineSeparator>
              <TimelineContent>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    background: alpha(theme.palette.success.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
                  }}
                >
                  <Typography variant="h6" component="h1" fontWeight={600}>
                    Report Generated
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {report.updatedAt ? format(new Date(report.updatedAt), 'MMM dd, yyyy h:mm a') : 'N/A'}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {report.findings?.length || 0} findings identified
                  </Typography>
                </Paper>
              </TimelineContent>
            </TimelineItem>
          </Timeline>
        </TabPanel>
      </Box>
    </Box>
  );
};

export default ReportDetailPanel;