/**
 * Voice Consultation API Service
 * Handles all API calls for the new voice consultation system
 */

import api from './axios';

const VOICE_BASE_URL = '/voice/consultation';

export interface VoiceSessionInfo {
  session_id: string;
  status: string;
  mode: string;
  started_at: string;
  chat_count: number;
}

export interface VoiceResponse {
  status: string;
  transcription?: string;
  response_text?: string;
  audio_response?: string;
  session_id?: string;
  message?: string;
}

export interface AgentInfo {
  provider: string;
  model_id: string | null;
  tools: string[];
  status: string;
}

class VoiceConsultationAPI {
  /**
   * Start a new voice consultation session
   */
  async startSession(userInfo?: any): Promise<any> {
    const response = await api.post(`${VOICE_BASE_URL}/sessions/create`, {
      consultation_type: 'audio',
      user_id: userInfo?.user_id
    });
    return response.data;
  }

  /**
   * Process audio input
   */
  async processAudio(sessionId: string, audioFile: File | Blob): Promise<VoiceResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    formData.append('session_id', sessionId);
    formData.append('format', 'webm');
    
    const response = await api.post(
      `${VOICE_BASE_URL}/process-audio`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  /**
   * Process text input
   */
  async processText(sessionId: string, text: string): Promise<VoiceResponse> {
    const response = await api.post(`${VOICE_BASE_URL}/process-text`, {
      session_id: sessionId,
      text,
    });
    return response.data;
  }

  /**
   * Set consultation mode (voice, video, screen_share)
   */
  async setMode(sessionId: string, mode: 'voice' | 'video' | 'screen_share'): Promise<any> {
    const response = await api.post(`${VOICE_BASE_URL}/set-mode`, {
      session_id: sessionId,
      mode,
    });
    return response.data;
  }

  /**
   * Get session information
   */
  async getSessionInfo(sessionId: string): Promise<VoiceSessionInfo> {
    const response = await api.get(`${VOICE_BASE_URL}/session/${sessionId}`);
    return response.data;
  }

  /**
   * End consultation session
   */
  async endSession(sessionId: string): Promise<any> {
    const response = await api.post(`${VOICE_BASE_URL}/end`, {
      session_id: sessionId
    });
    return response.data;
  }

  /**
   * Get active sessions
   */
  async getActiveSessions(): Promise<{ sessions: string[] }> {
    const response = await api.get(`${VOICE_BASE_URL}/active-sessions`);
    return response.data;
  }

  /**
   * Switch AI provider
   */
  async switchProvider(provider: string, modelId?: string): Promise<any> {
    const response = await api.post(`${VOICE_BASE_URL}/switch-provider`, {
      provider,
      model_id: modelId,
    });
    return response.data;
  }

  /**
   * Get agent information
   */
  async getAgentInfo(): Promise<AgentInfo> {
    const response = await api.get(`${VOICE_BASE_URL}/agent-info`);
    return response.data;
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<any> {
    const response = await api.get(`${VOICE_BASE_URL}/health`);
    return response.data;
  }

  /**
   * Get WebSocket URL for real-time communication
   */
  getWebSocketUrl(sessionId: string): string {
    const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    return `${baseUrl}/api/v1/voice/consultation/ws/${sessionId}`;
  }
}

export default new VoiceConsultationAPI();