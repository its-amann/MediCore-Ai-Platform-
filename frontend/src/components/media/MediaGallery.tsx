import React, { useState, useEffect } from 'react';
import {
  PhotoIcon,
  DocumentIcon,
  VideoCameraIcon,
  SpeakerWaveIcon,
  TrashIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  Squares2X2Icon,
  ListBulletIcon
} from '@heroicons/react/24/outline';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import toast from 'react-hot-toast';
import api from '../../api/axios';

interface MediaFile {
  id: string;
  filename: string;
  originalName: string;
  fileType: string;
  fileSize: number;
  thumbnailUrl?: string;
  downloadUrl: string;
  uploadedAt: string;
  caseId?: string;
  metadata?: {
    width?: number;
    height?: number;
    duration?: number;
    analysisResults?: any;
  };
}

interface MediaGalleryProps {
  caseId?: string;
  onFileSelect?: (file: MediaFile) => void;
  allowDelete?: boolean;
  viewMode?: 'grid' | 'list';
}

const MediaGallery: React.FC<MediaGalleryProps> = ({
  caseId,
  onFileSelect,
  allowDelete = true,
  viewMode: initialViewMode = 'grid'
}) => {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(initialViewMode);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [selectedFile, setSelectedFile] = useState<MediaFile | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  useEffect(() => {
    fetchFiles();
  }, [caseId]);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const endpoint = caseId ? `/media/case/${caseId}/media` : '/media/';
      const response = await api.get(endpoint);
      setFiles(response.data.files || response.data || []);
    } catch (error) {
      console.error('Failed to fetch media files:', error);
      toast.error('Failed to load media files');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (fileId: string) => {
    if (!window.confirm('Are you sure you want to delete this file?')) return;

    try {
      await api.delete(`/media/${fileId}`);
      setFiles(prev => prev.filter(f => f.id !== fileId));
      toast.success('File deleted successfully');
    } catch (error) {
      console.error('Failed to delete file:', error);
      toast.error('Failed to delete file');
    }
  };

  const downloadFile = async (file: MediaFile) => {
    try {
      const response = await api.get(`/media/${file.id}/download`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file.originalName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Download started');
    } catch (error) {
      console.error('Failed to download file:', error);
      toast.error('Failed to download file');
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredFiles = files.filter(file => {
    const matchesSearch = file.originalName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterType === 'all' || file.fileType.startsWith(filterType);
    return matchesSearch && matchesFilter;
  });

  const openPreview = (file: MediaFile) => {
    setSelectedFile(file);
    setPreviewOpen(true);
  };

  const FilePreviewModal = () => (
    <Transition appear show={previewOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => setPreviewOpen(false)}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-75" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl bg-white rounded-lg shadow-xl">
                <div className="flex items-center justify-between p-6 border-b">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    {selectedFile?.originalName}
                  </Dialog.Title>
                  <button
                    onClick={() => setPreviewOpen(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ×
                  </button>
                </div>

                <div className="p-6">
                  {selectedFile && (
                    <div className="space-y-4">
                      {/* Preview */}
                      <div className="flex justify-center">
                        {selectedFile.fileType.startsWith('image/') ? (
                          <img
                            src={selectedFile.downloadUrl}
                            alt={selectedFile.originalName}
                            className="max-h-96 object-contain rounded-lg"
                          />
                        ) : selectedFile.fileType.startsWith('video/') ? (
                          <video
                            controls
                            className="max-h-96 rounded-lg"
                            src={selectedFile.downloadUrl}
                          />
                        ) : selectedFile.fileType.startsWith('audio/') ? (
                          <audio controls className="w-full">
                            <source src={selectedFile.downloadUrl} type={selectedFile.fileType} />
                          </audio>
                        ) : (
                          <div className="text-center p-8">
                            <DocumentIcon className="h-16 w-16 mx-auto text-gray-400" />
                            <p className="mt-2 text-gray-600">Preview not available</p>
                          </div>
                        )}
                      </div>

                      {/* File Info */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium text-gray-700">File Size:</span>
                          <span className="ml-2 text-gray-900">{formatFileSize(selectedFile.fileSize)}</span>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Type:</span>
                          <span className="ml-2 text-gray-900">{selectedFile.fileType}</span>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Uploaded:</span>
                          <span className="ml-2 text-gray-900">{formatDate(selectedFile.uploadedAt)}</span>
                        </div>
                        {selectedFile.metadata?.analysisResults && (
                          <div className="col-span-2">
                            <span className="font-medium text-gray-700">Analysis Results:</span>
                            <div className="mt-1 p-3 bg-gray-50 rounded text-xs">
                              <pre>{JSON.stringify(selectedFile.metadata.analysisResults, null, 2)}</pre>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex justify-end space-x-3 pt-4 border-t">
                        <button
                          onClick={() => downloadFile(selectedFile)}
                          className="btn-secondary flex items-center"
                        >
                          <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                          Download
                        </button>
                        {allowDelete && (
                          <button
                            onClick={() => {
                              deleteFile(selectedFile.id);
                              setPreviewOpen(false);
                            }}
                            className="btn-danger flex items-center"
                          >
                            <TrashIcon className="h-4 w-4 mr-2" />
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="relative">
            <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Files</option>
            <option value="image">Images</option>
            <option value="video">Videos</option>
            <option value="audio">Audio</option>
            <option value="application">Documents</option>
          </select>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 rounded ${viewMode === 'grid' ? 'bg-white shadow' : 'hover:bg-gray-200'}`}
          >
            <Squares2X2Icon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 rounded ${viewMode === 'list' ? 'bg-white shadow' : 'hover:bg-gray-200'}`}
          >
            <ListBulletIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* File Grid/List */}
      {filteredFiles.length === 0 ? (
        <div className="text-center py-12">
          <PhotoIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No files found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {searchQuery || filterType !== 'all' 
              ? 'Try adjusting your search or filter criteria' 
              : 'Upload some files to get started'
            }
          </p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredFiles.map((file) => {
            const FileIcon = getFileIcon(file.fileType);
            return (
              <div
                key={file.id}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => onFileSelect?.(file)}
              >
                {/* Thumbnail */}
                <div className="aspect-square bg-gray-50 flex items-center justify-center">
                  {file.thumbnailUrl ? (
                    <img
                      src={file.thumbnailUrl}
                      alt={file.originalName}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <FileIcon className="h-12 w-12 text-gray-400" />
                  )}
                </div>

                {/* File Info */}
                <div className="p-3">
                  <p className="text-sm font-medium text-gray-900 truncate" title={file.originalName}>
                    {file.originalName}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {formatFileSize(file.fileSize)}
                  </p>
                </div>

                {/* Actions */}
                <div className="px-3 pb-3 flex items-center justify-between">
                  <span className="text-xs text-gray-400">
                    {formatDate(file.uploadedAt)}
                  </span>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openPreview(file);
                      }}
                      className="p-1 text-gray-400 hover:text-blue-600"
                    >
                      <EyeIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        downloadFile(file);
                      }}
                      className="p-1 text-gray-400 hover:text-green-600"
                    >
                      <ArrowDownTrayIcon className="h-4 w-4" />
                    </button>
                    {allowDelete && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteFile(file.id);
                        }}
                        className="p-1 text-gray-400 hover:text-red-600"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="divide-y divide-gray-200">
            {filteredFiles.map((file) => {
              const FileIcon = getFileIcon(file.fileType);
              return (
                <div
                  key={file.id}
                  className="p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => onFileSelect?.(file)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        {file.thumbnailUrl ? (
                          <img
                            src={file.thumbnailUrl}
                            alt={file.originalName}
                            className="h-10 w-10 object-cover rounded"
                          />
                        ) : (
                          <div className="h-10 w-10 bg-gray-100 rounded flex items-center justify-center">
                            <FileIcon className="h-5 w-5 text-gray-500" />
                          </div>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.originalName}
                        </p>
                        <p className="text-sm text-gray-500">
                          {formatFileSize(file.fileSize)} • {formatDate(file.uploadedAt)}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openPreview(file);
                        }}
                        className="p-2 text-gray-400 hover:text-blue-600"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadFile(file);
                        }}
                        className="p-2 text-gray-400 hover:text-green-600"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4" />
                      </button>
                      {allowDelete && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteFile(file.id);
                          }}
                          className="p-2 text-gray-400 hover:text-red-600"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <FilePreviewModal />
    </div>
  );
};

export default MediaGallery;