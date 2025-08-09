import React from 'react';
import { motion } from 'framer-motion';

interface AnalyzingCasesProps {
  message?: string;
  subMessage?: string;
  showProgress?: boolean;
  progress?: number;
}

const AnalyzingCases: React.FC<AnalyzingCasesProps> = ({
  message = "Analyzing past cases...",
  subMessage = "Finding similar medical patterns to assist with your consultation",
  showProgress = true,
  progress = 0
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8">
      {/* Medical Case Icon Animation */}
      <div className="relative mb-6">
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute inset-0 bg-blue-400 rounded-full blur-xl"
        />
        <div className="relative bg-white p-4 rounded-full shadow-lg">
          <svg
            className="w-12 h-12 text-blue-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12.5 3v5.25a.75.75 0 00.75.75H18.5"
            />
          </svg>
        </div>
      </div>

      {/* Loading Text */}
      <motion.h3
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-xl font-semibold text-gray-800 mb-2"
      >
        {message}
      </motion.h3>

      {/* Sub Message */}
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="text-sm text-gray-600 text-center max-w-md mb-6"
      >
        {subMessage}
      </motion.p>

      {/* Progress Indicator */}
      {showProgress && (
        <div className="w-full max-w-xs">
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <motion.div
              className="bg-blue-600 h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: progress ? `${progress}%` : '75%' }}
              transition={{
                duration: progress ? 0.5 : 3,
                ease: "easeInOut",
                repeat: progress ? 0 : Infinity
              }}
            />
          </div>

          {/* Loading Dots */}
          <div className="flex justify-center space-x-2">
            {[0, 1, 2].map((index) => (
              <motion.div
                key={index}
                className="w-2 h-2 bg-blue-600 rounded-full"
                animate={{
                  y: [0, -10, 0],
                  opacity: [0.5, 1, 0.5]
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  delay: index * 0.2,
                  ease: "easeInOut"
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Additional Info */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="mt-6 text-xs text-gray-500 text-center"
      >
        This may take a few moments while we review your medical history
      </motion.div>
    </div>
  );
};

export default AnalyzingCases;