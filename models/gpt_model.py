"""
Ultimate Math Agent - GPT-5.2 Pro Model Interface
The central coordinator model with Extended Thinking capabilities.
"""

import time
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI

from .base_model import BaseModel, ModelResponse
from config import get_config


class GPTModel(BaseModel):
    """
    OpenAI GPT-5.2 Pro interface with Extended Thinking support.
    
    This is the primary model used throughout the pipeline:
    - Stage 1: Problem decomposition and hypothesis generation
    - Stage 2: Deep exploration with Gemini
    - Stage 3: Main proof sketch generation
    - Stage 4: Reconfirmation after Claude verification
    - Stage 5: Final integration and output
    """
    
    def __init__(self):
        config = get_config()
        super().__init__(
            name=config.gpt.name,
            model_id=config.gpt.model_id,
            temperature=config.gpt.temperature,
            max_tokens=config.gpt.max_tokens
        )
        self._api_key = config.gpt.api_key
        self._thinking_mode = config.gpt.thinking_mode
        self._base_url = config.gpt.base_url  # OpenRouter/compatible APIs
    
    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        # Support OpenRouter and other OpenAI-compatible APIs
        if self._base_url:
            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        else:
            self._client = AsyncOpenAI(api_key=self._api_key)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: bool = False,
    ) -> ModelResponse:
        """Generate response from GPT-5.2 Pro."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self.generate_with_history(
            messages=messages,
            system_prompt=None,  # Already included
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
        
        # Enable extended thinking if requested
        # Note: o1/o3 models have different parameter structure
        if thinking_mode and self._thinking_mode:
            # For o1/o3 models, we remove temperature and max_tokens
            # and use max_completion_tokens instead
            if "o1" in self.model_id or "o3" in self.model_id:
                params.pop("temperature", None)
                params["max_completion_tokens"] = params.pop("max_tokens", self.max_tokens)
            else:
                # For GPT-5.2 Pro with extended thinking (hypothetical API)
                params["reasoning_effort"] = "high"
        
        response = await self._client.chat.completions.create(**params)
        
        # Extract content and thinking
        choice = response.choices[0]
        content = choice.message.content or ""
        thinking = None
        
        # Check for reasoning tokens in usage (o1/o3 models)
        reasoning_tokens = 0
        if hasattr(response.usage, 'completion_tokens_details'):
            details = response.usage.completion_tokens_details
            if hasattr(details, 'reasoning_tokens'):
                reasoning_tokens = details.reasoning_tokens
        
        # For models with visible reasoning, extract it
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
            metadata={
                "reasoning_tokens": reasoning_tokens,
                "finish_reason": choice.finish_reason
            }
        )
    
    async def generate_hypotheses(
        self,
        problem: str,
        count: int = 15,
    ) -> List[str]:
        """
        Generate multiple approach hypotheses for a math problem.
        Optimized for Stage 1 hypothesis generation.
        
        Args:
            problem: The mathematical problem to analyze
            count: Number of hypotheses to generate (10-20)
            
        Returns:
            List of approach hypotheses
        """
        system_prompt = """You are a world-class mathematician with expertise in problem-solving strategies.
Your task is to deeply analyze a mathematical problem and propose creative approach hypotheses.

For each hypothesis:
1. Consider different mathematical domains (algebra, analysis, combinatorics, number theory, geometry, etc.)
2. Think about transformations, generalizations, and special cases
3. Consider both classical techniques and novel approaches
4. Think about computational/algorithmic approaches if applicable

Output each hypothesis as a numbered item, with a brief description of the approach."""

        prompt = f"""Analyze this mathematical problem deeply and generate {count} distinct approach hypotheses.
Be creative and thorough. Consider unconventional approaches.

PROBLEM:
{problem}

Generate exactly {count} hypotheses, numbered 1 through {count}:"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            thinking_mode=True,
            temperature=0.8  # Higher for creativity
        )
        
        # Parse hypotheses from response
        hypotheses = []
        lines = response.content.split("\n")
        current_hypothesis = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_hypothesis:
                    hypotheses.append(current_hypothesis.strip())
                    current_hypothesis = ""
                continue
            
            # Check if this is a new numbered item
            if any(line.startswith(f"{i}.") or line.startswith(f"{i})") for i in range(1, count + 1)):
                if current_hypothesis:
                    hypotheses.append(current_hypothesis.strip())
                current_hypothesis = line
            else:
                current_hypothesis += " " + line
        
        if current_hypothesis:
            hypotheses.append(current_hypothesis.strip())
        
        return hypotheses[:count]
    
    async def assess_confidence(
        self,
        problem: str,
        proof: str,
        verification_result: str,
    ) -> float:
        """
        Assess confidence in the proof after verification.
        
        Args:
            problem: Original problem
            proof: Generated proof
            verification_result: Claude's verification output
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        system_prompt = """You are a rigorous mathematical reviewer.
Assess the confidence level in a proof based on the problem, proof, and verification feedback.

Output a single number between 0.0 and 1.0 representing your confidence:
- 0.9-1.0: Proof is rigorous, complete, and verified
- 0.7-0.9: Proof is mostly correct with minor concerns
- 0.5-0.7: Proof has gaps but core approach is valid
- 0.3-0.5: Significant issues but salvageable
- 0.0-0.3: Major errors or incomplete

Output ONLY the number, nothing else."""

        prompt = f"""PROBLEM:
{problem}

PROOF:
{proof}

VERIFICATION RESULT:
{verification_result}

Confidence score (0.0-1.0):"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Low for consistent scoring
            max_tokens=10
        )
        
        try:
            score = float(response.content.strip())
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except ValueError:
            return 0.5  # Default to uncertain
