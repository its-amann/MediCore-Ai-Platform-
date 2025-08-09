"""
Medical Image Processor Service
Handles all image processing including format conversion, quality assessment, enhancement, and heatmap generation
"""

import logging
import io
import base64
import uuid
import os
from typing import Dict, Any, Optional, Tuple, Union, List
from datetime import datetime
import tempfile

import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter
import pydicom
import nibabel as nib
from scipy import ndimage
from skimage import exposure, filters, morphology

from app.microservices.medical_imaging.models.imaging_models import ImageType, HeatmapData

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Complete image processor service for medical images
    Handles DICOM, NIFTI, standard formats, quality assessment, and enhancement
    """
    
    def __init__(self):
        """Initialize the image processor"""
        self.supported_formats = {
            'jpg': ImageType.OTHER,
            'jpeg': ImageType.OTHER,
            'png': ImageType.OTHER,
            'tiff': ImageType.OTHER,
            'tif': ImageType.OTHER,
            'bmp': ImageType.OTHER,
            'dcm': ImageType.CT,  # Default for DICOM
            'dicom': ImageType.CT,
            'nii': ImageType.MRI,  # Default for NIFTI
            'nii.gz': ImageType.MRI
        }
        
        # Standard target size for analysis
        self.target_size = (1024, 1024)
        
        # Quality thresholds
        self.quality_thresholds = {
            'contrast': 0.3,
            'brightness': 0.4,
            'sharpness': 0.5,
            'noise': 0.7
        }
        
        logger.info("Image processor initialized with all features")
    
    async def process_medical_image(
        self, 
        file_data: bytes, 
        filename: str,
        enhance: bool = True
    ) -> Dict[str, Any]:
        """
        Process a medical image file with optional enhancement
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            enhance: Whether to apply enhancement
            
        Returns:
            Processed image data with metadata
        """
        try:
            # Determine file format
            file_ext = self._get_file_extension(filename)
            
            # Process based on format
            if file_ext in ['dcm', 'dicom']:
                return await self._process_dicom(file_data, filename, enhance)
            elif file_ext in ['nii', 'nii.gz']:
                return await self._process_nifti(file_data, filename, enhance)
            else:
                return await self._process_standard_image(file_data, filename, enhance)
        
        except Exception as e:
            logger.error(f"Error processing image {filename}: {e}")
            raise
    
    async def _process_dicom(
        self, 
        file_data: bytes, 
        filename: str,
        enhance: bool
    ) -> Dict[str, Any]:
        """Process DICOM images"""
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as tmp_file:
                tmp_file.write(file_data)
                tmp_path = tmp_file.name
            
            # Read DICOM
            ds = pydicom.dcmread(tmp_path)
            
            # Extract metadata
            metadata = {
                'patient_name': str(ds.get('PatientName', 'Unknown')),
                'patient_id': str(ds.get('PatientID', 'Unknown')),
                'study_date': str(ds.get('StudyDate', 'Unknown')),
                'modality': str(ds.get('Modality', 'Unknown')),
                'body_part': str(ds.get('BodyPartExamined', 'Unknown')),
                'slice_thickness': float(ds.get('SliceThickness', 0)),
                'pixel_spacing': list(ds.get('PixelSpacing', [1.0, 1.0]))
            }
            
            # Get pixel array
            pixel_array = ds.pixel_array
            
            # Normalize to 8-bit
            pixel_array = self._normalize_pixel_array(pixel_array)
            
            # Convert to PIL Image
            image = Image.fromarray(pixel_array)
            
            # Clean up
            os.unlink(tmp_path)
            
            # Determine image type from modality
            image_type = self._get_image_type_from_modality(metadata['modality'])
            
            # Process image
            return await self._process_image_common(
                image, 
                filename, 
                image_type, 
                metadata,
                enhance
            )
        
        except Exception as e:
            logger.error(f"Error processing DICOM: {e}")
            raise
    
    async def _process_nifti(
        self, 
        file_data: bytes, 
        filename: str,
        enhance: bool
    ) -> Dict[str, Any]:
        """Process NIFTI images"""
        try:
            # Save to temporary file
            suffix = '.nii.gz' if filename.endswith('.gz') else '.nii'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                tmp_file.write(file_data)
                tmp_path = tmp_file.name
            
            # Load NIFTI
            nifti_img = nib.load(tmp_path)
            data = nifti_img.get_fdata()
            
            # Extract metadata
            header = nifti_img.header
            metadata = {
                'dimensions': list(data.shape),
                'voxel_sizes': list(header.get_zooms()),
                'data_type': str(header.get_data_dtype()),
                'units': str(header.get_xyzt_units())
            }
            
            # Get middle slice for 2D processing
            if len(data.shape) == 3:
                middle_slice = data.shape[2] // 2
                slice_data = data[:, :, middle_slice]
            else:
                slice_data = data
            
            # Normalize and convert to PIL Image
            slice_data = self._normalize_pixel_array(slice_data)
            image = Image.fromarray(slice_data)
            
            # Clean up
            os.unlink(tmp_path)
            
            # Process image
            return await self._process_image_common(
                image, 
                filename, 
                ImageType.MRI, 
                metadata,
                enhance
            )
        
        except Exception as e:
            logger.error(f"Error processing NIFTI: {e}")
            raise
    
    async def _process_standard_image(
        self, 
        file_data: bytes, 
        filename: str,
        enhance: bool
    ) -> Dict[str, Any]:
        """Process standard image formats (JPEG, PNG, etc.)"""
        try:
            # Load image
            image = Image.open(io.BytesIO(file_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Basic metadata
            metadata = {
                'format': image.format,
                'size': image.size,
                'mode': image.mode
            }
            
            # Determine image type
            file_ext = self._get_file_extension(filename)
            image_type = self.supported_formats.get(file_ext, ImageType.OTHER)
            
            # Process image
            return await self._process_image_common(
                image, 
                filename, 
                image_type, 
                metadata,
                enhance
            )
        
        except Exception as e:
            logger.error(f"Error processing standard image: {e}")
            raise
    
    async def _process_image_common(
        self,
        image: Image.Image,
        filename: str,
        image_type: ImageType,
        metadata: Dict[str, Any],
        enhance: bool
    ) -> Dict[str, Any]:
        """Common processing for all image types"""
        
        # Quality assessment
        quality_metrics = await self.assess_image_quality(image)
        
        # Apply enhancement if requested and needed
        if enhance and quality_metrics['overall_quality'] < 0.7:
            enhanced_image = await self.enhance_image(image, quality_metrics)
            quality_after = await self.assess_image_quality(enhanced_image)
        else:
            enhanced_image = image
            quality_after = quality_metrics
        
        # Resize to standard size
        resized_image = enhanced_image.resize(self.target_size, Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffered = io.BytesIO()
        resized_image.save(buffered, format='PNG')
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Convert to numpy array for further processing
        image_array = np.array(resized_image)
        
        return {
            'base64_image': base64_image,
            'image_array': image_array,
            'image_type': image_type,
            'original_size': image.size,
            'processed_size': self.target_size,
            'metadata': metadata,
            'quality_metrics': quality_metrics,
            'quality_after_enhancement': quality_after if enhance else None,
            'enhanced': enhance and quality_metrics['overall_quality'] < 0.7
        }
    
    async def assess_image_quality(self, image: Image.Image) -> Dict[str, float]:
        """
        Assess image quality metrics
        
        Returns:
            Dictionary with quality scores (0-1)
        """
        # Convert to numpy array
        img_array = np.array(image.convert('L'))  # Convert to grayscale
        
        # Contrast assessment using standard deviation
        contrast_score = np.std(img_array) / 127.5  # Normalize to 0-1
        
        # Brightness assessment
        mean_brightness = np.mean(img_array) / 255
        brightness_score = 1 - abs(mean_brightness - 0.5) * 2  # Best at 0.5
        
        # Sharpness assessment using Laplacian
        laplacian = cv2.Laplacian(img_array, cv2.CV_64F)
        sharpness_score = min(np.var(laplacian) / 1000, 1.0)  # Normalize
        
        # Noise assessment using high-frequency content
        noise_score = 1 - min(self._estimate_noise(img_array) / 50, 1.0)
        
        # Overall quality score
        overall_quality = (
            contrast_score * 0.3 +
            brightness_score * 0.2 +
            sharpness_score * 0.3 +
            noise_score * 0.2
        )
        
        return {
            'contrast': float(contrast_score),
            'brightness': float(brightness_score),
            'sharpness': float(sharpness_score),
            'noise': float(noise_score),
            'overall_quality': float(overall_quality)
        }
    
    async def enhance_image(
        self, 
        image: Image.Image, 
        quality_metrics: Dict[str, float]
    ) -> Image.Image:
        """
        Enhance image based on quality metrics
        
        Args:
            image: Input image
            quality_metrics: Quality assessment results
            
        Returns:
            Enhanced image
        """
        enhanced = image.copy()
        
        # Enhance contrast if needed
        if quality_metrics['contrast'] < self.quality_thresholds['contrast']:
            enhancer = ImageEnhance.Contrast(enhanced)
            factor = 1.5 if quality_metrics['contrast'] < 0.2 else 1.3
            enhanced = enhancer.enhance(factor)
        
        # Adjust brightness if needed
        if quality_metrics['brightness'] < self.quality_thresholds['brightness']:
            enhancer = ImageEnhance.Brightness(enhanced)
            current_brightness = quality_metrics['brightness']
            if current_brightness < 0.3:
                factor = 1.3
            elif current_brightness > 0.7:
                factor = 0.8
            else:
                factor = 1.1
            enhanced = enhancer.enhance(factor)
        
        # Enhance sharpness if needed
        if quality_metrics['sharpness'] < self.quality_thresholds['sharpness']:
            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(1.5)
        
        # Reduce noise if needed
        if quality_metrics['noise'] < self.quality_thresholds['noise']:
            # Apply median filter for noise reduction
            enhanced_array = np.array(enhanced)
            filtered = cv2.medianBlur(enhanced_array, 3)
            enhanced = Image.fromarray(filtered)
        
        # Apply CLAHE for better local contrast
        enhanced_array = np.array(enhanced.convert('L'))
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_array = clahe.apply(enhanced_array)
        
        # Convert back to RGB
        enhanced = Image.fromarray(cv2.cvtColor(enhanced_array, cv2.COLOR_GRAY2RGB))
        
        return enhanced
    
    async def generate_heatmap(
        self,
        image_array: np.ndarray,
        findings: List[Dict[str, Any]] = None,
        attention_weights: Optional[np.ndarray] = None
    ) -> HeatmapData:
        """
        Generate heatmap overlays for medical images
        
        Args:
            image_array: Input image as numpy array
            findings: List of findings with locations
            attention_weights: Optional attention weights from AI model
            
        Returns:
            HeatmapData with various visualizations
        """
        # Ensure image is in correct format
        if len(image_array.shape) == 2:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        
        # Generate attention map
        if attention_weights is None:
            # Generate synthetic attention based on findings
            attention_map = self._generate_attention_from_findings(
                image_array.shape[:2], 
                findings
            )
        else:
            attention_map = cv2.resize(
                attention_weights, 
                (image_array.shape[1], image_array.shape[0])
            )
        
        # Normalize attention map
        attention_map = (attention_map - attention_map.min()) / (attention_map.max() - attention_map.min() + 1e-8)
        
        # Create heatmap overlay
        heatmap = cv2.applyColorMap((attention_map * 255).astype(np.uint8), cv2.COLORMAP_JET)
        
        # Create overlay with transparency
        overlay = cv2.addWeighted(image_array, 0.7, heatmap, 0.3, 0)
        
        # Convert to base64
        _, buffer = cv2.imencode('.png', image_array)
        original_base64 = base64.b64encode(buffer).decode('utf-8')
        
        _, buffer = cv2.imencode('.png', overlay)
        overlay_base64 = base64.b64encode(buffer).decode('utf-8')
        
        _, buffer = cv2.imencode('.png', heatmap)
        heatmap_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Identify attention regions
        attention_regions = self._extract_attention_regions(attention_map, findings)
        
        return HeatmapData(
            original_image=original_base64,
            heatmap_overlay=overlay_base64,
            heatmap_only=heatmap_base64,
            attention_regions=attention_regions
        )
    
    def _normalize_pixel_array(self, pixel_array: np.ndarray) -> np.ndarray:
        """Normalize pixel array to 8-bit grayscale"""
        # Handle different data types
        if pixel_array.dtype != np.uint8:
            # Normalize to 0-255
            min_val = pixel_array.min()
            max_val = pixel_array.max()
            if max_val > min_val:
                pixel_array = ((pixel_array - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            else:
                pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)
        
        return pixel_array
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        if filename.endswith('.nii.gz'):
            return 'nii.gz'
        return filename.split('.')[-1].lower()
    
    def _get_image_type_from_modality(self, modality: str) -> ImageType:
        """Map DICOM modality to ImageType"""
        modality_map = {
            'CT': ImageType.CT,
            'MR': ImageType.MRI,
            'CR': ImageType.XRAY,
            'DX': ImageType.XRAY,
            'US': ImageType.ULTRASOUND,
            'PT': ImageType.PET,
            'NM': ImageType.PET
        }
        return modality_map.get(modality.upper(), ImageType.OTHER)
    
    def _estimate_noise(self, image: np.ndarray) -> float:
        """Estimate noise level in image"""
        # Use Laplacian to estimate noise
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        return np.std(laplacian)
    
    def _generate_attention_from_findings(
        self, 
        shape: Tuple[int, int], 
        findings: List[Dict[str, Any]]
    ) -> np.ndarray:
        """Generate attention map from findings"""
        attention_map = np.zeros(shape, dtype=np.float32)
        
        if not findings:
            # Generate center-focused attention
            center = (shape[1] // 2, shape[0] // 2)
            radius = min(shape) // 3
            y, x = np.ogrid[:shape[0], :shape[1]]
            mask = (x - center[0])**2 + (y - center[1])**2 <= radius**2
            attention_map[mask] = 1.0
            attention_map = filters.gaussian(attention_map, sigma=30)
        else:
            # Generate attention from findings locations
            for finding in findings:
                if 'location' in finding:
                    loc = finding['location']
                    x, y = int(loc.get('x', shape[1]//2)), int(loc.get('y', shape[0]//2))
                    # Create Gaussian blob at location
                    blob = np.zeros(shape)
                    blob[y, x] = 1.0
                    blob = filters.gaussian(blob, sigma=50)
                    attention_map = np.maximum(attention_map, blob)
        
        return attention_map
    
    def _extract_attention_regions(
        self, 
        attention_map: np.ndarray,
        findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract regions of high attention"""
        regions = []
        
        # Threshold attention map
        threshold = 0.7 * attention_map.max()
        binary_map = attention_map > threshold
        
        # Find connected components
        labeled, num_features = ndimage.label(binary_map)
        
        for i in range(1, num_features + 1):
            region_mask = labeled == i
            y_coords, x_coords = np.where(region_mask)
            
            if len(y_coords) > 0:
                region = {
                    'id': str(uuid.uuid4()),
                    'center': {
                        'x': int(np.mean(x_coords)),
                        'y': int(np.mean(y_coords))
                    },
                    'bounds': {
                        'x_min': int(x_coords.min()),
                        'x_max': int(x_coords.max()),
                        'y_min': int(y_coords.min()),
                        'y_max': int(y_coords.max())
                    },
                    'confidence': float(attention_map[region_mask].mean())
                }
                
                # Match with findings if available
                if findings:
                    for finding in findings:
                        if 'location' in finding:
                            loc = finding['location']
                            if (region['bounds']['x_min'] <= loc['x'] <= region['bounds']['x_max'] and
                                region['bounds']['y_min'] <= loc['y'] <= region['bounds']['y_max']):
                                region['finding'] = finding.get('text', '')
                                break
                
                regions.append(region)
        
        return regions


# Backward compatibility aliases
ImageProcessorService = ImageProcessor
EnhancedImageProcessor = ImageProcessor
ImageQualityAssessment = ImageProcessor
MedicalFormatHandler = ImageProcessor


# Singleton instance getter
_processor_instance = None

def get_image_processor() -> ImageProcessor:
    """Get singleton instance of image processor"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = ImageProcessor()
    return _processor_instance