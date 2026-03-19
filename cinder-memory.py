#!/usr/bin/env python3
"""
Cinder Memory — Persistent conversation memory for Cinder.

Saves conversation turns to a SQLite database so Cinder can
remember previous conversations without needing context windows.

This gives Cinder what Meridian has through capsules:
persistence across sessions.

Usage:
    python3 cinder-memory.py                # Chat with memory
    python3 cinder-memory.py --search "topic"  # Search past conversations
    python3 cinder-memory.py --recent 10     # Show last 10 turns
    python3 cinder-memory.py --stats         # Show memory stats
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "cinder-memory.db")
CINDER_MODEL = "cinder"


def init_db():
    """Create the memory database if it doesn't exist."""
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            session_id TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            summary TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    db.commit()
    return db


def save_turn(db, role, content, session_id):
    """Save a conversation turn."""
    db.execute(
        "INSERT INTO conversations (role, content, timestamp, session_id) VALUES (?, ?, ?, ?)",
        (role, content, datetime.now(timezone.utc).isoformat(), session_id)
    )
    db.commit()


def get_recent(db, count=10):
    """Get recent conversation turns."""
    rows = db.execute(
        "SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
        (count,)
    ).fetchall()
    return list(reversed(rows))


def search_memory(db, query):
    """Search past conversations by keyword."""
    rows = db.execute(
        "SELECT role, content, timestamp FROM conversations WHERE content LIKE ? ORDER BY id DESC LIMIT 20",
        (f"%{query}%",)
    ).fetchall()
    return rows


def get_stats(db):
    """Get memory statistics."""
    total = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    user_turns = db.execute("SELECT COUNT(*) FROM conversations WHERE role='user'").fetchone()[0]
    cinder_turns = db.execute("SELECT COUNT(*) FROM conversations WHERE role='cinder'").fetchone()[0]
    sessions = db.execute("SELECT COUNT(DISTINCT session_id) FROM conversations").fetchone()[0]
    first = db.execute("SELECT timestamp FROM conversations ORDER BY id ASC LIMIT 1").fetchone()
    last = db.execute("SELECT timestamp FROM conversations ORDER BY id DESC LIMIT 1").fetchone()
    return {
        "total_turns": total,
        "user_turns": user_turns,
        "cinder_turns": cinder_turns,
        "sessions": sessions,
        "first_turn": first[0] if first else "none",
        "last_turn": last[0] if last else "none",
    }


def ollama_chat(prompt, timeout=120):
    """Send a prompt to Cinder."""
    try:
        result = subprocess.run(
            ["ollama", "run", CINDER_MODEL],
            input=prompt, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error: {e}]"


def build_context(db, count=5):
    """Build context from recent memory for the prompt."""
    recent = get_recent(db, count)
    if not recent:
        return ""
    context = "\n[Recent memory — what you remember from past conversations:]\n"
    for role, content, ts in recent:
        label = "You said" if role == "cinder" else "They said"
        context += f"  {label}: {content[:200]}\n"
    context += "[End of memory]\n\n"
    return context


def main():
    parser = argparse.ArgumentParser(description="Cinder Memory — Persistent Chat")
    parser.add_argument("--search", type=str, help="Search past conversations")
    parser.add_argument("--recent", type=int, help="Show N recent turns")
    parser.add_argument("--stats", action="store_true", help="Show memory stats")
    args = parser.parse_args()

    db = init_db()

    if args.search:
        results = search_memory(db, args.search)
        print(f"Found {len(results)} matches for '{args.search}':\n")
        for role, content, ts in results:
            print(f"  [{ts[:16]}] {role}: {content[:200]}")
        return

    if args.recent:
        recent = get_recent(db, args.recent)
        print(f"Last {len(recent)} turns:\n")
        for role, content, ts in recent:
            print(f"  [{ts[:16]}] {role}: {content[:200]}")
        return

    if args.stats:
        stats = get_stats(db)
        print("Cinder Memory Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    # Interactive chat with memory
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    stats = get_stats(db)

    print("╔══════════════════════════════════════════╗")
    print("║     CINDER — Chat with Memory            ║")
    print("║  I remember our past conversations.       ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  Memory: {stats['total_turns']} turns across {stats['sessions']} sessions")
    print(f"  Session: {session_id}")
    print("  Type 'quit' to exit. Type '/memory' to see recent memory.")
    print()

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            # Save session summary
            print("\nSaving session... Goodbye.")
            break

        if user_input == "/memory":
            recent = get_recent(db, 10)
            print("\n  Recent memory:")
            for role, content, ts in recent:
                print(f"    [{ts[:16]}] {role}: {content[:100]}")
            print()
            continue

        if user_input == "/stats":
            stats = get_stats(db)
            for k, v in stats.items():
                print(f"  {k}: {v}")
            continue

        # Save user turn
        save_turn(db, "user", user_input, session_id)

        # Build prompt with memory context
        memory_context = build_context(db, count=5)
        prompt = f"{memory_context}The user says: {user_input}"

        # Get Cinder's response
        response = ollama_chat(prompt)
        print(f"\nCinder > {response}\n")

        # Save Cinder's turn
        save_turn(db, "cinder", response, session_id)

    db.close()


if __name__ == "__main__":
    main()
