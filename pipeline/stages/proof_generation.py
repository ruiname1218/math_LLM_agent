"""
Ultimate Math Agent - Stage 3: Proof Sketch Generation
GPT-5.2 Pro creates main proof draft, DeepSeek-Math-V2 refines and self-corrects.
"""

import time
from typing import Dict, Any

from pipeline.state import MathAgentState, StageMetrics
from models import GPTModel, DeepSeekModel
from config import get_config


async def proof_generation_node(state: MathAgentState) -> Dict[str, Any]:
    """
    Stage 3: Proof Sketch Generation
    
    This stage uses:
    - GPT-5.2 Pro Extended Thinking to create the main proof sketch
    - DeepSeek-Math-V2 to refine and self-correct
    
    If this is a retry after verification failure, the verification
    feedback is incorporated into the regeneration.
    
    Args:
        state: Current state with hypotheses and analysis
        
    Returns:
        Updated state with proof_sketch and detailed_proof
    """
    config = get_config()
    start_time = time.time()
    
    problem = state["problem"]
    hypotheses = [h["hypothesis"] for h in state["hypotheses"][:10]]  # Top 10
    deep_analysis = state.get("deep_analysis", "")
    exploration_results = state.get("code_execution_result", "")
    
    # Check if this is a retry
    is_retry = state["iteration_count"] > 0
    verification_feedback = state.get("verification_feedback", "") if is_retry else ""
    previous_proof = state.get("detailed_proof", "") if is_retry else ""
    
    # Initialize models
    gpt = GPTModel()
    deepseek = DeepSeekModel()
    await gpt.initialize()
    await deepseek.initialize()
    
    error_log = []
    models_used = []
    
    # Step 1: GPT-5.2 generates proof sketch
    try:
        proof_sketch = await _gpt_generate_proof_sketch(
            gpt, problem, hypotheses, deep_analysis, 
            exploration_results, verification_feedback, previous_proof
        )
        models_used.append("gpt-5.2-pro")
    except Exception as e:
        error_log.append(f"GPT proof generation error: {str(e)}")
        proof_sketch = ""
    
    # Step 2: DeepSeek refines the proof
    detailed_proof = proof_sketch
    if proof_sketch:
        try:
            detailed_proof = await deepseek.refine_proof(
                problem=problem,
                proof_sketch=proof_sketch,
                feedback=verification_feedback
            )
            models_used.append("deepseek-math-v2")
            
            # Step 3: DeepSeek self-correction
            detailed_proof = await deepseek.self_correct(
                problem=problem,
                proof=detailed_proof,
                max_iterations=2  # Quick self-correction
            )
        except Exception as e:
            error_log.append(f"DeepSeek refinement error: {str(e)}")
            detailed_proof = proof_sketch
    
    latency = (time.time() - start_time) * 1000
    
    messages = state.get("messages", [])
    iteration_info = f" (Iteration {state['iteration_count'] + 1})" if is_retry else ""
    messages.append({
        "role": "system",
        "content": f"[Stage 3 Complete{iteration_info}] Proof generated and refined"
    })
    
    return {
        "proof_sketch": proof_sketch,
        "detailed_proof": detailed_proof,
        "iteration_count": state["iteration_count"] + 1,
        "stage_metrics": [StageMetrics(
            stage_name="proof_generation",
            latency_ms=latency,
            tokens_used=0,
            models_used=models_used
        )],
        "error_log": error_log,
        "messages": messages
    }


async def _gpt_generate_proof_sketch(
    gpt: GPTModel,
    problem: str,
    hypotheses: list[str],
    deep_analysis: str,
    exploration_results: str,
    verification_feedback: str,
    previous_proof: str
) -> str:
    """
    GPT-5.2 Pro generates the main proof sketch.
    
    Uses Extended Thinking for deep reasoning about the proof structure.
    """
    system_prompt = """You are GPT-5.2 Pro with Extended Thinking, the world's most capable mathematical proof generator.

Your task is to create a rigorous mathematical proof. Follow these principles:
1. Start with a clear high-level strategy
2. State all assumptions and definitions explicitly
3. Proceed step by step with justification for each claim
4. Handle all cases exhaustively
5. Conclude with a clear statement of what was proven

Use precise mathematical notation and clear logical flow.
If this is a retry after verification failure, carefully address all feedback."""

    hypotheses_text = "\n".join(f"• {h}" for h in hypotheses[:5])
    
    prompt = f"""Generate a rigorous mathematical proof for the following problem.

PROBLEM:
{problem}

TOP APPROACH HYPOTHESES:
{hypotheses_text}
"""
    
    if deep_analysis:
        # Include summary of analysis
        prompt += f"""
ANALYSIS SUMMARY:
{deep_analysis[:2000]}
"""
    
    if exploration_results:
        prompt += f"""
COMPUTATIONAL EXPLORATION RESULTS:
{exploration_results[:1000]}
"""
    
    if verification_feedback and previous_proof:
        prompt += f"""
⚠️ PREVIOUS ATTEMPT FAILED VERIFICATION

PREVIOUS PROOF:
{previous_proof[:3000]}

VERIFICATION FEEDBACK TO ADDRESS:
{verification_feedback}

Please generate an improved proof that addresses all the issues above.
"""
    
    prompt += """
Generate your proof now. Structure it as:

PROOF STRATEGY:
[High-level approach]

PROOF:
[Detailed proof with numbered steps or clear logical flow]

QED"""

    response = await gpt.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        thinking_mode=True,
        temperature=0.5  # Balanced for creativity and precision
    )
    
    return response.content


async def proof_generation_node_simple(state: MathAgentState) -> Dict[str, Any]:
    """
    Simplified proof generation using only GPT (fallback).
    """
    start_time = time.time()
    
    problem = state["problem"]
    hypotheses = [h["hypothesis"] for h in state["hypotheses"][:10]]
    
    gpt = GPTModel()
    await gpt.initialize()
    
    proof_sketch = await _gpt_generate_proof_sketch(
        gpt, problem, hypotheses,
        state.get("deep_analysis", ""),
        state.get("code_execution_result", ""),
        state.get("verification_feedback", ""),
        state.get("detailed_proof", "")
    )
    
    latency = (time.time() - start_time) * 1000
    
    return {
        "proof_sketch": proof_sketch,
        "detailed_proof": proof_sketch,  # No refinement
        "iteration_count": state["iteration_count"] + 1,
        "stage_metrics": [StageMetrics(
            stage_name="proof_generation",
            latency_ms=latency,
            tokens_used=0,
            models_used=["gpt-5.2-pro"]
        )],
        "error_log": [],
        "messages": state.get("messages", []) + [{
            "role": "system",
            "content": "[Stage 3 Complete] Proof generated"
        }]
    }
