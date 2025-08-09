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
  MessageSquare
} from 'lucide-react';
import WaveformVisualizer from '../components/voice/WaveformVisualizer';
import FloatingParticles from '../components/voice/FloatingParticles';
import axios from '../api/axios';

type ConsultationState = 'idle' | 'listening' | 'processing' | 'responding';
type ViewMode = 'voice' | 'video' | 'screenshare';

const VoiceConsultation: React.FC = () => {
  const [state, setState] = useState<ConsultationState>('idle');
  const [viewMode, setViewMode] = useState<ViewMode>('voice');
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoEnabled, setIsVideoEnabled] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [statusText, setStatusText] = useState('Click to start consultation');
  const [showSettings, setShowSettings] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const screenShareRef = useRef<HTMLVideoElement>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const webSocketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  // Background gradient based on state and view mode
  const getBackgroundGradient = () => {
    if (viewMode === 'screenshare') {
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
        return 'from-blue-900 via-blue-800 to-white';
    }
  };

  // Initialize WebSocket connection
  const initializeWebSocket = async () => {
    try {
      // Create consultation session
      const response = await axios.post('/voice/consultations/create', {
        consultation_type: isVideoEnabled ? 'video' : 'voice',
        ai_provider: 'groq',
        language: 'en',
        doctor_type: 'general'
      });

      const { session_id, websocket_url } = response.data;
      setSessionId(session_id);

      // Connect WebSocket
      const ws = new WebSocket(websocket_url);
      webSocketRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setState('listening');
        setStatusText('Listening...');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setStatusText('Connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setState('idle');
        setStatusText('Click to start consultation');
      };

    } catch (error) {
      console.error('Failed to initialize session:', error);
      setStatusText('Failed to connect');
    }
  };

  // Handle WebSocket messages
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'voice_state_changed':
        // Handle state changes from flow coordinator
        switch (data.state) {
          case 'listening':
            setState('listening');
            setStatusText(data.message || 'Listening...');
            break;
          case 'processing':
            setState('processing');
            setStatusText(data.message || 'Processing...');
            break;
          case 'responding':
            setState('responding');
            setStatusText(data.message || 'Speaking...');
            // Play audio response if available
            if (data.audio_data) {
              playAudioResponseFromBase64(data.audio_data, data.audio_format);
            }
            break;
          case 'error':
            setState('idle');
            setStatusText(data.error || 'Error occurred');
            break;
        }
        break;
      case 'transcription_started':
        setState('processing');
        setStatusText('Processing...');
        break;
      case 'transcription_completed':
        console.log('User said:', data.text);
        break;
      case 'ai_response_started':
        setState('processing');
        setStatusText('Thinking...');
        break;
      case 'ai_response_completed':
        setState('responding');
        setStatusText('Speaking...');
        // Play audio response
        if (data.audio_url) {
          playAudioResponse(data.audio_url);
        } else if (data.audio_data) {
          playAudioResponseFromBase64(data.audio_data, 'wav');
        }
        break;
      case 'visual_analysis':
        console.log('Visual analysis:', data.analysis);
        break;
      case 'session_ended':
        handleSessionEnd();
        break;
      case 'audio_processing':
        // Handle processing step updates
        if (data.step && data.status) {
          const stepMessages: { [key: string]: string } = {
            'transcription': data.status === 'started' ? 'Transcribing speech...' : 'Transcription complete',
            'ai_processing': data.status === 'started' ? 'Processing with AI...' : 'AI response ready',
            'tts_generation': data.status === 'started' ? 'Generating speech...' : 'Speech ready'
          };
          const message = stepMessages[data.step] || `${data.step}: ${data.status}`;
          setStatusText(message);
          
          // Update transcript if available
          if (data.step === 'transcription' && data.status === 'completed' && data.text) {
            console.log('Transcription:', data.text);
          }
        }
        break;
    }
  };

  // Play audio response
  const playAudioResponse = async (audioUrl: string) => {
    try {
      const audio = new Audio(audioUrl);
      audio.onended = () => {
        setState('listening');
        setStatusText('Listening...');
      };
      await audio.play();
    } catch (error) {
      console.error('Failed to play audio:', error);
    }
  };

  // Play audio response from base64 data
  const playAudioResponseFromBase64 = async (base64Data: string, format: string = 'wav') => {
    try {
      // Convert base64 to blob
      const byteCharacters = atob(base64Data);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      
      // Create blob with appropriate MIME type
      const mimeType = format === 'wav' ? 'audio/wav' : 'audio/mpeg';
      const blob = new Blob([byteArray], { type: mimeType });
      
      // Create audio URL and play
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setState('listening');
        setStatusText('Listening...');
        URL.revokeObjectURL(audioUrl); // Clean up
      };
      
      await audio.play();
    } catch (error) {
      console.error('Failed to play audio from base64:', error);
    }
  };

  // Start audio streaming
  const startAudioStreaming = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });

      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      const source = audioContextRef.current.createMediaStreamSource(stream);
      const processor = audioContextRef.current.createScriptProcessor(512, 1, 1);

      processor.onaudioprocess = (e) => {
        if (!isMuted && webSocketRef.current?.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          const audioData = convertFloat32ToInt16(inputData);
          
          webSocketRef.current.send(JSON.stringify({
            type: 'audio_chunk',
            consultation_session_id: sessionId,
            format: 'pcm16',
            sample_rate: 16000,
            data: btoa(String.fromCharCode(...new Uint8Array(audioData.buffer))),
            timestamp: Date.now()
          }));
        }
      };

      source.connect(processor);
      processor.connect(audioContextRef.current.destination);
      processorRef.current = processor;
      localStreamRef.current = stream;

    } catch (error) {
      console.error('Failed to start audio:', error);
      setStatusText('Microphone access denied');
    }
  };

  // Convert Float32Array to Int16Array
  const convertFloat32ToInt16 = (float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  };

  // Toggle main voice session
  const toggleVoiceSession = async () => {
    if (state === 'idle') {
      await initializeWebSocket();
      await startAudioStreaming();
    } else {
      handleSessionEnd();
    }
  };

  // Handle session end
  const handleSessionEnd = () => {
    // Close WebSocket
    if (webSocketRef.current) {
      webSocketRef.current.close();
      webSocketRef.current = null;
    }

    // Stop audio
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }

    // Stop video/screen if active
    if (isVideoEnabled) toggleVideo();
    if (isScreenSharing) toggleScreenShare();

    setState('idle');
    setStatusText('Click to start consultation');
    setSessionId(null);
    setViewMode('voice');
  };

  // Toggle video
  const toggleVideo = async () => {
    if (!isVideoEnabled) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user"
          }
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        // Start sending video frames
        startVideoFrameCapture(stream);
        setIsVideoEnabled(true);
        setViewMode('video');

      } catch (error) {
        console.error('Failed to access camera:', error);
      }
    } else {
      // Stop video
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
        videoRef.current.srcObject = null;
      }
      setIsVideoEnabled(false);
      if (viewMode === 'video') setViewMode('voice');
    }
  };

  // Start capturing video frames
  const startVideoFrameCapture = (stream: MediaStream) => {
    const video = document.createElement('video');
    video.srcObject = stream;
    video.play();

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    const captureInterval = setInterval(() => {
      if (!isVideoEnabled || !webSocketRef.current) {
        clearInterval(captureInterval);
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx!.drawImage(video, 0, 0);

      canvas.toBlob((blob) => {
        if (blob) {
          const reader = new FileReader();
          reader.onload = () => {
            const base64 = reader.result!.toString().split(',')[1];
            
            webSocketRef.current!.send(JSON.stringify({
              type: 'video_frame',
              data: base64,
              timestamp: Date.now()
            }));
          };
          reader.readAsDataURL(blob);
        }
      }, 'image/jpeg', 0.8);
    }, 1000); // 1 FPS
  };

  // Toggle screen share
  const toggleScreenShare = async () => {
    if (!isScreenSharing) {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false
        });

        screenStreamRef.current = stream;
        
        if (screenShareRef.current) {
          screenShareRef.current.srcObject = stream;
        }
        
        stream.getVideoTracks()[0].onended = () => {
          setIsScreenSharing(false);
          if (viewMode === 'screenshare') setViewMode('voice');
        };

        startScreenCapture(stream);
        setIsScreenSharing(true);
        setViewMode('screenshare');

      } catch (error) {
        console.error('Screen share failed:', error);
      }
    } else {
      // Stop screen share
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
        screenStreamRef.current = null;
      }
      setIsScreenSharing(false);
      if (viewMode === 'screenshare') setViewMode('voice');
    }
  };

  // Start screen capture
  const startScreenCapture = (stream: MediaStream) => {
    const video = document.createElement('video');
    video.srcObject = stream;
    video.play();

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    const captureInterval = setInterval(() => {
      if (!isScreenSharing || !webSocketRef.current) {
        clearInterval(captureInterval);
        return;
      }

      canvas.width = Math.min(video.videoWidth, 1920);
      canvas.height = Math.min(video.videoHeight, 1080);

      ctx!.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob((blob) => {
        if (blob) {
          const reader = new FileReader();
          reader.onload = () => {
            const base64 = reader.result!.toString().split(',')[1];
            
            webSocketRef.current!.send(JSON.stringify({
              type: 'screen_frame',
              data: base64,
              dimensions: {
                width: canvas.width,
                height: canvas.height
              },
              timestamp: Date.now()
            }));
          };
          reader.readAsDataURL(blob);
        }
      }, 'image/jpeg', 0.7);
    }, 2000); // 0.5 FPS
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      handleSessionEnd();
    };
  }, []);

  return (
    <div className={`min-h-screen bg-gradient-to-b ${getBackgroundGradient()} transition-all duration-1000 relative overflow-hidden`}>
      {/* Floating particles background */}
      <FloatingParticles />

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen p-8">
        
        {/* Voice Mode View */}
        {viewMode === 'voice' && (
          <>
            {/* Status text */}
            <motion.p
              key={statusText}
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-white text-lg font-light mb-8"
            >
              {statusText}
            </motion.p>

            {/* Waveform visualizer */}
            <div className="w-full max-w-4xl h-64 mb-16">
              <WaveformVisualizer state={state} />
            </div>

            {/* Control buttons */}
            <div className="flex items-center gap-8">
              
              {/* Mute button */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsMuted(!isMuted)}
                className={`p-4 rounded-full transition-all ${
                  isMuted 
                    ? 'bg-red-500 text-white' 
                    : 'bg-white/20 text-white hover:bg-white/30'
                }`}
                disabled={state === 'idle'}
              >
                {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
              </motion.button>

              {/* Main microphone button */}
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleVoiceSession}
                className={`relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500 ${
                  state === 'idle' 
                    ? 'bg-white text-gray-800 hover:shadow-2xl' 
                    : state === 'listening'
                    ? 'bg-green-500 text-white animate-pulse'
                    : state === 'processing'
                    ? 'bg-blue-500 text-white'
                    : 'bg-orange-500 text-white animate-pulse'
                }`}
              >
                {/* Ripple effect for active states */}
                {state !== 'idle' && (
                  <>
                    <span className="absolute inset-0 rounded-full animate-ping opacity-25 bg-current" />
                    <span className="absolute inset-0 rounded-full animate-ping animation-delay-200 opacity-25 bg-current" />
                  </>
                )}
                
                <Mic size={40} />

                {/* Processing loader */}
                {state === 'processing' && (
                  <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-white animate-spin" />
                )}
              </motion.button>

              {/* Video button */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleVideo}
                className={`p-4 rounded-full transition-all ${
                  isVideoEnabled 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-white/20 text-white hover:bg-white/30'
                }`}
                disabled={state === 'idle'}
              >
                {isVideoEnabled ? <Video size={24} /> : <VideoOff size={24} />}
              </motion.button>

              {/* Screen share button */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleScreenShare}
                className={`p-4 rounded-full transition-all ${
                  isScreenSharing 
                    ? 'bg-purple-500 text-white' 
                    : 'bg-white/20 text-white hover:bg-white/30'
                }`}
                disabled={state === 'idle'}
              >
                {isScreenSharing ? <Monitor size={24} /> : <MonitorOff size={24} />}
              </motion.button>
            </div>
          </>
        )}

        {/* Video Call View */}
        {viewMode === 'video' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-6xl mx-auto"
          >
            {/* Remote video (main view) */}
            <div className="relative w-full h-[70vh] bg-black/30 rounded-lg overflow-hidden border border-white/20 backdrop-blur-sm">
              <video
                ref={remoteVideoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
              />
              
              {/* Placeholder when no remote video */}
              {!remoteVideoRef.current?.srcObject && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <div className="w-32 h-32 mx-auto bg-blue-900/50 rounded-full flex items-center justify-center mb-4">
                      <svg className="w-20 h-20 text-white/60" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                      </svg>
                    </div>
                    <p className="text-white/60">Waiting for video...</p>
                  </div>
                </div>
              )}

              {/* Self video (picture-in-picture) */}
              <motion.div
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                className="absolute top-4 right-4 w-48 h-36 bg-black rounded-lg overflow-hidden border border-white/30"
              >
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
              </motion.div>
            </div>

            {/* Video call controls */}
            <div className="flex items-center justify-center gap-6 mt-8">
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsMuted(!isMuted)}
                className="w-16 h-16 rounded-full bg-red-500/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-red-600/80 transition-all"
              >
                {isMuted ? <MicOff size={28} /> : <Mic size={28} />}
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleVideo}
                className="w-16 h-16 rounded-full bg-green-500/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-green-600/80 transition-all"
              >
                {isVideoEnabled ? <Video size={28} /> : <VideoOff size={28} />}
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleScreenShare}
                className="w-16 h-16 rounded-full bg-cyan-500/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-cyan-600/80 transition-all"
              >
                <Monitor size={28} />
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSessionEnd}
                className="w-16 h-16 rounded-full bg-red-600/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-red-700/80 transition-all"
              >
                <PhoneOff size={28} />
              </motion.button>
            </div>
          </motion.div>
        )}

        {/* Screen Share View */}
        {viewMode === 'screenshare' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-7xl mx-auto"
          >
            {/* Shared screen content */}
            <div className="relative w-full h-[75vh] bg-black/20 rounded-lg overflow-hidden border-2 border-white/30 backdrop-blur-sm">
              <video
                ref={screenShareRef}
                autoPlay
                playsInline
                className="w-full h-full object-contain"
              />
              
              {/* Placeholder when no screen share */}
              {!screenShareRef.current?.srcObject && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <Monitor className="w-24 h-24 text-white/40 mx-auto mb-4" />
                    <p className="text-white/60">Screen content will appear here</p>
                  </div>
                </div>
              )}

              {/* Video thumbnail */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="absolute top-4 right-4 w-40 h-30 bg-black/80 rounded-lg overflow-hidden border border-white/30 backdrop-blur-sm"
              >
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  {!isVideoEnabled && (
                    <div className="w-16 h-16 bg-blue-900/50 rounded-full flex items-center justify-center">
                      <svg className="w-10 h-10 text-white/60" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                      </svg>
                    </div>
                  )}
                </div>
              </motion.div>
            </div>

            {/* Screen share controls */}
            <div className="flex items-center justify-center gap-6 mt-8">
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsMuted(!isMuted)}
                className="w-16 h-16 rounded-full bg-red-500/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-red-600/80 transition-all"
              >
                {isMuted ? <MicOff size={28} /> : <Mic size={28} />}
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleVideo}
                className="w-16 h-16 rounded-full bg-green-500/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-green-600/80 transition-all"
              >
                {isVideoEnabled ? <Video size={28} /> : <VideoOff size={28} />}
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleScreenShare}
                className="w-16 h-16 rounded-full bg-orange-500/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-orange-600/80 transition-all"
              >
                <MonitorOff size={28} />
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowSettings(!showSettings)}
                className="w-16 h-16 rounded-full bg-blue-500/80 backdrop-blur-sm text-white flex items-center justify-center hover:bg-blue-600/80 transition-all"
              >
                <MoreVertical size={28} />
              </motion.button>
            </div>

            {/* Settings Menu */}
            <AnimatePresence>
              {showSettings && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 20 }}
                  className="absolute bottom-32 right-1/2 transform translate-x-1/2 bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20"
                >
                  <button className="flex items-center gap-3 text-white hover:bg-white/10 p-2 rounded w-full">
                    <Settings size={20} />
                    <span>Select Share Source</span>
                  </button>
                  <button className="flex items-center gap-3 text-white hover:bg-white/10 p-2 rounded w-full mt-2">
                    <MessageSquare size={20} />
                    <span>Annotation Tools</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default VoiceConsultation;