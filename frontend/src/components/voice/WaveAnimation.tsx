import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface WaveAnimationProps {
  isActive: boolean;
  state: 'idle' | 'listening' | 'processing' | 'responding';
  text?: string;
}

const WaveAnimation: React.FC<WaveAnimationProps> = ({ isActive, state, text }) => {
  const getStateText = () => {
    switch (state) {
      case 'listening':
        return text || 'Listening...';
      case 'processing':
        return text || 'Processing...';
      case 'responding':
        return text || 'Speaking...';
      default:
        return text || '';
    }
  };

  const getWaveConfig = () => {
    switch (state) {
      case 'listening':
        return {
          colors: ['rgba(255, 255, 255, 0.9)', 'rgba(255, 255, 255, 0.7)', 'rgba(255, 255, 255, 0.5)'],
          speed: 2,
          amplitude: 30,
          frequency: 0.5,
        };
      case 'processing':
        return {
          colors: ['rgba(255, 255, 255, 0.8)', 'rgba(200, 200, 255, 0.6)', 'rgba(150, 150, 255, 0.4)'],
          speed: 3,
          amplitude: 40,
          frequency: 0.7,
        };
      case 'responding':
        return {
          colors: ['rgba(255, 255, 255, 1)', 'rgba(255, 230, 230, 0.8)', 'rgba(255, 200, 200, 0.6)'],
          speed: 2.5,
          amplitude: 50,
          frequency: 0.6,
        };
      default:
        return {
          colors: ['rgba(255, 255, 255, 0.3)', 'rgba(255, 255, 255, 0.2)', 'rgba(255, 255, 255, 0.1)'],
          speed: 1,
          amplitude: 10,
          frequency: 0.3,
        };
    }
  };

  const config = getWaveConfig();
  const displayText = getStateText();

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
      {/* Dark/Blood background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-red-950 via-black to-purple-950 opacity-90" />
      
      {/* Ocean wave effects */}
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox="0 0 800 400"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Flowing light gradient */}
          <linearGradient id="flowingLight" x1="0%" y1="0%" x2="100%" y2="0%">
            <animate attributeName="x1" values="0%;100%;0%" dur={`${4 / config.speed}s`} repeatCount="indefinite" />
            <stop offset="0%" stopColor={config.colors[0]} stopOpacity="0" />
            <stop offset="50%" stopColor={config.colors[1]} stopOpacity="1" />
            <stop offset="100%" stopColor={config.colors[2]} stopOpacity="0" />
          </linearGradient>
          
          {/* Glow filter */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Multiple wave layers for ocean effect */}
        {[0, 1, 2, 3, 4].map((index) => (
          <motion.path
            key={`wave-${index}`}
            fill="none"
            stroke="url(#flowingLight)"
            strokeWidth={isActive ? 3 - index * 0.5 : 1}
            strokeOpacity={isActive ? 0.8 - index * 0.15 : 0.2}
            filter="url(#glow)"
            initial={{ d: `M 0,200 Q 200,200 400,200 T 800,200` }}
            animate={{
              d: isActive ? [
                `M 0,200 Q 200,${200 - config.amplitude * (1 + index * 0.2)} 400,200 T 800,200`,
                `M 0,200 Q 200,${200 + config.amplitude * (1 + index * 0.2)} 400,200 T 800,200`,
                `M 0,200 Q 200,${200 - config.amplitude * (1 + index * 0.2)} 400,200 T 800,200`,
              ] : `M 0,200 Q 200,200 400,200 T 800,200`,
            }}
            transition={{
              duration: (2 + index * 0.3) / config.speed,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: index * 0.1,
            }}
          />
        ))}
        
        {/* Additional flowing particles */}
        {isActive && [...Array(5)].map((_, i) => (
          <motion.circle
            key={`particle-${i}`}
            r="2"
            fill={config.colors[0]}
            filter="url(#glow)"
            initial={{ x: -10, y: 200 }}
            animate={{
              x: [0, 800],
              y: [
                200,
                200 - config.amplitude * Math.sin(i),
                200 + config.amplitude * Math.cos(i),
                200,
              ],
            }}
            transition={{
              duration: (4 + i) / config.speed,
              repeat: Infinity,
              ease: 'linear',
              delay: i * 0.5,
            }}
          />
        ))}
      </svg>

      {/* Centered text with wave zoom effect */}
      <AnimatePresence mode="wait">
        {displayText && (
          <motion.div
            key={displayText}
            className="relative z-10 text-center"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.3 }}
          >
            <motion.h2
              className="text-4xl md:text-6xl font-bold text-white drop-shadow-2xl"
              animate={isActive ? {
                scale: [1, 1.05, 1],
                textShadow: [
                  '0 0 20px rgba(255,255,255,0.5)',
                  '0 0 40px rgba(255,255,255,0.8)',
                  '0 0 20px rgba(255,255,255,0.5)',
                ],
              } : {}}
              transition={{
                duration: 2 / config.speed,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            >
              {displayText}
            </motion.h2>
            
            {/* Subtitle wave indicator */}
            <motion.div
              className="mt-4 flex justify-center space-x-2"
              animate={isActive ? {
                opacity: [0.5, 1, 0.5],
              } : {}}
              transition={{
                duration: 1.5 / config.speed,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            >
              {[0, 1, 2, 3, 4].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-8 bg-white rounded-full"
                  animate={isActive ? {
                    scaleY: [0.3, 1, 0.3],
                    opacity: [0.3, 1, 0.3],
                  } : {}}
                  transition={{
                    duration: 1 / config.speed,
                    repeat: Infinity,
                    ease: 'easeInOut',
                    delay: i * 0.1,
                  }}
                />
              ))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Ambient light pulses */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        animate={isActive ? {
          background: [
            'radial-gradient(circle at 50% 50%, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 100%)',
            'radial-gradient(circle at 50% 50%, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%)',
            'radial-gradient(circle at 50% 50%, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 100%)',
          ],
        } : {}}
        transition={{
          duration: 3 / config.speed,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  );
};

export default WaveAnimation;