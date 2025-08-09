import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  CloudArrowUpIcon,
  DocumentIcon,
  PhotoIcon,
  VideoCameraIcon,
  SpeakerWaveIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../../api/axios';

interface FileUploadProps {
  caseId?: string;
  onUploadComplete?: (files: UploadedFile[]) => void;
  acceptedTypes?: string[];
  maxFiles?: number;
  maxSize?: number; // in bytes
}

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
  thumbnailUrl?: string;
  uploadedAt: string;
}

interface FileWithPreview extends File {
  id: string;
  preview?: string;
  uploadStatus?: 'pending' | 'uploading' | 'success' | 'error';
  progress?: number;
  error?: string;
}

const FileUploadDropzone: React.FC<FileUploadProps> = ({
  caseId,
  onUploadComplete,
  acceptedTypes = ['image/*', '.pdf', '.doc', '.docx', 'audio/*', 'video/*'],
  maxFiles = 10,
  maxSize = 50 * 1024 * 1024 // 50MB
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const errors = rejectedFiles.map(file => file.errors[0]?.message).join(', ');
      toast.error(`Some files were rejected: ${errors}`);
    }

    // Process accepted files
    const newFiles: FileWithPreview[] = acceptedFiles.map(file => ({
      ...file,
      id: Math.random().toString(36).substr(2, 9),
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      uploadStatus: 'pending'
    }));

    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxFiles,
    maxSize,
    multiple: true
  });

  const removeFile = (fileId: string) => {
    setFiles(prev => {
      const file = prev.find(f => f.id === fileId);
      if (file?.preview) {
        URL.revokeObjectURL(file.preview);
      }
      return prev.filter(f => f.id !== fileId);
    });
  };

  const uploadFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);
    const uploadedFiles: UploadedFile[] = [];

    try {
      for (const file of files) {
        if (file.uploadStatus === 'success') continue;

        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, uploadStatus: 'uploading', progress: 0 } : f
        ));

        const formData = new FormData();
        formData.append('file', file);
        if (caseId) formData.append('case_id', caseId);

        try {
          const response = await api.post('/media/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (progressEvent) => {
              const progress = Math.round(
                (progressEvent.loaded * 100) / (progressEvent.total || 1)
              );
              setFiles(prev => prev.map(f => 
                f.id === file.id ? { ...f, progress } : f
              ));
            }
          });

          const uploadedFile: UploadedFile = response.data;
          uploadedFiles.push(uploadedFile);

          setFiles(prev => prev.map(f => 
            f.id === file.id ? { ...f, uploadStatus: 'success', progress: 100 } : f
          ));

          toast.success(`${file.name} uploaded successfully`);
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || 'Upload failed';
          setFiles(prev => prev.map(f => 
            f.id === file.id ? { ...f, uploadStatus: 'error', error: errorMessage } : f
          ));
          toast.error(`Failed to upload ${file.name}: ${errorMessage}`);
        }
      }

      if (uploadedFiles.length > 0 && onUploadComplete) {
        onUploadComplete(uploadedFiles);
      }
    } finally {
      setUploading(false);
    }
  };

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return PhotoIcon;
    if (type.startsWith('video/')) return VideoCameraIcon;
    if (type.startsWith('audio/')) return SpeakerWaveIcon;
    return DocumentIcon;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="w-full">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
          ${uploading ? 'pointer-events-none opacity-50' : ''}
        `}
      >
        <input {...getInputProps()} />
        <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
        <div className="mt-4">
          <p className="text-lg font-medium text-gray-900">
            {isDragActive ? 'Drop files here' : 'Upload medical files'}
          </p>
          <p className="text-sm text-gray-600 mt-2">
            Drag and drop files here, or click to select files
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Supports images, documents, audio, and video files (max {formatFileSize(maxSize)})
          </p>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              Files ({files.length})
            </h3>
            <button
              onClick={uploadFiles}
              disabled={uploading || files.every(f => f.uploadStatus === 'success')}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Uploading...' : 'Upload All'}
            </button>
          </div>

          <div className="space-y-3">
            {files.map((file) => {
              const FileIcon = getFileIcon(file.type);
              return (
                <div
                  key={file.id}
                  className="flex items-center p-4 bg-white border border-gray-200 rounded-lg"
                >
                  {/* File Preview/Icon */}
                  <div className="flex-shrink-0 mr-4">
                    {file.preview ? (
                      <img
                        src={file.preview}
                        alt={file.name}
                        className="h-12 w-12 object-cover rounded-lg"
                      />
                    ) : (
                      <div className="h-12 w-12 bg-gray-100 rounded-lg flex items-center justify-center">
                        <FileIcon className="h-6 w-6 text-gray-500" />
                      </div>
                    )}
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {formatFileSize(file.size)} • {file.type}
                    </p>

                    {/* Progress Bar */}
                    {file.uploadStatus === 'uploading' && (
                      <div className="mt-2">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${file.progress || 0}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {file.progress}% uploaded
                        </p>
                      </div>
                    )}

                    {/* Error Message */}
                    {file.uploadStatus === 'error' && (
                      <p className="text-sm text-red-600 mt-1">
                        {file.error}
                      </p>
                    )}
                  </div>

                  {/* Status & Actions */}
                  <div className="flex items-center space-x-2">
                    {file.uploadStatus === 'success' && (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    )}
                    {file.uploadStatus === 'error' && (
                      <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                    )}
                    
                    <button
                      onClick={() => removeFile(file.id)}
                      disabled={file.uploadStatus === 'uploading'}
                      className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-50"
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUploadDropzone;