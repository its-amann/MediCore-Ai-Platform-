// Room-related TypeScript interfaces

// Import common types to avoid duplication
import type { Message, MessageReaction } from './common';

// Export RoomType enum to match what's used in collaborationService.ts
export enum RoomType {
  CASE_DISCUSSION = 'case_discussion',
  TEACHING = 'teaching'
}

export enum RoomStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ARCHIVED = 'archived'
}

export interface Room {
  room_id: string;
  name: string;
  description?: string;
  room_type: RoomType;
  status: RoomStatus;
  host_id: string;
  max_participants?: number;
  is_private: boolean;
  created_at: string;
  updated_at: string;
  participant_count?: number;
  tags?: string[];
  settings?: RoomSettings;
  metadata?: {
    subject?: string;
    topic?: string;
    schedule_time?: string;
    duration?: number;
    materials_url?: string;
    case_id?: string;
    [key: string]: any;
  };
}

export interface RoomSettings {
  allow_recording?: boolean;
  allow_screen_share?: boolean;
  allow_file_share?: boolean;
  allow_video?: boolean;
  mute_participants_on_join?: boolean;
  require_permission_to_speak?: boolean;
  enable_waiting_room?: boolean;
  enable_chat?: boolean;
  enable_reactions?: boolean;
}

export interface RoomParticipant {
  user_id: string;
  username: string;
  role: 'host' | 'moderator' | 'participant' | 'viewer';
  joined_at: string;
  is_muted?: boolean;
  is_video_on?: boolean;
  is_screen_sharing?: boolean;
  is_speaking?: boolean;
  has_raised_hand?: boolean;
  connection_quality?: 'excellent' | 'good' | 'poor';
  avatar_url?: string;
}

// Re-export Message and MessageReaction from common to maintain compatibility
export type { Message, MessageReaction };

export interface VideoParticipant extends RoomParticipant {
  stream?: MediaStream;
  peer_id?: string;
  video_quality?: 'HD' | 'SD' | 'LD';
  audio_level?: number;
}