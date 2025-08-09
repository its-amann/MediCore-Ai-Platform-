import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Divider,
  Chip,
  Stack,
  Button,
  useTheme,
  alpha,
  Fade,
  Grid,
} from '@mui/material';
import {
  ArrowBack,
  Download,
  Share,
  Print,
  ZoomIn,
  ZoomOut,
  Fullscreen,
  CalendarToday,
  Assessment,
  LocalHospital,
  Layers,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import medicalImagingApi from '../services/medicalImagingApi';
import toast from 'react-hot-toast';

// Styled components
const GlassCard = styled(Paper)(({ theme }) => ({
  background: alpha(theme.palette.background.paper, 0.9),
  backdropFilter: 'blur(20px)',
  borderRadius: theme.spacing(2),
  border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  padding: theme.spacing(3),
  transition: 'all 0.3s ease',
  '&:hover': {
    boxShadow: theme.shadows[8],
  },
}));

const MarkdownContainer = styled(Box)(({ theme }) => ({
  '& h1, & h2, & h3, & h4, & h5, & h6': {
    marginTop: theme.spacing(3),
    marginBottom: theme.spacing(2),
    fontWeight: 600,
    color: theme.palette.text.primary,
  },
  '& h1': { fontSize: '2rem' },
  '& h2': { fontSize: '1.5rem' },
  '& h3': { fontSize: '1.25rem' },
  '& h4': { fontSize: '1.1rem' },
  '& p': {
    marginBottom: theme.spacing(2),
    lineHeight: 1.7,
    color: theme.palette.text.secondary,
  },
  '& ul, & ol': {
    marginBottom: theme.spacing(2),
    paddingLeft: theme.spacing(3),
    '& li': {
      marginBottom: theme.spacing(1),
      color: theme.palette.text.secondary,
    },
  },
  '& blockquote': {
    borderLeft: `4px solid ${theme.palette.primary.main}`,
    paddingLeft: theme.spacing(2),
    marginLeft: 0,
    marginRight: 0,
    marginBottom: theme.spacing(2),
    fontStyle: 'italic',
    color: theme.palette.text.secondary,
  },
  '& code': {
    backgroundColor: alpha(theme.palette.primary.main, 0.1),
    padding: '2px 6px',
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: '0.9em',
    color: theme.palette.primary.main,
  },
  '& pre': {
    backgroundColor: alpha(theme.palette.background.default, 0.8),
    padding: theme.spacing(2),
    borderRadius: theme.spacing(1),
    overflowX: 'auto',
    marginBottom: theme.spacing(2),
    '& code': {
      backgroundColor: 'transparent',
      padding: 0,
      color: theme.palette.text.primary,
    },
  },
  '& hr': {
    border: 'none',
    borderTop: `1px solid ${theme.palette.divider}`,
    marginTop: theme.spacing(3),
    marginBottom: theme.spacing(3),
  },
  '& table': {
    width: '100%',
    borderCollapse: 'collapse',
    marginBottom: theme.spacing(2),
    '& th, & td': {
      padding: theme.spacing(1),
      borderBottom: `1px solid ${theme.palette.divider}`,
      textAlign: 'left',
    },
    '& th': {
      fontWeight: 600,
      backgroundColor: alpha(theme.palette.primary.main, 0.05),
    },
  },
  '& strong': {
    fontWeight: 600,
    color: theme.palette.text.primary,
  },
  '& em': {
    fontStyle: 'italic',
  },
  '& a': {
    color: theme.palette.primary.main,
    textDecoration: 'none',
    '&:hover': {
      textDecoration: 'underline',
    },
  },
}));

const ImageContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '100%',
  marginBottom: theme.spacing(3),
  borderRadius: theme.spacing(1),
  overflow: 'hidden',
  backgroundColor: theme.palette.background.default,
  '& img': {
    width: '100%',
    height: 'auto',
    display: 'block',
  },
}));

const HeatmapOverlay = styled('img')(({ theme }) => ({
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  opacity: 0.7,
  mixBlendMode: 'multiply',
  transition: 'opacity 0.3s ease',
  '&:hover': {
    opacity: 0.5,
  },
}));

const MetaInfo = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  marginBottom: theme.spacing(2),
  color: theme.palette.text.secondary,
  fontSize: '0.875rem',
}));

interface Report {
  report_id: string;
  case_id: string;
  created_at: string;
  updated_at?: string;
  study_type: string;
  overall_analysis?: string;
  recommendations?: string[];
  key_findings?: string[];
  status?: string;
  user_id?: string;
  heatmap_data?: {
    overlay: string;
    confidence?: number;
    regions?: any[];
  };
  images?: Array<{
    id: string;
    url?: string;
    analysis_text?: string;
    findings?: string[];
    processing_time?: number;
    heatmap_data?: {
      heatmap_overlay: string;
      attention_regions?: any[];
    };
  }>;
  metadata?: {
    processing_time?: number;
    model_version?: string;
    confidence_score?: number;
  };
}

export const ReportViewer: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1);

  useEffect(() => {
    if (reportId) {
      fetchReport();
    }
  }, [reportId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await medicalImagingApi.get(`/medical-imaging/imaging-reports/${reportId}`);
      setReport(response.data);
    } catch (err: any) {
      console.error('Error fetching report:', err);
      setError(err.response?.data?.detail || 'Failed to load report');
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = () => {
    if (!report) return;
    
    // Create a blob with the report content
    const content = `# Medical Imaging Report
    
**Report ID:** ${report.report_id}
**Date:** ${new Date(report.created_at).toLocaleString()}
**Study Type:** ${report.study_type}

---

${report.overall_analysis || 'No report content available'}

---

*Generated by Unified Medical AI System*`;
    
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `medical-report-${report.report_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success('Report downloaded successfully');
  };

  const handlePrintReport = () => {
    window.print();
  };

  const handleShareReport = async () => {
    if (!report) return;
    
    const shareUrl = `${window.location.origin}/reports/${report.report_id}`;
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Medical Imaging Report - ${report.report_id}`,
          text: 'View my medical imaging report',
          url: shareUrl,
        });
      } catch (err) {
        // User cancelled sharing
      }
    } else {
      // Fallback - copy to clipboard
      navigator.clipboard.writeText(shareUrl);
      toast.success('Report link copied to clipboard');
    }
  };

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 0.25, 0.5));
  };

  const handleFullscreen = () => {
    const elem = document.getElementById('report-content');
    if (elem?.requestFullscreen) {
      elem.requestFullscreen();
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
          <CircularProgress size={60} />
        </Box>
      </Container>
    );
  }

  if (error || !report) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert 
          severity="error" 
          action={
            <Button color="inherit" onClick={() => navigate('/reports')}>
              Go Back
            </Button>
          }
        >
          {error || 'Report not found'}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Fade in={true}>
        <Box>
          {/* Header */}
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
            <Box display="flex" alignItems="center" gap={2}>
              <IconButton onClick={() => navigate('/reports')} size="large">
                <ArrowBack />
              </IconButton>
              <Typography variant="h4" fontWeight="bold">
                Medical Imaging Report
              </Typography>
            </Box>
            
            <Stack direction="row" spacing={1}>
              <Tooltip title="Download Report">
                <IconButton onClick={handleDownloadReport}>
                  <Download />
                </IconButton>
              </Tooltip>
              <Tooltip title="Share Report">
                <IconButton onClick={handleShareReport}>
                  <Share />
                </IconButton>
              </Tooltip>
              <Tooltip title="Print Report">
                <IconButton onClick={handlePrintReport}>
                  <Print />
                </IconButton>
              </Tooltip>
              <Tooltip title="Fullscreen">
                <IconButton onClick={handleFullscreen}>
                  <Fullscreen />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>

          {/* Report Metadata */}
          <GlassCard sx={{ mb: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={3}>
                <MetaInfo>
                  <Assessment color="primary" />
                  <Box>
                    <Typography variant="caption" color="text.secondary">Report ID</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {report.report_id}
                    </Typography>
                  </Box>
                </MetaInfo>
              </Grid>
              
              <Grid item xs={12} md={3}>
                <MetaInfo>
                  <CalendarToday color="primary" />
                  <Box>
                    <Typography variant="caption" color="text.secondary">Created</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {new Date(report.created_at).toLocaleDateString()}
                    </Typography>
                  </Box>
                </MetaInfo>
              </Grid>
              
              <Grid item xs={12} md={3}>
                <MetaInfo>
                  <LocalHospital color="primary" />
                  <Box>
                    <Typography variant="caption" color="text.secondary">Study Type</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {report.study_type}
                    </Typography>
                  </Box>
                </MetaInfo>
              </Grid>
              
              {report.metadata?.confidence_score && (
                <Grid item xs={12} md={3}>
                  <MetaInfo>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Confidence</Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {(report.metadata.confidence_score * 100).toFixed(1)}%
                      </Typography>
                    </Box>
                  </MetaInfo>
                </Grid>
              )}
            </Grid>
          </GlassCard>

          {/* Main Report Content */}
          <Grid container spacing={3} id="report-content">
            {/* Images with Heatmap */}
            {((report.images && report.images.length > 0) || report.heatmap_data) && (
              <Grid item xs={12} md={6}>
                <GlassCard>
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Typography variant="h6">Medical Images</Typography>
                    <Stack direction="row" spacing={1}>
                      <Chip
                        icon={<Layers />}
                        label={showHeatmap ? 'Hide Heatmap' : 'Show Heatmap'}
                        onClick={() => setShowHeatmap(!showHeatmap)}
                        color={showHeatmap ? 'primary' : 'default'}
                        size="small"
                        clickable
                      />
                      <IconButton size="small" onClick={handleZoomIn}>
                        <ZoomIn />
                      </IconButton>
                      <IconButton size="small" onClick={handleZoomOut}>
                        <ZoomOut />
                      </IconButton>
                    </Stack>
                  </Box>
                  
                  <Box sx={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top left' }}>
                    {report.heatmap_data?.overlay ? (
                      <ImageContainer>
                        <Box
                          component="img"
                          src={`data:image/png;base64,${report.heatmap_data.overlay}`}
                          alt="Medical scan with heatmap overlay"
                          sx={{ width: '100%', height: 'auto' }}
                        />
                      </ImageContainer>
                    ) : report.images?.map((image, index) => (
                      <ImageContainer key={image.id || index}>
                        {image.url && (
                          <img src={image.url} alt={`Medical scan ${index + 1}`} />
                        )}
                        {showHeatmap && image.heatmap_data?.heatmap_overlay && (
                          <HeatmapOverlay
                            src={`data:image/png;base64,${image.heatmap_data.heatmap_overlay}`}
                            alt="Heatmap overlay"
                          />
                        )}
                      </ImageContainer>
                    ))}
                  </Box>
                  
                  {report.heatmap_data?.confidence && (
                    <Box mt={2}>
                      <Typography variant="caption" color="text.secondary">
                        Heatmap Confidence: {(report.heatmap_data.confidence * 100).toFixed(1)}%
                      </Typography>
                    </Box>
                  )}
                </GlassCard>
              </Grid>
            )}

            {/* Report Text */}
            <Grid item xs={12} md={(report.images && report.images.length > 0) || report.heatmap_data ? 6 : 12}>
              <GlassCard>
                <Typography variant="h6" gutterBottom>
                  Radiological Analysis
                </Typography>
                <Divider sx={{ mb: 2 }} />
                
                <MarkdownContainer>
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm, remarkBreaks]}
                    components={{
                      // Custom rendering for specific markdown elements
                      h1: ({ children }) => (
                        <Typography variant="h4" component="h1" gutterBottom>
                          {children}
                        </Typography>
                      ),
                      h2: ({ children }) => (
                        <Typography variant="h5" component="h2" gutterBottom>
                          {children}
                        </Typography>
                      ),
                      h3: ({ children }) => (
                        <Typography variant="h6" component="h3" gutterBottom>
                          {children}
                        </Typography>
                      ),
                      p: ({ children }) => (
                        <Typography variant="body1" paragraph>
                          {children}
                        </Typography>
                      ),
                    }}
                  >
                    {report.overall_analysis || report.images?.[0]?.analysis_text || 'No report content available'}
                  </ReactMarkdown>
                  
                  {report.key_findings && report.key_findings.length > 0 && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="h6" gutterBottom>
                        Key Findings
                      </Typography>
                      <Box component="ul" sx={{ pl: 2 }}>
                        {report.key_findings.map((finding, index) => (
                          <Typography key={index} component="li" variant="body1" paragraph>
                            {finding}
                          </Typography>
                        ))}
                      </Box>
                    </>
                  )}
                  
                  {report.recommendations && report.recommendations.length > 0 && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="h6" gutterBottom>
                        Recommendations
                      </Typography>
                      <Box component="ul" sx={{ pl: 2 }}>
                        {report.recommendations.map((recommendation, index) => (
                          <Typography key={index} component="li" variant="body1" paragraph>
                            {recommendation}
                          </Typography>
                        ))}
                      </Box>
                    </>
                  )}
                </MarkdownContainer>
              </GlassCard>
            </Grid>
          </Grid>

          {/* Processing Metadata */}
          {report.metadata && (
            <GlassCard sx={{ mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Processing Information
              </Typography>
              <Grid container spacing={2}>
                {report.metadata.processing_time && (
                  <Grid item xs={12} sm={4}>
                    <Typography variant="caption" color="text.secondary">
                      Processing Time
                    </Typography>
                    <Typography variant="body2">
                      {report.metadata.processing_time.toFixed(2)} seconds
                    </Typography>
                  </Grid>
                )}
                {report.metadata.model_version && (
                  <Grid item xs={12} sm={4}>
                    <Typography variant="caption" color="text.secondary">
                      Model Version
                    </Typography>
                    <Typography variant="body2">
                      {report.metadata.model_version}
                    </Typography>
                  </Grid>
                )}
                {report.updated_at && (
                  <Grid item xs={12} sm={4}>
                    <Typography variant="caption" color="text.secondary">
                      Last Updated
                    </Typography>
                    <Typography variant="body2">
                      {new Date(report.updated_at).toLocaleString()}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </GlassCard>
          )}
        </Box>
      </Fade>
    </Container>
  );
};

export default ReportViewer;