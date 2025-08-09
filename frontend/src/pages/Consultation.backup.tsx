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

interface Message {
  id: string;
  type: 'user' | 'doctor';
  content: string;
  timestamp: Date;
  attachments?: {
    type: 'image' | 'audio';
    url: string;
  }[];
}

interface ConsultationData {
  case_id: string;
  case_title: string;
  doctor_type: string;
  doctor_name: string;
  status: string;
}

const Consultation: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [consultationData, setConsultationData] = useState<ConsultationData | null>(null);
  const [selectedDoctor, setSelectedDoctor] = useState<string>('general_consultant');
  const [voiceSessionId, setVoiceSessionId] = useState<string | null>(null);
  const [consultationSessionId, setConsultationSessionId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (caseId) {
      fetchCaseData();
      fetchChatHistory();
    }
  }, [caseId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
      const response = await api.get(`/chat/case/${caseId}/conversations`);
      const history = response.data?.messages || [];
      
      const formattedMessages: Message[] = history.map((chat: any) => ({
        id: chat.id || chat.message_id || `msg_${Date.now()}_${Math.random()}`,
        type: chat.is_user ? 'user' : 'doctor',
        content: chat.content || chat.user_message || chat.doctor_response || '',
        timestamp: new Date(chat.created_at || chat.timestamp || Date.now())
      }));
      
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Failed to fetch chat history:', error);
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

  const handleSendMessage = async () => {
    if ((!inputMessage.trim() && !selectedImage) || loading) return;

    setLoading(true);
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
      attachments: selectedImage ? [{
        type: 'image',
        url: imagePreview!
      }] : undefined
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');

    try {
      let requestData: any = {
        case_id: caseId,
        user_message: inputMessage || 'Please analyze this image',  // Changed from 'message' to 'user_message'
        specialty: selectedDoctor,
        session_id: consultationSessionId
      };

      // If image is selected, add it to the request
      if (selectedImage) {
        const base64 = await fileToBase64(selectedImage);
        requestData.image_data = base64.split(',')[1]; // Remove data:image/...;base64, prefix
      }

      const response = await api.post('/doctors/consult', requestData);
      
      // Save session ID if it's a new session
      if (response.data.session_id && !consultationSessionId) {
        setConsultationSessionId(response.data.session_id);
      }
      
      const doctorMessage: Message = {
        id: `doctor_${Date.now()}`,
        type: 'doctor',
        content: response.data.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, doctorMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: `error_${Date.now()}`,
        type: 'doctor',
        content: 'I apologize, but I encountered an error processing your request. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
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
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendVoiceMessage(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      // Start voice session if not already started
      if (!voiceSessionId) {
        const sessionResponse = await api.post('/voice/session', {
          case_id: caseId,
          doctor_type: selectedDoctor
        });
        setVoiceSessionId(sessionResponse.data.session_id);
      }

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      toast.error('Unable to access microphone. Please check your permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendVoiceMessage = async (audioBlob: Blob) => {
    setLoading(true);
    
    try {
      // Convert blob to base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result as string;
        
        // Add user's voice message placeholder
        const userMessage: Message = {
          id: `voice_user_${Date.now()}`,
          type: 'user',
          content: '🎤 Voice message',
          timestamp: new Date(),
          attachments: [{
            type: 'audio',
            url: base64Audio
          }]
        };
        setMessages(prev => [...prev, userMessage]);

        // Send to backend
        const response = await api.post('/voice/process', {
          session_id: voiceSessionId,
          audio_data: base64Audio.split(',')[1]
        });

        if (response.data.success) {
          // Update user message with transcription
          setMessages(prev => prev.map(msg => 
            msg.id === userMessage.id 
              ? { ...msg, content: response.data.transcription }
              : msg
          ));

          // Add doctor's response
          const doctorMessage: Message = {
            id: `voice_doctor_${Date.now()}`,
            type: 'doctor',
            content: response.data.response_text,
            timestamp: new Date()
          };
          setMessages(prev => [...prev, doctorMessage]);

          // Play audio response if available
          if (response.data.response_audio) {
            const audio = new Audio(`data:audio/mp3;base64,${response.data.response_audio}`);
            audio.play();
          }
        }
      };
    } catch (error) {
      console.error('Failed to process voice message:', error);
      setMessages(prev => [...prev, {
        id: `error_${Date.now()}`,
        type: 'doctor',
        content: 'I had trouble processing your voice message. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/cases')}
              className="text-gray-500 hover:text-gray-700"
            >
              <ArrowLeftIcon className="h-5 w-5" />
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

          <div className="flex items-center">
            <select
              value={selectedDoctor}
              onChange={(e) => {
                setSelectedDoctor(e.target.value);
                // Reset session when doctor changes
                setConsultationSessionId(null);
                // Clear messages for new doctor
                setMessages([]);
              }}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="general_consultant">General Consultant</option>
              <option value="cardiologist">Cardiologist</option>
              <option value="bp_specialist">BP Specialist</option>
            </select>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <UserCircleIcon className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-gray-500">
                Start your consultation by sending a message or uploading a medical image.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-900 shadow'
                }`}
              >
                {message.type === 'doctor' ? (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({children}) => <p className="text-sm mb-2 last:mb-0">{children}</p>,
                        ul: ({children}) => <ul className="list-disc pl-4 mb-2 text-sm">{children}</ul>,
                        ol: ({children}) => <ol className="list-decimal pl-4 mb-2 text-sm">{children}</ol>,
                        li: ({children}) => <li className="mb-1">{children}</li>,
                        strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                        em: ({children}) => <em className="italic">{children}</em>,
                        code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">{children}</code>,
                        pre: ({children}) => <pre className="bg-gray-100 p-2 rounded overflow-x-auto text-xs">{children}</pre>,
                        a: ({children, href}) => <a href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                )}
                {message.attachments?.map((attachment, idx) => (
                  <div key={idx} className="mt-2">
                    {attachment.type === 'image' && (
                      <img
                        src={attachment.url}
                        alt="Attachment"
                        className="rounded-md max-w-full"
                      />
                    )}
                    {attachment.type === 'audio' && (
                      <audio controls className="max-w-full">
                        <source src={attachment.url} type="audio/webm" />
                      </audio>
                    )}
                  </div>
                ))}
                <p className={`text-xs mt-1 ${
                  message.type === 'user' ? 'text-blue-200' : 'text-gray-500'
                }`}>
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-white text-gray-900 shadow max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200"></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Image Preview */}
      {imagePreview && (
        <div className="bg-white border-t px-6 py-3">
          <div className="flex items-center space-x-3">
            <img
              src={imagePreview}
              alt="Preview"
              className="h-20 w-20 object-cover rounded-md"
            />
            <div className="flex-1">
              <p className="text-sm text-gray-600">Image ready to send</p>
              <p className="text-xs text-gray-500">{selectedImage?.name}</p>
            </div>
            <button
              onClick={() => {
                setSelectedImage(null);
                setImagePreview(null);
              }}
              className="text-gray-500 hover:text-gray-700"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="bg-white border-t px-6 py-4">
        <div className="flex items-end space-x-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleImageSelect}
            accept="image/*"
            className="hidden"
          />
          
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-gray-500 hover:text-gray-700 p-2 relative group"
            disabled={loading}
            title="Upload medical image"
          >
            <PhotoIcon className="h-6 w-6" />
            <span className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-white bg-gray-800 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              Upload image
            </span>
          </button>

          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-2 rounded-full ${
              isRecording
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            disabled={loading}
          >
            {isRecording ? (
              <StopIcon className="h-6 w-6" />
            ) : (
              <MicrophoneIcon className="h-6 w-6" />
            )}
          </button>

          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Type your message or describe your symptoms..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 resize-none"
              rows={1}
              disabled={loading || isRecording}
            />
          </div>

          <button
            onClick={handleSendMessage}
            disabled={(!inputMessage.trim() && !selectedImage) || loading || isRecording}
            className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PaperAirplaneIcon className="h-6 w-6" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Consultation;