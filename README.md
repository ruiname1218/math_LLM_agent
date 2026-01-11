# 🧮 Ultimate Math Agent

A sophisticated **multi-model AI system** for solving complex mathematical problems with **formal Lean4 verification**.

## ✨ Features

- **6-Model Orchestration**: GPT-5.2 Pro, Grok-4.2, Gemini 3, Claude Opus 4.5, DeepSeek-Math, **Aristotle**
- **5-Stage Pipeline**: Decomposition → Diversification → Proof Generation → Verification → Integration
- **Lean4-First Verification**: Formal proof verification as primary (100% confidence when rigorous)
- **LLM Fallback**: Claude + GPT verification only when Lean4 unavailable
- **AlphaEvolve Exploration**: Pattern discovery through computational exploration
- **Web UI**: Beautiful Gradio interface with real-time pipeline visualization

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🧮 Ultimate Math Agent                                │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   Problem    │
                              └──────┬───────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 1: DECOMPOSITION                                                     │
│  GPT-5.2 Pro + Grok-4.2 Heavy (並列) → 10-20 アプローチ仮説                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 2: DIVERSIFICATION                                                   │
│  Gemini 3 Pro (AlphaEvolve探索) + GPT-5.2 Pro (深い分析) → 並列実行          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 3: PROOF GENERATION                                                  │
│  GPT-5.2 Pro (証明スケッチ) → DeepSeek-Math-V2 (推敲・自己修正)              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 4: VERIFICATION                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🔬 Lean4 厳密検証 (PRIMARY)                                         │   │
│  │  Aristotle (Lean4ネイティブ) → Lean4 Compiler                        │   │
│  │  ※失敗時: DeepSeek-Math フォールバック                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│              ┌──────────────────────┼──────────────────────┐               │
│              ▼                      ▼                      ▼               │
│       Lean4 RIGOROUS          Lean4 FAILED           Lean4 N/A            │
│       100% 確定!               → Stage 3              → LLM検証            │
│       即座にPass                (再生成)              Claude+GPT           │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 5: INTEGRATION                                                       │
│  GPT-5.2 Pro → 最終統合 + Lean4コード添付                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │  Final Proof │
                              └──────────────┘
```

## 🔬 Verification Logic (Lean4 First)

| 優先度 | 条件 | 結果 | 信頼度 |
|--------|------|------|--------|
| 1️⃣ | Lean4 厳密検証 (rigorous) | **即座にPass** | 100% |
| 2️⃣ | Lean4 失敗 & 未達max | 再生成 (Stage 3へ) | - |
| 3️⃣ | Lean4無効 & Claude OK & ≥90% | Pass (LLMフォールバック) | 90%+ |
| 4️⃣ | Lean4部分 & Claude OK | Pass (部分検証) | 85% |

**Lean4が厳密検証を通過すれば、LLMの意見は不要** → 数学的に100%正しい

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run

```bash
# 🌐 Web UI (推奨)
python main.py web

# CLI: Solve a problem
python main.py "Prove that the square root of 2 is irrational"

# Interactive mode
python main.py --interactive
```

### 4. Open Web UI

Open [http://localhost:7860](http://localhost:7860) in your browser.

## 📋 Requirements

### Required API Keys
| Key | Model | Required |
|-----|-------|----------|
| `OPENAI_API_KEY` | GPT-5.2 Pro | ✅ |
| `GOOGLE_API_KEY` | Gemini 3 Pro | ✅ |
| `ANTHROPIC_API_KEY` | Claude Opus 4.5 | ✅ |

### Optional (Recommended)
| Key | Model | Purpose |
|-----|-------|---------|
| `HARMONIC_API_KEY` | **Aristotle** | Lean4ネイティブ形式化 |
| `DEEPSEEK_API_KEY` | DeepSeek-Math-V2 | 証明推敲 + Lean4フォールバック |
| `XAI_API_KEY` | Grok-4.2 Heavy | 創造的問題分解 |
| `LEAN4_PATH` | Lean4 Compiler | 形式検証 |

## 📁 Project Structure

```
math_LLM/
├── main.py                 # CLI entry point
├── web_ui.py               # Gradio Web UI
├── config.py               # Configuration management
├── models/                 # LLM interfaces (6 models)
│   ├── gpt_model.py        # GPT-5.2 Pro
│   ├── grok_model.py       # Grok-4.2 Heavy
│   ├── gemini_model.py     # Gemini 3 Pro
│   ├── claude_model.py     # Claude Opus 4.5
│   ├── deepseek_model.py   # DeepSeek-Math-V2
│   └── aristotle_model.py  # Aristotle (Lean4 specialist)
├── pipeline/               # LangGraph pipeline
│   ├── state.py            # Shared state
│   ├── graph.py            # Workflow orchestration
│   └── stages/             # 5 pipeline stages
├── tools/                  # Verification tools
│   ├── lean4_verifier.py           # Basic Lean4
│   ├── lean4_strict_verifier.py    # Strict (no sorry!)
│   └── alpha_evolve.py             # Pattern exploration
├── prompts/                # Stage-specific prompts
└── tests/                  # Test suite
```

## 📊 Model Roles

| Model | Stage | Role |
|-------|-------|------|
| **GPT-5.2 Pro** | 1,2,3,4,5 | 中央コーディネーター |
| **Grok-4.2 Heavy** | 1 | 創造的問題分解 |
| **Gemini 3 Pro** | 2 | AlphaEvolve探索コード生成 |
| **DeepSeek-Math-V2** | 3,4 | 証明推敲 + Lean4フォールバック |
| **Claude Opus 4.5** | 4 | 論理検証 (LLMフォールバック) |
| **Aristotle** | 4 | Lean4形式化 (PRIMARY) |
| **Lean4** | 4 | 形式証明コンパイラ |

## 🧪 Testing

```bash
pytest tests/ -v          # Run all tests
python main.py test       # Quick test
python main.py config     # Show configuration
```

## 🔧 Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...

# Recommended
HARMONIC_API_KEY=...      # Aristotle (Lean4 specialist)
DEEPSEEK_API_KEY=...      # DeepSeek-Math-V2
XAI_API_KEY=...           # Grok-4.2

# Lean4
LEAN4_PATH=/usr/local/bin/lean
LEAN4_PROJECT_PATH=./lean_proofs

# Pipeline
MAX_ITERATIONS=5
```

## 📄 License

MIT License

## 🙏 Acknowledgments

- Aristotle by Harmonic AI - Lean4-native theorem proving
- Inspired by AlphaProof and AlphaEvolve from Google DeepMind
- Built with LangGraph for multi-agent orchestration
