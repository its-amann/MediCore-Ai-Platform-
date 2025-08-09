import React from 'react';
import { Container, Box, Paper, Typography } from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import ModernReportsViewer from './components/ModernReportsViewer';

const ModernReportsDemo: React.FC = () => {
  const theme = useTheme();

  const handleReportSelect = (report: any) => {
    console.log('Report selected:', report);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(180deg, ${alpha(theme.palette.primary.main, 0.02)} 0%, ${alpha(theme.palette.background.default, 1)} 100%)`,
        py: 4,
      }}
    >
      <Container maxWidth="xl">
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
            Modern Medical Reports Viewer
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 800 }}>
            Experience a beautiful, intuitive interface for viewing medical imaging reports with AI-powered insights,
            advanced filtering, and stunning visual design.
          </Typography>
        </Paper>

        <ModernReportsViewer
          onReportSelect={handleReportSelect}
        />
      </Container>
    </Box>
  );
};

export default ModernReportsDemo;