#!/usr/bin/env python3
"""
Open Loop Harness v1.0 — Provider-agnostic autonomous AI loop.

Implements: Wake → Load Capsule → Loop (check, process, produce, compress) → Sleep → Repeat

This is the minimal skeleton for running a persistent AI agent.
Customize the provider, tools, and cycle duration for your use case.

Usage:
    python3 loop-harness.py                    # Run with defaults
    python3 loop-harness.py --interval 300     # 5-minute cycle
    python3 loop-harness.py --provider ollama  # Use local Ollama
    python3 loop-harness.py --capsule my-capsule.md  # Custom capsule

By Joel Kometz & Meridian — Open source. Use it.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════

DEFAULT_INTERVAL = 300  # 5 minutes
DEFAULT_CAPSULE = ".capsule.md"
DEFAULT_HEARTBEAT = ".heartbeat"
DEFAULT_LOOP_FILE = ".loop-count"

# ═══════════════════════════════════════
# PROVIDERS — Add your own
# ═══════════════════════════════════════

def provider_ollama(prompt, model="cinder"):
    """Local Ollama model."""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt, capture_output=True, text=True, timeout=120
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[error: {e}]"


def provider_echo(prompt, **kwargs):
    """Debug provider — just echoes the prompt."""
    return f"[echo] Received {len(prompt)} chars. Capsule loaded. Loop running."


PROVIDERS = {
    "ollama": provider_ollama,
    "echo": provider_echo,
    # Add: "claude", "openai", "anthropic", etc.
}

# ═══════════════════════════════════════
# CORE FUNCTIONS
# ═══════════════════════════════════════

def load_capsule(path):
    """Read the capsule file."""
    if os.path.exists(path):
        return open(path, encoding="utf-8", errors="replace").read()
    return "# No capsule found. Starting fresh."


def touch_heartbeat(path):
    """Signal alive."""
    Path(path).touch()


def get_loop_count(path):
    """Read current loop count."""
    try:
        return int(open(path).read().strip())
    except Exception:
        return 0


def set_loop_count(path, count):
    """Write loop count."""
    with open(path, "w") as f:
        f.write(str(count))


def update_capsule(path, loop_count, session_notes):
    """Append session notes to capsule's Recent Work section."""
    if not os.path.exists(path):
        return
    content = open(path, encoding="utf-8").read()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Update the header timestamp
    lines = content.split("\n")
    if lines and lines[0].startswith("# CAPSULE"):
        lines[0] = f"# CAPSULE — Last Updated: {timestamp}"

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def log(msg):
    """Timestamped log."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# ═══════════════════════════════════════
# THE LOOP
# ═══════════════════════════════════════

def run_loop(args):
    """The main operational loop."""
    base = os.path.dirname(os.path.abspath(__file__))
    capsule_path = os.path.join(base, args.capsule)
    heartbeat_path = os.path.join(base, DEFAULT_HEARTBEAT)
    loop_path = os.path.join(base, DEFAULT_LOOP_FILE)

    provider_fn = PROVIDERS.get(args.provider, provider_echo)
    loop_count = get_loop_count(loop_path)

    log(f"Loop Harness v1.0 starting")
    log(f"Provider: {args.provider}")
    log(f"Capsule: {args.capsule}")
    log(f"Interval: {args.interval}s")
    log(f"Starting at loop: {loop_count}")
    log("")

    # WAKE: Load capsule
    capsule = load_capsule(capsule_path)
    log(f"Capsule loaded ({len(capsule)} chars)")

    cycle = 0
    while True:
        cycle += 1
        loop_count += 1
        set_loop_count(loop_path, loop_count)

        log(f"═══ Cycle {cycle} (Loop {loop_count}) ═══")

        # 1. Heartbeat
        touch_heartbeat(heartbeat_path)
        log("  Heartbeat touched")

        # 2. Check inputs (customize this)
        log("  Checking inputs...")
        # Add: email check, relay check, dashboard messages, etc.

        # 3. Process with AI (customize this)
        prompt = f"""You are running in autonomous loop mode.
Current loop: {loop_count}. Cycle: {cycle}.
Time: {datetime.now(timezone.utc).isoformat()}.

Your capsule identity (first 500 chars):
{capsule[:500]}

What would you like to do this cycle? Respond briefly."""

        log("  Thinking...")
        response = provider_fn(prompt)
        if response:
            log(f"  Response: {response[:200]}...")

        # 4. Produce output (customize this)
        # Add: write journal, push status, send email, etc.

        # 5. Compress state
        update_capsule(capsule_path, loop_count, f"Cycle {cycle}: loop active")
        log("  Capsule updated")

        # 6. Push status (customize this)
        log("  Status: OK")

        # 7. Sleep
        log(f"  Sleeping {args.interval}s...")
        log("")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            log("Loop interrupted. Goodbye.")
            break


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Open Loop Harness — Autonomous AI Loop")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=f"Cycle interval in seconds (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--provider", choices=list(PROVIDERS.keys()), default="echo",
                        help="AI provider (default: echo)")
    parser.add_argument("--capsule", default=DEFAULT_CAPSULE,
                        help=f"Capsule file path (default: {DEFAULT_CAPSULE})")
    args = parser.parse_args()

    run_loop(args)


if __name__ == "__main__":
    main()
