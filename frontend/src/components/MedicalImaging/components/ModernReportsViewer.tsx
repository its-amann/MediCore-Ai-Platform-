import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  InputAdornment,
  IconButton,
  Grid,
  Card,
  CardContent,
  CardMedia,
  CardActionArea,
  Chip,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  Skeleton,
  Alert,
  Pagination,
  Dialog,
  DialogTitle,
  DialogContent,
  Fade,
  Slide,
  Zoom,
  Avatar,
  LinearProgress,
  Stack,
  Badge,
  ToggleButton,
  ToggleButtonGroup,
  Collapse,
  useMediaQuery,
  Snackbar,
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import { useTheme, alpha, styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search as SearchIcon,
  LocalHospital as LocalHospitalIcon,
  Warning as WarningIcon,
  Description as DescriptionIcon,
  Visibility as VisibilityIcon,
  Download as DownloadIcon,
  Close as CloseIcon,
  GridView as GridViewIcon,
  ViewList as ListIcon,
  SmartToy as SmartToyIcon,
  AccessTime as AccessTimeIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Insights as InsightsIcon,
  ClearAll as ClearAllIcon,
  FilterAlt as FilterAltIcon,
  DateRange as DateRangeIcon,
  Category as CategoryIcon,
} from '@mui/icons-material';
// Date picker imports temporarily commented out due to version conflict
// import { DatePicker } from '@mui/x-date-pickers/DatePicker';
// import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
// import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format, isToday, isYesterday, isSameWeek, isSameMonth } from 'date-fns';
import { PastReportSummary, ReportFilter, MedicalReport } from '../types';
import EnhancedReportViewer from './EnhancedReportViewer';
import medicalImagingService from '../../../services/medicalImagingService';
import { useAuthStore } from '../../../store/authStore';

// Styled Components
const StyledCard = styled(Card)(({ theme }) => ({
  position: 'relative',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  background: `linear-gradient(135deg, ${alpha(theme.palette.background.paper, 0.95)} 0%, ${alpha(theme.palette.background.paper, 0.85)} 100%)`,
  backdropFilter: 'blur(20px)',
  border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
  borderRadius: theme.spacing(2),
  overflow: 'hidden',
  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    transform: 'translateY(-8px) scale(1.02)',
    boxShadow: `0 20px 40px ${alpha(theme.palette.common.black, 0.15)}`,
    border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
    '& .hover-overlay': {
      opacity: 1,
    },
    '& .card-media': {
      transform: 'scale(1.05)',
    },
  },
}));

const StyledChip = styled(Chip)(({ theme }) => ({
  backdropFilter: 'blur(10px)',
  background: alpha(theme.palette.background.paper, 0.7),
  border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  transition: 'all 0.3s ease',
  '&:hover': {
    background: alpha(theme.palette.background.paper, 0.9),
    transform: 'translateY(-2px)',
  },
}));

const FilterChip = styled(Chip)(({ theme }) => ({
  margin: theme.spacing(0.5),
  background: alpha(theme.palette.primary.main, 0.1),
  border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
  '&:hover': {
    background: alpha(theme.palette.primary.main, 0.2),
    border: `1px solid ${alpha(theme.palette.primary.main, 0.5)}`,
  },
}));

const GradientTypography = styled(Typography)(({ theme }) => ({
  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  color: 'transparent',
  fontWeight: 700,
}));

interface ExtendedReport extends PastReportSummary {
  aiModel?: string;
  confidenceScore?: number;
  aiInsights?: string[];
  isStarred?: boolean;
  processingTime?: number;
}

interface ModernReportsViewerProps {
  patientId?: string;
  onReportSelect?: (report: MedicalReport) => void;
  maxReports?: number;
  compact?: boolean;
}

const ModernReportsViewer: React.FC<ModernReportsViewerProps> = ({
  patientId,
  onReportSelect,
  maxReports = 50,
  compact = false,
}) => {
  const theme = useTheme();
  const [reports, setReports] = useState<ExtendedReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedReport, setSelectedReport] = useState<MedicalReport | null>(null);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);
  const [showError, setShowError] = useState(false);
  const hasInitiallyLoaded = useRef(false);
  const isFetching = useRef(false);
  
  // Filter state
  const [filter, setFilter] = useState<ReportFilter>({
    patientId,
    searchQuery: '',
    studyTypes: [],
    findingTypes: [],
    dateRange: undefined,
  });

  const { user } = useAuthStore();
  
  // Mock AI models for demonstration
  const AI_MODELS = ['GPT-4 Vision', 'Gemini Pro Vision', 'Medical AI', 'RadiologyNet', 'DiagnosticAI'];

  // Transform backend report to ExtendedReport format - useCallback to prevent recreating on every render
  const transformReportToExtended = useCallback((report: any): ExtendedReport => {
    const hasFindings = (report.key_findings?.length || 0) > 0;
    const criticalCount = report.key_findings?.filter((f: string) => 
      f.toLowerCase().includes('critical') || 
      f.toLowerCase().includes('urgent') ||
      f.toLowerCase().includes('severe')
    ).length || 0;
    
    return {
      id: report.report_id || report.id || 'unknown',
      patientId: report.patient_id || report.case_id || patientId || user?.user_id || 'unknown',
      patientName: report.patient_name || (user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() : 'Current Patient'),
      studyDate: new Date(report.created_at || report.studyDate || Date.now()),
      studyType: report.study_type || report.image_type || (report.images && report.images[0]?.image_type) || 'Medical Imaging',
      findingsCount: report.key_findings?.length || 0,
      criticalFindings: criticalCount,
      thumbnailUrl: report.thumbnail_url || `https://source.unsplash.com/400x300/?medical,xray,scan`,
      summary: report.clinical_impression || report.overall_analysis || report.summary ||
        (hasFindings ? 'Findings detected. Further analysis recommended.' : 'No significant abnormalities detected.'),
      aiModel: report.ai_model || 'Gemini Pro Vision',
      confidenceScore: report.confidence_score || 0.95,
      aiInsights: report.recommendations || report.key_findings || [],
      isStarred: false,
      processingTime: report.processing_time || 45,
    };
  }, [patientId, user]);

  // Fetch reports from backend
  const fetchReports = useCallback(async () => {
    // Prevent duplicate fetches
    if (isFetching.current) {
      return;
    }
    
    isFetching.current = true;
    setLoading(true);
    setError(null);
    
    try {
      // Apply filters
      const searchParams: any = {};
      if (filter.searchQuery) searchParams.query = filter.searchQuery;
      if (filter.patientId) searchParams.patientId = filter.patientId;
      if (filter.studyTypes?.length) searchParams.studyType = filter.studyTypes[0];
      if (filter.dateRange?.start) searchParams.startDate = filter.dateRange.start.toISOString();
      if (filter.dateRange?.end) searchParams.endDate = filter.dateRange.end.toISOString();
      
      // Fetch reports based on filters
      let fetchedReports: any[] = [];
      
      if (filter.searchQuery || Object.keys(searchParams).length > 1) {
        // Use search endpoint if there are filters
        fetchedReports = await medicalImagingService.searchReports(
          filter.searchQuery || '',
          searchParams,
          maxReports
        );
      } else {
        // Use recent reports endpoint for default view
        fetchedReports = await medicalImagingService.getRecentReports(
          maxReports,
          filter.studyTypes?.[0]
        );
      }
      
      // Transform reports to ExtendedReport format
      const transformedReports = fetchedReports.map(transformReportToExtended);
      
      // Calculate pagination
      const itemsPerPage = 12;
      const startIndex = (page - 1) * itemsPerPage;
      const endIndex = startIndex + itemsPerPage;
      
      setReports(transformedReports.slice(startIndex, endIndex));
      setTotalPages(Math.ceil(transformedReports.length / itemsPerPage));
      hasInitiallyLoaded.current = true;
      
    } catch (err: any) {
      console.error('Failed to fetch reports:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load reports. Please try again.');
      
      // If no reports found, set empty array
      if (err.response?.status === 404) {
        setReports([]);
        setError(null); // Don't show error for no reports
      }
      hasInitiallyLoaded.current = true;
    } finally {
      setLoading(false);
      isFetching.current = false;
    }
  }, [filter, page, maxReports, transformReportToExtended]);

  // Fetch reports only once on mount 
  useEffect(() => {
    if (!hasInitiallyLoaded.current) {
      fetchReports();
    }
  }, []); // Empty dependency array - only run once on mount
  
  // Separate effect for filter/page changes after initial load
  useEffect(() => {
    if (hasInitiallyLoaded.current) {
      const timer = setTimeout(() => {
        fetchReports();
      }, 500); // Debounce to prevent rapid fetches
      return () => clearTimeout(timer);
    }
  }, [filter.searchQuery, filter.studyTypes, page, fetchReports]);

  // Format date with relative time
  const formatReportDate = (date: Date) => {
    const reportDate = new Date(date);
    
    if (isToday(reportDate)) {
      return `Today, ${format(reportDate, 'h:mm a')}`;
    } else if (isYesterday(reportDate)) {
      return `Yesterday, ${format(reportDate, 'h:mm a')}`;
    } else if (isSameWeek(reportDate, new Date())) {
      return format(reportDate, 'EEEE, h:mm a');
    } else if (isSameMonth(reportDate, new Date())) {
      return format(reportDate, 'MMM d, h:mm a');
    } else {
      return format(reportDate, 'MMM d, yyyy');
    }
  };


  // Get confidence color
  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return theme.palette.success.main;
    if (score >= 0.7) return theme.palette.info.main;
    return theme.palette.warning.main;
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilter({ ...filter, searchQuery: event.target.value });
    setPage(1);
  };
  
  // Handle report selection and fetch full details
  const handleReportClick = async (report: ExtendedReport) => {
    try {
      // Fetch detailed report with all workflow data
      const fullReportData = await medicalImagingService.getReportDetail(report.id || 'unknown');
      
      // Transform the detailed report to MedicalReport format
      const fullReport: MedicalReport = {
        id: fullReportData.report_id || fullReportData.id,
        report_id: fullReportData.report_id || fullReportData.id,
        case_id: fullReportData.case_id,
        patientId: fullReportData.patient_info?.patient_id || fullReportData.patient_id,
        patientName: fullReportData.patient_info?.name || fullReportData.patient_name || 'Current Patient',
        patient_name: fullReportData.patient_info?.name || fullReportData.patient_name,
        createdAt: new Date(fullReportData.created_at || Date.now()),
        created_at: fullReportData.created_at,
        updatedAt: new Date(fullReportData.updated_at || fullReportData.created_at || Date.now()),
        updated_at: fullReportData.updated_at,
        studyType: fullReportData.study_info?.type || fullReportData.study_type || 'Medical Imaging',
        study_type: fullReportData.study_info?.type || fullReportData.study_type,
        studyDate: fullReportData.study_info?.date || fullReportData.study_date,
        study_date: fullReportData.study_info?.date || fullReportData.study_date,
        images: fullReportData.image_analyses?.map((img: any) => ({
          id: img.image_id,
          file: null as any,
          preview: img.heatmap_data?.original_image || '',
          type: img.image_type || 'Other' as any,
          uploadedAt: new Date(fullReportData.created_at || Date.now()),
          status: 'completed' as const,
        })) || [],
        findings: fullReportData.abnormalities_detected || fullReportData.findings || [],
        key_findings: fullReportData.key_findings || [],
        summary: fullReportData.overall_analysis || '',
        conclusion: fullReportData.clinical_impression,
        recommendations: fullReportData.recommendations || [],
        citations: fullReportData.citations || [],
        overall_analysis: fullReportData.overall_analysis,
        clinicalImpression: fullReportData.clinical_impression,
        clinical_impression: fullReportData.clinical_impression,
        severity: fullReportData.severity || 'low',
        final_report: fullReportData.final_report,
        literature_references: fullReportData.literature_references || [],
        quality_score: fullReportData.quality_score,
        abnormalities_detected: fullReportData.abnormalities_detected || [],
        heatmap_data: fullReportData.heatmap_data,
        status: fullReportData.status,
      };
      
      setSelectedReport(fullReport);
      setReportDialogOpen(true);
      
      if (onReportSelect) {
        onReportSelect(fullReport);
      }
    } catch (error) {
      console.error('Failed to fetch report details:', error);
      setError('Failed to load report details. Please try again.');
      setShowError(true);
    }
  };

  const handleViewModeChange = (_: any, newMode: 'grid' | 'list' | null) => {
    if (newMode !== null) {
      setViewMode(newMode);
    }
  };

  const renderReportCard = (report: ExtendedReport, index: number) => {
    const isHovered = hoveredCard === report.id;
    
    return (
      <Grid item xs={12} sm={viewMode === 'list' ? 12 : 6} md={viewMode === 'list' ? 12 : 4} key={report.id}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: index * 0.1 }}
          onMouseEnter={() => setHoveredCard(report.id)}
          onMouseLeave={() => setHoveredCard(null)}
        >
          <StyledCard>
            <Box
              className="hover-overlay"
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `linear-gradient(180deg, transparent 0%, ${alpha(theme.palette.primary.main, 0.1)} 100%)`,
                opacity: 0,
                transition: 'opacity 0.3s ease',
                pointerEvents: 'none',
                zIndex: 1,
              }}
            />
            
            <CardActionArea onClick={() => handleReportClick(report)} sx={{ flex: 1 }}>
              {viewMode === 'grid' && (
                <Box sx={{ position: 'relative', overflow: 'hidden' }}>
                  <CardMedia
                    component="img"
                    height="180"
                    image={report.thumbnailUrl}
                    alt={`${report.studyType} thumbnail`}
                    className="card-media"
                    sx={{
                      objectFit: 'cover',
                      transition: 'transform 0.4s ease',
                    }}
                  />
                  
                  {/* AI Badge */}
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 12,
                      right: 12,
                      display: 'flex',
                      gap: 1,
                    }}
                  >
                    <Fade in={true}>
                      <StyledChip
                        icon={<SmartToyIcon />}
                        label={report.aiModel}
                        size="small"
                        sx={{
                          background: alpha(theme.palette.background.paper, 0.9),
                          backdropFilter: 'blur(10px)',
                        }}
                      />
                    </Fade>
                  </Box>
                  
                  {/* Starred Badge */}
                  {report.isStarred && (
                    <IconButton
                      size="small"
                      sx={{
                        position: 'absolute',
                        top: 8,
                        left: 8,
                        background: alpha(theme.palette.background.paper, 0.9),
                        backdropFilter: 'blur(10px)',
                        '&:hover': {
                          background: alpha(theme.palette.warning.main, 0.2),
                        },
                      }}
                    >
                      <StarIcon sx={{ color: theme.palette.warning.main }} />
                    </IconButton>
                  )}
                </Box>
              )}
              
              <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box>
                    <Typography variant="h6" component="div" fontWeight={600}>
                      {report.studyType}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {report.patientName}
                    </Typography>
                  </Box>
                  
                  {report.criticalFindings > 0 && (
                    <Zoom in={true}>
                      <Badge badgeContent={report.criticalFindings} color="error">
                        <Avatar
                          sx={{
                            width: 36,
                            height: 36,
                            bgcolor: alpha(theme.palette.error.main, 0.1),
                          }}
                        >
                          <WarningIcon color="error" fontSize="small" />
                        </Avatar>
                      </Badge>
                    </Zoom>
                  )}
                </Box>
                
                {/* Date and Time Info */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <AccessTimeIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary">
                    {formatReportDate(report.studyDate)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mx: 1 }}>•</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {report.processingTime}s processing
                  </Typography>
                </Box>
                
                {/* AI Confidence Score */}
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      AI Confidence
                    </Typography>
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        color: getConfidenceColor(report.confidenceScore || 0),
                        fontWeight: 600,
                      }}
                    >
                      {((report.confidenceScore || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(report.confidenceScore || 0) * 100}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      backgroundColor: alpha(theme.palette.divider, 0.1),
                      '& .MuiLinearProgress-bar': {
                        background: `linear-gradient(90deg, ${getConfidenceColor(report.confidenceScore || 0)} 0%, ${alpha(getConfidenceColor(report.confidenceScore || 0), 0.6)} 100%)`,
                        borderRadius: 3,
                      },
                    }}
                  />
                </Box>
                
                {/* Findings Summary */}
                <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <StyledChip
                    icon={<DescriptionIcon />}
                    label={`${report.findingsCount} findings`}
                    size="small"
                    color={report.criticalFindings > 0 ? 'error' : 'success'}
                    variant="outlined"
                  />
                  {report.findingsCount > 0 && (
                    <StyledChip
                      icon={<InsightsIcon />}
                      label="AI Insights"
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  )}
                </Box>
                
                {/* Report Summary */}
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    flex: 1,
                    mb: 2,
                    lineHeight: 1.6,
                  }}
                >
                  {report.summary}
                </Typography>
                
                {/* AI Insights Preview */}
                {isHovered && report.aiInsights && report.aiInsights.length > 0 && (
                  <Fade in={isHovered}>
                    <Box
                      sx={{
                        p: 2,
                        mt: 2,
                        borderRadius: 2,
                        background: alpha(theme.palette.primary.main, 0.05),
                        border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
                      }}
                    >
                      <Typography variant="caption" fontWeight={600} color="primary" sx={{ mb: 1, display: 'block' }}>
                        AI Insights:
                      </Typography>
                      {report.aiInsights.slice(0, 2).map((insight, idx) => (
                        <Typography key={idx} variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                          • {insight}
                        </Typography>
                      ))}
                    </Box>
                  </Fade>
                )}
                
                {/* Action Buttons */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 'auto', pt: 2 }}>
                  <Button
                    size="small"
                    startIcon={<VisibilityIcon />}
                    sx={{
                      textTransform: 'none',
                      color: theme.palette.primary.main,
                      '&:hover': {
                        background: alpha(theme.palette.primary.main, 0.08),
                      },
                    }}
                  >
                    View Details
                  </Button>
                  
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="Download Report">
                      <IconButton
                        size="small"
                        onClick={async (e: React.MouseEvent) => {
                          e.stopPropagation();
                          try {
                            const blob = await medicalImagingService.downloadReport(report.id);
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `report_${report.id}.pdf`;
                            a.click();
                            URL.revokeObjectURL(url);
                          } catch (error) {
                            console.error('Failed to download report:', error);
                            setError('Failed to download report');
                            setShowError(true);
                          }
                        }}
                        sx={{
                          color: 'text.secondary',
                          '&:hover': {
                            color: theme.palette.primary.main,
                            background: alpha(theme.palette.primary.main, 0.08),
                          },
                        }}
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={report.isStarred ? "Unstar" : "Star"}>
                      <IconButton
                        size="small"
                        sx={{
                          color: report.isStarred ? theme.palette.warning.main : 'text.secondary',
                          '&:hover': {
                            color: theme.palette.warning.main,
                            background: alpha(theme.palette.warning.main, 0.08),
                          },
                        }}
                      >
                        {report.isStarred ? <StarIcon fontSize="small" /> : <StarBorderIcon fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
              </CardContent>
            </CardActionArea>
          </StyledCard>
        </motion.div>
      </Grid>
    );
  };

  return (
    // <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        {!compact && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Paper
              elevation={0}
              sx={{
                p: 4,
                mb: 4,
                background: `linear-gradient(135deg, ${alpha(theme.palette.background.paper, 0.95)} 0%, ${alpha(theme.palette.background.paper, 0.85)} 100%)`,
                backdropFilter: 'blur(20px)',
                border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                borderRadius: 3,
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box>
                  <GradientTypography variant="h4" gutterBottom>
                    Medical Imaging Reports
                  </GradientTypography>
                  <Typography variant="body1" color="text.secondary">
                    View and analyze your previous medical imaging reports with AI insights
                  </Typography>
                </Box>
                
                <ToggleButtonGroup
                  value={viewMode}
                  exclusive
                  onChange={handleViewModeChange}
                  size="small"
                  sx={{
                    background: alpha(theme.palette.background.default, 0.5),
                    borderRadius: 2,
                  }}
                >
                  <ToggleButton value="grid">
                    <Tooltip title="Grid View">
                      <GridViewIcon />
                    </Tooltip>
                  </ToggleButton>
                  <ToggleButton value="list">
                    <Tooltip title="List View">
                      <ListIcon />
                    </Tooltip>
                  </ToggleButton>
                </ToggleButtonGroup>
              </Box>
            
              {/* Search and Filter Bar */}
              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="Search by patient name, findings, AI insights, or keywords..."
                  value={filter.searchQuery}
                  onChange={handleSearchChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                    sx: {
                      borderRadius: 2,
                      background: alpha(theme.palette.background.default, 0.3),
                      '&:hover': {
                        background: alpha(theme.palette.background.default, 0.5),
                      },
                    },
                  }}
                />
                <Button
                  variant="contained"
                  startIcon={<FilterAltIcon />}
                  onClick={() => setShowFilters(!showFilters)}
                  sx={{
                    minWidth: 140,
                    borderRadius: 2,
                    background: showFilters 
                      ? `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`
                      : alpha(theme.palette.primary.main, 0.1),
                    color: showFilters ? 'white' : theme.palette.primary.main,
                    border: `1px solid ${alpha(theme.palette.primary.main, showFilters ? 0 : 0.3)}`,
                    boxShadow: showFilters ? theme.shadows[4] : 'none',
                    '&:hover': {
                      background: showFilters
                        ? `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.dark} 100%)`
                        : alpha(theme.palette.primary.main, 0.2),
                    },
                  }}
                >
                  Filters
                  {(filter.studyTypes?.length || filter.dateRange) && (
                    <Badge
                      badgeContent={
                        (filter.studyTypes?.length || 0) + 
                        (filter.dateRange ? 1 : 0)
                      }
                      color="error"
                      sx={{ ml: 2 }}
                    />
                  )}
                </Button>
              </Box>
              
              {/* Active Filters Display */}
              {(filter.studyTypes?.length || filter.dateRange || filter.searchQuery) && (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  {filter.searchQuery && (
                    <FilterChip
                      icon={<SearchIcon />}
                      label={`Search: ${filter.searchQuery}`}
                      onDelete={() => setFilter({ ...filter, searchQuery: '' })}
                    />
                  )}
                  {filter.studyTypes?.map((type) => (
                    <FilterChip
                      key={type}
                      icon={<CategoryIcon />}
                      label={type}
                      onDelete={() => setFilter({ 
                        ...filter, 
                        studyTypes: filter.studyTypes?.filter(t => t !== type) 
                      })}
                    />
                  ))}
                  {filter.dateRange && (
                    <FilterChip
                      icon={<DateRangeIcon />}
                      label="Date Range"
                      onDelete={() => setFilter({ ...filter, dateRange: undefined })}
                    />
                  )}
                  <Button
                    size="small"
                    startIcon={<ClearAllIcon />}
                    onClick={() => setFilter({ patientId, searchQuery: '', studyTypes: [], findingTypes: [], dateRange: undefined })}
                    sx={{ ml: 1 }}
                  >
                    Clear All
                  </Button>
                </Box>
              )}
              
              {/* Filters Panel */}
              <Collapse in={showFilters}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    mb: 3,
                    background: alpha(theme.palette.background.default, 0.3),
                    border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                    borderRadius: 2,
                  }}
                >
                  <Grid container spacing={3} alignItems="center">
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth>
                        <InputLabel>Study Types</InputLabel>
                        <Select
                          multiple
                          value={filter.studyTypes || []}
                          onChange={(e: SelectChangeEvent<string[]>) => 
                            setFilter({ ...filter, studyTypes: e.target.value as string[] })
                          }
                          renderValue={(selected: string[]) => (
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                              {selected.map((value) => (
                                <Chip key={value} label={value} size="small" />
                              ))}
                            </Box>
                          )}
                        >
                          {['CT Scan', 'MRI', 'X-Ray', 'Ultrasound', 'PET Scan'].map((type) => (
                            <MenuItem key={type} value={type}>
                              {type}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                      <TextField
                        label="Start Date"
                        type="date"
                        fullWidth
                        value={filter.dateRange?.start ? format(filter.dateRange.start, 'yyyy-MM-dd') : ''}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilter({
                          ...filter,
                          dateRange: e.target.value ? { 
                            start: new Date(e.target.value), 
                            end: filter.dateRange?.end 
                          } : undefined
                        })}
                        InputLabelProps={{
                          shrink: true,
                        }}
                      />
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                      <TextField
                        label="End Date"
                        type="date"
                        fullWidth
                        value={filter.dateRange?.end ? format(filter.dateRange.end, 'yyyy-MM-dd') : ''}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          if (!e.target.value) {
                            setFilter({
                              ...filter,
                              dateRange: filter.dateRange?.start ? { start: filter.dateRange.start } : undefined
                            });
                          } else {
                            setFilter({
                              ...filter,
                              dateRange: {
                                start: filter.dateRange?.start || new Date(),
                                end: new Date(e.target.value)
                              }
                            });
                          }
                        }}
                        InputLabelProps={{
                          shrink: true,
                        }}
                      />
                    </Grid>
                    
                    <Grid item xs={12} md={2}>
                      <Stack spacing={1}>
                        <FormControl size="small">
                          <InputLabel>AI Model</InputLabel>
                          <Select value="">
                            {AI_MODELS.map((model) => (
                              <MenuItem key={model} value={model}>
                                {model}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                        <FormControl size="small">
                          <InputLabel>Confidence</InputLabel>
                          <Select value="">
                            <MenuItem value="high">High (90%+)</MenuItem>
                            <MenuItem value="medium">Medium (70-90%)</MenuItem>
                            <MenuItem value="low">Low (&lt;70%)</MenuItem>
                          </Select>
                        </FormControl>
                      </Stack>
                    </Grid>
                  </Grid>
                </Paper>
              </Collapse>
            </Paper>
          </motion.div>
        )}
        
        {/* Results Grid */}
        {loading ? (
          <Grid container spacing={3}>
            {[...Array(6)].map((_, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Card sx={{ height: 400 }}>
                  <Skeleton variant="rectangular" height={180} />
                  <CardContent>
                    <Skeleton variant="text" width="60%" height={32} />
                    <Skeleton variant="text" width="40%" />
                    <Skeleton variant="rectangular" height={6} sx={{ my: 2, borderRadius: 3 }} />
                    <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                      <Skeleton variant="rounded" width={80} height={24} />
                      <Skeleton variant="rounded" width={80} height={24} />
                    </Box>
                    <Skeleton variant="text" />
                    <Skeleton variant="text" />
                    <Skeleton variant="text" width="70%" />
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : error ? (
          <Alert 
            severity="error" 
            sx={{ 
              mb: 3,
              borderRadius: 2,
              border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
            }}
          >
            {error}
          </Alert>
        ) : reports.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <Paper
              elevation={0}
              sx={{
                p: 8,
                textAlign: 'center',
                background: `linear-gradient(135deg, ${alpha(theme.palette.background.paper, 0.95)} 0%, ${alpha(theme.palette.background.paper, 0.85)} 100%)`,
                backdropFilter: 'blur(20px)',
                border: `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                borderRadius: 3,
              }}
            >
              <LocalHospitalIcon sx={{ fontSize: 80, color: 'text.secondary', mb: 3 }} />
              <Typography variant="h5" color="text.secondary" gutterBottom fontWeight={600}>
                No reports found
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Try adjusting your search criteria or filters
              </Typography>
              <Button
                variant="contained"
                startIcon={<ClearAllIcon />}
                onClick={() => setFilter({ patientId, searchQuery: '', studyTypes: [], findingTypes: [], dateRange: undefined })}
                sx={{
                  borderRadius: 2,
                  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                }}
              >
                Clear Filters
              </Button>
            </Paper>
          </motion.div>
        ) : (
          <>
            <Grid container spacing={3}>
              <AnimatePresence>
                {reports.map((report, index) => renderReportCard(report, index))}
              </AnimatePresence>
            </Grid>
            
            {totalPages > 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={(_: React.ChangeEvent<unknown>, value: number) => setPage(value)}
                  color="primary"
                  size="large"
                  sx={{
                    '& .MuiPaginationItem-root': {
                      borderRadius: 2,
                      border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                      backdropFilter: 'blur(10px)',
                      background: alpha(theme.palette.background.paper, 0.7),
                      '&:hover': {
                        background: alpha(theme.palette.primary.main, 0.1),
                      },
                      '&.Mui-selected': {
                        background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                        color: 'white',
                        border: 'none',
                        '&:hover': {
                          background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.dark} 100%)`,
                        },
                      },
                    },
                  }}
                />
              </Box>
            )}
          </>
        )}
        
        {/* Report Detail Modal */}
        <Dialog
          open={reportDialogOpen}
          onClose={() => setReportDialogOpen(false)}
          maxWidth="lg"
          fullWidth
          TransitionComponent={Slide}
          TransitionProps={{ direction: 'up' } as any}
          PaperProps={{
            sx: {
              borderRadius: 3,
              background: theme.palette.background.paper,
              overflow: 'hidden',
            },
          }}
        >
          {selectedReport && (
            <>
              <DialogTitle sx={{ p: 0 }}>
                <Box
                  sx={{
                    p: 3,
                    background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                    color: 'white',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <Box>
                    <Typography variant="h5" fontWeight={600}>
                      Medical Imaging Report
                    </Typography>
                    <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
                      {selectedReport.studyType} • {selectedReport.patientName}
                    </Typography>
                  </Box>
                  <IconButton
                    onClick={() => setReportDialogOpen(false)}
                    sx={{
                      color: 'white',
                      background: alpha(theme.palette.common.white, 0.1),
                      '&:hover': {
                        background: alpha(theme.palette.common.white, 0.2),
                      },
                    }}
                  >
                    <CloseIcon />
                  </IconButton>
                </Box>
              </DialogTitle>
              <DialogContent sx={{ p: 0 }}>
                <EnhancedReportViewer report={selectedReport} />
              </DialogContent>
            </>
          )}
        </Dialog>
        
        {/* Error Snackbar */}
        <Snackbar
          open={showError}
          autoHideDuration={6000}
          onClose={() => setShowError(false)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => setShowError(false)}
            severity="error"
            sx={{ 
              width: '100%',
              backgroundColor: alpha(theme.palette.error.main, 0.1),
              color: theme.palette.error.main,
              '& .MuiAlert-icon': { 
                color: theme.palette.error.main 
              }
            }}
          >
            {error}
          </Alert>
        </Snackbar>
      </Box>
    // </LocalizationProvider>
  );
};

export default ModernReportsViewer;