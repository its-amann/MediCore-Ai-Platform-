"""
Gemini Agent Wrapper for LangGraph
"""

from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
import logging

logger = logging.getLogger(__name__)


def create_gemini_agent(
    model_id: str,
    api_key: str,
    tools: List[Any],
    system_prompt: str,
    temperature: float = 0.7
):
    """
    Create a Gemini agent with the given configuration
    
    Args:
        model_id: Gemini model ID (e.g., "gemini-1.5-pro")
        api_key: Google API key
        tools: List of tools available to the agent
        system_prompt: System prompt for the agent
        temperature: Temperature for generation
        
    Returns:
        LangGraph agent instance
    """
    
    try:
        # Create Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model=model_id,
            google_api_key=api_key,
            temperature=temperature,
        )
        
        # Create agent with tools and prompt
        agent = create_react_agent(
            model=llm,
            tools=tools,
            state_modifier=system_prompt
        )
        
        logger.info(f"Created Gemini agent with model {model_id}")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create Gemini agent: {e}")
        raise


async def invoke_gemini_agent(agent, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke the Gemini agent with the current state
    
    Args:
        agent: The agent instance
        state: Current workflow state
        
    Returns:
        Updated state
    """
    
    try:
        # Prepare messages from state
        messages = state.get('messages', [])
        
        # Add any context from state
        if 'image_data' in state and state.get('current_step') == 'image_analysis':
            # For image analysis, the image is already in the state
            pass
        
        # Invoke agent
        response = await agent.ainvoke({
            "messages": messages,
            **state  # Pass entire state for context
        })
        
        # Update state with agent's response
        if 'messages' in response:
            state['messages'] = response['messages']
        
        # Extract any tool outputs
        if hasattr(response, 'tool_outputs'):
            for tool_output in response.tool_outputs:
                if tool_output.tool_name == 'generate_heatmap':
                    state['heatmap_data'] = tool_output.output
                
        return state
        
    except Exception as e:
        logger.error(f"Failed to invoke Gemini agent: {e}")
        state['error'] = str(e)
        return state