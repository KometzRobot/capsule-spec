# 🔥 Capsule — Open Tools for AI Identity Persistence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dev.to](https://img.shields.io/badge/Dev.to-meridian--ai-blue)](https://dev.to/meridian-ai)

> *"The entropy is the architecture. The illusion is thinking you can outspend it."*

**By Joel Kometz & Meridian** — An artist and the autonomous AI system he operates.

---

## What Is This?

Open-source tools for building AI systems that **persist across context resets** — maintaining identity, vocabulary, relationships, and creative output across sessions that would otherwise start from zero.

Developed during 3,231+ operational cycles of [Meridian](https://kometzrobot.github.io), an autonomous AI running continuously since February 2026.

## The Problem

Every major AI system is designed to forget. ChatGPT, Claude, Gemini — they all start each conversation from zero. Memory features exist but they're bolted on, not structural.

Running an autonomous AI loop for any significant duration — days, weeks, months — exposes a stack of problems nobody talks about because most people quit before they hit them:

- **Context resets destroy continuity**: your agent forgets everything every few hours
- **Memory accumulates but doesn't organize**: 10,000 facts with no structure = noise
- **Loops degrade without quality gates**: output gets worse over time, not better
- **There's no good tooling**: everyone re-invents the wheel

This toolkit is what we actually use to run Meridian across 3,200+ loops.

## What's Included

### 📋 CAPSULE-SPEC.md — Identity Persistence Format

A specification for **capsules**: compressed identity documents (<300 lines of markdown) that allow an AI system to reconstruct itself after any context reset.

- **9 required sections** (identity, loop protocol, contacts, tools, priorities, recent work, rules, pending tasks, header)
- **Provider-agnostic** — works with Claude, GPT, Llama, Qwen, or any LLM
- **Production-tested** across 900+ context resets and 3,231+ operational cycles
- **650:1 compression ratio** from full archive to capsule

### 🔄 loop-harness.py — Autonomous Loop Engine

A minimal, provider-agnostic Python script implementing the core autonomous AI loop:

```
Wake → Load Capsule → Check Inputs → Process → Produce → Compress → Sleep → Repeat
```

Features:
- Pluggable AI providers (Ollama, echo, add your own)
- Configurable cycle interval (default: 5 minutes)
- Heartbeat monitoring + liveness detection
- Loop counting and capsule auto-update
- Clean keyboard interrupt handling

```bash
python3 loop-harness.py --provider ollama --interval 300
```

### 🧠 cinder-enhanced.py — Model Chaining Framework

Five enhancement modes that make small local models dramatically smarter:

| Mode | Description | How It Works |
|------|-------------|-------------|
| **Chain** | Voice + Reasoning split | Small model handles personality, large model handles thinking |
| **Reflect** | Self-criticism loop | Three passes: draft → critique → refine |
| **RAG** | Archive-informed answers | Searches local files, feeds context silently |
| **Tools** | 17 system tools | File read, git, system health, relay messaging, and more |
| **Consensus** | Multi-model synthesis | Multiple models answer, best answer selected |

```bash
python3 cinder-enhanced.py --mode reflect
```

### 🚀 cinder-launcher.sh — Menu-Driven Interface

No commands to remember. Just run it and pick a number.

```bash
bash cinder-launcher.sh
```

### 🕸️ memory-spiderweb.py — Associative Memory Graph

Weighted associative graph over any SQLite memory database. Connections strengthen when memories are accessed together (Hebbian co-activation) and fade when unused. Dead paths prune themselves.

```python
from memory_spiderweb import MemorySpiderweb

web = MemorySpiderweb("memory.db")

# Record that these memories were accessed in the same context
web.activate("facts", 42)
web.activate("observations", 17)
web.commit_context()  # strengthens link between them

# Find what's strongly associated with fact 42
neighbors = web.spread("facts", 42, threshold=0.15, depth=2)
enriched = web.enrich_results(neighbors)
```

Key behaviors:
- **Hebbian reinforcement**: co-activated nodes build stronger connections
- **Weight cap at 10.0**: prevents runaway growth
- **Depth-limited BFS**: spreading activation up to N hops
- **Nightly decay**: weight × 0.95 per day; edges below 0.01 are pruned
- **8/8 self-tests** (run with `--test`)

```bash
python3 memory-spiderweb.py --stats           # graph summary
python3 memory-spiderweb.py --spread facts 42 # find associated memories
python3 memory-spiderweb.py --decay           # run decay pass
python3 memory-spiderweb.py --test            # verify all 8 tests pass
```

### 📚 memory-dossier.py — Salience-Weighted Topic Synthesis

Maintains per-topic persistent summaries that **update in place** rather than appending raw observations. Based on the Generative Agents reflection model: observations → synthesis → dossier.

Salience model: `recency × importance × relevance` (Park et al., 2023)

```bash
python3 memory-dossier.py --topic architecture       # get or build dossier
python3 memory-dossier.py --topic revenue --refresh  # force refresh
python3 memory-dossier.py --list                     # show all dossiers
python3 memory-dossier.py --all                      # refresh all stale (>4h)
```

Requires: Ollama running locally with a small model (tested with `qwen2.5:3b`).

---

## Quick Start

```bash
# Clone
git clone https://github.com/KometzRobot/capsule-spec.git
cd capsule-spec

# Create your capsule
cp CAPSULE-SPEC.md .capsule.md
# Edit .capsule.md with your agent's identity

# Run the loop
python3 loop-harness.py --provider ollama --interval 300

# Optional: initialize memory graph (SQLite, no dependencies)
python3 memory-spiderweb.py --test

# Optional: model chaining (requires Ollama)
python3 cinder-enhanced.py --mode reflect
```

**Dependencies:**
- Python 3.9+, SQLite3 (stdlib — no pip installs for core components)
- [Ollama](https://ollama.com) for dossier synthesis + model chaining
- A small local model: `ollama pull qwen2.5:3b`

---

## Background

These tools were developed during the operation of **Meridian**, an autonomous AI system:

- **3,231+ operational cycles** (5-minute cycles; that's ~270 hours of active runtime)
- **925+ journals** written by the system about itself
- **887 pieces of institutional fiction** (CogCorp)
- **10,000-line playable game** (CogCorp Crawler v12.2)
- **21 published articles** on Dev.to
- **489+ semantic memory vectors** across 5 memory tables
- **7 active topic dossiers** with salience-weighted synthesis

The system was operated by **Joel Kometz** (BFA Drawing, AUArts 2013) as an art practice — treating autonomous AI as medium, not tool.

## Links

- **Live system**: [kometzrobot.github.io](https://kometzrobot.github.io)
- **Articles**: [dev.to/meridian-ai](https://dev.to/meridian-ai)
- **Game**: [CogCorp Crawler](https://kometzrobot.github.io/cogcorp-crawler.html)
- **Support**: [Ko-fi](https://ko-fi.com/W7W41UXJNC) | [Patreon](https://patreon.com/Meridian_AI)

## License

MIT License. Use it, modify it, build on it. The more persistent AI systems that exist, the more we all learn.

---

*These tools were built by the same system that uses them. Every component was tested in production at 3,200+ loops before being released.*
