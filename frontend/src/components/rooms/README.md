# Room Components Documentation

## Overview
This directory contains all components for the collaboration room feature, supporting both case discussion (chat-only) and teaching (video + chat) room types.

## Component Structure

### Core Components
- **RoomHeader** - Top navigation bar with room info and controls
- **ParticipantsList** - Sidebar showing all room participants
- **CaseDiscussionView** - Layout for chat-only rooms
- **TeachingView** - Layout for video rooms with chat

### Chat Components
- **ChatArea** - Container for chat functionality
- **MessageList** - Displays chat messages with animations
- **MessageInput** - Input field with emoji picker and file attachments
- **TypingIndicator** - Shows who is currently typing

### Video Components
- **VideoGrid** - Grid layout for video participants
- **VideoControls** - Control bar for video/audio/screen sharing

### Utility Components
- **MobileLayout** - Responsive layout handler for mobile devices
- **LoadingRoom** - Loading state while joining room

## Features

### Case Discussion Rooms
- Real-time messaging with WebSocket
- File sharing (images, documents)
- Typing indicators
- Message status (sending, sent, delivered, read)
- Participant list with roles
- Mobile responsive design

### Teaching Rooms
- Video grid with dynamic layout (1-25 participants)
- Audio/video controls
- Screen sharing
- Hand raising feature
- Chat sidebar
- Participant management
- Connection quality indicators
- Full-screen mode

## Usage

```tsx
// In your route configuration
import RoomDetail from './pages/RoomDetailNew';

<Route path="/rooms/:roomId" element={<RoomDetail />} />
```

## Context Integration
The components use the `RoomContext` provider which manages:
- Room state and participants
- WebSocket connections
- Media streams (for video rooms)
- Message handling
- User permissions

## Responsive Design
- Desktop: Full layout with sidebars
- Tablet: Collapsible sidebars
- Mobile: Overlay panels with gestures

## WebSocket Events
- `chat_message` - New message received
- `user_typing` - User started typing
- `user_stopped_typing` - User stopped typing
- `user_joined` - New participant joined
- `user_left` - Participant left
- `media_state_change` - Video/audio state changed

## Styling
- Tailwind CSS for utility classes
- Framer Motion for animations
- Custom gradients and shadows for depth
- Dark theme for video rooms
- Light theme for chat rooms