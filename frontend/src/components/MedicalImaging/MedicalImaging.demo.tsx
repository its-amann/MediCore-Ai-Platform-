import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, Typography } from '@mui/material';
import MedicalImaging from './MedicalImaging';

// Create a premium theme with medical colors
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#3B82F6', // Medical blue
      light: '#60A5FA',
      dark: '#2563EB',
    },
    secondary: {
      main: '#8B5CF6', // Medical purple
      light: '#A78BFA',
      dark: '#7C3AED',
    },
    background: {
      default: '#F8FAFC',
      paper: '#FFFFFF',
    },
  },
  shape: {
    borderRadius: 8,
  },
  shadows: [
    'none',
    '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    ...Array(19).fill('0 25px 50px -12px rgb(0 0 0 / 0.25)'),
  ] as any,
});

const MedicalImagingDemo: React.FC = () => {
  const handleAnalysisComplete = (results: any[]) => {
    console.log('Analysis complete:', results);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <Box sx={{ py: 6 }}>
          <Typography
            variant="h2"
            component="h1"
            align="center"
            sx={{
              fontWeight: 700,
              background: 'linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 2,
            }}
          >
            Premium Medical Imaging Analysis
          </Typography>
          <Typography
            variant="h5"
            align="center"
            color="text.secondary"
            sx={{ mb: 6, fontWeight: 300 }}
          >
            Experience AI-powered medical image analysis with stunning UI
          </Typography>
        </Box>

        <MedicalImaging
          patientId="demo-patient-001"
          onAnalysisComplete={handleAnalysisComplete}
          allowMultiple={true}
          maxFileSize={50 * 1024 * 1024}
        />

        {/* Feature Highlights */}
        <Box sx={{ maxWidth: 1200, mx: 'auto', px: 3, py: 8 }}>
          <Typography variant="h4" align="center" sx={{ mb: 6, fontWeight: 600 }}>
            Premium Features
          </Typography>
          
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 4 }}>
            {[
              {
                title: 'Glassmorphism Design',
                description: 'Beautiful frosted glass effects with backdrop blur and transparency',
                gradient: 'linear-gradient(135deg, #3B82F6 0%, #60A5FA 100%)',
              },
              {
                title: 'Animated Gradients',
                description: 'Smooth gradient animations and mesh backgrounds for modern appeal',
                gradient: 'linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%)',
              },
              {
                title: '3D Transforms',
                description: 'Interactive 3D card effects with perspective and tilt animations',
                gradient: 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
              },
              {
                title: 'Pulse & Glow Effects',
                description: 'Attention-grabbing pulse animations and colorful glow shadows',
                gradient: 'linear-gradient(135deg, #F59E0B 0%, #FCD34D 100%)',
              },
              {
                title: 'Smooth Transitions',
                description: 'Carefully crafted transitions with custom easing functions',
                gradient: 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)',
              },
              {
                title: 'Loading Animations',
                description: 'Shimmer effects and skeleton screens for better UX',
                gradient: 'linear-gradient(135deg, #6366F1 0%, #818CF8 100%)',
              },
            ].map((feature, index) => (
              <Box
                key={index}
                sx={{
                  p: 4,
                  borderRadius: 3,
                  background: 'rgba(255, 255, 255, 0.7)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
                  },
                }}
              >
                <Box
                  sx={{
                    width: 60,
                    height: 60,
                    borderRadius: 2,
                    background: feature.gradient,
                    mb: 3,
                    boxShadow: '0 10px 20px rgba(0, 0, 0, 0.15)',
                  }}
                />
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {feature.description}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>

        {/* Animation Showcase */}
        <Box sx={{ bgcolor: 'rgba(59, 130, 246, 0.05)', py: 8 }}>
          <Box sx={{ maxWidth: 1200, mx: 'auto', px: 3 }}>
            <Typography variant="h4" align="center" sx={{ mb: 6, fontWeight: 600 }}>
              Style Showcase
            </Typography>
            
            <Typography variant="body1" align="center" color="text.secondary" sx={{ mb: 4 }}>
              This component features:
            </Typography>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'center' }}>
              {[
                'Slide-in animations',
                'Hover transforms',
                'Gradient shifts',
                'Blur effects',
                'Floating elements',
                'Stagger animations',
                'Glow shadows',
                'Progress shimmers',
              ].map((item, index) => (
                <Box
                  key={index}
                  sx={{
                    px: 3,
                    py: 1.5,
                    borderRadius: 20,
                    background: 'linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%)',
                    color: 'white',
                    fontWeight: 500,
                    animation: `pulse 2s infinite`,
                    animationDelay: `${index * 0.1}s`,
                    '@keyframes pulse': {
                      '0%, 100%': {
                        transform: 'scale(1)',
                        opacity: 1,
                      },
                      '50%': {
                        transform: 'scale(1.05)',
                        opacity: 0.9,
                      },
                    },
                  }}
                >
                  {item}
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default MedicalImagingDemo;