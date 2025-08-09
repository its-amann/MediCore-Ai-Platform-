import React, { useState } from 'react';
import {
  XMarkIcon,
  LinkIcon,
  EnvelopeIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  UserPlusIcon
} from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';
import { toast } from 'react-hot-toast';
import collaborationService from '../../services/collaborationService';

interface InviteParticipantsModalProps {
  isOpen: boolean;
  onClose: () => void;
  roomId: string;
  roomName: string;
}

const InviteParticipantsModal: React.FC<InviteParticipantsModalProps> = ({
  isOpen,
  onClose,
  roomId,
  roomName
}) => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [emails, setEmails] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'link' | 'email'>('link');

  const roomLink = `${window.location.origin}/rooms/${roomId}`;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(roomLink);
      setLinkCopied(true);
      toast.success('Room link copied to clipboard');
      setTimeout(() => setLinkCopied(false), 3000);
    } catch (error) {
      toast.error('Failed to copy link');
    }
  };

  const handleAddEmail = () => {
    const trimmedEmail = email.trim();
    if (trimmedEmail && !emails.includes(trimmedEmail)) {
      if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
        setEmails([...emails, trimmedEmail]);
        setEmail('');
      } else {
        toast.error('Please enter a valid email address');
      }
    }
  };

  const handleRemoveEmail = (emailToRemove: string) => {
    setEmails(emails.filter(e => e !== emailToRemove));
  };

  const handleSendInvites = async () => {
    if (emails.length === 0) {
      toast.error('Please add at least one email address');
      return;
    }

    setIsLoading(true);
    try {
      await collaborationService.inviteParticipants(roomId, {
        emails,
        message: message.trim() || undefined
      });
      toast.success(`Invitations sent to ${emails.length} participant${emails.length > 1 ? 's' : ''}`);
      setEmails([]);
      setMessage('');
      onClose();
    } catch (error) {
      console.error('Failed to send invitations:', error);
      toast.error('Failed to send invitations');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative bg-white rounded-xl shadow-xl max-w-md w-full mx-4 overflow-hidden"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <UserPlusIcon className="h-5 w-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">
                Invite to {roomName}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('link')}
            className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'link'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <LinkIcon className="h-4 w-4 inline mr-2" />
            Share Link
          </button>
          <button
            onClick={() => setActiveTab('email')}
            className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'email'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <EnvelopeIcon className="h-4 w-4 inline mr-2" />
            Email Invite
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'link' ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Share this link with others to invite them to the room
              </p>
              
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={roomLink}
                  readOnly
                  className="flex-1 px-3 py-2 text-sm bg-gray-50 border border-gray-300 rounded-lg focus:outline-none"
                />
                <button
                  onClick={handleCopyLink}
                  className={`px-4 py-2 rounded-lg transition-all ${
                    linkCopied
                      ? 'bg-green-600 text-white'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {linkCopied ? (
                    <>
                      <CheckIcon className="h-4 w-4 inline mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <ClipboardDocumentIcon className="h-4 w-4 inline mr-1" />
                      Copy
                    </>
                  )}
                </button>
              </div>

              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-blue-700">
                  Anyone with this link can request to join the room. 
                  {roomName.includes('Private') && ' You will need to approve their request.'}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Send email invitations to specific participants
              </p>

              {/* Email input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email addresses
                </label>
                <div className="flex space-x-2">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddEmail()}
                    placeholder="Enter email address"
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    onClick={handleAddEmail}
                    className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Email list */}
              {emails.length > 0 && (
                <div className="space-y-1">
                  {emails.map((email, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg"
                    >
                      <span className="text-sm text-gray-700">{email}</span>
                      <button
                        onClick={() => handleRemoveEmail(email)}
                        className="text-xs text-red-600 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Custom message */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Personal message (optional)
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Add a personal message to your invitation..."
                  rows={3}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>

              {/* Send button */}
              <button
                onClick={handleSendInvites}
                disabled={emails.length === 0 || isLoading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Sending...
                  </span>
                ) : (
                  `Send ${emails.length} invitation${emails.length !== 1 ? 's' : ''}`
                )}
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default InviteParticipantsModal;