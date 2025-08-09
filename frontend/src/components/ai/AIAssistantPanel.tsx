import React, { useState, useRef } from 'react';
import { Bot, Send, Mic, MicOff, Image } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../../contexts/WebSocketContext';
import AIResponseMessage from './AIResponseMessage';
import VoiceInputButton from './VoiceInputButton';

interface AIAssistantPanelProps {
  roomId: string;
  roomType: 'case_discussion' | 'teaching';
  subject?: string;
}

const AIAssistantPanel: React.FC<AIAssistantPanelProps> = ({ roomId, roomType, subject }) => {
  const [question, setQuestion] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [aiResponses, setAiResponses] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { sendMessage, onMessage } = useWebSocket();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Listen for AI responses
  React.useEffect(() => {
    const unsubscribe = onMessage((message) => {
      if (message.type === 'ai_response' || message.type === 'ai_stream_chunk') {
        setAiResponses(prev => [...prev, message]);
        setIsLoading(false);
      }
    });
    return unsubscribe;
  }, [onMessage]);

  const handleSendQuestion = () => {
    if (!question.trim()) return;

    setIsLoading(true);
    sendMessage({
      type: 'ai_question',
      room_id: roomId,
      question,
      subject,
      context: roomType
    });

    // Add user question to responses
    setAiResponses(prev => [...prev, {
      type: 'user_question',
      content: question,
      timestamp: new Date().toISOString()
    }]);

    setQuestion('');
  };

  const handleVoiceInput = (transcript: string) => {
    setQuestion(transcript);
  };

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Convert to base64
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      
      setIsLoading(true);
      sendMessage({
        type: 'ai_image_analysis',
        room_id: roomId,
        image: base64,
        filename: file.name,
        context: 'medical_image_analysis'
      });
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b">
        <div className="flex items-center space-x-2">
          <Bot className="w-6 h-6 text-indigo-600" />
          <h3 className="text-lg font-semibold">AI Medical Assistant</h3>
        </div>
        {subject && (
          <span className="text-sm text-gray-500">Topic: {subject}</span>
        )}
      </div>

      {/* Response Area */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        <AnimatePresence>
          {aiResponses.map((response, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              {response.type === 'user_question' ? (
                <div className="flex justify-end">
                  <div className="bg-indigo-100 text-indigo-900 rounded-lg px-4 py-2 max-w-xs">
                    {response.content}
                  </div>
                </div>
              ) : (
                <AIResponseMessage response={response} />
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <div className="flex items-center space-x-2 text-gray-500">
            <div className="animate-pulse">AI is thinking...</div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t pt-4">
        <div className="flex items-end space-x-2">
          <div className="flex-1 relative">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendQuestion();
                }
              }}
              placeholder="Ask a medical question..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none overflow-hidden"
              rows={2}
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
          </div>
          
          {/* Action Buttons */}
          <div className="flex flex-col space-y-2">
            <VoiceInputButton
              onTranscript={handleVoiceInput}
              isRecording={isRecording}
              setIsRecording={setIsRecording}
            />
            
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              title="Upload medical image"
            >
              <Image className="w-5 h-5" />
            </button>
            
            <button
              onClick={handleSendQuestion}
              disabled={!question.trim() || isLoading}
              className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          className="hidden"
        />
      </div>
    </div>
  );
};

export default AIAssistantPanel;