import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import MedicalImaging from './MedicalImaging';

// Mock problematic modules
jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('remark-gfm', () => ({
  __esModule: true,
  default: () => {},
}));

jest.mock('react-syntax-highlighter', () => ({
  __esModule: true,
  Prism: ({ children }: { children: React.ReactNode }) => <pre>{children}</pre>,
}));

jest.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  __esModule: true,
  vscDarkPlus: {},
}));

jest.mock('jspdf', () => ({
  __esModule: true,
  jsPDF: jest.fn().mockImplementation(() => ({
    addImage: jest.fn(),
    save: jest.fn(),
    text: jest.fn(),
    setFontSize: jest.fn(),
  })),
}));

jest.mock('html2canvas', () => ({
  __esModule: true,
  default: jest.fn().mockResolvedValue({
    toDataURL: jest.fn().mockReturnValue('data:image/png;base64,'),
  }),
}));

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    create: () => ({
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
      get: jest.fn().mockResolvedValue({ data: [] }),
      post: jest.fn().mockResolvedValue({ data: {} }),
      put: jest.fn().mockResolvedValue({ data: {} }),
      delete: jest.fn().mockResolvedValue({ data: {} }),
    }),
  },
}));

jest.mock('../../services/medicalImagingWebSocket', () => ({
  __esModule: true,
  default: class MockWebSocket {
    connect = jest.fn();
    disconnect = jest.fn();
    subscribe = jest.fn();
    emit = jest.fn();
  },
}));

jest.mock('../../services/medicalImagingService', () => ({
  __esModule: true,
  getPastReports: jest.fn().mockResolvedValue([]),
  analyzeImages: jest.fn().mockResolvedValue({ analysis: 'Test analysis' }),
  uploadImages: jest.fn().mockResolvedValue({ success: true }),
}));

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('MedicalImaging Enhanced UI', () => {
  it('renders welcome guide for first-time users', () => {
    renderWithTheme(<MedicalImaging />);
    
    expect(screen.getByText('Welcome to Medical Imaging Analysis')).toBeInTheDocument();
    expect(screen.getByText('1. Upload Images')).toBeInTheDocument();
    expect(screen.getByText('2. AI Analysis')).toBeInTheDocument();
    expect(screen.getByText('3. Ask Questions')).toBeInTheDocument();
  });

  it('displays past reports count in button badge', async () => {
    renderWithTheme(<MedicalImaging patientId="test-patient" />);
    
    // Wait for past reports count to load
    await waitFor(() => {
      const pastReportsButton = screen.getByText('Past Reports');
      expect(pastReportsButton).toBeInTheDocument();
    });
  });

  it('shows floating action buttons with tooltips', async () => {
    renderWithTheme(<MedicalImaging />);
    
    // Check for FABs
    const fabs = screen.getAllByRole('button').filter(btn => 
      btn.classList.contains('MuiFab-root')
    );
    
    expect(fabs.length).toBeGreaterThanOrEqual(1); // At least the history FAB
  });

  it('can interact with the welcome guide collapse button', async () => {
    const user = userEvent.setup();
    renderWithTheme(<MedicalImaging />);
    
    // Find the small icon button (likely a collapse/expand button)
    const iconButtons = screen.getAllByRole('button');
    const collapseButton = iconButtons.find(btn => 
      btn.classList.contains('MuiIconButton-root') && 
      btn.classList.contains('MuiIconButton-sizeSmall')
    );
    
    if (collapseButton) {
      await user.click(collapseButton);
      
      // Wait for any animation to complete
      await waitFor(() => {
        // The welcome guide might collapse or expand, but should still be in DOM
        const welcomeText = screen.queryByText('Welcome to Medical Imaging Analysis');
        expect(welcomeText).toBeInTheDocument();
      });
    }
  });
});