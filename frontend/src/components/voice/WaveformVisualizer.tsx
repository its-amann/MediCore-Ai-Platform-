import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface WaveformVisualizerProps {
  state: 'idle' | 'listening' | 'processing' | 'responding';
}

const WaveformVisualizer: React.FC<WaveformVisualizerProps> = ({ state }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    let time = 0;
    const animate = () => {
      time += 0.01;

      // Clear canvas
      ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);

      // Draw waveform based on state
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;
      const centerY = height / 2;

      ctx.lineWidth = 3;
      ctx.lineCap = 'round';

      // Create gradient based on state
      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      
      switch (state) {
        case 'listening':
          // Green waveform for listening
          gradient.addColorStop(0, '#10b981');
          gradient.addColorStop(0.5, '#34d399');
          gradient.addColorStop(1, '#6ee7b7');
          drawDynamicWaveform(ctx, width, centerY, time, 40, 3);
          break;
          
        case 'processing':
          // Blue swirling waves for processing
          gradient.addColorStop(0, '#3b82f6');
          gradient.addColorStop(0.5, '#60a5fa');
          gradient.addColorStop(1, '#93c5fd');
          drawSwirlWaveform(ctx, width, centerY, time, 30, 2);
          break;
          
        case 'responding':
          // Orange flowing waves for responding
          gradient.addColorStop(0, '#f97316');
          gradient.addColorStop(0.5, '#fb923c');
          gradient.addColorStop(1, '#fdba74');
          drawFlowingWaveform(ctx, width, centerY, time, 35, 2.5);
          break;
          
        default:
          // Subtle idle animation
          gradient.addColorStop(0, '#64748b');
          gradient.addColorStop(0.5, '#94a3b8');
          gradient.addColorStop(1, '#cbd5e1');
          drawIdleWaveform(ctx, width, centerY, time, 10, 1);
      }

      ctx.strokeStyle = gradient;

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [state]);

  // Draw dynamic waveform (listening state)
  const drawDynamicWaveform = (
    ctx: CanvasRenderingContext2D,
    width: number,
    centerY: number,
    time: number,
    amplitude: number,
    frequency: number
  ) => {
    ctx.beginPath();
    
    for (let x = 0; x < width; x++) {
      const t = x / width;
      const wave1 = Math.sin((t * frequency + time) * Math.PI * 2) * amplitude;
      const wave2 = Math.sin((t * frequency * 1.5 + time * 1.2) * Math.PI * 2) * amplitude * 0.5;
      const wave3 = Math.sin((t * frequency * 0.5 + time * 0.8) * Math.PI * 2) * amplitude * 0.3;
      
      const y = centerY + wave1 + wave2 + wave3;
      
      if (x === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    
    ctx.stroke();
  };

  // Draw swirling waveform (processing state)
  const drawSwirlWaveform = (
    ctx: CanvasRenderingContext2D,
    width: number,
    centerY: number,
    time: number,
    amplitude: number,
    frequency: number
  ) => {
    // Draw multiple overlapping waves
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.globalAlpha = 0.6 - i * 0.2;
      
      for (let x = 0; x < width; x++) {
        const t = x / width;
        const offset = i * 0.2;
        const wave = Math.sin((t * frequency + time + offset) * Math.PI * 2) * 
                    Math.sin(time * 0.5 + offset) * amplitude;
        const y = centerY + wave;
        
        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  };

  // Draw flowing waveform (responding state)
  const drawFlowingWaveform = (
    ctx: CanvasRenderingContext2D,
    width: number,
    centerY: number,
    time: number,
    amplitude: number,
    frequency: number
  ) => {
    ctx.beginPath();
    
    for (let x = 0; x < width; x++) {
      const t = x / width;
      const flow = Math.sin((t - time * 0.5) * Math.PI * 2) * amplitude;
      const modulation = Math.sin(time * 2) * 0.5 + 0.5;
      const y = centerY + flow * modulation;
      
      if (x === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    
    ctx.stroke();

    // Add secondary wave
    ctx.beginPath();
    ctx.globalAlpha = 0.5;
    
    for (let x = 0; x < width; x++) {
      const t = x / width;
      const flow = Math.sin((t - time * 0.5 + 0.5) * Math.PI * 2) * amplitude * 0.7;
      const modulation = Math.sin(time * 2 + Math.PI) * 0.5 + 0.5;
      const y = centerY + flow * modulation;
      
      if (x === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    
    ctx.stroke();
    ctx.globalAlpha = 1;
  };

  // Draw idle waveform
  const drawIdleWaveform = (
    ctx: CanvasRenderingContext2D,
    width: number,
    centerY: number,
    time: number,
    amplitude: number,
    frequency: number
  ) => {
    ctx.beginPath();
    ctx.globalAlpha = 0.3;
    
    for (let x = 0; x < width; x++) {
      const t = x / width;
      const wave = Math.sin((t * frequency + time * 0.5) * Math.PI * 2) * amplitude;
      const y = centerY + wave;
      
      if (x === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    
    ctx.stroke();
    ctx.globalAlpha = 1;
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full h-full relative"
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ background: 'transparent' }}
      />
    </motion.div>
  );
};

export default WaveformVisualizer;