import api from '../api/axios';
import { toast } from 'react-hot-toast';
import { Room, RoomType, RoomStatus } from '../types/room';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Re-export types for backward compatibility
export type { Room } from '../types/room';
export { RoomType, RoomStatus } from '../types/room';

export interface CreateRoomRequest {
  name: string;
  description?: string;
  room_type: RoomType;
  max_participants?: number;
  is_private: boolean;
  password?: string;
  tags?: string[];
}

export interface RoomParticipant {
  user_id: string;
  username: string;
  role: 'host' | 'participant' | 'viewer';
  joined_at: string;
  is_muted?: boolean;
  is_video_on?: boolean;
}

export interface JoinRequest {
  request_id: string;
  room_id: string;
  user_id: string;
  username: string;
  message?: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

class CollaborationService {
  private baseURL: string;

  constructor() {
    // Use collaboration microservice rooms endpoint
    this.baseURL = `${API_BASE_URL}/collaboration/rooms`;
  }

  // Room Management
  async getRooms(filters?: { room_type?: RoomType; status?: RoomStatus; is_private?: boolean }) {
    try {
      const params = new URLSearchParams();
      if (filters?.room_type) params.append('room_type', filters.room_type);
      if (filters?.status) params.append('status', filters.status);
      if (filters?.is_private !== undefined) params.append('is_private', filters.is_private.toString());
      
      const response = await api.get(`${this.baseURL}`, { params });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch rooms');
      throw error;
    }
  }

  async getRoom(roomId: string) {
    try {
      const response = await api.get(`${this.baseURL}/${roomId}`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch room details');
      throw error;
    }
  }

  async createRoom(data: CreateRoomRequest) {
    try {
      // Prepare request body matching backend expectations
      const requestBody = {
        name: data.name,
        description: data.description || '',
        room_type: data.room_type,
        max_participants: data.max_participants || 10,
        is_public: !data.is_private,
        password_protected: !!data.password,
        room_password: data.password,
        voice_enabled: true,
        screen_sharing: true,
        recording_enabled: false,
        settings: {
          require_approval: false
        },
        tags: data.tags || []
      };
      
      const response = await api.post(this.baseURL, requestBody);
      toast.success('Room created successfully');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create room');
      throw error;
    }
  }

  async updateRoom(roomId: string, data: Partial<CreateRoomRequest>) {
    try {
      const response = await api.put(`${this.baseURL}/${roomId}`, data);
      toast.success('Room updated successfully');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update room');
      throw error;
    }
  }

  async deleteRoom(roomId: string) {
    try {
      await api.delete(`${this.baseURL}/${roomId}`);
      toast.success('Room deleted successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete room');
      throw error;
    }
  }

  // Participant Management
  async getRoomParticipants(roomId: string) {
    try {
      const response = await api.get(`${this.baseURL}/${roomId}/participants`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch participants');
      throw error;
    }
  }

  async joinRoom(roomId: string, password?: string) {
    try {
      const response = await api.post(`${this.baseURL}/${roomId}/join`, { password });
      toast.success('Joined room successfully');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to join room');
      throw error;
    }
  }

  async leaveRoom(roomId: string) {
    try {
      await api.post(`${this.baseURL}/${roomId}/leave`);
      toast.success('Left room successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to leave room');
      throw error;
    }
  }

  async removeParticipant(roomId: string, userId: string) {
    try {
      await api.delete(`${this.baseURL}/${roomId}/participants/${userId}`);
      toast.success('Participant removed successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to remove participant');
      throw error;
    }
  }

  // Join Requests
  async getJoinRequests(roomId: string) {
    try {
      const response = await api.get(`${this.baseURL}/${roomId}/requests`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch join requests');
      throw error;
    }
  }

  async sendJoinRequest(roomId: string, message?: string) {
    try {
      const response = await api.post(`${this.baseURL}/${roomId}/request`, { message });
      toast.success('Join request sent successfully');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to send join request');
      throw error;
    }
  }

  async handleJoinRequest(roomId: string, requestId: string, action: 'approve' | 'reject') {
    try {
      const response = await api.post(`${this.baseURL}/${roomId}/requests/${requestId}/${action}`);
      toast.success(`Request ${action}d successfully`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Failed to ${action} request`);
      throw error;
    }
  }

  // Chat Messages
  async getRoomMessages(roomId: string, limit: number = 50, offset: number = 0) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/chat/rooms/${roomId}/messages`, {
        params: { limit, offset }
      });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch messages');
      throw error;
    }
  }

  async sendMessage(roomId: string, content: string, attachments?: any[]) {
    try {
      // Backend expects form data for messages
      const formData = new FormData();
      formData.append('content', content);
      formData.append('message_type', 'text');
      
      const response = await api.post(`${API_BASE_URL}/collaboration/chat/rooms/${roomId}/messages`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to send message');
      throw error;
    }
  }

  // User Rooms
  async getUserRooms() {
    try {
      const response = await api.get(`${this.baseURL}/user/rooms`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch user rooms');
      throw error;
    }
  }

  // Invitations
  async inviteParticipants(roomId: string, data: { emails: string[]; message?: string }) {
    try {
      const response = await api.post(`${this.baseURL}/${roomId}/invite`, data);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  }

  // Notifications
  async getNotifications(unread_only: boolean = false) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/notifications`, {
        params: { unread_only }
      });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch notifications');
      throw error;
    }
  }

  async markNotificationAsRead(notificationId: string) {
    try {
      const response = await api.put(`${API_BASE_URL}/collaboration/notifications/${notificationId}/read`);
      return response.data;
    } catch (error: any) {
      console.error('Failed to mark notification as read:', error);
      throw error;
    }
  }

  async markAllNotificationsAsRead() {
    try {
      const response = await api.put(`${API_BASE_URL}/collaboration/notifications/read-all`);
      return response.data;
    } catch (error: any) {
      console.error('Failed to mark all notifications as read:', error);
      throw error;
    }
  }

  async deleteNotification(notificationId: string) {
    try {
      await api.delete(`${API_BASE_URL}/collaboration/notifications/${notificationId}`);
      toast.success('Notification deleted');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete notification');
      throw error;
    }
  }

  // Notification Preferences
  async getNotificationPreferences(userId: string) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/notifications/preferences/${userId}`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch notification preferences');
      throw error;
    }
  }

  async updateNotificationPreferences(userId: string, preferences: any) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/notifications/preferences`, {
        user_id: userId,
        ...preferences
      });
      toast.success('Notification preferences updated');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update notification preferences');
      throw error;
    }
  }

  async subscribeToNotifications(subscription: any) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/notifications/subscribe`, subscription);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to subscribe to notifications');
      throw error;
    }
  }

  // User Profile Management
  async getUserProfile(userId: string) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/users/${userId}`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch user profile');
      throw error;
    }
  }

  async updateUserProfile(userId: string, profileData: any) {
    try {
      const response = await api.put(`${API_BASE_URL}/collaboration/users/${userId}`, profileData);
      toast.success('Profile updated successfully');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
      throw error;
    }
  }

  async requestVerification(userId: string, documents: FormData) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/users/${userId}/verify`, documents, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success('Verification request submitted');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to submit verification request');
      throw error;
    }
  }

  // Screen Sharing
  async startScreenShare(roomId: string, data: any) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/screen-share/${roomId}/start`, data);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to start screen sharing');
      throw error;
    }
  }

  async stopScreenShare(roomId: string) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/screen-share/${roomId}/stop`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to stop screen sharing');
      throw error;
    }
  }

  async updateScreenShareQuality(roomId: string, quality: string) {
    try {
      const response = await api.put(`${API_BASE_URL}/collaboration/screen-share/${roomId}/quality`, { quality });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update quality');
      throw error;
    }
  }

  async getScreenShareStatus(roomId: string) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/screen-share/${roomId}/status`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to get screen share status');
      throw error;
    }
  }

  // Gemini AI Integration
  async startAISession(roomId: string, mode: string, context?: any) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/ai/sessions/${roomId}/start`, {
        mode,
        context
      });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to start AI session');
      throw error;
    }
  }

  async sendAIMessage(roomId: string, message: string, mode?: string) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/ai/sessions/${roomId}/message`, {
        message,
        mode
      });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to send AI message');
      throw error;
    }
  }

  async getAISummary(roomId: string) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/ai/sessions/${roomId}/summary`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to get AI summary');
      throw error;
    }
  }

  // File Management
  async uploadFile(roomId: string, file: File, description?: string) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('room_id', roomId);
      if (description) {
        formData.append('description', description);
      }

      const response = await api.post(`${API_BASE_URL}/collaboration/media/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success('File uploaded successfully');
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to upload file');
      throw error;
    }
  }

  async getRoomFiles(roomId: string) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/media/rooms/${roomId}/files`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch room files');
      throw error;
    }
  }

  async getFile(fileId: string) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/media/files/${fileId}`);
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch file');
      throw error;
    }
  }

  async downloadFile(fileId: string) {
    try {
      const response = await api.get(`${API_BASE_URL}/collaboration/media/files/${fileId}/download`, {
        responseType: 'blob'
      });
      return response.data;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to download file');
      throw error;
    }
  }

  async deleteFile(fileId: string) {
    try {
      await api.delete(`${API_BASE_URL}/collaboration/media/files/${fileId}`);
      toast.success('File deleted successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete file');
      throw error;
    }
  }

  // Screen Sharing & WebRTC (handled via WebSocket)
  // These are managed through WebSocket connections, not REST API
  // See useCollaborationWebSocket hook for WebRTC signaling

  // AI Assistant Integration
  async getAISuggestions(roomId: string, context: any) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/ai/suggestions`, {
        room_id: roomId,
        context
      });
      return response.data;
    } catch (error: any) {
      console.error('Failed to get AI suggestions:', error);
      // Don't show error toast for AI features as they're optional
      return null;
    }
  }

  async generateSummary(roomId: string) {
    try {
      const response = await api.post(`${API_BASE_URL}/collaboration/ai/summary`, {
        room_id: roomId
      });
      return response.data;
    } catch (error: any) {
      toast.error('Failed to generate summary');
      throw error;
    }
  }
}

export const collaborationService = new CollaborationService();
export default collaborationService;