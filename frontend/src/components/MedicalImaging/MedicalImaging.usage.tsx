import React from 'react';
import { Box, Container, Typography } from '@mui/material';
import { MedicalImaging } from './index';
// import { AnalysisResult } from './types'; // Used in commented examples

/**
 * Example usage of the MedicalImaging component
 */
const MedicalImagingExample: React.FC = () => {
  // Example patient ID and handler are shown in commented out advanced usage below

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h3" gutterBottom align="center">
          Medical Imaging Analysis System
        </Typography>
        
        <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 4 }}>
          Upload and analyze medical images with AI-powered insights
        </Typography>

        {/* Basic usage with all default props */}
        <MedicalImaging />

        {/* Advanced usage with custom configuration */}
        {/* 
        <MedicalImaging
          patientId={patientId}
          onAnalysisComplete={handleAnalysisComplete}
          allowMultiple={true}
          acceptedFileTypes={[
            'image/jpeg',
            'image/png',
            'image/dicom',
            'application/dicom'
          ]}
          maxFileSize={100 * 1024 * 1024} // 100MB
        />
        */}
      </Box>
    </Container>
  );
};

// Example of using the component in a patient context
export const PatientMedicalImaging: React.FC<{ patientId: string }> = ({ patientId }) => {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Patient Medical Images
      </Typography>
      
      <MedicalImaging
        patientId={patientId}
        onAnalysisComplete={(results) => {
          // Update patient record with new analysis
          console.log(`Updating patient ${patientId} with new analysis results`);
        }}
      />
    </Box>
  );
};

// Example of using the component in a specific imaging type context
export const CTScanAnalysis: React.FC = () => {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        CT Scan Analysis
      </Typography>
      
      <MedicalImaging
        acceptedFileTypes={['image/dicom', 'application/dicom']} // Only accept DICOM files
        allowMultiple={false} // Single file at a time
        onAnalysisComplete={(results) => {
          // Handle CT-specific analysis
          const ctFindings = results[0]?.findings.filter(f => f.type === 'anomaly');
          console.log('CT anomalies detected:', ctFindings);
        }}
      />
    </Box>
  );
};

export default MedicalImagingExample;