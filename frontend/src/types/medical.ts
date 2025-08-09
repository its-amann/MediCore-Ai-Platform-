/**
 * Medical Imaging and Report Types
 * This file contains comprehensive type definitions for the medical imaging service
 * to ensure type compatibility between frontend components and backend API responses.
 */

// Import AnalysisResult type for use in this file
import type { AnalysisResult } from '../components/MedicalImaging/types';

// Re-export common types from MedicalImaging component
export type {
  MedicalImage,
  AnalysisResult,
  Finding,
  HeatmapData,
  HeatmapRegion,
  SimilarReport,
  MedicalImagingProps,
  UploadResponse,
  AnalysisResponse,
  ReportDownloadOptions,
  MedicalReport,
  Citation,
  ChatMessage,
  ChatSession,
  PastReportSummary,
  ReportFilter
} from '../components/MedicalImaging/types';

/**
 * Imaging Report Interface
 * Represents a medical imaging report with analysis results
 */
export interface ImagingReport {
  id: string;
  reportId?: string;
  caseId?: string;
  patientId: string;
  patientName: string;
  patientAge?: number;
  patientGender?: 'male' | 'female' | 'other';
  referringPhysician?: string;
  reportDate: Date | string;
  studyDate: Date | string;
  studyType: StudyType;
  modality: ImagingModality;
  bodyPart?: string;
  indication?: string;
  technique?: string;
  comparison?: string;
  findings: ImagingFinding[];
  impression: string;
  recommendations?: string[];
  status: ReportStatus;
  reportingRadiologist?: {
    id: string;
    name: string;
    credentials?: string;
    signature?: string;
  };
  images: ImagingFile[];
  metadata?: {
    accessionNumber?: string;
    studyInstanceUID?: string;
    seriesInstanceUID?: string;
    priority?: 'routine' | 'urgent' | 'stat';
    department?: string;
    facility?: string;
  };
  timestamps: {
    created: Date | string;
    updated?: Date | string;
    finalized?: Date | string;
    signed?: Date | string;
  };
}

/**
 * Imaging Finding Interface
 * Represents individual findings within an imaging report
 */
export interface ImagingFinding {
  id: string;
  category: FindingCategory;
  type: string;
  description: string;
  location?: AnatomicalLocation;
  measurements?: Measurement[];
  severity: FindingSeverity;
  confidence: number;
  comparisonToPrior?: 'new' | 'unchanged' | 'improved' | 'worsened';
  followUpRecommended?: boolean;
  clinicalSignificance?: string;
  differentialDiagnosis?: string[];
  annotations?: ImageAnnotation[];
}

/**
 * Anatomical Location Interface
 */
export interface AnatomicalLocation {
  region: string;
  subregion?: string;
  laterality?: 'left' | 'right' | 'bilateral';
  specific?: string;
  coordinates?: {
    x: number;
    y: number;
    z?: number;
  };
}

/**
 * Measurement Interface
 */
export interface Measurement {
  type: 'linear' | 'area' | 'volume' | 'angle' | 'density';
  value: number;
  unit: string;
  label?: string;
  referenceRange?: {
    min?: number;
    max?: number;
    normal?: string;
  };
}

/**
 * Image Annotation Interface
 */
export interface ImageAnnotation {
  id: string;
  imageId: string;
  type: 'arrow' | 'circle' | 'rectangle' | 'polygon' | 'text';
  coordinates: any; // Specific to annotation type
  label?: string;
  color?: string;
  createdBy?: string;
  createdAt?: Date | string;
}

/**
 * Imaging File Interface
 */
export interface ImagingFile {
  id: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  url: string;
  thumbnailUrl?: string;
  dicomMetadata?: DicomMetadata;
  uploadedAt: Date | string;
  uploadedBy?: string;
  processingStatus?: 'pending' | 'processing' | 'completed' | 'failed';
  analysisResults?: AnalysisResult;
}

/**
 * DICOM Metadata Interface
 */
export interface DicomMetadata {
  studyInstanceUID: string;
  seriesInstanceUID: string;
  sopInstanceUID: string;
  studyDescription?: string;
  seriesDescription?: string;
  modality: string;
  manufacturer?: string;
  institutionName?: string;
  patientPosition?: string;
  imageOrientation?: number[];
  pixelSpacing?: number[];
  sliceThickness?: number;
  windowCenter?: number;
  windowWidth?: number;
}

/**
 * Report Status Enum
 */
export enum ReportStatus {
  DRAFT = 'draft',
  PRELIMINARY = 'preliminary',
  FINAL = 'final',
  AMENDED = 'amended',
  CANCELLED = 'cancelled'
}

/**
 * Study Type Enum
 */
export enum StudyType {
  DIAGNOSTIC = 'diagnostic',
  SCREENING = 'screening',
  FOLLOW_UP = 'follow_up',
  INTERVENTIONAL = 'interventional',
  EMERGENCY = 'emergency'
}

/**
 * Imaging Modality Enum
 */
export enum ImagingModality {
  CT = 'CT',
  MRI = 'MRI',
  XRAY = 'X-ray',
  ULTRASOUND = 'Ultrasound',
  PET = 'PET',
  PETCT = 'PET-CT',
  MAMMOGRAPHY = 'Mammography',
  FLUOROSCOPY = 'Fluoroscopy',
  ANGIOGRAPHY = 'Angiography',
  NUCLEAR = 'Nuclear Medicine',
  OTHER = 'Other'
}

/**
 * Finding Category Enum
 */
export enum FindingCategory {
  NORMAL = 'normal',
  BENIGN = 'benign',
  PROBABLY_BENIGN = 'probably_benign',
  SUSPICIOUS = 'suspicious',
  HIGHLY_SUSPICIOUS = 'highly_suspicious',
  KNOWN_MALIGNANCY = 'known_malignancy',
  INCIDENTAL = 'incidental',
  POST_TREATMENT = 'post_treatment'
}

/**
 * Finding Severity Enum
 */
export enum FindingSeverity {
  NONE = 'none',
  MINIMAL = 'minimal',
  MILD = 'mild',
  MODERATE = 'moderate',
  SEVERE = 'severe',
  CRITICAL = 'critical'
}

/**
 * API Response Interfaces
 */
export interface ImagingReportResponse {
  success: boolean;
  data?: ImagingReport;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  metadata?: {
    requestId: string;
    timestamp: string;
    processingTime: number;
  };
}

export interface ImagingReportListResponse {
  success: boolean;
  data?: {
    reports: ImagingReport[];
    pagination: {
      page: number;
      pageSize: number;
      totalItems: number;
      totalPages: number;
    };
  };
  error?: {
    code: string;
    message: string;
  };
}

/**
 * Request Interfaces
 */
export interface CreateImagingReportRequest {
  patientId: string;
  studyType: StudyType;
  modality: ImagingModality;
  images: File[] | string[]; // Files or URLs
  indication?: string;
  urgency?: 'routine' | 'urgent' | 'stat';
  metadata?: Record<string, any>;
}

export interface UpdateImagingReportRequest {
  findings?: ImagingFinding[];
  impression?: string;
  recommendations?: string[];
  status?: ReportStatus;
}

export interface ImagingAnalysisRequest {
  imageIds: string[];
  analysisType?: 'full' | 'quick' | 'comparison';
  previousReportId?: string;
  aiModel?: string;
  enhancementOptions?: {
    contrastAdjustment?: boolean;
    noiseReduction?: boolean;
    edgeEnhancement?: boolean;
  };
}

/**
 * Utility Types
 */
export type PartialImagingReport = Partial<ImagingReport>;
export type ImagingReportSummary = Pick<ImagingReport, 'id' | 'patientName' | 'studyDate' | 'modality' | 'status' | 'impression'>;
export type ImagingReportWithAnalysis = ImagingReport & {
  aiAnalysis: AnalysisResult;
  processingMetrics: {
    duration: number;
    modelVersion: string;
    confidence: number;
  };
};

/**
 * Filter and Sort Options
 */
export interface ImagingReportFilter {
  patientId?: string;
  modality?: ImagingModality | ImagingModality[];
  studyType?: StudyType | StudyType[];
  status?: ReportStatus | ReportStatus[];
  dateRange?: {
    start: Date | string;
    end: Date | string;
  };
  bodyPart?: string;
  findingSeverity?: FindingSeverity | FindingSeverity[];
  hasFindings?: boolean;
  reportingRadiologist?: string;
  searchText?: string;
}

export interface ImagingReportSortOptions {
  field: 'studyDate' | 'reportDate' | 'patientName' | 'modality' | 'status' | 'severity';
  direction: 'asc' | 'desc';
}

/**
 * Event Types for WebSocket or Real-time Updates
 */
export interface ImagingReportEvent {
  type: 'created' | 'updated' | 'finalized' | 'deleted' | 'analysis_complete';
  reportId: string;
  timestamp: Date | string;
  userId?: string;
  changes?: Partial<ImagingReport>;
}

/**
 * Integration Types
 */
export interface PACSIntegration {
  enabled: boolean;
  serverUrl: string;
  authentication: {
    type: 'basic' | 'token' | 'oauth';
    credentials?: any;
  };
  autoFetch: boolean;
  syncInterval?: number;
}

export interface HL7Message {
  messageType: string;
  messageId: string;
  timestamp: Date | string;
  segments: Record<string, any>;
  reportId?: string;
}