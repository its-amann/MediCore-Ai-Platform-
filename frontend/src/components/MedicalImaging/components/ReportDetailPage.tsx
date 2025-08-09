import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Divider,
  Chip,
  Button,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
  LinearProgress,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon,
  Print as PrintIcon,
  Share as ShareIcon,
  Download as DownloadIcon,
  Visibility as VisibilityIcon,
  LocalHospital as LocalHospitalIcon,
  Science as ScienceIcon,
  Description as DescriptionIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  ZoomIn as ZoomInIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { MedicalReport, Finding, Citation, HeatmapData } from '../types';
import api from '../../../api/axios';
import medicalImagingApi from '../../../services/medicalImagingApi';

interface ReportDetailPageProps {
  report: MedicalReport;
  onBack?: () => void;
  showActions?: boolean;
}

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
      id={`report-tabpanel-${index}`}
      aria-labelledby={`report-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const ReportDetailPage: React.FC<ReportDetailPageProps> = ({
  report,
  onBack,
  showActions = true,
}) => {
  const theme = useTheme();
  const [selectedTab, setSelectedTab] = useState(0);
  const [imageDialogOpen, setImageDialogOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState<any>(null);
  const [heatmapDialogOpen, setHeatmapDialogOpen] = useState(false);
  const [selectedHeatmap, setSelectedHeatmap] = useState<HeatmapData | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = async () => {
    setLoading(true);
    try {
      const response = await medicalImagingApi.get(`/medical-imaging/imaging-reports/${report.id}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `medical-report-${report.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download report:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityIcon = (severity?: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <WarningIcon color="error" />;
      case 'medium':
        return <WarningIcon color="warning" />;
      default:
        return <CheckCircleIcon color="success" />;
    }
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return theme.palette.error.main;
      case 'medium':
        return theme.palette.warning.main;
      default:
        return theme.palette.success.main;
    }
  };

  const renderMarkdown = (content: string) => {
    return (
      <ReactMarkdown
        components={{
          code({ className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const inline = !match;
            return !inline ? (
              <SyntaxHighlighter
                language={match[1]}
                style={vscDarkPlus as any}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: alpha(theme.palette.background.default, 0.95) }}>
      {loading && <LinearProgress />}
      
      {/* Header */}
      <Paper
        elevation={0}
        sx={{
          p: 3,
          backgroundColor: alpha(theme.palette.primary.main, 0.05),
          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {onBack && (
              <IconButton onClick={onBack}>
                <ArrowBackIcon />
              </IconButton>
            )}
            <Box>
              <Typography variant="h4" fontWeight={600}>
                Medical Imaging Report
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Report ID: {report.id || 'N/A'} | Generated: {report.createdAt ? format(new Date(report.createdAt), 'PPpp') : 'N/A'}
              </Typography>
            </Box>
          </Box>
          
          {showActions && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Print Report">
                <IconButton onClick={handlePrint}>
                  <PrintIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Download PDF">
                <IconButton onClick={handleDownload}>
                  <DownloadIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Share Report">
                <IconButton>
                  <ShareIcon />
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </Box>
      </Paper>

      <Box sx={{ px: 3, py: 4 }}>
        {/* Patient Information */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              Patient Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={3}>
                <Typography variant="body2" color="text.secondary">Name</Typography>
                <Typography variant="body1" fontWeight={500}>{report.patientName || 'Unknown'}</Typography>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Typography variant="body2" color="text.secondary">Patient ID</Typography>
                <Typography variant="body1" fontWeight={500}>{report.patientId}</Typography>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Typography variant="body2" color="text.secondary">Study Type</Typography>
                <Typography variant="body1" fontWeight={500}>{report.studyType || 'N/A'}</Typography>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Typography variant="body2" color="text.secondary">Study Date</Typography>
                <Typography variant="body1" fontWeight={500}>
                  {(report as any).studyDate || report.createdAt ? format(new Date((report as any).studyDate || report.createdAt), 'PP') : 'N/A'}
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Severity Summary */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <AssessmentIcon color="primary" />
              <Typography variant="h6" fontWeight={600}>
                Report Summary
              </Typography>
            </Box>
            
            <Grid container spacing={3}>
              <Grid item xs={12} sm={4}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h3" sx={{ color: getSeverityColor((report as any).severity || 'low') }}>
                    {report.findings?.filter(f => f.severity === 'critical' || f.severity === 'high').length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Critical Findings
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h3" color="warning.main">
                    {report.findings?.filter(f => f.severity === 'medium').length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Moderate Findings
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h3" color="success.main">
                    {report.findings?.filter(f => f.severity === 'low' || !f.severity).length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Normal/Low Findings
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Main Content Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs
            value={selectedTab}
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label="Clinical Analysis" icon={<LocalHospitalIcon />} iconPosition="start" />
            <Tab label="Images & Heatmaps" icon={<VisibilityIcon />} iconPosition="start" />
            <Tab label="References" icon={<DescriptionIcon />} iconPosition="start" />
            <Tab label="Timeline" icon={<TimelineIcon />} iconPosition="start" />
          </Tabs>

          <Box sx={{ p: 3 }}>
            <TabPanel value={selectedTab} index={0}>
              {/* Clinical Analysis Tab */}
              <Box>
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  Radiological Analysis
                </Typography>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    mb: 3,
                    backgroundColor: alpha(theme.palette.background.default, 0.5),
                    border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                  }}
                >
                  {renderMarkdown((report as any).radiologicalAnalysis || (report as any).overall_analysis || report.summary || '')}
                </Paper>

                <Typography variant="h6" gutterBottom fontWeight={600}>
                  Clinical Impression
                </Typography>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    mb: 3,
                    backgroundColor: alpha(theme.palette.info.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                  }}
                >
                  {renderMarkdown((report as any).clinicalImpression || report.conclusion || '')}
                </Paper>

                <Typography variant="h6" gutterBottom fontWeight={600}>
                  Key Findings
                </Typography>
                <List>
                  {(report.findings || []).map((finding, index) => (
                    <ListItem
                      key={finding.id || index}
                      sx={{
                        mb: 2,
                        backgroundColor: alpha(theme.palette.background.paper, 0.8),
                        borderRadius: 1,
                        border: `1px solid ${alpha(getSeverityColor(finding.severity), 0.3)}`,
                      }}
                    >
                      <ListItemIcon>
                        {getSeverityIcon(finding.severity)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body1">{finding.description}</Typography>
                            {finding.severity && (
                              <Chip
                                label={finding.severity}
                                size="small"
                                color={
                                  finding.severity === 'critical' || finding.severity === 'high'
                                    ? 'error'
                                    : finding.severity === 'medium'
                                    ? 'warning'
                                    : 'success'
                                }
                              />
                            )}
                          </Box>
                        }
                        secondary={
                          finding.recommendations && finding.recommendations.length > 0 && (
                            <Box sx={{ mt: 1 }}>
                              <Typography variant="caption" color="text.secondary">
                                Recommendations:
                              </Typography>
                              <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                                {finding.recommendations.map((rec, idx) => (
                                  <li key={idx}>
                                    <Typography variant="body2">{rec}</Typography>
                                  </li>
                                ))}
                              </ul>
                            </Box>
                          )
                        }
                      />
                    </ListItem>
                  ))}
                </List>

                {report.recommendations && report.recommendations.length > 0 && (
                  <>
                    <Typography variant="h6" gutterBottom fontWeight={600} sx={{ mt: 3 }}>
                      Recommendations
                    </Typography>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 3,
                        backgroundColor: alpha(theme.palette.warning.main, 0.05),
                        border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                      }}
                    >
                      <List>
                        {(report.recommendations || []).map((rec, index) => (
                          <ListItem key={index}>
                            <ListItemIcon>
                              <InfoIcon color="warning" />
                            </ListItemIcon>
                            <ListItemText primary={rec} />
                          </ListItem>
                        ))}
                      </List>
                    </Paper>
                  </>
                )}
              </Box>
            </TabPanel>

            <TabPanel value={selectedTab} index={1}>
              {/* Images & Heatmaps Tab */}
              <Grid container spacing={3}>
                {(report.images || []).map((image, index) => (
                  <Grid item xs={12} md={6} key={image.id}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          {image.file.name}
                        </Typography>
                        <Box
                          sx={{
                            position: 'relative',
                            cursor: 'pointer',
                            '&:hover': { opacity: 0.9 },
                          }}
                          onClick={() => {
                            setSelectedImage(image);
                            setImageDialogOpen(true);
                          }}
                        >
                          <img
                            src={image.preview}
                            alt={image.file.name}
                            style={{
                              width: '100%',
                              height: 'auto',
                              borderRadius: 8,
                              maxHeight: 300,
                              objectFit: 'cover',
                            }}
                          />
                          <IconButton
                            sx={{
                              position: 'absolute',
                              top: 8,
                              right: 8,
                              backgroundColor: alpha(theme.palette.background.paper, 0.8),
                            }}
                          >
                            <ZoomInIcon />
                          </IconButton>
                        </Box>
                        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                          <Chip label={image.type} size="small" color="primary" />
                          {image.status === 'completed' && (
                            <Chip
                              label="Analyzed"
                              size="small"
                              color="success"
                              icon={<CheckCircleIcon />}
                            />
                          )}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </TabPanel>

            <TabPanel value={selectedTab} index={2}>
              {/* References Tab */}
              {report.citations && report.citations.length > 0 ? (
                <List>
                  {report.citations.map((citation, index) => (
                    <ListItem
                      key={index}
                      sx={{
                        mb: 2,
                        backgroundColor: alpha(theme.palette.background.paper, 0.8),
                        borderRadius: 1,
                        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                      }}
                    >
                      <ListItemIcon>
                        <ScienceIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Typography variant="body1" fontWeight={500}>
                            [{index + 1}] {citation.title || citation.text}
                          </Typography>
                        }
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                              {citation.authors || 'Unknown Authors'} ({citation.year || 'N/A'})
                            </Typography>
                            {citation.snippet && (
                              <Typography
                                variant="body2"
                                sx={{ mt: 1, fontStyle: 'italic' }}
                              >
                                "{citation.snippet}"
                              </Typography>
                            )}
                            {citation.source && (
                              <Typography variant="caption" color="primary.main">
                                Source: {citation.source}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Alert severity="info">No references available for this report.</Alert>
              )}
            </TabPanel>

            <TabPanel value={selectedTab} index={3}>
              {/* Timeline Tab */}
              <Box sx={{ position: 'relative' }}>
                <Box
                  sx={{
                    position: 'absolute',
                    left: 20,
                    top: 0,
                    bottom: 0,
                    width: 2,
                    backgroundColor: alpha(theme.palette.primary.main, 0.3),
                  }}
                />
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: '50%',
                          backgroundColor: theme.palette.primary.main,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                        }}
                      >
                        <LocalHospitalIcon />
                      </Box>
                    </ListItemIcon>
                    <ListItemText
                      primary="Report Created"
                      secondary={report.createdAt ? format(new Date(report.createdAt), 'PPpp') : 'N/A'}
                    />
                  </ListItem>
                  {report.updatedAt && report.createdAt && report.updatedAt !== report.createdAt && (
                    <ListItem>
                      <ListItemIcon>
                        <Box
                          sx={{
                            width: 40,
                            height: 40,
                            borderRadius: '50%',
                            backgroundColor: theme.palette.info.main,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                          }}
                        >
                          <InfoIcon />
                        </Box>
                      </ListItemIcon>
                      <ListItemText
                        primary="Report Updated"
                        secondary={format(new Date(report.updatedAt), 'PPpp')}
                      />
                    </ListItem>
                  )}
                </List>
              </Box>
            </TabPanel>
          </Box>
        </Paper>
      </Box>

      {/* Image Dialog */}
      <Dialog
        open={imageDialogOpen}
        onClose={() => setImageDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        {selectedImage && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">{selectedImage.file.name}</Typography>
                <IconButton onClick={() => setImageDialogOpen(false)}>
                  <ArrowBackIcon />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent>
              <img
                src={selectedImage.preview}
                alt={selectedImage.file.name}
                style={{ width: '100%', height: 'auto' }}
              />
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default ReportDetailPage;