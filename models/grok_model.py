"""
Ultimate Math Agent - Grok-4.2 Heavy Model Interface
Used for parallel problem decomposition in Stage 1.
"""

import time
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI

from .base_model import BaseModel, ModelResponse
from config import get_config


class GrokModel(BaseModel):
    """
    xAI Grok-4.2 Heavy interface with Thinking mode.
    
    Used in Stage 1 alongside GPT-5.2 for parallel problem decomposition.
    Grok's strength: Creative reasoning and unconventional perspectives.
    """
    
    def __init__(self):
        config = get_config()
        super().__init__(
            name=config.grok.name,
            model_id=config.grok.model_id,
            temperature=config.grok.temperature,
            max_tokens=config.grok.max_tokens
        )
        self._api_key = config.grok.api_key
        self._base_url = config.grok.base_url
        self._thinking_mode = config.grok.thinking_mode
    
    async def initialize(self) -> None:
        """Initialize the Grok client (uses OpenAI-compatible API)."""
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: bool = False,
    ) -> ModelResponse:
        """Generate response from Grok-4.2 Heavy."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self.generate_with_history(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_mode=thinking_mode
        )
    
    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: bool = False,
    ) -> ModelResponse:
        """Generate response with conversation history."""
        if not self._client:
            await self.initialize()
        
        start_time = time.time()
        
        # Prepare messages
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        
        # Build request parameters
        params: Dict[str, Any] = {
            "model": self.model_id,
            "messages": all_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        response = await self._client.chat.completions.create(**params)
        
        choice = response.choices[0]
        content = choice.message.content or ""
        thinking = None
        
        # Extract thinking if present
        if "<thinking>" in content:
            parts = content.split("</thinking>")
            if len(parts) == 2:
                thinking = parts[0].replace("<thinking>", "").strip()
                content = parts[1].strip()
        
        return ModelResponse(
            content=content,
            thinking=thinking,
            model=self.model_id,
            latency_ms=self._measure_time(start_time),
            tokens_used=response.usage.total_tokens if response.usage else 0,
            metadata={"finish_reason": choice.finish_reason}
        )
    
    async def decompose_problem(
        self,
        problem: str,
    ) -> Dict[str, Any]:
        """
        Decompose a mathematical problem into components.
        Grok's perspective complements GPT's analysis.
        
        Args:
            problem: The mathematical problem to decompose
            
        Returns:
            Dictionary with problem structure analysis
        """
        system_prompt = """You are Grok, an AI with a unique perspective on problem-solving.
Analyze mathematical problems with creativity and unconventional thinking.

Your analysis should include:
1. Core mathematical structures (what type of problem is this?)
2. Hidden assumptions and constraints
3. Potential transformations or reformulations
4. Connections to other mathematical areas
5. Unexpected approaches that might work

Be bold in your suggestions. Think outside the box."""

        prompt = f"""Deeply decompose this mathematical problem:

PROBLEM:
{problem}

Provide your analysis in a structured format:

PROBLEM TYPE:
[Classify the problem]

KEY STRUCTURES:
[List the mathematical structures involved]

HIDDEN ASSUMPTIONS:
[What assumptions are implicit?]

POSSIBLE TRANSFORMATIONS:
[How might we reformulate this?]

UNCONVENTIONAL APPROACHES:
[What creative methods might apply?]

CONNECTIONS:
[Links to other mathematical areas]"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            thinking_mode=True,
            temperature=0.8
        )
        
        # Parse structured response
        result = {
            "raw_analysis": response.content,
            "thinking": response.thinking,
            "sections": {}
        }
        
        current_section = None
        current_content = []
        
        for line in response.content.split("\n"):
            line = line.strip()
            if line.endswith(":") and line.isupper():
                if current_section:
                    result["sections"][current_section] = "\n".join(current_content)
                current_section = line[:-1].lower().replace(" ", "_")
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            result["sections"][current_section] = "\n".join(current_content)
        
        return result
