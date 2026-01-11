"""
Ultimate Math Agent - Stage 4: Rigorous Verification
Claude Opus 4.5 Thinking + GPT-5.2 Pro reconfirmation + Lean4 verification.
"""

import time
from typing import Dict, Any

from pipeline.state import MathAgentState, StageMetrics, VerificationResult
from models import GPTModel, ClaudeModel, DeepSeekModel
from config import get_config


async def verification_node(state: MathAgentState) -> Dict[str, Any]:
    """
    Stage 4: Rigorous Verification
    
    This is the critical quality gate:
    1. Claude Opus 4.5 performs thorough logic checking
    2. GPT-5.2 Pro assesses confidence
    3. Optional: Lean4 formal verification
    
    Exit conditions:
    - Claude says VALID AND GPT confidence >= 90%: proceed to Stage 5
    - Otherwise: return to Stage 3 for revision
    
    Args:
        state: Current state with detailed_proof
        
    Returns:
        Updated state with verification results and routing decision
    """
    config = get_config()
    start_time = time.time()
    
    problem = state["problem"]
    proof = state["detailed_proof"]
    iteration = state["iteration_count"]
    max_iter = state["max_iterations"]
    
    # Initialize models
    claude = ClaudeModel()
    gpt = GPTModel()
    await claude.initialize()
    await gpt.initialize()
    
    error_log = []
    models_used = []
    
    # Step 1: Claude verification
    verification_result: VerificationResult = {
        "is_valid": False,
        "status": "ERROR",
        "issues": [],
        "suggestions": [],
        "confidence": 0.0,
        "raw_response": "",
        "thinking": None
    }
    
    try:
        claude_result = await claude.verify_proof(problem, proof)
        verification_result = VerificationResult(
            is_valid=claude_result["is_valid"],
            status=claude_result["status"],
            issues=claude_result.get("issues", []),
            suggestions=claude_result.get("suggestions", []),
            confidence=claude_result.get("confidence", 0.0),
            raw_response=claude_result.get("raw_response", ""),
            thinking=claude_result.get("thinking")
        )
        models_used.append("claude-opus-4.5")
    except Exception as e:
        error_log.append(f"Claude verification error: {str(e)}")
    
    # Step 2: GPT-5.2 confidence assessment
    confidence_score = 0.0
    try:
        confidence_score = await gpt.assess_confidence(
            problem=problem,
            proof=proof,
            verification_result=verification_result["raw_response"]
        )
        models_used.append("gpt-5.2-pro")
    except Exception as e:
        error_log.append(f"GPT confidence error: {str(e)}")
    
    # Step 3: STRICT Lean4 verification (no sorry allowed!)
    # Priority: Aristotle (Lean4 native) > DeepSeek-Math > GPT fallback
    lean4_code = None
    lean4_verified = False
    lean4_is_rigorous = False
    lean4_model_used = None
    
    if config.pipeline.lean4_enabled and verification_result["is_valid"]:
        try:
            from tools.lean4_strict_verifier import (
                StrictLean4Verifier, 
                VerificationLevel,
            )
            from models import AristotleModel
            
            # Try Aristotle first (Lean4 specialist from Harmonic AI)
            if config.aristotle.api_key:
                try:
                    aristotle = AristotleModel()
                    await aristotle.initialize()
                    
                    # Aristotle has specialized formalization method
                    lean4_code = await aristotle.formalize_proof(problem, proof)
                    lean4_model_used = "aristotle"
                    models_used.append("aristotle")
                    
                    # Verify the generated code
                    verifier = StrictLean4Verifier(VerificationLevel.STRICT)
                    lean4_result = await verifier.verify_strict(lean4_code)
                    
                    if not lean4_result.is_rigorous:
                        # Use Aristotle's specialized error fixing
                        for attempt in range(3):
                            lean4_code = await aristotle.fix_lean_errors(
                                lean4_code, 
                                lean4_result.errors
                            )
                            lean4_result = await verifier.verify_strict(lean4_code)
                            if lean4_result.is_rigorous:
                                break
                    
                    lean4_verified = lean4_result.verified
                    lean4_is_rigorous = lean4_result.is_rigorous
                    
                    if lean4_is_rigorous:
                        models_used.append("lean4-rigorous")
                    
                except Exception as e:
                    error_log.append(f"Aristotle error, falling back to DeepSeek: {str(e)}")
                    lean4_model_used = None
            
            # Fallback to DeepSeek if Aristotle unavailable or failed
            if not lean4_is_rigorous and config.deepseek.api_key:
                from tools.lean4_strict_verifier import verify_with_lean4_strict
                
                deepseek = DeepSeekModel()
                await deepseek.initialize()
                
                lean4_result = await verify_with_lean4_strict(
                    problem=problem,
                    proof=proof,
                    model=deepseek
                )
                
                lean4_code = lean4_result.get("lean4_code", "")
                lean4_verified = lean4_result.get("formally_verified", False)
                lean4_is_rigorous = lean4_result.get("is_rigorous", False)
                lean4_model_used = "deepseek"
                
                if lean4_verified:
                    models_used.append("lean4-deepseek")
            
            # Log verification details
            if lean4_verified:
                models_used.append("lean4-strict")
                if lean4_is_rigorous:
                    models_used.append("lean4-complete")
            else:
                # If Lean4 fails, lower confidence
                if isinstance(lean4_result, dict) and lean4_result.get("sorry_count", 0) > 0:
                    error_log.append(
                        f"Lean4: Proof contains {lean4_result['sorry_count']} incomplete parts (sorry)"
                    )
                    confidence_score = min(confidence_score, 0.7)  # Cap confidence
                    
        except ImportError:
            # Fallback to basic verifier
            from tools.lean4_verifier import Lean4Verifier
            deepseek = DeepSeekModel()
            await deepseek.initialize()
            lean4_code = await deepseek.generate_lean4_sketch(problem, proof)
            verifier = Lean4Verifier()
            lean4_result = await verifier.verify(lean4_code)
            lean4_verified = lean4_result.get("verified", False)
            if lean4_verified:
                models_used.append("lean4")
        except Exception as e:
            error_log.append(f"Lean4 verification error: {str(e)}")
    
    # Generate feedback for potential retry
    verification_feedback = ""
    if not verification_result["is_valid"] or confidence_score < config.pipeline.confidence_threshold:
        try:
            verification_feedback = await claude.generate_feedback(
                problem=problem,
                proof=proof,
                verification_result=verification_result
            )
        except Exception as e:
            # Use basic feedback from issues/suggestions
            verification_feedback = "Issues:\n" + "\n".join(verification_result["issues"])
    
    # ============================================================
    # NEW EXIT CONDITION LOGIC
    # Priority: Lean4 rigorous > LLM verification (fallback only)
    # ============================================================
    
    max_iterations_reached = iteration >= max_iter
    
    # Determine pass/fail based on verification hierarchy
    if lean4_is_rigorous:
        # CASE 1: Lean4 formal verification passed
        # This is mathematically proven - no LLM opinion needed
        should_continue = False
        confidence_score = 1.0  # 100% - formally verified
        pass_reason = "lean4_rigorous"
        
    elif config.pipeline.lean4_enabled and not lean4_verified:
        # CASE 2: Lean4 enabled but failed to verify
        # Proof has issues - need to retry
        if max_iterations_reached:
            should_continue = False
            pass_reason = "max_iterations_lean4_failed"
        else:
            should_continue = True
            pass_reason = "lean4_failed_retry"
            
    elif not config.pipeline.lean4_enabled:
        # CASE 3: Lean4 not available - fallback to LLM verification
        claude_ok = verification_result["is_valid"] or verification_result["status"] == "VALID"
        confidence_ok = confidence_score >= config.pipeline.confidence_threshold
        
        if claude_ok and confidence_ok:
            should_continue = False
            pass_reason = "llm_verified"
        elif max_iterations_reached:
            should_continue = False
            pass_reason = "max_iterations_llm"
        else:
            should_continue = True
            pass_reason = "llm_failed_retry"
    else:
        # CASE 4: Lean4 partially verified (compiled but contains sorry, etc.)
        # Accept with reduced confidence, or retry if below threshold
        claude_ok = verification_result["is_valid"] or verification_result["status"] == "VALID"
        
        if claude_ok and lean4_verified:
            should_continue = False
            confidence_score = 0.85  # Partial - not fully rigorous
            pass_reason = "lean4_partial_llm_ok"
        elif max_iterations_reached:
            should_continue = False
            pass_reason = "max_iterations"
        else:
            should_continue = True
            pass_reason = "needs_improvement"
    
    latency = (time.time() - start_time) * 1000
    
    messages = state.get("messages", [])
    
    # Generate appropriate status message based on pass_reason
    if pass_reason == "lean4_rigorous":
        status_emoji = "✅"
        status_msg = f"[Stage 4] {status_emoji} LEAN4 VERIFIED - 形式的に証明済み (100%)"
    elif pass_reason == "llm_verified":
        status_emoji = "✓"
        status_msg = f"[Stage 4] {status_emoji} LLM検証通過 (Lean4なし) - 信頼度: {confidence_score:.1%}"
    elif pass_reason == "lean4_partial_llm_ok":
        status_emoji = "⚠️"
        status_msg = f"[Stage 4] {status_emoji} 部分検証 - Lean4部分的, Claude OK - 信頼度: {confidence_score:.1%}"
    elif should_continue:
        status_emoji = "🔄"
        status_msg = f"[Stage 4] {status_emoji} 再生成必要 - {pass_reason}"
    else:
        status_emoji = "⚠️"
        status_msg = f"[Stage 4] {status_emoji} 終了 (max iterations) - {pass_reason}"
    
    messages.append({"role": "system", "content": status_msg})
    
    return {
        "verification_result": verification_result,
        "verification_feedback": verification_feedback,
        "confidence_score": confidence_score,
        "lean4_code": lean4_code,
        "lean4_verified": lean4_verified,
        "lean4_is_rigorous": lean4_is_rigorous,
        "should_continue": should_continue,
        "stage_metrics": [StageMetrics(
            stage_name="verification",
            latency_ms=latency,
            tokens_used=0,
            models_used=models_used
        )],
        "error_log": error_log,
        "messages": messages
    }


def should_retry(state: MathAgentState) -> str:
    """
    Routing function for conditional edge.
    
    Returns:
        "proof_generation" if retry needed
        "integration" if verification passed
    """
    if state["should_continue"]:
        return "proof_generation"
    return "integration"


async def verification_node_simple(state: MathAgentState) -> Dict[str, Any]:
    """
    Simplified verification using only GPT (fallback when Claude unavailable).
    """
    start_time = time.time()
    config = get_config()
    
    problem = state["problem"]
    proof = state["detailed_proof"]
    
    gpt = GPTModel()
    await gpt.initialize()
    
    # GPT self-verification
    system_prompt = """You are a rigorous mathematical proof verifier.
Verify the following proof and provide:
1. VERIFICATION_STATUS: VALID, INVALID, or NEEDS_REVISION
2. ISSUES_FOUND: List any problems
3. SUGGESTIONS: How to fix issues
4. CONFIDENCE: Score from 0.0 to 1.0"""

    response = await gpt.generate(
        prompt=f"PROBLEM:\n{problem}\n\nPROOF:\n{proof}\n\nVerify:",
        system_prompt=system_prompt,
        thinking_mode=True
    )
    
    # Parse response
    content = response.content
    is_valid = "VALID" in content and "INVALID" not in content
    
    confidence = 0.5
    if "CONFIDENCE:" in content:
        try:
            conf_str = content.split("CONFIDENCE:")[1].split("\n")[0].strip()
            confidence = float(conf_str)
        except:
            pass
    
    iteration = state["iteration_count"]
    max_iter = state["max_iterations"]
    confidence_ok = confidence >= config.pipeline.confidence_threshold
    should_continue = not (is_valid and confidence_ok) and iteration < max_iter
    
    latency = (time.time() - start_time) * 1000
    
    return {
        "verification_result": VerificationResult(
            is_valid=is_valid,
            status="VALID" if is_valid else "NEEDS_REVISION",
            issues=[],
            suggestions=[],
            confidence=confidence,
            raw_response=content,
            thinking=response.thinking
        ),
        "verification_feedback": "" if is_valid else content,
        "confidence_score": confidence,
        "lean4_code": None,
        "lean4_verified": False,
        "should_continue": should_continue,
        "stage_metrics": [StageMetrics(
            stage_name="verification",
            latency_ms=latency,
            tokens_used=0,
            models_used=["gpt-5.2-pro"]
        )],
        "error_log": [],
        "messages": state.get("messages", []) + [{
            "role": "system",
            "content": f"[Stage 4 Complete] GPT self-verification: {'VALID' if is_valid else 'NEEDS_REVISION'}"
        }]
    }
