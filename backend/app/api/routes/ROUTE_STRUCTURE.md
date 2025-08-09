# Unified Medical AI Platform - Route Structure

## Overview

The API routes have been reorganized into a clean, microservice-based structure. Each microservice has its own directory containing all related routes, and common functionality is shared through the `common` directory.

## Directory Structure

```
app/api/routes/
├── __init__.py                 # Main router exports
├── auth/                       # Authentication microservice
│   ├── __init__.py
│   └── auth.py                # Authentication endpoints
├── cases/                      # Cases management microservice
│   ├── __init__.py
│   ├── cases.py               # Case management endpoints
│   └── chat.py                # Chat functionality for cases
├── medical_imaging/            # Medical imaging microservice
│   ├── __init__.py
│   ├── medical_imaging.py     # Image analysis endpoints
│   └── debug.py               # Debug endpoints for medical imaging
├── collaboration/              # Collaboration microservice
│   ├── __init__.py
│   ├── rooms.py               # Room management
│   └── media.py               # Media upload/download
├── voice/                      # Voice consultation microservice
│   ├── __init__.py
│   └── voice.py               # Voice consultation endpoints
└── common/                     # Shared/common routes
    ├── __init__.py
    ├── websocket.py           # Unified WebSocket handler
    ├── health.py              # Health check endpoints
    ├── doctors.py             # AI doctor management
    ├── medical_context.py     # Medical context handling
    └── logs.py                # Logging endpoints
```

## WebSocket Consolidation

All WebSocket functionality has been consolidated into a single unified WebSocket endpoint:

### Unified WebSocket Endpoint
- **Path**: `/api/v1/ws/unified`
- **Purpose**: Single WebSocket endpoint that handles all microservice WebSocket needs
- **Features**:
  - Automatic message routing based on message type
  - Service hint support for optimized initialization
  - Backward compatibility with existing client code
  - Unified authentication and error handling

### Service-Specific Message Types

#### Cases Chat
- `chat_message`, `load_chat_history`, `create_chat_session`
- `join_case_room`, `leave_case_room`, `get_available_cases`

#### Medical Imaging
- `start_analysis`, `get_workflow_status`, `cancel_workflow`
- `get_analysis_history`, `medical_imaging_request`

#### Voice Consultation
- `start_voice_session`, `end_voice_session`, `voice_data`
- `transcription_request`, `voice_command`

#### Collaboration
- `join_room`, `leave_room`, `collaboration_message`
- `screen_share`, `video_call`

## Route Registration in main.py

Routes are now registered in a clean, organized manner:

```python
# Common routes
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(doctors_router, prefix="/api/v1/doctors", tags=["AI Doctors"])
app.include_router(medical_context_router, prefix="/api/v1/medical-context", tags=["Medical Context"])
app.include_router(logs_router, prefix="/api/v1/logs", tags=["Logs"])

# Authentication
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

# Microservices
app.include_router(cases_router, prefix="/api/v1", tags=["Cases"])
app.include_router(medical_imaging_router, prefix="/api/v1/medical-imaging", tags=["Medical Imaging"])
app.include_router(voice_router, prefix="/api/v1/voice", tags=["Voice"])
app.include_router(collaboration_router, prefix="/api/v1/collaboration", tags=["Collaboration"])

# Unified WebSocket
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])
```

## Benefits of New Structure

1. **Clear Organization**: Each microservice has its own directory with related routes
2. **Single WebSocket Entry Point**: Eliminates redundancy and simplifies client integration
3. **Easy Maintenance**: Related functionality is grouped together
4. **Scalability**: New microservices can be added easily following the same pattern
5. **Reduced Duplication**: Common functionality is shared through the common directory

## Migration Guide

### For WebSocket Clients

Old endpoints → New unified endpoint:
- `/api/v1/ws` → `/api/v1/ws/unified`
- `/api/medical-imaging/ws/{client_id}` → `/api/v1/ws/unified?service=medical_imaging`
- `/api/v1/cases/ws` → `/api/v1/ws/unified?service=cases`

### For HTTP Endpoints

Most HTTP endpoints remain the same, with minor prefix adjustments:
- Medical imaging routes now under `/api/v1/medical-imaging/`
- Voice routes now under `/api/v1/voice/`
- Collaboration routes now under `/api/v1/collaboration/`

## Best Practices

1. **New Routes**: Add to the appropriate microservice directory
2. **Shared Functionality**: Place in the common directory
3. **WebSocket Features**: Extend the unified WebSocket handler
4. **Documentation**: Update this file when adding new microservices