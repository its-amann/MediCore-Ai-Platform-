import React, { forwardRef } from 'react';
import { ExclamationCircleIcon, CheckCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';

interface BaseFormFieldProps {
  label?: string;
  error?: string;
  success?: string;
  hint?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  labelClassName?: string;
  id?: string;
}

interface InputProps extends BaseFormFieldProps {
  name?: string;
  type?: 'text' | 'email' | 'password' | 'tel' | 'url' | 'search' | 'number';
  placeholder?: string;
  value?: string | number;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void;
  onFocus?: (e: React.FocusEvent<HTMLInputElement>) => void;
  autoComplete?: string;
  maxLength?: number;
  min?: number;
  max?: number;
  step?: number;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

interface TextAreaProps extends BaseFormFieldProps {
  name?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onBlur?: (e: React.FocusEvent<HTMLTextAreaElement>) => void;
  onFocus?: (e: React.FocusEvent<HTMLTextAreaElement>) => void;
  rows?: number;
  maxLength?: number;
  resize?: boolean;
}

interface SelectProps extends BaseFormFieldProps {
  name?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onBlur?: (e: React.FocusEvent<HTMLSelectElement>) => void;
  onFocus?: (e: React.FocusEvent<HTMLSelectElement>) => void;
  children: React.ReactNode;
  placeholder?: string;
}

// Input Component
export const FormInput = forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  success,
  hint,
  required,
  disabled,
  className = '',
  labelClassName = '',
  id,
  type = 'text',
  leftIcon,
  rightIcon,
  ...props
}, ref) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  
  const getInputClasses = () => {
    const base = "block w-full px-3 py-2 border rounded-md shadow-sm transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2";
    const iconPadding = leftIcon ? "pl-10" : rightIcon ? "pr-10" : "";
    
    if (error) {
      return `${base} ${iconPadding} border-red-300 text-red-900 placeholder-red-300 focus:ring-red-500 focus:border-red-500`;
    }
    
    if (success) {
      return `${base} ${iconPadding} border-green-300 text-green-900 placeholder-green-300 focus:ring-green-500 focus:border-green-500`;
    }
    
    if (disabled) {
      return `${base} ${iconPadding} border-gray-300 bg-gray-50 text-gray-500 cursor-not-allowed`;
    }
    
    return `${base} ${iconPadding} border-gray-300 placeholder-gray-400 focus:ring-blue-500 focus:border-blue-500`;
  };

  return (
    <div className={className}>
      {label && (
        <label 
          htmlFor={inputId} 
          className={`block text-sm font-medium text-gray-700 mb-1 ${labelClassName}`}
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <div className="relative">
        {leftIcon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <div className={error ? 'text-red-400' : success ? 'text-green-400' : 'text-gray-400'}>
              {leftIcon}
            </div>
          </div>
        )}
        
        <input
          ref={ref}
          id={inputId}
          type={type}
          disabled={disabled}
          className={`${getInputClasses()}`}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={
            error ? `${inputId}-error` : 
            success ? `${inputId}-success` : 
            hint ? `${inputId}-hint` : undefined
          }
          {...props}
        />
        
        {rightIcon && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <div className={error ? 'text-red-400' : success ? 'text-green-400' : 'text-gray-400'}>
              {rightIcon}
            </div>
          </div>
        )}
        
        {/* Auto-generated status icons */}
        {(error || success) && !rightIcon && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            {error && <ExclamationCircleIcon className="h-5 w-5 text-red-400" />}
            {success && <CheckCircleIcon className="h-5 w-5 text-green-400" />}
          </div>
        )}
      </div>
      
      {/* Error Message */}
      {error && (
        <p id={`${inputId}-error`} className="mt-1 text-sm text-red-600 flex items-center">
          <ExclamationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {error}
        </p>
      )}
      
      {/* Success Message */}
      {success && !error && (
        <p id={`${inputId}-success`} className="mt-1 text-sm text-green-600 flex items-center">
          <CheckCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {success}
        </p>
      )}
      
      {/* Hint */}
      {hint && !error && !success && (
        <p id={`${inputId}-hint`} className="mt-1 text-sm text-gray-500 flex items-center">
          <InformationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {hint}
        </p>
      )}
    </div>
  );
});

FormInput.displayName = 'FormInput';

// TextArea Component
export const FormTextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(({
  label,
  error,
  success,
  hint,
  required,
  disabled,
  className = '',
  labelClassName = '',
  id,
  rows = 3,
  resize = true,
  ...props
}, ref) => {
  const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;
  
  const getTextAreaClasses = () => {
    const base = `block w-full px-3 py-2 border rounded-md shadow-sm transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${!resize ? 'resize-none' : ''}`;
    
    if (error) {
      return `${base} border-red-300 text-red-900 placeholder-red-300 focus:ring-red-500 focus:border-red-500`;
    }
    
    if (success) {
      return `${base} border-green-300 text-green-900 placeholder-green-300 focus:ring-green-500 focus:border-green-500`;
    }
    
    if (disabled) {
      return `${base} border-gray-300 bg-gray-50 text-gray-500 cursor-not-allowed`;
    }
    
    return `${base} border-gray-300 placeholder-gray-400 focus:ring-blue-500 focus:border-blue-500`;
  };

  return (
    <div className={className}>
      {label && (
        <label 
          htmlFor={textareaId} 
          className={`block text-sm font-medium text-gray-700 mb-1 ${labelClassName}`}
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <textarea
        ref={ref}
        id={textareaId}
        rows={rows}
        disabled={disabled}
        className={getTextAreaClasses()}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={
          error ? `${textareaId}-error` : 
          success ? `${textareaId}-success` : 
          hint ? `${textareaId}-hint` : undefined
        }
        {...props}
      />
      
      {/* Error Message */}
      {error && (
        <p id={`${textareaId}-error`} className="mt-1 text-sm text-red-600 flex items-center">
          <ExclamationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {error}
        </p>
      )}
      
      {/* Success Message */}
      {success && !error && (
        <p id={`${textareaId}-success`} className="mt-1 text-sm text-green-600 flex items-center">
          <CheckCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {success}
        </p>
      )}
      
      {/* Hint */}
      {hint && !error && !success && (
        <p id={`${textareaId}-hint`} className="mt-1 text-sm text-gray-500 flex items-center">
          <InformationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {hint}
        </p>
      )}
    </div>
  );
});

FormTextArea.displayName = 'FormTextArea';

// Select Component
export const FormSelect = forwardRef<HTMLSelectElement, SelectProps>(({
  label,
  error,
  success,
  hint,
  required,
  disabled,
  className = '',
  labelClassName = '',
  id,
  placeholder,
  children,
  ...props
}, ref) => {
  const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;
  
  const getSelectClasses = () => {
    const base = "block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200";
    
    if (error) {
      return `${base} border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500`;
    }
    
    if (success) {
      return `${base} border-green-300 text-green-900 focus:ring-green-500 focus:border-green-500`;
    }
    
    if (disabled) {
      return `${base} border-gray-300 bg-gray-50 text-gray-500 cursor-not-allowed`;
    }
    
    return `${base} border-gray-300 focus:ring-blue-500 focus:border-blue-500`;
  };

  return (
    <div className={className}>
      {label && (
        <label 
          htmlFor={selectId} 
          className={`block text-sm font-medium text-gray-700 mb-1 ${labelClassName}`}
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          disabled={disabled}
          className={getSelectClasses()}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={
            error ? `${selectId}-error` : 
            success ? `${selectId}-success` : 
            hint ? `${selectId}-hint` : undefined
          }
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {children}
        </select>
        
        {/* Status icons */}
        {(error || success) && (
          <div className="absolute inset-y-0 right-8 pr-3 flex items-center pointer-events-none">
            {error && <ExclamationCircleIcon className="h-5 w-5 text-red-400" />}
            {success && <CheckCircleIcon className="h-5 w-5 text-green-400" />}
          </div>
        )}
      </div>
      
      {/* Error Message */}
      {error && (
        <p id={`${selectId}-error`} className="mt-1 text-sm text-red-600 flex items-center">
          <ExclamationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {error}
        </p>
      )}
      
      {/* Success Message */}
      {success && !error && (
        <p id={`${selectId}-success`} className="mt-1 text-sm text-green-600 flex items-center">
          <CheckCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {success}
        </p>
      )}
      
      {/* Hint */}
      {hint && !error && !success && (
        <p id={`${selectId}-hint`} className="mt-1 text-sm text-gray-500 flex items-center">
          <InformationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
          {hint}
        </p>
      )}
    </div>
  );
});

FormSelect.displayName = 'FormSelect';