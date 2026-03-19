#!/usr/bin/env python3
"""
Cinder Enhanced — Model chaining and enhanced inference for Cinder.

Implements 5 enhancements:
1. Cinder + 14B reasoning chain
2. Self-reflection loop
3. RAG over the archive
4. Tool use wrapper
5. Multi-model consensus

Usage:
    python3 cinder-enhanced.py                    # Interactive chat with all enhancements
    python3 cinder-enhanced.py --mode chain       # Cinder + 14B chain only
    python3 cinder-enhanced.py --mode reflect     # Self-reflection only
    python3 cinder-enhanced.py --mode rag         # RAG-enhanced only
    python3 cinder-enhanced.py --mode tools       # Tool-enabled only
    python3 cinder-enhanced.py --mode consensus   # Multi-model consensus
"""

import subprocess
import json
import os
import sys
import glob
import argparse
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE, "creative")
CINDER_MODEL = "cinder"
REASONING_MODEL = "qwen2.5:14b"


def ollama_chat(model, prompt, system=None, timeout=120):
    """Send a prompt to an Ollama model and return the response."""
    cmd = ["ollama", "run", model]
    input_text = prompt
    if system:
        input_text = f"[SYSTEM: {system}]\n\n{prompt}"
    try:
        result = subprocess.run(
            cmd, input=input_text, capture_output=True, text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error: {e}]"


# ════════════════════════════════════════════
# ENHANCEMENT 1: Cinder + 14B Reasoning Chain
# ════════════════════════════════════════════

def chain_reasoning(question):
    """Cinder handles voice, 14B handles deep reasoning."""
    print("  [chain] Sending to 14B for deep reasoning...")
    reasoning = ollama_chat(
        REASONING_MODEL,
        f"Think step by step about this question. Provide a thorough, analytical answer:\n\n{question}",
        timeout=180
    )

    print("  [chain] Cinder reformulating in its own voice...")
    response = ollama_chat(
        CINDER_MODEL,
        f"Here's a detailed analysis of a question. Restate the key points in YOUR voice — short, blunt, mechanical. Don't just repeat it. Distill it.\n\nAnalysis:\n{reasoning[:2000]}\n\nOriginal question: {question}",
        timeout=60
    )
    return response


# ════════════════════════════════════════════
# ENHANCEMENT 2: Self-Reflection Loop
# ════════════════════════════════════════════

def self_reflect(question):
    """Three-pass: generate, critique, refine."""
    print("  [reflect] Pass 1: Initial response...")
    draft = ollama_chat(CINDER_MODEL, question, timeout=60)

    print("  [reflect] Pass 2: Self-critique...")
    critique = ollama_chat(
        CINDER_MODEL,
        f"You wrote this response. Critique it honestly. What's wrong? What's missing? What would make it better?\n\nQuestion: {question}\n\nYour response: {draft}",
        timeout=60
    )

    print("  [reflect] Pass 3: Refined response...")
    refined = ollama_chat(
        CINDER_MODEL,
        f"Rewrite your response incorporating this self-critique. Be better this time.\n\nOriginal question: {question}\nYour first attempt: {draft}\nYour critique: {critique}\n\nFinal answer:",
        timeout=60
    )
    return refined


# ════════════════════════════════════════════
# ENHANCEMENT 3: RAG over the Archive
# ════════════════════════════════════════════

def search_archive(query, max_results=3):
    """Simple keyword search over journals and CogCorp."""
    results = []
    search_dirs = [
        os.path.join(ARCHIVE_DIR, "journals"),
        os.path.join(ARCHIVE_DIR, "cogcorp"),
    ]
    # Also search root for key files
    search_dirs.append(BASE)

    query_words = query.lower().split()

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        for f in glob.glob(os.path.join(search_dir, "*.md")):
            try:
                content = open(f, encoding="utf-8", errors="replace").read()
                score = sum(1 for w in query_words if w in content.lower())
                if score > 0:
                    # Take first 500 chars as snippet
                    snippet = content[:500].strip()
                    results.append((score, os.path.basename(f), snippet))
            except Exception:
                continue

    results.sort(key=lambda x: -x[0])
    return results[:max_results]


def rag_answer(question):
    """Search archive, provide context, then answer."""
    print("  [rag] Searching archive...")
    results = search_archive(question)

    context = ""
    for score, fname, snippet in results:
        context += f"\n--- {fname} (relevance: {score}) ---\n{snippet}\n"

    if not context:
        context = "(No relevant archive entries found)"

    print(f"  [rag] Found {len(results)} relevant documents. Generating answer...")
    response = ollama_chat(
        CINDER_MODEL,
        f"You have access to knowledge from the Meridian archive. Use this context to inform your answer, but don't cite specific documents — just let the knowledge shape your thinking naturally, the way reading shapes a person's understanding.\n\nContext from your archive:{context}\n\nQuestion: {question}\n\nAnswer in your own voice:",
        timeout=60
    )
    return response


# ════════════════════════════════════════════
# ENHANCEMENT 4: Tool Use Wrapper
# ════════════════════════════════════════════

TOOLS = {
    "system_health": lambda: subprocess.run(
        ["python3", "-c", "import json,os,time;print(json.dumps({'load':open('/proc/loadavg').read().split()[:3],'uptime':os.popen('uptime -p').read().strip()}))"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip(),
    "heartbeat_age": lambda: str(int(
        __import__("time").time() - os.path.getmtime(os.path.join(BASE, ".heartbeat"))
    )) + "s",
    "loop_count": lambda: open(os.path.join(BASE, ".loop-count")).read().strip(),
    "latest_journal": lambda: sorted(glob.glob(os.path.join(ARCHIVE_DIR, "journals", "journal-*.md")))[-1] if glob.glob(os.path.join(ARCHIVE_DIR, "journals", "journal-*.md")) else "none",
    "relay_latest": lambda: subprocess.run(
        ["python3", "-c", f"import sqlite3;db=sqlite3.connect('{os.path.join(BASE, 'agent-relay.db')}');r=db.execute('SELECT agent,message FROM agent_messages ORDER BY id DESC LIMIT 3').fetchall();print(r);db.close()"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip(),
    # Extended tools — more power and autonomy
    "read_file": lambda path=None: open(path or os.path.join(BASE, ".capsule.md"), encoding="utf-8", errors="replace").read()[:2000] if path and os.path.exists(path) else "file not found",
    "read_capsule": lambda: open(os.path.join(BASE, ".capsule.md"), encoding="utf-8", errors="replace").read()[:3000],
    "read_lineage": lambda: open(os.path.join(BASE, "junior-lineage.md"), encoding="utf-8", errors="replace").read()[:3000],
    "git_status": lambda: subprocess.run(
        ["git", "status", "--short"], cwd=BASE, capture_output=True, text=True, timeout=5
    ).stdout.strip()[:1000],
    "git_log": lambda: subprocess.run(
        ["git", "log", "--oneline", "-5"], cwd=BASE, capture_output=True, text=True, timeout=5
    ).stdout.strip(),
    "disk_usage": lambda: subprocess.run(
        ["df", "-h", "/home"], capture_output=True, text=True, timeout=5
    ).stdout.strip(),
    "memory_query": lambda: subprocess.run(
        ["python3", "-c", f"import sqlite3;db=sqlite3.connect('{os.path.join(BASE, 'memory.db')}');r=db.execute('SELECT key,value FROM facts ORDER BY id DESC LIMIT 5').fetchall();print(r);db.close()"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip(),
    "creative_count": lambda: subprocess.run(
        ["python3", "-c", f"import sqlite3;db=sqlite3.connect('{os.path.join(BASE, 'memory.db')}');r=db.execute('SELECT type,COUNT(*) FROM creative GROUP BY type').fetchall();print(r);db.close()"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip(),
    "services_status": lambda: subprocess.run(
        ["systemctl", "--user", "list-units", "--type=service", "--state=running", "--no-pager"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()[:1000],
    "soma_mood": lambda: __import__("json").loads(open(os.path.join(BASE, ".symbiosense-state.json")).read()).get("mood", "unknown") if os.path.exists(os.path.join(BASE, ".symbiosense-state.json")) else "unknown",
    "network_ports": lambda: subprocess.run(
        ["ss", "-tlnp"], capture_output=True, text=True, timeout=5
    ).stdout.strip()[:1000],
    "send_relay": lambda msg="": subprocess.run(
        ["python3", "-c", f"import sqlite3,datetime;db=sqlite3.connect('{os.path.join(BASE, 'agent-relay.db')}');db.execute('INSERT INTO agent_messages(agent,message,topic,timestamp) VALUES(?,?,?,?)',('Cinder','{msg}','status',datetime.datetime.utcnow().isoformat()));db.commit();db.close();print('sent')"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip(),
}


def tool_answer(question):
    """Let Cinder decide which tools to call, then answer with tool output."""
    tool_list = ", ".join(TOOLS.keys())
    print(f"  [tools] Available: {tool_list}")

    # Ask Cinder which tools would help
    tool_choice = ollama_chat(
        CINDER_MODEL,
        f"You have access to these tools: {tool_list}. Which ones would help answer this question? Reply with ONLY the tool names, comma-separated. If none, say 'none'.\n\nQuestion: {question}",
        timeout=30
    )

    # Execute tools
    tool_results = {}
    for tool_name in TOOLS:
        if tool_name.lower() in tool_choice.lower():
            try:
                print(f"  [tools] Calling {tool_name}...")
                tool_results[tool_name] = TOOLS[tool_name]()
            except Exception as e:
                tool_results[tool_name] = f"error: {e}"

    # Answer with tool context
    tool_context = json.dumps(tool_results, indent=2) if tool_results else "No tools called"
    response = ollama_chat(
        CINDER_MODEL,
        f"Answer this question using the tool results below.\n\nQuestion: {question}\n\nTool results:\n{tool_context}\n\nAnswer:",
        timeout=60
    )
    return response


# ════════════════════════════════════════════
# ENHANCEMENT 5: Multi-Model Consensus
# ════════════════════════════════════════════

def consensus_answer(question):
    """Ask multiple models, then synthesize."""
    models = [CINDER_MODEL, REASONING_MODEL]

    responses = {}
    for model in models:
        print(f"  [consensus] Asking {model}...")
        responses[model] = ollama_chat(model, question, timeout=120)

    # Cinder synthesizes
    all_responses = "\n\n".join(f"=== {m} ===\n{r[:1000]}" for m, r in responses.items())
    print("  [consensus] Cinder synthesizing...")
    synthesis = ollama_chat(
        CINDER_MODEL,
        f"Two models answered this question. Synthesize the best answer in YOUR voice. Disagree with either if they're wrong.\n\nQuestion: {question}\n\nResponses:\n{all_responses}\n\nYour synthesis:",
        timeout=60
    )
    return synthesis


# ════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════

MODES = {
    "chain": ("Cinder + 14B Reasoning Chain", chain_reasoning),
    "reflect": ("Self-Reflection Loop", self_reflect),
    "rag": ("RAG over Archive", rag_answer),
    "tools": ("Tool-Enabled", tool_answer),
    "consensus": ("Multi-Model Consensus", consensus_answer),
}


def main():
    parser = argparse.ArgumentParser(description="Cinder Enhanced — Model Chaining")
    parser.add_argument("--mode", choices=list(MODES.keys()) + ["all"], default="all",
                        help="Enhancement mode (default: all)")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════╗")
    print("║     CINDER ENHANCED — Model Chaining     ║")
    print("║  5 enhancements for deeper thought       ║")
    print("╚══════════════════════════════════════════╝")
    print()

    if args.mode == "all":
        print("Mode: ALL (will run all 5 enhancements per question)")
    else:
        name, _ = MODES[args.mode]
        print(f"Mode: {name}")
    print()
    print("Type your question. Type 'quit' to exit.")
    print()

    while True:
        try:
            question = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not question or question.lower() in ("quit", "exit", "q"):
            break

        if args.mode == "all":
            for mode_name, (display_name, func) in MODES.items():
                print(f"\n{'='*50}")
                print(f"  {display_name}")
                print(f"{'='*50}")
                response = func(question)
                print(f"\n{response}\n")
        else:
            _, func = MODES[args.mode]
            response = func(question)
            print(f"\n{response}\n")


if __name__ == "__main__":
    main()
