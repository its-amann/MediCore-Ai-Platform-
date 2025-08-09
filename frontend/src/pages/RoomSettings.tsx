import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  CogIcon,
  UserGroupIcon,
  ShieldCheckIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  UserMinusIcon,
  UserPlusIcon,
  KeyIcon
} from '@heroicons/react/24/outline';
import api from '../api/axios';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

interface RoomSettings {
  room_id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  is_public: boolean;
  password_protected: boolean;
  max_participants: number;
  voice_enabled: boolean;
  screen_sharing: boolean;
  recording_enabled: boolean;
  settings: {
    allow_anonymous: boolean;
    require_approval: boolean;
    auto_close_empty: boolean;
    auto_close_minutes: number;
  };
  created_by: {
    user_id: string;
    username: string;
  };
  moderators: Array<{
    user_id: string;
    username: string;
  }>;
  banned_users: Array<{
    user_id: string;
    username: string;
    banned_at: string;
    banned_by: string;
  }>;
}

interface Participant {
  user_id: string;
  username: string;
  role: string;
  joined_at: string;
  is_online: boolean;
}

const RoomSettings: React.FC = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [room, setRoom] = useState<RoomSettings | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('general');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');

  useEffect(() => {
    fetchRoomSettings();
    fetchParticipants();
  }, [roomId]);

  const fetchRoomSettings = async () => {
    try {
      const response = await api.get(`/rooms/${roomId}/settings`);
      setRoom(response.data);
    } catch (error) {
      console.error('Failed to fetch room settings:', error);
      toast.error('Failed to load room settings');
      navigate('/rooms');
    } finally {
      setLoading(false);
    }
  };

  const fetchParticipants = async () => {
    try {
      const response = await api.get(`/rooms/${roomId}/participants`);
      setParticipants(response.data.participants || []);
    } catch (error) {
      console.error('Failed to fetch participants:', error);
    }
  };

  const updateRoomSettings = async (updates: Partial<RoomSettings>) => {
    try {
      await api.put(`/rooms/${roomId}/settings`, updates);
      toast.success('Settings updated successfully');
      fetchRoomSettings();
    } catch (error) {
      console.error('Failed to update settings:', error);
      toast.error('Failed to update settings');
    }
  };

  const handleInputChange = (field: string, value: any) => {
    if (!room) return;

    const updates = {
      [field]: value
    };

    updateRoomSettings(updates);
  };

  const handleSettingChange = (setting: string, value: any) => {
    if (!room) return;

    const updates = {
      settings: {
        ...room.settings,
        [setting]: value
      }
    };

    updateRoomSettings(updates);
  };

  const addModerator = async (userId: string) => {
    try {
      await api.post(`/rooms/${roomId}/moderators`, { user_id: userId });
      toast.success('Moderator added successfully');
      fetchRoomSettings();
      fetchParticipants();
    } catch (error) {
      toast.error('Failed to add moderator');
    }
  };

  const removeModerator = async (userId: string) => {
    try {
      await api.delete(`/rooms/${roomId}/moderators/${userId}`);
      toast.success('Moderator removed successfully');
      fetchRoomSettings();
      fetchParticipants();
    } catch (error) {
      toast.error('Failed to remove moderator');
    }
  };

  const banUser = async (userId: string) => {
    try {
      await api.post(`/rooms/${roomId}/ban`, { user_id: userId });
      toast.success('User banned successfully');
      fetchRoomSettings();
      fetchParticipants();
    } catch (error) {
      toast.error('Failed to ban user');
    }
  };

  const unbanUser = async (userId: string) => {
    try {
      await api.delete(`/rooms/${roomId}/ban/${userId}`);
      toast.success('User unbanned successfully');
      fetchRoomSettings();
    } catch (error) {
      toast.error('Failed to unban user');
    }
  };

  const deleteRoom = async () => {
    if (!room || deleteConfirmation !== room.name) {
      toast.error('Room name does not match');
      return;
    }

    try {
      await api.delete(`/rooms/${roomId}`);
      toast.success('Room deleted successfully');
      navigate('/rooms');
    } catch (error) {
      toast.error('Failed to delete room');
    }
  };

  if (loading || !room) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const isOwner = room.created_by.user_id === user?.user_id;
  const isModerator = room.moderators.some(mod => mod.user_id === user?.user_id);
  const canManage = isOwner || isModerator;

  if (!canManage) {
    navigate(`/rooms/${roomId}`);
    return null;
  }

  const tabs = [
    { id: 'general', name: 'General', icon: CogIcon },
    { id: 'participants', name: 'Participants', icon: UserGroupIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'danger', name: 'Danger Zone', icon: ExclamationTriangleIcon, show: isOwner }
  ];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={() => navigate(`/rooms/${roomId}`)}
              className="mr-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Room Settings</h1>
              <p className="text-gray-600 mt-1">{room.name}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-64">
          <nav className="space-y-1">
            {tabs.filter(tab => tab.show !== false).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="h-5 w-5 mr-3" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'general' && (
            <div className="bg-white rounded-lg shadow p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">General Settings</h2>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Room Name
                </label>
                <input
                  type="text"
                  value={room.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={room.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Maximum Participants
                </label>
                <select
                  value={room.max_participants}
                  onChange={(e) => handleInputChange('max_participants', parseInt(e.target.value, 10))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value={5}>5 participants</option>
                  <option value={10}>10 participants</option>
                  <option value={20}>20 participants</option>
                  <option value={50}>50 participants</option>
                  <option value={100}>100 participants</option>
                </select>
              </div>

              <div className="space-y-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={room.voice_enabled}
                    onChange={(e) => handleInputChange('voice_enabled', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-700">Enable voice chat</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={room.screen_sharing}
                    onChange={(e) => handleInputChange('screen_sharing', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-700">Enable screen sharing</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={room.recording_enabled}
                    onChange={(e) => handleInputChange('recording_enabled', e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-sm text-gray-700">Enable recording</span>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'participants' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Participants & Moderators</h2>
              
              <div className="space-y-6">
                {/* Moderators */}
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3">Moderators</h3>
                  <div className="space-y-2">
                    {room.moderators.map((mod) => (
                      <div key={mod.user_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center">
                          <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-blue-600">
                              {mod.username.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <span className="ml-3 text-sm font-medium text-gray-900">
                            {mod.username}
                          </span>
                        </div>
                        {isOwner && mod.user_id !== user?.user_id && (
                          <button
                            onClick={() => removeModerator(mod.user_id)}
                            className="text-sm text-red-600 hover:text-red-700"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Active Participants */}
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3">Active Participants</h3>
                  <div className="space-y-2">
                    {participants
                      .filter(p => !room.moderators.some(m => m.user_id === p.user_id))
                      .map((participant) => (
                        <div key={participant.user_id} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                          <div className="flex items-center">
                            <div className="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center">
                              <span className="text-sm font-medium text-gray-700">
                                {participant.username.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div className="ml-3">
                              <span className="text-sm font-medium text-gray-900">
                                {participant.username}
                              </span>
                              <p className="text-xs text-gray-500">
                                Joined {new Date(participant.joined_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => addModerator(participant.user_id)}
                              className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                              title="Make moderator"
                            >
                              <UserPlusIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => banUser(participant.user_id)}
                              className="p-1 text-red-600 hover:bg-red-50 rounded"
                              title="Ban user"
                            >
                              <UserMinusIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

                {/* Banned Users */}
                {room.banned_users.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-3">Banned Users</h3>
                    <div className="space-y-2">
                      {room.banned_users.map((banned) => (
                        <div key={banned.user_id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                          <div>
                            <span className="text-sm font-medium text-gray-900">
                              {banned.username}
                            </span>
                            <p className="text-xs text-gray-500">
                              Banned on {new Date(banned.banned_at).toLocaleDateString()}
                            </p>
                          </div>
                          <button
                            onClick={() => unbanUser(banned.user_id)}
                            className="text-sm text-blue-600 hover:text-blue-700"
                          >
                            Unban
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="bg-white rounded-lg shadow p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">Security Settings</h2>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">Room Visibility</p>
                    <p className="text-sm text-gray-600">
                      {room.is_public ? 'Anyone can find and join this room' : 'Only invited users can join'}
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={room.is_public}
                      onChange={(e) => handleInputChange('is_public', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">Password Protection</p>
                    <p className="text-sm text-gray-600">Require a password to join</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={room.password_protected}
                      onChange={(e) => handleInputChange('password_protected', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                {room.password_protected && (
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">Change Password</p>
                        <p className="text-sm text-gray-600">Update the room password</p>
                      </div>
                      <button className="flex items-center px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
                        <KeyIcon className="h-4 w-4 mr-1.5" />
                        Change
                      </button>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">Require Approval</p>
                    <p className="text-sm text-gray-600">Approve participants before they can join</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={room.settings.require_approval}
                      onChange={(e) => handleSettingChange('require_approval', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'danger' && isOwner && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-red-600 mb-6">Danger Zone</h2>
              
              <div className="space-y-6">
                <div className="p-4 border border-red-200 rounded-lg bg-red-50">
                  <h3 className="font-medium text-gray-900 mb-2">Delete Room</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Once you delete a room, there is no going back. All messages, files, and settings will be permanently deleted.
                  </p>
                  <button
                    onClick={() => setShowDeleteModal(true)}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                  >
                    Delete Room
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && room && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Delete Room</h3>
            <p className="text-gray-600 mb-4">
              This action cannot be undone. This will permanently delete the room and all its contents.
            </p>
            <p className="text-sm text-gray-600 mb-4">
              Please type <span className="font-mono font-semibold">{room.name}</span> to confirm.
            </p>
            <input
              type="text"
              value={deleteConfirmation}
              onChange={(e) => setDeleteConfirmation(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent mb-4"
              placeholder="Type room name here"
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmation('');
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={deleteRoom}
                disabled={deleteConfirmation !== room.name}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                Delete Room
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoomSettings;