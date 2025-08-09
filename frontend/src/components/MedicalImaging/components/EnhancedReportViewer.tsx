import React, { useState, useRef, useMemo, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  IconButton,
  Tooltip,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Link,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  Print as PrintIcon,
  Share as ShareIcon,
  FormatQuote as FormatQuoteIcon,
  LocalHospital as LocalHospitalIcon,
  Assessment as AssessmentIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  FileCopy as FileCopyIcon,
  PictureAsPdf as PictureAsPdfIcon,
  Description as DescriptionIcon,
  Code as CodeIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import { MedicalReport, Citation } from '../types';

// Medical term highlighting patterns
const MEDICAL_TERMS = {
  anatomy: /\b(heart|lung|liver|kidney|brain|spine|bone|muscle|artery|vein|nerve)\b/gi,
  conditions: /\b(cancer|tumor|fracture|inflammation|infection|lesion|anomaly|abnormality)\b/gi,
  procedures: /\b(MRI|CT|X-ray|ultrasound|biopsy|surgery|scan|examination)\b/gi,
  measurements: /\b(\d+\.?\d*\s*(mm|cm|ml|mg|cc))\b/gi,
};

interface EnhancedReportViewerProps {
  report: MedicalReport;
  onCitationClick?: (citation: Citation) => void;
  onDownload?: (format: 'pdf' | 'markdown' | 'json') => void;
}

const EnhancedReportViewer: React.FC<EnhancedReportViewerProps> = ({
  report,
  onCitationClick,
  onDownload,
}) => {
  const theme = useTheme();
  const reportRef = useRef<HTMLDivElement>(null);
  const [expandedSections, setExpandedSections] = useState<string[]>(['summary', 'findings', 'full_report']);
  const [citationDialogOpen, setCitationDialogOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [downloading, setDownloading] = useState(false);

  const handleCitationClick = useCallback((citation: Citation) => {
    setSelectedCitation(citation);
    setCitationDialogOpen(true);
    onCitationClick?.(citation);
  }, [onCitationClick]);

  // Custom markdown components with medical term highlighting
  const markdownComponents = useMemo(() => ({
    p: ({ children, ...props }: any) => {
      const highlightMedicalTerms = (text: string) => {
        let result = text;
        Object.entries(MEDICAL_TERMS).forEach(([category, pattern]) => {
          result = result.replace(pattern, (match) => {
            const color = {
              anatomy: theme.palette.info.main,
              conditions: theme.palette.error.main,
              procedures: theme.palette.primary.main,
              measurements: theme.palette.success.main,
            }[category] || theme.palette.text.primary;
            
            return `<mark style="background-color: ${alpha(color, 0.2)}; color: ${color}; padding: 2px 4px; border-radius: 4px; font-weight: 500;">${match}</mark>`;
          });
        });
        return <span dangerouslySetInnerHTML={{ __html: result }} />;
      };

      if (typeof children === 'string') {
        return <Typography variant="body1" paragraph {...props}>{highlightMedicalTerms(children)}</Typography>;
      }
      return <Typography variant="body1" paragraph {...props}>{children}</Typography>;
    },
    code: ({ inline, className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={match[1]}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    a: ({ href, children, ...props }: any) => {
      // Check if this is a citation link
      const citationMatch = href?.match(/^#citation-(\d+)$/);
      if (citationMatch && report.citations) {
        const citationIndex = parseInt(citationMatch[1]) - 1;
        const citation = report.citations[citationIndex];
        if (citation) {
          return (
            <Tooltip title={`Source: ${citation.source}`}>
              <Link
                component="button"
                variant="body2"
                onClick={() => handleCitationClick(citation)}
                sx={{ 
                  verticalAlign: 'super', 
                  fontSize: '0.75em',
                  fontWeight: 600,
                }}
              >
                [{citationIndex + 1}]
              </Link>
            </Tooltip>
          );
        }
      }
      return <Link href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</Link>;
    },
    h1: ({ children, ...props }: any) => <Typography variant="h4" gutterBottom {...props}>{children}</Typography>,
    h2: ({ children, ...props }: any) => <Typography variant="h5" gutterBottom {...props}>{children}</Typography>,
    h3: ({ children, ...props }: any) => <Typography variant="h6" gutterBottom {...props}>{children}</Typography>,
    blockquote: ({ children, ...props }: any) => (
      <Paper
        elevation={0}
        sx={{
          borderLeft: `4px solid ${theme.palette.primary.main}`,
          pl: 2,
          py: 1,
          my: 2,
          backgroundColor: alpha(theme.palette.primary.main, 0.05),
        }}
        {...props}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
          <FormatQuoteIcon sx={{ mr: 1, mt: 0.5, color: theme.palette.primary.main, fontSize: 20 }} />
          <Box>{children}</Box>
        </Box>
      </Paper>
    ),
  }), [theme, report.citations, handleCitationClick]);

  const handleSectionToggle = (section: string) => {
    setExpandedSections((prev) =>
      prev.includes(section)
        ? prev.filter((s) => s !== section)
        : [...prev, section]
    );
  };

  const generatePDF = async () => {
    if (!reportRef.current) return;
    
    setDownloading(true);
    try {
      const canvas = await html2canvas(reportRef.current as HTMLElement, {
        logging: false,
        useCORS: true,
      } as any);
      
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });
      
      const imgWidth = 210;
      const pageHeight = 295;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;
      
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
      
      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }
      
      pdf.save(`medical-report-${report.id}-${new Date().getTime()}.pdf`);
      onDownload?.('pdf');
    } catch (error) {
      console.error('Error generating PDF:', error);
    } finally {
      setDownloading(false);
    }
  };

  const downloadMarkdown = () => {
    const markdown = report.markdownContent || generateMarkdownFromReport();
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `medical-report-${report.id}-${new Date().getTime()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    onDownload?.('markdown');
  };

  const downloadJSON = () => {
    const json = JSON.stringify(report, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `medical-report-${report.id}-${new Date().getTime()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    onDownload?.('json');
  };

  const generateMarkdownFromReport = () => {
    let markdown = `# Medical Imaging Report\n\n`;
    markdown += `**Patient:** ${report.patientName} (ID: ${report.patientId})\n`;
    markdown += `**Study Type:** ${report.studyType}\n`;
    markdown += `**Study Date:** ${report.createdAt ? new Date(report.createdAt).toLocaleDateString() : 'N/A'}\n\n`;
    
    markdown += `## Summary\n\n${report.summary || 'No summary available'}\n\n`;
    
    if (report.findings && report.findings.length > 0) {
      markdown += `## Findings\n\n`;
      report.findings.forEach((finding, index) => {
        markdown += `### ${index + 1}. ${finding.description}\n`;
        markdown += `- **Type:** ${finding.type}\n`;
        markdown += `- **Severity:** ${finding.severity || 'N/A'}\n`;
        markdown += `- **Confidence:** ${Math.round(finding.confidence * 100)}%\n`;
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
      markdown += `## Recommendations\n\n`;
      report.recommendations.forEach((rec) => {
        markdown += `- ${rec}\n`;
      });
    }
    
    return markdown;
  };

  const getSeverityIcon = (severity?: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <WarningIcon color="error" />;
      case 'medium':
        return <InfoIcon color="warning" />;
      case 'low':
      case 'normal':
        return <CheckCircleIcon color="success" />;
      default:
        return <InfoIcon color="inherit" />;
    }
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
      case 'normal':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Paper
        ref={reportRef}
        elevation={0}
        sx={{
          p: 4,
          backgroundColor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: 'blur(10px)',
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          borderRadius: 2,
        }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
          <Box>
            <Typography variant="h4" gutterBottom fontWeight={600}>
              Medical Imaging Report
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip
                icon={<LocalHospitalIcon />}
                label={`Patient: ${report.patientName}`}
                variant="outlined"
              />
              <Chip
                icon={<AssessmentIcon />}
                label={report.studyType}
                color="primary"
                variant="outlined"
              />
              <Chip
                label={report.createdAt ? new Date(report.createdAt).toLocaleDateString() : 'N/A'}
                variant="outlined"
              />
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Download as PDF">
              <IconButton
                onClick={generatePDF}
                disabled={downloading}
                sx={{ 
                  backgroundColor: alpha(theme.palette.background.paper, 0.8),
                  '&:hover': { backgroundColor: theme.palette.action.hover },
                }}
              >
                {downloading ? <CircularProgress size={24} /> : <PictureAsPdfIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Download as Markdown">
              <IconButton
                onClick={downloadMarkdown}
                sx={{ 
                  backgroundColor: alpha(theme.palette.background.paper, 0.8),
                  '&:hover': { backgroundColor: theme.palette.action.hover },
                }}
              >
                <DescriptionIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Download as JSON">
              <IconButton
                onClick={downloadJSON}
                sx={{ 
                  backgroundColor: alpha(theme.palette.background.paper, 0.8),
                  '&:hover': { backgroundColor: theme.palette.action.hover },
                }}
              >
                <CodeIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Print">
              <IconButton
                onClick={() => window.print()}
                sx={{ 
                  backgroundColor: alpha(theme.palette.background.paper, 0.8),
                  '&:hover': { backgroundColor: theme.palette.action.hover },
                }}
              >
                <PrintIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Share">
              <IconButton
                sx={{ 
                  backgroundColor: alpha(theme.palette.background.paper, 0.8),
                  '&:hover': { backgroundColor: theme.palette.action.hover },
                }}
              >
                <ShareIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Report Content */}
        <Box sx={{ mt: 3 }}>
          {/* Summary Section */}
          <Accordion
            expanded={expandedSections.includes('summary')}
            onChange={() => handleSectionToggle('summary')}
            elevation={0}
            sx={{
              backgroundColor: 'transparent',
              '&:before': { display: 'none' },
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Summary</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ pl: 2 }}>
                {report.markdownContent ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {report.summary || 'No summary available'}
                  </ReactMarkdown>
                ) : (
                  <Typography variant="body1">{report.summary || 'No summary available'}</Typography>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>

          {/* Findings Section */}
          {report.findings && report.findings.length > 0 && (
            <Accordion
              expanded={expandedSections.includes('findings')}
              onChange={() => handleSectionToggle('findings')}
              elevation={0}
              sx={{
                backgroundColor: 'transparent',
                '&:before': { display: 'none' },
                mt: 2,
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography variant="h6">Findings</Typography>
                  <Chip
                    label={`${report.findings?.length || 0} total`}
                    size="small"
                    color="primary"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ pl: 2 }}>
                  {(report.findings || []).map((finding, index) => (
                    <Paper
                      key={finding.id}
                      elevation={0}
                      sx={{
                        p: 2,
                        mb: 2,
                        backgroundColor: alpha(theme.palette.background.default, 0.5),
                        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                        {getSeverityIcon(finding.severity)}
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle1" fontWeight={500} gutterBottom>
                            {finding.description}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                            <Chip
                              label={finding.type}
                              size="small"
                              variant="outlined"
                            />
                            {finding.severity && (
                              <Chip
                                label={finding.severity}
                                size="small"
                                color={getSeverityColor(finding.severity) as any}
                                variant="outlined"
                              />
                            )}
                            <Chip
                              label={`${Math.round(finding.confidence * 100)}% confidence`}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                          {finding.recommendations && finding.recommendations.length > 0 && (
                            <Box sx={{ mt: 2 }}>
                              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                                Recommendations:
                              </Typography>
                              <Box component="ul" sx={{ pl: 3, m: 0 }}>
                                {finding.recommendations.map((rec, idx) => (
                                  <li key={idx}>
                                    <Typography variant="body2">{rec}</Typography>
                                  </li>
                                ))}
                              </Box>
                            </Box>
                          )}
                        </Box>
                      </Box>
                    </Paper>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Conclusion Section */}
          {report.conclusion && (
            <Accordion
              expanded={expandedSections.includes('conclusion')}
              onChange={() => handleSectionToggle('conclusion')}
              elevation={0}
              sx={{
                backgroundColor: 'transparent',
                '&:before': { display: 'none' },
                mt: 2,
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Conclusion</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ pl: 2 }}>
                  {report.markdownContent ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={markdownComponents}
                    >
                      {report.conclusion || 'No conclusion available'}
                    </ReactMarkdown>
                  ) : (
                    <Typography variant="body1">{report.conclusion || 'No conclusion available'}</Typography>
                  )}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Recommendations Section */}
          {report.recommendations && report.recommendations.length > 0 && (
            <Accordion
              expanded={expandedSections.includes('recommendations')}
              onChange={() => handleSectionToggle('recommendations')}
              elevation={0}
              sx={{
                backgroundColor: 'transparent',
                '&:before': { display: 'none' },
                mt: 2,
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Recommendations</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ pl: 2 }}>
                  <Box component="ul" sx={{ pl: 3, m: 0 }}>
                    {(report.recommendations || []).map((rec, idx) => (
                      <li key={idx}>
                        <Typography variant="body1">{rec}</Typography>
                      </li>
                    ))}
                  </Box>
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Full Comprehensive Report Section */}
          {report.final_report?.content && (
            <Accordion
              expanded={expandedSections.includes('full_report')}
              onChange={() => handleSectionToggle('full_report')}
              elevation={0}
              sx={{
                backgroundColor: 'transparent',
                '&:before': { display: 'none' },
                mt: 2,
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography variant="h6">Comprehensive Report</Typography>
                  {report.final_report.literature_included && (
                    <Chip
                      icon={<FormatQuoteIcon />}
                      label="Literature Included"
                      size="small"
                      color="primary"
                    />
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ pl: 2 }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {report.final_report.content}
                  </ReactMarkdown>
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Literature References Section */}
          {report.literature_references && report.literature_references.length > 0 && (
            <Accordion
              expanded={expandedSections.includes('literature')}
              onChange={() => handleSectionToggle('literature')}
              elevation={0}
              sx={{
                backgroundColor: 'transparent',
                '&:before': { display: 'none' },
                mt: 2,
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography variant="h6">Medical Literature</Typography>
                  <Chip
                    label={`${report.literature_references.length} sources`}
                    size="small"
                    color="secondary"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ pl: 2 }}>
                  {report.literature_references.map((ref, index) => (
                    <Paper
                      key={index}
                      elevation={0}
                      sx={{
                        p: 2,
                        mb: 2,
                        backgroundColor: alpha(theme.palette.background.default, 0.5),
                        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                      }}
                    >
                      <Typography variant="subtitle1" fontWeight={500} gutterBottom>
                        {ref.title}
                      </Typography>
                      {ref.authors && (
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {ref.authors.join(', ')} • {ref.year}
                        </Typography>
                      )}
                      {ref.journal && (
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {ref.journal}
                        </Typography>
                      )}
                      {ref.abstract && (
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          {ref.abstract}
                        </Typography>
                      )}
                      {ref.url && (
                        <Link
                          href={ref.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          sx={{ display: 'inline-flex', mt: 1 }}
                        >
                          View Source
                        </Link>
                      )}
                      {ref.relevance_score && (
                        <Box sx={{ mt: 1 }}>
                          <Chip
                            label={`Relevance: ${ref.relevance_score}/10`}
                            size="small"
                            color={ref.relevance_score >= 7 ? "success" : "default"}
                          />
                        </Box>
                      )}
                    </Paper>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Citations Section */}
          {report.citations && report.citations.length > 0 && (
            <Accordion
              expanded={expandedSections.includes('citations')}
              onChange={() => handleSectionToggle('citations')}
              elevation={0}
              sx={{
                backgroundColor: 'transparent',
                '&:before': { display: 'none' },
                mt: 2,
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">References</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ pl: 2 }}>
                  {report.citations.map((citation, index) => (
                    <Box key={citation.id} sx={{ mb: 1 }}>
                      <Typography variant="body2">
                        [{index + 1}] {citation.text} - 
                        {citation.url ? (
                          <Link href={citation.url} target="_blank" rel="noopener noreferrer" sx={{ ml: 1 }}>
                            {citation.source}
                          </Link>
                        ) : (
                          <span style={{ marginLeft: 4 }}>{citation.source}</span>
                        )}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}
        </Box>
      </Paper>

      {/* Citation Dialog */}
      <Dialog
        open={citationDialogOpen}
        onClose={() => setCitationDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        {selectedCitation && (
          <>
            <DialogTitle>Citation Details</DialogTitle>
            <DialogContent>
              <Box sx={{ pt: 2 }}>
                <Typography variant="body1" paragraph>
                  {selectedCitation.text}
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Source
                </Typography>
                <Typography variant="body2" paragraph>
                  {selectedCitation.source}
                </Typography>
                {selectedCitation.url && (
                  <>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Reference URL
                    </Typography>
                    <Link
                      href={selectedCitation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                    >
                      {selectedCitation.url}
                    </Link>
                  </>
                )}
                <Box sx={{ mt: 2 }}>
                  <Chip
                    label={`Relevance: ${Math.round(selectedCitation.relevance * 100)}%`}
                    color="primary"
                    size="small"
                  />
                </Box>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setCitationDialogOpen(false)}>Close</Button>
              {selectedCitation.url && (
                <Button
                  variant="contained"
                  href={selectedCitation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open Source
                </Button>
              )}
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default EnhancedReportViewer;