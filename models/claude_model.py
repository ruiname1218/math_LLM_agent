"""
Ultimate Math Agent - Claude Opus 4.5 Model Interface
Used for rigorous verification in Stage 4.
"""

import time
from typing import Optional, List, Dict, Any
from anthropic import AsyncAnthropic

from .base_model import BaseModel, ModelResponse
from config import get_config


class ClaudeModel(BaseModel):
    """
    Anthropic Claude Opus 4.5 interface with Thinking mode.
    
    Used in Stage 4 for rigorous verification:
    - Thorough logic hole checking
    - Proof structure validation
    - Error identification and feedback
    """
    
    def __init__(self):
        config = get_config()
        super().__init__(
            name=config.claude.name,
            model_id=config.claude.model_id,
            temperature=config.claude.temperature,
            max_tokens=config.claude.max_tokens
        )
        self._api_key = config.claude.api_key
        self._thinking_mode = config.claude.thinking_mode
    
    async def initialize(self) -> None:
        """Initialize the Anthropic client."""
        self._client = AsyncAnthropic(api_key=self._api_key)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: bool = False,
    ) -> ModelResponse:
        """Generate response from Claude Opus 4.5."""
        messages = [{"role": "user", "content": prompt}]
        
        return await self.generate_with_history(
            messages=messages,
            system_prompt=system_prompt,
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
        
        # Build request parameters
        params: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        if system_prompt:
            params["system"] = system_prompt
        
        # Configure thinking mode for Claude
        if thinking_mode and self._thinking_mode:
            # Extended thinking budget
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": 16000
            }
            # Temperature not allowed with extended thinking
        else:
            params["temperature"] = temperature or self.temperature
        
        response = await self._client.messages.create(**params)
        
        # Extract content and thinking
        content = ""
        thinking = None
        
        for block in response.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                content = block.text
        
        return ModelResponse(
            content=content,
            thinking=thinking,
            model=self.model_id,
            latency_ms=self._measure_time(start_time),
            tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else 0,
            metadata={
                "stop_reason": response.stop_reason,
                "thinking_tokens": len(thinking) if thinking else 0
            }
        )
    
    async def verify_proof(
        self,
        problem: str,
        proof: str,
    ) -> Dict[str, Any]:
        """
        Rigorously verify a mathematical proof.
        
        Claude's strength is in careful, methodical verification.
        This function checks for:
        - Logical gaps
        - Unjustified claims
        - Missing cases
        - Circular reasoning
        - Mathematical errors
        
        Args:
            problem: The original problem statement
            proof: The proof to verify
            
        Returns:
            Dictionary with verification result and feedback
        """
        system_prompt = """You are a rigorous mathematical proof verifier.
Your role is to carefully check proofs for correctness and completeness.

When verifying a proof:
1. Check each logical step carefully
2. Identify any gaps or unjustified claims
3. Look for missing edge cases
4. Check for circular reasoning
5. Verify mathematical operations are correct
6. Ensure definitions are used properly
7. Check that all assumptions are stated

Be thorough but fair. Don't nitpick notation if the logic is sound.

Your response MUST follow this format:
VERIFICATION_STATUS: [VALID / INVALID / NEEDS_REVISION]

OVERALL_ASSESSMENT:
[Brief summary of the proof's correctness]

DETAILED_ANALYSIS:
[Step-by-step analysis of the proof]

ISSUES_FOUND:
[List any issues, or "None" if valid]

SUGGESTIONS:
[Suggestions for improvement, or "None" if valid]

CONFIDENCE: [0.0-1.0]"""

        prompt = f"""Rigorously verify the following mathematical proof.

PROBLEM STATEMENT:
{problem}

PROOF TO VERIFY:
{proof}

Provide your complete verification analysis:"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            thinking_mode=True,
            temperature=0.3  # Low for consistent verification
        )
        
        # Parse verification result
        content = response.content
        result = {
            "raw_response": content,
            "thinking": response.thinking,
            "is_valid": False,
            "status": "UNKNOWN",
            "issues": [],
            "suggestions": [],
            "confidence": 0.5
        }
        
        # Extract status
        if "VERIFICATION_STATUS:" in content:
            status_line = content.split("VERIFICATION_STATUS:")[1].split("\n")[0].strip()
            result["status"] = status_line
            result["is_valid"] = status_line == "VALID"
        
        # Extract confidence
        if "CONFIDENCE:" in content:
            try:
                conf_str = content.split("CONFIDENCE:")[1].split("\n")[0].strip()
                result["confidence"] = float(conf_str)
            except ValueError:
                pass
        
        # Extract issues
        if "ISSUES_FOUND:" in content:
            issues_section = content.split("ISSUES_FOUND:")[1]
            if "SUGGESTIONS:" in issues_section:
                issues_section = issues_section.split("SUGGESTIONS:")[0]
            issues = [line.strip() for line in issues_section.split("\n") 
                     if line.strip() and line.strip() != "None" and line.strip().startswith("-")]
            result["issues"] = issues
        
        # Extract suggestions
        if "SUGGESTIONS:" in content:
            suggestions_section = content.split("SUGGESTIONS:")[1]
            if "CONFIDENCE:" in suggestions_section:
                suggestions_section = suggestions_section.split("CONFIDENCE:")[0]
            suggestions = [line.strip() for line in suggestions_section.split("\n")
                          if line.strip() and line.strip() != "None" and line.strip().startswith("-")]
            result["suggestions"] = suggestions
        
        return result
    
    async def generate_feedback(
        self,
        problem: str,
        proof: str,
        verification_result: Dict[str, Any],
    ) -> str:
        """
        Generate actionable feedback for proof improvement.
        
        Args:
            problem: Original problem
            proof: Current proof
            verification_result: Output from verify_proof
            
        Returns:
            Structured feedback for GPT-5.2 to improve the proof
        """
        system_prompt = """You are helping improve a mathematical proof.
Based on the verification results, provide clear, actionable feedback.

Your feedback should:
1. Prioritize issues by severity
2. Explain exactly what needs to change
3. Suggest specific approaches to fix each issue
4. Be constructive and clear

Format your feedback as a numbered list of action items."""

        prompt = f"""Generate improvement feedback for this proof.

PROBLEM:
{problem}

CURRENT PROOF:
{proof}

VERIFICATION STATUS: {verification_result['status']}

ISSUES FOUND:
{chr(10).join(verification_result.get('issues', ['None']))}

SUGGESTIONS:
{chr(10).join(verification_result.get('suggestions', ['None']))}

Provide actionable improvement feedback:"""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5
        )
        
        return response.content
