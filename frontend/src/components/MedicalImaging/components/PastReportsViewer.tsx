import React, { useState, useEffect, useCallback } from 'react';
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
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Search as SearchIcon,
  FilterList as FilterListIcon,
  CalendarToday as CalendarIcon,
  LocalHospital as LocalHospitalIcon,
  Warning as WarningIcon,
  Description as DescriptionIcon,
  Visibility as VisibilityIcon,
  Download as DownloadIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format } from 'date-fns';
import { PastReportSummary, ReportFilter, MedicalReport } from '../types';
import EnhancedReportViewer from './EnhancedReportViewer';
import api from '../../../api/axios';
import medicalImagingApi from '../../../services/medicalImagingApi';

interface PastReportsViewerProps {
  patientId?: string;
  onReportSelect?: (report: MedicalReport) => void;
  maxReports?: number;
  compact?: boolean;
}

const PastReportsViewer: React.FC<PastReportsViewerProps> = ({
  patientId,
  onReportSelect,
  maxReports = 50,
  compact = false,
}) => {
  const theme = useTheme();
  const [reports, setReports] = useState<PastReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedReport, setSelectedReport] = useState<MedicalReport | null>(null);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  
  // Filter state
  const [filter, setFilter] = useState<ReportFilter>({
    patientId,
    searchQuery: '',
    studyTypes: [],
    findingTypes: [],
    dateRange: undefined,
  });

  // Fetch reports
  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (filter.patientId) params.append('patient_id', filter.patientId);
      if (filter.searchQuery) params.append('search', filter.searchQuery);
      if (filter.studyTypes?.length) params.append('study_types', filter.studyTypes.join(','));
      if (filter.findingTypes?.length) params.append('finding_types', filter.findingTypes.join(','));
      if (filter.dateRange?.start) params.append('start_date', filter.dateRange.start.toISOString());
      if (filter.dateRange?.end) params.append('end_date', filter.dateRange.end.toISOString());
      params.append('page', page.toString());
      params.append('limit', '12');
      
      // Use the appropriate endpoint based on whether a patient ID is provided
      const endpoint = filter.patientId
        ? `/medical-imaging/imaging-reports/patient/${filter.patientId}?${params.toString()}`
        : `/medical-imaging/imaging-reports/recent?${params.toString()}`;
      
      const response = await api.get(endpoint);
      
      // Handle different response formats based on endpoint
      let allReports: PastReportSummary[] = [];
      if (filter.patientId && response.data.reports) {
        // Patient endpoint returns object with reports array
        allReports = response.data.reports;
      } else if (Array.isArray(response.data)) {
        // Recent endpoint returns array directly
        allReports = response.data;
      } else {
        console.error('Unexpected response format:', response.data);
        allReports = [];
      }
      const startIndex = (page - 1) * 12;
      const endIndex = startIndex + 12;
      const paginatedReports = allReports.slice(startIndex, endIndex);
      
      setReports(paginatedReports);
      setTotalPages(Math.ceil(allReports.length / 12));
    } catch (err) {
      setError('Failed to load past reports. Please try again.');
      console.error('Error fetching reports:', err);
    } finally {
      setLoading(false);
    }
  }, [filter, page]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Load full report details
  const loadFullReport = async (reportId: string) => {
    try {
      const response = await medicalImagingApi.get<MedicalReport>(`/medical-imaging/imaging-reports/${reportId}/detail`);
      setSelectedReport(response.data);
      setReportDialogOpen(true);
      onReportSelect?.(response.data);
    } catch (err) {
      setError('Failed to load report details.');
      console.error('Error loading report:', err);
    }
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilter({ ...filter, searchQuery: event.target.value });
    setPage(1);
  };

  const handleStudyTypeChange = (event: SelectChangeEvent<string[]>) => {
    setFilter({ ...filter, studyTypes: event.target.value as string[] });
    setPage(1);
  };

  const handleDateRangeChange = (field: 'start' | 'end', date: Date | null) => {
    setFilter({
      ...filter,
      dateRange: {
        ...filter.dateRange,
        [field]: date,
      } as any,
    });
    setPage(1);
  };

  const clearFilters = () => {
    setFilter({
      patientId,
      searchQuery: '',
      studyTypes: [],
      findingTypes: [],
      dateRange: undefined,
    });
    setPage(1);
  };

  const getSeverityColor = (criticalFindings: number) => {
    if (criticalFindings > 0) return theme.palette.error.main;
    return theme.palette.success.main;
  };

  const renderReportCard = (report: PastReportSummary) => (
    <Grid item xs={12} sm={6} md={4} key={report.id}>
      <Card
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: 'blur(10px)',
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          transition: 'all 0.3s ease',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: theme.shadows[8],
          },
        }}
      >
        <CardActionArea onClick={() => loadFullReport(report.id)} sx={{ flex: 1 }}>
          {report.thumbnailUrl ? (
            <CardMedia
              component="img"
              height="140"
              image={report.thumbnailUrl}
              alt={`${report.studyType} thumbnail`}
              sx={{ objectFit: 'cover' }}
            />
          ) : (
            <Box
              sx={{
                height: 140,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: alpha(theme.palette.primary.main, 0.1),
              }}
            >
              <LocalHospitalIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
            </Box>
          )}
          
          <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
              <Typography variant="h6" component="div" noWrap>
                {report.studyType}
              </Typography>
              {report.criticalFindings > 0 && (
                <Tooltip title={`${report.criticalFindings} critical findings`}>
                  <WarningIcon color="error" fontSize="small" />
                </Tooltip>
              )}
            </Box>
            
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {report.patientName}
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
              <Chip
                icon={<CalendarIcon />}
                label={format(new Date(report.studyDate), 'MMM dd, yyyy')}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<DescriptionIcon />}
                label={`${report.findingsCount} findings`}
                size="small"
                color={report.criticalFindings > 0 ? 'error' : 'success'}
                variant="outlined"
              />
            </Box>
            
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                flex: 1,
              }}
            >
              {report.summary}
            </Typography>
            
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2, gap: 1 }}>
              <Tooltip title="View Report">
                <IconButton size="small" color="primary">
                  <VisibilityIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Download Report">
                <IconButton size="small">
                  <DownloadIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </CardContent>
        </CardActionArea>
      </Card>
    </Grid>
  );

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        {!compact && (
          <Paper
            elevation={0}
            sx={{
              p: 3,
              mb: 3,
              backgroundColor: alpha(theme.palette.background.paper, 0.8),
              backdropFilter: 'blur(10px)',
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            }}
          >
            <Typography variant="h5" gutterBottom fontWeight={600}>
              Past Medical Reports
            </Typography>
          
          {/* Search Bar */}
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Search reports by patient name, findings, or keywords..."
              value={filter.searchQuery}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <Button
              variant="outlined"
              startIcon={<FilterListIcon />}
              onClick={() => setShowFilters(!showFilters)}
              sx={{ minWidth: 120 }}
            >
              Filters
              {(filter.studyTypes?.length || filter.dateRange) && (
                <Chip
                  label={
                    (filter.studyTypes?.length || 0) + 
                    (filter.dateRange ? 1 : 0)
                  }
                  size="small"
                  color="primary"
                  sx={{ ml: 1, height: 20 }}
                />
              )}
            </Button>
          </Box>
          
          {/* Filters */}
          {showFilters && (
            <Paper
              elevation={0}
              sx={{
                p: 2,
                mb: 3,
                backgroundColor: alpha(theme.palette.background.default, 0.5),
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              }}
            >
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Study Types</InputLabel>
                    <Select
                      multiple
                      value={filter.studyTypes || []}
                      onChange={handleStudyTypeChange}
                      renderValue={(selected: string[]) => selected.join(', ')}
                    >
                      {['CT', 'MRI', 'X-ray', 'Ultrasound', 'PET'].map((type) => (
                        <MenuItem key={type} value={type}>
                          {type}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} sm={3}>
                  <DatePicker
                    label="Start Date"
                    value={filter.dateRange?.start || null}
                    onChange={(date) => handleDateRangeChange('start', date)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        size: 'small',
                      },
                    }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={3}>
                  <DatePicker
                    label="End Date"
                    value={filter.dateRange?.end || null}
                    onChange={(date) => handleDateRangeChange('end', date)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        size: 'small',
                      },
                    }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={2}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={clearFilters}
                    size="small"
                  >
                    Clear
                  </Button>
                </Grid>
              </Grid>
            </Paper>
          )}
          </Paper>
        )}
        
        {/* Results */}
        {loading ? (
          <Grid container spacing={3}>
            {[...Array(6)].map((_, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Card>
                  <Skeleton variant="rectangular" height={140} />
                  <CardContent>
                    <Skeleton variant="text" width="60%" />
                    <Skeleton variant="text" width="80%" />
                    <Skeleton variant="text" width="100%" />
                    <Skeleton variant="text" width="100%" />
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : error ? (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        ) : reports.length === 0 ? (
          <Paper
            elevation={0}
            sx={{
              p: 6,
              textAlign: 'center',
              backgroundColor: alpha(theme.palette.background.paper, 0.8),
              backdropFilter: 'blur(10px)',
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            }}
          >
            <LocalHospitalIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No reports found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try adjusting your search criteria or filters
            </Typography>
          </Paper>
        ) : (
          <>
            <Grid container spacing={3}>
              {reports.map(renderReportCard)}
            </Grid>
            
            {totalPages > 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={(_: any, value: number) => setPage(value)}
                  color="primary"
                  size="large"
                />
              </Box>
            )}
          </>
        )}
        
        {/* Report Dialog */}
        <Dialog
          open={reportDialogOpen}
          onClose={() => setReportDialogOpen(false)}
          maxWidth="lg"
          fullWidth
          PaperProps={{
            sx: {
              backgroundColor: 'transparent',
              boxShadow: 'none',
            },
          }}
        >
          {selectedReport && (
            <>
              <DialogTitle>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="h6">Medical Report</Typography>
                  <IconButton onClick={() => setReportDialogOpen(false)}>
                    <CloseIcon />
                  </IconButton>
                </Box>
              </DialogTitle>
              <DialogContent>
                <EnhancedReportViewer report={selectedReport} />
              </DialogContent>
            </>
          )}
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};

export default PastReportsViewer;