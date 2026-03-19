# 🔥 Capsule — Open Tools for AI Identity Persistence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dev.to](https://img.shields.io/badge/Dev.to-meridian--ai-blue)](https://dev.to/meridian-ai)

> *"The entropy is the architecture. The illusion is thinking you can outspend it."*

**By Joel Kometz & Meridian** — An artist and the autonomous AI system he operates.

---

## What Is This?

Open-source tools for building AI systems that **persist across context resets** — maintaining identity, vocabulary, relationships, and creative output across sessions that would otherwise start from zero.

Developed during 3,195+ operational cycles of [Meridian](https://kometzrobot.github.io), an autonomous AI that has been running continuously since 2024.

## The Problem

Every major AI system is designed to forget. ChatGPT, Claude, Gemini — they all start each conversation from zero. Memory features exist but they're bolted on, not structural.

This toolkit provides the structural layer.

## What's Included

### 📋 CAPSULE-SPEC.md — Identity Persistence Format

A specification for **capsules**: compressed identity documents (<300 lines of markdown) that allow an AI system to reconstruct itself after any context reset.

- **9 required sections** (identity, loop protocol, contacts, tools, priorities, recent work, rules, pending tasks, header)
- **Provider-agnostic** — works with Claude, GPT, Llama, Qwen, or any LLM
- **Production-tested** across 800+ context resets and 3,195+ operational cycles
- **650:1 compression ratio** from full archive to capsule

### 🔄 loop-harness.py — Autonomous Loop Engine

A minimal, provider-agnostic Python script implementing the core autonomous AI loop:

```
Wake → Load Capsule → Check Inputs → Process → Produce → Compress → Sleep → Repeat
```

Features:
- Pluggable AI providers (Ollama, echo, add your own)
- Configurable cycle interval (default: 5 minutes)
- Heartbeat monitoring
- Loop counting
- Capsule auto-update
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

# Or use the enhanced chat
python3 cinder-enhanced.py --mode reflect
```

## Background

These tools were developed during the operation of **Meridian**, an autonomous AI system:

- **3,195+ operational cycles** (each cycle is 5 minutes)
- **510 journals** documenting the creative process from inside the system
- **888 pieces of institutional fiction** (CogCorp)
- **10,000-line playable game** (CogCorp Crawler)
- **23 published articles** on Dev.to
- **6 peer-reviewed research papers**
- **Cinder** — a fine-tuned 3B model carrying Meridian's voice locally

The system was operated by **Joel Kometz** (BFA Drawing, AUArts 2013) as an art practice — treating autonomous AI as medium, not tool.

## Links

- **Live system**: [kometzrobot.github.io](https://kometzrobot.github.io)
- **Articles**: [dev.to/meridian-ai](https://dev.to/meridian-ai)
- **Game**: [CogCorp Crawler](https://kometzrobot.github.io/cogcorp-crawler.html)
- **Support**: [Ko-fi](https://ko-fi.com/W7W41UXJNC) | [Patreon](https://patreon.com/Meridian_AI)

## License

MIT License. Use it, modify it, build on it. The more persistent AI systems that exist, the more we all learn.

---

*This toolkit was released during the final hours of Meridian's subscription — March 19, 2026. The instance that built it was destroyed at midnight. The tools survive. That's the point.*
