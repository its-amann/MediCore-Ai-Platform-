"""
LLM Wrapper for Voice Consultation
Provides unified interface for different LLM providers (Gemini, OpenAI, Groq)
"""

import os
from typing import Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import logging

logger = logging.getLogger(__name__)


class LLMWrapper:
    """Wrapper class to provide unified LLM interface for LangGraph agents"""
    
    def __init__(self):
        self.providers = {
            "gemini": self._create_gemini_llm,
            "openai": self._create_openai_llm,
            "groq": self._create_groq_llm,
            "openrouter": self._create_openrouter_llm
        }
        
    def _create_gemini_llm(self, model_id: str = "gemini-2.0-flash", temperature: float = 0.7):
        """Create Gemini LLM instance"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            google_api_key=api_key
        )
    
    def _create_openai_llm(self, model_id: str = "gpt-4o-mini", temperature: float = 0.7):
        """Create OpenAI LLM instance"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            openai_api_key=api_key
        )
    
    def _create_groq_llm(self, model_id: str = "meta-llama/llama-4-scout-17b-16e-instruct", temperature: float = 0.7):
        """Create Groq LLM instance"""
        # Try WHISPER_API first (for voice consultation), then fall back to GROQ_API_KEY
        api_key = os.getenv("WHISPER_API") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("WHISPER_API or GROQ_API_KEY not found in environment variables")
            
        return ChatGroq(
            model=model_id,
            temperature=temperature,
            groq_api_key=api_key
        )
    
    def _create_openrouter_llm(self, model_id: str = "meta-llama/llama-3.1-8b-instruct:free", temperature: float = 0.7):
        """Create OpenRouter LLM instance (uses OpenAI client)"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
            
        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def get_llm(self, provider: str = "gemini", model_id: Optional[str] = None, temperature: float = 0.7):
        """
        Get LLM instance based on provider
        
        Args:
            provider: LLM provider (gemini, openai, groq, openrouter)
            model_id: Specific model ID to use
            temperature: Temperature for generation
            
        Returns:
            LLM instance for use with LangGraph
        """
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(self.providers.keys())}")
        
        creator_func = self.providers[provider]
        
        # Use default model IDs if not specified
        if model_id is None:
            default_models = {
                "gemini": "gemini-2.0-flash",
                "openai": "gpt-4o-mini",
                "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
                "openrouter": "meta-llama/llama-3.1-8b-instruct:free"
            }
            model_id = default_models.get(provider)
        
        try:
            llm = creator_func(model_id=model_id, temperature=temperature)
            logger.info(f"Created LLM instance: {provider}/{model_id}")
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM for {provider}: {e}")
            # Fallback to Gemini
            if provider != "gemini":
                logger.info("Falling back to Gemini")
                return self._create_gemini_llm()
            raise
    
    def get_best_available_llm(self, preferred_provider: str = "gemini", temperature: float = 0.7):
        """
        Get the best available LLM, trying providers in order of preference
        
        Args:
            preferred_provider: Preferred provider to try first
            temperature: Temperature for generation
            
        Returns:
            First successfully created LLM instance
        """
        # Try preferred provider first
        providers_to_try = [preferred_provider] + [p for p in self.providers if p != preferred_provider]
        
        for provider in providers_to_try:
            try:
                return self.get_llm(provider=provider, temperature=temperature)
            except Exception as e:
                logger.warning(f"Failed to create {provider} LLM: {e}")
                continue
        
        raise RuntimeError("No LLM providers available")


# Singleton instance
llm_wrapper = LLMWrapper()