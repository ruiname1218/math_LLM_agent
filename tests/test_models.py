"""
Ultimate Math Agent - Model Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.base_model import BaseModel, ModelResponse


class TestModelResponse:
    """Test ModelResponse dataclass."""
    
    def test_basic_response(self):
        resp = ModelResponse(content="Hello", model="test")
        assert resp.content == "Hello"
        assert resp.model == "test"
        assert not resp.has_thinking
    
    def test_response_with_thinking(self):
        resp = ModelResponse(
            content="Result",
            thinking="Let me think...",
            model="test"
        )
        assert resp.has_thinking
        assert resp.thinking == "Let me think..."
    
    def test_response_metadata(self):
        resp = ModelResponse(
            content="Answer",
            model="test",
            latency_ms=150.5,
            tokens_used=100,
            metadata={"key": "value"}
        )
        assert resp.latency_ms == 150.5
        assert resp.tokens_used == 100
        assert resp.metadata["key"] == "value"


class TestGPTModel:
    """Test GPT model interface."""
    
    @pytest.mark.asyncio
    async def test_generate_hypotheses_parsing(self):
        """Test that hypotheses are parsed correctly from response."""
        with patch('models.gpt_model.AsyncOpenAI') as mock_client:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = """
1. Try direct algebraic manipulation
2. Use proof by contradiction
3. Apply induction on n
4. Consider geometric interpretation
5. Use generating functions
"""
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = MagicMock(total_tokens=100)
            
            mock_instance = AsyncMock()
            mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance
            
            from models.gpt_model import GPTModel
            
            # Create model with mock config
            with patch('models.gpt_model.get_config') as mock_config:
                mock_config.return_value.gpt.api_key = "test-key"
                mock_config.return_value.gpt.model_id = "gpt-4"
                mock_config.return_value.gpt.temperature = 0.7
                mock_config.return_value.gpt.max_tokens = 1000
                mock_config.return_value.gpt.thinking_mode = True
                mock_config.return_value.gpt.name = "GPT Test"
                
                model = GPTModel()
                await model.initialize()
                
                hypotheses = await model.generate_hypotheses("Prove 1+1=2", count=5)
                
                assert len(hypotheses) >= 1
                assert any("algebraic" in h.lower() or "manipulation" in h.lower() for h in hypotheses)


class TestClaudeModel:
    """Test Claude model interface."""
    
    @pytest.mark.asyncio
    async def test_verification_parsing(self):
        """Test verification result parsing."""
        with patch('models.claude_model.AsyncAnthropic') as mock_client:
            mock_response = MagicMock()
            mock_response.content = [
                MagicMock(type="text", text="""
VERIFICATION_STATUS: VALID

OVERALL_ASSESSMENT:
The proof is correct and complete.

ISSUES_FOUND:
None

CONFIDENCE: 0.95
""")
            ]
            mock_response.stop_reason = "end_turn"
            mock_response.usage = MagicMock(input_tokens=50, output_tokens=100)
            
            mock_instance = AsyncMock()
            mock_instance.messages.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance
            
            from models.claude_model import ClaudeModel
            
            with patch('models.claude_model.get_config') as mock_config:
                mock_config.return_value.claude.api_key = "test-key"
                mock_config.return_value.claude.model_id = "claude-3"
                mock_config.return_value.claude.temperature = 0.5
                mock_config.return_value.claude.max_tokens = 1000
                mock_config.return_value.claude.thinking_mode = True
                mock_config.return_value.claude.name = "Claude Test"
                
                model = ClaudeModel()
                await model.initialize()
                
                result = await model.verify_proof("Problem", "Proof")
                
                assert result["is_valid"] == True
                assert result["status"] == "VALID"
                assert result["confidence"] == 0.95


class TestDeepSeekModel:
    """Test DeepSeek model interface."""
    
    @pytest.mark.asyncio
    async def test_refine_proof(self):
        """Test proof refinement."""
        with patch('models.deepseek_model.AsyncOpenAI') as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = """
Refined proof:
Step 1: Define terms
Step 2: Apply theorem
Step 3: Conclude
QED
"""
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = MagicMock(total_tokens=50)
            
            mock_instance = AsyncMock()
            mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance
            
            from models.deepseek_model import DeepSeekModel
            
            with patch('models.deepseek_model.get_config') as mock_config:
                mock_config.return_value.deepseek.api_key = "test-key"
                mock_config.return_value.deepseek.model_id = "deepseek-chat"
                mock_config.return_value.deepseek.temperature = 0.6
                mock_config.return_value.deepseek.max_tokens = 1000
                mock_config.return_value.deepseek.base_url = "https://api.deepseek.com/v1"
                mock_config.return_value.deepseek.name = "DeepSeek Test"
                
                model = DeepSeekModel()
                await model.initialize()
                
                refined = await model.refine_proof("Problem", "Draft proof")
                
                assert "Step 1" in refined
                assert "QED" in refined
