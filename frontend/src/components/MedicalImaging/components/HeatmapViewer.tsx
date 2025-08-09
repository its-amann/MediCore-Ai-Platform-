import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Download, ZoomIn, ZoomOut, Move, Square, Maximize2 } from 'lucide-react';

interface HeatmapViewerProps {
  data: number[][];
  width?: number;
  height?: number;
  colorScale?: string[];
  onRegionSelect?: (region: { x: number; y: number; width: number; height: number }) => void;
}

export const HeatmapViewer: React.FC<HeatmapViewerProps> = ({
  data,
  width = 600,
  height = 400,
  colorScale = ['#00008B', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8C00', '#FF0000', '#8B0000'],
  onRegionSelect
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [intensity, setIntensity] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [isSelecting, setIsSelecting] = useState(false);
  const [selection, setSelection] = useState<{ start: { x: number; y: number }; end: { x: number; y: number } } | null>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Generate color from value
  const getColorFromValue = useCallback((value: number) => {
    const normalizedValue = Math.max(0, Math.min(1, value * intensity));
    const index = Math.floor(normalizedValue * (colorScale.length - 1));
    return colorScale[index];
  }, [colorScale, intensity]);

  // Draw heatmap
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data || data.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Calculate cell dimensions
    const cellWidth = canvas.width / data[0].length;
    const cellHeight = canvas.height / data.length;

    // Draw heatmap cells
    for (let i = 0; i < data.length; i++) {
      for (let j = 0; j < data[i].length; j++) {
        const value = data[i][j];
        ctx.fillStyle = getColorFromValue(value);
        ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth, cellHeight);
      }
    }

    // Draw selection if active
    if (selection) {
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      const x = Math.min(selection.start.x, selection.end.x);
      const y = Math.min(selection.start.y, selection.end.y);
      const w = Math.abs(selection.end.x - selection.start.x);
      const h = Math.abs(selection.end.y - selection.start.y);
      ctx.strokeRect(x, y, w, h);
    }
  }, [data, intensity, selection, getColorFromValue]);

  // Handle mouse events
  const handleMouseDown = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = (e.clientX - rect.left) / zoom - pan.x;
    const y = (e.clientY - rect.top) / zoom - pan.y;

    if (isSelecting) {
      setSelection({ start: { x, y }, end: { x, y } });
    } else {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x * zoom, y: e.clientY - pan.y * zoom });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: (e.clientX - dragStart.x) / zoom,
        y: (e.clientY - dragStart.y) / zoom
      });
    } else if (isSelecting && selection) {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      
      const x = (e.clientX - rect.left) / zoom - pan.x;
      const y = (e.clientY - rect.top) / zoom - pan.y;
      setSelection({ ...selection, end: { x, y } });
    }
  };

  const handleMouseUp = () => {
    if (isSelecting && selection && onRegionSelect) {
      const region = {
        x: Math.min(selection.start.x, selection.end.x),
        y: Math.min(selection.start.y, selection.end.y),
        width: Math.abs(selection.end.x - selection.start.x),
        height: Math.abs(selection.end.y - selection.start.y)
      };
      onRegionSelect(region);
    }
    setIsDragging(false);
    setIsSelecting(false);
  };

  // Export functionality
  const handleExport = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = `heatmap_${new Date().getTime()}.png`;
    link.href = canvas.toDataURL();
    link.click();
  };

  // Zoom controls
  const handleZoomIn = () => setZoom(prev => Math.min(prev * 1.2, 5));
  const handleZoomOut = () => setZoom(prev => Math.max(prev / 1.2, 0.5));
  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-gray-900 rounded-xl p-6 shadow-2xl"
    >
      {/* Controls */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center space-x-4">
          <button
            onClick={handleZoomIn}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-5 h-5 text-gray-300" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-5 h-5 text-gray-300" />
          </button>
          <button
            onClick={handleResetView}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="Reset View"
          >
            <Maximize2 className="w-5 h-5 text-gray-300" />
          </button>
          <button
            onClick={() => setIsSelecting(!isSelecting)}
            className={`p-2 rounded-lg transition-colors ${
              isSelecting ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-800 hover:bg-gray-700'
            }`}
            title="Select Region"
          >
            <Square className="w-5 h-5 text-gray-300" />
          </button>
          <button
            onClick={handleExport}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="Export"
          >
            <Download className="w-5 h-5 text-gray-300" />
          </button>
        </div>
        
        {/* Intensity Slider */}
        <div className="flex items-center space-x-3">
          <label className="text-sm text-gray-400">Intensity:</label>
          <input
            type="range"
            min="0.1"
            max="2"
            step="0.1"
            value={intensity}
            onChange={(e) => setIntensity(parseFloat(e.target.value))}
            className="w-32"
          />
          <span className="text-sm text-gray-400 w-12">{intensity.toFixed(1)}x</span>
        </div>
      </div>

      {/* Heatmap Canvas Container */}
      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-lg bg-gray-800"
        style={{ width, height }}
      >
        <motion.div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'top left',
            cursor: isDragging ? 'grabbing' : isSelecting ? 'crosshair' : 'grab'
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            className="block"
          />
        </motion.div>
      </div>

      {/* Color Scale Legend */}
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-gray-400">Low</span>
        <div className="flex-1 mx-4 h-6 rounded flex overflow-hidden">
          {colorScale.map((color, index) => (
            <div
              key={index}
              className="flex-1"
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
        <span className="text-xs text-gray-400">High</span>
      </div>
    </motion.div>
  );
};

export default HeatmapViewer;