export interface MedicalImage {
  id: string;
  file: File;
  preview: string;
  type: 'CT' | 'MRI' | 'X-ray' | 'Ultrasound' | 'PET' | 'Other';
  uploadedAt: Date;
  status: 'uploading' | 'uploaded' | 'analyzing' | 'completed' | 'error';
  progress?: number;
  reportId?: string;
}

export interface AnalysisResult {
  id: string;
  imageId: string;
  findings: Finding[];
  summary: string;
  confidence: number;
  processingTime: number;
  generatedAt: Date;
  reportUrl?: string;
}

export interface Finding {
  id: string;
  type: 'anomaly' | 'normal' | 'attention_required';
  description: string;
  confidence: number;
  location?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  severity?: 'low' | 'medium' | 'high' | 'critical';
  recommendations?: string[];
}

export interface HeatmapData {
  imageId: string;
  heatmapUrl: string;
  regions: HeatmapRegion[];
}

export interface HeatmapRegion {
  id: string;
  intensity: number;
  label: string;
  coordinates: {
    x: number;
    y: number;
    radius: number;
  };
}

export interface SimilarReport {
  id: string;
  patientId: string;
  date: Date;
  similarity: number;
  diagnosis: string;
  imageType: string;
  thumbnailUrl?: string;
}

export interface MedicalImagingProps {
  patientId?: string;
  onAnalysisComplete?: (results: AnalysisResult[]) => void;
  allowMultiple?: boolean;
  acceptedFileTypes?: string[];
  maxFileSize?: number; // in bytes
}

export interface UploadResponse {
  id: string;
  message: string;
  imageUrl: string;
}

export interface AnalysisResponse {
  results: AnalysisResult;
  heatmap: HeatmapData;
  similarReports: SimilarReport[];
}

export interface ReportDownloadOptions {
  format: 'pdf' | 'docx' | 'json' | 'markdown';
  includeImages: boolean;
  includeHeatmaps: boolean;
  includeSimilarReports: boolean;
}

// Enhanced types for new features
export interface MedicalReport {
  id?: string;
  report_id?: string;
  case_id?: string;
  patientId?: string;
  patientName?: string;
  patient_name?: string;
  createdAt?: Date;
  created_at?: string;
  updatedAt?: Date;
  updated_at?: string;
  studyType?: string;
  study_type?: string;
  studyDate?: Date | string;
  study_date?: string;
  images?: MedicalImage[];
  findings?: Finding[];
  key_findings?: string[];
  summary?: string;
  conclusion?: string;
  recommendations?: string[];
  markdownContent?: string;
  citations?: Citation[];
  metadata?: Record<string, any>;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  radiologicalAnalysis?: string;
  overall_analysis?: string;
  clinicalImpression?: string;
  clinical_impression?: string;
  final_report?: {
    content: string;
    sections: string[];
    generated_at?: string;
    literature_included?: boolean;
  };
  literature_references?: LiteratureReference[];
  quality_score?: number;
  abnormalities_detected?: Finding[];
  heatmap_data?: any;
  status?: string;
}

export interface LiteratureReference {
  title: string;
  authors?: string[];
  journal?: string;
  year?: string;
  type?: string;
  abstract?: string;
  url?: string;
  relevance_score?: number;
  patient_demographics?: string;
  treatment?: string;
  outcome?: string;
}

export interface Citation {
  id: string;
  text: string;
  source: string;
  url?: string;
  relevance: number;
  title?: string;
  authors?: string;
  year?: string | number;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  reportContext?: {
    reportId: string;
    findingIds?: string[];
    imageIds?: string[];
  };
}

export interface ChatSession {
  id: string;
  reportId: string;
  messages: ChatMessage[];
  createdAt: Date;
  lastMessageAt: Date;
}

export interface PastReportSummary {
  id: string;
  patientId: string;
  patientName: string;
  studyDate: Date;
  studyType: string;
  findingsCount: number;
  criticalFindings: number;
  thumbnailUrl?: string;
  summary: string;
}

export interface ReportFilter {
  patientId?: string;
  dateRange?: {
    start: Date;
    end?: Date;
  };
  studyTypes?: string[];
  findingTypes?: string[];
  searchQuery?: string;
}