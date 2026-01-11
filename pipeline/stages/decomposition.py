"""
Ultimate Math Agent - Stage 1: Problem Decomposition
Parallel execution of GPT-5.2 Pro, Grok-4.2 Heavy, and Claude Opus 4.5 Thinking.
"""

import asyncio
import time
from typing import Dict, Any, List

from pipeline.state import MathAgentState, HypothesisResult, StageMetrics
from models import GPTModel, GrokModel, ClaudeModel
from config import get_config


async def decomposition_node(state: MathAgentState) -> Dict[str, Any]:
    """
    Stage 1: Problem Decomposition
    
    This stage runs 3 models in parallel:
    1. GPT-5.2 Pro: Generate 10-20 approach hypotheses
    2. Grok-4.2 Heavy: Creative/unconventional problem analysis
    3. Claude Opus 4.5 Thinking: Counter-example search, edge cases, traps
    
    Args:
        state: Current pipeline state with problem
        
    Returns:
        Updated state with hypotheses, analysis, and risk assessment
    """
    config = get_config()
    start_time = time.time()
    
    problem = state["problem"]
    
    # Initialize models
    gpt = GPTModel()
    grok = GrokModel()
    claude = ClaudeModel()
    
    await asyncio.gather(
        gpt.initialize(),
        grok.initialize(),
        claude.initialize()
    )
    
    # Run all 3 models in parallel
    gpt_task = gpt.generate_hypotheses(problem, count=15)
    grok_task = grok.decompose_problem(problem)
    claude_task = _claude_deep_analysis(claude, problem)
    
    results = await asyncio.gather(
        gpt_task,
        grok_task,
        claude_task,
        return_exceptions=True
    )
    
    gpt_hypotheses, grok_analysis, claude_analysis = results
    
    # Process results
    hypotheses: List[HypothesisResult] = []
    error_log: List[str] = []
    models_used = []
    
    # Process GPT hypotheses
    if isinstance(gpt_hypotheses, Exception):
        error_log.append(f"GPT-5.2 error: {str(gpt_hypotheses)}")
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
        error_log.append(f"Grok-4.2 error: {str(grok_analysis)}")
    else:
        models_used.append("grok-4.2-heavy")
        problem_analysis = grok_analysis
        
        # Extract additional hypotheses from Grok
        if "sections" in grok_analysis:
            unconventional = grok_analysis["sections"].get("unconventional_approaches", "")
            if unconventional:
                lines = [l.strip() for l in unconventional.split("\n") if l.strip()]
                for line in lines[:5]:
                    hypotheses.append(HypothesisResult(
                        hypothesis=line,
                        source="grok",
                        score=None
                    ))
    
    # Process Claude deep analysis (NEW)
    risk_assessment = {}
    if isinstance(claude_analysis, Exception):
        error_log.append(f"Claude-4.5 error: {str(claude_analysis)}")
    else:
        models_used.append("claude-opus-4.5")
        risk_assessment = claude_analysis
        
        # Add Claude's warnings to problem analysis
        problem_analysis["risk_assessment"] = risk_assessment
        
        # Extract potential counterexamples as warnings
        if risk_assessment.get("counterexamples"):
            problem_analysis["counterexample_warnings"] = risk_assessment["counterexamples"]
        
        # Extract edge cases to watch
        if risk_assessment.get("edge_cases"):
            problem_analysis["edge_cases"] = risk_assessment["edge_cases"]
    
    # Calculate stage metrics
    latency = (time.time() - start_time) * 1000
    
    stage_metrics = StageMetrics(
        stage_name="decomposition",
        latency_ms=latency,
        tokens_used=0,
        models_used=models_used
    )
    
    # Add message to history
    messages = state.get("messages", [])
    
    # Include Claude's warnings in the message
    warning_count = len(risk_assessment.get("edge_cases", [])) + len(risk_assessment.get("counterexamples", []))
    claude_msg = f", Claude found {warning_count} potential issues" if warning_count > 0 else ""
    
    messages.append({
        "role": "system",
        "content": f"[Stage 1 Complete] Generated {len(hypotheses)} hypotheses using {', '.join(models_used)}{claude_msg}"
    })
    
    return {
        "problem_analysis": problem_analysis,
        "hypotheses": hypotheses,
        "stage_metrics": [stage_metrics],
        "error_log": error_log,
        "messages": messages
    }


async def _claude_deep_analysis(claude: ClaudeModel, problem: str) -> Dict[str, Any]:
    """
    Claude Opus 4.5 Thinking for deep problem analysis.
    
    Focuses on:
    1. Counter-examples that might break naive approaches
    2. Edge cases that need special handling
    3. Hidden assumptions that could cause issues
    4. Traps and common mistakes
    
    Args:
        claude: Initialized Claude model
        problem: Mathematical problem to analyze
        
    Returns:
        Risk assessment dictionary
    """
    prompt = f"""あなたは数学的証明の「悪魔の代弁者」です。この問題について深く分析してください。

## 問題
{problem}

## 分析タスク

### 1. 反例探索 (COUNTEREXAMPLES)
この問題に対する素朴なアプローチを破壊する可能性のある反例やケースを探してください。
「この命題が偽になる状況はあるか？」を徹底的に考えてください。

### 2. エッジケース (EDGE_CASES)
特別な扱いが必要な境界条件や極端なケースをリストアップしてください：
- n=0, n=1 などの初期値
- 無限大への極限
- 負の数、複素数への拡張
- 特異点や未定義の状況

### 3. 暗黙の仮定 (HIDDEN_ASSUMPTIONS)
この問題が暗黙的に仮定していることを明示化してください。
これらの仮定が成り立たない場合はどうなりますか？

### 4. よくある間違い (COMMON_TRAPS)
この種の問題で数学者がよく犯す間違いは何ですか？

### 5. 証明の難所 (PROOF_DIFFICULTIES)
形式的な証明（Lean4など）で問題になりそうな箇所を特定してください。

## 出力形式
以下のJSONフォーマットで回答してください：

```json
{{
  "counterexamples": ["反例1の説明", "反例2の説明"],
  "edge_cases": ["エッジケース1", "エッジケース2"],
  "hidden_assumptions": ["仮定1", "仮定2"],
  "common_traps": ["よくある間違い1", "よくある間違い2"],
  "proof_difficulties": ["難所1", "難所2"],
  "overall_risk_level": "LOW/MEDIUM/HIGH",
  "recommendation": "この問題への推奨アプローチ"
}}
```"""

    response = await claude.generate(
        prompt=prompt,
        thinking_mode=True,
        temperature=0.3  # Lower for analytical task
    )
    
    # Parse JSON from response
    import json
    import re
    
    content = response.content
    
    # Extract JSON block
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try direct JSON parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Fallback: return raw analysis
    return {
        "raw_analysis": content,
        "counterexamples": [],
        "edge_cases": [],
        "hidden_assumptions": [],
        "common_traps": [],
        "proof_difficulties": [],
        "overall_risk_level": "UNKNOWN",
        "recommendation": ""
    }


async def decomposition_node_simple(state: MathAgentState) -> Dict[str, Any]:
    """
    Simplified decomposition using only GPT (fallback when other models unavailable).
    """
    start_time = time.time()
    problem = state["problem"]
    
    gpt = GPTModel()
    await gpt.initialize()
    
    gpt_hypotheses = await gpt.generate_hypotheses(problem, count=15)
    
    analysis_prompt = f"""Analyze this mathematical problem structure:

PROBLEM:
{problem}

Provide:
1. PROBLEM_TYPE: Classify the mathematical domain
2. KEY_STRUCTURES: Main mathematical concepts involved
3. DIFFICULTY_ASSESSMENT: Estimated difficulty and why
4. SUGGESTED_TECHNIQUES: Promising solution approaches
5. EDGE_CASES: Potential edge cases to watch for
6. POTENTIAL_TRAPS: Common mistakes to avoid"""

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
