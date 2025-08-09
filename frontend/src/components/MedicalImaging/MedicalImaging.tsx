import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Typography,
  CircularProgress,
  Chip,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Alert,
  Snackbar,
  Zoom,
  Fade,
  Divider,
  IconButton,
  Fab,
  Button,
  Badge,
  Paper,
  Collapse,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Search as SearchIcon,
  Visibility as VisibilityIcon,
  Assessment as AssessmentIcon,
  LocalHospital as LocalHospitalIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  History as HistoryIcon,
  Chat as ChatIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useTheme, alpha } from '@mui/material/styles';
import { format } from 'date-fns';
import api from '../../api/axios';
import medicalImagingApi from '../../services/medicalImagingApi';
import WebSocketManager, { ConnectionState } from '../../utils/websocketManager';
import {
  MedicalImage,
  AnalysisResult,
  MedicalImagingProps,
  HeatmapData,
  SimilarReport,
  Finding,
  MedicalReport,
  Citation,
} from './types';
import {
  Container,
  UploadSection,
  ImageGrid,
  ImageCard,
  ImagePreview,
  ImageOverlay,
  StatusBadge,
  ResultsSection,
  FindingCard,
  HeatmapContainer,
  ActionButton,
  FloatingActionBar,
  SimilarReportCard,
  ProgressOverlay,
  DeleteButton,
} from './MedicalImaging.styles';
import EnhancedReportViewer from './components/EnhancedReportViewer';
import ReportChat from './components/ReportChat';
import PastReportsViewer from './components/PastReportsViewer';
import DownloadManager from './components/DownloadManager';
import WorkflowProgress from './components/WorkflowProgress';

const MedicalImaging: React.FC<MedicalImagingProps> = ({
  patientId,
  onAnalysisComplete,
  allowMultiple = true,
  acceptedFileTypes = ['image/jpeg', 'image/png', 'image/dicom', 'application/dicom'],
  maxFileSize = 50 * 1024 * 1024, // 50MB
}) => {
  const theme = useTheme();
  const [images, setImages] = useState<MedicalImage[]>([]);
  const [analysisResults, setAnalysisResults] = useState<Map<string, AnalysisResult>>(new Map());
  const [heatmaps, setHeatmaps] = useState<Map<string, HeatmapData>>(new Map());
  const [similarReports, setSimilarReports] = useState<SimilarReport[]>([]);
  const [selectedImage, setSelectedImage] = useState<MedicalImage | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [currentReport, setCurrentReport] = useState<MedicalReport | null>(null);
  const [showReportViewer, setShowReportViewer] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showPastReports, setShowPastReports] = useState(false);
  const [downloadDialogOpen, setDownloadDialogOpen] = useState(false);
  const [pastReportsCount, setPastReportsCount] = useState<number>(0);
  const [showWelcomeGuide, setShowWelcomeGuide] = useState(true);
  const wsManagerRef = useRef<WebSocketManager | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const pendingReportsRef = useRef<Set<string>>(new Set());
  const [chatPulse, setChatPulse] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState<{
    status: string;
    progress: number;
    message?: string;
    totalImages?: number;
    currentImage?: number;
  } | null>(null);
  const [showWorkflowProgress, setShowWorkflowProgress] = useState(false);
  const [alert, setAlert] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info',
  });

  const showAlert = useCallback((message: string, severity: 'success' | 'error' | 'info') => {
    setAlert({ open: true, message, severity });
  }, []);


  const detectImageType = (filename: string): MedicalImage['type'] => {
    const lower = filename.toLowerCase();
    if (lower.includes('ct')) return 'CT';
    if (lower.includes('mri')) return 'MRI';
    if (lower.includes('xray') || lower.includes('x-ray')) return 'X-ray';
    if (lower.includes('ultrasound') || lower.includes('us')) return 'Ultrasound';
    if (lower.includes('pet')) return 'PET';
    return 'Other';
  };

  const updateImageStatus = (imageId: string, status: MedicalImage['status'], progress?: number) => {
    setImages((prev) =>
      prev.map((img) =>
        img.id === imageId ? { ...img, status, ...(progress !== undefined && { progress }) } : img
      )
    );
  };

  // Helper functions for report generation
  const detectStudyType = (images: MedicalImage[]): string => {
    const types = images.map(img => img.type);
    const uniqueTypes = [...new Set(types)];
    return uniqueTypes.length === 1 ? uniqueTypes[0] : 'Multi-Modal Study';
  };
  
  const generateConclusion = (findings: Finding[]): string => {
    const critical = findings.filter(f => f.severity === 'critical' || f.severity === 'high').length;
    const abnormal = findings.filter(f => f.type === 'anomaly' || f.type === 'attention_required').length;
    
    if (critical > 0) {
      return `Critical findings detected requiring immediate attention. ${critical} high-priority issues identified.`;
    } else if (abnormal > 0) {
      return `${abnormal} abnormal findings detected. Further evaluation recommended.`;
    } else {
      return 'No significant abnormalities detected. Routine follow-up recommended.';
    }
  };
  
  const generateRecommendations = (findings: Finding[]): string[] => {
    const recommendations = new Set<string>();
    
    findings.forEach(finding => {
      if (finding.recommendations) {
        finding.recommendations.forEach(rec => recommendations.add(rec));
      }
    });
    
    return Array.from(recommendations);
  };
  
  const generateMarkdownReport = (images: MedicalImage[], findings: Finding[]): string => {
    let markdown = '# Medical Imaging Analysis Report\n\n';
    markdown += `Generated on: ${new Date().toLocaleDateString()}\n\n`;
    
    markdown += '## Images Analyzed\n\n';
    images.forEach((img, idx) => {
      markdown += `${idx + 1}. ${img.file.name} (${img.type})\n`;
    });
    
    markdown += '\n## Findings\n\n';
    findings.forEach((finding, idx) => {
      markdown += `### Finding ${idx + 1}\n`;
      markdown += `- **Description**: ${finding.description}\n`;
      markdown += `- **Type**: ${finding.type}\n`;
      markdown += `- **Severity**: ${finding.severity || 'N/A'}\n`;
      markdown += `- **Confidence**: ${Math.round(finding.confidence * 100)}%\n\n`;
    });
    
    return markdown;
  };

  // Generate combined report when all images are analyzed
  const checkAndGenerateReport = useCallback(async () => {
    const completedImages = images.filter((img) => img.status === 'completed');
    const totalImages = images.filter((img) => img.status !== 'error');
    
    if (completedImages.length === totalImages.length && completedImages.length > 0) {
      // All images analyzed, generate combined report
      const allFindings: Finding[] = [];
      const allCitations: Citation[] = [];
      let combinedSummary = '';
      
      completedImages.forEach((image) => {
        const result = analysisResults.get(image.id);
        if (result) {
          allFindings.push(...result.findings);
          combinedSummary += `\n\n## ${image.file.name}\n${result.summary}`;
        }
      });
      
      const report: MedicalReport = {
        id: `report-${Date.now()}`,
        patientId: patientId || 'unknown',
        patientName: 'Patient Name', // This should come from props or context
        createdAt: new Date(),
        updatedAt: new Date(),
        studyType: detectStudyType(images),
        images: completedImages,
        findings: allFindings,
        summary: combinedSummary,
        conclusion: generateConclusion(allFindings),
        recommendations: generateRecommendations(allFindings),
        markdownContent: generateMarkdownReport(completedImages, allFindings),
        citations: allCitations,
      };
      
      // Store the report for display in report viewer
      setCurrentReport(report);
      setShowReportViewer(true);
    }
  }, [images, analysisResults, patientId]);

  const uploadAndAnalyzeImageFunc = useCallback(async (image: MedicalImage) => {
    const formData = new FormData();
    formData.append('case_id', patientId || 'default-case');
    formData.append('image_type', image.type);
    formData.append('files', image.file);

    try {
      // Upload and analyze images
      updateImageStatus(image.id, 'uploading', 30);
      const response = await api.post<{
        report_id: string;
        status: string;
        images_processed: number;
        message: string;
      }>('/api/medical-imaging/upload-images', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const progress = progressEvent.total
            ? Math.round((progressEvent.loaded * 70) / progressEvent.total)
            : 0;
          updateImageStatus(image.id, 'uploading', progress);
        },
      });

      updateImageStatus(image.id, 'analyzing', 80);
      
      // Store the report ID in the image and add to pending reports
      image.reportId = response.data.report_id;
      pendingReportsRef.current.add(response.data.report_id);
      
      // Update image with report ID
      setImages((prev) => prev.map(img => 
        img.id === image.id ? { ...img, reportId: response.data.report_id } : img
      ));
      
      // If WebSocket is not connected, use polling as fallback
      if (!wsConnected) {
        console.log('WebSocket not connected, using polling fallback');
        pollForReportStatus(response.data.report_id);
      }
    } catch (error) {
      updateImageStatus(image.id, 'error');
      showAlert(`Failed to analyze ${image.file.name}`, 'error');
      console.error('Analysis error:', error);
      throw error;
    }
  }, [patientId, showAlert, analysisResults, onAnalysisComplete, checkAndGenerateReport]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const newImages: MedicalImage[] = acceptedFiles.map((file) => ({
      id: `${Date.now()}-${Math.random()}`,
      file,
      preview: URL.createObjectURL(file),
      type: detectImageType(file.name),
      uploadedAt: new Date(),
      status: 'uploading',
      progress: 0,
    }));

    setImages((prev) => (allowMultiple ? [...prev, ...newImages] : newImages));

    // Upload and analyze each image
    for (const image of newImages) {
      try {
        await uploadAndAnalyzeImageFunc(image);
      } catch (error) {
        console.error('Error processing image:', error);
        updateImageStatus(image.id, 'error');
        showAlert(`Failed to process ${image.file.name}`, 'error');
      }
    }
  }, [allowMultiple, uploadAndAnalyzeImageFunc, showAlert]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize: maxFileSize,
    multiple: allowMultiple,
  });

  const handleDeleteImage = (imageId: string) => {
    setImages((prev) => prev.filter((img) => img.id !== imageId));
    setAnalysisResults((prev) => {
      const newMap = new Map(prev);
      newMap.delete(imageId);
      return newMap;
    });
    setHeatmaps((prev) => {
      const newMap = new Map(prev);
      newMap.delete(imageId);
      return newMap;
    });
    showAlert('Image removed', 'info');
  };

  const handleViewImage = (image: MedicalImage) => {
    setSelectedImage(image);
    setViewDialogOpen(true);
  };


  const handleFindSimilar = async () => {
    try {
      const imageIds = Array.from(analysisResults.keys());
      // For now, use a placeholder since find-similar endpoint doesn't exist in backend
      // TODO: Implement this endpoint in the backend or use existing similar reports endpoint
      const response = { data: [] as SimilarReport[] };
      // const response = await medicalImagingApi.post<SimilarReport[]>('/medical-imaging/find-similar', {
      //   image_ids: imageIds,
      //   limit: 10,
      // });
      setSimilarReports(response.data);
      showAlert(`Found ${response.data.length} similar reports`, 'success');
    } catch (error) {
      showAlert('Failed to find similar reports', 'error');
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

  const completedAnalyses = useMemo(
    () => images.filter((img) => img.status === 'completed'),
    [images]
  );
  
  useEffect(() => {
    checkAndGenerateReport();
  }, [checkAndGenerateReport]);
  
  // Initialize WebSocket connection
  useEffect(() => {
    const initWebSocket = () => {
      if (!wsManagerRef.current) {
        wsManagerRef.current = new WebSocketManager({
          url: '/ws',
          onMessage: (data) => {
            console.log('Medical imaging WebSocket message:', data);
            
            // Handle medical imaging progress updates
            if (data.type === 'medical_imaging_progress' || data.type === 'medical_progress') {
              const { status, report_id, progress_percentage, message, total_images, current_image, progress } = data;
              
              // Update workflow status
              setWorkflowStatus({
                status: status,
                progress: progress || progress_percentage || 0,
                message: message,
                totalImages: total_images,
                currentImage: current_image,
              });
              
              // Show workflow progress for multi-step statuses
              if (['workflow_started', 'image_processing', 'literature_search', 'report_generation', 'quality_check', 'storing_results'].includes(status)) {
                setShowWorkflowProgress(true);
              }
              
              if (status === 'completed' && report_id && pendingReportsRef.current.has(report_id)) {
                // Report is ready, fetch it
                pendingReportsRef.current.delete(report_id);
                fetchReportWhenReady(report_id);
                setShowWorkflowProgress(false);
              } else if (status === 'error' && report_id) {
                pendingReportsRef.current.delete(report_id);
                showAlert(`Error processing report: ${message || 'Unknown error'}`, 'error');
                setShowWorkflowProgress(false);
                // Find and update the image status to error
                setImages(prevImages => {
                  const imageWithReport = prevImages.find(img => img.reportId === report_id);
                  if (imageWithReport) {
                    updateImageStatus(imageWithReport.id, 'error');
                  }
                  return prevImages;
                });
              } else if (status === 'processing' && progress_percentage) {
                // Update progress
                setImages(prevImages => {
                  const imageWithReport = prevImages.find(img => img.reportId === report_id);
                  if (imageWithReport) {
                    updateImageStatus(imageWithReport.id, 'analyzing', progress_percentage);
                  }
                  return prevImages;
                });
              }
            }
          },
          onOpen: () => {
            console.log('Medical imaging WebSocket connected');
            setWsConnected(true);
          },
          onClose: () => {
            console.log('Medical imaging WebSocket disconnected');
            setWsConnected(false);
          },
          onError: (error) => {
            console.error('Medical imaging WebSocket error:', error);
          },
          onStateChange: (state: ConnectionState) => {
            setWsConnected(state === ConnectionState.CONNECTED);
          },
        });
        
        // Connect WebSocket
        wsManagerRef.current.connect();
      }
    };
    
    initWebSocket();
    
    // Cleanup on unmount
    return () => {
      if (wsManagerRef.current) {
        wsManagerRef.current.disconnect();
        wsManagerRef.current = null;
      }
    };
  }, []);
  
  // Fetch report when ready
  const fetchReportWhenReady = async (reportId: string) => {
    try {
      const reportResponse = await medicalImagingApi.get<any>(`/medical-imaging/imaging-reports/${reportId}`);
      const report = reportResponse.data;
      
      if (report && report.images && report.images.length > 0) {
        const imageAnalysis = report.images[0];
        // Find the image with this report ID
        let imageWithReport: MedicalImage | undefined;
        setImages(prevImages => {
          imageWithReport = prevImages.find(img => img.reportId === reportId);
          return prevImages;
        });
        
        if (imageWithReport) {
          // Store reference to avoid TypeScript narrowing issues
          const foundImage = imageWithReport;
          
          // Create analysis result
          const analysisResult: AnalysisResult = {
            id: imageAnalysis.id || foundImage.id,
            imageId: foundImage.id,
            findings: imageAnalysis.findings || [],
            summary: imageAnalysis.analysis_text || '',
            confidence: 0.95,
            processingTime: imageAnalysis.processing_time || 0,
            generatedAt: new Date(),
          };
          
          // Process heatmap data
          if (imageAnalysis.heatmap_data) {
            const heatmapData: HeatmapData = {
              imageId: foundImage.id,
              heatmapUrl: `data:image/png;base64,${imageAnalysis.heatmap_data.heatmap_overlay}`,
              regions: imageAnalysis.heatmap_data.attention_regions?.map((region: any, idx: number) => ({
                id: `region-${idx}`,
                intensity: region.intensity / 255,
                label: `Region ${idx + 1}`,
                coordinates: {
                  x: region.center.x,
                  y: region.center.y,
                  radius: Math.max(region.bbox.width, region.bbox.height) / 2,
                },
              })) || [],
            };
            setHeatmaps((prev) => new Map(prev).set(foundImage.id, heatmapData));
          }
          
          setAnalysisResults((prev) => new Map(prev).set(foundImage.id, analysisResult));
          setCurrentReport(report);
          updateImageStatus(foundImage.id, 'completed', 100);
          showAlert(`Analysis completed for ${foundImage.file.name}`, 'success');
          
          // Refresh past reports count
          fetchPastReportsCount();
          
          // Check if all images are analyzed to generate combined report
          checkAndGenerateReport();
        }
      }
    } catch (error) {
      console.error('Error fetching report:', error);
      showAlert('Failed to fetch analysis report', 'error');
    }
  };
  
  // Fetch past reports count
  const fetchPastReportsCount = async () => {
    try {
      const endpoint = patientId
        ? `/medical-imaging/imaging-reports/patient/${patientId}`
        : '/medical-imaging/imaging-reports/recent';
      const response = await api.get(endpoint);
      // Handle different response formats
      const reportsData = patientId && response.data.reports 
        ? response.data.reports 
        : response.data;
      setPastReportsCount(Array.isArray(reportsData) ? reportsData.length : 0);
    } catch (error) {
      console.error('Error fetching past reports count:', error);
    }
  };
  
  // Fetch past reports count
  useEffect(() => {
    fetchPastReportsCount();
  }, [patientId]);
  
  // Polling fallback for report status
  const pollForReportStatus = async (reportId: string, attempts = 0) => {
    const maxAttempts = 30; // 30 attempts = 1 minute with 2-second intervals
    const pollInterval = 2000; // 2 seconds
    
    if (attempts >= maxAttempts) {
      pendingReportsRef.current.delete(reportId);
      showAlert('Report processing timed out. Please check past reports.', 'error');
      return;
    }
    
    try {
      const reportResponse = await medicalImagingApi.get<any>(`/medical-imaging/imaging-reports/${reportId}`);
      const report = reportResponse.data;
      
      if (report && report.status === 'completed' && report.images && report.images.length > 0) {
        // Report is ready, process it
        pendingReportsRef.current.delete(reportId);
        fetchReportWhenReady(reportId);
      } else if (report && report.status === 'error') {
        // Report failed
        pendingReportsRef.current.delete(reportId);
        showAlert('Report processing failed', 'error');
        setImages(prevImages => {
          const imageWithReport = prevImages.find(img => img.reportId === reportId);
          if (imageWithReport) {
            updateImageStatus(imageWithReport.id, 'error');
          }
          return prevImages;
        });
      } else {
        // Still processing, continue polling
        setTimeout(() => {
          pollForReportStatus(reportId, attempts + 1);
        }, pollInterval);
      }
    } catch (error) {
      // If 404, report might not be created yet, continue polling
      if ((error as any).response?.status === 404 && attempts < 5) {
        setTimeout(() => {
          pollForReportStatus(reportId, attempts + 1);
        }, pollInterval);
      } else {
        console.error('Error polling for report status:', error);
        pendingReportsRef.current.delete(reportId);
        showAlert('Failed to check report status', 'error');
      }
    }
  };
  
  // Start chat pulse animation when report is ready
  useEffect(() => {
    if (currentReport && !showChat) {
      setChatPulse(true);
      const timer = setTimeout(() => setChatPulse(false), 10000); // Stop after 10 seconds
      return () => clearTimeout(timer);
    }
  }, [currentReport, showChat]);

  return (
    <Container>
      {/* Welcome Guide */}
      <Collapse in={showWelcomeGuide && images.length === 0}>
        <Paper
          elevation={0}
          sx={{
            p: 3,
            mb: 3,
            backgroundColor: alpha(theme.palette.info.main, 0.05),
            border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
            borderRadius: 2,
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" gutterBottom sx={{ color: theme.palette.info.main }}>
                Welcome to Medical Imaging Analysis
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                Get AI-powered insights from your medical images in three simple steps:
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CloudUploadIcon color="primary" />
                    <Typography variant="body2">
                      <strong>1. Upload Images</strong> - Drag & drop or click to upload
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AssessmentIcon color="primary" />
                    <Typography variant="body2">
                      <strong>2. AI Analysis</strong> - Get instant medical insights
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ChatIcon color="primary" />
                    <Typography variant="body2">
                      <strong>3. Ask Questions</strong> - Chat with AI about results
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
              <Box sx={{ mt: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
                <Chip
                  icon={<HistoryIcon />}
                  label={`${pastReportsCount} past reports available`}
                  color="primary"
                  variant="outlined"
                  onClick={() => setShowPastReports(true)}
                  sx={{ cursor: 'pointer' }}
                />
                <Typography variant="caption" color="text.secondary">
                  Click to view your medical history
                </Typography>
              </Box>
            </Box>
            <IconButton size="small" onClick={() => setShowWelcomeGuide(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Paper>
      </Collapse>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Medical Imaging Analysis
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Badge badgeContent={pastReportsCount} color="primary" max={99}>
            <Button
              variant="contained"
              startIcon={<HistoryIcon />}
              onClick={() => setShowPastReports(true)}
              sx={{ 
                backgroundColor: theme.palette.primary.main,
                '&:hover': {
                  backgroundColor: theme.palette.primary.dark,
                }
              }}
            >
              Past Reports
            </Button>
          </Badge>
        </Box>
      </Box>

      <UploadSection {...getRootProps()}>
        <input {...getInputProps()} />
        <Box sx={{ textAlign: 'center' }}>
          <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {isDragActive ? 'Drop files here' : 'Drag & drop medical images'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            or click to select files (CT, MRI, X-ray, Ultrasound, PET)
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Maximum file size: {maxFileSize / (1024 * 1024)}MB
          </Typography>
        </Box>
      </UploadSection>

      {/* Workflow Progress Display */}
      {showWorkflowProgress && workflowStatus && (
        <Fade in>
          <Box sx={{ mt: 3 }}>
            <WorkflowProgress
              currentStatus={workflowStatus.status}
              progress={workflowStatus.progress}
              message={workflowStatus.message}
              totalImages={workflowStatus.totalImages}
              currentImage={workflowStatus.currentImage}
            />
          </Box>
        </Fade>
      )}

      {/* Recent Reports Preview - Only show if there are past reports */}
      {pastReportsCount > 0 && (
        <Box sx={{ mt: 4, mb: 4 }}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              backgroundColor: alpha(theme.palette.background.paper, 0.8),
              backdropFilter: 'blur(10px)',
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Recent Reports
                </Typography>
                <Chip 
                  label={`${pastReportsCount} total`} 
                  size="small" 
                  color="primary" 
                  variant="outlined" 
                />
              </Box>
              <Button
                variant="outlined"
                size="small"
                endIcon={<VisibilityIcon />}
                onClick={() => setShowPastReports(true)}
              >
                View All Reports
              </Button>
            </Box>
            <PastReportsViewer
              patientId={patientId}
              onReportSelect={(report) => {
                setCurrentReport(report);
                setShowReportViewer(true);
              }}
              maxReports={3}
              compact={true}
            />
          </Paper>
        </Box>
      )}

      {images.length > 0 && (
        <ImageGrid>
          {images.map((image) => {
            return (
              <Zoom in key={image.id}>
                <ImageCard>
                  <ImagePreview src={image.preview} alt={image.file.name} />
                  
                  <StatusBadge status={image.status}>
                    {image.status}
                  </StatusBadge>

                  <DeleteButton
                    size="small"
                    onClick={() => handleDeleteImage(image.id)}
                    disabled={image.status === 'uploading' || image.status === 'analyzing'}
                  >
                    <DeleteIcon fontSize="small" />
                  </DeleteButton>

                  {(image.status === 'uploading' || image.status === 'analyzing') && (
                    <ProgressOverlay>
                      <CircularProgress
                        variant="determinate"
                        value={image.progress}
                        size={60}
                        thickness={4}
                      />
                      <Typography variant="body2" sx={{ mt: 2 }}>
                        {image.status === 'uploading' ? 'Uploading...' : 'Analyzing...'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {image.progress}%
                      </Typography>
                    </ProgressOverlay>
                  )}

                  <ImageOverlay>
                    <Tooltip title="View Details">
                      <IconButton
                        color="primary"
                        onClick={() => handleViewImage(image)}
                        sx={{ backgroundColor: 'background.paper', mx: 1 }}
                      >
                        <VisibilityIcon />
                      </IconButton>
                    </Tooltip>
                  </ImageOverlay>

                  <Box sx={{ p: 2 }}>
                    <Typography variant="subtitle2" noWrap>
                      {image.file.name}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                      <Chip label={image.type} size="small" color="primary" variant="outlined" />
                      <Chip
                        label={format(image.uploadedAt, 'MMM dd, HH:mm')}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                </ImageCard>
              </Zoom>
            );
          })}
        </ImageGrid>
      )}

      {completedAnalyses.length > 0 && (
        <Fade in>
          <ResultsSection>
            <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
              Analysis Results
            </Typography>

            {completedAnalyses.map((image) => {
              const result = analysisResults.get(image.id);
              const heatmap = heatmaps.get(image.id);

              if (!result) return null;

              return (
                <Box key={image.id} sx={{ mb: 4 }}>
                  <Typography variant="h6" gutterBottom>
                    {image.file.name}
                  </Typography>
                  
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                        Summary
                      </Typography>
                      <Typography variant="body2" paragraph color="text.secondary">
                        {result.summary}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                        <Chip
                          icon={<AssessmentIcon />}
                          label={`Confidence: ${Math.round(result.confidence * 100)}%`}
                          color="primary"
                        />
                        <Chip
                          icon={<LocalHospitalIcon />}
                          label={`${result.findings.length} findings`}
                          color="secondary"
                        />
                      </Box>

                      <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600, mt: 3 }}>
                        Findings
                      </Typography>
                      {result.findings.map((finding) => (
                        <FindingCard key={finding.id} severity={finding.severity}>
                          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                            {getSeverityIcon(finding.severity)}
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="body2" gutterBottom>
                                {finding.description}
                              </Typography>
                              {finding.recommendations && finding.recommendations.length > 0 && (
                                <Box sx={{ mt: 1 }}>
                                  <Typography variant="caption" color="text.secondary">
                                    Recommendations:
                                  </Typography>
                                  <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                                    {finding.recommendations.map((rec, idx) => (
                                      <li key={idx}>
                                        <Typography variant="caption">{rec}</Typography>
                                      </li>
                                    ))}
                                  </ul>
                                </Box>
                              )}
                            </Box>
                          </Box>
                        </FindingCard>
                      ))}
                    </Grid>

                    <Grid item xs={12} md={6}>
                      {heatmap && (
                        <Box>
                          <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                            Heatmap Visualization
                          </Typography>
                          <HeatmapContainer>
                            <img 
                              src={heatmap.heatmapUrl} 
                              alt="Heatmap visualization"
                              style={{ width: '100%', height: 'auto', maxHeight: '400px', objectFit: 'contain' }}
                            />
                          </HeatmapContainer>
                          <Box sx={{ mt: 2 }}>
                            {heatmap.regions.map((region) => (
                              <Chip
                                key={region.id}
                                label={`${region.label}: ${Math.round(region.intensity * 100)}%`}
                                size="small"
                                sx={{ mr: 1, mb: 1 }}
                                color={region.intensity > 0.7 ? 'error' : 'default'}
                              />
                            ))}
                          </Box>
                        </Box>
                      )}
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 3 }} />
                </Box>
              );
            })}

            {similarReports.length > 0 && (
              <Box sx={{ mt: 4 }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  Similar Reports
                </Typography>
                <Grid container spacing={2}>
                  {similarReports.slice(0, 6).map((report) => (
                    <Grid item xs={12} sm={6} md={4} key={report.id}>
                      <SimilarReportCard>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          {report.thumbnailUrl && (
                            <img
                              src={report.thumbnailUrl}
                              alt="Report thumbnail"
                              style={{ width: 60, height: 60, borderRadius: 8, objectFit: 'cover' }}
                            />
                          )}
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="subtitle2">{report.diagnosis}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {format(new Date(report.date), 'MMM dd, yyyy')}
                            </Typography>
                            <Typography variant="body2" color="primary">
                              {Math.round(report.similarity * 100)}% match
                            </Typography>
                          </Box>
                        </Box>
                      </SimilarReportCard>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}
          </ResultsSection>
        </Fade>
      )}

      {completedAnalyses.length > 0 && (
        <FloatingActionBar>
          <ActionButton
            variant="contained"
            startIcon={<DownloadIcon />}
            onClick={() => setDownloadDialogOpen(true)}
          >
            Download Report
          </ActionButton>
          <ActionButton
            variant="outlined"
            startIcon={<VisibilityIcon />}
            onClick={() => setShowReportViewer(true)}
          >
            View Report
          </ActionButton>
          <ActionButton
            variant="outlined"
            startIcon={<SearchIcon />}
            onClick={handleFindSimilar}
          >
            Find Similar
          </ActionButton>
        </FloatingActionBar>
      )}
      
      {/* Chat Notification for New Reports */}
      {currentReport && !showChat && (
        <Snackbar
          open={chatPulse}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          sx={{ mb: 10, mr: 2 }}
        >
          <Alert 
            severity="info" 
            variant="filled"
            action={
              <Button 
                color="inherit" 
                size="small" 
                onClick={() => {
                  setShowChat(true);
                  setChatPulse(false);
                }}
              >
                Open Chat
              </Button>
            }
          >
            AI Assistant is ready to answer questions about your report!
          </Alert>
        </Snackbar>
      )}

      {/* Enhanced Report Viewer Dialog */}
      <Dialog
        open={showReportViewer && currentReport !== null}
        onClose={() => setShowReportViewer(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: 'transparent',
            boxShadow: 'none',
          },
        }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Medical Imaging Report</Typography>
            <IconButton onClick={() => setShowReportViewer(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {currentReport && <EnhancedReportViewer report={currentReport} />}
        </DialogContent>
      </Dialog>
      
      {/* Download Manager */}
      {currentReport && (
        <DownloadManager
          open={downloadDialogOpen}
          onClose={() => setDownloadDialogOpen(false)}
          report={currentReport}
          images={completedAnalyses}
          heatmaps={heatmaps}
        />
      )}
      
      {/* Report Chat */}
      {showChat && currentReport && (
        <ReportChat
          report={currentReport}
          position="right"
          onClose={() => setShowChat(false)}
        />
      )}
      
      {/* Past Reports Dialog */}
      <Dialog
        open={showPastReports}
        onClose={() => setShowPastReports(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Past Medical Reports</Typography>
            <IconButton onClick={() => setShowPastReports(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <PastReportsViewer
            patientId={patientId}
            onReportSelect={(report) => {
              setCurrentReport(report);
              setShowReportViewer(true);
              setShowPastReports(false);
            }}
          />
        </DialogContent>
      </Dialog>
      
      {/* Floating Action Buttons */}
      <Box sx={{ position: 'fixed', bottom: 20, right: 20, display: 'flex', gap: 2, zIndex: 1200 }}>
        <Tooltip title={`View ${pastReportsCount} Past Reports`} placement="left">
          <Badge badgeContent={pastReportsCount} color="error" overlap="circular">
            <Fab
              color="primary"
              onClick={() => setShowPastReports(true)}
              sx={{ 
                backgroundColor: alpha(theme.palette.primary.main, 0.9),
                '&:hover': {
                  backgroundColor: theme.palette.primary.main,
                  transform: 'scale(1.1)',
                },
                transition: 'all 0.3s ease',
              }}
            >
              <HistoryIcon />
            </Fab>
          </Badge>
        </Tooltip>
        {currentReport && (
          <Tooltip 
            title="Chat with AI Assistant about your report" 
            placement="left"
            arrow
          >
            <Fab
              color="secondary"
              onClick={() => setShowChat(!showChat)}
              sx={{ 
                backgroundColor: alpha(theme.palette.secondary.main, 0.9),
                '&:hover': {
                  backgroundColor: theme.palette.secondary.main,
                  transform: 'scale(1.1)',
                },
                transition: 'all 0.3s ease',
                animation: chatPulse ? 'pulse 2s infinite' : 'none',
                '@keyframes pulse': {
                  '0%': {
                    boxShadow: `0 0 0 0 ${alpha(theme.palette.secondary.main, 0.7)}`,
                  },
                  '70%': {
                    boxShadow: `0 0 0 10px ${alpha(theme.palette.secondary.main, 0)}`,
                  },
                  '100%': {
                    boxShadow: `0 0 0 0 ${alpha(theme.palette.secondary.main, 0)}`,
                  },
                },
              }}
            >
              <ChatIcon />
            </Fab>
          </Tooltip>
        )}
      </Box>

      <Dialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        {selectedImage && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="h6">{selectedImage.file.name}</Typography>
                <Chip label={selectedImage.type} color="primary" />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ textAlign: 'center' }}>
                <img
                  src={selectedImage.preview}
                  alt={selectedImage.file.name}
                  style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain' }}
                />
              </Box>
              {analysisResults.has(selectedImage.id) && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Analysis Details
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {analysisResults.get(selectedImage.id)?.summary}
                  </Typography>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <ActionButton onClick={() => setViewDialogOpen(false)}>Close</ActionButton>
            </DialogActions>
          </>
        )}
      </Dialog>

      <Snackbar
        open={alert.open}
        autoHideDuration={6000}
        onClose={() => setAlert({ ...alert, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        <Alert
          onClose={() => setAlert({ ...alert, open: false })}
          severity={alert.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {alert.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default MedicalImaging;