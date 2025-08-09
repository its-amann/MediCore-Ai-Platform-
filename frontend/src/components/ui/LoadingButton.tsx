import React from 'react';

interface LoadingButtonProps {
  loading: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
  className?: string;
  loadingText?: string;
}

const LoadingButton: React.FC<LoadingButtonProps> = ({
  loading,
  children,
  onClick,
  type = 'button',
  disabled = false,
  className = '',
  loadingText = 'Loading...'
}) => {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading || disabled}
      className={`inline-flex items-center justify-center ${className} disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {loading && (
        <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"></div>
      )}
      {loading ? loadingText : children}
    </button>
  );
};

export default LoadingButton;