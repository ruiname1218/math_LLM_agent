"""
Ultimate Math Agent - Strict Lean4 Formal Verification
Enhanced Lean4 integration that enforces rigorous, complete proofs.
Rejects proofs containing 'sorry' or incomplete tactics.
"""

import asyncio
import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from config import get_config


class VerificationLevel(Enum):
    """Verification strictness levels."""
    SKETCH = "sketch"           # Allows sorry, structural check only
    PARTIAL = "partial"         # Some sorry allowed, warns about them
    STRICT = "strict"           # No sorry allowed, complete formal proof required
    MATHLIB = "mathlib"         # Strict + requires Mathlib theorems


@dataclass
class Lean4VerificationResult:
    """Detailed result from strict Lean4 verification."""
    verified: bool
    level: VerificationLevel
    output: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sorry_count: int = 0
    axiom_usage: List[str] = field(default_factory=list)
    theorem_name: Optional[str] = None
    proof_complete: bool = False
    tactics_used: List[str] = field(default_factory=list)
    
    @property
    def is_rigorous(self) -> bool:
        """Check if the proof is truly rigorous (no sorry, no critical errors)."""
        return (
            self.verified and 
            self.sorry_count == 0 and 
            len(self.errors) == 0 and
            self.proof_complete
        )


class StrictLean4Verifier:
    """
    Strict Lean4 formal verification tool.
    
    Unlike the basic verifier, this enforces:
    1. No 'sorry' statements allowed (in STRICT mode)
    2. All lemmas must be fully proven
    3. Axiom usage is tracked and reported
    4. Complete proof tree validation
    """
    
    def __init__(self, level: VerificationLevel = VerificationLevel.STRICT):
        config = get_config()
        self.lean4_path = config.lean4_path
        self.project_path = config.lean4_project
        self.level = level
        self._initialized = False
        
        # Patterns to detect incomplete proofs
        self.SORRY_PATTERNS = [
            r'\bsorry\b',
            r'\badmit\b', 
            r'\b_\b\s*:=',  # Underscore as proof term
            r'\.\.\.pending',
        ]
        
        # Patterns to extract theorem info
        self.THEOREM_PATTERN = r'(theorem|lemma|def)\s+(\w+)'
        self.TACTIC_PATTERN = r'\b(simp|ring|linarith|omega|decide|norm_num|nlinarith|polyrith|exact|apply|intro|cases|induction|rfl|trivial|constructor|assumption|contradiction|exfalso|by_contra|push_neg|use|existsi|choose|rcases|obtain|have|let|show|calc|conv|rw|rewrite|unfold|dsimp|refine|specialize|generalize|clear|rename|subst|ext|funext|congr|ac_refl|ring_nf|field_simp|norm_cast|push_cast|lift|positivity|bound_tac|continuity|measurability|aesop)\b'
    
    async def initialize(self) -> bool:
        """Initialize the Lean4 environment with full checks."""
        if self._initialized:
            return True
        
        # Check Lean4 installation
        if not await self._check_lean4_installation():
            return False
        
        # Check Mathlib if needed
        if self.level == VerificationLevel.MATHLIB:
            if not await self._check_mathlib():
                return False
        
        # Ensure project directory exists
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
        return True
    
    async def _check_lean4_installation(self) -> bool:
        """Verify Lean4 is properly installed."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "lean", "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            
            if proc.returncode != 0:
                return False
            
            version_str = stdout.decode()
            # Ensure we have Lean 4
            if "Lean" in version_str and "4" in version_str:
                return True
            
            return False
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
    
    async def _check_mathlib(self) -> bool:
        """Check if Mathlib4 is available."""
        # This is a simplified check - in production, verify lake manifest
        mathlib_path = self.project_path / "lake-packages" / "mathlib"
        return mathlib_path.exists()
    
    async def verify_strict(
        self,
        lean_code: str,
        theorem_name: Optional[str] = None
    ) -> Lean4VerificationResult:
        """
        Strictly verify Lean4 code with no sorry statements allowed.
        
        Args:
            lean_code: Complete Lean4 code including imports and proof
            theorem_name: Expected theorem name for validation
            
        Returns:
            Detailed verification result
        """
        if not await self.initialize():
            return Lean4VerificationResult(
                verified=False,
                level=self.level,
                output="",
                errors=["Lean4 not properly installed or configured"],
                proof_complete=False
            )
        
        # Pre-check: Scan for sorry statements
        sorry_locations = self._find_sorry_statements(lean_code)
        
        if sorry_locations and self.level == VerificationLevel.STRICT:
            return Lean4VerificationResult(
                verified=False,
                level=self.level,
                output="Code contains incomplete proof markers",
                errors=[f"Found {len(sorry_locations)} incomplete proof(s): {sorry_locations}"],
                sorry_count=len(sorry_locations),
                proof_complete=False
            )
        
        # Extract theorem name if not provided
        if not theorem_name:
            theorem_name = self._extract_theorem_name(lean_code)
        
        # Extract tactics used
        tactics_used = self._extract_tactics(lean_code)
        
        # Write to temp file and compile
        result = await self._compile_and_verify(lean_code)
        
        # Enhance result with extracted info
        result.theorem_name = theorem_name
        result.tactics_used = tactics_used
        result.sorry_count = len(sorry_locations)
        
        # Final assessment
        result.proof_complete = (
            result.verified and 
            result.sorry_count == 0 and
            len(result.errors) == 0
        )
        
        return result
    
    def _find_sorry_statements(self, code: str) -> List[Tuple[int, str]]:
        """Find all sorry/incomplete proof markers in code."""
        findings = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.SORRY_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append((i, line.strip()))
        
        return findings
    
    def _extract_theorem_name(self, code: str) -> Optional[str]:
        """Extract the main theorem/lemma name from code."""
        match = re.search(self.THEOREM_PATTERN, code)
        if match:
            return match.group(2)
        return None
    
    def _extract_tactics(self, code: str) -> List[str]:
        """Extract all tactics used in the proof."""
        return list(set(re.findall(self.TACTIC_PATTERN, code, re.IGNORECASE)))
    
    async def _compile_and_verify(self, code: str) -> Lean4VerificationResult:
        """Compile the Lean4 code and capture results."""
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.lean',
            dir=self.project_path,
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Run lean with detailed output
            proc = await asyncio.create_subprocess_exec(
                "lean", temp_path,
                "--threads=4",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=120  # 2 minute timeout for complex proofs
            )
            
            output = stdout.decode('utf-8', errors='replace')
            error_output = stderr.decode('utf-8', errors='replace')
            combined = output + "\n" + error_output
            
            # Parse output
            errors = self._parse_errors(combined)
            warnings = self._parse_warnings(combined)
            axiom_usage = self._parse_axiom_usage(combined)
            
            verified = proc.returncode == 0 and len(errors) == 0
            
            return Lean4VerificationResult(
                verified=verified,
                level=self.level,
                output=combined,
                errors=errors,
                warnings=warnings,
                axiom_usage=axiom_usage,
                proof_complete=verified
            )
            
        except asyncio.TimeoutError:
            return Lean4VerificationResult(
                verified=False,
                level=self.level,
                output="",
                errors=["Verification timed out (120s limit)"],
                proof_complete=False
            )
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _parse_errors(self, output: str) -> List[str]:
        """Parse error messages from Lean output."""
        errors = []
        for line in output.split('\n'):
            if 'error:' in line.lower():
                errors.append(line.strip())
            elif 'unknown identifier' in line.lower():
                errors.append(line.strip())
            elif 'type mismatch' in line.lower():
                errors.append(line.strip())
        return errors
    
    def _parse_warnings(self, output: str) -> List[str]:
        """Parse warning messages from Lean output."""
        return [line.strip() for line in output.split('\n') 
                if 'warning:' in line.lower()]
    
    def _parse_axiom_usage(self, output: str) -> List[str]:
        """Parse axiom usage from Lean output."""
        axioms = []
        axiom_patterns = ['propext', 'Classical.choice', 'Quot.sound', 'funext']
        for axiom in axiom_patterns:
            if axiom in output:
                axioms.append(axiom)
        return axioms


class Lean4ProofGenerator:
    """
    Generate rigorous Lean4 proofs from natural language.
    Uses iterative refinement to ensure completeness.
    """
    
    def __init__(self):
        self.verifier = StrictLean4Verifier(VerificationLevel.STRICT)
        self.max_refinement_attempts = 5
    
    async def generate_verified_proof(
        self,
        problem: str,
        natural_proof: str,
        model  # The LLM model to use (GPT or DeepSeek)
    ) -> Dict[str, Any]:
        """
        Generate and iteratively refine Lean4 proof until verified.
        
        Args:
            problem: Original math problem
            natural_proof: Natural language proof to formalize
            model: LLM model for code generation
            
        Returns:
            Dictionary with verified Lean4 code and result
        """
        # Initial Lean4 generation
        lean_code = await self._generate_lean4_code(model, problem, natural_proof)
        
        for attempt in range(self.max_refinement_attempts):
            # Verify current code
            result = await self.verifier.verify_strict(lean_code)
            
            if result.is_rigorous:
                return {
                    "success": True,
                    "lean_code": lean_code,
                    "verification": result,
                    "attempts": attempt + 1
                }
            
            # Refine based on errors
            lean_code = await self._refine_proof(
                model, lean_code, result.errors, result.warnings
            )
        
        # Failed after max attempts
        final_result = await self.verifier.verify_strict(lean_code)
        return {
            "success": False,
            "lean_code": lean_code,
            "verification": final_result,
            "attempts": self.max_refinement_attempts,
            "errors": final_result.errors
        }
    
    async def _generate_lean4_code(
        self,
        model,
        problem: str,
        natural_proof: str
    ) -> str:
        """Generate initial Lean4 code from natural language proof."""
        prompt = f"""Convert this mathematical proof to rigorous Lean4 code.

CRITICAL REQUIREMENTS:
1. NO 'sorry' statements - proof must be COMPLETE
2. Use appropriate Mathlib tactics (simp, ring, linarith, etc.)
3. Include all necessary imports
4. Define any required lemmas
5. The proof must compile without errors

PROBLEM:
{problem}

NATURAL LANGUAGE PROOF:
{natural_proof}

Generate complete, verified Lean4 code:

```lean4
import Mathlib.Tactic
import Mathlib.Data.Real.Basic
import Mathlib.Data.Nat.Basic

-- Theorem statement and COMPLETE proof (no sorry!)
"""
        
        response = await model.generate(prompt)
        return self._extract_lean_code(response.content)
    
    async def _refine_proof(
        self,
        model,
        current_code: str,
        errors: List[str],
        warnings: List[str]
    ) -> str:
        """Refine Lean4 code based on compilation errors."""
        error_text = "\n".join(errors) if errors else "No specific errors"
        warning_text = "\n".join(warnings) if warnings else "No warnings"
        
        prompt = f"""Fix this Lean4 proof to make it compile successfully.

CURRENT CODE:
```lean4
{current_code}
```

ERRORS TO FIX:
{error_text}

WARNINGS:
{warning_text}

REQUIREMENTS:
1. Fix ALL errors - the code must compile
2. NO 'sorry' statements allowed
3. Keep the mathematical meaning correct
4. Use appropriate tactics for each proof step

Generate the FIXED, complete Lean4 code:

```lean4"""
        
        response = await model.generate(prompt)
        return self._extract_lean_code(response.content)
    
    def _extract_lean_code(self, response: str) -> str:
        """Extract Lean4 code from LLM response."""
        if "```lean4" in response:
            start = response.find("```lean4") + 8
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        if "```lean" in response:
            start = response.find("```lean") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        return response


# Common mathematical proof templates in Lean4

LEAN4_TEMPLATES = {
    "irrationality": '''
import Mathlib.Data.Real.Irrational
import Mathlib.Data.Real.Sqrt
import Mathlib.Tactic

theorem sqrt_two_irrational : Irrational (Real.sqrt 2) := by
  rw [irrational_iff_ne_rational]
  intro ⟨p, q, hq, h⟩
  have h2 : (Real.sqrt 2) ^ 2 = 2 := Real.sq_sqrt (by norm_num : (0 : ℝ) ≤ 2)
  -- Continue with rigorous proof...
  sorry  -- TODO: Complete this in production
''',
    
    "induction": '''
import Mathlib.Data.Nat.Basic
import Mathlib.Tactic

theorem sum_first_n (n : ℕ) : 2 * (Finset.range (n + 1)).sum id = n * (n + 1) := by
  induction n with
  | zero => simp
  | succ n ih =>
    simp [Finset.sum_range_succ]
    ring_nf
    linarith
''',
    
    "divisibility": '''
import Mathlib.Data.Nat.Basic
import Mathlib.Tactic

theorem div_example (n : ℕ) : 3 ∣ n * (n + 1) * (n + 2) := by
  have h : n % 3 = 0 ∨ n % 3 = 1 ∨ n % 3 = 2 := Nat.mod_three_cases n
  rcases h with h | h | h
  · exact dvd_mul_of_dvd_left (Nat.dvd_of_mod_eq_zero h) _
  · have : (n + 2) % 3 = 0 := by omega
    exact dvd_mul_of_dvd_right (Nat.dvd_of_mod_eq_zero this) _
  · have : (n + 1) % 3 = 0 := by omega
    exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_right (Nat.dvd_of_mod_eq_zero this) _) _
'''
}


async def verify_with_lean4_strict(
    problem: str,
    proof: str,
    model
) -> Dict[str, Any]:
    """
    High-level function to verify a proof rigorously with Lean4.
    
    This is the main interface for the pipeline's Stage 4.
    
    Args:
        problem: Mathematical problem statement
        proof: Natural language proof to verify
        model: LLM for Lean4 code generation
        
    Returns:
        Complete verification result with Lean4 code
    """
    generator = Lean4ProofGenerator()
    result = await generator.generate_verified_proof(problem, proof, model)
    
    return {
        "formally_verified": result["success"],
        "lean4_code": result["lean_code"],
        "is_rigorous": result["verification"].is_rigorous if result.get("verification") else False,
        "sorry_count": result["verification"].sorry_count if result.get("verification") else -1,
        "errors": result.get("errors", []),
        "attempts": result["attempts"],
        "tactics_used": result["verification"].tactics_used if result.get("verification") else [],
        "axioms_used": result["verification"].axiom_usage if result.get("verification") else []
    }
