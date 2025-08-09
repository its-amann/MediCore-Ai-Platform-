import React from 'react';
import { Bot, FileText, ExternalLink, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface AIResponseMessageProps {
  response: {
    type: string;
    content?: string;
    data?: any;
    references?: Array<{ title: string; url: string }>;
    confidence?: number;
    timestamp: string;
  };
}

const AIResponseMessage: React.FC<AIResponseMessageProps> = ({ response }) => {
  const renderContent = () => {
    if (response.type === 'ai_stream_chunk') {
      return <span>{response.content}</span>;
    }

    if (response.type === 'ai_image_analysis') {
      return (
        <div className="space-y-2">
          <p className="font-semibold">Medical Image Analysis:</p>
          <div className="bg-gray-50 p-3 rounded">
            <ReactMarkdown children={response.content || ''} />
          </div>
          {response.data?.findings && (
            <div className="mt-2">
              <p className="text-sm font-semibold text-gray-700">Key Findings:</p>
              <ul className="list-disc list-inside text-sm text-gray-600 mt-1">
                {response.data.findings.map((finding: string, index: number) => (
                  <li key={index}>{finding}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="space-y-2">
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown 
            components={{
              a: ({ node, ...props }) => (
                <a {...props} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-800" />
              ),
              code: ({ node, className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || '');
                const inline = !match;
                return inline ? (
                  <code className="bg-gray-100 px-1 py-0.5 rounded text-sm" {...props}>
                    {children}
                  </code>
                ) : (
                  <pre className="bg-gray-100 p-2 rounded overflow-x-auto">
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                );
              }
            }}
            children={response.content || ''}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="flex items-start space-x-3">
      <div className="flex-shrink-0">
        <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
          <Bot className="w-5 h-5 text-indigo-600" />
        </div>
      </div>
      
      <div className="flex-1">
        <div className="bg-gray-50 rounded-lg p-4">
          {renderContent()}
          
          {/* Confidence Score */}
          {response.confidence && (
            <div className="mt-3 flex items-center space-x-2 text-sm text-gray-500">
              <AlertCircle className="w-4 h-4" />
              <span>Confidence: {Math.round(response.confidence * 100)}%</span>
            </div>
          )}
          
          {/* References */}
          {response.references && response.references.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-200">
              <p className="text-sm font-semibold text-gray-700 mb-2">References:</p>
              <ul className="space-y-1">
                {response.references.map((ref, index) => (
                  <li key={index} className="flex items-center space-x-2 text-sm">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <a 
                      href={ref.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
                    >
                      <span>{ref.title}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        
        <p className="text-xs text-gray-400 mt-1">
          {new Date(response.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
};

export default AIResponseMessage;