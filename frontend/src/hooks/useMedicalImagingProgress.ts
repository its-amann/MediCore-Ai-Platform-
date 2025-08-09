import { useEffect, useState, useCallback, useRef } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { 
  MedicalImagingProgress, 
  MedicalImagingProgressStatus,
  isMedicalImagingProgress,
  isErrorStatus,
  isCompleteStatus 
} from '../types/medicalImagingProgress';

export interface MedicalImagingProgressState {
  reportId?: string;
  caseId?: string;
  status?: MedicalImagingProgressStatus;
  progress: number;
  currentImage?: number;
  totalImages?: number;
  currentFilename?: string;
  message?: string;
  error?: string;
  findingsCount?: number;
  severity?: 'low' | 'medium' | 'high';
  qualityScore?: number;
  isProcessing: boolean;
  isComplete: boolean;
  hasError: boolean;
}

export function useMedicalImagingProgress() {
  const { onMessage } = useWebSocket();
  const [progressState, setProgressState] = useState<MedicalImagingProgressState>({
    progress: 0,
    isProcessing: false,
    isComplete: false,
    hasError: false
  });

  // History of all progress messages for this session
  const [progressHistory, setProgressHistory] = useState<MedicalImagingProgress[]>([]);

  const resetProgress = useCallback(() => {
    setProgressState({
      progress: 0,
      isProcessing: false,
      isComplete: false,
      hasError: false
    });
    setProgressHistory([]);
  }, []);

  useEffect(() => {
    const unsubscribe = onMessage((message) => {
      try {
        const data = message as any;
      
      if (isMedicalImagingProgress(data)) {
        // Add to history
        setProgressHistory(prev => [...prev, data]);

        // Update progress state
        setProgressState(prev => {
          const newState: MedicalImagingProgressState = {
            ...prev,
            reportId: data.report_id,
            caseId: data.case_id,
            status: data.status,
            message: data.message,
            isProcessing: !isCompleteStatus(data.status) && !isErrorStatus(data.status),
            isComplete: isCompleteStatus(data.status),
            hasError: isErrorStatus(data.status)
          };

          // Update progress percentage if provided
          if (data.progress_percentage !== undefined) {
            newState.progress = data.progress_percentage;
          }

          // Handle specific status updates
          switch (data.status) {
            case 'upload_started':
              newState.totalImages = data.total_images;
              newState.progress = 0;
              break;

            case 'processing_image':
              newState.currentImage = data.current_image;
              newState.totalImages = data.total_images;
              newState.currentFilename = data.filename;
              break;

            case 'ai_analysis_started':
              newState.currentImage = data.current_image;
              newState.totalImages = data.total_images;
              newState.currentFilename = data.filename;
              break;

            case 'image_processed':
              newState.currentImage = data.current_image;
              newState.totalImages = data.total_images;
              newState.currentFilename = data.filename;
              newState.findingsCount = data.findings_count;
              break;

            case 'image_error':
            case 'workflow_image_error':
              newState.currentImage = data.current_image;
              newState.totalImages = data.total_images;
              newState.currentFilename = data.filename;
              newState.error = data.error;
              break;

            case 'completed':
              newState.progress = 100;
              newState.findingsCount = data.findings_count;
              newState.severity = data.severity;
              break;

            case 'workflow_completed':
              newState.progress = 100;
              newState.findingsCount = data.findings_count;
              newState.qualityScore = data.quality_score;
              break;

            case 'failed':
            case 'error':
            case 'workflow_failed':
            case 'workflow_error':
              newState.error = data.error;
              newState.progress = 0;
              break;

            case 'workflow_started':
              newState.totalImages = data.total_images;
              newState.progress = 0;
              break;

            case 'workflow_analyzing_image':
              newState.currentImage = data.current_image;
              newState.totalImages = data.total_images;
              break;
          }

          return newState;
        });
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  });

  return unsubscribe;
}, [onMessage]);

  return {
    progressState,
    progressHistory,
    resetProgress
  };
}

/**
 * Hook to track progress for a specific report
 */
export function useMedicalImagingReportProgress(reportId?: string) {
  const { progressState, progressHistory, resetProgress } = useMedicalImagingProgress();

  // Filter progress for specific report if reportId is provided
  const reportProgress = reportId 
    ? progressHistory.filter(p => p.report_id === reportId)
    : progressHistory;

  const reportState = reportId && progressState.reportId !== reportId
    ? {
        progress: 0,
        isProcessing: false,
        isComplete: false,
        hasError: false
      }
    : progressState;

  return {
    progressState: reportState,
    progressHistory: reportProgress,
    resetProgress
  };
}