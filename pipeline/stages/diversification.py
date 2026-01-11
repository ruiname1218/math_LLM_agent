"""
Ultimate Math Agent - Stage 2: Hypothesis Diversification
Parallel execution of Gemini 3 Pro (AlphaEvolve) and GPT-5.2 Pro for deep exploration.
"""

import asyncio
import time
from typing import Dict, Any

from pipeline.state import MathAgentState, StageMetrics
from models import GPTModel, GeminiModel
from config import get_config


async def diversification_node(state: MathAgentState) -> Dict[str, Any]:
    """
    Stage 2: Hypothesis Diversification
    
    This stage runs Gemini 3 Pro and GPT-5.2 Pro in parallel:
    - Gemini generates AlphaEvolve-style exploration code
    - GPT-5.2 performs deep analysis of hypotheses
    
    Args:
        state: Current state with hypotheses from Stage 1
        
    Returns:
        Updated state with exploration code and deep analysis
    """
    config = get_config()
    start_time = time.time()
    
    problem = state["problem"]
    hypotheses = [h["hypothesis"] for h in state["hypotheses"]]
    
    # Initialize models
    gpt = GPTModel()
    gemini = GeminiModel()
    await gpt.initialize()
    await gemini.initialize()
    
    # Run both in parallel
    gemini_task = gemini.generate_exploration_code(problem, hypotheses)
    gpt_task = _gpt_deep_analysis(gpt, problem, hypotheses, state.get("problem_analysis", {}))
    
    exploration_code, deep_analysis = await asyncio.gather(
        gemini_task,
        gpt_task,
        return_exceptions=True
    )
    
    # Process results
    error_log = []
    models_used = []
    
    if isinstance(exploration_code, Exception):
        error_log.append(f"Gemini error: {str(exploration_code)}")
        exploration_code = ""
    else:
        models_used.append("gemini-3-pro")
    
    if isinstance(deep_analysis, Exception):
        error_log.append(f"GPT-5.2 error: {str(deep_analysis)}")
        deep_analysis = ""
    else:
        models_used.append("gpt-5.2-pro")
    
    # Optionally execute exploration code
    code_execution_result = None
    if exploration_code and config.pipeline.verbose:
        code_execution_result = await _safe_execute_exploration(exploration_code)
    
    latency = (time.time() - start_time) * 1000
    
    messages = state.get("messages", [])
    messages.append({
        "role": "system",
        "content": f"[Stage 2 Complete] Generated exploration code and deep analysis"
    })
    
    return {
        "exploration_code": exploration_code,
        "code_execution_result": code_execution_result,
        "deep_analysis": deep_analysis,
        "stage_metrics": [StageMetrics(
            stage_name="diversification",
            latency_ms=latency,
            tokens_used=0,
            models_used=models_used
        )],
        "error_log": error_log,
        "messages": messages
    }


async def _gpt_deep_analysis(
    gpt: GPTModel,
    problem: str,
    hypotheses: list[str],
    problem_analysis: dict
) -> str:
    """
    GPT-5.2 performs deep analysis of the hypotheses.
    
    This complements Gemini's computational exploration with
    deeper conceptual reasoning.
    """
    system_prompt = """You are GPT-5.2 Pro, performing deep mathematical analysis.
Your role in this stage is to:
1. Evaluate each hypothesis for viability
2. Identify connections between hypotheses
3. Prioritize the most promising approaches
4. Suggest how to combine or refine hypotheses
5. Identify any missing approaches

Be thorough and creative. Think deeply about the mathematical structures."""

    hypotheses_text = "\n".join(f"{i+1}. {h}" for i, h in enumerate(hypotheses[:15]))
    
    analysis_text = ""
    if problem_analysis:
        analysis_text = f"\nPROBLEM ANALYSIS:\n{problem_analysis.get('raw_analysis', '')[:2000]}"
    
    prompt = f"""Perform deep analysis of these approach hypotheses.

PROBLEM:
{problem}
{analysis_text}

HYPOTHESES:
{hypotheses_text}

Provide:

1. HYPOTHESIS EVALUATION
[Rate each hypothesis 1-10 and explain briefly]

2. CONNECTIONS
[Identify conceptual links between hypotheses]

3. PRIORITY RANKING
[Rank top 5 most promising approaches]

4. SYNTHESIS
[Suggest how to combine approaches]

5. MISSING APPROACHES
[Identify overlooked techniques]"""

    response = await gpt.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        thinking_mode=True,
        temperature=0.7
    )
    
    return response.content


async def _safe_execute_exploration(code: str) -> str:
    """
    Safely execute exploration code in a restricted environment.
    
    This is a simplified version - in production, use a sandbox.
    """
    import io
    import sys
    from contextlib import redirect_stdout, redirect_stderr
    
    # Safety check - only allow safe imports
    allowed_imports = ["sympy", "numpy", "math", "fractions", "itertools", "functools"]
    
    for line in code.split("\n"):
        if line.strip().startswith("import ") or "from " in line:
            module = line.split()[1].split(".")[0]
            if module not in allowed_imports:
                return f"Error: Import of '{module}' not allowed for safety"
    
    # Limit execution time and capture output
    try:
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Create restricted globals
        restricted_globals = {
            "__builtins__": {
                "print": print,
                "range": range,
                "len": len,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "tuple": tuple,
                "dict": dict,
                "set": set,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sorted": sorted,
                "reversed": reversed,
                "True": True,
                "False": False,
                "None": None,
            }
        }
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, restricted_globals)
        
        output = stdout_capture.getvalue()
        errors = stderr_capture.getvalue()
        
        if errors:
            return f"Output:\n{output}\n\nWarnings:\n{errors}"
        return output if output else "Code executed successfully (no output)"
        
    except Exception as e:
        return f"Execution error: {str(e)}"


async def diversification_node_simple(state: MathAgentState) -> Dict[str, Any]:
    """
    Simplified diversification using only GPT (fallback).
    """
    start_time = time.time()
    
    problem = state["problem"]
    hypotheses = [h["hypothesis"] for h in state["hypotheses"]]
    
    gpt = GPTModel()
    await gpt.initialize()
    
    # GPT does both exploration and analysis
    deep_analysis = await _gpt_deep_analysis(gpt, problem, hypotheses, state.get("problem_analysis", {}))
    
    # Generate basic exploration code
    exploration_code = f'''# Exploration code generated by GPT-5.2
import sympy as sp
from sympy import symbols, simplify, solve

# Problem: {problem[:100]}...

# Key hypotheses to explore:
# {chr(10).join("# - " + h[:80] for h in hypotheses[:5])}

# TODO: Implement computational exploration
print("Exploration skeleton - implement based on hypotheses")
'''
    
    latency = (time.time() - start_time) * 1000
    
    return {
        "exploration_code": exploration_code,
        "code_execution_result": None,
        "deep_analysis": deep_analysis,
        "stage_metrics": [StageMetrics(
            stage_name="diversification",
            latency_ms=latency,
            tokens_used=0,
            models_used=["gpt-5.2-pro"]
        )],
        "error_log": [],
        "messages": state.get("messages", []) + [{
            "role": "system",
            "content": "[Stage 2 Complete] Deep analysis completed"
        }]
    }
