"""
LLM Factory for creating different LLM instances
Supports OpenAI, Anthropic, and Gemini
"""
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM instances"""
    
    # Models that only support temperature=1.0 (default)
    TEMPERATURE_RESTRICTED_MODELS = {
        "gpt-5",
        "o1-preview",
        "o1-mini",
    }
    
    @staticmethod
    def _get_temperature(model: str, requested_temp: float = 1.0) -> float:
        """
        Get the appropriate temperature for a model.
        Some models only support temperature=1.0
        """
        if model.lower() in LLMFactory.TEMPERATURE_RESTRICTED_MODELS:
            logger.info(f"Model {model} only supports temperature=1.0, using default")
            return 1.0
        return requested_temp
    
    @staticmethod
    def create_llm(
        provider: Literal["OPENAI", "ANTHROPIC", "GEMINI"],
        model: Optional[str] = None,
        temperature: float = 1.0,  # Default to 1.0 like weam (opts.temperature ?? 1)
        api_key: Optional[str] = None
    ):
        """Create an LLM instance based on provider"""
        
        # Use default model if not specified
        if model is None:
            model = settings.DEFAULT_MODEL
        
        # Use default API key if not provided
        if api_key is None:
            if provider == "OPENAI":
                api_key = settings.OPENAI_API_KEY
            elif provider == "ANTHROPIC":
                api_key = settings.ANTHROPIC_API_KEY
            elif provider == "GEMINI":
                api_key = settings.GOOGLE_API_KEY
        
        if not api_key:
            raise ValueError(f"API key is required for {provider}")
        
        # Adjust temperature based on model restrictions
        adjusted_temperature = LLMFactory._get_temperature(model, temperature)
        
        try:
            if provider == "OPENAI":
                # For restricted models, explicitly set temperature=1.0
                # For other models, use the requested temperature
                is_restricted = model.lower() in LLMFactory.TEMPERATURE_RESTRICTED_MODELS
                
                if is_restricted:
                    # Restricted models must use temperature=1.0
                    logger.info(f"Model {model} is temperature-restricted, setting temperature=1.0")
                    return ChatOpenAI(
                        model=model,
                        temperature=1.0,
                        openai_api_key=api_key
                    )
                else:
                    # Non-restricted models can use custom temperature
                    return ChatOpenAI(
                        model=model,
                        temperature=adjusted_temperature,
                        openai_api_key=api_key
                    )
            
            elif provider == "ANTHROPIC":
                # Use api_key parameter (not anthropic_api_key) to match gocustomai pattern
                return ChatAnthropic(
                    model=model,
                    temperature=adjusted_temperature,
                    api_key=api_key
                )
            
            elif provider == "GEMINI":
                return ChatGoogleGenerativeAI(
                    model=model,
                    temperature=adjusted_temperature,
                    google_api_key=api_key
                )
            
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
        except Exception as e:
            logger.error(f"Failed to create LLM for {provider}: {e}")
            raise

