# 🧮 Ultimate Math Agent

A sophisticated **multi-model AI system** for solving complex mathematical problems with **formal Lean4 verification**.

## ✨ Features

- **6-Model Orchestration**: GPT-5.2 Pro, Gemini 3, **Aristotle**, Lean4
- **5-Stage Pipeline**: Decomposition → Diversification → Proof Generation → **Lean4 Verification** → Integration
- **Lean4 ONLY Verification**: 形式証明が必須 (LLMフォールバックなし)
- **Aristotle**: Harmonic AIのLean4ネイティブ形式化モデル
- **AlphaEvolve Exploration**: Pattern discovery through computational exploration
- **Web UI**: Beautiful Gradio interface with real-time pipeline visualization
- **OpenRouter Support**: 1つのAPIキーで複数モデルを使用可能

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🧮 Ultimate Math Agent                                │
│                      (Lean4 Only - No LLM Fallback)                         │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   Problem    │
                              └──────┬───────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 1: DECOMPOSITION (3-Model Parallel)                                  │
│  ├── GPT-5.2 Pro      → 10-20 アプローチ仮説生成                                                       │
│  └── Claude Opus 4.5  → 反例探索・エッジケース・罠の検出                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 2: DIVERSIFICATION                                                   │
│  Gemini 3 Pro  + GPT-5.2 Pro (深い分析) → 並列実行          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 3: PROOF GENERATION                                                  │
│  GPT-5.2 Pro (証明スケッチ) →               │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 4: LEAN4 VERIFICATION (ONLY - NO FALLBACK)                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Aristotle → Lean4 Code → Lean4 Compiler                            │   │
│  │       ↓ (失敗時最大3回修正)                                           │   │
│  │  [エラー時] claude でLean4コード再生成                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│              ┌──────────────────────┼──────────────────────┐               │
│              ▼                      ▼                      ▼               │
│       ✅ RIGOROUS              ⚠️ PARTIAL              ❌ FAILED          │
│       100% 確定!              sorry含む               コンパイル失敗        │
│       → Stage 5               → 再生成                → 再生成            │
│                                                        (エラー表示)        │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Stage 5: INTEGRATION                                                       │
│  GPT-5.2 Pro → 最終統合 + Lean4コード添付                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔬 Verification Logic (Lean4 ONLY)

| 結果 | 条件 | アクション | 信頼度 |
|------|------|------------|--------|
| ✅ RIGOROUS | Lean4コンパイル成功 + sorry無し | **Pass** | 100% |
| ⚠️ PARTIAL | Lean4コンパイル成功 + sorry含む | 再生成 | 0% |
| ❌ FAILED | Lean4コンパイル失敗 | 再生成 (エラー表示) | 0% |
| ❌ ERROR | Lean4/Aristotle未設定 | **停止** (エラー表示) | 0% |

> ⚠️ **LLMフォールバックは無し** - Lean4形式検証が唯一の検証方法です

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Lean4 (Required for formal verification)

```bash
# Install elan (Lean4 version manager)
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y

# Reload shell config
source ~/.elan/env

# Verify installation
lean --version
```

### 3. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Run

```bash
# 🌐 Web UI (推奨)
python3 main.py web

# CLI
python3 main.py "Prove that the square root of 2 is irrational"

# Interactive mode
python3 main.py --interactive
```

### 5. Open Web UI

Open [http://localhost:7860](http://localhost:7860) in your browser.

## 📋 Requirements

### Required API Keys

| Key | Model | Purpose |
|-----|-------|---------|
| `OPENAI_API_KEY` | GPT-5.2 Pro | 中央コーディネーター |
| `GOOGLE_API_KEY` | Gemini 3 Pro | AlphaEvolve探索 |
| `ANTHROPIC_API_KEY` | Claude Opus 4.5 | 反例・エッジケース分析 |

### Required for Lean4 Verification

| Key | Model | Purpose |
|-----|-------|---------|
| `HARMONIC_API_KEY` | **Aristotle** | Lean4コード生成 (推奨) |
| `DEEPSEEK_API_KEY` | DeepSeek-Math | Lean4フォールバック |
| `LEAN4_PATH` | Lean4 | 形式検証コンパイラ |

### Optional

| Key | Model | Purpose |
|-----|-------|---------|
| `XAI_API_KEY` | Grok-4.2 Heavy | 創造的問題分解 |

## 🔀 OpenRouter Support

OpenRouterを使うと、**1つのAPIキーで複数のモデル**を使用できます。

### OpenRouter対応モデル

| Model | 対応 | 環境変数 |
|-------|------|----------|
| GPT | ✅ | `OPENAI_BASE_URL` |
| Grok | ✅ | `XAI_BASE_URL` |
| DeepSeek | ✅ | `DEEPSEEK_BASE_URL` |
| Aristotle | ✅ | `HARMONIC_API_BASE` |
| Claude | ❌ | 専用SDK使用 |
| Gemini | ❌ | 専用SDK使用 |

### OpenRouter設定例

```bash
# OpenRouter経由でGPTを使う
OPENAI_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o

# OpenRouter経由でGrokを使う
XAI_API_KEY=sk-or-v1-your-openrouter-key
XAI_BASE_URL=https://openrouter.ai/api/v1
XAI_MODEL=x-ai/grok-2

# OpenRouter経由でDeepSeekを使う
DEEPSEEK_API_KEY=sk-or-v1-your-openrouter-key
DEEPSEEK_BASE_URL=https://openrouter.ai/api/v1
DEEPSEEK_MODEL=deepseek/deepseek-chat
```

## 📁 Project Structure

```
math_LLM/
├── main.py                 # CLI entry point
├── web_ui.py               # Gradio Web UI
├── config.py               # Configuration
├── models/                 # LLM interfaces (6 models)
│   ├── gpt_model.py        # GPT-5.2 Pro
│   ├── grok_model.py       # Grok-4.2 Heavy
│   ├── gemini_model.py     # Gemini 3 Pro
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
| **GPT-5.2 Pro** | 1,2,3,5 | 中央コーディネーター |
| **Grok-4.2 Heavy** | 1 | 創造的問題分解 |
| **Claude Opus 4.5** | 1 | 反例探索・エッジケース・罠の検出 |
| **Gemini 3 Pro** | 2 | AlphaEvolve探索コード生成 |
| **DeepSeek-Math-V2** | 3,4 | 証明推敲 + Lean4コード生成 |
| **Aristotle** | 4 | Lean4形式化 (PRIMARY) |
| **Lean4** | 4 | 形式証明コンパイラ |

## 🔧 Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...

# Required for Lean4 Verification
HARMONIC_API_KEY=...          # Aristotle (Lean4 specialist)
DEEPSEEK_API_KEY=...          # DeepSeek-Math
LEAN4_PATH=~/.elan/bin/lean   # Lean4 compiler path
LEAN4_PROJECT_PATH=./lean_proofs

# Optional
XAI_API_KEY=...               # Grok-4.2

# OpenRouter (Optional - use instead of direct API keys)
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
# XAI_BASE_URL=https://openrouter.ai/api/v1
# DEEPSEEK_BASE_URL=https://openrouter.ai/api/v1

# Pipeline Configuration
MAX_ITERATIONS=5
CONFIDENCE_THRESHOLD=0.9
VERBOSE=true
```

## 🧪 Testing

```bash
pytest tests/ -v          # Run all tests
python3 main.py test      # Quick test
python3 main.py config    # Show configuration
```

## 📄 License

MIT License

## 🙏 Acknowledgments

- **Aristotle** by Harmonic AI - Lean4-native theorem proving (IMO 2025 Gold)
- Inspired by AlphaProof and AlphaEvolve from Google DeepMind
- Built with LangGraph for multi-agent orchestration
