import React, { useState, useRef } from 'react';
import { Mic, MicOff, Loader } from 'lucide-react';
import { motion } from 'framer-motion';

interface VoiceInputButtonProps {
  onTranscript: (transcript: string) => void;
  isRecording: boolean;
  setIsRecording: (recording: boolean) => void;
}

const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({ 
  onTranscript, 
  isRecording, 
  setIsRecording 
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

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
        setIsProcessing(true);
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // In a real implementation, send to speech-to-text API
        // For now, simulate with a timeout
        setTimeout(() => {
          onTranscript("This is a simulated transcription of your voice input.");
          setIsProcessing(false);
        }, 1500);

        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={isProcessing}
      className={`
        p-2 rounded-lg transition-all duration-200
        ${isRecording 
          ? 'bg-red-500 text-white hover:bg-red-600' 
          : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
        }
        ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
      `}
      title={isRecording ? 'Stop recording' : 'Start voice input'}
    >
      {isProcessing ? (
        <Loader className="w-5 h-5 animate-spin" />
      ) : isRecording ? (
        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        >
          <MicOff className="w-5 h-5" />
        </motion.div>
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  );
};

export default VoiceInputButton;