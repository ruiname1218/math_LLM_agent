"""
Ultimate Math Agent - AlphaEvolve-style Exploration Tool
Generates and executes exploration code for mathematical pattern discovery.
"""

import asyncio
import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import sympy as sp
from sympy import symbols, simplify, solve, expand, factor


@dataclass
class ExplorationResult:
    """Result from exploration code execution."""
    success: bool
    output: str
    patterns_found: List[str]
    conjectures: List[str]
    error: Optional[str] = None


class AlphaEvolveExplorer:
    """
    AlphaEvolve-inspired mathematical exploration tool.
    
    This tool:
    1. Generates exploration code based on hypotheses
    2. Executes code in a sandboxed environment
    3. Analyzes output for patterns and conjectures
    4. Provides structured feedback for hypothesis refinement
    """
    
    # Safe builtins for code execution
    SAFE_BUILTINS = {
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
        "all": all,
        "any": any,
        "round": round,
        "pow": pow,
        "True": True,
        "False": False,
        "None": None,
    }
    
    # Allowed imports
    ALLOWED_IMPORTS = {
        "sympy",
        "numpy",
        "math",
        "fractions",
        "itertools",
        "functools",
        "collections",
        "decimal",
    }
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize the explorer.
        
        Args:
            timeout: Maximum execution time in seconds
        """
        self.timeout = timeout
    
    async def explore(
        self,
        code: str,
        problem_context: str = ""
    ) -> ExplorationResult:
        """
        Execute exploration code and analyze results.
        
        Args:
            code: Python code to execute
            problem_context: Original problem for context
            
        Returns:
            ExplorationResult with patterns and conjectures
        """
        # Validate code safety
        safety_check = self._check_code_safety(code)
        if not safety_check["safe"]:
            return ExplorationResult(
                success=False,
                output="",
                patterns_found=[],
                conjectures=[],
                error=f"Unsafe code: {safety_check['reason']}"
            )
        
        # Execute code
        try:
            output = await self._execute_code(code)
            
            # Analyze output
            patterns = self._extract_patterns(output)
            conjectures = self._generate_conjectures(output, patterns)
            
            return ExplorationResult(
                success=True,
                output=output,
                patterns_found=patterns,
                conjectures=conjectures
            )
            
        except asyncio.TimeoutError:
            return ExplorationResult(
                success=False,
                output="",
                patterns_found=[],
                conjectures=[],
                error=f"Execution timed out after {self.timeout}s"
            )
        except Exception as e:
            return ExplorationResult(
                success=False,
                output="",
                patterns_found=[],
                conjectures=[],
                error=str(e)
            )
    
    def _check_code_safety(self, code: str) -> Dict[str, Any]:
        """
        Check if code is safe to execute.
        
        Returns:
            Dictionary with 'safe' boolean and 'reason' if unsafe
        """
        # Check for dangerous patterns
        dangerous_patterns = [
            "open(",
            "exec(",
            "eval(",
            "__import__",
            "subprocess",
            "os.system",
            "shutil",
            "pickle",
            "socket",
            "requests",
            "urllib",
            "http",
            "file",
            "write(",
            "delete",
            "remove",
            "rmdir",
            "unlink",
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return {"safe": False, "reason": f"Dangerous pattern: {pattern}"}
        
        # Check imports
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                # Extract module name
                if line.startswith("import "):
                    module = line.split()[1].split('.')[0].split(',')[0]
                else:  # from X import Y
                    module = line.split()[1].split('.')[0]
                
                if module not in self.ALLOWED_IMPORTS:
                    return {"safe": False, "reason": f"Disallowed import: {module}"}
        
        return {"safe": True, "reason": ""}
    
    async def _execute_code(self, code: str) -> str:
        """
        Execute code in a restricted environment.
        
        Args:
            code: Code to execute
            
        Returns:
            Captured stdout output
        """
        # Create restricted globals
        restricted_globals = {
            "__builtins__": self.SAFE_BUILTINS,
            "sp": sp,
            "sympy": sp,
            "symbols": symbols,
            "simplify": simplify,
            "solve": solve,
            "expand": expand,
            "factor": factor,
        }
        
        # Import allowed modules
        import math
        import fractions
        import itertools
        import functools
        import collections
        import decimal
        
        restricted_globals.update({
            "math": math,
            "fractions": fractions,
            "itertools": itertools,
            "functools": functools,
            "collections": collections,
            "decimal": decimal,
        })
        
        # Try to import numpy (optional)
        try:
            import numpy as np
            restricted_globals["np"] = np
            restricted_globals["numpy"] = np
        except ImportError:
            pass
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        def run_code():
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, restricted_globals)
        
        # Run in thread pool with timeout
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(
            loop.run_in_executor(None, run_code),
            timeout=self.timeout
        )
        
        output = stdout_capture.getvalue()
        errors = stderr_capture.getvalue()
        
        if errors:
            output += f"\n[Warnings/Errors]:\n{errors}"
        
        return output
    
    def _extract_patterns(self, output: str) -> List[str]:
        """
        Extract patterns from exploration output.
        
        Looks for:
        - Explicit pattern markers
        - Sequences that show regularity
        - Formulas or expressions
        
        Args:
            output: Code execution output
            
        Returns:
            List of discovered patterns
        """
        patterns = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for explicit pattern markers
            if any(marker in line.lower() for marker in ['pattern:', 'found:', 'conjecture:', 'formula:']):
                patterns.append(line)
                continue
            
            # Look for equations
            if '=' in line and any(c.isalpha() for c in line):
                # Might be a formula
                patterns.append(f"Potential formula: {line}")
                continue
            
            # Look for sequences (comma-separated numbers)
            if ',' in line:
                parts = line.split(',')
                try:
                    nums = [float(p.strip()) for p in parts if p.strip()]
                    if len(nums) >= 3:
                        # Check for arithmetic progression
                        diffs = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
                        if len(set(diffs)) == 1:
                            patterns.append(f"Arithmetic sequence found: diff = {diffs[0]}")
                        
                        # Check for geometric progression
                        if all(n != 0 for n in nums[:-1]):
                            ratios = [nums[i+1] / nums[i] for i in range(len(nums)-1)]
                            if len(set(round(r, 6) for r in ratios)) == 1:
                                patterns.append(f"Geometric sequence found: ratio = {ratios[0]}")
                except (ValueError, ZeroDivisionError):
                    pass
        
        return patterns
    
    def _generate_conjectures(
        self,
        output: str,
        patterns: List[str]
    ) -> List[str]:
        """
        Generate conjectures based on output and patterns.
        
        Args:
            output: Code execution output
            patterns: Extracted patterns
            
        Returns:
            List of conjectures
        """
        conjectures = []
        
        # Look for explicit conjectures in output
        for line in output.split('\n'):
            if 'conjecture' in line.lower():
                conjectures.append(line.strip())
        
        # Generate conjectures from patterns
        for pattern in patterns:
            if 'arithmetic sequence' in pattern.lower():
                conjectures.append(f"Conjecture: Linear relationship exists. {pattern}")
            elif 'geometric sequence' in pattern.lower():
                conjectures.append(f"Conjecture: Exponential relationship exists. {pattern}")
            elif 'formula' in pattern.lower():
                conjectures.append(f"Conjecture: Closed-form expression may exist. {pattern}")
        
        return conjectures
    
    def generate_exploration_template(
        self,
        problem: str,
        hypotheses: List[str]
    ) -> str:
        """
        Generate a code template for exploration.
        
        Args:
            problem: The mathematical problem
            hypotheses: List of approach hypotheses
            
        Returns:
            Python code template
        """
        hypotheses_comments = '\n'.join(f'# {i+1}. {h}' for i, h in enumerate(hypotheses[:5]))
        
        return f'''# Mathematical Exploration Code
# Problem: {problem[:200]}...
#
# Hypotheses to explore:
{hypotheses_comments}

import sympy as sp
from sympy import symbols, simplify, solve, expand, factor, Rational, sqrt
from itertools import combinations, permutations
from fractions import Fraction
import math

# Define symbolic variables
x, y, z, n, k = symbols('x y z n k', integer=True)
a, b, c = symbols('a b c', real=True)

print("=== Mathematical Exploration ===")
print()

# Exploration 1: Small case analysis
print("--- Small Case Analysis ---")
for n_val in range(1, 10):
    # TODO: Evaluate expression for small cases
    # result = ...
    # print(f"n={n_val}: result = {{result}}")
    pass

print()

# Exploration 2: Pattern search
print("--- Pattern Search ---")
# TODO: Look for patterns in sequences or structures
# for pattern in patterns:
#     print(f"Pattern found: {{pattern}}")
pass

print()

# Exploration 3: Symbolic manipulation
print("--- Symbolic Analysis ---")
expr = x**2 + 2*x + 1  # TODO: Replace with problem expression
simplified = simplify(expr)
factored = factor(expr)
print(f"Original: {{expr}}")
print(f"Simplified: {{simplified}}")
print(f"Factored: {{factored}}")

print()
print("=== Exploration Complete ===")
'''
    
    async def run_quick_exploration(
        self,
        problem: str,
        hypothesis: str
    ) -> Dict[str, Any]:
        """
        Run a quick exploration for a single hypothesis.
        
        Args:
            problem: The problem statement
            hypothesis: Single hypothesis to test
            
        Returns:
            Dictionary with exploration results
        """
        # Generate minimal exploration code
        code = f'''
import sympy as sp
from sympy import symbols, simplify, factor, expand, solve

# Quick exploration: {hypothesis[:100]}
x, n = symbols('x n')

# Test small cases
print("Testing small cases:")
for i in range(1, 6):
    print(f"  n={i}: (placeholder)")

# Basic symbolic check
print("\\nHypothesis relevance: Needs further investigation")
'''
        
        result = await self.explore(code, problem)
        
        return {
            "hypothesis": hypothesis,
            "executed": result.success,
            "output": result.output,
            "patterns": result.patterns_found,
            "conjectures": result.conjectures,
            "error": result.error
        }
