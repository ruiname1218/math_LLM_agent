"""
Ultimate Math Agent - Gemini 3 Pro Model Interface
Used for AlphaEvolve-style exploration code generation in Stage 2.
"""

import time
from typing import Optional, List, Dict, Any
import google.generativeai as genai

from .base_model import BaseModel, ModelResponse
from config import get_config


class GeminiModel(BaseModel):
    """
    Google Gemini 3 Pro interface with Deep Think mode.
    
    Used in Stage 2 for AlphaEvolve-style exploration:
    - Generates executable code to explore mathematical patterns
    - Fast exploration of hypothesis space
    - Symbolic computation integration
    """
    
    def __init__(self):
        config = get_config()
        super().__init__(
            name=config.gemini.name,
            model_id=config.gemini.model_id,
            temperature=config.gemini.temperature,
            max_tokens=config.gemini.max_tokens
        )
        self._api_key = config.gemini.api_key
        self._thinking_mode = config.gemini.thinking_mode
        self._model = None
    
    async def initialize(self) -> None:
        """Initialize the Gemini client."""
        genai.configure(api_key=self._api_key)
        
        # Configure generation settings
        generation_config = genai.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )
        
        self._model = genai.GenerativeModel(
            model_name=self.model_id,
            generation_config=generation_config
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: bool = False,
    ) -> ModelResponse:
        """Generate response from Gemini 3 Pro."""
        if not self._model:
            await self.initialize()
        
        start_time = time.time()
        
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Update generation config if needed
        config_overrides = {}
        if temperature is not None:
            config_overrides["temperature"] = temperature
        if max_tokens is not None:
            config_overrides["max_output_tokens"] = max_tokens
        
        if config_overrides:
            generation_config = genai.GenerationConfig(**config_overrides)
            response = await self._model.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
        else:
            response = await self._model.generate_content_async(full_prompt)
        
        content = response.text if response.text else ""
        thinking = None
        
        # Check for thinking in response (Gemini Deep Think)
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                # Could contain reasoning traces
                pass
        
        # Extract thinking markers if present
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
            tokens_used=0,  # Gemini doesn't always return token counts
            metadata={}
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
        if not self._model:
            await self.initialize()
        
        start_time = time.time()
        
        # Start a chat session
        chat = self._model.start_chat(history=[])
        
        # Add system prompt as first message if provided
        if system_prompt:
            await chat.send_message_async(f"System instructions: {system_prompt}")
        
        # Send all but the last message to build history
        for msg in messages[:-1]:
            if msg["role"] == "user":
                await chat.send_message_async(msg["content"])
        
        # Send the final message and get response
        last_message = messages[-1]["content"] if messages else ""
        
        config_overrides = {}
        if temperature is not None:
            config_overrides["temperature"] = temperature
        if max_tokens is not None:
            config_overrides["max_output_tokens"] = max_tokens
        
        if config_overrides:
            generation_config = genai.GenerationConfig(**config_overrides)
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config
            )
        else:
            response = await chat.send_message_async(last_message)
        
        content = response.text if response.text else ""
        
        return ModelResponse(
            content=content,
            thinking=None,
            model=self.model_id,
            latency_ms=self._measure_time(start_time),
            tokens_used=0,
            metadata={}
        )
    
    async def generate_exploration_code(
        self,
        problem: str,
        hypotheses: List[str],
    ) -> str:
        """
        Generate AlphaEvolve-style exploration code.
        
        Creates Python code that:
        - Explores the hypothesis space computationally
        - Tests small cases and looks for patterns
        - Uses symbolic computation (SymPy)
        - Generates conjectures based on observations
        
        Args:
            problem: The mathematical problem
            hypotheses: List of approach hypotheses from Stage 1
            
        Returns:
            Python code for mathematical exploration
        """
        system_prompt = """You are an AI specialized in generating executable mathematical exploration code.
Your code should use Python with SymPy for symbolic computation.

The code should:
1. Define symbolic variables appropriately
2. Test the hypotheses computationally where possible
3. Search for patterns in small cases
4. Generate visualizations if helpful
5. Output conjectures based on observations

Make the code self-contained and executable.
Include clear comments explaining each exploration step.
Use functions like sympy.simplify, sympy.solve, sympy.factor, etc.
Handle both numeric and symbolic computations."""

        hypotheses_text = "\n".join(f"- {h}" for h in hypotheses)
        
        prompt = f"""Generate Python exploration code for this mathematical problem.

PROBLEM:
{problem}

HYPOTHESES TO EXPLORE:
{hypotheses_text}

Generate comprehensive exploration code that tests these hypotheses computationally.
The code should be executable as a single Python script.

```python
# Mathematical Exploration Code
"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            thinking_mode=True,
            temperature=0.7
        )
        
        # Extract code from response
        content = response.content
        
        # Find code block
        if "```python" in content:
            code_start = content.find("```python") + len("```python")
            code_end = content.find("```", code_start)
            if code_end > code_start:
                return content[code_start:code_end].strip()
        
        # If no code block, try to extract any Python-like content
        if "import sympy" in content or "from sympy" in content:
            return content
        
        return f"""# Auto-generated exploration code
import sympy as sp
from sympy import symbols, simplify, solve, expand, factor
from sympy import Rational, sqrt, I, pi, E
import numpy as np

# Problem: {problem[:200]}...

# TODO: Implement exploration based on hypotheses
# Hypotheses:
{chr(10).join('# ' + h for h in hypotheses[:5])}

print("Exploration code needs manual implementation")
"""
