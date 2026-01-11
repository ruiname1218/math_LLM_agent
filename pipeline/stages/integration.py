"""
Ultimate Math Agent - Stage 5: Integration & Final Output
GPT-5.2 Pro Extended Thinking consolidates all outputs into final proof.
"""

import time
from typing import Dict, Any

from pipeline.state import MathAgentState, StageMetrics
from models import GPTModel
from config import get_config


async def integration_node(state: MathAgentState) -> Dict[str, Any]:
    """
    Stage 5: Integration & Final Output
    
    GPT-5.2 Pro Extended Thinking consolidates all previous outputs:
    - Resolves any remaining inconsistencies
    - Formats the proof for maximum clarity
    - Adds final polish and verification summary
    
    Args:
        state: Final state with verified proof
        
    Returns:
        Updated state with final_proof
    """
    config = get_config()
    start_time = time.time()
    
    problem = state["problem"]
    detailed_proof = state["detailed_proof"]
    verification_result = state["verification_result"]
    confidence_score = state["confidence_score"]
    lean4_code = state.get("lean4_code")
    lean4_verified = state.get("lean4_verified", False)
    
    # Initialize GPT
    gpt = GPTModel()
    await gpt.initialize()
    
    # Prepare context
    verification_summary = f"""
Verification Status: {verification_result['status']}
Confidence Score: {confidence_score:.1%}
Claude Assessment: {'Approved' if verification_result['is_valid'] else 'Concerns noted'}
Lean4 Formal Verification: {'Verified ✓' if lean4_verified else 'Not performed'}
"""
    
    # Generate final integrated proof
    system_prompt = """You are GPT-5.2 Pro with Extended Thinking, performing final integration.

Your task is to create the definitive, publication-ready proof by:
1. Reviewing all work done so far
2. Resolving any minor inconsistencies
3. Ensuring logical flow is impeccable
4. Adding clear section headers
5. Including a verification summary
6. Formatting for maximum readability

The output should be a complete, self-contained mathematical document."""

    prompt = f"""Create the final, integrated proof for publication.

ORIGINAL PROBLEM:
{problem}

VERIFIED PROOF:
{detailed_proof}

VERIFICATION SUMMARY:
{verification_summary}
"""
    
    if verification_result.get("suggestions"):
        suggestions = "\n".join(f"- {s}" for s in verification_result["suggestions"])
        prompt += f"""
MINOR SUGGESTIONS TO CONSIDER:
{suggestions}
"""
    
    prompt += """
Generate the final, polished proof document with:

1. PROBLEM STATEMENT
2. PROOF STRATEGY  
3. DETAILED PROOF
4. VERIFICATION SUMMARY
5. CONCLUSION

Make it publication-ready."""

    response = await gpt.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        thinking_mode=True,
        temperature=0.4  # Low for consistency
    )
    
    final_proof = response.content
    
    # Append Lean4 code if available
    if lean4_code and lean4_verified:
        final_proof += f"""

---

## FORMAL VERIFICATION (Lean4)

The following Lean4 code formally verifies key aspects of this proof:

```lean4
{lean4_code}
```

✓ Lean4 verification: PASSED
"""
    
    latency = (time.time() - start_time) * 1000
    
    messages = state.get("messages", [])
    messages.append({
        "role": "system",
        "content": f"[Stage 5 Complete] ✨ Final proof generated with {confidence_score:.0%} confidence"
    })
    
    return {
        "final_proof": final_proof,
        "stage_metrics": [StageMetrics(
            stage_name="integration",
            latency_ms=latency,
            tokens_used=response.tokens_used,
            models_used=["gpt-5.2-pro"]
        )],
        "error_log": [],
        "messages": messages
    }


async def integration_node_simple(state: MathAgentState) -> Dict[str, Any]:
    """
    Simplified integration that just formats the proof.
    """
    start_time = time.time()
    
    problem = state["problem"]
    proof = state["detailed_proof"]
    confidence = state["confidence_score"]
    verification = state["verification_result"]
    
    # Simple formatting without additional LLM call
    final_proof = f"""# Mathematical Proof

## Problem Statement
{problem}

## Proof
{proof}

---

## Verification Summary
- Status: {verification['status']}
- Confidence: {confidence:.1%}
- Iterations: {state['iteration_count']}
"""
    
    latency = (time.time() - start_time) * 1000
    
    return {
        "final_proof": final_proof,
        "stage_metrics": [StageMetrics(
            stage_name="integration",
            latency_ms=latency,
            tokens_used=0,
            models_used=[]
        )],
        "error_log": [],
        "messages": state.get("messages", []) + [{
            "role": "system",
            "content": "[Stage 5 Complete] Proof formatted"
        }]
    }
