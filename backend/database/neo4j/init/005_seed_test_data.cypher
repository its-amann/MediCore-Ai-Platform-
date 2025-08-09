// 005_seed_test_data.cypher
// Unified Medical AI Platform - Seed Test Data
// This script creates sample data for testing and development
// Run this script after doctors are created

// Create Test Users
CREATE (:User {
  user_id: 'user_patient_001',
  username: 'john_doe',
  email: 'john.doe@example.com',
  password_hash: '$2b$10$YourHashedPasswordHere',
  first_name: 'John',
  last_name: 'Doe',
  role: 'patient',
  created_at: datetime() - duration('P30D'),
  last_login: datetime() - duration('P1D'),
  is_active: true,
  preferences: {
    theme: 'light',
    notifications: true,
    language: 'en'
  },
  profile_image: '/assets/avatars/default-patient.png',
  timezone: 'America/New_York',
  language: 'en'
});

CREATE (:User {
  user_id: 'user_doctor_001',
  username: 'dr_smith',
  email: 'dr.smith@hospital.com',
  password_hash: '$2b$10$YourHashedPasswordHere',
  first_name: 'Sarah',
  last_name: 'Smith',
  role: 'doctor',
  specialization: 'cardiology',
  license_number: 'MD123456',
  created_at: datetime() - duration('P90D'),
  last_login: datetime() - duration('PT2H'),
  is_active: true,
  preferences: {
    theme: 'dark',
    notifications: true,
    language: 'en'
  },
  profile_image: '/assets/avatars/doctor-smith.png',
  timezone: 'America/Los_Angeles',
  language: 'en'
});

CREATE (:User {
  user_id: 'user_admin_001',
  username: 'admin',
  email: 'admin@medicalai.com',
  password_hash: '$2b$10$YourHashedPasswordHere',
  first_name: 'Admin',
  last_name: 'User',
  role: 'admin',
  created_at: datetime() - duration('P180D'),
  last_login: datetime(),
  is_active: true,
  preferences: {
    theme: 'auto',
    notifications: true,
    language: 'en'
  },
  profile_image: '/assets/avatars/admin.png',
  timezone: 'UTC',
  language: 'en'
});

// Create Test Cases
CREATE (:Case {
  case_id: 'case_001',
  title: 'Chest Pain Evaluation',
  description: 'Patient presenting with acute chest pain, needs cardiac evaluation',
  chief_complaint: 'Sharp chest pain for 2 hours',
  status: 'active',
  priority: 'high',
  urgency_level: 8,
  medical_category: 'cardiology',
  patient_age: 55,
  patient_gender: 'male',
  symptoms: ['chest pain', 'shortness of breath', 'sweating'],
  diagnosis: null,
  treatment_plan: null,
  outcome: null,
  created_at: datetime() - duration('PT6H'),
  updated_at: datetime() - duration('PT1H'),
  closed_at: null,
  tags: ['cardiac', 'urgent', 'chest-pain'],
  is_public: false,
  metadata: {
    vital_signs: {
      bp: '145/90',
      hr: '95',
      temp: '98.6',
      spo2: '96%'
    }
  },
  embedding: null
});

CREATE (:Case {
  case_id: 'case_002',
  title: 'Pre-operative BP Assessment',
  description: 'Pre-surgical blood pressure evaluation for elective knee replacement',
  chief_complaint: 'Pre-operative assessment required',
  status: 'active',
  priority: 'medium',
  urgency_level: 5,
  medical_category: 'pre-operative',
  patient_age: 68,
  patient_gender: 'female',
  symptoms: ['hypertension', 'knee pain'],
  diagnosis: 'Essential hypertension, osteoarthritis',
  treatment_plan: 'Optimize BP control before surgery',
  outcome: null,
  created_at: datetime() - duration('P2D'),
  updated_at: datetime() - duration('PT4H'),
  closed_at: null,
  tags: ['pre-op', 'hypertension', 'elective-surgery'],
  is_public: true,
  metadata: {
    surgery_date: datetime() + duration('P14D'),
    surgery_type: 'Total knee replacement',
    asa_score: 2
  },
  embedding: null
});

CREATE (:Case {
  case_id: 'case_003',
  title: 'Annual Health Check-up',
  description: 'Routine annual health examination with general health concerns',
  chief_complaint: 'Annual check-up, feeling tired lately',
  status: 'closed',
  priority: 'low',
  urgency_level: 2,
  medical_category: 'general',
  patient_age: 42,
  patient_gender: 'female',
  symptoms: ['fatigue', 'mild headaches'],
  diagnosis: 'Iron deficiency anemia',
  treatment_plan: 'Iron supplementation, follow-up in 3 months',
  outcome: 'Resolved with treatment',
  created_at: datetime() - duration('P7D'),
  updated_at: datetime() - duration('P3D'),
  closed_at: datetime() - duration('P3D'),
  tags: ['routine', 'check-up', 'preventive'],
  is_public: true,
  metadata: {
    lab_results: {
      hemoglobin: '10.2',
      ferritin: '8'
    }
  },
  embedding: null
});

// Create relationships between users and cases
MATCH (u:User {username: 'john_doe'}), (c:Case {case_id: 'case_001'})
CREATE (u)-[:OWNS {
  created_at: datetime() - duration('PT6H'),
  role: 'primary',
  permissions: ['read', 'write', 'delete', 'share']
}]->(c);

MATCH (u:User {username: 'dr_smith'}), (c:Case {case_id: 'case_002'})
CREATE (u)-[:OWNS {
  created_at: datetime() - duration('P2D'),
  role: 'primary',
  permissions: ['read', 'write', 'delete', 'share']
}]->(c);

MATCH (u:User {username: 'john_doe'}), (c:Case {case_id: 'case_003'})
CREATE (u)-[:OWNS {
  created_at: datetime() - duration('P7D'),
  role: 'primary',
  permissions: ['read', 'write', 'delete', 'share']
}]->(c);

// Create Test Media
CREATE (:Media {
  media_id: 'media_001',
  filename: 'chest_xray_001.jpg',
  file_path: '/storage/media/2024/01/chest_xray_001.jpg',
  file_size: 2048576,
  mime_type: 'image/jpeg',
  media_type: 'image',
  format: 'JPEG',
  dimensions: {
    width: 2048,
    height: 2048
  },
  duration: null,
  quality: 'high',
  is_processed: true,
  processing_status: 'completed',
  thumbnail_path: '/storage/thumbnails/2024/01/chest_xray_001_thumb.jpg',
  metadata: {
    modality: 'X-Ray',
    body_part: 'Chest',
    view: 'PA'
  },
  hash: 'sha256:abcdef123456',
  uploaded_at: datetime() - duration('PT5H'),
  processed_at: datetime() - duration('PT4H30M'),
  is_archived: false,
  archive_location: null,
  privacy_level: 'private',
  retention_policy: 'standard'
});

CREATE (:Media {
  media_id: 'media_002',
  filename: 'ecg_recording_001.pdf',
  file_path: '/storage/media/2024/01/ecg_recording_001.pdf',
  file_size: 512000,
  mime_type: 'application/pdf',
  media_type: 'document',
  format: 'PDF',
  dimensions: null,
  duration: null,
  quality: 'high',
  is_processed: true,
  processing_status: 'completed',
  thumbnail_path: null,
  metadata: {
    test_type: 'ECG',
    leads: 12,
    duration_seconds: 10
  },
  hash: 'sha256:123456abcdef',
  uploaded_at: datetime() - duration('PT3H'),
  processed_at: datetime() - duration('PT2H45M'),
  is_archived: false,
  archive_location: null,
  privacy_level: 'private',
  retention_policy: 'standard'
});

// Create relationships between cases and media
MATCH (c:Case {case_id: 'case_001'}), (m:Media {media_id: 'media_001'})
CREATE (c)-[:CONTAINS_MEDIA {
  attached_at: datetime() - duration('PT5H'),
  media_role: 'primary',
  is_evidence: true,
  order: 1
}]->(m);

MATCH (c:Case {case_id: 'case_001'}), (m:Media {media_id: 'media_002'})
CREATE (c)-[:CONTAINS_MEDIA {
  attached_at: datetime() - duration('PT3H'),
  media_role: 'supporting',
  is_evidence: true,
  order: 2
}]->(m);

// Create Test Analysis
CREATE (:Analysis {
  analysis_id: 'analysis_001',
  type: 'image',
  status: 'completed',
  input_data: {
    media_id: 'media_001',
    analysis_params: {
      contrast_enhancement: true,
      edge_detection: true
    }
  },
  analysis_result: 'Chest X-ray analysis shows mild cardiomegaly with no acute pulmonary findings. Heart size is at upper limits of normal. Lungs are clear without consolidation or effusion.',
  findings: [
    'Mild cardiomegaly',
    'Clear lung fields',
    'No acute pathology'
  ],
  recommendations: [
    'Echocardiogram recommended for further cardiac evaluation',
    'Follow-up chest X-ray in 6 months',
    'Continue current cardiac medications'
  ],
  confidence_score: 0.92,
  processing_time: 3.45,
  model_used: 'chest-xray-analyzer-v2',
  model_version: '2.0.1',
  parameters: {
    sensitivity: 'high',
    specificity: 'balanced'
  },
  medical_codes: ['I51.7', 'Z86.74'],
  severity_score: 3,
  urgency_indicators: [],
  created_at: datetime() - duration('PT4H'),
  completed_at: datetime() - duration('PT3H55M'),
  reviewed_at: null,
  is_reviewed: false,
  review_notes: null,
  metadata: {},
  embedding: null
});

// Create relationships between case, analysis, and doctor
MATCH (c:Case {case_id: 'case_001'}), (a:Analysis {analysis_id: 'analysis_001'})
CREATE (c)-[:HAS_ANALYSIS {
  created_at: datetime() - duration('PT4H'),
  order: 1,
  is_primary: true,
  analysis_type: 'image'
}]->(a);

MATCH (a:Analysis {analysis_id: 'analysis_001'}), (d:Doctor {doctor_id: 'doc_radiology_001'})
CREATE (a)-[:ANALYZED_BY {
  started_at: datetime() - duration('PT4H'),
  completed_at: datetime() - duration('PT3H55M'),
  confidence_level: 0.92,
  review_status: 'pending',
  review_notes: null,
  chat_context_included: false
}]->(d);

MATCH (a:Analysis {analysis_id: 'analysis_001'}), (m:Media {media_id: 'media_001'})
CREATE (a)-[:USES {
  usage_type: 'input',
  processing_order: 1,
  extraction_method: 'direct'
}]->(m);

// Create Test Collaboration Room
CREATE (:Room {
  room_id: 'room_001',
  name: 'Cardiology Case Discussion',
  description: 'Discussion room for complex cardiology cases',
  type: 'case_discussion',
  status: 'active',
  max_participants: 10,
  current_participants: 2,
  is_public: false,
  requires_approval: true,
  password_protected: false,
  room_password: null,
  voice_enabled: true,
  screen_sharing: true,
  recording_enabled: false,
  created_at: datetime() - duration('P1D'),
  last_activity: datetime() - duration('PT30M'),
  closed_at: null,
  settings: {
    auto_archive_days: 30,
    notification_settings: {
      new_message: true,
      user_joined: true
    }
  },
  moderator_permissions: ['kick_user', 'mute_user', 'delete_message', 'pin_message'],
  participant_permissions: ['send_message', 'share_screen', 'voice_chat'],
  tags: ['cardiology', 'case-review', 'consultation']
});

// Create room relationships
MATCH (r:Room {room_id: 'room_001'}), (c:Case {case_id: 'case_001'})
CREATE (r)-[:DISCUSSES {
  started_at: datetime() - duration('P1D'),
  focus_area: 'diagnosis',
  discussion_status: 'active',
  moderator_notes: 'Discussing chest pain evaluation and cardiac workup'
}]->(c);

MATCH (u:User {username: 'dr_smith'}), (r:Room {room_id: 'room_001'})
CREATE (u)-[:PARTICIPATES_IN {
  joined_at: datetime() - duration('P1D'),
  role: 'moderator',
  last_seen: datetime() - duration('PT30M'),
  is_muted: false,
  permissions: ['all'],
  joined_via_invitation: false
}]->(r);

MATCH (u:User {username: 'john_doe'}), (r:Room {room_id: 'room_001'})
CREATE (u)-[:PARTICIPATES_IN {
  joined_at: datetime() - duration('PT2H'),
  role: 'participant',
  last_seen: datetime() - duration('PT45M'),
  is_muted: false,
  permissions: ['send_message', 'view_content'],
  joined_via_invitation: true
}]->(r);

// Create Test Chat History
CREATE (:ChatHistory {
  chat_id: 'chat_001',
  conversation_id: 'conv_case_001',
  message_content: 'I have been experiencing sharp chest pain for the last 2 hours. It gets worse when I breathe deeply.',
  message_type: 'user_message',
  sender_type: 'user',
  timestamp: datetime() - duration('PT5H'),
  doctor_specialty: null,
  response_time: null,
  confidence_score: null,
  session_id: 'session_001',
  case_context: 'case_001',
  user_sentiment: 'urgent',
  language: 'en',
  attachments: [],
  is_voice_message: false,
  voice_duration: null,
  metadata: {
    device: 'mobile',
    app_version: '1.2.0'
  }
});

CREATE (:ChatHistory {
  chat_id: 'chat_002',
  conversation_id: 'conv_case_001',
  message_content: 'I understand you are experiencing chest pain. Based on your description, this could be a cardiac issue that requires immediate attention. Let me analyze your symptoms and the chest X-ray you provided.',
  message_type: 'doctor_response',
  sender_type: 'doctor_ai',
  timestamp: datetime() - duration('PT4H58M'),
  doctor_specialty: 'cardiologist',
  response_time: 2.3,
  confidence_score: 0.88,
  session_id: 'session_001',
  case_context: 'case_001',
  user_sentiment: null,
  language: 'en',
  attachments: [],
  is_voice_message: false,
  voice_duration: null,
  metadata: {
    analysis_included: true,
    recommendations_count: 3
  }
});

// Create chat relationships
MATCH (u:User {username: 'john_doe'}), (ch:ChatHistory {chat_id: 'chat_001'})
CREATE (u)-[:HAS_CHAT_HISTORY {
  started_at: datetime() - duration('PT5H'),
  conversation_type: 'case_consultation',
  doctor_involved: 'cardiologist',
  total_messages: 1
}]->(ch);

MATCH (c:Case {case_id: 'case_001'}), (ch:ChatHistory {conversation_id: 'conv_case_001'})
CREATE (c)-[:HAS_CHAT_HISTORY {
  chat_started_at: datetime() - duration('PT5H'),
  conversation_context: 'Initial symptom reporting',
  doctor_consultations: ['cardiologist'],
  total_interactions: 2,
  last_interaction: datetime() - duration('PT4H58M')
}]->(ch);

MATCH (d:Doctor {doctor_id: 'doc_cardiologist_001'}), (ch:ChatHistory {chat_id: 'chat_002'})
CREATE (d)-[:PARTICIPATED_IN_CHAT {
  participation_start: datetime() - duration('PT4H58M'),
  participation_end: datetime() - duration('PT4H58M'),
  messages_sent: 1,
  consultation_type: 'diagnosis',
  user_satisfaction: null,
  response_quality: 0.88
}]->(ch);

// Create Test Messages in Room
CREATE (:Message {
  message_id: 'msg_001',
  content: 'Patient has presented with chest pain. X-ray shows mild cardiomegaly. Requesting cardiology input.',
  message_type: 'text',
  sender_type: 'user',
  timestamp: datetime() - duration('PT1H'),
  is_deleted: false,
  metadata: {
    mentions: ['@cardiology_team']
  },
  attachments: ['analysis_001'],
  reply_to: null
});

CREATE (:Message {
  message_id: 'msg_002',
  content: 'Reviewing the case now. The cardiomegaly appears mild. Recommend echo for further evaluation.',
  message_type: 'text',
  sender_type: 'user',
  timestamp: datetime() - duration('PT45M'),
  is_deleted: false,
  metadata: {},
  attachments: [],
  reply_to: 'msg_001'
});

// Create message relationships
MATCH (u:User {username: 'dr_smith'}), (m:Message {message_id: 'msg_001'})
CREATE (u)-[:SENT {
  sent_at: datetime() - duration('PT1H'),
  device_info: 'Web Browser',
  ip_address: '192.168.1.100'
}]->(m);

MATCH (r:Room {room_id: 'room_001'}), (m:Message {message_id: 'msg_001'})
CREATE (r)-[:HAS_MESSAGE {
  message_order: 1,
  is_announcement: false,
  visibility: 'all'
}]->(m);

MATCH (r:Room {room_id: 'room_001'}), (m:Message {message_id: 'msg_002'})
CREATE (r)-[:HAS_MESSAGE {
  message_order: 2,
  is_announcement: false,
  visibility: 'all'
}]->(m);

// Create Test Invitation
CREATE (:Invitation {
  invitation_id: 'inv_001',
  room_id: 'room_001',
  inviter_id: 'user_doctor_001',
  invitee_id: 'user_patient_001',
  invitee_username: 'john_doe',
  status: 'accepted',
  invitation_type: 'case_consultation',
  invited_at: datetime() - duration('PT3H'),
  responded_at: datetime() - duration('PT2H'),
  expires_at: datetime() + duration('P1D'),
  message: 'Please join the discussion about your case',
  permissions: ['view_content', 'send_message'],
  metadata: {
    case_reference: 'case_001'
  },
  room_name: 'Cardiology Case Discussion',
  case_title: 'Chest Pain Evaluation',
  urgency_level: 'high'
});

// Create invitation relationships
MATCH (u:User {username: 'dr_smith'}), (inv:Invitation {invitation_id: 'inv_001'})
CREATE (u)-[:SENT_INVITATION {
  sent_at: datetime() - duration('PT3H'),
  invitation_type: 'case_consultation',
  target_room: 'room_001'
}]->(inv);

MATCH (u:User {username: 'john_doe'}), (inv:Invitation {invitation_id: 'inv_001'})
CREATE (u)-[:RECEIVED_INVITATION {
  received_at: datetime() - duration('PT3H'),
  notification_sent: true,
  viewed_at: datetime() - duration('PT2H30M')
}]->(inv);

MATCH (r:Room {room_id: 'room_001'}), (inv:Invitation {invitation_id: 'inv_001'})
CREATE (r)-[:HAS_INVITATION {
  invitation_sent_at: datetime() - duration('PT3H'),
  invitation_purpose: 'join_discussion',
  required_expertise: null,
  urgency_level: 'high'
}]->(inv);

// Create Test Report
CREATE (:Report {
  report_id: 'report_001',
  title: 'Cardiac Evaluation Report - Case 001',
  report_type: 'analysis',
  format: 'pdf',
  status: 'generated',
  content: 'Comprehensive cardiac evaluation report...',
  template_used: 'cardiac_eval_v1',
  generated_by: 'ai',
  file_path: '/storage/reports/2024/01/report_001.pdf',
  file_size: 256000,
  page_count: 4,
  language: 'en',
  version: 1,
  created_at: datetime() - duration('PT2H'),
  updated_at: datetime() - duration('PT2H'),
  published_at: null,
  expires_at: null,
  is_confidential: true,
  access_level: 'private',
  download_count: 0,
  last_accessed: null,
  metadata: {
    included_analyses: ['analysis_001'],
    generated_for: 'case_001'
  },
  signatures: [],
  watermark: 'CONFIDENTIAL - Patient Records'
});

// Create report relationship
MATCH (c:Case {case_id: 'case_001'}), (r:Report {report_id: 'report_001'})
CREATE (c)-[:GENERATES {
  created_at: datetime() - duration('PT2H'),
  report_purpose: 'diagnosis',
  is_official: false
}]->(r);

// Create Test Session
CREATE (:Session {
  session_id: 'session_001',
  session_type: 'chat',
  status: 'ended',
  started_at: datetime() - duration('PT5H'),
  ended_at: datetime() - duration('PT4H'),
  duration: 3600,
  participant_count: 2,
  quality_metrics: {
    message_count: 15,
    response_time_avg: 2.5,
    user_satisfaction: 4.5
  },
  recording_available: false,
  recording_path: null,
  transcript_available: true,
  transcript_path: '/storage/transcripts/session_001.txt',
  bandwidth_usage: 1024000,
  error_count: 0,
  reconnection_count: 1,
  average_latency: 45.0,
  settings: {
    auto_save: true,
    quality: 'high'
  },
  metadata: {
    platform: 'web',
    browser: 'Chrome'
  }
});

// Create session relationships
MATCH (u:User {username: 'john_doe'}), (s:Session {session_id: 'session_001'})
CREATE (u)-[:HAS_SESSION {
  started_at: datetime() - duration('PT5H'),
  role: 'participant',
  device_type: 'desktop',
  connection_quality: 'good'
}]->(s);