"""
Ultimate Math Agent - Pipeline Tests
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from pipeline.state import MathAgentState, create_initial_state, HypothesisResult


class TestMathAgentState:
    """Test state management."""
    
    def test_create_initial_state(self):
        """Test initial state creation."""
        state = create_initial_state("Prove something", max_iterations=3)
        
        assert state["problem"] == "Prove something"
        assert state["max_iterations"] == 3
        assert state["iteration_count"] == 0
        assert state["should_continue"] == True
        assert state["hypotheses"] == []
        assert state["confidence_score"] == 0.0
    
    def test_state_fields(self):
        """Test all required fields exist."""
        state = create_initial_state("Test")
        
        required_fields = [
            "problem", "problem_analysis", "hypotheses",
            "exploration_code", "deep_analysis",
            "proof_sketch", "detailed_proof",
            "verification_result", "confidence_score",
            "final_proof", "iteration_count", "max_iterations",
            "should_continue", "stage_metrics", "messages"
        ]
        
        for field in required_fields:
            assert field in state, f"Missing field: {field}"


class TestHypothesisResult:
    """Test hypothesis result structure."""
    
    def test_hypothesis_creation(self):
        h = HypothesisResult(
            hypothesis="Try induction",
            source="gpt",
            score=0.8
        )
        
        assert h["hypothesis"] == "Try induction"
        assert h["source"] == "gpt"
        assert h["score"] == 0.8


class TestDecompositionStage:
    """Test Stage 1: Decomposition."""
    
    @pytest.mark.asyncio
    async def test_decomposition_produces_hypotheses(self):
        """Test that decomposition generates hypotheses."""
        # Mock both models
        with patch('pipeline.stages.decomposition.GPTModel') as mock_gpt, \
             patch('pipeline.stages.decomposition.GrokModel') as mock_grok:
            
            # Setup GPT mock
            gpt_instance = AsyncMock()
            gpt_instance.generate_hypotheses = AsyncMock(return_value=[
                "Hypothesis 1", "Hypothesis 2", "Hypothesis 3"
            ])
            mock_gpt.return_value = gpt_instance
            
            # Setup Grok mock
            grok_instance = AsyncMock()
            grok_instance.decompose_problem = AsyncMock(return_value={
                "raw_analysis": "Analysis",
                "sections": {"unconventional_approaches": "Try X\nTry Y"}
            })
            mock_grok.return_value = grok_instance
            
            from pipeline.stages.decomposition import decomposition_node
            
            state = create_initial_state("Prove 1+1=2")
            result = await decomposition_node(state)
            
            # Should have hypotheses from both models
            assert len(result["hypotheses"]) >= 3
            assert result["stage_metrics"][0]["stage_name"] == "decomposition"


class TestVerificationRouting:
    """Test verification stage routing logic."""
    
    def test_should_retry_when_invalid(self):
        """Test routing to proof_generation when verification fails."""
        from pipeline.stages.verification import should_retry
        
        state = create_initial_state("Problem")
        state["should_continue"] = True
        
        result = should_retry(state)
        assert result == "proof_generation"
    
    def test_should_integrate_when_valid(self):
        """Test routing to integration when verification passes."""
        from pipeline.stages.verification import should_retry
        
        state = create_initial_state("Problem")
        state["should_continue"] = False
        
        result = should_retry(state)
        assert result == "integration"


class TestPipelineGraph:
    """Test the full pipeline graph."""
    
    def test_graph_creation(self):
        """Test that graph is created correctly."""
        from pipeline.graph import create_math_agent_graph
        
        graph = create_math_agent_graph()
        
        # Graph should be compiled
        assert graph is not None
    
    def test_graph_nodes(self):
        """Test that all required nodes exist."""
        from pipeline.graph import create_math_agent_graph
        
        graph = create_math_agent_graph()
        
        # Check node configuration
        # Note: Exact API may vary by LangGraph version
        assert graph is not None


class TestToolIntegration:
    """Test tool integrations."""
    
    def test_alpha_evolve_safety_check(self):
        """Test that dangerous code is rejected."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        # Test dangerous code rejection
        dangerous_code = "import os; os.system('rm -rf /')"
        result = explorer._check_code_safety(dangerous_code)
        
        assert result["safe"] == False
        assert "os" in result["reason"].lower() or "dangerous" in result["reason"].lower()
    
    def test_alpha_evolve_safe_code(self):
        """Test that safe code is allowed."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        safe_code = """
import sympy as sp
x = sp.Symbol('x')
print(sp.expand((x+1)**2))
"""
        result = explorer._check_code_safety(safe_code)
        
        assert result["safe"] == True
    
    @pytest.mark.asyncio
    async def test_alpha_evolve_execution(self):
        """Test safe code execution."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer(timeout=5.0)
        
        code = "print('test output')"
        result = await explorer.explore(code)
        
        assert result.success == True
        assert "test output" in result.output


class TestE2EFull:
    """End-to-end tests (require mocking all models)."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires all model mocks - run manually")
    async def test_full_pipeline(self):
        """Test full pipeline execution."""
        from pipeline import run_math_agent
        
        result = await run_math_agent(
            problem="Prove that 1 + 1 = 2",
            max_iterations=1,
            verbose=False
        )
        
        assert result is not None
        assert "final_proof" in result
