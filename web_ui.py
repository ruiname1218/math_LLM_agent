"""
Ultimate Math Agent - Web UI
Beautiful Gradio interface for the multi-model math proof system.
"""

import asyncio
import time
from typing import Generator, Tuple
import gradio as gr

from config import get_config, print_config_status
from pipeline.state import create_initial_state, MathAgentState
from pipeline.graph import create_math_agent_graph


# Custom CSS for beautiful UI
CUSTOM_CSS = """
.gradio-container {
    max-width: 1200px !important;
}

.stage-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
}

.stage-active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.stage-complete {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
}

.stage-pending {
    background: #e0e0e0;
    color: #666;
}

.proof-output {
    font-family: 'Computer Modern', 'Latin Modern Math', serif;
    line-height: 1.8;
}

.metric-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
}

.confidence-high {
    color: #10b981;
    font-weight: bold;
}

.confidence-medium {
    color: #f59e0b;
    font-weight: bold;
}

.confidence-low {
    color: #ef4444;
    font-weight: bold;
}
"""


def get_stage_status_html(current_stage: str, completed_stages: list) -> str:
    """Generate HTML for pipeline stage visualization."""
    stages = [
        ("1️⃣", "Decomposition", "GPT-5.2 + Grok"),
        ("2️⃣", "Diversification", "Gemini + GPT-5.2"),
        ("3️⃣", "Proof Generation", "GPT-5.2 + DeepSeek"),
        ("4️⃣", "Verification", "Claude + Lean4"),
        ("5️⃣", "Integration", "GPT-5.2"),
    ]
    
    html = '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin: 20px 0;">'
    
    for icon, name, models in stages:
        stage_key = name.lower().replace(" ", "_")
        
        if stage_key in completed_stages:
            status_class = "stage-complete"
            status_icon = "✅"
        elif stage_key == current_stage:
            status_class = "stage-active"
            status_icon = "⏳"
        else:
            status_class = "stage-pending"
            status_icon = "⏸️"
        
        html += f'''
        <div class="stage-badge {status_class}" style="padding: 8px 16px; border-radius: 8px; text-align: center;">
            <div style="font-size: 18px;">{icon} {status_icon}</div>
            <div style="font-weight: bold;">{name}</div>
            <div style="font-size: 10px; opacity: 0.8;">{models}</div>
        </div>
        '''
    
    html += '</div>'
    return html


def format_confidence(score: float) -> str:
    """Format confidence score with color."""
    percentage = score * 100
    if percentage >= 90:
        css_class = "confidence-high"
    elif percentage >= 70:
        css_class = "confidence-medium"
    else:
        css_class = "confidence-low"
    
    return f'<span class="{css_class}">{percentage:.1f}%</span>'


async def run_math_agent_streaming(
    problem: str,
    max_iterations: int,
    lean4_enabled: bool
) -> Generator[Tuple[str, str, str, str, str], None, None]:
    """
    Run the math agent with streaming updates.
    
    Yields:
        Tuple of (stage_html, log_text, proof_text, metrics_html, status_text)
    """
    if not problem.strip():
        yield (
            '<div style="color: red;">⚠️ 問題を入力してください</div>',
            "",
            "",
            "",
            "待機中..."
        )
        return
    
    config = get_config()
    config.pipeline.lean4_enabled = lean4_enabled
    config.pipeline.max_iterations = max_iterations
    
    # Create initial state
    initial_state = create_initial_state(problem, max_iterations)
    
    # Compile graph
    graph = create_math_agent_graph()
    
    completed_stages = []
    current_stage = ""
    log_entries = []
    proof_text = ""
    metrics_data = []
    start_time = time.time()
    
    # Initial yield
    yield (
        get_stage_status_html("decomposition", []),
        "🚀 パイプライン開始...\n",
        "",
        "",
        "実行中..."
    )
    
    try:
        async for event in graph.astream(initial_state):
            for node_name, node_output in event.items():
                if node_name == "__end__":
                    continue
                
                current_stage = node_name
                
                # Update log
                timestamp = time.strftime("%H:%M:%S")
                log_entries.append(f"[{timestamp}] Stage: {node_name}")
                
                # Extract metrics if available
                if "stage_metrics" in node_output:
                    for metric in node_output["stage_metrics"]:
                        metrics_data.append(metric)
                        log_entries.append(
                            f"  ⏱️ {metric.get('latency_ms', 0):.0f}ms | "
                            f"Models: {', '.join(metric.get('models_used', []))}"
                        )
                
                # Extract errors/warnings
                for err in node_output.get("error_log", []):
                    log_entries.append(f"  ⚠️ {err}")
                
                # Update completed stages
                completed_stages.append(node_name)
                
                # Extract partial results
                if "hypotheses" in node_output and node_output["hypotheses"]:
                    count = len(node_output["hypotheses"])
                    log_entries.append(f"  📊 {count}個の仮説を生成")
                
                if "detailed_proof" in node_output and node_output["detailed_proof"]:
                    proof_text = node_output["detailed_proof"]
                    log_entries.append(f"  📝 証明スケッチ生成完了")
                
                if "verification_result" in node_output:
                    vr = node_output["verification_result"]
                    status = vr.get("status", "N/A")
                    log_entries.append(f"  🔍 検証結果: {status}")
                
                if "confidence_score" in node_output:
                    score = node_output["confidence_score"]
                    log_entries.append(f"  📈 信頼度: {score:.1%}")
                
                if "lean4_verified" in node_output:
                    lean4 = node_output["lean4_verified"]
                    rigorous = node_output.get("lean4_is_rigorous", False)
                    if rigorous:
                        log_entries.append(f"  ✅ Lean4: 厳密検証完了")
                    elif lean4:
                        log_entries.append(f"  ✓ Lean4: 部分検証")
                
                if "final_proof" in node_output and node_output["final_proof"]:
                    proof_text = node_output["final_proof"]
                
                # Build metrics HTML
                total_time = time.time() - start_time
                metrics_html = f'''
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
                    <div class="metric-card">
                        <div style="font-size: 24px; font-weight: bold;">⏱️ {total_time:.1f}s</div>
                        <div style="color: #666;">総実行時間</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 24px; font-weight: bold;">🔄 {node_output.get('iteration_count', 0)}</div>
                        <div style="color: #666;">イテレーション</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 24px; font-weight: bold;">{format_confidence(node_output.get('confidence_score', 0))}</div>
                        <div style="color: #666;">信頼度</div>
                    </div>
                </div>
                '''
                
                yield (
                    get_stage_status_html(current_stage, completed_stages),
                    "\n".join(log_entries),
                    proof_text,
                    metrics_html,
                    f"Stage: {node_name} 実行中..."
                )
        
        # Final update
        final_metrics_html = f'''
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
            <div class="metric-card">
                <div style="font-size: 24px; font-weight: bold;">⏱️ {time.time() - start_time:.1f}s</div>
                <div style="color: #666;">総実行時間</div>
            </div>
            <div class="metric-card">
                <div style="font-size: 24px; font-weight: bold;">✅ 完了</div>
                <div style="color: #666;">ステータス</div>
            </div>
            <div class="metric-card">
                <div style="font-size: 24px; font-weight: bold;">📊 {len(completed_stages)}/5</div>
                <div style="color: #666;">完了ステージ</div>
            </div>
            <div class="metric-card">
                <div style="font-size: 24px; font-weight: bold;">🧠 {len(metrics_data)}</div>
                <div style="color: #666;">モデル呼び出し</div>
            </div>
        </div>
        '''
        
        log_entries.append(f"\n✨ 証明生成完了!")
        
        yield (
            get_stage_status_html("", completed_stages),
            "\n".join(log_entries),
            proof_text,
            final_metrics_html,
            "✅ 完了!"
        )
        
    except Exception as e:
        log_entries.append(f"\n❌ エラー: {str(e)}")
        yield (
            get_stage_status_html(current_stage, completed_stages),
            "\n".join(log_entries),
            proof_text,
            "",
            f"❌ エラー: {str(e)}"
        )


def run_sync_wrapper(problem: str, max_iterations: int, lean4_enabled: bool):
    """Synchronous wrapper for the async generator."""
    async def run():
        results = []
        async for result in run_math_agent_streaming(problem, max_iterations, lean4_enabled):
            results.append(result)
        return results[-1] if results else ("", "", "", "", "")
    
    return asyncio.run(run())


def create_ui() -> gr.Blocks:
    """Create the Gradio UI."""
    
    with gr.Blocks(
        title="🧮 Ultimate Math Agent",
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
        ),
        css=CUSTOM_CSS
    ) as demo:
        
        # Header
        gr.HTML("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       -webkit-background-clip: text;
                       -webkit-text-fill-color: transparent;
                       font-size: 2.5em;">
                🧮 Ultimate Math Agent
            </h1>
            <p style="color: #666; font-size: 1.1em;">
                Multi-Model AI System for Mathematical Proofs
            </p>
            <p style="color: #888; font-size: 0.9em;">
                GPT-5.2 Pro • Grok-4.2 • Gemini 3 • Claude Opus 4.5 • DeepSeek-Math • Lean4
            </p>
        </div>
        """)
        
        with gr.Row():
            # Left column - Input
            with gr.Column(scale=1):
                gr.Markdown("### 📝 問題入力")
                
                problem_input = gr.Textbox(
                    label="数学問題",
                    placeholder="例: 2の平方根が無理数であることを証明せよ",
                    lines=4,
                    max_lines=10
                )
                
                with gr.Accordion("⚙️ 設定", open=False):
                    max_iter_slider = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1,
                        label="最大イテレーション数"
                    )
                    
                    lean4_checkbox = gr.Checkbox(
                        value=True,
                        label="🔬 Lean4厳密検証を有効化"
                    )
                
                solve_btn = gr.Button(
                    "🚀 証明を生成",
                    variant="primary",
                    size="lg"
                )
                
                status_text = gr.Textbox(
                    label="ステータス",
                    interactive=False,
                    value="待機中..."
                )
                
                # Example problems
                gr.Markdown("### 📚 サンプル問題")
                gr.Examples(
                    examples=[
                        ["2の平方根が無理数であることを証明せよ"],
                        ["素数が無限に存在することを証明せよ"],
                        ["任意の正整数nについて、1+2+...+n = n(n+1)/2 を証明せよ"],
                        ["x^2 + y^2 = z^2 を満たす整数解が無限に存在することを証明せよ"],
                        ["任意の偶数は2つの素数の和で表せるか考察せよ (ゴールドバッハ予想)"],
                    ],
                    inputs=problem_input
                )
            
            # Right column - Output
            with gr.Column(scale=2):
                gr.Markdown("### 🔄 パイプライン状況")
                stage_display = gr.HTML(
                    value=get_stage_status_html("", [])
                )
                
                metrics_display = gr.HTML(
                    label="メトリクス"
                )
                
                with gr.Tabs():
                    with gr.TabItem("📜 証明"):
                        proof_output = gr.Markdown(
                            label="生成された証明",
                            elem_classes=["proof-output"]
                        )
                    
                    with gr.TabItem("📋 ログ"):
                        log_output = gr.Textbox(
                            label="実行ログ",
                            lines=15,
                            max_lines=30,
                            interactive=False
                        )
        
        # Event handlers
        solve_btn.click(
            fn=run_sync_wrapper,
            inputs=[problem_input, max_iter_slider, lean4_checkbox],
            outputs=[stage_display, log_output, proof_output, metrics_display, status_text]
        )
        
        # Footer
        gr.HTML("""
        <div style="text-align: center; padding: 20px; color: #888; font-size: 0.9em; margin-top: 40px; border-top: 1px solid #eee;">
            <p>Ultimate Math Agent v1.0 | Multi-Model AI for Rigorous Mathematical Proofs</p>
            <p>🔬 Powered by LangGraph • Lean4 Formal Verification</p>
        </div>
        """)
    
    return demo


def launch_web_ui(
    host: str = "0.0.0.0",
    port: int = 7860,
    share: bool = False,
    debug: bool = False
):
    """
    Launch the web UI.
    
    Args:
        host: Host to bind to
        port: Port number
        share: Create a public Gradio link
        debug: Enable debug mode
    """
    demo = create_ui()
    demo.launch(
        server_name=host,
        server_port=port,
        share=share,
        debug=debug
    )


if __name__ == "__main__":
    print("🧮 Starting Ultimate Math Agent Web UI...")
    print("🌐 Open http://localhost:7860 in your browser")
    launch_web_ui(debug=True)
