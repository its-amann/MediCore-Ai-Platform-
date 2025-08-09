import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileImage, CheckCircle, AlertCircle, Clock } from 'lucide-react';

interface FileWithPreview extends File {
  preview?: string;
  id: string;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

interface UploadZoneProps {
  onFilesAccepted: (files: File[]) => void;
  acceptedFileTypes?: string[];
  maxFileSize?: number;
  maxFiles?: number;
  uploadEndpoint?: string;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFilesAccepted,
  acceptedFileTypes = ['image/*'],
  maxFileSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 10,
  uploadEndpoint
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      ...file,
      id: Math.random().toString(36).substr(2, 9),
      preview: URL.createObjectURL(file),
      progress: 0,
      status: 'pending' as const
    }));

    setFiles(prev => [...prev, ...newFiles].slice(0, maxFiles));
    onFilesAccepted(acceptedFiles);

    // Simulate upload if endpoint provided
    if (uploadEndpoint) {
      simulateUpload(newFiles);
    }
  }, [maxFiles, onFilesAccepted, uploadEndpoint]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: acceptedFileTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize: maxFileSize,
    maxFiles
  });

  // Simulate file upload with progress
  const simulateUpload = async (filesToUpload: FileWithPreview[]) => {
    setIsUploading(true);

    for (const file of filesToUpload) {
      // Update status to uploading
      setFiles(prev => prev.map(f => 
        f.id === file.id ? { ...f, status: 'uploading' } : f
      ));

      // Simulate progress
      for (let progress = 0; progress <= 100; progress += 10) {
        await new Promise(resolve => setTimeout(resolve, 100));
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, progress } : f
        ));
      }

      // Simulate success/error (90% success rate)
      const isSuccess = Math.random() > 0.1;
      setFiles(prev => prev.map(f => 
        f.id === file.id 
          ? { 
              ...f, 
              status: isSuccess ? 'completed' : 'error',
              error: isSuccess ? undefined : 'Upload failed. Please try again.'
            } 
          : f
      ));
    }

    setIsUploading(false);
  };

  // Remove file from queue
  const removeFile = (id: string) => {
    setFiles(prev => {
      const file = prev.find(f => f.id === id);
      if (file?.preview) {
        URL.revokeObjectURL(file.preview);
      }
      return prev.filter(f => f.id !== id);
    });
  };

  // Retry failed upload
  const retryUpload = (file: FileWithPreview) => {
    setFiles(prev => prev.map(f => 
      f.id === file.id ? { ...f, status: 'pending', progress: 0, error: undefined } : f
    ));
    if (uploadEndpoint) {
      simulateUpload([file]);
    }
  };

  // Get status icon
  const getStatusIcon = (status: FileWithPreview['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'uploading':
        return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="w-full">
      {/* Drop Zone */}
      <motion.div
        className={`
          relative border-2 border-dashed rounded-xl p-8 transition-all cursor-pointer
          ${isDragActive ? 'border-blue-500 bg-blue-500/10' : 'border-gray-600 hover:border-gray-500'}
          ${isDragReject ? 'border-red-500 bg-red-500/10' : ''}
        `}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        {...(() => {
          const props = getRootProps();
          const { 
            onAnimationStart, 
            onDragStart,
            onDragEnd,
            onDrag,
            ...restProps 
          } = props;
          return restProps;
        })()}
      >
        <input {...getInputProps()} />
        
        <motion.div
          initial={false}
          animate={{
            scale: isDragActive ? 1.1 : 1,
            opacity: isDragActive ? 1 : 0.8
          }}
          className="flex flex-col items-center justify-center text-center"
        >
          <Upload className={`w-12 h-12 mb-4 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`} />
          
          {isDragActive ? (
            <p className="text-lg font-medium text-blue-500">Drop files here...</p>
          ) : isDragReject ? (
            <p className="text-lg font-medium text-red-500">Invalid file type or size</p>
          ) : (
            <>
              <p className="text-lg font-medium text-gray-300 mb-2">
                Drag & drop medical images here
              </p>
              <p className="text-sm text-gray-500">
                or click to browse files
              </p>
              <p className="text-xs text-gray-600 mt-2">
                Accepted: {acceptedFileTypes.join(', ')} • Max size: {formatFileSize(maxFileSize)}
              </p>
            </>
          )}
        </motion.div>

        {/* Animated background effect */}
        {isDragActive && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 pointer-events-none"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl" />
          </motion.div>
        )}
      </motion.div>

      {/* File Preview Cards */}
      {files.length > 0 && (
        <div className="mt-6 space-y-3">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-300">Upload Queue</h3>
            {isUploading && (
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="text-sm text-blue-500"
              >
                Uploading...
              </motion.div>
            )}
          </div>

          <AnimatePresence>
            {files.map((file) => (
              <motion.div
                key={file.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                className="bg-gray-800 rounded-lg p-4 flex items-center space-x-4"
              >
                {/* Preview */}
                <div className="flex-shrink-0 w-16 h-16 bg-gray-700 rounded-lg overflow-hidden">
                  {file.preview ? (
                    <img
                      src={file.preview}
                      alt={file.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <FileImage className="w-8 h-8 text-gray-500" />
                    </div>
                  )}
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-gray-200 truncate">
                      {file.name}
                    </p>
                    {getStatusIcon(file.status)}
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    {formatFileSize(file.size)}
                  </p>

                  {/* Progress Bar */}
                  {file.status === 'uploading' && (
                    <div className="w-full bg-gray-700 rounded-full h-1.5">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${file.progress}%` }}
                        className="bg-blue-500 h-1.5 rounded-full"
                      />
                    </div>
                  )}

                  {/* Error Message */}
                  {file.error && (
                    <p className="text-xs text-red-400 mt-1">{file.error}</p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex-shrink-0">
                  {file.status === 'error' ? (
                    <button
                      onClick={() => retryUpload(file)}
                      className="text-sm text-blue-500 hover:text-blue-400"
                    >
                      Retry
                    </button>
                  ) : (
                    <button
                      onClick={() => removeFile(file.id)}
                      className="p-1 hover:bg-gray-700 rounded transition-colors"
                      disabled={file.status === 'uploading'}
                    >
                      <X className="w-4 h-4 text-gray-400" />
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};

export default UploadZone;