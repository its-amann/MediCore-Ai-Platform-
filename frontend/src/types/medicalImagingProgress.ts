/**
 * Medical Imaging Progress WebSocket Message Types
 */

export type MedicalImagingProgressStatus = 
  | 'upload_started'
  | 'processing_image'
  | 'ai_analysis_started'
  | 'image_processed'
  | 'image_error'
  | 'generating_report'
  | 'completed'
  | 'failed'
  | 'error'
  | 'workflow_started'
  | 'workflow_analyzing_image'
  | 'workflow_image_error'
  | 'workflow_failed'
  | 'workflow_generating_report'
  | 'workflow_completed'
  | 'workflow_error';

export interface MedicalImagingProgressBase {
  type: 'medical_imaging_progress';
  status: MedicalImagingProgressStatus;
  report_id: string;
  case_id: string;
  message: string;
  timestamp: string;
  progress_percentage?: number;
}

export interface UploadStartedProgress extends MedicalImagingProgressBase {
  status: 'upload_started';
  total_images: number;
}

export interface ProcessingImageProgress extends MedicalImagingProgressBase {
  status: 'processing_image';
  current_image: number;
  total_images: number;
  filename: string;
  progress_percentage: number;
}

export interface AIAnalysisStartedProgress extends MedicalImagingProgressBase {
  status: 'ai_analysis_started';
  current_image: number;
  total_images: number;
  filename: string;
}

export interface ImageProcessedProgress extends MedicalImagingProgressBase {
  status: 'image_processed';
  current_image: number;
  total_images: number;
  filename: string;
  progress_percentage: number;
  findings_count: number;
}

export interface ImageErrorProgress extends MedicalImagingProgressBase {
  status: 'image_error';
  current_image: number;
  total_images: number;
  filename: string;
  error: string;
}

export interface GeneratingReportProgress extends MedicalImagingProgressBase {
  status: 'generating_report';
  progress_percentage: number;
}

export interface CompletedProgress extends MedicalImagingProgressBase {
  status: 'completed';
  progress_percentage: 100;
  images_processed: number;
  severity: 'low' | 'medium' | 'high';
  findings_count: number;
}

export interface FailedProgress extends MedicalImagingProgressBase {
  status: 'failed';
  error: string;
}

export interface ErrorProgress extends MedicalImagingProgressBase {
  status: 'error';
  error: string;
}

export interface WorkflowStartedProgress extends MedicalImagingProgressBase {
  status: 'workflow_started';
  workflow_type: string;
  total_images: number;
}

export interface WorkflowAnalyzingImageProgress extends MedicalImagingProgressBase {
  status: 'workflow_analyzing_image';
  current_image: number;
  total_images: number;
  progress_percentage: number;
}

export interface WorkflowImageErrorProgress extends MedicalImagingProgressBase {
  status: 'workflow_image_error';
  current_image: number;
  total_images: number;
  filename: string;
  error: string;
}

export interface WorkflowFailedProgress extends MedicalImagingProgressBase {
  status: 'workflow_failed';
  error: string;
}

export interface WorkflowGeneratingReportProgress extends MedicalImagingProgressBase {
  status: 'workflow_generating_report';
  progress_percentage: number;
}

export interface WorkflowCompletedProgress extends MedicalImagingProgressBase {
  status: 'workflow_completed';
  progress_percentage: 100;
  images_analyzed: number;
  findings_count: number;
  quality_score: number;
}

export interface WorkflowErrorProgress extends MedicalImagingProgressBase {
  status: 'workflow_error';
  error: string;
}

export type MedicalImagingProgress = 
  | UploadStartedProgress
  | ProcessingImageProgress
  | AIAnalysisStartedProgress
  | ImageProcessedProgress
  | ImageErrorProgress
  | GeneratingReportProgress
  | CompletedProgress
  | FailedProgress
  | ErrorProgress
  | WorkflowStartedProgress
  | WorkflowAnalyzingImageProgress
  | WorkflowImageErrorProgress
  | WorkflowFailedProgress
  | WorkflowGeneratingReportProgress
  | WorkflowCompletedProgress
  | WorkflowErrorProgress;

/**
 * Type guard to check if a message is a medical imaging progress message
 */
export function isMedicalImagingProgress(message: any): message is MedicalImagingProgress {
  return message?.type === 'medical_imaging_progress' && 
         typeof message?.status === 'string' &&
         typeof message?.report_id === 'string' &&
         typeof message?.case_id === 'string';
}

/**
 * Helper to get progress color based on status
 */
export function getProgressColor(status: MedicalImagingProgressStatus): string {
  switch (status) {
    case 'completed':
    case 'workflow_completed':
    case 'image_processed':
      return 'success';
    case 'processing_image':
    case 'ai_analysis_started':
    case 'generating_report':
    case 'workflow_analyzing_image':
    case 'workflow_generating_report':
      return 'info';
    case 'upload_started':
    case 'workflow_started':
      return 'primary';
    case 'image_error':
    case 'workflow_image_error':
      return 'warning';
    case 'failed':
    case 'error':
    case 'workflow_failed':
    case 'workflow_error':
      return 'error';
    default:
      return 'default';
  }
}

/**
 * Helper to check if the progress indicates an error state
 */
export function isErrorStatus(status: MedicalImagingProgressStatus): boolean {
  return [
    'failed',
    'error',
    'workflow_failed',
    'workflow_error'
  ].includes(status);
}

/**
 * Helper to check if the progress indicates completion
 */
export function isCompleteStatus(status: MedicalImagingProgressStatus): boolean {
  return status === 'completed' || status === 'workflow_completed';
}