// WebSocket message types for room collaboration

export interface WSMessage {
  type: string;
  room_id?: string;
  [key: string]: any;
}

export interface ChatMessage extends WSMessage {
  type: 'chat_message';
  content: string;
  attachments?: MessageAttachment[];
  reply_to?: string;
}

export interface MessageAttachment {
  url: string;
  type: 'image' | 'document' | 'audio';
  name: string;
  size: number;
}

export interface UserTypingMessage extends WSMessage {
  type: 'user_typing' | 'user_stopped_typing';
  user_id: string;
  username: string;
}

export interface UserJoinedMessage extends WSMessage {
  type: 'user_joined';
  user_id: string;
  username: string;
  role: string;
}

export interface UserLeftMessage extends WSMessage {
  type: 'user_left';
  user_id: string;
  username: string;
}

export interface MediaStateChangeMessage extends WSMessage {
  type: 'media_state_change';
  user_id: string;
  is_muted?: boolean;
  is_video_on?: boolean;
  is_screen_sharing?: boolean;
}

export interface HandRaiseMessage extends WSMessage {
  type: 'hand_raise';
  user_id: string;
  raised: boolean;
}

export interface RoomStatusUpdateMessage extends WSMessage {
  type: 'room_status_update';
  status: 'active' | 'inactive' | 'archived';
}

export interface ParticipantsUpdateMessage extends WSMessage {
  type: 'participants_update';
  participants: any[];
}

// WebRTC signaling messages
export interface WebRTCOffer extends WSMessage {
  type: 'webrtc_offer';
  from_user_id: string;
  to_user_id: string;
  offer: RTCSessionDescriptionInit;
}

export interface WebRTCAnswer extends WSMessage {
  type: 'webrtc_answer';
  from_user_id: string;
  to_user_id: string;
  answer: RTCSessionDescriptionInit;
}

export interface WebRTCIceCandidate extends WSMessage {
  type: 'webrtc_ice_candidate';
  from_user_id: string;
  to_user_id: string;
  candidate: RTCIceCandidateInit;
}

// Union type for all WebSocket messages
export type RoomWebSocketMessage = 
  | ChatMessage
  | UserTypingMessage
  | UserJoinedMessage
  | UserLeftMessage
  | MediaStateChangeMessage
  | HandRaiseMessage
  | RoomStatusUpdateMessage
  | ParticipantsUpdateMessage
  | WebRTCOffer
  | WebRTCAnswer
  | WebRTCIceCandidate;