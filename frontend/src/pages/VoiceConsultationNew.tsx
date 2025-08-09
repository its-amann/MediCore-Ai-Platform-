import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mic, 
  MicOff, 
  Video, 
  VideoOff, 
  Monitor, 
  MonitorOff,
  PhoneOff,
  MoreVertical,
  Settings,
  MessageSquare,
  Activity,
  Wifi,
  WifiOff
} from 'lucide-react';
import WaveAnimation from '../components/voice/WaveAnimation';
import FloatingParticles from '../components/voice/FloatingParticles';
import voiceConsultationAPI from '../api/voiceConsultation';
import { useVoiceConsultationWebSocket } from '../hooks/useVoiceConsultationWebSocket';
import toast from 'react-hot-toast';

type ConsultationState = 'idle' | 'listening' | 'processing' | 'responding';
type ViewMode = 'voice' | 'video' | 'screen_share';

const VoiceConsultationNew: React.FC = () => {
  const [state, setState] = useState<ConsultationState>('idle');
  const [viewMode, setViewMode] = useState<ViewMode>('voice');
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoEnabled, setIsVideoEnabled] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [statusText, setStatusText] = useState('Click to start consultation');
  const [showSettings, setShowSettings] = useState(false);
  const [transcript, setTranscript] = useState<string>('');
  const [aiResponse, setAiResponse] = useState<string>('');
  const [chatHistory, setChatHistory] = useState<Array<{user: string, ai: string}>>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const screenShareRef = useRef<HTMLVideoElement>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const wsConnectedRef = useRef<boolean>(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(document.createElement('canvas'));
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket hook
  const {
    isConnected,
    isProcessing,
    sendAudio,
    sendText,
    setMode,
    endSession
  } = useVoiceConsultationWebSocket({
    sessionId,
    userId,
    onMessage: (response) => {
      console.log('WebSocket response:', response);
      
      // Handle both 'type' field and response.type from backend
      const messageType = response.type || (response as any).type;
      
      switch (messageType) {
        case 'processing': {
          // Backend generic processing state
          setState('processing');
          setStatusText((response as any).message || 'Processing...');
          break;
        }
        case 'response': {
          // Unified response payload from backend
          const data = (response as any).data || {};
          const userText = data.transcription || transcript || '';
          const aiText = data.response_text || '';
          if (userText) setTranscript(userText);
          if (aiText) setAiResponse(aiText);
          if (userText || aiText) {
            setChatHistory(prev => [...prev, { user: userText, ai: aiText }]);
          }
          // Play audio if provided as base64 (mp3)
          if (data.audio_response) {
            try {
              // Stop any currently playing audio
              if (currentAudioRef.current) {
                currentAudioRef.current.pause();
                currentAudioRef.current = null;
              }
              
              const audio = new Audio(`data:audio/mp3;base64,${data.audio_response}`);
              currentAudioRef.current = audio;
              
              audio.play().catch(() => {});
              
              // Clear reference when audio ends
              audio.onended = () => {
                currentAudioRef.current = null;
              };
            } catch {}
          }
          setState('responding');
          setTimeout(() => setState('listening'), 1500);
          break;
        }
        case 'connection_established':
          setStatusText('Session connected');
          setState('listening');
          break;
          
        case 'transcription':
          setTranscript((response as any).text || '');
          setState('processing');
          break;
          
        case 'ai_response':
          const aiText = (response as any).text || '';
          setAiResponse(aiText);
          setChatHistory(prev => [...prev, { 
            user: transcript, 
            ai: aiText 
          }]);
          setState('responding');
          setTimeout(() => setState('listening'), 2000);
          break;
          
        case 'audio_response':
          const audioUrl = (response as any).audio_url;
          if (audioUrl) {
            // Play audio from data URL
            const audio = new Audio(audioUrl);
            audio.play().catch(e => console.error('Error playing audio:', e));
          }
          break;
          
        case 'mode_changed': {
          const mode = ((response as any).data && (response as any).data.mode) || (response as any).mode;
          toast.success(`Switched to ${mode || 'voice'} mode`);
          break;
        }
          
        case 'camera_status':
        case 'screen_share_status':
          // Status updates handled
          break;
          
        case 'system_message':
          toast((response as any).text || 'System message', { icon: 'ℹ️' });
          break;
          
        case 'chat_history':
          // Handle chat history if needed
          break;
          
        case 'pong':
          // Ping response, no action needed
          break;
          
        case 'error':
          toast.error((response as any).message || 'An error occurred');
          setState('idle');
          break;
          
        default:
          console.log('Unknown message type:', messageType);
      }
    },
    onConnect: () => {
      toast.success('Connected to voice service');
      console.log('WebSocket connected, starting audio recording...');
      startAudioRecording().catch(error => {
        console.error('Failed to start audio recording:', error);
        toast.error('Failed to start microphone');
      });
    },
    onDisconnect: () => {
      toast('Disconnected from voice service', { icon: 'ℹ️' });
      stopAudioRecording();
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
      toast.error('Connection error');
    }
  });

  // Update the ref whenever isConnected changes
  useEffect(() => {
    wsConnectedRef.current = isConnected;
    console.log('WebSocket connection status updated in ref:', isConnected);
  }, [isConnected]);

  // Background gradient based on state and view mode
  const getBackgroundGradient = () => {
    if (viewMode === 'screen_share') {
      return 'from-blue-900 via-purple-800 to-pink-700';
    }
    if (viewMode === 'video') {
      return 'from-blue-900 via-purple-900 to-purple-800';
    }
    
    switch (state) {
      case 'listening':
        return 'from-teal-900 via-green-800 to-blue-900';
      case 'processing':
        return 'from-blue-900 via-purple-900 to-indigo-900';
      case 'responding':
        return 'from-purple-900 via-pink-900 to-orange-900';
      default:
        return 'from-blue-900 via-blue-800 to-purple-700';
    }
  };

  // Start consultation session with video
  const startConsultation = async () => {
    try {
      // Start video immediately
      await startVideo();
      
      const result = await voiceConsultationAPI.startSession({
        user_name: localStorage.getItem('user_name') || 'User'
      });
      
      if (result.status === 'created' || result.session_id) {
        setSessionId(result.session_id);
        setUserId(result.user_id || null);
        setStatusText('Connecting...');
        setState('listening');
        toast.success('Video consultation started');
      }
    } catch (error) {
      console.error('Error starting consultation:', error);
      toast.error('Failed to start consultation');
      stopVideo();
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
        setStatusText('Click to start consultation');
        setChatHistory([]);
        setTranscript('');
        setAiResponse('');
        
        stopAudioRecording();
        stopVideo();
        stopScreenShare();
        
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
      console.log('Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      console.log('Microphone access granted, creating MediaRecorder...');
      
      // Check if MediaRecorder is supported with the desired mimeType
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' 
        : 'audio/webm';
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000 // Higher quality audio
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          console.log('Received audio data chunk, size:', event.data.size);
          audioChunksRef.current.push(event.data);
          
          // Stop any playing audio when user speaks (voice activity detected)
          if (currentAudioRef.current && !currentAudioRef.current.paused) {
            console.log('User speaking detected - stopping AI audio playback');
            currentAudioRef.current.pause();
            currentAudioRef.current = null;
            setState('listening');
          }
          
          // Send accumulated chunks when we have enough data (similar to speech_recognition library)
          // This helps ensure we have meaningful audio to process
          const totalSize = audioChunksRef.current.reduce((acc, chunk) => acc + chunk.size, 0);
          console.log('Total accumulated audio size:', totalSize);
          
          // Send when we have at least 50KB of audio data (roughly 1-2 seconds of speech)
          if (totalSize >= 50000) {
            console.log('Threshold reached! Processing audio blob...');
            const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
            console.log('Audio blob created, size:', audioBlob.size);
            
            const reader = new FileReader();
            
            reader.onloadend = () => {
              console.log('FileReader onloadend triggered');
              const base64Audio = reader.result?.toString().split(',')[1];
              console.log('Base64 audio extracted, length:', base64Audio ? base64Audio.length : 'null');
              console.log('wsConnectedRef.current status:', wsConnectedRef.current);
              
              if (base64Audio && wsConnectedRef.current) {
                console.log('Sending accumulated audio, base64 length:', base64Audio.length);
                const sent = sendAudio(base64Audio, 'webm');
                console.log('Audio sent result:', sent);
              } else {
                console.log('Cannot send audio - base64Audio:', !!base64Audio, 'wsConnectedRef.current:', wsConnectedRef.current);
              }
            };
            
            reader.onerror = (error) => {
              console.error('FileReader error:', error);
            };
            
            console.log('Starting to read blob as data URL...');
            reader.readAsDataURL(audioBlob);
            
            // Clear chunks after sending
            audioChunksRef.current = [];
          }
        }
      };
      
      mediaRecorder.onstop = () => {
        console.log('Audio recording stopped');
        // Send any remaining chunks
        if (audioChunksRef.current.length > 0) {
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          const reader = new FileReader();
          
          reader.onloadend = () => {
            const base64Audio = reader.result?.toString().split(',')[1];
            if (base64Audio && wsConnectedRef.current) {
              console.log('Sending final audio chunk on stop');
              sendAudio(base64Audio, 'webm');
            }
          };
          
          reader.readAsDataURL(audioBlob);
        }
        audioChunksRef.current = [];
      };
      
      // Start recording with timeslice to get data every 500ms
      // This ensures we get regular data availability
      mediaRecorder.start(500);
      console.log('MediaRecorder started with 500ms timeslice, state:', mediaRecorder.state);
      
    } catch (error) {
      console.error('Error starting audio recording:', error);
      toast.error('Failed to access microphone');
      throw error; // Re-throw to be caught by the caller
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

  // Play audio response
  const playAudioResponse = (audioBase64: string) => {
    try {
      const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
      audio.play();
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  };

  // Toggle video
  const toggleVideo = async () => {
    if (isVideoEnabled) {
      stopVideo();
    } else {
      await startVideo();
    }
  };

  // Capture frame from video
  const captureVideoFrame = () => {
    if (!videoRef.current || !localStreamRef.current) return null;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const context = canvas.getContext('2d');
    if (!context) return null;
    
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to base64
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
    return dataUrl.split(',')[1]; // Return just the base64 part
  };

  // Send video frame for analysis
  const sendVideoFrame = () => {
    if (!isConnected || !isVideoEnabled) return;
    
    const frameBase64 = captureVideoFrame();
    if (frameBase64) {
      // Send frame with current transcript as context
      sendAudio(frameBase64, 'image');
      console.log('Sent video frame for analysis');
    }
  };

  // Start video
  const startVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 1280, height: 720 },
        audio: false 
      });
      
      localStreamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      
      setIsVideoEnabled(true);
      setViewMode('video');
      
      if (isConnected) {
        setMode('video');
        
        // Start periodic frame capture (every 5 seconds)
        if (frameIntervalRef.current) {
          clearInterval(frameIntervalRef.current);
        }
        frameIntervalRef.current = setInterval(sendVideoFrame, 5000);
      }
      
      toast.success('Video enabled');
    } catch (error) {
      console.error('Error starting video:', error);
      toast.error('Failed to access camera');
    }
  };

  // Stop video
  const stopVideo = () => {
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    // Clear frame capture interval
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    
    setIsVideoEnabled(false);
    
    if (viewMode === 'video') {
      setViewMode('voice');
    }
    
    if (isConnected) {
      setMode('audio');
    }
  };

  // Toggle screen share
  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      stopScreenShare();
    } else {
      await startScreenShare();
    }
  };

  // Start screen share
  const startScreenShare = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false
      });
      
      screenStreamRef.current = stream;
      
      if (screenShareRef.current) {
        screenShareRef.current.srcObject = stream;
      }
      
      setIsScreenSharing(true);
      setViewMode('screen_share');
      
      if (isConnected) {
        setMode('screen_share');
      }
      
      // Handle screen share end
      stream.getVideoTracks()[0].onended = () => {
        stopScreenShare();
      };
      
      toast.success('Screen sharing started');
    } catch (error) {
      console.error('Error starting screen share:', error);
      toast.error('Failed to share screen');
    }
  };

  // Stop screen share
  const stopScreenShare = () => {
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
      screenStreamRef.current = null;
    }
    
    if (screenShareRef.current) {
      screenShareRef.current.srcObject = null;
    }
    
    setIsScreenSharing(false);
    
    if (viewMode === 'screen_share') {
      setViewMode('voice');
    }
    
    if (isConnected) {
      setMode('audio');
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

  // Send text message
  const handleSendText = (text: string) => {
    if (isConnected && text.trim()) {
      sendText(text);
      setTranscript(text);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (sessionId) {
        handleEndSession();
      }
    };
  }, []);

  return (
    <div className={`h-screen bg-gradient-to-br ${getBackgroundGradient()} transition-all duration-1000 overflow-hidden relative`}>
      <FloatingParticles />
      
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 p-6 flex justify-between items-center z-10">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-white">Voice Consultation</h1>
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <><Wifi className="w-4 h-4 text-green-400" /><span className="text-green-400 text-sm">Connected</span></>
            ) : (
              <><WifiOff className="w-4 h-4 text-red-400" /><span className="text-red-400 text-sm">Disconnected</span></>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          >
            <Settings className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="h-full flex items-center justify-center">
        {/* Video Display - Primary View */}
        {state === 'idle' ? (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
            <motion.div
              className="w-48 h-48 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center cursor-pointer hover:scale-105 transition-transform shadow-2xl"
              onClick={startConsultation}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5 }}
            >
              <Video className="w-20 h-20 text-white" />
            </motion.div>
          </div>
        ) : (
          <div className="relative w-full h-full bg-black">
            {/* Main Video Feed */}
            {isVideoEnabled && (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="absolute inset-0 w-full h-full object-cover"
              />
            )}
            
            {/* Screen Share Overlay */}
            {isScreenSharing && (
              <video
                ref={screenShareRef}
                autoPlay
                playsInline
                muted
                className="absolute inset-0 w-full h-full object-contain"
              />
            )}
            
            {/* Status Overlay */}
            <div className="absolute top-4 left-4 z-20">
              <div className="bg-black/60 backdrop-blur-sm rounded-lg px-4 py-2">
                <div className="flex items-center space-x-2">
                  {state === 'listening' && <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />}
                  {state === 'processing' && <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse" />}
                  {state === 'responding' && <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />}
                  <span className="text-white text-sm font-medium">
                    {state === 'listening' ? 'Listening...' : 
                     state === 'processing' ? 'Processing...' : 
                     state === 'responding' ? 'AI Responding...' : 'Ready'}
                  </span>
                </div>
              </div>
            </div>
            
            {/* AI Response Overlay */}
            {aiResponse && (
              <div className="absolute bottom-32 left-4 right-4 z-20">
                <div className="bg-black/70 backdrop-blur-sm rounded-lg p-4 max-w-2xl mx-auto">
                  <p className="text-white text-lg">{aiResponse}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Control Bar - Fixed at bottom */}
      {sessionId && (
        <div className="absolute bottom-0 left-0 right-0 bg-black/80 backdrop-blur-md">
          <div className="flex justify-center items-center py-6 px-8">
            <div className="flex items-center space-x-8">
              {/* Mic Control - Left */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={toggleMute}
                className={`p-4 rounded-full transition-all ${
                  isMuted ? 'bg-red-500 hover:bg-red-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {isMuted ? <MicOff className="w-6 h-6 text-white" /> : <Mic className="w-6 h-6 text-white" />}
              </motion.button>

              {/* Video Control - Center */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={toggleVideo}
                className={`p-5 rounded-full transition-all ${
                  isVideoEnabled ? 'bg-blue-500 hover:bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {isVideoEnabled ? <Video className="w-7 h-7 text-white" /> : <VideoOff className="w-7 h-7 text-white" />}
              </motion.button>

              {/* End Call - Right */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={handleEndSession}
                className="p-4 rounded-full bg-red-600 hover:bg-red-700 transition-all"
              >
                <PhoneOff className="w-6 h-6 text-white" />
              </motion.button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceConsultationNew;