"""
Ultimate Math Agent - Configuration Management
Handles all API keys, model settings, and pipeline configuration.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ModelConfig:
    """Configuration for a single LLM."""
    name: str
    api_key: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 16384
    thinking_mode: bool = False
    base_url: Optional[str] = None


@dataclass
class PipelineConfig:
    """Configuration for the math agent pipeline."""
    max_iterations: int = 5
    confidence_threshold: float = 0.9
    verbose: bool = True
    lean4_enabled: bool = True
    parallel_execution: bool = True


@dataclass
class Config:
    """Central configuration container."""
    
    # Model configurations
    gpt: ModelConfig = field(default_factory=lambda: ModelConfig(
        name="GPT-5.2 Pro",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model_id=os.getenv("OPENAI_MODEL", "gpt-4o"),  # Fallback to gpt-4o
        temperature=0.7,
        max_tokens=32768,
        thinking_mode=True,  # Extended thinking enabled
        base_url=os.getenv("OPENAI_BASE_URL")  # OpenRouter/compatible APIs
    ))
    
    grok: ModelConfig = field(default_factory=lambda: ModelConfig(
        name="Grok-4.2 Heavy",
        api_key=os.getenv("XAI_API_KEY", ""),
        model_id=os.getenv("XAI_MODEL", "grok-2"),  # Fallback
        temperature=0.8,
        max_tokens=16384,
        thinking_mode=True,
        base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")  # OpenRouter: https://openrouter.ai/api/v1
    ))
    
    gemini: ModelConfig = field(default_factory=lambda: ModelConfig(
        name="Gemini 3 Pro",
        api_key=os.getenv("GOOGLE_API_KEY", ""),
        model_id=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-thinking-exp"),
        temperature=0.7,
        max_tokens=32768,
        thinking_mode=True  # Deep Think mode
    ))
    
    claude: ModelConfig = field(default_factory=lambda: ModelConfig(
        name="Claude Opus 4.5",
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model_id=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),  # Fallback
        temperature=0.5,  # Lower for rigorous verification
        max_tokens=16384,
        thinking_mode=True
    ))
    
    deepseek: ModelConfig = field(default_factory=lambda: ModelConfig(
        name="DeepSeek-Math-V2",
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        model_id=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),  # Fallback
        temperature=0.6,
        max_tokens=16384,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")  # OpenRouter: https://openrouter.ai/api/v1
    ))
    
    # Aristotle - Lean4 specialist from Harmonic AI
    aristotle: ModelConfig = field(default_factory=lambda: ModelConfig(
        name="Aristotle",
        api_key=os.getenv("HARMONIC_API_KEY", ""),
        model_id=os.getenv("ARISTOTLE_MODEL", "aristotle-lean4"),
        temperature=0.3,  # Very low for precise Lean4 code
        max_tokens=16384,
        base_url=os.getenv("HARMONIC_API_BASE", "https://api.harmonic.ai/v1")
    ))
    
    # Pipeline configuration
    pipeline: PipelineConfig = field(default_factory=lambda: PipelineConfig(
        max_iterations=int(os.getenv("MAX_ITERATIONS", "5")),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.9")),
        verbose=os.getenv("VERBOSE", "true").lower() == "true",
        lean4_enabled=bool(os.getenv("LEAN4_PATH")),
        parallel_execution=True
    ))
    
    # Lean4 paths
    lean4_path: Path = field(default_factory=lambda: Path(os.getenv("LEAN4_PATH", "/usr/local/bin/lean")))
    lean4_project: Path = field(default_factory=lambda: Path(os.getenv("LEAN4_PROJECT_PATH", "./lean_proofs")))
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of warnings."""
        warnings = []
        
        if not self.gpt.api_key:
            warnings.append("⚠️ OpenAI API key not set - GPT-5.2 Pro will not work")
        if not self.grok.api_key:
            warnings.append("⚠️ xAI API key not set - Grok-4.2 will use fallback")
        if not self.gemini.api_key:
            warnings.append("⚠️ Google API key not set - Gemini 3 will not work")
        if not self.claude.api_key:
            warnings.append("⚠️ Anthropic API key not set - Claude verification disabled")
        if not self.deepseek.api_key:
            warnings.append("⚠️ DeepSeek API key not set - using GPT fallback")
        if not self.aristotle.api_key:
            warnings.append("⚠️ Harmonic/Aristotle API key not set - Lean4 will use DeepSeek/GPT")
        if not self.lean4_path.exists():
            warnings.append("⚠️ Lean4 not found - formal verification disabled")
            
        return warnings


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def print_config_status():
    """Print configuration status to console."""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    table = Table(title="🧮 Ultimate Math Agent - Configuration Status")
    
    table.add_column("Model", style="cyan")
    table.add_column("API Key", style="green")
    table.add_column("Model ID", style="yellow")
    table.add_column("Status", style="bold")
    
    models = [
        ("GPT-5.2 Pro", config.gpt),
        ("Grok-4.2 Heavy", config.grok),
        ("Gemini 3 Pro", config.gemini),
        ("Claude Opus 4.5", config.claude),
        ("DeepSeek-Math-V2", config.deepseek),
        ("Aristotle (Lean4)", config.aristotle),
    ]
    
    for name, model in models:
        key_status = "✅ Set" if model.api_key else "❌ Missing"
        status = "🟢 Ready" if model.api_key else "🔴 Disabled"
        table.add_row(name, key_status, model.model_id, status)
    
    console.print(table)
    
    # Print warnings
    warnings = config.validate()
    if warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for w in warnings:
            console.print(f"  {w}")
