import React, { useState, useRef, useEffect } from 'react';
import { useRoom } from '../../../contexts/RoomContext';
import { useWebSocket } from '../../../contexts/WebSocketContext';
import {
  PaperAirplaneIcon,
  PhotoIcon,
  DocumentIcon,
  FaceSmileIcon,
  XMarkIcon,
  ChevronDownIcon,
  CameraIcon
} from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';
import EmojiPicker from 'emoji-picker-react';
import { toast } from 'react-hot-toast';

interface FilePreview {
  file: File;
  url: string;
  type: 'image' | 'document';
}

interface EnhancedMessageInputProps {
  onScreenshotCapture?: (screenshot: Blob) => void;
  isScreenSharing?: boolean;
  screenShareUserId?: string;
  screenShareUsername?: string;
}

const EnhancedMessageInput: React.FC<EnhancedMessageInputProps> = ({
  onScreenshotCapture,
  isScreenSharing = false,
  screenShareUserId,
  screenShareUsername
}) => {
  const { sendMessage, room } = useRoom();
  const { startTyping, stopTyping } = useWebSocket();
  const [message, setMessage] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [filePreviews, setFilePreviews] = useState<FilePreview[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadMenu, setShowUploadMenu] = useState(false);
  const [isCapturingScreenshot, setIsCapturingScreenshot] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  // Handle typing indicators
  useEffect(() => {
    if (message.trim()) {
      startTyping(room?.room_id);
      
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      
      typingTimeoutRef.current = setTimeout(() => {
        stopTyping(room?.room_id);
      }, 2000);
    } else {
      stopTyping(room?.room_id);
    }

    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [message, room?.room_id, startTyping, stopTyping]);

  const handleScreenshotCapture = async () => {
    if (!isScreenSharing) {
      toast.error('No active screen share to capture');
      return;
    }

    setIsCapturingScreenshot(true);
    try {
      // Get the screen share video element
      const screenShareVideo = document.querySelector(`video[data-user-id="${screenShareUserId}"]`) as HTMLVideoElement;
      
      if (!screenShareVideo) {
        toast.error('Screen share video not found');
        return;
      }

      // Create a canvas to capture the screenshot
      const canvas = document.createElement('canvas');
      canvas.width = screenShareVideo.videoWidth;
      canvas.height = screenShareVideo.videoHeight;
      const ctx = canvas.getContext('2d');
      
      if (!ctx) {
        toast.error('Failed to create canvas context');
        return;
      }

      // Draw the current frame
      ctx.drawImage(screenShareVideo, 0, 0, canvas.width, canvas.height);
      
      // Convert to blob
      canvas.toBlob(async (blob) => {
        if (!blob) {
          toast.error('Failed to capture screenshot');
          return;
        }

        // Create a file from the blob
        const file = new File([blob], `screenshot-${Date.now()}.png`, { type: 'image/png' });
        
        // Add to file previews
        const reader = new FileReader();
        reader.onload = () => {
          const preview: FilePreview = {
            file,
            url: reader.result as string,
            type: 'image'
          };
          setFilePreviews(prev => [...prev, preview]);
        };
        reader.readAsDataURL(file);

        // Call the callback if provided
        if (onScreenshotCapture) {
          onScreenshotCapture(blob);
        }

        toast.success(`Screenshot captured from ${screenShareUsername}'s screen share`);
      }, 'image/png');

    } catch (error) {
      console.error('Error capturing screenshot:', error);
      toast.error('Failed to capture screenshot');
    } finally {
      setIsCapturingScreenshot(false);
    }
  };

  const handleSend = async () => {
    if (!message.trim() && filePreviews.length === 0) return;

    try {
      const attachments = filePreviews.length > 0 ? 
        filePreviews.map(fp => ({
          url: fp.url,
          type: fp.type,
          name: fp.file.name,
          size: fp.file.size
        })) : undefined;

      await sendMessage(message.trim(), attachments);
      
      setMessage('');
      setFilePreviews([]);
      stopTyping(room?.room_id);
      
      inputRef.current?.focus();
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const preview: FilePreview = {
          file,
          url: reader.result as string,
          type: file.type.startsWith('image/') ? 'image' : 'document'
        };
        setFilePreviews(prev => [...prev, preview]);
      };
      reader.readAsDataURL(file);
    });
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    setFilePreviews(prev => prev.filter((_, i) => i !== index));
  };

  const handleEmojiClick = (emoji: any) => {
    const cursorPosition = inputRef.current?.selectionStart || message.length;
    const newMessage = 
      message.slice(0, cursorPosition) + 
      emoji.emoji + 
      message.slice(cursorPosition);
    
    setMessage(newMessage);
    setShowEmojiPicker(false);
    
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
        const newPosition = cursorPosition + emoji.emoji.length;
        inputRef.current.setSelectionRange(newPosition, newPosition);
      }
    }, 0);
  };

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  return (
    <div className="border-t border-gray-200 bg-white">
      {/* File previews */}
      <AnimatePresence>
        {filePreviews.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 pt-3 pb-2 border-b border-gray-100"
          >
            <div className="flex flex-wrap gap-2">
              {filePreviews.map((preview, index) => (
                <div
                  key={index}
                  className="relative group"
                >
                  {preview.type === 'image' ? (
                    <img
                      src={preview.url}
                      alt="Upload preview"
                      className="h-20 w-20 object-cover rounded-lg"
                    />
                  ) : (
                    <div className="h-20 w-20 bg-gray-100 rounded-lg flex items-center justify-center">
                      <DocumentIcon className="h-8 w-8 text-gray-400" />
                    </div>
                  )}
                  
                  <button
                    onClick={() => removeFile(index)}
                    className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <XMarkIcon className="h-3 w-3" />
                  </button>
                  
                  {preview.type === 'document' && (
                    <p className="text-xs text-gray-600 mt-1 truncate max-w-[80px]">
                      {preview.file.name}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input area */}
      <div className="px-4 py-3">
        <div className="flex items-end space-x-2">
          {/* Upload menu button */}
          <div className="relative">
            <button
              onClick={() => setShowUploadMenu(!showUploadMenu)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex items-center"
              title="Upload media"
            >
              <PhotoIcon className="h-5 w-5" />
              <ChevronDownIcon className="h-3 w-3 ml-1" />
            </button>
            
            {showUploadMenu && (
              <div className="absolute bottom-full left-0 mb-2 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                <button
                  onClick={() => {
                    fileInputRef.current?.setAttribute('accept', 'image/*');
                    fileInputRef.current?.click();
                    setShowUploadMenu(false);
                  }}
                  className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                >
                  <PhotoIcon className="h-4 w-4 mr-2" />
                  Image
                </button>
                <button
                  onClick={() => {
                    fileInputRef.current?.setAttribute('accept', '.pdf,.doc,.docx,.txt');
                    fileInputRef.current?.click();
                    setShowUploadMenu(false);
                  }}
                  className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                >
                  <DocumentIcon className="h-4 w-4 mr-2" />
                  Document
                </button>
              </div>
            )}
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* Screenshot capture button - only show when screen sharing is active */}
          {isScreenSharing && (
            <button
              onClick={handleScreenshotCapture}
              disabled={isCapturingScreenshot}
              className={`p-2 rounded-lg transition-colors ${
                isCapturingScreenshot 
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                  : 'text-blue-600 hover:text-blue-700 hover:bg-blue-50'
              }`}
              title={`Capture screenshot from ${screenShareUsername}'s screen`}
            >
              <CameraIcon className="h-5 w-5" />
            </button>
          )}

          {/* Emoji picker button */}
          <div className="relative">
            <button
              onClick={() => setShowEmojiPicker(!showEmojiPicker)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Add emoji"
            >
              <FaceSmileIcon className="h-5 w-5" />
            </button>
            
            {showEmojiPicker && (
              <div className="absolute bottom-full left-0 mb-2 z-50">
                <EmojiPicker
                  onEmojiClick={handleEmojiClick}
                  searchDisabled
                  skinTonesDisabled
                  height={350}
                  width={300}
                />
              </div>
            )}
          </div>

          {/* Message input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message..."
              className="w-full px-4 py-2 pr-12 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={1}
              style={{ minHeight: '40px', maxHeight: '120px' }}
            />
            
            {/* Character count */}
            {message.length > 500 && (
              <span className="absolute bottom-2 right-12 text-xs text-gray-500">
                {message.length}/1000
              </span>
            )}
          </div>

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!message.trim() && filePreviews.length === 0}
            className={`p-2 rounded-lg transition-colors ${
              message.trim() || filePreviews.length > 0
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
            title="Send message"
          >
            <PaperAirplaneIcon className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default EnhancedMessageInput;