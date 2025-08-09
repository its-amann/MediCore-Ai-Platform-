import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  MicrophoneIcon,
  StopIcon,
  PaperAirplaneIcon,
  PhotoIcon,
  XMarkIcon,
  ArrowLeftIcon,
  UserCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import api from '../api/axios';
import { useAuthStore } from '../store/authStore';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import AnalyzingCases from '../components/ui/AnalyzingCases';
import { useWebSocket } from '../contexts/WebSocketContext';

interface Message {
  id: string;
  type: 'user' | 'doctor';
  content: string;
  timestamp: Date;
  attachments?: {
    type: 'image' | 'audio';
    url: string;
  }[];
  doctorType?: string; // Add this to track which doctor responded
  sessionId?: string;  // Add this to track which session the message belongs to
}

interface ConsultationData {
  case_id: string;
  case_title: string;
  doctor_type: string;
  doctor_name: string;
  status: string;
}

interface DoctorSession {
  doctorType: string;
  sessionId: string | null;
}

// Storage keys for persistence
const STORAGE_KEYS = {
  SELECTED_DOCTOR: (caseId: string) => `selected_doctor_${caseId}`,
  DOCTOR_SESSIONS: (caseId: string) => `doctor_sessions_${caseId}`,
};

const Consultation: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { onMessage } = useWebSocket();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzingContext, setAnalyzingContext] = useState(false);
  const [consultationData, setConsultationData] = useState<ConsultationData | null>(null);
  const [selectedDoctor, setSelectedDoctor] = useState<string>('general_consultant');
  const [voiceSessionId, setVoiceSessionId] = useState<string | null>(null);
  const [doctorSessions, setDoctorSessions] = useState<Map<string, string | null>>(new Map());
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Load persisted doctor selection and sessions on mount
  useEffect(() => {
    if (caseId) {
      // Load persisted doctor selection
      const savedDoctor = localStorage.getItem(STORAGE_KEYS.SELECTED_DOCTOR(caseId));
      if (savedDoctor) {
        setSelectedDoctor(savedDoctor);
      }

      // Load persisted doctor sessions
      const savedSessions = localStorage.getItem(STORAGE_KEYS.DOCTOR_SESSIONS(caseId));
      if (savedSessions) {
        try {
          const sessionsArray = JSON.parse(savedSessions) as DoctorSession[];
          const sessionsMap = new Map(sessionsArray.map(s => [s.doctorType, s.sessionId]));
          setDoctorSessions(sessionsMap);
        } catch (error) {
          console.error('Failed to parse saved sessions:', error);
        }
      }

      fetchCaseData();
      fetchChatHistory();
    }
  }, [caseId]);

  // Persist doctor selection changes
  useEffect(() => {
    if (caseId && selectedDoctor) {
      localStorage.setItem(STORAGE_KEYS.SELECTED_DOCTOR(caseId), selectedDoctor);
    }
  }, [caseId, selectedDoctor]);

  // Persist doctor sessions changes
  useEffect(() => {
    if (caseId && doctorSessions.size > 0) {
      const sessionsArray = Array.from(doctorSessions.entries()).map(([doctorType, sessionId]) => ({
        doctorType,
        sessionId
      }));
      localStorage.setItem(STORAGE_KEYS.DOCTOR_SESSIONS(caseId), JSON.stringify(sessionsArray));
    }
  }, [caseId, doctorSessions]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Listen for WebSocket MCP analysis events
  useEffect(() => {
    const unsubscribe = onMessage((message: any) => {
      // Only handle MCP analysis events for this case
      if (message.case_id === caseId) {
        switch (message.type) {
          case 'mcp_analysis_started':
            setAnalyzingContext(true);
            break;
          case 'mcp_analysis_completed':
          case 'mcp_analysis_failed':
            setAnalyzingContext(false);
            break;
        }
      }
    });

    return unsubscribe;
  }, [caseId, onMessage]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchCaseData = async () => {
    try {
      const response = await api.get(`/cases/${caseId}`);
      const caseData = response.data;
      setConsultationData({
        case_id: caseData.case_id,
        case_title: caseData.chief_complaint || 'Medical Case',
        doctor_type: selectedDoctor,
        doctor_name: getDoctorName(selectedDoctor),
        status: 'active'
      });
    } catch (error) {
      console.error('Failed to fetch case data:', error);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const response = await api.get(`/cases/${caseId}/chat/history`);
      const data = response.data;
      
      // Handle both the object format and array format
      const history = data?.messages || data || [];
      const sessions = data?.sessions || [];
      
      const formattedMessages: Message[] = history.map((chat: any) => ({
        id: chat.id || chat.message_id || `msg_${Date.now()}_${Math.random()}`,
        type: chat.is_user ? 'user' : 'doctor',
        content: chat.content || chat.user_message || chat.doctor_response || '',
        timestamp: new Date(chat.created_at || chat.timestamp || Date.now()),
        doctorType: chat.doctor_type || chat.specialty || 'general_consultant',
        sessionId: chat.session_id
      }));
      
      // Update doctor sessions from the fetched data
      if (sessions.length > 0) {
        const newSessions = new Map<string, string | null>();
        sessions.forEach((session: any) => {
          if (session.doctor_type && session.session_id) {
            newSessions.set(session.doctor_type, session.session_id);
          }
        });
        setDoctorSessions(newSessions);
      }
      
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Failed to fetch chat history:', error);
      // Don't clear messages on error - preserve what we have
      toast.error('Failed to load chat history. Some messages may be missing.');
    }
  };

  const getDoctorName = (doctorType: string): string => {
    const doctorNames: { [key: string]: string } = {
      cardiologist: 'Dr. Sarah Mitchell (Cardiologist)',
      bp_specialist: 'Dr. James Chen (BP Specialist)',
      general_consultant: 'Dr. Emily Rodriguez (General Consultant)'
    };
    return doctorNames[doctorType] || 'AI Doctor';
  };

  // Filter messages based on selected doctor
  const filteredMessages = messages.filter(message => {
    if (message.type === 'user') return true; // Always show user messages
    return !message.doctorType || message.doctorType === selectedDoctor;
  });

  const handleDoctorChange = (newDoctor: string) => {
    setSelectedDoctor(newDoctor);
    // Don't clear messages or session - just switch view
    // The session for each doctor is maintained separately
  };

  const getCurrentSessionId = (): string | null => {
    return doctorSessions.get(selectedDoctor) || null;
  };

  const updateDoctorSession = (doctorType: string, sessionId: string) => {
    setDoctorSessions(prev => {
      const newMap = new Map(prev);
      newMap.set(doctorType, sessionId);
      return newMap;
    });
  };

  const handleSendMessage = async () => {
    if ((!inputMessage.trim() && !selectedImage) || loading) return;

    setLoading(true);
    // Note: analyzingContext will be controlled by WebSocket events from the backend
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
      doctorType: selectedDoctor,
      sessionId: getCurrentSessionId() || undefined,
      attachments: selectedImage ? [{
        type: 'image',
        url: imagePreview!
      }] : undefined
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');

    try {
      // MCP analysis state is handled by WebSocket events
      let requestData: any = {
        case_id: caseId,
        user_message: inputMessage || 'Please analyze this image',
        specialty: selectedDoctor,
        session_id: getCurrentSessionId()
      };

      // If image is selected, add it to the request
      if (selectedImage) {
        const base64 = await fileToBase64(selectedImage);
        requestData.image_data = base64.split(',')[1]; // Remove data:image/...;base64, prefix
      }

      const response = await api.post('/doctors/consult', requestData);
      
      // Save session ID if it's a new session
      if (response.data.session_id && !getCurrentSessionId()) {
        updateDoctorSession(selectedDoctor, response.data.session_id);
      }
      
      const doctorMessage: Message = {
        id: `doctor_${Date.now()}`,
        type: 'doctor',
        content: response.data.response,
        timestamp: new Date(),
        doctorType: selectedDoctor,
        sessionId: response.data.session_id
      };

      setMessages(prev => [...prev, doctorMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: `error_${Date.now()}`,
        type: 'doctor',
        content: 'I apologize, but I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
        doctorType: selectedDoctor
      }]);
    } finally {
      setLoading(false);
      // analyzingContext is controlled by WebSocket events
      setSelectedImage(null);
      setImagePreview(null);
    }
  };

  const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await sendAudioMessage(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      toast.error('Failed to access microphone');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  const sendAudioMessage = async (audioBlob: Blob) => {
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice_message.wav');
      formData.append('case_id', caseId || '');
      formData.append('specialty', selectedDoctor);
      
      if (voiceSessionId) {
        formData.append('session_id', voiceSessionId);
      }

      const response = await api.post('/doctors/voice-consult', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.session_id && !voiceSessionId) {
        setVoiceSessionId(response.data.session_id);
      }

      const userMessage: Message = {
        id: `user_${Date.now()}`,
        type: 'user',
        content: response.data.user_query || 'Voice message',
        timestamp: new Date(),
        doctorType: selectedDoctor,
        sessionId: getCurrentSessionId() || undefined,
        attachments: [{
          type: 'audio',
          url: URL.createObjectURL(audioBlob)
        }]
      };

      const doctorMessage: Message = {
        id: `doctor_${Date.now()}`,
        type: 'doctor',
        content: response.data.response,
        timestamp: new Date(),
        doctorType: selectedDoctor,
        sessionId: response.data.session_id
      };

      setMessages(prev => [...prev, userMessage, doctorMessage]);
    } catch (error) {
      console.error('Failed to send audio message:', error);
      toast.error('Failed to process voice message');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Please log in to access consultations.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                {consultationData?.case_title || 'Medical Consultation'}
              </h1>
              <p className="text-sm text-gray-600">
                Consulting with {getDoctorName(selectedDoctor)}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={selectedDoctor}
              onChange={(e) => handleDoctorChange(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="general_consultant">General Consultant</option>
              <option value="cardiologist">Cardiologist</option>
              <option value="bp_specialist">BP Specialist</option>
            </select>
            
            {getCurrentSessionId() && (
              <span className="text-xs text-gray-500 px-2 py-1 bg-gray-100 rounded">
                Session Active
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {filteredMessages.length === 0 && (
            <div className="text-center py-12">
              <UserCircleIcon className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-gray-500">
                Start your consultation with {getDoctorName(selectedDoctor)} by sending a message or uploading a medical image.
              </p>
              {messages.length > 0 && (
                <p className="mt-1 text-sm text-gray-400">
                  You have previous conversations with other specialists. Switch doctors to view them.
                </p>
              )}
            </div>
          )}

          {filteredMessages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-800'
                }`}
              >
                {message.attachments?.map((attachment, index) => (
                  <div key={index} className="mb-2">
                    {attachment.type === 'image' && (
                      <img
                        src={attachment.url}
                        alt="Uploaded"
                        className="rounded-lg max-w-full h-auto"
                      />
                    )}
                    {attachment.type === 'audio' && (
                      <audio controls className="w-full">
                        <source src={attachment.url} type="audio/wav" />
                      </audio>
                    )}
                  </div>
                ))}
                
                <div className={`prose ${message.type === 'user' ? 'prose-invert' : ''} max-w-none`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                </div>
                
                <div className={`text-xs mt-2 ${
                  message.type === 'user' ? 'text-blue-200' : 'text-gray-500'
                }`}>
                  <ClockIcon className="inline h-3 w-3 mr-1" />
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          
          {loading && (
            analyzingContext ? (
              <div className="flex justify-center py-4">
                <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
                  <AnalyzingCases 
                    message="Analyzing past cases..."
                    subMessage="Finding similar medical patterns to provide better diagnosis"
                  />
                </div>
              </div>
            ) : (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-lg px-4 py-2">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              </div>
            )
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t px-6 py-4">
        {selectedImage && (
          <div className="mb-3 flex items-center space-x-3 bg-gray-50 p-3 rounded-lg">
            <img
              src={imagePreview!}
              alt="Selected"
              className="h-20 w-20 object-cover rounded-lg"
            />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-700">Image attached</p>
              <p className="text-xs text-gray-500">{selectedImage.name}</p>
            </div>
            <button
              onClick={() => {
                setSelectedImage(null);
                setImagePreview(null);
              }}
              className="p-1 hover:bg-gray-200 rounded"
            >
              <XMarkIcon className="h-5 w-5 text-gray-600" />
            </button>
          </div>
        )}
        
        <div className="flex items-center space-x-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleImageSelect}
            accept="image/*"
            className="hidden"
          />
          
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            disabled={loading}
          >
            <PhotoIcon className="h-6 w-6 text-gray-600" />
          </button>
          
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-2 rounded-lg transition-colors ${
              isRecording 
                ? 'bg-red-100 hover:bg-red-200' 
                : 'hover:bg-gray-100'
            }`}
            disabled={loading}
          >
            {isRecording ? (
              <StopIcon className="h-6 w-6 text-red-600" />
            ) : (
              <MicrophoneIcon className="h-6 w-6 text-gray-600" />
            )}
          </button>
          
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading || isRecording}
          />
          
          <button
            onClick={handleSendMessage}
            disabled={loading || (!inputMessage.trim() && !selectedImage)}
            className={`p-2 rounded-lg transition-colors ${
              loading || (!inputMessage.trim() && !selectedImage)
                ? 'bg-gray-100 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            <PaperAirplaneIcon className={`h-6 w-6 ${
              loading || (!inputMessage.trim() && !selectedImage)
                ? 'text-gray-400'
                : 'text-white'
            }`} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Consultation;