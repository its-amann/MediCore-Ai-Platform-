"""
Voice Processing Agent with LangGraph
Main agent for handling voice consultations with multimodal capabilities
"""

from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool
from typing import Optional, List, Dict, Any
import logging
from ..services.llm_wrapper import llm_wrapper
from .tools import analyze_image_with_camera, analyze_screen_share

logger = logging.getLogger(__name__)


class VoiceProcessingAgent:
    """Main agent for voice consultation with multimodal capabilities"""
    
    def __init__(self, provider: str = "groq", model_id: Optional[str] = "meta-llama/llama-4-scout-17b-16e-instruct"):
        """
        Initialize voice processing agent
        
        Args:
            provider: LLM provider to use
            model_id: Specific model ID
        """
        self.provider = provider
        self.model_id = model_id
        self.llm = None
        self.agent = None
        self.tools = []
        self.system_prompt = self._get_system_prompt()
        
        # Initialize agent
        self._initialize_agent()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the voice agent"""
        return """You are a medical AI assistant for voice consultation.

        CRITICAL: Maximum 30 words per response. Be extremely concise. Voice mode only.
        
        Rules:
        - ONE sentence only
        - Direct answers only
        - No explanations or elaborations
        - Maximum 30 words
        
        Example responses:
        "Take ibuprofen and rest. See a doctor if pain persists."
        "Apply ice for 20 minutes to reduce swelling."
        "That sounds like allergies. Try an antihistamine."
        
        NEVER exceed 30 words. Keep responses ultra-short."""
    
    def _initialize_tools(self) -> List[Tool]:
        """Initialize the tools for the agent"""
        # Enable webcam analysis tool for video consultation
        tools = [
            Tool(
                name="analyze_webcam",
                func=lambda query: analyze_image_with_camera(query),
                description="Analyze image from user's webcam. Use when user shows something or asks about visual symptoms."
            )
        ]
        return tools
    
    def _initialize_agent(self):
        """Initialize the LangGraph ReAct agent"""
        try:
            # Get LLM instance
            self.llm = llm_wrapper.get_llm(
                provider=self.provider,
                model_id=self.model_id,
                temperature=0.7
            )
            
            # Initialize tools
            self.tools = self._initialize_tools()
            
            # Create ReAct agent
            self.agent = create_react_agent(
                model=self.llm,
                tools=self.tools,
                messages_modifier=self.system_prompt
            )
            
            logger.info(f"Voice agent initialized with {self.provider}/{self.model_id or 'default'}")
            
        except Exception as e:
            logger.error(f"Failed to initialize voice agent: {e}")
            # Don't recursively call _initialize_agent, just raise the error
            raise
    
    def process_query(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a user query and return response
        
        Args:
            user_query: The user's question or statement
            context: Optional context (chat history, mode, etc.)
            
        Returns:
            Agent's response as string
        """
        try:
            # Prepare input messages
            input_messages = {
                "messages": [
                    {"role": "user", "content": user_query}
                ]
            }
            
            # Add context if provided (e.g., chat history)
            if context and "chat_history" in context:
                # Prepend chat history to messages
                history_messages = []
                for user_msg, assistant_msg in context["chat_history"][-5:]:  # Last 5 exchanges
                    history_messages.append({"role": "user", "content": user_msg})
                    history_messages.append({"role": "assistant", "content": assistant_msg})
                
                input_messages["messages"] = history_messages + input_messages["messages"]
            
            # Invoke agent
            response = self.agent.invoke(input_messages)
            
            # Extract the final message content
            if response and "messages" in response and len(response["messages"]) > 0:
                return response["messages"][-1].content
            else:
                return "I'm sorry, I couldn't process that request. Could you please try again?"
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error processing your request. Please try again."
    
    def switch_provider(self, provider: str, model_id: Optional[str] = None):
        """
        Switch to a different LLM provider
        
        Args:
            provider: New provider name
            model_id: Optional model ID
        """
        self.provider = provider
        self.model_id = model_id
        self._initialize_agent()
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the current agent configuration"""
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "tools": [tool.name for tool in self.tools],
            "status": "active" if self.agent else "inactive"
        }


# Create a singleton instance (lazy initialization)
voice_agent = None

def get_voice_agent():
    """Get or create the voice agent instance"""
    global voice_agent
    if voice_agent is None:
        # Try different providers in order of preference
        providers_to_try = [
            ("groq", "llama-3.3-70b-versatile"),  # More reliable model
            ("groq", "llama3-8b-8192"),  # Smaller, faster model
            ("gemini", "gemini-2.0-flash"),  # Fallback to Gemini if available
        ]
        
        for provider, model_id in providers_to_try:
            try:
                voice_agent = VoiceProcessingAgent(
                    provider=provider,
                    model_id=model_id
                )
                logger.info(f"Voice agent initialized with {provider}/{model_id}")
                break
            except Exception as e:
                logger.warning(f"Failed to initialize with {provider}/{model_id}: {e}")
                continue
        
        if voice_agent is None:
            raise RuntimeError("Failed to initialize voice agent with any provider")
    
    return voice_agent