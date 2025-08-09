import React from 'react';

interface SkeletonLoaderProps {
  lines?: number;
  className?: string;
  height?: string;
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  lines = 3,
  className = '',
  height = 'h-4'
}) => {
  return (
    <div className={`animate-pulse ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={`bg-gray-300 rounded ${height} ${
            index !== lines - 1 ? 'mb-2' : ''
          } ${index === lines - 1 ? 'w-3/4' : 'w-full'}`}
        />
      ))}
    </div>
  );
};

// Card skeleton for case items
export const CaseCardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-lg shadow border-2 border-gray-100 p-6 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-3">
            <div className="h-5 w-5 bg-gray-300 rounded"></div>
            <div className="h-6 bg-gray-300 rounded w-1/2"></div>
            <div className="h-5 bg-gray-300 rounded-full w-16"></div>
          </div>
          
          <div className="space-y-2 mb-4">
            <div className="h-4 bg-gray-300 rounded w-16"></div>
            <div className="flex flex-wrap gap-2">
              <div className="h-6 bg-gray-300 rounded-md w-20"></div>
              <div className="h-6 bg-gray-300 rounded-md w-24"></div>
              <div className="h-6 bg-gray-300 rounded-md w-16"></div>
            </div>
          </div>
          
          <div className="flex items-center space-x-6 text-sm">
            <div className="flex items-center">
              <div className="h-4 w-4 bg-gray-300 rounded mr-1"></div>
              <div className="h-4 bg-gray-300 rounded w-24"></div>
            </div>
            <div className="flex items-center">
              <div className="h-4 w-4 bg-gray-300 rounded mr-1"></div>
              <div className="h-4 bg-gray-300 rounded w-24"></div>
            </div>
          </div>
        </div>
        
        <div className="ml-4 flex-shrink-0">
          <div className="h-5 w-5 bg-gray-300 rounded"></div>
        </div>
      </div>
    </div>
  );
};

// Message skeleton for chat
export const MessageSkeleton: React.FC<{ isUser?: boolean }> = ({ isUser = false }) => {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-pulse`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
        isUser ? 'bg-blue-100' : 'bg-gray-100'
      }`}>
        <div className="space-y-2">
          <div className="h-4 bg-gray-300 rounded w-full"></div>
          <div className="h-4 bg-gray-300 rounded w-3/4"></div>
        </div>
        <div className="mt-2">
          <div className="h-3 bg-gray-300 rounded w-16"></div>
        </div>
      </div>
    </div>
  );
};

export default SkeletonLoader;