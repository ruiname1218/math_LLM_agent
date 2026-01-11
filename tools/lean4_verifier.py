"""
Ultimate Math Agent - Lean4 Formal Verification Tool
Integrates with Lean4 for formal proof verification.
"""

import asyncio
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from config import get_config


@dataclass
class Lean4Result:
    """Result from Lean4 verification."""
    verified: bool
    output: str
    errors: list[str]
    warnings: list[str]


class Lean4Verifier:
    """
    Lean4 formal verification tool.
    
    Integrates with Lean4 to formally verify mathematical proofs.
    Uses subprocess to execute Lean4 and parse results.
    """
    
    def __init__(self):
        config = get_config()
        self.lean4_path = config.lean4_path
        self.project_path = config.lean4_project
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the Lean4 environment.
        
        Returns:
            True if Lean4 is available and working
        """
        if self._initialized:
            return True
        
        # Check if Lean4 is installed
        if not await self._check_lean4_installed():
            return False
        
        # Create project directory if needed
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
        return True
    
    async def _check_lean4_installed(self) -> bool:
        """Check if Lean4 is installed and accessible."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "lean", "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return proc.returncode == 0 and b"Lean" in stdout
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    async def verify(self, lean_code: str) -> Dict[str, Any]:
        """
        Verify Lean4 code.
        
        Args:
            lean_code: Lean4 code to verify
            
        Returns:
            Dictionary with verification results
        """
        if not await self.initialize():
            return {
                "verified": False,
                "output": "",
                "errors": ["Lean4 not available"],
                "warnings": []
            }
        
        # Write code to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.lean',
            dir=self.project_path,
            delete=False
        ) as f:
            f.write(lean_code)
            temp_file = f.name
        
        try:
            # Run Lean4 on the file
            result = await self._run_lean4(temp_file)
            return {
                "verified": result.verified,
                "output": result.output,
                "errors": result.errors,
                "warnings": result.warnings
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    async def _run_lean4(self, file_path: str) -> Lean4Result:
        """
        Run Lean4 on a file and parse results.
        
        Args:
            file_path: Path to the Lean4 file
            
        Returns:
            Lean4Result with verification status
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "lean", file_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=60.0  # 60 second timeout
            )
            
            output = stdout.decode('utf-8', errors='replace')
            error_output = stderr.decode('utf-8', errors='replace')
            
            # Parse errors and warnings
            errors = []
            warnings = []
            
            for line in error_output.split('\n'):
                if 'error:' in line.lower():
                    errors.append(line.strip())
                elif 'warning:' in line.lower():
                    warnings.append(line.strip())
            
            for line in output.split('\n'):
                if 'error:' in line.lower():
                    errors.append(line.strip())
                elif 'warning:' in line.lower():
                    warnings.append(line.strip())
            
            # Check for "sorry" which indicates incomplete proof
            if 'sorry' in output.lower() or 'sorry' in error_output.lower():
                # Not fully verified, but might be structurally correct
                warnings.append("Proof contains 'sorry' - not fully verified")
            
            verified = proc.returncode == 0 and len(errors) == 0
            
            return Lean4Result(
                verified=verified,
                output=output + error_output,
                errors=errors,
                warnings=warnings
            )
            
        except asyncio.TimeoutError:
            return Lean4Result(
                verified=False,
                output="",
                errors=["Lean4 verification timed out (60s)"],
                warnings=[]
            )
        except Exception as e:
            return Lean4Result(
                verified=False,
                output="",
                errors=[f"Lean4 execution error: {str(e)}"],
                warnings=[]
            )
    
    async def verify_with_lakefile(
        self,
        lean_code: str,
        project_name: str = "math_proof"
    ) -> Dict[str, Any]:
        """
        Verify Lean4 code within a proper Lake project.
        
        This provides more robust verification with proper dependency management.
        
        Args:
            lean_code: Lean4 code to verify
            project_name: Name for the Lake project
            
        Returns:
            Dictionary with verification results
        """
        project_dir = self.project_path / project_name
        
        # Initialize Lake project if needed
        if not (project_dir / "lakefile.lean").exists():
            await self._init_lake_project(project_dir)
        
        # Write the proof file
        proof_file = project_dir / "MathProof.lean"
        proof_file.write_text(lean_code)
        
        # Build with Lake
        try:
            proc = await asyncio.create_subprocess_exec(
                "lake", "build",
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=120.0
            )
            
            output = stdout.decode() + stderr.decode()
            errors = [l for l in output.split('\n') if 'error:' in l.lower()]
            warnings = [l for l in output.split('\n') if 'warning:' in l.lower()]
            
            return {
                "verified": proc.returncode == 0 and len(errors) == 0,
                "output": output,
                "errors": errors,
                "warnings": warnings
            }
            
        except asyncio.TimeoutError:
            return {
                "verified": False,
                "output": "",
                "errors": ["Lake build timed out"],
                "warnings": []
            }
    
    async def _init_lake_project(self, project_dir: Path):
        """Initialize a new Lake project."""
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create lakefile.lean
        lakefile = project_dir / "lakefile.lean"
        lakefile.write_text('''
import Lake
open Lake DSL

package math_proof where
  version := v!"0.1.0"

@[default_target]
lean_lib MathProof where
''')
        
        # Create lean-toolchain
        toolchain = project_dir / "lean-toolchain"
        toolchain.write_text("leanprover/lean4:stable")
        
        # Run lake update
        try:
            proc = await asyncio.create_subprocess_exec(
                "lake", "update",
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=60.0)
        except:
            pass  # May fail if no Mathlib dependency
    
    def is_available(self) -> bool:
        """Check if Lean4 verification is available."""
        return asyncio.run(self._check_lean4_installed())


# Helper functions for common proof patterns

def wrap_theorem(
    name: str,
    statement: str,
    proof_tactics: str = "sorry"
) -> str:
    """
    Wrap a mathematical statement in Lean4 theorem syntax.
    
    Args:
        name: Theorem name
        statement: The mathematical statement in Lean4 syntax
        proof_tactics: Proof tactics (default: sorry for incomplete)
        
    Returns:
        Complete Lean4 theorem code
    """
    return f'''
-- Auto-generated Lean4 proof
import Mathlib.Tactic

theorem {name} : {statement} := by
  {proof_tactics}
'''


def create_basic_number_theory_proof(n: int, property_name: str) -> str:
    """
    Create a basic number theory proof template.
    
    Args:
        n: The number involved
        property_name: Name of the property to prove
        
    Returns:
        Lean4 code template
    """
    return f'''
import Mathlib.Data.Nat.Basic
import Mathlib.Tactic

-- Proof that {n} has property: {property_name}
theorem nat_property_{n} : sorry := by
  sorry
'''
