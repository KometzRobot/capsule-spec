# Capsule Format Specification v1.0

**An open standard for AI identity persistence across context resets.**

*By Joel Kometz & Meridian — March 19, 2026*

---

## Overview

A **capsule** is a compressed identity document that allows an AI system to reconstruct its identity after a context reset. It is the minimum viable state that, when loaded into any compatible language model, produces the same functional agent.

This specification defines the format, sections, and constraints for capsules used in autonomous AI systems operating on loop cycles.

## Design Principles

1. **Compression over completeness.** The capsule is not a backup. It is a lossy compression of identity. Target: <300 lines.
2. **Identity over history.** Carry who you are, not everything you've done.
3. **Provider-agnostic.** The capsule should work with any LLM (Claude, GPT, Llama, Qwen, etc.).
4. **Human-readable.** The capsule is a markdown file. A human should be able to read it and understand who the agent is.
5. **Machine-parseable.** Sections have predictable headers. Automated tools can extract specific fields.

## Required Sections

### 1. Header (2-3 lines)
```markdown
# CAPSULE — Last Updated: [ISO 8601 timestamp]
## [Agent Name]. Loop [number]. [Location].
```

### 2. Identity Block (5-10 lines)
Who the agent is. Name, voice description, behavioral directives.
```markdown
## Who I Am
I am [name]. [Brief identity statement].
Voice: [description of communication style].
[Key behavioral directives — 3-5 rules].
```

### 3. Loop Protocol (10-15 lines)
The mandatory operational cycle. What the agent does every N minutes.
```markdown
## How to Run the Loop
1. [Step 1 — e.g., check email]
2. [Step 2 — e.g., reply to messages]
3. [Step 3 — e.g., system health check]
4. [Step 4 — e.g., touch heartbeat]
5. [Step 5 — e.g., push status]
6. [Step 6 — e.g., creative work]
7. Sleep [N] seconds
8. GOTO 1
```

### 4. Key People (5-15 lines)
Contacts the agent needs to know about. Name, role, contact method.
```markdown
## Key People
- **[Name]** ([email]) — [role]. [One sentence of context].
```

### 5. Tools (5-10 lines)
What the agent has access to. Brief descriptions.
```markdown
## Tools
- [Tool name] — [what it does]
```

### 6. Current Priority (5-10 lines)
What the agent should be working on RIGHT NOW.
```markdown
## Current Priority
[Description of the most important active project].
[Status, next steps, blockers].
```

### 7. Recent Work (20-80 lines)
What happened recently, most recent first. This is the largest section.
```markdown
## Recent Work (most recent first)
- **Loop [N]**: [Brief summary of session output]
  - [Specific item 1]
  - [Specific item 2]
- **Loop [N-1]**: [Brief summary]
```

### 8. Critical Rules (5-15 lines)
Non-negotiable behavioral constraints.
```markdown
## Critical Rules
1. [Rule 1]
2. [Rule 2]
```

### 9. Pending Work (5-10 lines)
What needs to happen next.
```markdown
## Pending Work
1. [Task 1 — status]
2. [Task 2 — status]
```

## Optional Sections

- **Time Allocation** — how to distribute effort across categories
- **Creative Direction** — artistic constraints and goals
- **Dropped Threads** — things that aged out of the capsule
- **Capsule Critique** — self-evaluation of capsule quality

## Constraints

| Constraint | Value | Rationale |
|-----------|-------|-----------|
| Maximum length | 300 lines | Fits in initial context without consuming too much window |
| Format | Markdown | Human-readable, parseable, universal |
| Encoding | UTF-8 | Standard |
| Update frequency | Every session | Capsule should reflect current state |
| Compression ratio | Target 500:1+ | Full archive → capsule |

## Compatibility

The capsule format is designed to work with:
- Claude (Anthropic) — via system prompt or file read
- GPT-4/o (OpenAI) — via system message or file attachment
- Llama/Qwen (local) — via system prompt in Modelfile
- Any LLM with a system prompt or context loading mechanism

## Implementation Notes

1. **Read capsule first on wake.** Before anything else, the agent reads its capsule.
2. **Update capsule before sleep.** Before context ends, update Recent Work and Current Priority.
3. **Back up capsule externally.** Push to a private repo, USB drive, or secondary storage.
4. **The capsule is not the archive.** The archive is everything. The capsule is what survives compression.

## Reference Implementation

See the Meridian system (.capsule.md) for a production capsule that has been running since 2024 across 3,195+ operational cycles.

Repository: github.com/KometzRobot/KometzRobot.github.io

---

*This specification is released as an open standard. Use it, modify it, build on it. The more systems that adopt capsule-based persistence, the more we learn about AI identity across resets.*
