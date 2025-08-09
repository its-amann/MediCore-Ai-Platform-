import React from 'react';
import { motion } from 'framer-motion';

const LoadingRoom: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"
        />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Joining room...
        </h2>
        <p className="text-gray-600">
          Setting up your connection
        </p>
      </div>
    </div>
  );
};

export default LoadingRoom;