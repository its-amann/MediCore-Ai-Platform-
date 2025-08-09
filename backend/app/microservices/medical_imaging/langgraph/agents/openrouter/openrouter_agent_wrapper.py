"""
OpenRouter Agent Wrapper for LangGraph
"""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import logging

logger = logging.getLogger(__name__)


def create_openrouter_agent(
    model_id: str,
    api_key: str,
    tools: List[Any],
    system_prompt: str,
    temperature: float = 0.7
):
    """
    Create an OpenRouter agent using ChatOpenAI with OpenRouter configuration
    
    Args:
        model_id: OpenRouter model ID (e.g., "anthropic/claude-3-opus")
        api_key: OpenRouter API key
        tools: List of tools available to the agent
        system_prompt: System prompt for the agent
        temperature: Temperature for generation
        
    Returns:
        LangGraph agent instance
    """
    
    try:
        # Create OpenRouter LLM using ChatOpenAI
        llm = ChatOpenAI(
            model=model_id,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            default_headers={
                "HTTP-Referer": "https://medical-ai.com",
                "X-Title": "Medical AI Assistant"
            }
        )
        
        # Create agent with tools and prompt
        agent = create_react_agent(
            model=llm,
            tools=tools,
            state_modifier=system_prompt
        )
        
        logger.info(f"Created OpenRouter agent with model {model_id}")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create OpenRouter agent: {e}")
        raise


async def invoke_openrouter_agent(agent, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke the OpenRouter agent with the current state
    
    Args:
        agent: The agent instance
        state: Current workflow state
        
    Returns:
        Updated state
    """
    
    try:
        # Prepare messages from state
        messages = state.get('messages', [])
        
        # Invoke agent
        response = await agent.ainvoke({
            "messages": messages,
            **state  # Pass entire state for context
        })
        
        # Update state with agent's response
        if 'messages' in response:
            state['messages'] = response['messages']
        
        # Extract any tool outputs based on current step
        current_step = state.get('current_step', '')
        
        if current_step == 'report_generation' and hasattr(response, 'tool_outputs'):
            for tool_output in response.tool_outputs:
                if tool_output.tool_name in ['search_web', 'search_duckduckgo']:
                    if 'web_search_results' not in state:
                        state['web_search_results'] = []
                    state['web_search_results'].extend(tool_output.output)
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to invoke OpenRouter agent: {e}")
        state['error'] = str(e)
        return state