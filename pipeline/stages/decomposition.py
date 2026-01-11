"""
Ultimate Math Agent - Stage 1: Problem Decomposition
Parallel execution of GPT-5.2 Pro and Grok-4.2 Heavy for problem analysis.
"""

import asyncio
import time
from typing import Dict, Any

from pipeline.state import MathAgentState, HypothesisResult, StageMetrics
from models import GPTModel, GrokModel
from config import get_config


async def decomposition_node(state: MathAgentState) -> Dict[str, Any]:
    """
    Stage 1: Problem Decomposition
    
    This stage runs GPT-5.2 Pro and Grok-4.2 Heavy in parallel to:
    1. Deeply analyze the mathematical problem structure
    2. Generate 10-20 creative approach hypotheses
    3. Identify key mathematical concepts and techniques
    
    GPT-5.2 is the primary generator, Grok provides complementary insights.
    
    Args:
        state: Current pipeline state with problem
        
    Returns:
        Updated state with hypotheses and analysis
    """
    config = get_config()
    start_time = time.time()
    
    problem = state["problem"]
    
    # Initialize models
    gpt = GPTModel()
    grok = GrokModel()
    await gpt.initialize()
    await grok.initialize()
    
    # Run both models in parallel
    gpt_task = gpt.generate_hypotheses(problem, count=15)
    grok_task = grok.decompose_problem(problem)
    
    gpt_hypotheses, grok_analysis = await asyncio.gather(
        gpt_task,
        grok_task,
        return_exceptions=True
    )
    
    # Process results
    hypotheses: list[HypothesisResult] = []
    error_log: list[str] = []
    models_used = []
    
    # Process GPT hypotheses
    if isinstance(gpt_hypotheses, Exception):
        error_log.append(f"GPT-5.2 error in decomposition: {str(gpt_hypotheses)}")
    else:
        models_used.append("gpt-5.2-pro")
        for h in gpt_hypotheses:
            hypotheses.append(HypothesisResult(
                hypothesis=h,
                source="gpt",
                score=None
            ))
    
    # Process Grok analysis
    problem_analysis = {}
    if isinstance(grok_analysis, Exception):
        error_log.append(f"Grok-4.2 error in decomposition: {str(grok_analysis)}")
    else:
        models_used.append("grok-4.2-heavy")
        problem_analysis = grok_analysis
        
        # Extract additional hypotheses from Grok's unconventional approaches
        if "sections" in grok_analysis:
            unconventional = grok_analysis["sections"].get("unconventional_approaches", "")
            if unconventional:
                lines = [l.strip() for l in unconventional.split("\n") if l.strip()]
                for line in lines[:5]:  # Add up to 5 from Grok
                    hypotheses.append(HypothesisResult(
                        hypothesis=line,
                        source="grok",
                        score=None
                    ))
    
    # Calculate stage metrics
    latency = (time.time() - start_time) * 1000
    
    stage_metrics = StageMetrics(
        stage_name="decomposition",
        latency_ms=latency,
        tokens_used=0,  # TODO: Track actual tokens
        models_used=models_used
    )
    
    # Add message to history
    messages = state.get("messages", [])
    messages.append({
        "role": "system",
        "content": f"[Stage 1 Complete] Generated {len(hypotheses)} hypotheses using {', '.join(models_used)}"
    })
    
    return {
        "problem_analysis": problem_analysis,
        "hypotheses": hypotheses,
        "stage_metrics": [stage_metrics],
        "error_log": error_log,
        "messages": messages
    }


async def decomposition_node_simple(state: MathAgentState) -> Dict[str, Any]:
    """
    Simplified decomposition using only GPT (fallback when Grok unavailable).
    """
    start_time = time.time()
    problem = state["problem"]
    
    gpt = GPTModel()
    await gpt.initialize()
    
    # Generate hypotheses
    gpt_hypotheses = await gpt.generate_hypotheses(problem, count=15)
    
    # Also get problem analysis from GPT
    analysis_prompt = f"""Analyze this mathematical problem structure:

PROBLEM:
{problem}

Provide:
1. PROBLEM_TYPE: Classify the mathematical domain
2. KEY_STRUCTURES: Main mathematical concepts involved
3. DIFFICULTY_ASSESSMENT: Estimated difficulty and why
4. SUGGESTED_TECHNIQUES: Promising solution approaches"""

    analysis_response = await gpt.generate(
        prompt=analysis_prompt,
        thinking_mode=True
    )
    
    hypotheses = [
        HypothesisResult(hypothesis=h, source="gpt", score=None)
        for h in gpt_hypotheses
    ]
    
    latency = (time.time() - start_time) * 1000
    
    return {
        "problem_analysis": {"raw_analysis": analysis_response.content},
        "hypotheses": hypotheses,
        "stage_metrics": [StageMetrics(
            stage_name="decomposition",
            latency_ms=latency,
            tokens_used=analysis_response.tokens_used,
            models_used=["gpt-5.2-pro"]
        )],
        "error_log": [],
        "messages": state.get("messages", []) + [{
            "role": "system",
            "content": f"[Stage 1 Complete] Generated {len(hypotheses)} hypotheses"
        }]
    }
