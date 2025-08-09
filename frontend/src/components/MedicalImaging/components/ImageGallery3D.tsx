import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence, PanInfo } from 'framer-motion';
import { ChevronLeft, ChevronRight, X, Maximize2, RotateCw } from 'lucide-react';

interface Image {
  id: string;
  url: string;
  title: string;
  description?: string;
  metadata?: Record<string, any>;
}

interface ImageGallery3DProps {
  images: Image[];
  onImageSelect?: (image: Image) => void;
  autoRotate?: boolean;
  rotationSpeed?: number;
}

export const ImageGallery3D: React.FC<ImageGallery3DProps> = ({
  images,
  onImageSelect,
  autoRotate = false,
  rotationSpeed = 3000
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState<Image | null>(null);
  const [rotation, setRotation] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const autoRotateRef = useRef<NodeJS.Timeout | null>(null);

  // Calculate positions for 3D carousel
  const calculatePosition = (index: number) => {
    const totalImages = images.length;
    const angle = (360 / totalImages) * index + rotation;
    const radius = 250;
    const x = Math.sin((angle * Math.PI) / 180) * radius;
    const z = Math.cos((angle * Math.PI) / 180) * radius;
    const scale = (z + radius) / (radius * 2);
    const opacity = scale > 0.5 ? 1 : 0.3;
    
    return { x, z, scale, opacity, angle };
  };

  // Auto-rotation
  useEffect(() => {
    if (autoRotate && !isDragging) {
      autoRotateRef.current = setInterval(() => {
        setRotation(prev => prev - 360 / images.length);
      }, rotationSpeed);
    } else {
      if (autoRotateRef.current) {
        clearInterval(autoRotateRef.current);
      }
    }

    return () => {
      if (autoRotateRef.current) {
        clearInterval(autoRotateRef.current);
      }
    };
  }, [autoRotate, isDragging, images.length, rotationSpeed]);

  // Handle drag gestures
  const handleDrag = (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const dragX = info.offset.x;
    const sensitivity = 0.5;
    setRotation(prev => prev + dragX * sensitivity);
  };

  // Navigate carousel
  const navigate = (direction: 'prev' | 'next') => {
    const step = 360 / images.length;
    setRotation(prev => prev + (direction === 'next' ? -step : step));
    setCurrentIndex(prev => 
      direction === 'next' 
        ? (prev + 1) % images.length 
        : (prev - 1 + images.length) % images.length
    );
  };

  // Open lightbox
  const openLightbox = (image: Image) => {
    setSelectedImage(image);
    setIsLightboxOpen(true);
    if (onImageSelect) {
      onImageSelect(image);
    }
  };

  // Touch gesture support
  const handleTouchStart = (e: React.TouchEvent) => {
    setIsDragging(true);
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    setIsDragging(false);
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="relative w-full h-[600px] bg-gradient-to-b from-gray-900 to-black rounded-xl overflow-hidden"
      >
        {/* 3D Carousel Container */}
        <div
          ref={containerRef}
          className="absolute inset-0 flex items-center justify-center perspective-1000"
          style={{ perspective: '1000px' }}
        >
          <motion.div
            className="relative w-full h-full"
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.2}
            onDrag={handleDrag}
            onDragStart={() => setIsDragging(true)}
            onDragEnd={() => setIsDragging(false)}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            style={{ transformStyle: 'preserve-3d' }}
          >
            {images.map((image, index) => {
              const { x, z, scale, opacity, angle } = calculatePosition(index);
              const isActive = Math.abs(angle % 360) < 30;
              
              return (
                <motion.div
                  key={image.id}
                  className="absolute top-1/2 left-1/2 cursor-pointer"
                  style={{
                    transform: `translate(-50%, -50%) translateX(${x}px) translateZ(${z}px) scale(${scale})`,
                    opacity,
                    zIndex: Math.round(z),
                    transformStyle: 'preserve-3d'
                  }}
                  animate={{
                    rotateY: -angle,
                    transition: { duration: 0.5, ease: 'easeInOut' }
                  }}
                  whileHover={{ scale: scale * 1.05 }}
                  onClick={() => openLightbox(image)}
                >
                  <div className="relative w-64 h-80 bg-gray-800 rounded-lg overflow-hidden shadow-2xl">
                    <img
                      src={image.url}
                      alt={image.title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                    <div className={`absolute inset-0 bg-gradient-to-t from-black/80 to-transparent transition-opacity ${
                      isActive ? 'opacity-100' : 'opacity-0'
                    }`}>
                      <div className="absolute bottom-0 left-0 right-0 p-4">
                        <h3 className="text-white font-semibold text-lg">{image.title}</h3>
                        {image.description && (
                          <p className="text-gray-300 text-sm mt-1 line-clamp-2">{image.description}</p>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>

        {/* Navigation Controls */}
        <button
          onClick={() => navigate('prev')}
          className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-gray-800/80 hover:bg-gray-700/80 rounded-full backdrop-blur-sm transition-all z-10"
        >
          <ChevronLeft className="w-6 h-6 text-white" />
        </button>
        <button
          onClick={() => navigate('next')}
          className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-gray-800/80 hover:bg-gray-700/80 rounded-full backdrop-blur-sm transition-all z-10"
        >
          <ChevronRight className="w-6 h-6 text-white" />
        </button>

        {/* Auto-rotate toggle */}
        <button
          onClick={() => setIsDragging(!autoRotate)}
          className={`absolute top-4 right-4 p-2 rounded-lg transition-all z-10 ${
            autoRotate ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-800/80 hover:bg-gray-700/80'
          }`}
        >
          <RotateCw className={`w-5 h-5 text-white ${autoRotate ? 'animate-spin' : ''}`} />
        </button>

        {/* Indicator dots */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex space-x-2 z-10">
          {images.map((_, index) => (
            <button
              key={index}
              onClick={() => {
                const targetRotation = -(360 / images.length) * index;
                setRotation(targetRotation);
                setCurrentIndex(index);
              }}
              className={`w-2 h-2 rounded-full transition-all ${
                index === currentIndex ? 'bg-white w-8' : 'bg-white/40'
              }`}
            />
          ))}
        </div>
      </motion.div>

      {/* Lightbox */}
      <AnimatePresence>
        {isLightboxOpen && selectedImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/95 backdrop-blur-lg z-50 flex items-center justify-center p-4"
            onClick={() => setIsLightboxOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="relative max-w-6xl max-h-[90vh] bg-gray-900 rounded-xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close button */}
              <button
                onClick={() => setIsLightboxOpen(false)}
                className="absolute top-4 right-4 p-2 bg-gray-800/80 hover:bg-gray-700/80 rounded-full backdrop-blur-sm transition-all z-10"
              >
                <X className="w-6 h-6 text-white" />
              </button>

              {/* Image */}
              <div className="relative">
                <img
                  src={selectedImage.url}
                  alt={selectedImage.title}
                  className="max-w-full max-h-[70vh] object-contain"
                />
              </div>

              {/* Image info */}
              <div className="p-6 bg-gray-900">
                <h2 className="text-2xl font-bold text-white mb-2">{selectedImage.title}</h2>
                {selectedImage.description && (
                  <p className="text-gray-300 mb-4">{selectedImage.description}</p>
                )}
                {selectedImage.metadata && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(selectedImage.metadata).map(([key, value]) => (
                      <div key={key} className="bg-gray-800 rounded-lg p-3">
                        <p className="text-xs text-gray-400 uppercase">{key}</p>
                        <p className="text-sm text-white font-medium mt-1">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ImageGallery3D;