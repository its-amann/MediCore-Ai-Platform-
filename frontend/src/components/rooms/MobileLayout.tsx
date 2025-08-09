import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface MobileLayoutProps {
  children: React.ReactNode;
  sidePanel?: React.ReactNode;
  showSidePanel: boolean;
  onCloseSidePanel: () => void;
  sidePanelTitle?: string;
}

const MobileLayout: React.FC<MobileLayoutProps> = ({
  children,
  sidePanel,
  showSidePanel,
  onCloseSidePanel,
  sidePanelTitle = 'Panel'
}) => {
  return (
    <div className="relative h-full">
      {/* Main content */}
      <div className="h-full">
        {children}
      </div>

      {/* Side panel overlay */}
      <AnimatePresence>
        {showSidePanel && (
          <>
            {/* Background overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-50 z-40"
              onClick={onCloseSidePanel}
            />

            {/* Side panel */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 right-0 w-full max-w-sm bg-white shadow-xl z-50"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">
                  {sidePanelTitle}
                </h2>
                <button
                  onClick={onCloseSidePanel}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Content */}
              <div className="h-full overflow-y-auto pb-16">
                {sidePanel}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MobileLayout;