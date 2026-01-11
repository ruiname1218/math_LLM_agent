"""
Ultimate Math Agent - Base Model Interface
Abstract base class for all LLM implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import time


@dataclass
class ModelResponse:
    """Standardized response from any LLM."""
    content: str
    thinking: Optional[str] = None  # Extended thinking/reasoning trace
    model: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_thinking(self) -> bool:
        """Check if response includes thinking trace."""
        return self.thinking is not None and len(self.thinking) > 0


class BaseModel(ABC):
    """Abstract base class for all LLM interfaces."""
    
    def __init__(self, name: str, model_id: str, temperature: float = 0.7, max_tokens: int = 16384):
        self.name = name
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the model client."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: bool = False,
    ) -> ModelResponse:
        """
        Generate a response from the model.
        
        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instructions
            temperature: Override default temperature
            max_tokens: Override default max tokens
            thinking_mode: Enable extended thinking if supported
            
        Returns:
            ModelResponse with content and optional thinking trace
        """
        pass
    
    @abstractmethod
    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: bool = False,
    ) -> ModelResponse:
        """
        Generate a response with conversation history.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system_prompt: Optional system instructions
            temperature: Override default temperature
            max_tokens: Override default max tokens
            thinking_mode: Enable extended thinking if supported
            
        Returns:
            ModelResponse with content and optional thinking trace
        """
        pass
    
    async def health_check(self) -> bool:
        """Check if the model is accessible and working."""
        try:
            response = await self.generate("Say 'ok' if you're working.", max_tokens=10)
            return len(response.content) > 0
        except Exception:
            return False
    
    def _measure_time(self, start: float) -> float:
        """Calculate elapsed time in milliseconds."""
        return (time.time() - start) * 1000
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', model='{self.model_id}')"
