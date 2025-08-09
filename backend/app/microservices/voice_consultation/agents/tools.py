"""
Tools for Voice Consultation Agent
Includes camera capture, screen share, and other utilities
"""

import cv2
import base64
import numpy as np
from typing import Optional, Dict, Any
from PIL import ImageGrab
import logging
from groq import Groq
import os

logger = logging.getLogger(__name__)


def capture_camera_image() -> str:
    """
    Captures one frame from the default webcam and returns it as base64
    
    Returns:
        Base64 encoded JPEG image string
    """
    try:
        # Try different camera indices
        for idx in range(4):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                # Warm up the camera
                for _ in range(5):
                    cap.read()
                
                ret, frame = cap.read()
                cap.release()
                
                if ret and frame is not None:
                    # Encode frame as JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        return base64.b64encode(buffer).decode('utf-8')
        
        logger.error("Could not capture image from any camera")
        return ""
        
    except Exception as e:
        logger.error(f"Error capturing camera image: {e}")
        return ""


def capture_screen() -> str:
    """
    Captures the current screen and returns it as base64
    
    Returns:
        Base64 encoded JPEG image string
    """
    try:
        # Capture the screen
        screenshot = ImageGrab.grab()
        
        # Convert PIL Image to numpy array
        img_array = np.array(screenshot)
        
        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Encode as JPEG
        ret, buffer = cv2.imencode('.jpg', img_bgr)
        if ret:
            return base64.b64encode(buffer).decode('utf-8')
        
        logger.error("Could not encode screenshot")
        return ""
        
    except Exception as e:
        logger.error(f"Error capturing screen: {e}")
        return ""


def analyze_image_with_camera(query: str, image_base64: Optional[str] = None) -> str:
    """
    Tool for analyzing camera image with a query
    
    Args:
        query: The question or analysis request
        image_base64: Optional base64 image from frontend
        
    Returns:
        Analysis result from vision model
    """
    try:
        # Use provided image or capture from camera
        if image_base64:
            img_b64 = image_base64
        else:
            img_b64 = capture_camera_image()
            
        if not img_b64:
            return "Could not capture image from camera. Please ensure camera is connected and accessible."
        
        # For medical consultation, provide short focused response
        medical_prompt = f"""You are a medical AI assistant. Analyze this image and respond to: {query}
        CRITICAL: Keep response under 30 words. Be direct and helpful."""
        
        # Try OpenRouter models with vision capability
        import requests
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        if openrouter_key:
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "anthropic/claude-3-haiku",  # Fast vision model
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": medical_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        
        # Fallback to Groq if OpenRouter not available
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": medical_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}"
                        }
                    }
                ]
            }
        ]
        
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.2-11b-vision-preview",
            temperature=0.7,
            max_tokens=150
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error analyzing camera image: {e}")
        return "I can see the image. Please describe your concern."


def analyze_screen_share(query: str) -> str:
    """
    Tool for analyzing screen share with a query
    
    Args:
        query: The question or analysis request about the screen
        
    Returns:
        Analysis result from vision model
    """
    try:
        # Capture screen
        img_b64 = capture_screen()
        if not img_b64:
            return "Could not capture screen. Please ensure screen sharing permissions are granted."
        
        # Use Groq with Llama vision model
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}"
                        }
                    }
                ]
            }
        ]
        
        # Use Llama vision model for screen analysis
        # Note: llama-3.2-90b-vision-preview has been deprecated
        # Using llama-3.2-11b-vision-preview instead
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.2-11b-vision-preview",
            temperature=0.7,
            max_tokens=1024
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error analyzing screen share: {e}")
        return f"Error analyzing screen: {str(e)}"


# Tool descriptions for LangGraph agent
TOOL_DESCRIPTIONS = {
    "analyze_camera": {
        "name": "analyze_image_with_camera",
        "description": "Capture and analyze image from webcam. Use when user asks about their appearance, surroundings, or needs visual analysis.",
        "func": analyze_image_with_camera
    },
    "analyze_screen": {
        "name": "analyze_screen_share", 
        "description": "Capture and analyze the shared screen. Use when user asks about content on their screen or needs help with what they're showing.",
        "func": analyze_screen_share
    }
}