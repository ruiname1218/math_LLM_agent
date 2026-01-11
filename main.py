#!/usr/bin/env python3
"""
Ultimate Math Agent - Main Entry Point
A multi-model AI system for solving mathematical problems with formal verification.

Usage:
    python main.py "Prove that the square root of 2 is irrational"
    python main.py --file problem.txt
    python main.py --interactive
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from config import get_config, print_config_status
from pipeline import run_math_agent, MathAgentState


app = typer.Typer(
    name="math-agent",
    help="🧮 Ultimate Math Agent - Multi-model AI for mathematical proofs",
    add_completion=False
)
console = Console()


@app.command()
def solve(
    problem: Optional[str] = typer.Argument(
        None,
        help="The mathematical problem to solve"
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f",
        help="Read problem from a file"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Save the final proof to a file"
    ),
    max_iterations: int = typer.Option(
        5, "--max-iter", "-m",
        help="Maximum verification → regeneration loops"
    ),
    verbose: bool = typer.Option(
        True, "--verbose/--quiet", "-v/-q",
        help="Enable verbose output"
    ),
    show_config: bool = typer.Option(
        False, "--show-config",
        help="Show configuration status and exit"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i",
        help="Interactive mode - enter problems one by one"
    )
):
    """
    Solve a mathematical problem using the multi-model AI pipeline.
    
    The system uses 5 LLMs in a sophisticated pipeline:
    
    1. GPT-5.2 Pro + Grok-4.2 → Problem decomposition
    2. Gemini 3 Pro + GPT-5.2 → Hypothesis diversification  
    3. GPT-5.2 + DeepSeek-Math → Proof generation
    4. Claude Opus 4.5 + GPT-5.2 → Rigorous verification
    5. GPT-5.2 → Final integration
    
    Examples:
    
        python main.py "Prove √2 is irrational"
        
        python main.py -f problem.txt -o proof.md
        
        python main.py --interactive
    """
    # Show config if requested
    if show_config:
        print_config_status()
        raise typer.Exit()
    
    # Interactive mode
    if interactive:
        _interactive_mode(max_iterations, verbose)
        raise typer.Exit()
    
    # Get problem from argument or file
    if file:
        if not file.exists():
            console.print(f"[red]Error: File not found: {file}[/red]")
            raise typer.Exit(1)
        problem = file.read_text().strip()
    
    if not problem:
        console.print("[yellow]No problem provided. Use --help for usage.[/yellow]")
        console.print("\n[dim]Tip: Use --interactive for interactive mode[/dim]")
        raise typer.Exit(1)
    
    # Validate configuration
    config = get_config()
    warnings = config.validate()
    
    if verbose and warnings:
        console.print("\n[yellow]Configuration warnings:[/yellow]")
        for w in warnings:
            console.print(f"  {w}")
        console.print()
    
    # Run the agent
    try:
        result = asyncio.run(
            run_math_agent(
                problem=problem,
                max_iterations=max_iterations,
                verbose=verbose
            )
        )
        
        # Output final proof
        if result and result.get("final_proof"):
            if output:
                output.write_text(result["final_proof"])
                console.print(f"\n[green]✓ Proof saved to {output}[/green]")
            
            if verbose:
                console.print("\n" + "=" * 60)
                console.print(Markdown(result["final_proof"]))
        else:
            console.print("[red]Failed to generate proof[/red]")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


def _interactive_mode(max_iterations: int, verbose: bool):
    """
    Interactive mode for solving multiple problems.
    """
    console.print(Panel.fit(
        "[bold cyan]🧮 Ultimate Math Agent[/bold cyan]\n"
        "[dim]Interactive Mode - Type 'quit' to exit[/dim]",
        border_style="cyan"
    ))
    
    print_config_status()
    console.print()
    
    while True:
        try:
            problem = Prompt.ask("\n[bold cyan]Enter problem[/bold cyan]")
            
            if problem.lower() in ('quit', 'exit', 'q'):
                console.print("[dim]Goodbye![/dim]")
                break
            
            if not problem.strip():
                continue
            
            # Run the agent
            result = asyncio.run(
                run_math_agent(
                    problem=problem,
                    max_iterations=max_iterations,
                    verbose=verbose
                )
            )
            
            if result and result.get("final_proof"):
                console.print("\n[bold green]Final Proof:[/bold green]")
                console.print(Markdown(result["final_proof"]))
                
                # Offer to save
                save = Prompt.ask(
                    "\n[dim]Save to file? (enter filename or press Enter to skip)[/dim]",
                    default=""
                )
                if save:
                    Path(save).write_text(result["final_proof"])
                    console.print(f"[green]✓ Saved to {save}[/green]")
            else:
                console.print("[red]Failed to generate proof[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[dim]Type 'quit' to exit[/dim]")
            continue


@app.command()
def config():
    """Show configuration status."""
    print_config_status()


@app.command()
def test():
    """Run a quick test with a simple problem."""
    console.print("[cyan]Running test with: 'Prove that 1 + 1 = 2'[/cyan]\n")
    
    try:
        result = asyncio.run(
            run_math_agent(
                problem="Prove that 1 + 1 = 2 in the natural numbers",
                max_iterations=2,
                verbose=True
            )
        )
        
        if result and result.get("final_proof"):
            console.print("\n[green]✓ Test passed[/green]")
        else:
            console.print("[red]✗ Test failed[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Test failed: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print("[bold cyan]Ultimate Math Agent[/bold cyan] v1.0.0")
    console.print()
    console.print("Models:")
    console.print("  • GPT-5.2 Pro Extended Thinking (Central Coordinator)")
    console.print("  • Grok-4.2 Heavy Thinking (Problem Decomposition)")
    console.print("  • Gemini 3 Pro Deep Think (AlphaEvolve Exploration)")
    console.print("  • Claude Opus 4.5 Thinking (Rigorous Verification)")
    console.print("  • DeepSeek-Math-V2 (Proof Refinement)")
    console.print()
    console.print("Features:")
    console.print("  • LangGraph-based multi-model orchestration")
    console.print("  • Confidence-based verification loop")
    console.print("  • Strict Lean4 formal verification (no sorry!)")
    console.print("  • AlphaEvolve-style pattern exploration")
    console.print("  • Web UI with Gradio")


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(7860, "--port", "-p", help="Port number"),
    share: bool = typer.Option(False, "--share", help="Create public Gradio link"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode")
):
    """
    Launch the web UI.
    
    Opens a beautiful Gradio interface in your browser.
    
    Examples:
        python main.py web
        python main.py web --port 8080
        python main.py web --share  # Create public link
    """
    from web_ui import launch_web_ui
    
    console.print(Panel.fit(
        "[bold cyan]🧮 Ultimate Math Agent - Web UI[/bold cyan]\n"
        f"[dim]Starting server at http://{host}:{port}[/dim]",
        border_style="cyan"
    ))
    
    print_config_status()
    console.print()
    console.print(f"[green]🌐 Open http://localhost:{port} in your browser[/green]")
    
    if share:
        console.print("[yellow]📤 Creating public share link...[/yellow]")
    
    launch_web_ui(host=host, port=port, share=share, debug=debug)


if __name__ == "__main__":
    app()

