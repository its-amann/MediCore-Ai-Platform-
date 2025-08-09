// MedicalImaging.fixes.tsx - Immediate fixes for TypeError and other critical issues

import { MedicalImage, Finding, Citation, MedicalReport } from './types';

/**
 * Fixed checkAndGenerateReport function that handles missing file properties
 * Replace the existing function at line 329-366 in MedicalImaging.tsx
 */
export const checkAndGenerateReportFixed = (
  images: MedicalImage[],
  analysisResults: Map<string, any>,
  patientId: string | undefined,
  setCurrentReport: (report: MedicalReport) => void,
  setShowReportViewer: (show: boolean) => void
) => {
  const completedImages = images.filter((img) => img.status === 'completed');
  const totalImages = images.filter((img) => img.status !== 'error');
  
  if (completedImages.length === totalImages.length && completedImages.length > 0) {
    const allFindings: Finding[] = [];
    const allCitations: Citation[] = [];
    let combinedSummary = '';
    
    completedImages.forEach((image) => {
      const result = analysisResults.get(image.id);
      if (result) {
        allFindings.push(...result.findings);
        // Use optional chaining to safely access file.name
        const imageName = image.file?.name || `Image ${image.id}`;
        combinedSummary += `\n\n## ${imageName}\n${result.summary}`;
      }
    });
    
    const report: MedicalReport = {
      id: `report-${Date.now()}`,
      patientId: patientId || 'unknown',
      patientName: 'Patient Name',
      createdAt: new Date(),
      updatedAt: new Date(),
      studyType: detectStudyType(completedImages),
      images: completedImages.map(img => ({
        ...img,
        // Ensure file property exists or create a safe alternative
        file: img.file || { 
          name: `processed-${img.id}`, 
          size: 0, 
          type: img.type,
          lastModified: Date.now()
        } as File
      })),
      findings: allFindings,
      summary: combinedSummary,
      conclusion: generateConclusion(allFindings),
      recommendations: generateRecommendations(allFindings),
      markdownContent: generateMarkdownReportFixed(completedImages, allFindings),
      citations: allCitations,
    };
    
    setCurrentReport(report);
    setShowReportViewer(true);
  }
};

/**
 * Fixed generateMarkdownReport function with safe file.name access
 * Replace the existing function at line 398-418
 */
export const generateMarkdownReportFixed = (images: MedicalImage[], findings: Finding[]): string => {
  let markdown = '# Medical Imaging Analysis Report\n\n';
  markdown += `Generated on: ${new Date().toLocaleDateString()}\n\n`;
  
  markdown += '## Images Analyzed\n\n';
  images.forEach((img, idx) => {
    // Use optional chaining for safe access
    const imageName = img.file?.name || `Image ${idx + 1}`;
    markdown += `${idx + 1}. ${imageName} (${img.type})\n`;
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

/**
 * Helper function to detect study type
 */
const detectStudyType = (images: MedicalImage[]): string => {
  const types = images.map(img => img.type);
  const uniqueTypes = [...new Set(types)];
  return uniqueTypes.length === 1 ? uniqueTypes[0] : 'Multi-Modal Study';
};

/**
 * Helper function to generate conclusion
 */
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

/**
 * Helper function to generate recommendations
 */
const generateRecommendations = (findings: Finding[]): string[] => {
  const recommendations = new Set<string>();
  
  findings.forEach(finding => {
    if (finding.recommendations) {
      finding.recommendations.forEach(rec => recommendations.add(rec));
    }
  });
  
  return Array.from(recommendations);
};

/**
 * Enhanced file validation function
 */
export const validateFile = (file: File, maxFileSize: number): { valid: boolean; error?: string } => {
  // Check file size
  if (file.size > maxFileSize) {
    return { 
      valid: false, 
      error: `File size exceeds maximum allowed size of ${maxFileSize / (1024 * 1024)}MB` 
    };
  }
  
  // Check file type
  const validTypes = ['image/jpeg', 'image/png', 'image/dicom', 'application/dicom'];
  const validExtensions = ['dcm', 'dicom', 'jpg', 'jpeg', 'png'];
  
  if (!validTypes.includes(file.type)) {
    // Additional check for DICOM files without proper MIME type
    const extension = file.name.toLowerCase().split('.').pop();
    if (!validExtensions.includes(extension || '')) {
      return { 
        valid: false, 
        error: 'Invalid file type. Supported types: JPEG, PNG, DICOM' 
      };
    }
  }
  
  // Check filename for potential security issues
  if (!/^[\w\-. ]+$/i.test(file.name)) {
    return {
      valid: false,
      error: 'Filename contains invalid characters'
    };
  }
  
  return { valid: true };
};

/**
 * Update image status while preserving file property
 */
export const updateImageStatusFixed = (
  images: MedicalImage[],
  imageId: string,
  status: MedicalImage['status'],
  progress?: number
): MedicalImage[] => {
  return images.map((img) => {
    if (img.id === imageId) {
      return {
        ...img,
        status,
        ...(progress !== undefined && { progress }),
        // Preserve the file property
        file: img.file
      };
    }
    return img;
  });
};

/**
 * Safe image preview creation
 */
export const createSafeImagePreview = async (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      const result = e.target?.result;
      if (typeof result === 'string') {
        // Basic validation
        if (result.startsWith('data:image/')) {
          resolve(result);
        } else {
          reject(new Error('Invalid image data'));
        }
      } else {
        reject(new Error('Failed to read file'));
      }
    };
    
    reader.onerror = () => reject(new Error('Failed to read file'));
    
    try {
      reader.readAsDataURL(file);
    } catch (error) {
      reject(error);
    }
  });
};

/**
 * Integration instructions:
 * 
 * 1. Replace the checkAndGenerateReport function (lines 329-366) with checkAndGenerateReportFixed
 * 2. Replace the generateMarkdownReport function (lines 398-418) with generateMarkdownReportFixed
 * 3. Add validateFile function to the onDrop callback for file validation
 * 4. Replace updateImageStatus with updateImageStatusFixed to preserve file property
 * 5. Use createSafeImagePreview instead of URL.createObjectURL for secure previews
 * 
 * Example integration in onDrop:
 * 
 * const onDrop = useCallback(async (acceptedFiles: File[]) => {
 *   // Validate files
 *   const validFiles = acceptedFiles.filter(file => {
 *     const validation = validateFile(file, maxFileSize);
 *     if (!validation.valid) {
 *       showAlert(`${file.name}: ${validation.error}`, 'error');
 *       return false;
 *     }
 *     return true;
 *   });
 *   
 *   // Create safe previews
 *   const newImages = await Promise.all(validFiles.map(async (file) => {
 *     const preview = await createSafeImagePreview(file);
 *     return {
 *       id: `${Date.now()}-${Math.random()}`,
 *       file,
 *       preview,
 *       type: detectImageType(file.name),
 *       uploadedAt: new Date(),
 *       status: 'uploading' as const,
 *       progress: 0,
 *     };
 *   }));
 *   
 *   // Continue with upload...
 * }, [maxFileSize]);
 */