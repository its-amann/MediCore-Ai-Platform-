import React, { useState, useEffect } from 'react';
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  InformationCircleIcon, 
  XCircleIcon,
  XMarkIcon 
} from '@heroicons/react/24/outline';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  autoClose?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastProps {
  toast: ToastMessage;
  onClose: (id: string) => void;
}

const Toast: React.FC<ToastProps> = ({ toast, onClose }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Trigger entrance animation
    const timer = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (toast.autoClose !== false && toast.duration !== 0) {
      const duration = toast.duration || 5000;
      const timer = setTimeout(() => {
        handleClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [toast.duration, toast.autoClose]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      onClose(toast.id);
    }, 300);
  };

  const getIcon = () => {
    const iconProps = { className: "h-6 w-6" };
    
    switch (toast.type) {
      case 'success':
        return <CheckCircleIcon {...iconProps} className="h-6 w-6 text-green-600" />;
      case 'error':
        return <XCircleIcon {...iconProps} className="h-6 w-6 text-red-600" />;
      case 'warning':
        return <ExclamationTriangleIcon {...iconProps} className="h-6 w-6 text-yellow-600" />;
      case 'info':
        return <InformationCircleIcon {...iconProps} className="h-6 w-6 text-blue-600" />;
    }
  };

  const getStyles = () => {
    const base = "border-l-4 shadow-lg";
    
    switch (toast.type) {
      case 'success':
        return `${base} bg-green-50 border-green-400`;
      case 'error':
        return `${base} bg-red-50 border-red-400`;
      case 'warning':
        return `${base} bg-yellow-50 border-yellow-400`;
      case 'info':
        return `${base} bg-blue-50 border-blue-400`;
    }
  };

  const getTextStyles = () => {
    switch (toast.type) {
      case 'success':
        return "text-green-800";
      case 'error':
        return "text-red-800";
      case 'warning':
        return "text-yellow-800";
      case 'info':
        return "text-blue-800";
    }
  };

  return (
    <div
      className={`
        max-w-sm w-full rounded-lg pointer-events-auto transform transition-all duration-300 ease-in-out
        ${isVisible && !isExiting ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        ${getStyles()}
      `}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {getIcon()}
          </div>
          <div className="ml-3 w-0 flex-1">
            <div className={`text-sm font-medium ${getTextStyles()}`}>
              {toast.title}
            </div>
            {toast.message && (
              <div className={`mt-1 text-sm ${getTextStyles()} opacity-90`}>
                {toast.message}
              </div>
            )}
            {toast.action && (
              <div className="mt-3">
                <button
                  onClick={toast.action.onClick}
                  className={`
                    text-sm font-medium underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-offset-2 focus:rounded
                    ${toast.type === 'success' ? 'text-green-700 focus:ring-green-500' : ''}
                    ${toast.type === 'error' ? 'text-red-700 focus:ring-red-500' : ''}
                    ${toast.type === 'warning' ? 'text-yellow-700 focus:ring-yellow-500' : ''}
                    ${toast.type === 'info' ? 'text-blue-700 focus:ring-blue-500' : ''}
                  `}
                >
                  {toast.action.label}
                </button>
              </div>
            )}
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={handleClose}
              className={`
                rounded-md inline-flex focus:outline-none focus:ring-2 focus:ring-offset-2
                ${toast.type === 'success' ? 'text-green-500 hover:text-green-600 focus:ring-green-500' : ''}
                ${toast.type === 'error' ? 'text-red-500 hover:text-red-600 focus:ring-red-500' : ''}
                ${toast.type === 'warning' ? 'text-yellow-500 hover:text-yellow-600 focus:ring-yellow-500' : ''}
                ${toast.type === 'info' ? 'text-blue-500 hover:text-blue-600 focus:ring-blue-500' : ''}
              `}
              aria-label="Close notification"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Toast Container Component
interface ToastContainerProps {
  toasts: ToastMessage[];
  onClose: (id: string) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ 
  toasts, 
  onClose, 
  position = 'top-right' 
}) => {
  const getPositionStyles = () => {
    switch (position) {
      case 'top-right':
        return 'top-4 right-4';
      case 'top-left':
        return 'top-4 left-4';
      case 'bottom-right':
        return 'bottom-4 right-4';
      case 'bottom-left':
        return 'bottom-4 left-4';
      case 'top-center':
        return 'top-4 left-1/2 transform -translate-x-1/2';
      case 'bottom-center':
        return 'bottom-4 left-1/2 transform -translate-x-1/2';
      default:
        return 'top-4 right-4';
    }
  };

  if (toasts.length === 0) return null;

  return (
    <div 
      className={`fixed z-50 pointer-events-none ${getPositionStyles()}`}
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex flex-col space-y-4">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} onClose={onClose} />
        ))}
      </div>
    </div>
  );
};

export default Toast;