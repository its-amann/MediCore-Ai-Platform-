/**
 * Central export file for all application types
 */

// Export common types
export * from './common';

// Export WebSocket types with namespace to avoid conflicts
export * as WebSocketTypes from './websocket';

// Export room types
export * from './room';

// Export medical imaging and report types
export * from './medical';

// Re-export specific types to resolve naming conflicts
export type { ChatMessage as MedicalChatMessage } from '../components/MedicalImaging/types';
export type { ChatMessage as WSChatMessage } from './websocket';