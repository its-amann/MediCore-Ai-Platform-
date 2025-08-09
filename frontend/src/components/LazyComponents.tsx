import React, { lazy, Suspense } from 'react';
import LoadingSpinner from './ui/LoadingSpinner';

// Lazy load heavy components to improve initial bundle size
export const LazyAnalyticsDashboard = lazy(() => import('./analytics/AnalyticsDashboard'));
export const LazyMediaGallery = lazy(() => import('./media/MediaGallery'));
export const LazyEnhancedChatInterface = lazy(() => import('./chat/EnhancedChatInterface'));

// Lazy load pages
export const LazyMedicalImaging = lazy(() => import('../pages/MedicalImaging'));
export const LazyVoiceConsultation = lazy(() => import('../pages/VoiceConsultation'));
export const LazyVoiceConsultationNew = lazy(() => import('../pages/VoiceConsultationNew'));
export const LazyVoiceConsultationGeminiLive = lazy(() => import('../pages/VoiceConsultationGeminiLive'));
export const LazyReports = lazy(() => import('../pages/Reports'));
export const LazyReportViewer = lazy(() => import('../pages/ReportViewer'));
export const LazySettings = lazy(() => import('../pages/Settings'));
export const LazyRoomDetail = lazy(() => import('../pages/RoomDetail'));
export const LazyRoomSettings = lazy(() => import('../pages/RoomSettings'));

// HOC for lazy loading with error boundary
interface LazyWrapperProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const LazyWrapper: React.FC<LazyWrapperProps> = ({ 
  children, 
  fallback = (
    <div className="flex items-center justify-center p-8">
      <LoadingSpinner size="lg" />
      <span className="ml-3 text-gray-600">Loading...</span>
    </div>
  ) 
}) => {
  return (
    <Suspense fallback={fallback}>
      <ErrorBoundary>
        {children}
      </ErrorBoundary>
    </Suspense>
  );
};

// Simple error boundary for lazy loaded components
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(_: Error) {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Lazy component loading error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="text-center">
            <p className="text-red-600 mb-2">Failed to load component</p>
            <button 
              onClick={() => this.setState({ hasError: false })}
              className="btn-primary"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}