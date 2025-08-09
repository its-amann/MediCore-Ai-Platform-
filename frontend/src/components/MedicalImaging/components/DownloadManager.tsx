import React, { useState, ChangeEvent } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  FormLabel,
  FormGroup,
  FormControlLabel,
  Checkbox,
  RadioGroup,
  Radio,
  Box,
  Typography,
  CircularProgress,
  LinearProgress,
  Alert,
  Chip,
  Divider,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Download as DownloadIcon,
  PictureAsPdf as PdfIcon,
  Description as MarkdownIcon,
  Code as JsonIcon,
  Image as ImageIcon,
  Assessment as ReportIcon,
  Assessment,
} from '@mui/icons-material';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { MedicalReport, MedicalImage, HeatmapData } from '../types';
import { Finding } from '../types';
import api from '../../../api/axios';

interface DownloadManagerProps {
  open: boolean;
  onClose: () => void;
  report: MedicalReport;
  images: MedicalImage[];
  heatmaps: Map<string, HeatmapData>;
}

interface DownloadOptions {
  format: 'pdf' | 'markdown' | 'json' | 'zip';
  includeReport: boolean;
  includeImages: boolean;
  includeHeatmaps: boolean;
  includeCitations: boolean;
  imageQuality: 'high' | 'medium' | 'low';
}

const DownloadManager: React.FC<DownloadManagerProps> = ({
  open,
  onClose,
  report,
  images,
  heatmaps,
}) => {
  const theme = useTheme();
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<DownloadOptions>({
    format: 'pdf',
    includeReport: true,
    includeImages: true,
    includeHeatmaps: true,
    includeCitations: true,
    imageQuality: 'high',
  });

  const handleOptionChange = (field: keyof DownloadOptions, value: any) => {
    setOptions({ ...options, [field]: value });
  };

  const generateMarkdown = (): string => {
    let markdown = `# Medical Imaging Report\n\n`;
    markdown += `**Report ID:** ${report.id || 'N/A'}\n`;
    markdown += `**Patient:** ${report.patientName || 'Unknown'} (ID: ${report.patientId || 'N/A'})\n`;
    markdown += `**Study Type:** ${report.studyType || 'N/A'}\n`;
    markdown += `**Date:** ${report.createdAt ? new Date(report.createdAt).toLocaleDateString() : 'N/A'}\n\n`;
    
    markdown += `## Summary\n\n${report.summary || 'No summary available'}\n\n`;
    
    if (report.findings && report.findings.length > 0) {
      markdown += `## Findings\n\n`;
      report.findings.forEach((finding, index) => {
        markdown += `### ${index + 1}. ${finding.description}\n`;
        markdown += `- **Type:** ${finding.type}\n`;
        markdown += `- **Severity:** ${finding.severity || 'N/A'}\n`;
        markdown += `- **Confidence:** ${Math.round(finding.confidence * 100)}%\n`;
        if (finding.location) {
          markdown += `- **Location:** (${finding.location.x}, ${finding.location.y})\n`;
        }
        if (finding.recommendations?.length) {
          markdown += `- **Recommendations:**\n`;
          finding.recommendations.forEach((rec) => {
            markdown += `  - ${rec}\n`;
          });
        }
        markdown += '\n';
      });
    }
    
    if (report.conclusion) {
      markdown += `## Conclusion\n\n${report.conclusion}\n\n`;
    }
    
    if (report.recommendations && report.recommendations.length > 0) {
      markdown += `## Overall Recommendations\n\n`;
      report.recommendations.forEach((rec) => {
        markdown += `- ${rec}\n`;
      });
      markdown += '\n';
    }
    
    if (options.includeCitations && report.citations?.length) {
      markdown += `## References\n\n`;
      report.citations.forEach((citation, index) => {
        markdown += `${index + 1}. ${citation.text} - [${citation.source}](${citation.url || '#'})\n`;
      });
    }
    
    return markdown;
  };

  const generatePDF = async (): Promise<Blob> => {
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });
    
    let yPosition = 20;
    const pageHeight = pdf.internal.pageSize.height;
    const margin = 20;
    
    // Title
    pdf.setFontSize(20);
    pdf.text('Medical Imaging Report', margin, yPosition);
    yPosition += 15;
    
    // Patient info
    pdf.setFontSize(12);
    pdf.text(`Patient: ${report.patientName || 'Unknown'} (ID: ${report.patientId || 'N/A'})`, margin, yPosition);
    yPosition += 8;
    pdf.text(`Study Type: ${report.studyType || 'N/A'}`, margin, yPosition);
    yPosition += 8;
    pdf.text(`Date: ${report.createdAt ? new Date(report.createdAt).toLocaleDateString() : 'N/A'}`, margin, yPosition);
    yPosition += 15;
    
    // Summary
    pdf.setFontSize(14);
    pdf.text('Summary', margin, yPosition);
    yPosition += 8;
    pdf.setFontSize(11);
    
    const summaryLines = pdf.splitTextToSize(report.summary || 'No summary available', 170);
    summaryLines.forEach((line: string) => {
      if (yPosition > pageHeight - margin) {
        pdf.addPage();
        yPosition = margin;
      }
      pdf.text(line, margin, yPosition);
      yPosition += 6;
    });
    
    // Findings
    if (report.findings && report.findings.length > 0) {
      yPosition += 10;
      pdf.setFontSize(14);
      pdf.text('Findings', margin, yPosition);
      yPosition += 8;
      
      report.findings.forEach((finding, index) => {
        if (yPosition > pageHeight - 40) {
          pdf.addPage();
          yPosition = margin;
        }
        
        pdf.setFontSize(12);
        pdf.text(`${index + 1}. ${finding.description}`, margin, yPosition);
        yPosition += 6;
        
        pdf.setFontSize(10);
        pdf.text(`   Type: ${finding.type} | Severity: ${finding.severity || 'N/A'} | Confidence: ${Math.round(finding.confidence * 100)}%`, margin, yPosition);
        yPosition += 6;
        
        if (finding.recommendations?.length) {
          finding.recommendations.forEach((rec) => {
            const recLines = pdf.splitTextToSize(`   • ${rec}`, 160);
            recLines.forEach((line: string) => {
              if (yPosition > pageHeight - margin) {
                pdf.addPage();
                yPosition = margin;
              }
              pdf.text(line, margin, yPosition);
              yPosition += 5;
            });
          });
        }
        yPosition += 5;
      });
    }
    
    // Add images if requested
    if (options.includeImages && images.length > 0) {
      for (const image of images) {
        pdf.addPage();
        yPosition = margin;
        
        pdf.setFontSize(12);
        pdf.text(`Image: ${image.file.name}`, margin, yPosition);
        yPosition += 10;
        
        try {
          const imgData = await convertImageToBase64(image.preview);
          const imgProps = pdf.getImageProperties(imgData);
          const imgWidth = 170;
          const imgHeight = (imgProps.height * imgWidth) / imgProps.width;
          
          if (yPosition + imgHeight > pageHeight - margin) {
            pdf.addPage();
            yPosition = margin;
          }
          
          pdf.addImage(imgData, 'JPEG', margin, yPosition, imgWidth, imgHeight);
          yPosition += imgHeight + 10;
        } catch (err) {
          console.error('Error adding image to PDF:', err);
        }
      }
    }
    
    // Add heatmaps if requested
    if (options.includeHeatmaps && heatmaps.size > 0) {
      for (const [imageId, heatmap] of heatmaps) {
        pdf.addPage();
        yPosition = margin;
        
        pdf.setFontSize(12);
        pdf.text(`Heatmap Analysis`, margin, yPosition);
        yPosition += 10;
        
        try {
          const imgData = await convertImageToBase64(heatmap.heatmapUrl);
          const imgProps = pdf.getImageProperties(imgData);
          const imgWidth = 170;
          const imgHeight = (imgProps.height * imgWidth) / imgProps.width;
          
          pdf.addImage(imgData, 'JPEG', margin, yPosition, imgWidth, imgHeight);
          yPosition += imgHeight + 10;
          
          // Add regions info
          pdf.setFontSize(10);
          heatmap.regions.forEach((region) => {
            if (yPosition > pageHeight - margin) {
              pdf.addPage();
              yPosition = margin;
            }
            pdf.text(`${region.label}: ${Math.round(region.intensity * 100)}% intensity`, margin, yPosition);
            yPosition += 5;
          });
        } catch (err) {
          console.error('Error adding heatmap to PDF:', err);
        }
      }
    }
    
    return pdf.output('blob');
  };

  const convertImageToBase64 = (url: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Could not get canvas context'));
          return;
        }
        ctx.drawImage(img, 0, 0);
        resolve(canvas.toDataURL('image/jpeg', options.imageQuality === 'high' ? 0.9 : options.imageQuality === 'medium' ? 0.7 : 0.5));
      };
      img.onerror = reject;
      img.src = url;
    });
  };

  const handleDownload = async () => {
    setDownloading(true);
    setError(null);
    setProgress(0);
    
    try {
      switch (options.format) {
        case 'markdown':
          const markdown = generateMarkdown();
          const mdBlob = new Blob([markdown], { type: 'text/markdown' });
          saveAs(mdBlob, `medical-report-${report.id || 'report'}.md`);
          break;
          
        case 'json':
          const jsonData = {
            report: options.includeReport ? report : undefined,
            images: options.includeImages ? images.map(img => ({
              id: img.id,
              name: img.file.name,
              type: img.type,
              uploadedAt: img.uploadedAt,
            })) : undefined,
            heatmaps: options.includeHeatmaps ? Array.from(heatmaps.entries()).map(([id, data]) => ({
              imageId: id,
              regions: data.regions,
            })) : undefined,
          };
          const jsonBlob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
          saveAs(jsonBlob, `medical-report-${report.id || 'report'}.json`);
          break;
          
        case 'pdf':
          const pdfBlob = await generatePDF();
          saveAs(pdfBlob, `medical-report-${report.id || 'report'}.pdf`);
          break;
          
        case 'zip':
          const zip = new JSZip();
          
          // Add report as markdown
          if (options.includeReport) {
            zip.file('report.md', generateMarkdown());
            zip.file('report.json', JSON.stringify(report, null, 2));
          }
          
          // Add images
          if (options.includeImages) {
            const imagesFolder = zip.folder('images');
            for (const image of images) {
              try {
                const response = await fetch(image.preview);
                const blob = await response.blob();
                imagesFolder?.file(image.file.name, blob);
              } catch (err) {
                console.error('Error adding image to zip:', err);
              }
            }
          }
          
          // Add heatmaps
          if (options.includeHeatmaps) {
            const heatmapsFolder = zip.folder('heatmaps');
            let index = 0;
            for (const [imageId, heatmap] of heatmaps) {
              try {
                const response = await fetch(heatmap.heatmapUrl);
                const blob = await response.blob();
                heatmapsFolder?.file(`heatmap-${index}.png`, blob);
                heatmapsFolder?.file(`heatmap-${index}-data.json`, JSON.stringify(heatmap.regions, null, 2));
                index++;
              } catch (err) {
                console.error('Error adding heatmap to zip:', err);
              }
            }
          }
          
          const zipBlob = await zip.generateAsync({ type: 'blob' });
          saveAs(zipBlob, `medical-report-${report.id || 'report'}.zip`);
          break;
      }
      
      setProgress(100);
      setTimeout(() => {
        onClose();
        setProgress(0);
      }, 1000);
    } catch (err) {
      console.error('Download error:', err);
      setError('Failed to download report. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'pdf':
        return <PdfIcon />;
      case 'markdown':
        return <MarkdownIcon />;
      case 'json':
        return <JsonIcon />;
      case 'zip':
        return <DownloadIcon />;
      default:
        return <DownloadIcon />;
    }
  };

  const getEstimatedSize = () => {
    let size = 0;
    if (options.includeReport) size += 50; // KB
    if (options.includeImages) size += images.length * 500; // KB per image
    if (options.includeHeatmaps) size += heatmaps.size * 300; // KB per heatmap
    return Math.round(size / 1024); // Convert to MB
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <DownloadIcon />
          <Typography variant="h6">Download Report</Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        
        <FormControl component="fieldset" sx={{ mb: 3 }}>
          <FormLabel component="legend">Download Format</FormLabel>
          <RadioGroup
            value={options.format}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleOptionChange('format', e.target.value)}
            sx={{ mt: 1 }}
          >
            <FormControlLabel
              value="pdf"
              control={<Radio />}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <PdfIcon />
                  <Typography>PDF Document</Typography>
                  <Chip label="Recommended" size="small" color="primary" />
                </Box>
              }
            />
            <FormControlLabel
              value="markdown"
              control={<Radio />}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MarkdownIcon />
                  <Typography>Markdown File</Typography>
                </Box>
              }
            />
            <FormControlLabel
              value="json"
              control={<Radio />}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <JsonIcon />
                  <Typography>JSON Data</Typography>
                </Box>
              }
            />
            <FormControlLabel
              value="zip"
              control={<Radio />}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <DownloadIcon />
                  <Typography>ZIP Archive (All Files)</Typography>
                </Box>
              }
            />
          </RadioGroup>
        </FormControl>
        
        <Divider sx={{ my: 2 }} />
        
        <FormControl component="fieldset">
          <FormLabel component="legend">Include in Download</FormLabel>
          <FormGroup sx={{ mt: 1 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={options.includeReport}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => handleOptionChange('includeReport', e.target.checked)}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ReportIcon />
                  <Typography>Medical Report</Typography>
                </Box>
              }
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={options.includeImages}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => handleOptionChange('includeImages', e.target.checked)}
                  disabled={options.format === 'markdown' || options.format === 'json'}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ImageIcon />
                  <Typography>Original Images ({images.length})</Typography>
                </Box>
              }
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={options.includeHeatmaps}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => handleOptionChange('includeHeatmaps', e.target.checked)}
                  disabled={options.format === 'markdown' || options.format === 'json'}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Assessment />
                  <Typography>Heatmap Visualizations ({heatmaps.size})</Typography>
                </Box>
              }
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={options.includeCitations}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => handleOptionChange('includeCitations', e.target.checked)}
                />
              }
              label="Include Citations & References"
            />
          </FormGroup>
        </FormControl>
        
        {(options.format === 'pdf' || options.format === 'zip') && (
          <>
            <Divider sx={{ my: 2 }} />
            <FormControl component="fieldset">
              <FormLabel component="legend">Image Quality</FormLabel>
              <RadioGroup
                row
                value={options.imageQuality}
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleOptionChange('imageQuality', e.target.value)}
                sx={{ mt: 1 }}
              >
                <FormControlLabel value="high" control={<Radio />} label="High" />
                <FormControlLabel value="medium" control={<Radio />} label="Medium" />
                <FormControlLabel value="low" control={<Radio />} label="Low" />
              </RadioGroup>
            </FormControl>
          </>
        )}
        
        <Box
          sx={{
            mt: 3,
            p: 2,
            backgroundColor: alpha(theme.palette.info.main, 0.1),
            borderRadius: 1,
            border: `1px solid ${alpha(theme.palette.info.main, 0.3)}`,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            Estimated file size: ~{getEstimatedSize()} MB
          </Typography>
        </Box>
        
        {downloading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress variant="determinate" value={progress} />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
              Preparing download... {progress}%
            </Typography>
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose} disabled={downloading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleDownload}
          disabled={downloading}
          startIcon={downloading ? <CircularProgress size={20} /> : getFormatIcon(options.format)}
        >
          {downloading ? 'Downloading...' : 'Download'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DownloadManager;