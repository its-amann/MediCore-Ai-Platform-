import React, { useState } from 'react';
import {
  Box,
  Container,
  Tab,
  Tabs,
  Paper,
  Typography,
  Fade,
  Slide,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Dashboard as DashboardIcon,
  History as HistoryIcon,
  Code as CodeIcon,
} from '@mui/icons-material';
import ModernReportsViewer from '../components/MedicalImaging/components/ModernReportsViewer';
import PastReportsViewer from '../components/MedicalImaging/components/PastReportsViewer';
import ModernReportsUsage from '../components/MedicalImaging/ModernReportsUsage';

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
      id={`medical-reports-tabpanel-${index}`}
      aria-labelledby={`medical-reports-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Fade in={true} timeout={500}>
          <Box sx={{ pt: 3 }}>
            {children}
          </Box>
        </Fade>
      )}
    </div>
  );
}

const MedicalReportsPage: React.FC = () => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(180deg, ${alpha(theme.palette.primary.main, 0.03)} 0%, ${theme.palette.background.default} 100%)`,
        pb: 6,
      }}
    >
      <Slide direction="down" in={true} timeout={500}>
        <Paper
          elevation={0}
          sx={{
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
            color: 'white',
            borderRadius: 0,
            borderBottomLeftRadius: theme.spacing(4),
            borderBottomRightRadius: theme.spacing(4),
          }}
        >
          <Container maxWidth="xl">
            <Box sx={{ py: 6 }}>
              <Typography
                variant="h2"
                fontWeight={700}
                gutterBottom
                sx={{
                  textShadow: '0 2px 4px rgba(0,0,0,0.2)',
                }}
              >
                Medical Imaging Reports
              </Typography>
              <Typography
                variant="h5"
                sx={{
                  opacity: 0.9,
                  maxWidth: 800,
                }}
              >
                Access, analyze, and manage medical imaging reports with AI-powered insights
              </Typography>
            </Box>
          </Container>
        </Paper>
      </Slide>

      <Container maxWidth="xl" sx={{ mt: -4 }}>
        <Paper
          elevation={3}
          sx={{
            borderRadius: 3,
            overflow: 'hidden',
            background: theme.palette.background.paper,
          }}
        >
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs
              value={activeTab}
              onChange={handleTabChange}
              centered
              sx={{
                '& .MuiTab-root': {
                  py: 3,
                  px: 4,
                  fontSize: '1rem',
                  fontWeight: 500,
                  textTransform: 'none',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    background: alpha(theme.palette.primary.main, 0.05),
                  },
                },
                '& .Mui-selected': {
                  color: theme.palette.primary.main,
                  fontWeight: 600,
                },
                '& .MuiTabs-indicator': {
                  height: 3,
                  borderRadius: '3px 3px 0 0',
                  background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                },
              }}
            >
              <Tab
                icon={<DashboardIcon />}
                iconPosition="start"
                label="Modern Reports Viewer"
                aria-label="modern reports viewer"
              />
              <Tab
                icon={<HistoryIcon />}
                iconPosition="start"
                label="Classic Reports Viewer"
                aria-label="classic reports viewer"
              />
              <Tab
                icon={<CodeIcon />}
                iconPosition="start"
                label="Usage & Documentation"
                aria-label="usage and documentation"
              />
            </Tabs>
          </Box>

          <Box sx={{ p: { xs: 2, sm: 3, md: 4 } }}>
            <TabPanel value={activeTab} index={0}>
              <ModernReportsViewer />
            </TabPanel>

            <TabPanel value={activeTab} index={1}>
              <PastReportsViewer />
            </TabPanel>

            <TabPanel value={activeTab} index={2}>
              <ModernReportsUsage />
            </TabPanel>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default MedicalReportsPage;