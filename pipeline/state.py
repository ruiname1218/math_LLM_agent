"""
Ultimate Math Agent - Pipeline State Definition
Shared state that flows through all stages of the multi-model pipeline.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add


class VerificationResult(TypedDict):
    """Result from Claude's verification stage."""
    is_valid: bool
    status: str  # VALID, INVALID, NEEDS_REVISION
    issues: List[str]
    suggestions: List[str]
    confidence: float
    raw_response: str
    thinking: Optional[str]


class HypothesisResult(TypedDict):
    """Result from hypothesis generation."""
    hypothesis: str
    source: str  # gpt, grok, or merged
    score: Optional[float]


class StageMetrics(TypedDict):
    """Metrics for a single stage execution."""
    stage_name: str
    latency_ms: float
    tokens_used: int
    models_used: List[str]


class MathAgentState(TypedDict):
    """
    Shared state for the math agent pipeline.
    
    This state flows through all 5 stages:
    1. Problem Decomposition → hypotheses
    2. Hypothesis Diversification → exploration_code, deep_analysis
    3. Proof Sketch Generation → proof_sketch, detailed_proof
    4. Rigorous Verification → verification_result, confidence_score
    5. Integration & Final Output → final_proof
    
    The state uses TypedDict for type safety and LangGraph compatibility.
    """
    
    # Input
    problem: str
    
    # Stage 1: Problem Decomposition
    problem_analysis: Dict[str, Any]
    hypotheses: Annotated[List[HypothesisResult], add]  # Accumulated across iterations
    
    # Stage 2: Hypothesis Diversification
    exploration_code: str
    code_execution_result: Optional[str]
    deep_analysis: str
    
    # Stage 3: Proof Sketch Generation
    proof_sketch: str
    detailed_proof: str
    
    # Stage 4: Rigorous Verification
    verification_result: VerificationResult
    verification_feedback: str
    confidence_score: float
    lean4_code: Optional[str]
    lean4_verified: bool
    lean4_is_rigorous: bool  # True only if no sorry and fully compiled
    lean4_attempts: int      # Number of refinement attempts for Lean4
    
    # Stage 5: Integration
    final_proof: str
    
    # Control flow
    iteration_count: int
    max_iterations: int
    should_continue: bool
    
    # Metrics and history
    stage_metrics: Annotated[List[StageMetrics], add]
    error_log: Annotated[List[str], add]
    
    # Full conversation for context
    messages: List[Dict[str, str]]


def create_initial_state(problem: str, max_iterations: int = 5) -> MathAgentState:
    """
    Create the initial state for a new math problem.
    
    Args:
        problem: The mathematical problem to solve
        max_iterations: Maximum number of verification → regeneration loops
        
    Returns:
        Initialized MathAgentState
    """
    return MathAgentState(
        # Input
        problem=problem,
        
        # Stage 1
        problem_analysis={},
        hypotheses=[],
        
        # Stage 2
        exploration_code="",
        code_execution_result=None,
        deep_analysis="",
        
        # Stage 3
        proof_sketch="",
        detailed_proof="",
        
        # Stage 4
        verification_result={
            "is_valid": False,
            "status": "PENDING",
            "issues": [],
            "suggestions": [],
            "confidence": 0.0,
            "raw_response": "",
            "thinking": None
        },
        verification_feedback="",
        confidence_score=0.0,
        lean4_code=None,
        lean4_verified=False,
        lean4_is_rigorous=False,
        lean4_attempts=0,
        
        # Stage 5
        final_proof="",
        
        # Control
        iteration_count=0,
        max_iterations=max_iterations,
        should_continue=True,
        
        # Metrics
        stage_metrics=[],
        error_log=[],
        
        # Messages
        messages=[]
    )
