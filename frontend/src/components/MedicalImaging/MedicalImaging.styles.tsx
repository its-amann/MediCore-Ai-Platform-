import { styled, keyframes } from '@mui/material/styles';
import { Box, Paper, Card, Button, IconButton, alpha } from '@mui/material';

// Keyframe Animations
const shimmer = keyframes`
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
`;

const pulse = keyframes`
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
`;

const slideInFromRight = keyframes`
  0% {
    transform: translateX(100%);
    opacity: 0;
  }
  100% {
    transform: translateX(0);
    opacity: 1;
  }
`;

const slideInFromBottom = keyframes`
  0% {
    transform: translateY(30px);
    opacity: 0;
  }
  100% {
    transform: translateY(0);
    opacity: 1;
  }
`;

const gradientShift = keyframes`
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
`;

const float = keyframes`
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
`;

const rotateGradient = keyframes`
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
`;

// Main Container with Animated Mesh Gradient Background
export const Container = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  maxWidth: '1400px',
  margin: '0 auto',
  position: 'relative',
  '&::before': {
    content: '""',
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `
      radial-gradient(circle at 20% 80%, ${alpha(theme.palette.primary.main, 0.1)} 0%, transparent 50%),
      radial-gradient(circle at 80% 20%, ${alpha(theme.palette.secondary.main, 0.1)} 0%, transparent 50%),
      radial-gradient(circle at 40% 40%, ${alpha('#8B5CF6', 0.1)} 0%, transparent 50%)
    `,
    zIndex: -1,
    animation: `${gradientShift} 15s ease infinite`,
    backgroundSize: '200% 200%',
  },
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(2),
  },
}));

// Glassmorphic Upload Section with Animated Border
export const UploadSection = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  marginBottom: theme.spacing(3),
  background: `${alpha(theme.palette.background.paper, 0.7)}`,
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  borderRadius: theme.spacing(3),
  border: `2px dashed ${alpha(theme.palette.primary.main, 0.3)}`,
  position: 'relative',
  overflow: 'hidden',
  animation: `${slideInFromBottom} 0.6s ease-out`,
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  boxShadow: `
    0 10px 40px ${alpha(theme.palette.primary.main, 0.1)},
    inset 0 1px 0 ${alpha(theme.palette.common.white, 0.1)}
  `,
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.05)} 0%, ${alpha(theme.palette.secondary.main, 0.05)} 100%)`,
    opacity: 0,
    transition: 'opacity 0.3s ease',
  },
  '&:hover': {
    borderColor: theme.palette.primary.main,
    transform: 'translateY(-2px)',
    boxShadow: `
      0 20px 60px ${alpha(theme.palette.primary.main, 0.2)},
      inset 0 1px 0 ${alpha(theme.palette.common.white, 0.2)}
    `,
    '&::before': {
      opacity: 1,
    },
  },
  '&:active': {
    transform: 'translateY(0)',
  },
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(2),
  },
}));

// Image Grid with Stagger Animation
export const ImageGrid = styled(Box)(({ theme }) => ({
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: theme.spacing(3),
  marginBottom: theme.spacing(4),
  '& > *': {
    animation: `${slideInFromBottom} 0.6s ease-out backwards`,
    '&:nth-of-type(1)': { animationDelay: '0.1s' },
    '&:nth-of-type(2)': { animationDelay: '0.2s' },
    '&:nth-of-type(3)': { animationDelay: '0.3s' },
    '&:nth-of-type(4)': { animationDelay: '0.4s' },
    '&:nth-of-type(5)': { animationDelay: '0.5s' },
    '&:nth-of-type(6)': { animationDelay: '0.6s' },
  },
  [theme.breakpoints.down('sm')]: {
    gridTemplateColumns: '1fr',
    gap: theme.spacing(2),
  },
}));

// 3D Transform Image Card with Glassmorphism
export const ImageCard = styled(Card)(({ theme }) => ({
  position: 'relative',
  overflow: 'hidden',
  borderRadius: theme.spacing(3),
  background: `${alpha(theme.palette.background.paper, 0.8)}`,
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  transformStyle: 'preserve-3d',
  perspective: '1000px',
  boxShadow: `
    0 10px 30px ${alpha(theme.palette.primary.main, 0.15)},
    0 1px 3px ${alpha(theme.palette.common.black, 0.1)},
    inset 0 1px 0 ${alpha(theme.palette.common.white, 0.1)}
  `,
  '&:hover': {
    transform: 'translateY(-8px) rotateX(2deg)',
    boxShadow: `
      0 20px 50px ${alpha(theme.palette.primary.main, 0.25)},
      0 10px 20px ${alpha(theme.palette.common.black, 0.1)},
      inset 0 1px 0 ${alpha(theme.palette.common.white, 0.2)}
    `,
    '& $ImagePreview': {
      transform: 'scale(1.05)',
    },
    '& $ImageOverlay': {
      opacity: 1,
    },
  },
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, transparent 100%)`,
    opacity: 0,
    transition: 'opacity 0.3s ease',
    pointerEvents: 'none',
  },
  '&:hover::before': {
    opacity: 1,
  },
}));

// Image Preview with Smooth Transitions
export const ImagePreview = styled('img')({
  width: '100%',
  height: '200px',
  objectFit: 'cover',
  display: 'block',
  transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
});

// Premium Image Overlay with Gradient
export const ImageOverlay = styled(Box)(({ theme }) => ({
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: `linear-gradient(to bottom, 
    ${alpha(theme.palette.common.black, 0.2)} 0%, 
    ${alpha(theme.palette.common.black, 0.7)} 100%
  )`,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  opacity: 0,
  transition: 'opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  backdropFilter: 'blur(2px)',
  WebkitBackdropFilter: 'blur(2px)',
}));

// Animated Status Badge with Glow Effect
export const StatusBadge = styled(Box)<{ status: string }>(({ theme, status }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return { bg: theme.palette.success.main, glow: theme.palette.success.light };
      case 'analyzing':
        return { bg: theme.palette.warning.main, glow: theme.palette.warning.light };
      case 'error':
        return { bg: theme.palette.error.main, glow: theme.palette.error.light };
      default:
        return { bg: theme.palette.grey[500], glow: theme.palette.grey[400] };
    }
  };

  const colors = getStatusColor();

  return {
    position: 'absolute',
    top: theme.spacing(1),
    right: theme.spacing(1),
    padding: theme.spacing(0.5, 1.5),
    borderRadius: theme.spacing(2),
    fontSize: '0.75rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    backgroundColor: colors.bg,
    color: theme.palette.common.white,
    boxShadow: `0 2px 10px ${alpha(colors.glow, 0.5)}`,
    animation: status === 'analyzing' ? `${pulse} 2s infinite` : 'none',
    transition: 'all 0.3s ease',
    '&:hover': {
      transform: 'scale(1.05)',
      boxShadow: `0 4px 20px ${alpha(colors.glow, 0.7)}`,
    },
  };
});

// Results Section with Glassmorphism and Gradient Border
export const ResultsSection = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  marginTop: theme.spacing(4),
  background: `${alpha(theme.palette.background.paper, 0.8)}`,
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  borderRadius: theme.spacing(3),
  position: 'relative',
  animation: `${slideInFromBottom} 0.8s ease-out`,
  border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
  boxShadow: `
    0 20px 50px ${alpha(theme.palette.primary.main, 0.1)},
    inset 0 1px 0 ${alpha(theme.palette.common.white, 0.1)}
  `,
  '&::before': {
    content: '""',
    position: 'absolute',
    top: -2,
    left: -2,
    right: -2,
    bottom: -2,
    background: `linear-gradient(45deg, 
      ${theme.palette.primary.main}, 
      ${theme.palette.secondary.main}, 
      ${theme.palette.primary.main}
    )`,
    borderRadius: theme.spacing(3),
    opacity: 0.1,
    zIndex: -1,
    animation: `${rotateGradient} 10s linear infinite`,
    backgroundSize: '200% 200%',
  },
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(2),
  },
}));

// Finding Card with Animated Border and Glow
export const FindingCard = styled(Card)<{ severity?: string }>(({ theme, severity }) => {
  const getSeverityColor = () => {
    switch (severity) {
      case 'critical':
        return { main: theme.palette.error.main, light: theme.palette.error.light };
      case 'high':
        return { main: theme.palette.warning.main, light: theme.palette.warning.light };
      case 'medium':
        return { main: theme.palette.info.main, light: theme.palette.info.light };
      default:
        return { main: theme.palette.success.main, light: theme.palette.success.light };
    }
  };

  const colors = getSeverityColor();

  return {
    padding: theme.spacing(2),
    marginBottom: theme.spacing(2),
    background: `${alpha(theme.palette.background.paper, 0.6)}`,
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    borderLeft: `4px solid ${colors.main}`,
    borderRadius: theme.spacing(2),
    position: 'relative',
    overflow: 'hidden',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    animation: `${slideInFromRight} 0.6s ease-out`,
    boxShadow: `
      0 4px 20px ${alpha(colors.main, 0.15)},
      inset 0 1px 0 ${alpha(theme.palette.common.white, 0.1)}
    `,
    '&::before': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: 0,
      bottom: 0,
      width: '100%',
      background: `linear-gradient(90deg, ${alpha(colors.light, 0.1)} 0%, transparent 100%)`,
      opacity: 0,
      transition: 'opacity 0.3s ease',
    },
    '&:hover': {
      transform: 'translateX(4px)',
      boxShadow: `
        0 8px 30px ${alpha(colors.main, 0.25)},
        inset 0 1px 0 ${alpha(theme.palette.common.white, 0.2)}
      `,
      '&::before': {
        opacity: 1,
      },
    },
  };
});

// Heatmap Container with Premium Styling
export const HeatmapContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  marginTop: theme.spacing(2),
  borderRadius: theme.spacing(2),
  overflow: 'hidden',
  background: `${alpha(theme.palette.background.paper, 0.8)}`,
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
  boxShadow: `
    0 10px 30px ${alpha(theme.palette.primary.main, 0.1)},
    inset 0 1px 0 ${alpha(theme.palette.common.white, 0.1)}
  `,
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  '& img': {
    width: '100%',
    height: 'auto',
    display: 'block',
    transition: 'transform 0.3s ease',
  },
  '&:hover': {
    transform: 'scale(1.02)',
    boxShadow: `
      0 20px 40px ${alpha(theme.palette.primary.main, 0.2)},
      inset 0 1px 0 ${alpha(theme.palette.common.white, 0.2)}
    `,
    '& img': {
      transform: 'scale(1.05)',
    },
  },
}));

// Premium Action Button with Pulse Animation
export const ActionButton = styled(Button)(({ theme }) => ({
  borderRadius: theme.spacing(3),
  padding: theme.spacing(1.5, 3),
  fontWeight: 600,
  textTransform: 'none',
  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
  color: theme.palette.common.white,
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  boxShadow: `
    0 4px 20px ${alpha(theme.palette.primary.main, 0.3)},
    inset 0 1px 0 ${alpha(theme.palette.common.white, 0.2)}
  `,
  '&::before': {
    content: '""',
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: '100%',
    height: '100%',
    background: `radial-gradient(circle, ${alpha(theme.palette.common.white, 0.3)} 0%, transparent 70%)`,
    transform: 'translate(-50%, -50%) scale(0)',
    transition: 'transform 0.5s ease',
  },
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: `
      0 8px 30px ${alpha(theme.palette.primary.main, 0.4)},
      inset 0 1px 0 ${alpha(theme.palette.common.white, 0.3)}
    `,
    '&::before': {
      transform: 'translate(-50%, -50%) scale(2)',
    },
  },
  '&:active': {
    transform: 'translateY(0)',
  },
  '&.MuiButton-outlined': {
    background: `${alpha(theme.palette.background.paper, 0.8)}`,
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    border: `2px solid ${theme.palette.primary.main}`,
    color: theme.palette.primary.main,
    '&:hover': {
      background: `${alpha(theme.palette.primary.main, 0.1)}`,
      borderColor: theme.palette.primary.dark,
    },
  },
}));

// Floating Action Bar with Glassmorphism
export const FloatingActionBar = styled(Box)(({ theme }) => ({
  position: 'fixed',
  bottom: theme.spacing(3),
  right: theme.spacing(3),
  display: 'flex',
  gap: theme.spacing(2),
  zIndex: theme.zIndex.speedDial,
  padding: theme.spacing(2),
  borderRadius: theme.spacing(3),
  background: `${alpha(theme.palette.background.paper, 0.9)}`,
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
  boxShadow: `
    0 10px 40px ${alpha(theme.palette.primary.main, 0.2)},
    inset 0 1px 0 ${alpha(theme.palette.common.white, 0.1)}
  `,
  animation: `${float} 3s ease-in-out infinite`,
  [theme.breakpoints.down('sm')]: {
    bottom: theme.spacing(2),
    right: theme.spacing(2),
    flexDirection: 'column',
    padding: theme.spacing(1.5),
  },
}));

// Similar Report Card with Hover Effects
export const SimilarReportCard = styled(Card)(({ theme }) => ({
  padding: theme.spacing(2),
  cursor: 'pointer',
  background: `${alpha(theme.palette.background.paper, 0.7)}`,
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
  borderRadius: theme.spacing(2),
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  position: 'relative',
  overflow: 'hidden',
  boxShadow: `
    0 4px 20px ${alpha(theme.palette.primary.main, 0.1)},
    inset 0 1px 0 ${alpha(theme.palette.common.white, 0.1)}
  `,
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: '-100%',
    width: '100%',
    height: '100%',
    background: `linear-gradient(90deg, transparent, ${alpha(theme.palette.primary.light, 0.2)}, transparent)`,
    transition: 'left 0.5s ease',
  },
  '&:hover': {
    transform: 'translateY(-4px) scale(1.02)',
    boxShadow: `
      0 12px 30px ${alpha(theme.palette.primary.main, 0.2)},
      inset 0 1px 0 ${alpha(theme.palette.common.white, 0.2)}
    `,
    '&::before': {
      left: '100%',
    },
  },
}));

// Progress Overlay with Shimmer Effect
export const ProgressOverlay = styled(Box)(({ theme }) => ({
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: `${alpha(theme.palette.background.paper, 0.95)}`,
  backdropFilter: 'blur(5px)',
  WebkitBackdropFilter: 'blur(5px)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1,
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `linear-gradient(90deg, 
      transparent 0%, 
      ${alpha(theme.palette.primary.light, 0.1)} 50%, 
      transparent 100%
    )`,
    animation: `${shimmer} 2s linear infinite`,
    backgroundSize: '1000px 100%',
  },
}));

// Delete Button with Hover Glow
export const DeleteButton = styled(IconButton)(({ theme }) => ({
  position: 'absolute',
  top: theme.spacing(1),
  left: theme.spacing(1),
  background: `${alpha(theme.palette.background.paper, 0.9)}`,
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: `linear-gradient(135deg, ${theme.palette.error.light} 0%, ${theme.palette.error.main} 100%)`,
    color: theme.palette.common.white,
    transform: 'scale(1.1)',
    boxShadow: `0 4px 20px ${alpha(theme.palette.error.main, 0.4)}`,
  },
  '&:active': {
    transform: 'scale(0.95)',
  },
}));

// Loading Skeleton with Shimmer
export const LoadingSkeleton = styled(Box)(({ theme }) => ({
  position: 'relative',
  overflow: 'hidden',
  backgroundColor: alpha(theme.palette.action.hover, 0.1),
  borderRadius: theme.spacing(2),
  '&::after': {
    content: '""',
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    transform: 'translateX(-100%)',
    background: `linear-gradient(
      90deg,
      ${alpha(theme.palette.action.hover, 0)} 0%,
      ${alpha(theme.palette.action.hover, 0.2)} 20%,
      ${alpha(theme.palette.action.hover, 0.5)} 60%,
      ${alpha(theme.palette.action.hover, 0)}
    )`,
    animation: `${shimmer} 2s infinite`,
  },
}));

// All components are already exported individually above