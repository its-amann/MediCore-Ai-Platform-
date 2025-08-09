"""
Audio Processing Services
Handles speech-to-text (STT) and text-to-speech (TTS) operations
"""

import os
import sys
import logging
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import which
from io import BytesIO
from groq import Groq
from gtts import gTTS
import tempfile
import base64
from typing import Optional, Tuple
import numpy as np

# Set FFmpeg path for pydub
ffmpeg_path = os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe")
if os.path.exists(ffmpeg_path):
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffmpeg = ffmpeg_path
    AudioSegment.ffprobe = os.path.join(os.path.dirname(sys.executable), "ffprobe.exe")
    logger = logging.getLogger(__name__)
    logger.info(f"FFmpeg found at: {ffmpeg_path}")
else:
    logger = logging.getLogger(__name__)
    logger.warning(f"FFmpeg not found at: {ffmpeg_path}, audio conversion may fail")


class AudioProcessor:
    """Handles audio recording, transcription, and speech synthesis"""
    
    def __init__(self):
        """Initialize audio processor with required clients"""
        self.groq_client = None
        self.recognizer = sr.Recognizer()
        self.audio_buffer = BytesIO()
        self.chunk_accumulator = []
        self.min_chunk_size = 50000  # Minimum 50KB for valid audio
        self._initialize_groq()
    
    def _initialize_groq(self):
        """Initialize Groq client for Whisper transcription"""
        try:
            # Use WHISPER_API if available, otherwise fall back to GROQ_API_KEY
            api_key = os.getenv("WHISPER_API") or os.getenv("GROQ_API_KEY")
            if api_key:
                self.groq_client = Groq(api_key=api_key)
                logger.info("Groq client initialized for Whisper transcription")
            else:
                logger.warning("WHISPER_API or GROQ_API_KEY not found, transcription may be limited")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
    
    def record_audio(self, timeout: int = 20, phrase_time_limit: Optional[int] = None) -> Optional[bytes]:
        """
        Record audio from microphone
        
        Args:
            timeout: Maximum time to wait for speech to start (seconds)
            phrase_time_limit: Maximum time for a phrase (seconds)
            
        Returns:
            Audio data as bytes (WAV format) or None if failed
        """
        try:
            with sr.Microphone() as source:
                logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info("Listening for speech...")
                
                # Record audio
                audio_data = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                
                # Get WAV data
                wav_data = audio_data.get_wav_data()
                logger.info(f"Recorded {len(wav_data)} bytes of audio")
                return wav_data
                
        except sr.WaitTimeoutError:
            logger.info("No speech detected within timeout")
            return None
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return None
    
    def transcribe_with_groq(self, audio_data: bytes, language: str = "en") -> Optional[str]:
        """
        Transcribe audio using Groq's Whisper API
        
        Args:
            audio_data: Audio data in WAV format
            language: Language code for transcription
            
        Returns:
            Transcribed text or None if failed
        """
        if not self.groq_client:
            logger.error("Groq client not initialized")
            return None
        
        try:
            # Save audio to temporary file (Groq API requires file)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe with Groq
            with open(temp_file_path, "rb") as audio_file:
                transcription = self.groq_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            logger.info(f"Transcribed: {transcription[:100]}...")
            return transcription
            
        except Exception as e:
            logger.error(f"Error transcribing with Groq: {e}")
            return None
    
    def validate_webm_chunk(self, audio_bytes: bytes) -> bool:
        """Validate if WebM chunk has proper headers"""
        if len(audio_bytes) < 4:
            return False
        
        # Check for WebM/EBML header (0x1A45DFA3)
        header = audio_bytes[:4]
        is_valid = header[0] == 0x1A and header[1] == 0x45
        
        # For browser-generated WebM, we need to be more lenient
        # The browser MediaRecorder may send chunks without full headers
        if not is_valid and len(audio_bytes) > 10000:
            # If we have enough data, assume it's valid
            logger.info("Large chunk without EBML header, assuming valid continuation")
            return True
            
        return is_valid
    
    def accumulate_audio_chunk(self, audio_base64: str) -> Optional[bytes]:
        """Accumulate audio chunks until we have enough for processing"""
        try:
            audio_bytes = base64.b64decode(audio_base64)
            
            # Add to accumulator
            self.chunk_accumulator.append(audio_bytes)
            
            # Calculate total size
            total_size = sum(len(chunk) for chunk in self.chunk_accumulator)
            
            logger.info(f"Accumulated {len(self.chunk_accumulator)} chunks, total size: {total_size} bytes")
            
            # If we have enough data, combine and return
            if total_size >= self.min_chunk_size:
                combined_audio = b''.join(self.chunk_accumulator)
                self.chunk_accumulator = []  # Reset accumulator
                
                # Validate the combined audio
                if self.validate_webm_chunk(combined_audio):
                    logger.info(f"Returning valid WebM chunk of {len(combined_audio)} bytes")
                    return combined_audio
                else:
                    logger.warning("Combined audio failed validation, continuing accumulation")
                    self.chunk_accumulator = [combined_audio]
                    
        except Exception as e:
            logger.error(f"Error accumulating audio chunk: {e}")
            
        return None
    
    def transcribe_audio_base64(self, audio_base64: str, format: str = "webm") -> Optional[str]:
        """
        Transcribe audio from base64 encoded data with accumulation for WebM
        
        Args:
            audio_base64: Base64 encoded audio data
            format: Audio format (webm, wav, mp3, etc.)
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            if format == "webm":
                # Accumulate chunks for WebM
                complete_audio = self.accumulate_audio_chunk(audio_base64)
                
                if not complete_audio:
                    # Still accumulating
                    return None
                    
                audio_bytes = complete_audio
            else:
                # For other formats, process directly
                audio_bytes = base64.b64decode(audio_base64)
            
            # First, try to convert webm to wav using speech_recognition
            if format == "webm":
                try:
                    # Convert webm to wav using speech_recognition AudioData
                    logger.info("Converting webm to wav for speech recognition")
                    
                    # Try direct conversion with pydub first (if ffmpeg is available)
                    try:
                        audio_segment = AudioSegment.from_file(BytesIO(audio_bytes), format="webm")
                        wav_io = BytesIO()
                        audio_segment.export(wav_io, format="wav")
                        wav_io.seek(0)
                        audio_bytes = wav_io.getvalue()
                        format = "wav"
                        logger.info("Successfully converted webm to wav")
                    except Exception as pydub_error:
                        logger.warning(f"Pydub conversion failed (ffmpeg likely missing): {pydub_error}")
                        # Continue with original webm bytes for Groq
                        pass
                        
                except Exception as conv_error:
                    logger.warning(f"Audio conversion failed: {conv_error}")
                    # Continue with original format
            
            # Try using speech_recognition if we have wav format
            if format == "wav":
                try:
                    # Create AudioData object from wav bytes
                    audio_data = sr.AudioData(audio_bytes, 16000, 2)  # Assuming 16kHz, 16-bit audio
                    
                    # Try Google Speech Recognition first (no API key needed)
                    try:
                        text = self.recognizer.recognize_google(audio_data)
                        logger.info(f"Google Speech Recognition: {text[:100]}...")
                        return text
                    except sr.UnknownValueError:
                        logger.warning("Google Speech Recognition could not understand audio")
                    except sr.RequestError as e:
                        logger.warning(f"Google Speech Recognition error: {e}")
                        
                except Exception as sr_error:
                    logger.warning(f"Speech recognition failed: {sr_error}")
            
            # Fall back to Groq API if available
            if self.groq_client:
                logger.info(f"Attempting to transcribe {format} audio with Groq")
                
                # Create a temporary file with the audio data
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
                    temp_file.write(audio_bytes)
                    temp_file_path = temp_file.name
                
                try:
                    # Try Groq transcription
                    with open(temp_file_path, "rb") as audio_file:
                        transcription = self.groq_client.audio.transcriptions.create(
                            model="whisper-large-v3",
                            file=audio_file,
                            language="en",
                            response_format="text"
                        )
                    
                    logger.info(f"Groq transcription successful: {transcription[:100] if transcription else 'Empty'}...")
                    return transcription
                    
                except Exception as groq_error:
                    logger.error(f"Groq transcription failed: {groq_error}")
                    
                    # If webm failed, try converting to mp3 (more widely supported)
                    if format == "webm":
                        try:
                            logger.info("Attempting webm to mp3 conversion for Groq")
                            audio_segment = AudioSegment.from_file(BytesIO(audio_bytes), format="webm")
                            mp3_io = BytesIO()
                            audio_segment.export(mp3_io, format="mp3")
                            mp3_io.seek(0)
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3_file:
                                mp3_file.write(mp3_io.getvalue())
                                mp3_path = mp3_file.name
                            
                            try:
                                with open(mp3_path, "rb") as audio_file:
                                    transcription = self.groq_client.audio.transcriptions.create(
                                        model="whisper-large-v3",
                                        file=audio_file,
                                        language="en",
                                        response_format="text"
                                    )
                                os.unlink(mp3_path)
                                return transcription
                            except Exception as e:
                                if os.path.exists(mp3_path):
                                    os.unlink(mp3_path)
                                    
                        except Exception as mp3_error:
                            logger.error(f"MP3 conversion failed: {mp3_error}")
                            
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
            
            # Return None instead of mock response - no speech detected
            logger.debug("No speech detected in audio chunk")
            return None
            
        except Exception as e:
            logger.error(f"Error transcribing base64 audio: {e}")
            return None
    
    def text_to_speech_gtts(self, text: str, language: str = "en") -> Optional[bytes]:
        """
        Convert text to speech using gTTS
        
        Args:
            text: Text to convert to speech
            language: Language code for speech
            
        Returns:
            Audio data as bytes (MP3 format) or None if failed
        """
        try:
            # Create gTTS object
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Save to BytesIO
            audio_io = BytesIO()
            tts.write_to_fp(audio_io)
            audio_io.seek(0)
            
            audio_data = audio_io.read()
            logger.info(f"Generated {len(audio_data)} bytes of speech")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech with gTTS: {e}")
            return None
    
    def text_to_speech_base64(self, text: str, language: str = "en") -> Optional[str]:
        """
        Convert text to speech and return as base64
        
        Args:
            text: Text to convert to speech
            language: Language code for speech
            
        Returns:
            Base64 encoded audio (MP3) or None if failed
        """
        audio_data = self.text_to_speech_gtts(text, language)
        if audio_data:
            return base64.b64encode(audio_data).decode('utf-8')
        return None
    
    def detect_voice_activity(self, audio_data: bytes, threshold: float = 0.01) -> bool:
        """
        Simple voice activity detection using RMS energy
        
        Args:
            audio_data: Audio data in WAV format
            threshold: Energy threshold for voice detection
            
        Returns:
            True if voice activity detected, False otherwise
        """
        try:
            # Try using pydub if available
            try:
                audio_segment = AudioSegment.from_wav(BytesIO(audio_data))
                samples = np.array(audio_segment.get_array_of_samples())
                
                # Calculate RMS energy
                rms = np.sqrt(np.mean(samples**2))
                normalized_rms = rms / 32768.0  # Normalize for 16-bit audio
                
                # Check if energy exceeds threshold
                has_voice = normalized_rms > threshold
                logger.debug(f"VAD: RMS={normalized_rms:.4f}, threshold={threshold}, has_voice={has_voice}")
                
                return has_voice
                
            except Exception as pydub_error:
                # Fallback: Simple byte-level analysis
                logger.warning(f"Pydub VAD failed, using simple analysis: {pydub_error}")
                
                # Check if audio data has significant variation (not silence)
                if len(audio_data) < 1000:
                    return False
                    
                # Sample some bytes and check for variation
                sample = audio_data[1000:2000]  # Sample middle portion
                variation = len(set(sample))  # Count unique values
                
                # If there's significant variation, assume voice
                has_voice = variation > 50  # Threshold for variation
                logger.debug(f"Simple VAD: variation={variation}, has_voice={has_voice}")
                
                return has_voice
                
        except Exception as e:
            logger.error(f"Error in voice activity detection: {e}")
            # Default to True to avoid missing speech
            return True
    
    def process_audio_chunk(self, audio_chunk: bytes, format: str = "webm") -> Tuple[bool, Optional[str]]:
        """
        Process an audio chunk for voice activity and transcription
        
        Args:
            audio_chunk: Audio data chunk
            format: Audio format (webm, wav, etc.)
            
        Returns:
            Tuple of (has_voice, transcribed_text)
        """
        # For webm format, we skip VAD and try to transcribe directly
        # since VAD requires wav format and ffmpeg
        if format == "webm":
            # Always try to transcribe webm chunks
            # The transcription service will handle silence detection
            text = self.transcribe_audio_base64(
                base64.b64encode(audio_chunk).decode('utf-8'),
                format=format
            )
            return text is not None and len(text.strip()) > 0, text
        
        # For wav format, use VAD
        has_voice = self.detect_voice_activity(audio_chunk)
        
        if has_voice:
            # Transcribe if voice detected
            text = self.transcribe_with_groq(audio_chunk)
            return True, text
        
        return False, None


# Create singleton instance
audio_processor = AudioProcessor()