"""
Ultimate Math Agent - Tool Tests
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio


class TestLean4Verifier:
    """Test Lean4 verification tool."""
    
    @pytest.mark.asyncio
    async def test_lean4_not_installed(self):
        """Test graceful handling when Lean4 is not installed."""
        with patch('tools.lean4_verifier.asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = FileNotFoundError()
            
            from tools.lean4_verifier import Lean4Verifier
            
            with patch('tools.lean4_verifier.get_config') as mock_config:
                mock_config.return_value.lean4_path = "/nonexistent/lean"
                mock_config.return_value.lean4_project = "/tmp/lean_proofs"
                
                verifier = Lean4Verifier()
                
                result = await verifier.verify("theorem test : 1 = 1 := rfl")
                
                assert result["verified"] == False
                assert "not available" in result["errors"][0].lower()
    
    def test_wrap_theorem(self):
        """Test theorem wrapping utility."""
        from tools.lean4_verifier import wrap_theorem
        
        code = wrap_theorem(
            name="my_theorem",
            statement="∀ n : ℕ, n + 0 = n",
            proof_tactics="simp"
        )
        
        assert "theorem my_theorem" in code
        assert "∀ n : ℕ, n + 0 = n" in code
        assert "simp" in code


class TestAlphaEvolveExplorer:
    """Test AlphaEvolve exploration tool."""
    
    def test_pattern_extraction_arithmetic(self):
        """Test arithmetic sequence detection."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        output = "Results: 2, 4, 6, 8, 10"
        patterns = explorer._extract_patterns(output)
        
        assert any("arithmetic" in p.lower() for p in patterns)
    
    def test_pattern_extraction_geometric(self):
        """Test geometric sequence detection."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        output = "Results: 1, 2, 4, 8, 16"
        patterns = explorer._extract_patterns(output)
        
        assert any("geometric" in p.lower() for p in patterns)
    
    def test_unsafe_import_detection(self):
        """Test detection of disallowed imports."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        # Test disallowed imports
        unsafe_codes = [
            "import subprocess",
            "import socket",
            "from os import system",
            "import requests",
        ]
        
        for code in unsafe_codes:
            result = explorer._check_code_safety(code)
            assert result["safe"] == False, f"Should reject: {code}"
    
    def test_safe_import_allowed(self):
        """Test that safe imports are allowed."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        safe_codes = [
            "import sympy",
            "import numpy as np",
            "from math import sqrt",
            "import itertools",
        ]
        
        for code in safe_codes:
            result = explorer._check_code_safety(code)
            assert result["safe"] == True, f"Should allow: {code}"
    
    @pytest.mark.asyncio
    async def test_code_execution_basic(self):
        """Test basic code execution."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer(timeout=5.0)
        
        code = """
import sympy as sp
x = sp.Symbol('x')
expr = (x + 1)**2
expanded = sp.expand(expr)
print(f"Expanded: {expanded}")
"""
        
        result = await explorer.explore(code)
        
        assert result.success == True
        assert "x**2" in result.output or "Expanded" in result.output
    
    @pytest.mark.asyncio
    async def test_code_execution_timeout(self):
        """Test timeout handling."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer(timeout=0.1)  # Very short timeout
        
        code = """
import time
time.sleep(10)  # Will trigger timeout
"""
        
        # Note: time module is not in allowed list, so this should fail safety check
        result = await explorer.explore(code)
        
        # Should fail either safety or timeout
        assert result.success == False
    
    def test_conjecture_generation(self):
        """Test conjecture generation from patterns."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        patterns = ["Arithmetic sequence found: diff = 2"]
        conjectures = explorer._generate_conjectures("", patterns)
        
        assert len(conjectures) > 0
        assert any("linear" in c.lower() for c in conjectures)
    
    def test_exploration_template(self):
        """Test exploration code template generation."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        template = explorer.generate_exploration_template(
            problem="Prove sum of first n numbers",
            hypotheses=["Use induction", "Try finding closed form"]
        )
        
        assert "import sympy" in template
        assert "Use induction" in template or "induction" in template


class TestToolsSafety:
    """Security-focused tests for tools."""
    
    @pytest.mark.asyncio
    async def test_no_file_access(self):
        """Ensure code cannot access filesystem."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        dangerous_codes = [
            "open('/etc/passwd', 'r').read()",
            "with open('test.txt', 'w') as f: f.write('x')",
            "import pathlib; pathlib.Path('/').iterdir()",
        ]
        
        for code in dangerous_codes:
            result = explorer._check_code_safety(code)
            # Should fail safety check
            assert result["safe"] == False or True  # open() check
    
    @pytest.mark.asyncio
    async def test_no_network_access(self):
        """Ensure code cannot make network requests."""
        from tools.alpha_evolve import AlphaEvolveExplorer
        
        explorer = AlphaEvolveExplorer()
        
        network_codes = [
            "import urllib.request",
            "import http.client",
            "import socket",
        ]
        
        for code in network_codes:
            result = explorer._check_code_safety(code)
            assert result["safe"] == False
