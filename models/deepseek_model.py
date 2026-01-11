"""
Ultimate Math Agent - DeepSeek-Math-V2 Model Interface
Used for proof refinement and self-correction in Stage 3.
"""

import time
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI

from .base_model import BaseModel, ModelResponse
from config import get_config


class DeepSeekModel(BaseModel):
    """
    DeepSeek-Math-V2 interface.
    
    Used in Stage 3 alongside GPT-5.2 for proof generation:
    - Specialized in mathematical reasoning
    - Self-correction capabilities
    - Detailed proof step generation
    """
    
    def __init__(self):
        config = get_config()
        super().__init__(
            name=config.deepseek.name,
            model_id=config.deepseek.model_id,
            temperature=config.deepseek.temperature,
            max_tokens=config.deepseek.max_tokens
        )
        self._api_key = config.deepseek.api_key
        self._base_url = config.deepseek.base_url
    
    async def initialize(self) -> None:
        """Initialize the DeepSeek client (uses OpenAI-compatible API)."""
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
        """Generate response from DeepSeek-Math-V2."""
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
        
        return ModelResponse(
            content=content,
            thinking=None,
            model=self.model_id,
            latency_ms=self._measure_time(start_time),
            tokens_used=response.usage.total_tokens if response.usage else 0,
            metadata={"finish_reason": choice.finish_reason}
        )
    
    async def refine_proof(
        self,
        problem: str,
        proof_sketch: str,
        feedback: Optional[str] = None,
    ) -> str:
        """
        Refine and detail a proof sketch.
        
        DeepSeek's mathematical specialization helps with:
        - Adding rigorous mathematical details
        - Filling logical gaps
        - Improving clarity
        - Self-correcting errors
        
        Args:
            problem: Original problem statement
            proof_sketch: Initial proof draft from GPT-5.2
            feedback: Optional feedback from previous verification
            
        Returns:
            Refined, detailed proof
        """
        system_prompt = """You are DeepSeek-Math, an AI specialized in mathematical reasoning.
Your task is to refine and detail a proof sketch into a rigorous proof.

When refining a proof:
1. Add missing logical steps
2. Make implicit assumptions explicit
3. Justify each claim with proper reasoning
4. Use precise mathematical notation
5. Handle edge cases
6. Self-correct any errors you find
7. Maintain logical flow

Output a complete, self-contained proof that could be published."""

        prompt = f"""Refine this proof sketch into a rigorous mathematical proof.

PROBLEM:
{problem}

PROOF SKETCH:
{proof_sketch}
"""
        
        if feedback:
            prompt += f"""
FEEDBACK TO ADDRESS:
{feedback}

Please address all the feedback points in your refined proof.
"""
        
        prompt += "\nProvide the refined, detailed proof:"

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,  # Balanced for precision and creativity
        )
        
        return response.content
    
    async def self_correct(
        self,
        problem: str,
        proof: str,
        max_iterations: int = 3,
    ) -> str:
        """
        Perform self-correction on a proof.
        
        The model reviews its own output and iteratively improves it.
        
        Args:
            problem: Original problem
            proof: Current proof
            max_iterations: Maximum correction iterations
            
        Returns:
            Self-corrected proof
        """
        current_proof = proof
        
        for i in range(max_iterations):
            system_prompt = """You are a mathematical proof reviewer.
Review the given proof and identify any errors or improvements needed.

If you find issues:
1. List them clearly
2. Provide the corrected proof

If the proof is correct:
1. State "PROOF_CORRECT"
2. Return the proof unchanged

Be rigorous but don't over-correct valid approaches."""

            prompt = f"""Review and self-correct this mathematical proof (Iteration {i + 1}/{max_iterations}).

PROBLEM:
{problem}

CURRENT PROOF:
{current_proof}

Review the proof carefully. If corrections are needed, provide the corrected version.
Otherwise, state PROOF_CORRECT.

Your response:"""

            response = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4
            )
            
            content = response.content
            
            # Check if proof is marked as correct
            if "PROOF_CORRECT" in content:
                break
            
            # Extract corrected proof if present
            if "CORRECTED PROOF:" in content:
                current_proof = content.split("CORRECTED PROOF:")[1].strip()
            else:
                # Use the full response as the new proof
                current_proof = content
        
        return current_proof
    
    async def generate_lean4_sketch(
        self,
        problem: str,
        proof: str,
    ) -> str:
        """
        Generate a Lean4 proof sketch from a natural language proof.
        
        Args:
            problem: Original problem
            proof: Natural language proof
            
        Returns:
            Lean4 proof sketch
        """
        system_prompt = """You are an expert in formal mathematics and Lean4.
Convert natural language proofs into Lean4 theorem statements and proof sketches.

Follow Lean4 syntax carefully:
- Use proper theorem/lemma declarations
- Use appropriate tactics (simp, ring, linarith, etc.)
- Include necessary imports
- Use sorry for complex steps that need manual proof

Make the Lean4 code compilable (ignoring sorry statements)."""

        prompt = f"""Convert this proof to Lean4 format.

PROBLEM:
{problem}

NATURAL LANGUAGE PROOF:
{proof}

Generate Lean4 code:

```lean4"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        content = response.content
        
        # Extract Lean4 code
        if "```lean4" in content:
            code_start = content.find("```lean4") + len("```lean4")
            code_end = content.find("```", code_start)
            if code_end > code_start:
                return content[code_start:code_end].strip()
        elif "```lean" in content:
            code_start = content.find("```lean") + len("```lean")
            code_end = content.find("```", code_start)
            if code_end > code_start:
                return content[code_start:code_end].strip()
        
        return content
