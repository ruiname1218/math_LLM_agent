"""
Ultimate Math Agent - Aristotle Model Interface
Harmonic AI's Lean4-native theorem proving model.

Aristotle is specialized for:
- Formal theorem proving in Lean4
- Autoformalization (natural language → Lean4)
- Hallucination-free mathematical proofs
- IMO gold-medal level problem solving
"""

import time
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI

from .base_model import BaseModel, ModelResponse
from config import get_config


class AristotleModel(BaseModel):
    """
    Harmonic AI's Aristotle interface for Lean4 theorem proving.
    
    Aristotle is THE specialist for Lean4 code generation because:
    - Native Lean4 training (not just general LLM + Lean4 examples)
    - Autoformalization capabilities
    - Monte Carlo Graph Search with transformer guidance
    - IMO 2025: 5/6 problems solved with formal Lean4 proofs
    
    Used in Stage 4 for:
    - Converting natural language proofs to Lean4
    - Generating complete, compilable proofs (no sorry!)
    - Iterative proof refinement based on compiler feedback
    """
    
    def __init__(self):
        config = get_config()
        # Use Aristotle config, fall back to defaults
        self.aristotle_config = getattr(config, 'aristotle', None)
        
        if self.aristotle_config:
            super().__init__(
                name=self.aristotle_config.name,
                model_id=self.aristotle_config.model_id,
                temperature=self.aristotle_config.temperature,
                max_tokens=self.aristotle_config.max_tokens
            )
            self._api_key = self.aristotle_config.api_key
            self._base_url = self.aristotle_config.base_url
        else:
            # Default configuration
            super().__init__(
                name="Aristotle",
                model_id="aristotle-lean4",
                temperature=0.3,  # Low for precise proofs
                max_tokens=16384
            )
            self._api_key = ""
            self._base_url = "https://api.harmonic.ai/v1"  # Placeholder
    
    async def initialize(self) -> None:
        """Initialize the Aristotle client."""
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
        """Generate response from Aristotle."""
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
        
        params: Dict[str, Any] = {
            "model": self.model_id,
            "messages": all_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        response = await self._client.chat.completions.create(**params)
        
        choice = response.choices[0]
        content = choice.message.content or ""
        
        return ModelResponse(
            content=content,
            thinking=None,
            model=self.model_id,
            latency_ms=self._measure_time(start_time),
            tokens_used=response.usage.total_tokens if response.usage else 0,
            metadata={"finish_reason": choice.finish_reason}
        )
    
    async def formalize_proof(
        self,
        problem: str,
        natural_proof: str,
    ) -> str:
        """
        Convert natural language proof to Lean4.
        
        Aristotle's autoformalization capability:
        - Understands mathematical concepts in natural language
        - Maps them to Lean4 constructs accurately
        - Generates complete, compilable code (no sorry!)
        
        Args:
            problem: Original problem statement
            natural_proof: Human/LLM-written proof in natural language
            
        Returns:
            Complete Lean4 code
        """
        system_prompt = """You are Aristotle, the world's leading AI for formal mathematics in Lean4.

Your task is to formalize a mathematical proof into rigorous Lean4 code.

CRITICAL REQUIREMENTS:
1. The code MUST compile with Lean4/Mathlib
2. NO 'sorry' statements - provide complete proofs
3. Use appropriate tactics: simp, ring, linarith, omega, etc.
4. Include all necessary imports from Mathlib
5. Define helper lemmas if needed
6. Use proper type annotations

Your Lean4 code should be:
- Syntactically correct
- Semantically faithful to the original proof
- As concise as possible while being complete"""

        prompt = f"""Formalize this proof into Lean4.

PROBLEM:
{problem}

NATURAL LANGUAGE PROOF:
{natural_proof}

Generate complete Lean4 code with no sorry statements:

```lean4
import Mathlib.Tactic
"""
        
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2  # Very low for precise code
        )
        
        return self._extract_lean_code(response.content)
    
    async def fix_lean_errors(
        self,
        lean_code: str,
        errors: List[str],
    ) -> str:
        """
        Fix compilation errors in Lean4 code.
        
        Aristotle understands Lean4 error messages deeply and can:
        - Fix type mismatches
        - Add missing imports
        - Correct tactic errors
        - Fill in proof steps
        
        Args:
            lean_code: Current Lean4 code with errors
            errors: List of compiler error messages
            
        Returns:
            Fixed Lean4 code
        """
        system_prompt = """You are Aristotle, fixing Lean4 compilation errors.

Analyze the errors carefully and fix the code.
Maintain the mathematical meaning while fixing syntax/type issues.
Do NOT use sorry - find actual proof tactics."""

        error_text = "\n".join(errors[:10])  # Limit errors
        
        prompt = f"""Fix these Lean4 compilation errors.

CURRENT CODE:
```lean4
{lean_code}
```

ERRORS:
{error_text}

Provide the FIXED complete code:

```lean4"""
        
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2
        )
        
        return self._extract_lean_code(response.content)
    
    async def suggest_tactics(
        self,
        goal_state: str,
    ) -> List[str]:
        """
        Suggest tactics for a given Lean4 goal state.
        
        Args:
            goal_state: The current proof goal from Lean4
            
        Returns:
            List of suggested tactics, ranked by likelihood
        """
        system_prompt = """You are Aristotle suggesting Lean4 tactics.
Given a proof goal, suggest the most likely tactics to make progress.
Return ONE tactic per line, most promising first."""

        prompt = f"""What tactics would solve or make progress on this goal?

GOAL STATE:
{goal_state}

Suggest tactics (one per line):"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )
        
        tactics = [line.strip() for line in response.content.split('\n')
                   if line.strip() and not line.startswith('#')]
        return tactics[:10]
    
    def _extract_lean_code(self, response: str) -> str:
        """Extract Lean4 code from response."""
        if "```lean4" in response:
            start = response.find("```lean4") + 8
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        if "```lean" in response:
            start = response.find("```lean") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        # Return as-is if no code blocks
        return response.strip()


# Helper function to check if Aristotle is available
async def is_aristotle_available() -> bool:
    """Check if Aristotle API is configured and accessible."""
    config = get_config()
    if not hasattr(config, 'aristotle') or not config.aristotle.api_key:
        return False
    
    try:
        model = AristotleModel()
        return await model.health_check()
    except:
        return False
