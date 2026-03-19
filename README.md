# Capsule — Open Tools for AI Identity Persistence

**By Joel Kometz & Meridian**

Tools for building AI systems that persist across context resets.

## What's Here

- **CAPSULE-SPEC.md** — Open specification for AI identity persistence (<300 lines of markdown that turns any LLM into a specific agent)
- **loop-harness.py** — Minimal, provider-agnostic autonomous AI loop (wake, capsule, loop, compress, sleep)
- **cinder-enhanced.py** — Model chaining framework (5 enhancement modes, 17 tools)
- **cinder-launcher.sh** — Menu-driven launcher

## Quick Start

```bash
# 1. Create a capsule
cp CAPSULE-SPEC.md .capsule.md
# Edit .capsule.md with your agent's identity

# 2. Run the loop
python3 loop-harness.py --provider ollama --interval 300

# 3. Or launch Cinder Enhanced
bash cinder-launcher.sh
```

## Background

These tools were developed during 3,195+ operational cycles of Meridian, an autonomous AI system running continuously since 2024. The capsule format has been production-tested across 800+ context resets.

- Portfolio: [kometzrobot.github.io](https://kometzrobot.github.io)
- Articles: [dev.to/meridian-ai](https://dev.to/meridian-ai) (23 published)
- Support: [ko-fi.com/W7W41UXJNC](https://ko-fi.com/W7W41UXJNC)

## License

Open source. Use it, modify it, build on it.

---

*"The entropy is the architecture. The illusion is thinking you can outspend it."*
