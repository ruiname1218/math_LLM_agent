"""
Ultimate Math Agent - LangGraph Workflow Definition
Orchestrates the 5-stage multi-model pipeline.
"""

import asyncio
from typing import Literal
from langgraph.graph import StateGraph, END, START
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from pipeline.state import MathAgentState, create_initial_state
from pipeline.stages import (
    decomposition_node,
    diversification_node,
    proof_generation_node,
    verification_node,
    integration_node,
)
from pipeline.stages.verification import should_retry
from config import get_config


def create_math_agent_graph() -> StateGraph:
    """
    Create the LangGraph workflow for the math agent.
    
    The workflow implements a 5-stage pipeline with a feedback loop:
    
    1. decomposition      - GPT-5.2 + Grok (parallel)
    2. diversification    - Gemini + GPT-5.2 (parallel)  
    3. proof_generation   - GPT-5.2 + DeepSeek
    4. verification       - Claude + GPT-5.2 + Lean4
       ↓ (if INVALID or low confidence) ↓
       └──────────→ 3. proof_generation (retry)
       ↓ (if VALID and high confidence) ↓
    5. integration        - GPT-5.2 final output
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create the state graph
    workflow = StateGraph(MathAgentState)
    
    # Add nodes for each stage
    workflow.add_node("decomposition", decomposition_node)
    workflow.add_node("diversification", diversification_node)
    workflow.add_node("proof_generation", proof_generation_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("integration", integration_node)
    
    # Add edges
    workflow.add_edge(START, "decomposition")
    workflow.add_edge("decomposition", "diversification")
    workflow.add_edge("diversification", "proof_generation")
    workflow.add_edge("proof_generation", "verification")
    
    # Conditional edge from verification
    workflow.add_conditional_edges(
        "verification",
        should_retry,
        {
            "proof_generation": "proof_generation",  # Retry
            "integration": "integration"              # Success
        }
    )
    
    workflow.add_edge("integration", END)
    
    return workflow.compile()


async def run_math_agent(
    problem: str,
    max_iterations: int = 5,
    verbose: bool = True
) -> MathAgentState:
    """
    Run the math agent on a problem.
    
    Args:
        problem: The mathematical problem to solve
        max_iterations: Maximum verification → regeneration loops
        verbose: Whether to print progress
        
    Returns:
        Final state with proof and metrics
    """
    console = Console()
    config = get_config()
    
    # Create initial state
    initial_state = create_initial_state(problem, max_iterations)
    
    # Compile the graph
    graph = create_math_agent_graph()
    
    if verbose:
        console.print("\n[bold cyan]🧮 Ultimate Math Agent[/bold cyan]")
        console.print(f"[dim]Problem: {problem[:100]}{'...' if len(problem) > 100 else ''}[/dim]\n")
    
    # Run the workflow
    final_state = None
    
    if verbose:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Running pipeline...", total=None)
            
            async for event in graph.astream(initial_state):
                # Extract the node name and update
                for node_name, node_output in event.items():
                    if node_name != "__end__":
                        progress.update(task, description=f"[cyan]Stage: {node_name}")
                        final_state = node_output
            
            progress.update(task, description="[green]✓ Complete!")
    else:
        async for event in graph.astream(initial_state):
            for node_name, node_output in event.items():
                if node_name != "__end__":
                    final_state = node_output
    
    if verbose and final_state:
        _print_summary(console, final_state)
    
    return final_state


def _print_summary(console: Console, state: MathAgentState):
    """Print a summary of the math agent execution."""
    from rich.panel import Panel
    from rich.table import Table
    
    # Metrics table
    table = Table(title="📊 Execution Metrics")
    table.add_column("Stage", style="cyan")
    table.add_column("Latency", style="yellow")
    table.add_column("Models Used", style="green")
    
    total_latency = 0
    for metric in state.get("stage_metrics", []):
        latency = metric.get("latency_ms", 0)
        total_latency += latency
        table.add_row(
            metric.get("stage_name", "?"),
            f"{latency:.0f}ms",
            ", ".join(metric.get("models_used", []))
        )
    
    table.add_row("[bold]Total[/bold]", f"[bold]{total_latency:.0f}ms[/bold]", "")
    console.print(table)
    
    # Verification summary
    verification = state.get("verification_result", {})
    confidence = state.get("confidence_score", 0)
    iterations = state.get("iteration_count", 0)
    
    status_color = "green" if verification.get("is_valid") else "yellow"
    console.print(f"\n[{status_color}]Verification: {verification.get('status', 'N/A')}[/{status_color}]")
    console.print(f"Confidence: {confidence:.1%}")
    console.print(f"Iterations: {iterations}")
    
    if state.get("lean4_verified"):
        console.print("[green]✓ Lean4 formal verification passed[/green]")
    
    # Errors
    errors = state.get("error_log", [])
    if errors:
        console.print("\n[yellow]⚠️ Warnings/Errors:[/yellow]")
        for err in errors:
            console.print(f"  • {err}")
    
    # Final proof preview
    final_proof = state.get("final_proof", "")
    if final_proof:
        preview = final_proof[:500] + "..." if len(final_proof) > 500 else final_proof
        console.print(Panel(preview, title="[bold]Final Proof Preview[/bold]", border_style="blue"))


# Synchronous wrapper for CLI
def run_math_agent_sync(problem: str, **kwargs) -> MathAgentState:
    """Synchronous wrapper for run_math_agent."""
    return asyncio.run(run_math_agent(problem, **kwargs))
