export interface Message {
  id: string;
  type?: 'text' | 'image' | 'audio' | 'file' | 'system' | 'chat' | 'notification' | 'status' | 'typing' | 'ai_response' | 'ai_stream_chunk' | 'ai_image_analysis' | 'user_question' | 'ai_question';
  content: string;
  sender_id: string;
  sender_name?: string;
  sender_type?: 'user' | 'doctor' | 'system' | 'ai';
  timestamp: string;
  metadata?: {
    message_type?: 'text' | 'image' | 'audio' | 'document';
    file_url?: string;
    file_name?: string;
    file_size?: number;
    doctor_specialty?: string;
    analysis_result?: any;
    confidence_score?: number;
    reply_to?: string;
    edited?: boolean;
    edited_at?: string;
    notification_type?: string;
    participant?: any;
    user_id?: string;
    username?: string;
  };
  status?: 'sending' | 'sent' | 'delivered' | 'failed' | 'read';
  room_id?: string;
  case_id?: string;
  reactions?: MessageReaction[];
  // AI-specific fields
  data?: any;
  references?: Array<{ title: string; url: string }>;
  confidence?: number;
}

export interface MessageReaction {
  emoji: string;
  users: string[];
}

export interface TypingUser {
  user_id: string;
  username: string;
  room_id?: string;
}

export interface OnlineUser {
  user_id: string;
  username: string;
  status: 'online' | 'away' | 'busy';
}