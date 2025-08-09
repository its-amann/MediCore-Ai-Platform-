# Medical AI Backend Microservices Architecture

## Overview

The Medical AI Backend consists of four sophisticated microservices that work together to provide comprehensive AI-powered medical consultation, collaboration, and analysis capabilities. Each microservice is designed with scalability, reliability, and real-time performance in mind.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Medical AI Backend Platform                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────┐│
│  │  Cases & Chat    │  │  Collaboration   │  │ Medical Imaging  │  │  Voice  ││
│  │   Microservice   │  │   Microservice   │  │   Microservice   │  │Consult  ││
│  │                  │  │                  │  │                  │  │         ││
│  │ • AI Doctors     │  │ • Video/WebRTC   │  │ • Image Analysis │  │ • STT   ││
│  │ • Case Mgmt     │  │ • Screen Share   │  │ • LangGraph      │  │ • TTS   ││
│  │ • MCP Server    │  │ • Gemini Live    │  │ • Report Gen     │  │ • VAD   ││
│  │ • WebSocket     │  │ • Notifications  │  │ • Embeddings     │  │ • AI    ││
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────┬────┘│
│           │                      │                      │                 │     │
│           └──────────────────────┴──────────────────────┴─────────────────┘     │
│                                          │                                      │
│                              ┌───────────┴────────────┐                         │
│                              │   Shared Services      │                         │
│                              │                        │                         │
│                              │ • Neo4j Graph Database │                         │
│                              │ • AI Provider Manager  │                         │
│                              │ • WebSocket Manager    │                         │
│                              │ • Authentication       │                         │
│                              └────────────────────────┘                         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Microservices Overview

### 1. Cases & Chat Microservice (`cases_chat/`)

**Purpose:** AI-powered medical consultation service with specialized doctor agents and case management.

**Key Features:**
- Multiple AI doctor specialists (General Consultant, Cardiologist, BP Specialist)
- Real-time chat with WebSocket support
- Medical Context Protocol (MCP) integration
- Case numbering and management system
- Media handling (images/audio)

### 2. Collaboration Microservice (`collaboration/`)

**Purpose:** Real-time collaboration platform for medical professionals with video conferencing and AI assistance.

**Key Features:**
- WebRTC video conferencing
- Screen sharing with AI analysis
- Gemini Live API integration
- Real-time notifications
- Multi-user room management

### 3. Medical Imaging Microservice (`medical_imaging/`)

**Purpose:** Advanced medical image analysis using LangGraph workflows and multiple AI providers.

**Key Features:**
- LangGraph workflow orchestration
- Multi-provider AI architecture (Gemini, Groq, OpenRouter)
- Embedding-based similarity search
- Comprehensive report generation
- Quality validation system

### 4. Voice Consultation Microservice (`voice_consultation/`)

**Purpose:** Real-time voice-based medical consultations with speech processing and multi-modal capabilities.

**Key Features:**
- Whisper-powered speech recognition
- Voice Activity Detection (VAD)
- Text-to-Speech synthesis
- Multi-modal support (voice/video/screen)
- Real-time WebSocket streaming

## Detailed Architecture

### 1. Cases & Chat Microservice

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Cases & Chat Microservice                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Client Request                                                        │
│       ↓                                                                │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐              │
│  │  FastAPI │────→│  WebSocket  │────→│ Message      │              │
│  │  Routes  │     │  Manager    │     │ Processor    │              │
│  └──────────┘     └─────────────┘     └──────────────┘              │
│       ↓                ↓                      ↓                       │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐              │
│  │   Case   │     │   Doctor    │     │     MCP      │              │
│  │  Service │←───→│ Coordinator │←───→│   Client     │              │
│  └──────────┘     └─────────────┘     └──────────────┘              │
│       ↓                ↓                      ↓                       │
│  ┌──────────────────────────────────────────────────┐                │
│  │           Neo4j Graph Database                   │                │
│  │                                                  │                │
│  │  Nodes: User, Case, ChatSession, Message        │                │
│  │  Relationships: HAS_CASE, BELONGS_TO, SENT_BY   │                │
│  └──────────────────────────────────────────────────┘                │
│                                                                        │
│  AI Providers:                                                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                              │
│  │ Gemini  │  │  Groq   │  │  Local  │                              │
│  │ Vision  │  │  Fast   │  │ Models  │                              │
│  └─────────┘  └─────────┘  └─────────┘                              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Workflow:**
1. **Case Creation** → User initiates medical case with patient details
2. **Doctor Selection** → System selects appropriate AI specialist
3. **Context Enhancement** → MCP server provides historical context
4. **Chat Interaction** → Real-time WebSocket communication
5. **Response Generation** → AI processes and generates medical advice
6. **Case Update** → Store conversation in Neo4j graph

**MCP Server Integration:**
```
┌─────────────────────────────────────────────────────┐
│              MCP Server Architecture                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Main Application ←──HTTP──→ MCP Client             │
│                                   ↓                  │
│                          ┌────────────────┐         │
│                          │   MCP Server   │         │
│                          │                │         │
│                          │ • Case History │         │
│                          │ • Similar Cases│         │
│                          │ • Statistics   │         │
│                          └────────────────┘         │
│                                   ↓                  │
│                          Neo4j Database              │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 2. Collaboration Microservice

```
┌────────────────────────────────────────────────────────────────────────┐
│                    Collaboration Microservice                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  User Connection                                                       │
│       ↓                                                                │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐              │
│  │   Room   │────→│   WebRTC    │────→│   Gemini     │              │
│  │  Service │     │   Service   │     │  Live API    │              │
│  └──────────┘     └─────────────┘     └──────────────┘              │
│       ↓                ↓                      ↓                       │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐              │
│  │  Screen  │     │   Video     │     │     AI       │              │
│  │  Share   │←───→│   Service   │←───→│ Integration  │              │
│  └──────────┘     └─────────────┘     └──────────────┘              │
│       ↓                ↓                      ↓                       │
│  ┌──────────────────────────────────────────────────┐                │
│  │         Service Container & Integration          │                │
│  │                                                  │                │
│  │  • Dependency Injection                          │                │
│  │  • Service Lifecycle Management                  │                │
│  │  • Cross-Service Communication                   │                │
│  └──────────────────────────────────────────────────┘                │
│                           ↓                                           │
│                    Neo4j Database                                     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Workflow:**
1. **Room Creation** → Medical team creates collaboration room
2. **Participant Join** → Doctors join via WebRTC
3. **Video Stream** → Establish peer-to-peer connections
4. **Screen Sharing** → Share medical images/diagnostics
5. **AI Analysis** → Gemini Live provides real-time insights
6. **Decision Recording** → Store outcomes in database

**Gemini Live Integration:**
```
┌─────────────────────────────────────────────────────┐
│           Gemini Live API Integration               │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Modes:                                              │
│  • Voice Conversation Mode                          │
│  • Screen Understanding Mode                         │
│  • Medical Analysis Mode                            │
│  • Teaching Assistant Mode                          │
│  • Case Discussion Mode                             │
│                                                      │
│  Features:                                          │
│  • Real-time audio/video processing                 │
│  • Multi-modal understanding                        │
│  • Context-aware responses                          │
│  • Medical knowledge integration                    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 3. Medical Imaging Microservice

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Medical Imaging Microservice                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Image Input                                                           │
│       ↓                                                                │
│  ┌────────────────────────────────────────────┐                      │
│  │         LangGraph Workflow Engine          │                      │
│  │                                             │                      │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐ │                      │
│  │  │Image │→│Analyze│→│Report│→│Quality│ │                      │
│  │  │Input │  │ Node │  │ Node │  │Check │ │                      │
│  │  └──────┘  └──────┘  └──────┘  └──────┘ │                      │
│  │                ↓          ↓         ↓      │                      │
│  └────────────────────────────────────────────┘                      │
│                                                                        │
│  ┌────────────────────────────────────────────┐                      │
│  │         AI Provider Manager                │                      │
│  │                                             │                      │
│  │  ┌─────────┐  ┌─────────┐  ┌────────────┐│                      │
│  │  │ Gemini  │  │  Groq   │  │ OpenRouter ││                      │
│  │  │Provider │  │Provider │  │  Provider  ││                      │
│  │  └─────────┘  └─────────┘  └────────────┘│                      │
│  │                                             │                      │
│  │  • Health Monitoring                        │                      │
│  │  • Automatic Fallback                       │                      │
│  │  • Rate Limit Management                    │                      │
│  └────────────────────────────────────────────┘                      │
│                       ↓                                               │
│  ┌────────────────────────────────────────────┐                      │
│  │      Database Services                     │                      │
│  │                                             │                      │
│  │  • Neo4j Report Storage                    │                      │
│  │  • Embedding Vector Storage                │                      │
│  │  • Similarity Matching                     │                      │
│  └────────────────────────────────────────────┘                      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**LangGraph Workflow:**
```
Start → Image Analysis → Literature Search → Report Generation → Quality Check → End
         ↓                ↓                   ↓                   ↓
    [Provider 1]     [Provider 2]        [Provider 3]      [Validation]
         ↓                ↓                   ↓                   ↓
    [Fallback]       [Fallback]          [Fallback]        [Retry/Fix]
```

**Workflow Steps:**
1. **Image Ingestion** → Receive medical images with metadata
2. **Provider Selection** → Choose optimal AI provider
3. **Parallel Analysis** → Process through multiple models
4. **Literature Search** → Find relevant medical research
5. **Report Synthesis** → Generate comprehensive report
6. **Quality Validation** → AI-powered quality assurance
7. **Embedding Storage** → Store for similarity matching
8. **Result Delivery** → Return analysis with confidence scores

### 4. Voice Consultation Microservice

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Voice Consultation Microservice                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Audio Stream                                                          │
│       ↓                                                                │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐              │
│  │WebSocket │────→│    Audio    │────→│   Whisper    │              │
│  │ Handler  │     │  Processing │     │     STT      │              │
│  └──────────┘     └─────────────┘     └──────────────┘              │
│       ↓                ↓                      ↓                       │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐              │
│  │   VAD    │     │   Voice     │     │     AI       │              │
│  │Detection │←───→│    Agent    │←───→│   Provider   │              │
│  └──────────┘     └─────────────┘     └──────────────┘              │
│       ↓                ↓                      ↓                       │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐              │
│  │   TTS    │←────│  Response   │←────│   Medical    │              │
│  │  Engine  │     │  Generator  │     │   Context    │              │
│  └──────────┘     └─────────────┘     └──────────────┘              │
│                                                                        │
│  Multi-Modal Support:                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                              │
│  │  Audio  │  │  Video  │  │ Screen  │                              │
│  │  Mode   │  │  Mode   │  │  Share  │                              │
│  └─────────┘  └─────────┘  └─────────┘                              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Voice Processing Pipeline:**
```
Audio Input → VAD Detection → Speech Recognition → AI Processing → Response Generation → TTS → Audio Output
     ↓              ↓                ↓                   ↓              ↓             ↓          ↓
[WebSocket]    [RMS Energy]    [Whisper API]      [Llama/Groq]    [Medical AI]    [gTTS]   [Stream]
```

**Workflow:**
1. **Connection Init** → Establish WebSocket with client
2. **Audio Streaming** → Receive real-time audio chunks
3. **VAD Processing** → Detect speech vs. silence
4. **Transcription** → Convert speech to text (Whisper)
5. **AI Analysis** → Process medical consultation
6. **Response Gen** → Generate appropriate response
7. **Speech Synthesis** → Convert response to audio
8. **Multi-Modal** → Support video/screen sharing
9. **Context Save** → Store consultation history

## Database Architecture

### Neo4j Graph Database Schema

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Neo4j Graph Database Schema                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Nodes:                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   User   │  │   Case   │  │ Session  │  │ Message  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│       │             │             │             │                     │
│       └─HAS_CASE───→│←─BELONGS_TO─┘             │                     │
│                     └────────CONTAINS───────────→│                     │
│                                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Doctor  │  │  Report  │  │Embedding │  │  Room    │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│       │             │             │             │                     │
│       └─CONSULTED──→│←─HAS_VECTOR─┘             │                     │
│                     └────────IN_ROOM────────────→│                     │
│                                                                        │
│  Properties:                                                          │
│  • User: {id, name, email, role, created_at}                        │
│  • Case: {id, case_number, patient_info, status}                    │
│  • Session: {id, type, started_at, ended_at}                        │
│  • Message: {id, content, timestamp, speaker}                       │
│  • Report: {id, findings, recommendations}                          │
│  • Embedding: {id, vector, model, dimensions}                       │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## AI Provider Architecture

### Unified AI Provider Management

```
┌────────────────────────────────────────────────────────────────────────┐
│                    AI Provider Management System                       │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌────────────────────────────────────────────┐                      │
│  │         Provider Health Monitor            │                      │
│  │                                             │                      │
│  │  • Real-time availability checking         │                      │
│  │  • Response time monitoring                │                      │
│  │  • Error rate tracking                     │                      │
│  │  • Automatic failover triggers             │                      │
│  └────────────────────────────────────────────┘                      │
│                       ↓                                               │
│  ┌────────────────────────────────────────────┐                      │
│  │         Provider Manager                   │                      │
│  │                                             │                      │
│  │  ┌─────────┐  ┌─────────┐  ┌────────────┐│                      │
│  │  │ Primary │  │Secondary│  │  Fallback  ││                      │
│  │  │Provider │→│Provider │→│  Provider   ││                      │
│  │  └─────────┘  └─────────┘  └────────────┘│                      │
│  │                                             │                      │
│  │  • Load balancing                          │                      │
│  │  • Rate limit management                   │                      │
│  │  • Circuit breaker pattern                 │                      │
│  └────────────────────────────────────────────┘                      │
│                                                                        │
│  Supported Providers:                                                 │
│  • Gemini (Vision, Pro, Flash)                                       │
│  • Groq (Llama, Mixtral, Whisper)                                   │
│  • OpenRouter (Medical models)                                       │
│  • Local models (Ollama)                                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Integration Patterns

### Cross-Service Communication

```
┌────────────────────────────────────────────────────────────────────────┐
│                  Cross-Service Communication Pattern                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Service A                    Service B                               │
│  ┌──────────┐                ┌──────────┐                           │
│  │  HTTP    │──────REST─────→│  HTTP    │                           │
│  │  Client  │                │  Server  │                           │
│  └──────────┘                └──────────┘                           │
│       ↓                            ↓                                  │
│  ┌──────────┐                ┌──────────┐                           │
│  │WebSocket │←───Events──────│WebSocket │                           │
│  │  Client  │                │  Server  │                           │
│  └──────────┘                └──────────┘                           │
│       ↓                            ↓                                  │
│  ┌────────────────────────────────────┐                             │
│  │      Shared Neo4j Database         │                             │
│  └────────────────────────────────────┘                             │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Event-Driven Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                    Event-Driven Architecture                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Event Sources:                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  User    │  │   AI     │  │  System  │  │ External │           │
│  │  Actions │  │Responses │  │  Events  │  │   APIs   │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │              │                  │
│       └──────────────┴──────────────┴──────────────┘                  │
│                             ↓                                         │
│                   ┌──────────────────┐                               │
│                   │  Event Bus       │                               │
│                   │  (WebSocket)     │                               │
│                   └──────────────────┘                               │
│                             ↓                                         │
│       ┌──────────────┬──────────────┬──────────────┐                 │
│       ↓              ↓              ↓              ↓                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Cases   │  │  Collab  │  │ Imaging  │  │  Voice   │           │
│  │  Service │  │  Service │  │  Service │  │  Service │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Container Orchestration

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Kubernetes Deployment                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                    Ingress Controller                        │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                             ↓                                         │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                      Load Balancer                           │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                             ↓                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Cases   │  │  Collab  │  │ Imaging  │  │  Voice   │           │
│  │   Pod    │  │   Pod    │  │   Pod    │  │   Pod    │           │
│  │ (3 rep)  │  │ (2 rep)  │  │ (2 rep)  │  │ (3 rep)  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                             ↓                                         │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │              Persistent Volume Claims                        │     │
│  │                                                              │     │
│  │  • Neo4j Data                                               │     │
│  │  • Media Storage                                            │     │
│  │  • Model Cache                                              │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Environment Configuration

### Required Environment Variables

```bash
# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# AI Providers
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key

# WebSocket
WS_PORT=8000
WS_HOST=0.0.0.0

# MCP Server
MCP_SERVER_URL=http://localhost:3000
MCP_API_KEY=your_mcp_key

# Voice Services
WHISPER_MODEL=large-v3
TTS_ENGINE=gtts
VAD_THRESHOLD=0.02

# Collaboration
WEBRTC_STUN_SERVER=stun:stun.l.google.com:19302
GEMINI_LIVE_ENDPOINT=wss://gemini.live/api/v1
```

## API Documentation

### REST Endpoints

| Service | Endpoint | Method | Description |
|---------|----------|--------|-------------|
| Cases & Chat | `/api/v1/cases` | GET, POST, PUT, DELETE | Case management |
| Cases & Chat | `/api/v1/chat` | POST | Send chat message |
| Cases & Chat | `/api/v1/media` | POST | Upload media |
| Cases & Chat | `/api/v1/ws` | WS | WebSocket connection |
| Collaboration | `/rooms` | GET, POST | Room management |
| Collaboration | `/screen-share` | POST | Start screen sharing |
| Medical Imaging | `/analyze` | POST | Analyze medical image |
| Voice Consultation | `/consultation` | POST | Start consultation |

### WebSocket Events

| Service | Event | Direction | Description |
|---------|-------|-----------|-------------|
| Cases & Chat | `user_message` | Client→Server | User sends message |
| Cases & Chat | `doctor_response` | Server→Client | AI doctor responds |
| Collaboration | `video_offer` | Client→Server | WebRTC offer |
| Collaboration | `ice_candidate` | Both | ICE candidate exchange |
| Voice | `audio_data` | Client→Server | Audio stream |
| Voice | `transcription` | Server→Client | Speech to text result |

## Performance Metrics

### Service SLAs

| Service | Latency (p99) | Availability | Throughput |
|---------|---------------|--------------|------------|
| Cases & Chat | < 200ms | 99.9% | 1000 req/s |
| Collaboration | < 100ms | 99.95% | 500 connections |
| Medical Imaging | < 5s | 99.5% | 100 images/min |
| Voice Consultation | < 50ms | 99.9% | 200 streams |

### Resource Requirements

| Service | CPU | Memory | Storage |
|---------|-----|--------|---------|
| Cases & Chat | 2 cores | 4GB | 10GB |
| Collaboration | 4 cores | 8GB | 20GB |
| Medical Imaging | 8 cores | 16GB | 50GB |
| Voice Consultation | 4 cores | 8GB | 20GB |
| Neo4j Database | 8 cores | 32GB | 100GB |

## Security Considerations

### Authentication & Authorization
- JWT-based authentication across all services
- Role-based access control (RBAC)
- Service-to-service authentication using API keys
- WebSocket connection authentication

### Data Protection
- End-to-end encryption for sensitive medical data
- HIPAA compliance for medical information
- PII data anonymization
- Audit logging for all data access

### Network Security
- TLS 1.3 for all communications
- API rate limiting and DDoS protection
- WebSocket connection validation
- CORS configuration for cross-origin requests

## Monitoring & Observability

### Logging
- Structured logging with correlation IDs
- Centralized log aggregation (ELK stack)
- Error tracking and alerting
- Performance metrics logging

### Metrics
- Prometheus metrics collection
- Grafana dashboards for visualization
- Custom business metrics
- AI provider performance tracking

### Health Checks
- Liveness probes for container health
- Readiness probes for service availability
- Database connection monitoring
- External API health monitoring

## Development Setup

### Prerequisites
```bash
# Python 3.11+
python --version

# Node.js 18+ (for MCP server)
node --version

# Neo4j 5.0+
neo4j --version

# FFmpeg (for audio processing)
ffmpeg -version
```

### Installation
```bash
# Clone repository
git clone https://github.com/your-org/unified-medical-ai.git
cd unified-medical-ai/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup Neo4j database
cd app/microservices/cases_chat/migrations
python run_migrations.py

# Start services
python -m app.microservices.cases_chat.main
python -m app.microservices.collaboration.integration
python -m app.microservices.medical_imaging.workflows.workflow_manager
python -m app.microservices.voice_consultation.routes.websocket_handler
```

## Testing

### Unit Tests
```bash
# Run all tests
pytest tests/

# Run specific service tests
pytest tests/cases_chat/
pytest tests/collaboration/
pytest tests/medical_imaging/
pytest tests/voice_consultation/
```

### Integration Tests
```bash
# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=app tests/
```

### Load Testing
```bash
# Using locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## Contributing

Please refer to the individual microservice README files for specific contribution guidelines:
- [Cases & Chat README](cases_chat/README.md)
- [Collaboration README](collaboration/README.md)
- [Medical Imaging Workflow](medical_imaging/workflows/README.md)
- [Voice Consultation Guide](voice_consultation/docs/VOICE_CONSULTATION_COMPLETE_GUIDE.md)

## License

This project is proprietary and confidential. All rights reserved.

## Support

For technical support or questions, please contact the development team or create an issue in the project repository.

---

*Last Updated: January 2025*