import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mic, 
  MicOff, 
  PhoneOff,
  Wifi,
  WifiOff,
  Volume2,
  Bot,
  User
} from 'lucide-react';
import voiceConsultationAPI from '../api/voiceConsultation';
import { useVoiceConsultationWebSocket } from '../hooks/useVoiceConsultationWebSocket';
import toast from 'react-hot-toast';

type ConsultationState = 'idle' | 'listening' | 'processing' | 'responding';

interface Message {
  id: string;
  type: 'user' | 'ai' | 'system';
  text: string;
  timestamp: Date;
  state?: ConsultationState;
}

const VoiceConsultationChat: React.FC = () => {
  const [state, setState] = useState<ConsultationState>('idle');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState<string>('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const wsConnectedRef = useRef<boolean>(false);
  const conversationRef = useRef<HTMLDivElement>(null);

  // WebSocket hook
  const {
    isConnected,
    sendAudio,
    endSession
  } = useVoiceConsultationWebSocket({
    sessionId,
    userId,
    onMessage: (response) => {
      console.log('WebSocket response:', response);
      
      const messageType = (response as any).type || response.type;
      const messageData = response as any;
      
      switch (messageType) {
        case 'partial_transcript':
          // Update current transcript being spoken
          setCurrentTranscript(prev => prev + ' ' + (messageData.text || ''));
          break;
        
        case 'transcription':
          // Final transcript - add user message
          if (messageData.text) {
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              type: 'user',
              text: messageData.text,
              timestamp: new Date()
            }]);
            setCurrentTranscript('');
            setState('processing');
          }
          break;
        
        case 'processing':
          setState('processing');
          break;
        
        case 'ai_response':
          if (messageData.text) {
            setState('responding');
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              type: 'ai',
              text: messageData.text,
              timestamp: new Date()
            }]);
            // Go back to listening after response
            setTimeout(() => setState('listening'), 1500);
          }
          break;
        
        case 'audio_response':
          if (messageData.audio_url) {
            const audio = new Audio(messageData.audio_url);
            audio.play().catch(e => console.error('Error playing audio:', e));
          }
          break;
        
        case 'connection_established':
        case 'session_started':
          setState('listening');
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            type: 'system',
            text: 'Connected. You can start speaking now.',
            timestamp: new Date()
          }]);
          break;
          
        case 'error':
          toast.error(messageData.message || 'An error occurred');
          break;
      }
    },
    onConnect: () => {
      toast.success('Connected to voice service');
      startAudioRecording().catch(error => {
        console.error('Failed to start audio recording:', error);
        toast.error('Failed to start microphone');
      });
    },
    onDisconnect: () => {
      toast('Disconnected from voice service', { icon: 'ℹ️' });
      stopAudioRecording();
      setState('idle');
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
      toast.error('Connection error');
    }
  });

  // Update the ref whenever isConnected changes
  useEffect(() => {
    wsConnectedRef.current = isConnected;
  }, [isConnected]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Start consultation session
  const startConsultation = async () => {
    try {
      const result = await voiceConsultationAPI.startSession({
        user_name: localStorage.getItem('user_name') || 'User'
      });
      
      if (result.status === 'created' || result.session_id) {
        setSessionId(result.session_id);
        setUserId(result.user_id || null);
        setMessages([{
          id: Date.now().toString(),
          type: 'system',
          text: 'Starting consultation...',
          timestamp: new Date()
        }]);
        toast.success('Consultation started');
      }
    } catch (error) {
      console.error('Error starting consultation:', error);
      toast.error('Failed to start consultation');
    }
  };

  // End consultation session
  const handleEndSession = async () => {
    if (sessionId) {
      try {
        if (isConnected) {
          endSession();
        } else {
          await voiceConsultationAPI.endSession(sessionId);
        }
        
        setSessionId(null);
        setState('idle');
        setMessages([]);
        setCurrentTranscript('');
        
        stopAudioRecording();
        
        toast.success('Consultation ended');
      } catch (error) {
        console.error('Error ending consultation:', error);
        toast.error('Failed to end consultation properly');
      }
    }
  };

  // Start audio recording
  const startAudioRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000
        } 
      });
      
      // Try to use WAV format if supported, otherwise fallback to webm
      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/wav')) {
        mimeType = 'audio/wav';
      } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      }
      
      console.log('Using audio format:', mimeType);
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      let recordingStartTime = Date.now();
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      // Send audio chunks every 3 seconds for more complete audio
      const sendInterval = setInterval(() => {
        if (audioChunksRef.current.length > 0 && wsConnectedRef.current) {
          // Create a new blob with all accumulated chunks
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          
          // Only send if we have substantial audio data (at least 10KB)
          if (audioBlob.size > 10000) {
            console.log(`Sending ${audioBlob.size} bytes of audio after ${Date.now() - recordingStartTime}ms`);
            
            const reader = new FileReader();
            reader.onloadend = () => {
              const base64Audio = reader.result?.toString().split(',')[1];
              if (base64Audio && wsConnectedRef.current) {
                // Send as webm even if it's wav (backend will detect format)
                sendAudio(base64Audio, mimeType.includes('wav') ? 'wav' : 'webm');
              }
            };
            
            reader.readAsDataURL(audioBlob);
            recordingStartTime = Date.now();
          } else {
            console.log(`Skipping send - only ${audioBlob.size} bytes accumulated`);
          }
          audioChunksRef.current = [];
        }
      }, 3000); // Send every 3 seconds for more complete chunks
      
      // Store interval ID for cleanup
      (mediaRecorder as any).sendInterval = sendInterval;
      
      mediaRecorder.onstop = () => {
        // Clear the interval
        if ((mediaRecorder as any).sendInterval) {
          clearInterval((mediaRecorder as any).sendInterval);
        }
        
        // Send any remaining audio
        if (audioChunksRef.current.length > 0) {
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          console.log(`Sending final ${audioBlob.size} bytes of audio`);
          
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64Audio = reader.result?.toString().split(',')[1];
            if (base64Audio && wsConnectedRef.current) {
              sendAudio(base64Audio, mimeType.includes('wav') ? 'wav' : 'webm');
            }
          };
          
          reader.readAsDataURL(audioBlob);
        }
        audioChunksRef.current = [];
      };
      
      // Start recording with longer timeslice for better chunks
      mediaRecorder.start(1000); // Collect data every 1 second, send every 3s
      
    } catch (error) {
      console.error('Error starting audio recording:', error);
      toast.error('Failed to access microphone');
      throw error;
    }
  };

  // Stop audio recording
  const stopAudioRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      mediaRecorderRef.current = null;
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (mediaRecorderRef.current) {
      const stream = mediaRecorderRef.current.stream;
      const audioTrack = stream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = isMuted;
        setIsMuted(!isMuted);
        toast.success(isMuted ? 'Unmuted' : 'Muted');
      }
    }
  };

  // Get state color
  const getStateColor = () => {
    switch (state) {
      case 'listening': return 'bg-green-500';
      case 'processing': return 'bg-yellow-500';
      case 'responding': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  // Get state text
  const getStateText = () => {
    switch (state) {
      case 'listening': return '🎤 Listening... (Speak now)';
      case 'processing': return '⚡ Processing...';
      case 'responding': return '💬 Responding...';
      default: return 'Click to start';
    }
  };

  return (
    <div className="h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex flex-col">
      {/* Header */}
      <div className="bg-black/30 backdrop-blur-sm p-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-white">Voice Consultation</h1>
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-400" />
                <span className="text-green-400 text-sm">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-400" />
                <span className="text-red-400 text-sm">Disconnected</span>
              </>
            )}
          </div>
        </div>
        
        {/* State Indicator */}
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${getStateColor()} animate-pulse`} />
          <span className="text-white text-sm">{getStateText()}</span>
        </div>
      </div>

      {/* Conversation Area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div 
          ref={conversationRef}
          className="flex-1 overflow-y-auto p-4 space-y-4"
        >
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex items-start space-x-2 max-w-lg ${
                message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  message.type === 'user' ? 'bg-blue-500' : 
                  message.type === 'ai' ? 'bg-purple-500' : 'bg-gray-500'
                }`}>
                  {message.type === 'user' ? <User className="w-5 h-5 text-white" /> :
                   message.type === 'ai' ? <Bot className="w-5 h-5 text-white" /> :
                   <Volume2 className="w-5 h-5 text-white" />}
                </div>
                
                {/* Message Bubble */}
                <div className={`px-4 py-2 rounded-2xl ${
                  message.type === 'user' ? 'bg-blue-600 text-white' :
                  message.type === 'ai' ? 'bg-white/20 text-white' :
                  'bg-yellow-600/20 text-yellow-200 text-sm italic'
                }`}>
                  <p>{message.text}</p>
                  <p className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
          
          {/* Current Transcript (while speaking) */}
          {currentTranscript && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-end"
            >
              <div className="flex items-start space-x-2 max-w-lg flex-row-reverse space-x-reverse">
                <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
                <div className="px-4 py-2 rounded-2xl bg-blue-600/50 text-white italic">
                  <p>{currentTranscript}</p>
                  <div className="flex space-x-1 mt-1">
                    <div className="w-2 h-2 bg-white rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-white rounded-full animate-bounce delay-100" />
                    <div className="w-2 h-2 bg-white rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Control Bar */}
      <div className="bg-black/30 backdrop-blur-sm p-6">
        <div className="flex justify-center items-center space-x-6">
          {state === 'idle' ? (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={startConsultation}
              className="p-6 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 transition-all"
            >
              <Mic className="w-8 h-8 text-white" />
            </motion.button>
          ) : (
            <>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={toggleMute}
                className={`p-4 rounded-full transition-colors ${
                  isMuted ? 'bg-red-500 hover:bg-red-600' : 'bg-white/20 hover:bg-white/30'
                }`}
              >
                {isMuted ? <MicOff className="w-6 h-6 text-white" /> : <Mic className="w-6 h-6 text-white" />}
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={handleEndSession}
                className="p-4 rounded-full bg-red-500 hover:bg-red-600 transition-colors"
              >
                <PhoneOff className="w-6 h-6 text-white" />
              </motion.button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default VoiceConsultationChat;