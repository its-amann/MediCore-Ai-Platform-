import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  IconButton,
  Slider,
  Fab,
  Chip,
  LinearProgress,
  CircularProgress,
  Skeleton,
  Button,
  Menu,
  MenuItem,
  Collapse,
  Alert,
  Snackbar,
  Tabs,
  Tab,
  Paper,
} from '@mui/material';
import {
  CloudUpload,
  Close,
  GetApp,
  Visibility,
  ZoomIn,
  ZoomOut,
  Palette,
  GridView,
  ViewModule,
  Analytics,
  AutoFixHigh,
  Biotech,
  Psychology,
  MoreVert,
  Share,
  Print,
  Fullscreen,
  PhotoLibrary,
  CameraAlt,
  Speed,
  ThermostatAuto,
  Description,
  LocalHospital,
  Science,
  LibraryBooks,
  History,
  PlayArrow,
  CloudUploadOutlined,
  AssessmentOutlined,
} from '@mui/icons-material';
import { motion, AnimatePresence, useAnimation } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import CountUp from 'react-countup';
import { styled, keyframes } from '@mui/material/styles';
import confetti from 'canvas-confetti';
import { v4 as uuidv4 } from 'uuid';
import medicalImagingService from '../../services/medicalImagingService';
import WorkflowProgress from './WorkflowProgress';
import ModernReportsViewer from './components/ModernReportsViewer';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
// import Divider from '@mui/material/Divider'; // Unused
// import Grid from '@mui/material/Grid'; // Unused
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Link from '@mui/material/Link';

// Type definitions
interface MedicalReport {
  report_id: string;
  case_id?: string;
  created_at?: string;
  status?: string;
  clinical_impression?: string;
  key_findings?: string[];
  recommendations?: string[];
  patient_name?: string;
  study_type?: string;
  study_date?: string;
}

// Styled Components
const GlassContainer = styled(Box)(({ theme }) => ({
  background: 'rgba(255, 255, 255, 0.1)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  borderRadius: '24px',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
  padding: theme.spacing(3),
  position: 'relative',
  overflow: 'hidden',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)',
    pointerEvents: 'none',
  },
}));

const float = keyframes`
  0% { transform: translateY(0px) rotate(0deg); }
  33% { transform: translateY(-20px) rotate(1deg); }
  66% { transform: translateY(10px) rotate(-1deg); }
  100% { transform: translateY(0px) rotate(0deg); }
`;

const pulse = keyframes`
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
`;

// const ripple = keyframes`
//   0% { transform: scale(0); opacity: 1; }
//   100% { transform: scale(4); opacity: 0; }
// `; // Unused

const NeumorphicButton = styled(Button)(({ theme }) => ({
  background: 'linear-gradient(145deg, #e6e9fc, #f7faff)',
  boxShadow: '20px 20px 60px #d1d5e8, -20px -20px 60px #ffffff',
  borderRadius: '15px',
  padding: '12px 24px',
  transition: 'all 0.3s ease',
  '&:hover': {
    boxShadow: '5px 5px 20px #d1d5e8, -5px -5px 20px #ffffff',
    transform: 'translateY(-2px)',
  },
  '&:active': {
    boxShadow: 'inset 5px 5px 10px #d1d5e8, inset -5px -5px 10px #ffffff',
  },
}));

const FloatingActionButton = styled(Fab)(({ theme }) => ({
  position: 'fixed',
  animation: `${float} 6s ease-in-out infinite`,
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: 'white',
  '&:hover': {
    background: 'linear-gradient(135deg, #764ba2 0%, #667eea 100%)',
  },
}));

const ParticleCanvas = styled('canvas')({
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  pointerEvents: 'none',
  zIndex: 1,
});

interface ImageData {
  id: string;
  file: File;
  preview: string;
  analysis?: AnalysisResult;
  uploadProgress: number;
  isAnalyzing: boolean;
  type?: string; // Add type property for compatibility
}

interface AnalysisResult {
  diagnosis: string;
  confidence: number;
  heatmap?: string;
  heatmapData?: {
    original_image: string;
    heatmap_overlay: string;
    heatmap_only: string;
    attention_regions: any[];
  };
  findings: Finding[];
  statistics: Statistics;
  groqFallback?: boolean;
  fullReport?: {
    technical_details?: {
      model_used?: string;
      processing_pipeline?: string[];
      confidence_scores?: Record<string, number>;
    };
  };
}

interface Finding {
  type: string;
  severity: 'low' | 'medium' | 'high';
  location: string;
  description: string;
}

interface Statistics {
  processingTime: number;
  accuracy: number;
  regionsAnalyzed: number;
}

interface HeatmapSettings {
  intensity: number;
  colorScheme: 'thermal' | 'medical' | 'custom';
  opacity: number;
  showRegions: boolean;
}

const MedicalImagingModern: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const [images, setImages] = useState<ImageData[]>([]);
  const [selectedImage, setSelectedImage] = useState<ImageData | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'masonry'>('grid');
  const [heatmapSettings, setHeatmapSettings] = useState<HeatmapSettings>({
    intensity: 50,
    colorScheme: 'thermal',
    opacity: 70,
    showRegions: true,
  });
  const [showHeatmap] = useState(false); // setShowHeatmap unused but may be needed for future functionality
  const [showOriginal, setShowOriginal] = useState(true);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [showError, setShowError] = useState(false);
  const [currentCaseId] = useState<string>(uuidv4());
  // const [recentReports, setRecentReports] = useState<any[]>([]); // TODO: Implement recent reports feature
  const [showFullReport, setShowFullReport] = useState(false);
  const [showWorkflowProgress, setShowWorkflowProgress] = useState(false);
  const [activeWorkflowCaseId, setActiveWorkflowCaseId] = useState<string | null>(null);
  // Processing details can be shown later if needed
  // Current report state can be added when needed
  const [isUploadingImages, setIsUploadingImages] = useState(false);
  const [previousReports, setPreviousReports] = useState<MedicalReport[]>([]);
  const [showPreviousReports, setShowPreviousReports] = useState(false);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particleAnimationRef = useRef<number | null>(null);
  const controls = useAnimation();

  // Start analysis function
  const startAnalysis = useCallback(async () => {
    if (images.length === 0) {
      setError('Please upload at least one image before starting analysis');
      setShowError(true);
      return;
    }

    setIsUploadingImages(true);
    
    try {
      // Update all images to show analyzing state
      setImages((prev) =>
        prev.map((img) => ({ ...img, isAnalyzing: true }))
      );
      
      // Extract files from images
      const files = images.map(img => img.file);
      
      // Call the actual backend API to analyze images
      const imageType = 'xray'; // Default to X-ray for now
      const useTemporal = false; // Use direct mode for now
      
      const result = await medicalImagingService.analyzeImages(
        files,
        currentCaseId,
        imageType,
        useTemporal
      );
      
      // Use the workflow_id returned by backend for tracking workflow progress
      if (result.workflow_id) {
        setActiveWorkflowCaseId(result.workflow_id);
        setShowWorkflowProgress(true);
      } else if (result.report_id) {
        // Fallback to report_id if workflow_id not available
        setActiveWorkflowCaseId(result.report_id);
        setShowWorkflowProgress(true);
      } else if (result.case_id) {
        // Use case_id as last resort
        setActiveWorkflowCaseId(result.case_id);
        setShowWorkflowProgress(true);
      } else {
        // Don't show workflow progress without a valid ID
        setError('No workflow ID received from server');
        setShowError(true);
      }
      
    } catch (err: any) {
      console.error('Error starting analysis:', err);
      setError(err.message || 'Failed to start analysis');
      setShowWorkflowProgress(false);
      setActiveWorkflowCaseId(null);
      setShowError(true);
      
      // Reset images to not analyzing state
      setImages((prev) =>
        prev.map((img) => ({ ...img, isAnalyzing: false }))
      );
    } finally {
      setIsUploadingImages(false);
    }
  }, [images, currentCaseId]);

  // Load previous reports
  const loadPreviousReports = useCallback(async () => {
    try {
      const reports = await medicalImagingService.getRecentReports();
      setPreviousReports(reports || []);
    } catch (error) {
      console.error('Failed to load previous reports:', error);
    }
  }, []);

  // Particle effect for upload area
  // Handle workflow completion
  const handleWorkflowComplete = useCallback(async (result: any) => {
    console.log('Workflow completed:', result);
    
    // If we have a report_id, navigate to the reports page
    if (result.report_id) {
      try {
        // Fetch the full report first to ensure it's available
        const fullReport = await medicalImagingService.getReport(result.report_id);
        console.log('Full report fetched:', fullReport);
        
        // Navigate to the reports page with the report ID in the URL
        // This makes it easier to share and bookmark specific reports
        navigate(`/reports?reportId=${result.report_id}`);
      } catch (error) {
        console.error('Failed to fetch full report:', error);
        // Still navigate to reports page even if fetch fails
        navigate('/reports');
      }
    } else {
      // If no report_id, still try to navigate to reports
      console.warn('No report_id in workflow result, navigating to reports anyway');
      navigate('/reports');
      
      // Trigger success animation
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#6366f1', '#8b5cf6', '#10b981'],
      });
      
      // Show success notification
      setError('Analysis completed successfully!');
      setShowError(true);
    }
    
    // Hide workflow progress after a delay
    setTimeout(() => {
      setShowWorkflowProgress(false);
      setActiveWorkflowCaseId(null);
      setIsUploadingImages(false);
    }, 3000);
  }, [navigate]);
  
  const createParticles = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const particles: any[] = [];
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        size: Math.random() * 3 + 1,
        opacity: Math.random() * 0.5 + 0.5,
      });
    }
    
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach((particle) => {
        particle.x += particle.vx;
        particle.y += particle.vy;
        
        if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;
        
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(99, 102, 241, ${particle.opacity})`;
        ctx.fill();
      });
      
      particleAnimationRef.current = requestAnimationFrame(animate);
    };
    
    animate();
  }, []);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const newImages: ImageData[] = acceptedFiles.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      preview: URL.createObjectURL(file),
      uploadProgress: 100, // Set to 100 since upload is complete
      isAnalyzing: false, // Will be set to true when analysis starts
    }));
    
    setImages((prev) => [...prev, ...newImages]);
    
    // Trigger confetti
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#6366f1', '#8b5cf6', '#ec4899'],
    });
  }, []);


  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.dcm'],
    },
    multiple: true,
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas && isDragActive) {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      createParticles();
    } else if (particleAnimationRef.current) {
      cancelAnimationFrame(particleAnimationRef.current);
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx?.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
    
    return () => {
      if (particleAnimationRef.current) {
        cancelAnimationFrame(particleAnimationRef.current);
      }
    };
  }, [isDragActive, createParticles]);

  const handleImageClick = (image: ImageData) => {
    setSelectedImage(image);
    controls.start({
      scale: [0.8, 1],
      opacity: [0, 1],
      transition: { duration: 0.3 },
    });
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const renderUploadArea = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <GlassContainer
        {...getRootProps()}
        sx={{
          position: 'relative',
          minHeight: 300,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transform: isDragActive ? 'perspective(1000px) rotateX(5deg)' : 'none',
          transition: 'all 0.3s ease',
          border: isDragActive
            ? '2px dashed rgba(99, 102, 241, 0.8)'
            : '2px dashed rgba(255, 255, 255, 0.3)',
          '&:hover': {
            borderColor: 'rgba(99, 102, 241, 0.6)',
            transform: 'translateY(-4px)',
            boxShadow: '0 12px 40px 0 rgba(31, 38, 135, 0.45)',
          },
        }}
      >
        <ParticleCanvas ref={canvasRef} />
        <input {...getInputProps()} />
        
        <motion.div
          animate={{
            scale: isDragActive ? 1.1 : 1,
            rotate: isDragActive ? 5 : 0,
          }}
          transition={{ type: 'spring', stiffness: 300 }}
        >
          <CloudUpload
            sx={{
              fontSize: 80,
              color: 'rgba(99, 102, 241, 0.8)',
              mb: 2,
              filter: 'drop-shadow(0 4px 8px rgba(99, 102, 241, 0.3))',
            }}
          />
        </motion.div>
        
        <Typography
          variant="h5"
          sx={{
            color: 'rgba(255, 255, 255, 0.9)',
            fontWeight: 600,
            mb: 1,
            textAlign: 'center',
          }}
        >
          {isDragActive ? 'Drop your medical images here' : 'Upload Medical Images'}
        </Typography>
        
        <Typography
          variant="body2"
          sx={{
            color: 'rgba(255, 255, 255, 0.7)',
            textAlign: 'center',
            maxWidth: 400,
          }}
        >
          Drag & drop DICOM, X-ray, MRI, or CT scan images here, or click to browse
        </Typography>
        
        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Chip
            icon={<CameraAlt />}
            label="DICOM"
            sx={{
              background: 'rgba(99, 102, 241, 0.2)',
              color: 'white',
              backdropFilter: 'blur(10px)',
            }}
          />
          <Chip
            icon={<Biotech />}
            label="X-Ray"
            sx={{
              background: 'rgba(139, 92, 246, 0.2)',
              color: 'white',
              backdropFilter: 'blur(10px)',
            }}
          />
          <Chip
            icon={<Psychology />}
            label="MRI/CT"
            sx={{
              background: 'rgba(236, 72, 153, 0.2)',
              color: 'white',
              backdropFilter: 'blur(10px)',
            }}
          />
        </Box>
      </GlassContainer>
    </motion.div>
  );

  const renderImageGallery = () => (
    <AnimatePresence>
      {images.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography
              variant="h6"
              sx={{
                color: 'rgba(255, 255, 255, 0.9)',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <PhotoLibrary />
              Image Gallery
              <Chip
                label={images.length}
                size="small"
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                }}
              />
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              {images.length > 0 && !showWorkflowProgress && (
                <NeumorphicButton
                  startIcon={<PlayArrow />}
                  onClick={startAnalysis}
                  disabled={isUploadingImages}
                  sx={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #764ba2 0%, #667eea 100%)',
                    },
                  }}
                >
                  Start Analysis
                </NeumorphicButton>
              )}
              <IconButton
                onClick={() => {
                  loadPreviousReports();
                  setShowPreviousReports(!showPreviousReports);
                }}
                sx={{
                  color: showPreviousReports ? '#667eea' : 'rgba(255, 255, 255, 0.5)',
                }}
                title="View Previous Reports"
              >
                <History />
              </IconButton>
              <IconButton
                onClick={() => setViewMode('grid')}
                sx={{
                  color: viewMode === 'grid' ? '#667eea' : 'rgba(255, 255, 255, 0.5)',
                }}
              >
                <GridView />
              </IconButton>
              <IconButton
                onClick={() => setViewMode('masonry')}
                sx={{
                  color: viewMode === 'masonry' ? '#667eea' : 'rgba(255, 255, 255, 0.5)',
                }}
              >
                <ViewModule />
              </IconButton>
            </Box>
          </Box>
          
          <Box
            sx={{
              display: viewMode === 'grid' ? 'grid' : 'flex',
              gridTemplateColumns: viewMode === 'grid' ? 'repeat(auto-fill, minmax(300px, 1fr))' : undefined,
              flexWrap: viewMode === 'masonry' ? 'wrap' : undefined,
              gap: 3,
            }}
          >
            {images.map((image, index) => {
              // Add null check for image object
              if (!image) return null;
              
              return (
              <motion.div
                key={image.id}
                initial={{ opacity: 0, scale: 0.8, rotateY: -180 }}
                animate={{ opacity: 1, scale: 1, rotateY: 0 }}
                exit={{ opacity: 0, scale: 0.8, rotateY: 180 }}
                transition={{
                  duration: 0.6,
                  delay: index * 0.1,
                  type: 'spring',
                  stiffness: 100,
                }}
                whileHover={{ y: -8, transition: { duration: 0.2 } }}
                style={{
                  flex: viewMode === 'masonry' ? `1 1 ${300 + Math.random() * 100}px` : undefined,
                }}
              >
                <GlassContainer
                  sx={{
                    p: 2,
                    cursor: 'pointer',
                    position: 'relative',
                    overflow: 'hidden',
                    '&:hover': {
                      '& .image-overlay': {
                        opacity: 1,
                      },
                      '& img': {
                        transform: 'scale(1.05)',
                      },
                    },
                  }}
                  onClick={() => handleImageClick(image)}
                >
                  {image?.uploadProgress < 100 ? (
                    <Box
                      sx={{
                        height: 250,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                        <CircularProgress
                          variant="determinate"
                          value={image?.uploadProgress || 0}
                          size={80}
                          thickness={4}
                          sx={{
                            color: 'rgba(99, 102, 241, 0.8)',
                            '& .MuiCircularProgress-circle': {
                              strokeLinecap: 'round',
                            },
                          }}
                        />
                        <Box
                          sx={{
                            top: 0,
                            left: 0,
                            bottom: 0,
                            right: 0,
                            position: 'absolute',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Typography
                            variant="caption"
                            component="div"
                            sx={{ color: 'rgba(255, 255, 255, 0.9)' }}
                          >
                            {`${Math.round(image?.uploadProgress || 0)}%`}
                          </Typography>
                        </Box>
                      </Box>
                      <Typography
                        variant="body2"
                        sx={{ mt: 2, color: 'rgba(255, 255, 255, 0.7)' }}
                      >
                        Uploading...
                      </Typography>
                    </Box>
                  ) : image?.isAnalyzing ? (
                    <Box
                      sx={{
                        height: 250,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <motion.div
                        animate={{
                          rotate: 360,
                        }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                          ease: 'linear',
                        }}
                      >
                        <Analytics sx={{ fontSize: 60, color: 'rgba(99, 102, 241, 0.8)' }} />
                      </motion.div>
                      <Typography
                        variant="body2"
                        sx={{ mt: 2, color: 'rgba(255, 255, 255, 0.7)' }}
                      >
                        Analyzing image...
                      </Typography>
                      <Box sx={{ width: '100%', mt: 2 }}>
                        <LinearProgress
                          sx={{
                            height: 4,
                            borderRadius: 2,
                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                            '& .MuiLinearProgress-bar': {
                              borderRadius: 2,
                              background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                            },
                          }}
                        />
                      </Box>
                    </Box>
                  ) : (
                    <>
                      <Box
                        sx={{
                          position: 'relative',
                          overflow: 'hidden',
                          borderRadius: 2,
                          height: viewMode === 'masonry' ? 'auto' : 250,
                        }}
                      >
                        <img
                          src={image?.preview || ''}
                          alt="Medical scan"
                          style={{
                            width: '100%',
                            height: viewMode === 'masonry' ? 'auto' : '100%',
                            objectFit: viewMode === 'masonry' ? 'contain' : 'cover',
                            transition: 'transform 0.3s ease',
                          }}
                        />
                        <Box
                          className="image-overlay"
                          sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 60%)',
                            opacity: 0,
                            transition: 'opacity 0.3s ease',
                            display: 'flex',
                            alignItems: 'flex-end',
                            p: 2,
                          }}
                        >
                          <Box>
                            <Typography
                              variant="body2"
                              sx={{ color: 'white', fontWeight: 600 }}
                            >
                              {image?.file?.name || 'Unnamed Image'}
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{ color: 'rgba(255, 255, 255, 0.8)' }}
                            >
                              Click to view analysis
                            </Typography>
                          </Box>
                        </Box>
                      </Box>
                      
                      {image?.analysis && (
                        <Box sx={{ mt: 2 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography
                              variant="caption"
                              sx={{ color: 'rgba(255, 255, 255, 0.7)' }}
                            >
                              Confidence Score
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{ color: '#667eea', fontWeight: 600 }}
                            >
                              <CountUp
                                end={(image?.analysis?.confidence || 0) * 100}
                                duration={2}
                                decimals={1}
                                suffix="%"
                              />
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={(image?.analysis?.confidence || 0) * 100}
                            sx={{
                              height: 6,
                              borderRadius: 3,
                              backgroundColor: 'rgba(255, 255, 255, 0.1)',
                              '& .MuiLinearProgress-bar': {
                                borderRadius: 3,
                                background: `linear-gradient(90deg, #667eea 0%, #764ba2 ${
                                  (image?.analysis?.confidence || 0) * 100
                                }%, transparent ${(image?.analysis?.confidence || 0) * 100}%)`,
                              },
                            }}
                          />
                        </Box>
                      )}
                    </>
                  )}
                  
                  <IconButton
                    size="small"
                    sx={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      backgroundColor: 'rgba(255, 255, 255, 0.1)',
                      backdropFilter: 'blur(10px)',
                      '&:hover': {
                        backgroundColor: 'rgba(255, 255, 255, 0.2)',
                      },
                    }}
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      setImages((prev) => prev.filter((img) => img?.id !== image?.id));
                    }}
                  >
                    <Close sx={{ fontSize: 16, color: 'rgba(255, 255, 255, 0.8)' }} />
                  </IconButton>
                </GlassContainer>
              </motion.div>
              );
            })}
          </Box>
        </motion.div>
      )}
    </AnimatePresence>
  );

  const renderSelectedImageView = () => (
    <AnimatePresence>
      {selectedImage && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.9)',
            zIndex: 1300,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
          onClick={() => setSelectedImage(null)}
        >
          <motion.div
            animate={controls}
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 1200, width: '100%' }}
          >
            <GlassContainer sx={{ p: 0, overflow: 'hidden' }}>
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: { xs: 'column', md: 'row' },
                  height: { xs: 'auto', md: '80vh' },
                }}
              >
                {/* Image Section - Show Original and Annotated Side by Side */}
                <Box
                  sx={{
                    flex: 1,
                    position: 'relative',
                    background: 'rgba(0, 0, 0, 0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                  }}
                >
                  {selectedImage?.analysis?.heatmapData ? (
                    <Box sx={{ display: 'flex', width: '100%', height: '100%', gap: 2, p: 2 }}>
                      {/* Original Image */}
                      <Box
                        sx={{
                          flex: 1,
                          display: showOriginal ? 'flex' : 'none',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Typography
                          variant="subtitle2"
                          sx={{
                            color: 'rgba(255, 255, 255, 0.8)',
                            mb: 1,
                            textTransform: 'uppercase',
                            letterSpacing: 1,
                          }}
                        >
                          Original Image
                        </Typography>
                        <motion.img
                          src={`data:image/png;base64,${selectedImage?.analysis?.heatmapData?.original_image}`}
                          alt="Original medical scan"
                          style={{
                            maxWidth: '100%',
                            maxHeight: 'calc(100% - 40px)',
                            objectFit: 'contain',
                            transform: `scale(${zoomLevel})`,
                            transition: 'transform 0.3s ease',
                          }}
                        />
                      </Box>
                      
                      {/* Annotated Image with Heatmap */}
                      <Box
                        sx={{
                          flex: 1,
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Typography
                          variant="subtitle2"
                          sx={{
                            color: 'rgba(255, 255, 255, 0.8)',
                            mb: 1,
                            textTransform: 'uppercase',
                            letterSpacing: 1,
                          }}
                        >
                          AI Analysis with Annotations
                        </Typography>
                        <motion.img
                          src={`data:image/png;base64,${selectedImage?.analysis?.heatmapData?.heatmap_overlay}`}
                          alt="Annotated medical scan with heatmap"
                          style={{
                            maxWidth: '100%',
                            maxHeight: 'calc(100% - 40px)',
                            objectFit: 'contain',
                            transform: `scale(${zoomLevel})`,
                            transition: 'transform 0.3s ease',
                          }}
                        />
                      </Box>
                    </Box>
                  ) : (
                    <motion.img
                      src={selectedImage?.preview || ''}
                      alt="Medical scan"
                      style={{
                        maxWidth: '100%',
                        maxHeight: '100%',
                        objectFit: 'contain',
                        transform: `scale(${zoomLevel})`,
                        transition: 'transform 0.3s ease',
                      }}
                    />
                  )}
                  
                  {/* Controls */}
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: 16,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      display: 'flex',
                      gap: 1,
                    }}
                  >
                    <IconButton
                      sx={{
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        backdropFilter: 'blur(10px)',
                        color: 'white',
                        '&:hover': {
                          backgroundColor: 'rgba(255, 255, 255, 0.2)',
                        },
                      }}
                      onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.25))}
                    >
                      <ZoomOut />
                    </IconButton>
                    <IconButton
                      sx={{
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        backdropFilter: 'blur(10px)',
                        color: 'white',
                        '&:hover': {
                          backgroundColor: 'rgba(255, 255, 255, 0.2)',
                        },
                      }}
                      onClick={() => setZoomLevel(Math.min(3, zoomLevel + 0.25))}
                    >
                      <ZoomIn />
                    </IconButton>
                    {selectedImage?.analysis?.heatmapData && (
                      <IconButton
                        sx={{
                          backgroundColor: showOriginal ? 'rgba(99, 102, 241, 0.3)' : 'rgba(255, 255, 255, 0.1)',
                          backdropFilter: 'blur(10px)',
                          color: 'white',
                          '&:hover': {
                            backgroundColor: showOriginal ? 'rgba(99, 102, 241, 0.4)' : 'rgba(255, 255, 255, 0.2)',
                          },
                        }}
                        onClick={() => setShowOriginal(!showOriginal)}
                        title={showOriginal ? "Hide original image" : "Show original image"}
                      >
                        <Visibility />
                      </IconButton>
                    )}
                    <IconButton
                      sx={{
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        backdropFilter: 'blur(10px)',
                        color: 'white',
                        '&:hover': {
                          backgroundColor: 'rgba(255, 255, 255, 0.2)',
                        },
                      }}
                    >
                      <Fullscreen />
                    </IconButton>
                  </Box>
                  
                  <IconButton
                    sx={{
                      position: 'absolute',
                      top: 16,
                      right: 16,
                      backgroundColor: 'rgba(255, 255, 255, 0.1)',
                      backdropFilter: 'blur(10px)',
                      color: 'white',
                      '&:hover': {
                        backgroundColor: 'rgba(255, 255, 255, 0.2)',
                      },
                    }}
                    onClick={() => setSelectedImage(null)}
                  >
                    <Close />
                  </IconButton>
                </Box>
                
                {/* Analysis Section */}
                <Box
                  sx={{
                    width: { xs: '100%', md: 400 },
                    p: 3,
                    overflowY: 'auto',
                    background: 'rgba(0, 0, 0, 0.2)',
                  }}
                >
                  {selectedImage?.analysis ? (
                    <>
                      <Box sx={{ mb: 3 }}>
                        <Typography
                          variant="h5"
                          sx={{
                            color: 'rgba(255, 255, 255, 0.9)',
                            fontWeight: 600,
                            mb: 2,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                          }}
                        >
                          <AutoFixHigh sx={{ color: '#667eea' }} />
                          Analysis Report
                          {selectedImage?.analysis?.groqFallback && (
                            <Chip
                              label="Groq AI"
                              size="small"
                              sx={{
                                ml: 2,
                                backgroundColor: 'rgba(33, 150, 243, 0.2)',
                                color: '#2196f3',
                                fontSize: '0.75rem'
                              }}
                            />
                          )}
                        </Typography>
                        
                        <Box
                          sx={{
                            p: 2,
                            borderRadius: 2,
                            background: 'rgba(99, 102, 241, 0.1)',
                            border: '1px solid rgba(99, 102, 241, 0.3)',
                          }}
                        >
                          <Typography
                            variant="body1"
                            sx={{ color: 'rgba(255, 255, 255, 0.9)', mb: 1 }}
                          >
                            {selectedImage?.analysis?.diagnosis}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Speed sx={{ fontSize: 16, color: '#667eea' }} />
                            <Typography
                              variant="caption"
                              sx={{ color: 'rgba(255, 255, 255, 0.7)' }}
                            >
                              Confidence:{' '}
                              <CountUp
                                end={(selectedImage?.analysis?.confidence || 0) * 100}
                                duration={1}
                                decimals={1}
                                suffix="%"
                              />
                            </Typography>
                          </Box>
                        </Box>
                      </Box>
                      
                      <Box sx={{ mb: 3 }}>
                        <Typography
                          variant="h6"
                          sx={{
                            color: 'rgba(255, 255, 255, 0.9)',
                            fontWeight: 600,
                            mb: 2,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                          }}
                        >
                          <Biotech sx={{ color: '#764ba2' }} />
                          Key Findings
                        </Typography>
                        <AnimatePresence>
                        {selectedImage?.analysis?.findings?.map((finding, index) => (
                          <motion.div
                            key={index}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1 }}
                          >
                            <Box
                              sx={{
                                p: 2,
                                mb: 2,
                                borderRadius: 2,
                                background: 'rgba(255, 255, 255, 0.05)',
                                border: '1px solid rgba(255, 255, 255, 0.1)',
                                borderLeft: `4px solid ${
                                  finding?.severity === 'high'
                                    ? '#ef4444'
                                    : finding?.severity === 'medium'
                                    ? '#f59e0b'
                                    : '#10b981'
                                }`,
                              }}
                            >
                              <Box
                                sx={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  mb: 1,
                                }}
                              >
                                <Typography
                                  variant="subtitle2"
                                  sx={{ color: 'rgba(255, 255, 255, 0.9)' }}
                                >
                                  {finding?.type || ''}
                                </Typography>
                                <Chip
                                  label={finding?.severity || 'unknown'}
                                  size="small"
                                  sx={{
                                    backgroundColor:
                                      finding?.severity === 'high'
                                        ? 'rgba(239, 68, 68, 0.2)'
                                        : finding?.severity === 'medium'
                                        ? 'rgba(245, 158, 11, 0.2)'
                                        : 'rgba(16, 185, 129, 0.2)',
                                    color:
                                      finding?.severity === 'high'
                                        ? '#ef4444'
                                        : finding?.severity === 'medium'
                                        ? '#f59e0b'
                                        : '#10b981',
                                    textTransform: 'capitalize',
                                  }}
                                />
                              </Box>
                              <Typography
                                variant="caption"
                                sx={{ color: 'rgba(255, 255, 255, 0.6)', display: 'block', mb: 0.5 }}
                              >
                                Location: {finding.location}
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{ color: 'rgba(255, 255, 255, 0.8)' }}
                              >
                                {finding.description}
                              </Typography>
                            </Box>
                          </motion.div>
                        ))}
                        </AnimatePresence>
                      </Box>
                      
                      <Box sx={{ mb: 3 }}>
                        <Typography
                          variant="h6"
                          sx={{
                            color: 'rgba(255, 255, 255, 0.9)',
                            fontWeight: 600,
                            mb: 2,
                          }}
                        >
                          Processing Statistics
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <Box>
                            <Typography
                              variant="caption"
                              sx={{ color: 'rgba(255, 255, 255, 0.6)' }}
                            >
                              Processing Time
                            </Typography>
                            <Typography
                              variant="h6"
                              sx={{ color: '#667eea' }}
                            >
                              <CountUp
                                end={selectedImage?.analysis?.statistics?.processingTime || 0}
                                duration={1}
                                decimals={1}
                                suffix="s"
                              />
                            </Typography>
                          </Box>
                          <Box>
                            <Typography
                              variant="caption"
                              sx={{ color: 'rgba(255, 255, 255, 0.6)' }}
                            >
                              Model Accuracy
                            </Typography>
                            <Typography
                              variant="h6"
                              sx={{ color: '#764ba2' }}
                            >
                              <CountUp
                                end={(selectedImage?.analysis?.statistics?.accuracy || 0) * 100}
                                duration={1}
                                decimals={1}
                                suffix="%"
                              />
                            </Typography>
                          </Box>
                          <Box>
                            <Typography
                              variant="caption"
                              sx={{ color: 'rgba(255, 255, 255, 0.6)' }}
                            >
                              Regions Analyzed
                            </Typography>
                            <Typography
                              variant="h6"
                              sx={{ color: '#ec4899' }}
                            >
                              <CountUp
                                end={selectedImage?.analysis?.statistics?.regionsAnalyzed || 0}
                                duration={1}
                              />
                            </Typography>
                          </Box>
                        </Box>
                      </Box>
                      
                      <Box sx={{ display: 'flex', gap: 2 }}>
                        <NeumorphicButton
                          fullWidth
                          startIcon={<Description />}
                          onClick={() => {
                            // Navigate to report viewer instead of showing dialog
                            if (selectedImage?.id) {
                              navigate(`/reports/${selectedImage.id}`);
                            }
                          }}
                        >
                          View Full Report
                        </NeumorphicButton>
                        <NeumorphicButton
                          fullWidth
                          startIcon={<GetApp />}
                          onClick={async () => {
                            try {
                              // For now, create a simple text report
                              const reportText = selectedImage?.analysis ? `Medical Imaging Analysis Report
                              
Diagnosis: ${selectedImage?.analysis?.diagnosis}
Confidence: ${((selectedImage?.analysis?.confidence || 0) * 100).toFixed(1)}%

Key Findings:
${selectedImage?.analysis?.findings?.map(f => `- ${f?.type || 'Unknown'}: ${f?.description || 'No description'}`).join('\n') || ''}

Processing Statistics:
- Processing Time: ${selectedImage?.analysis?.statistics?.processingTime || 0}s
- Model Accuracy: ${((selectedImage?.analysis?.statistics?.accuracy || 0) * 100).toFixed(1)}%
- Regions Analyzed: ${selectedImage?.analysis?.statistics?.regionsAnalyzed || 0}

Generated on: ${new Date().toLocaleString()}
` : `Medical Imaging Analysis Report

No analysis data available for this image.

Generated on: ${new Date().toLocaleString()}
`;
                              
                              // Create a Blob and download
                              const blob = new Blob([reportText], { type: 'text/plain' });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `medical_report_${selectedImage?.id || 'unknown'}.txt`;
                              document.body.appendChild(a);
                              a.click();
                              document.body.removeChild(a);
                              URL.revokeObjectURL(url);
                              
                              confetti({
                                particleCount: 50,
                                spread: 60,
                                origin: { y: 0.8 },
                              });
                            } catch (error) {
                              console.error('Error downloading report:', error);
                              setError('Failed to download report');
                              setShowError(true);
                            }
                          }}
                        >
                          Download Report
                        </NeumorphicButton>
                        <IconButton
                          sx={{
                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                            backdropFilter: 'blur(10px)',
                            color: 'white',
                            '&:hover': {
                              backgroundColor: 'rgba(255, 255, 255, 0.2)',
                            },
                          }}
                          onClick={handleMenuClick}
                        >
                          <MoreVert />
                        </IconButton>
                      </Box>
                    </>
                  ) : (
                    <Box
                      sx={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                      }}
                    >
                      <Skeleton
                        variant="rectangular"
                        width="100%"
                        height={60}
                        sx={{ mb: 2, borderRadius: 2 }}
                      />
                      <Skeleton
                        variant="rectangular"
                        width="100%"
                        height={120}
                        sx={{ mb: 2, borderRadius: 2 }}
                      />
                      <Skeleton
                        variant="rectangular"
                        width="100%"
                        height={180}
                        sx={{ borderRadius: 2 }}
                      />
                    </Box>
                  )}
                </Box>
              </Box>
              
              {/* Heatmap Settings */}
              <Collapse in={showHeatmap}>
                <Box
                  sx={{
                    p: 2,
                    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                    background: 'rgba(0, 0, 0, 0.2)',
                  }}
                >
                  <Typography
                    variant="subtitle2"
                    sx={{ color: 'rgba(255, 255, 255, 0.9)', mb: 2 }}
                  >
                    Heatmap Settings
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                    <Box sx={{ flex: 1, minWidth: 200 }}>
                      <Typography
                        variant="caption"
                        sx={{ color: 'rgba(255, 255, 255, 0.6)' }}
                      >
                        Intensity
                      </Typography>
                      <Slider
                        value={heatmapSettings.intensity}
                        onChange={(e: Event, value: number | number[]) =>
                          setHeatmapSettings({
                            ...heatmapSettings,
                            intensity: value as number,
                          })
                        }
                        min={0}
                        max={100}
                        sx={{
                          color: '#667eea',
                          '& .MuiSlider-thumb': {
                            backgroundColor: '#667eea',
                            '&:hover': {
                              boxShadow: '0 0 0 8px rgba(102, 126, 234, 0.16)',
                            },
                          },
                        }}
                      />
                    </Box>
                    <Box sx={{ flex: 1, minWidth: 200 }}>
                      <Typography
                        variant="caption"
                        sx={{ color: 'rgba(255, 255, 255, 0.6)' }}
                      >
                        Opacity
                      </Typography>
                      <Slider
                        value={heatmapSettings.opacity}
                        onChange={(e: Event, value: number | number[]) =>
                          setHeatmapSettings({
                            ...heatmapSettings,
                            opacity: value as number,
                          })
                        }
                        min={0}
                        max={100}
                        sx={{
                          color: '#764ba2',
                          '& .MuiSlider-thumb': {
                            backgroundColor: '#764ba2',
                            '&:hover': {
                              boxShadow: '0 0 0 8px rgba(118, 75, 162, 0.16)',
                            },
                          },
                        }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      <IconButton
                        size="small"
                        sx={{
                          backgroundColor:
                            heatmapSettings.colorScheme === 'thermal'
                              ? 'rgba(99, 102, 241, 0.2)'
                              : 'rgba(255, 255, 255, 0.1)',
                          color: 'white',
                        }}
                        onClick={() =>
                          setHeatmapSettings({
                            ...heatmapSettings,
                            colorScheme: 'thermal',
                          })
                        }
                      >
                        <Palette />
                      </IconButton>
                      <IconButton
                        size="small"
                        sx={{
                          backgroundColor:
                            heatmapSettings.colorScheme === 'medical'
                              ? 'rgba(139, 92, 246, 0.2)'
                              : 'rgba(255, 255, 255, 0.1)',
                          color: 'white',
                        }}
                        onClick={() =>
                          setHeatmapSettings({
                            ...heatmapSettings,
                            colorScheme: 'medical',
                          })
                        }
                      >
                        <Biotech />
                      </IconButton>
                    </Box>
                  </Box>
                </Box>
              </Collapse>
            </GlassContainer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%)',
        padding: 4,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background decoration */}
      <Box
        sx={{
          position: 'absolute',
          top: -100,
          right: -100,
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.3) 0%, transparent 70%)',
          filter: 'blur(80px)',
          animation: `${pulse} 4s ease-in-out infinite`,
        }}
      />
      <Box
        sx={{
          position: 'absolute',
          bottom: -150,
          left: -150,
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%)',
          filter: 'blur(100px)',
          animation: `${pulse} 6s ease-in-out infinite`,
        }}
      />
      
      <Box sx={{ maxWidth: 1400, margin: '0 auto', position: 'relative', zIndex: 1 }}>
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Typography
            variant="h3"
            sx={{
              color: 'white',
              fontWeight: 700,
              mb: 1,
              textAlign: 'center',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Medical Imaging Analysis
          </Typography>
          <Typography
            variant="h6"
            sx={{
              color: 'rgba(255, 255, 255, 0.7)',
              textAlign: 'center',
              mb: 5,
            }}
          >
            AI-powered medical image analysis with advanced visualization
          </Typography>
        </motion.div>
        
        {/* Tabs for Upload and View Reports */}
        <Paper
          elevation={0}
          sx={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(20px)',
            borderRadius: 3,
            mb: 4,
            overflow: 'hidden',
          }}
        >
          <Tabs
            value={activeTab}
            onChange={(_: React.SyntheticEvent, newValue: number) => setActiveTab(newValue)}
            centered
            sx={{
              '& .MuiTab-root': {
                color: 'rgba(255, 255, 255, 0.7)',
                fontSize: '1rem',
                fontWeight: 500,
                minHeight: 64,
                '&:hover': {
                  color: 'rgba(255, 255, 255, 0.9)',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                },
                '&.Mui-selected': {
                  color: '#667eea',
                  fontWeight: 600,
                },
              },
              '& .MuiTabs-indicator': {
                height: 3,
                background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
              },
            }}
          >
            <Tab
              icon={<CloudUploadOutlined sx={{ fontSize: 24, mb: 0.5 }} />}
              label="Upload & Analyze"
              iconPosition="start"
            />
            <Tab
              icon={<AssessmentOutlined sx={{ fontSize: 24, mb: 0.5 }} />}
              label="View Reports"
              iconPosition="start"
            />
          </Tabs>
        </Paper>
        
        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 0 ? (
            // Upload & Analyze Tab
            <motion.div
              key="upload-tab"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
            >
              {/* Show loading indicator while uploading images */}
              {isUploadingImages && (
                <Box sx={{ mb: 4, textAlign: 'center' }}>
                  <CircularProgress size={40} sx={{ color: '#667eea' }} />
                  <Typography variant="body2" sx={{ mt: 2, color: 'rgba(255, 255, 255, 0.7)' }}>
                    Uploading images and initializing workflow...
                  </Typography>
                </Box>
              )}
              
              {/* Workflow Progress and Upload Area with Animation */}
              <AnimatePresence mode="wait">
                {showWorkflowProgress && activeWorkflowCaseId && !isUploadingImages ? (
                  <motion.div
                    key="workflow-progress"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                    style={{ marginBottom: '32px' }}
                  >
                    <WorkflowProgress
                      caseId={activeWorkflowCaseId}
                      onComplete={handleWorkflowComplete}
                      onError={(error) => {
                        setError(error.message || 'Workflow processing failed');
                        setShowError(true);
                        setShowWorkflowProgress(false);
                        setActiveWorkflowCaseId(null);
                      }}
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key="upload-area"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                  >
                    {renderUploadArea()}
                  </motion.div>
                )}
              </AnimatePresence>
              
              <Box sx={{ mt: 5 }}>
                {renderImageGallery()}
              </Box>
              
              {/* Previous Reports Section */}
              <Collapse in={showPreviousReports}>
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.5 }}
                >
                  <Box sx={{ mt: 4 }}>
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
                      <History />
                      Previous Reports
                    </Typography>
                    
                    {previousReports.length > 0 ? (
                      <Box
                        sx={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
                          gap: 3,
                        }}
                      >
                        {previousReports.map((report, index) => (
                          <motion.div
                            key={report.report_id || index}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                          >
                            <GlassContainer
                              sx={{
                                p: 3,
                                cursor: 'pointer',
                                transition: 'all 0.3s ease',
                                '&:hover': {
                                  transform: 'translateY(-4px)',
                                  boxShadow: '0 12px 40px 0 rgba(31, 38, 135, 0.45)',
                                },
                              }}
                              onClick={async () => {
                                try {
                                  // Navigate to report viewer instead of showing dialog
                                  navigate(`/reports/${report.report_id}`);
                                } catch (error) {
                                  console.error('Failed to load report:', error);
                                }
                              }}
                            >
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                                <Typography
                                  variant="subtitle1"
                                  sx={{ color: 'rgba(255, 255, 255, 0.9)', fontWeight: 600 }}
                                >
                                  Report #{report.report_id?.slice(-6) || 'Unknown'}
                                </Typography>
                                <Chip
                                  label={report.status || 'Completed'}
                                  size="small"
                                  sx={{
                                    background: report.status === 'completed' 
                                      ? 'rgba(16, 185, 129, 0.2)' 
                                      : 'rgba(99, 102, 241, 0.2)',
                                    color: report.status === 'completed' ? '#10b981' : '#667eea',
                                  }}
                                />
                              </Box>
                              
                              <Typography
                                variant="body2"
                                sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}
                              >
                                {report.created_at 
                                  ? `${new Date(report.created_at).toLocaleDateString()} at ${new Date(report.created_at).toLocaleTimeString()}`
                                  : 'Date not available'}
                              </Typography>
                              
                              {report.key_findings && report.key_findings.length > 0 && (
                                <Box sx={{ mt: 2 }}>
                                  <Typography
                                    variant="caption"
                                    sx={{ color: 'rgba(255, 255, 255, 0.6)', display: 'block', mb: 1 }}
                                  >
                                    Key Findings:
                                  </Typography>
                                  {report.key_findings.slice(0, 2).map((finding: string, idx: number) => (
                                    <Typography
                                      key={idx}
                                      variant="caption"
                                      sx={{
                                        color: 'rgba(255, 255, 255, 0.8)',
                                        display: 'block',
                                        ml: 2,
                                      }}
                                    >
                                      • {finding}
                                    </Typography>
                                  ))}
                                </Box>
                              )}
                              
                              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                                <Button
                                  size="small"
                                  startIcon={<Visibility />}
                                  sx={{ color: '#667eea' }}
                                >
                                  View
                                </Button>
                                <Button
                                  size="small"
                                  startIcon={<GetApp />}
                                  sx={{ color: '#764ba2' }}
                                  onClick={async (e: React.MouseEvent) => {
                                    e.stopPropagation();
                                    try {
                                      const blob = await medicalImagingService.downloadReport(report.report_id);
                                      const url = URL.createObjectURL(blob);
                                      const a = document.createElement('a');
                                      a.href = url;
                                      a.download = `report_${report.report_id}.pdf`;
                                      a.click();
                                      URL.revokeObjectURL(url);
                                    } catch (error) {
                                      console.error('Failed to download report:', error);
                                    }
                                  }}
                                >
                                  Download
                                </Button>
                              </Box>
                            </GlassContainer>
                          </motion.div>
                        ))}
                      </Box>
                    ) : (
                      <GlassContainer sx={{ p: 4, textAlign: 'center' }}>
                        <Typography
                          variant="body1"
                          sx={{ color: 'rgba(255, 255, 255, 0.7)' }}
                        >
                          No previous reports found. Start by analyzing some medical images!
                        </Typography>
                      </GlassContainer>
                    )}
                  </Box>
                </motion.div>
              </Collapse>
            </motion.div>
          ) : (
            // View Reports Tab
            <motion.div
              key="reports-tab"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <ModernReportsViewer
                onReportSelect={(report) => {
                  // Navigate to report viewer instead of showing dialog
                  navigate(`/reports/${report.report_id}`);
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
        
        {renderSelectedImageView()}
        
        {/* Floating Action Buttons */}
        <FloatingActionButton
          color="primary"
          sx={{ bottom: 16, right: 16 }}
          onClick={() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            input.accept = 'image/*';
            input.onchange = (e) => {
              const files = Array.from((e.target as HTMLInputElement).files || []);
              onDrop(files);
            };
            input.click();
          }}
        >
          <CloudUpload />
        </FloatingActionButton>
        
        <FloatingActionButton
          color="secondary"
          sx={{ bottom: 16, right: 88, animationDelay: '2s' }}
          onClick={() => {
            confetti({
              particleCount: 200,
              spread: 90,
              origin: { y: 0.6 },
              colors: ['#6366f1', '#8b5cf6', '#ec4899', '#3b82f6'],
            });
          }}
        >
          <AutoFixHigh />
        </FloatingActionButton>
        
        {/* Action Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          PaperProps={{
            sx: {
              background: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              '& .MuiMenuItem-root': {
                color: 'rgba(255, 255, 255, 0.9)',
                '&:hover': {
                  background: 'rgba(255, 255, 255, 0.1)',
                },
              },
            },
          }}
        >
          <MenuItem onClick={handleMenuClose}>
            <Share sx={{ mr: 1, fontSize: 20 }} /> Share Report
          </MenuItem>
          <MenuItem onClick={handleMenuClose}>
            <Print sx={{ mr: 1, fontSize: 20 }} /> Print Report
          </MenuItem>
        </Menu>
        
        {/* Notification Snackbar */}
        <Snackbar
          open={showError}
          autoHideDuration={6000}
          onClose={() => setShowError(false)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => setShowError(false)}
            severity={error?.includes('success') ? 'success' : 'error'}
            sx={{ 
              width: '100%',
              backgroundColor: error?.includes('success') 
                ? 'rgba(16, 185, 129, 0.1)' 
                : 'rgba(239, 68, 68, 0.1)',
              color: 'white',
              '& .MuiAlert-icon': { 
                color: error?.includes('success') ? '#10b981' : '#ef4444' 
              }
            }}
          >
            {error}
          </Alert>
        </Snackbar>

        {/* Full Report Dialog removed - now using navigation to report viewer */}
      </Box>
    </Box>
  );
};

export default MedicalImagingModern;