import React from 'react';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: 'blue' | 'green' | 'red' | 'gray' | 'white';
  text?: string;
  overlay?: boolean;
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  color = 'blue', 
  text, 
  overlay = false,
  className = '' 
}) => {
  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'h-4 w-4 border-2';
      case 'md':
        return 'h-8 w-8 border-2';
      case 'lg':
        return 'h-12 w-12 border-3';
      case 'xl':
        return 'h-16 w-16 border-4';
      default:
        return 'h-8 w-8 border-2';
    }
  };

  const getColorClasses = () => {
    switch (color) {
      case 'blue':
        return 'border-blue-200 border-t-blue-600';
      case 'green':
        return 'border-green-200 border-t-green-600';
      case 'red':
        return 'border-red-200 border-t-red-600';
      case 'gray':
        return 'border-gray-200 border-t-gray-600';
      case 'white':
        return 'border-white/30 border-t-white';
      default:
        return 'border-blue-200 border-t-blue-600';
    }
  };

  const getTextColor = () => {
    switch (color) {
      case 'blue':
        return 'text-blue-600';
      case 'green':
        return 'text-green-600';
      case 'red':
        return 'text-red-600';
      case 'gray':
        return 'text-gray-600';
      case 'white':
        return 'text-white';
      default:
        return 'text-blue-600';
    }
  };

  const spinner = (
    <div className={`flex flex-col items-center justify-center ${overlay ? 'p-8' : 'p-4'} ${className}`}>
      <div 
        className={`
          animate-spin rounded-full 
          ${getSizeClasses()} 
          ${getColorClasses()}
        `}
        role="status"
        aria-label="Loading"
      />
      {text && (
        <p className={`mt-3 text-sm font-medium ${getTextColor()}`}>
          {text}
        </p>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  );

  if (overlay) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-25 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg">
          {spinner}
        </div>
      </div>
    );
  }

  return spinner;
};

// Medical-specific loading variants
export const MedicalLoadingSpinner: React.FC<Omit<LoadingSpinnerProps, 'color'>> = (props) => (
  <LoadingSpinner {...props} color="blue" />
);

export const ProcessingSpinner: React.FC<{ text?: string }> = ({ text = "Processing your request..." }) => (
  <LoadingSpinner size="lg" color="green" text={text} />
);

export const AIThinkingSpinner: React.FC = () => (
  <div className="flex items-center space-x-3 p-4">
    <LoadingSpinner size="sm" color="blue" />
    <div className="flex items-center space-x-1">
      <span className="text-sm text-gray-600">AI is analyzing</span>
      <div className="flex space-x-1">
        <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  </div>
);

export default LoadingSpinner;