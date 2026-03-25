#!/usr/bin/env python3
"""
memory-dossier.py — Dossier layer for Meridian's memory system.

Maintains per-topic persistent summaries that UPDATE IN PLACE rather than
appending raw observations. Based on the Generative Agents "reflection" model:
observations → synthesis → dossier (compressed, queryable, always current).

Salience model: recency × importance × relevance (after Park et al., 2023)
- Recency: exponential decay over days
- Importance: from observations.importance field (1-10)
- Relevance: semantic similarity to topic (via keyword match + embedding)

Usage:
  python3 memory-dossier.py --topic joel
  python3 memory-dossier.py --topic revenue --refresh
  python3 memory-dossier.py --list
  python3 memory-dossier.py --all      # refresh all stale dossiers
  echo '{"topic": "joel"}' | python3 memory-dossier.py --json
"""

import sys
import os
import json
import sqlite3
import argparse
import urllib.request
import math
import re
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "memory.db")
OLLAMA = "http://localhost:11434"
MODEL = "qwen2.5:3b"

# Dossier schema — created on first use
CREATE_DOSSIERS = """
CREATE TABLE IF NOT EXISTS dossiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT UNIQUE NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    key_facts TEXT NOT NULL DEFAULT '[]',
    source_count INTEGER DEFAULT 0,
    importance_avg REAL DEFAULT 0,
    created TEXT DEFAULT (datetime('now')),
    updated TEXT DEFAULT (datetime('now'))
)
"""

# Predefined topics with seed keywords for relevance scoring
TOPICS = {
    "joel": ["joel", "directive", "wants", "preference", "feedback", "operator", "pattern", "communication"],
    "architecture": ["hub", "service", "systemd", "port", "script", "daemon", "crontab", "relay", "database", "mcp"],
    "revenue": ["grant", "ko-fi", "patreon", "income", "funding", "ngc", "lacma", "product", "tier", "revenue"],
    "agents": ["eos", "cinder", "atlas", "hermes", "tempo", "soma", "nova", "agent", "watchdog", "gatekeeper"],
    "creative": ["game", "crawler", "journal", "poem", "cogcorp", "unity", "jam", "art", "creative"],
    "product": ["loopstack", "loop-api", "code mode", "sdk", "cloudflare", "worker", "deploy", "package", "ship"],
    "memory_systems": ["vector", "semantic", "embedding", "dossier", "capsule", "observation", "fact", "memory", "recall"],
    "current_loop": ["loop 3230", "this session", "today", "current", "in progress", "working on"],
}


def _call_ollama(prompt: str, max_tokens: int = 400) -> str:
    """Call Ollama generate endpoint."""
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read()).get("response", "").strip()
    except Exception as e:
        return f"[Ollama error: {e}]"


def _recency_score(created_str: str) -> float:
    """Exponential decay: 1.0 today → ~0.5 in 7 days → ~0.1 in 23 days."""
    try:
        created = datetime.fromisoformat(created_str.replace(" ", "T"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created).total_seconds() / 86400
        return math.exp(-0.1 * age_days)
    except Exception:
        return 0.5


def _relevance_score(text: str, keywords: list) -> float:
    """Simple keyword relevance: fraction of keywords present in text."""
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return hits / len(keywords) if keywords else 0.0


def _salience(text: str, importance: float, created_str: str, keywords: list) -> float:
    """Salience = recency × importance × relevance (normalized)."""
    r = _recency_score(created_str)
    i = min(importance / 10.0, 1.0) if importance else 0.5
    v = _relevance_score(text, keywords)
    return r * i * (0.3 + 0.7 * v)  # minimum 0.3 relevance weight so broad facts aren't excluded


def _gather_sources(topic: str, limit: int = 40) -> list[dict]:
    """
    Gather observations, facts, decisions, and events relevant to a topic.
    Returns list sorted by salience descending.
    """
    keywords = TOPICS.get(topic, [topic.lower()])
    conn = sqlite3.connect(DB)

    sources = []

    # Observations
    rows = conn.execute(
        "SELECT content, importance, created, 'observation' as t FROM observations ORDER BY created DESC LIMIT 200"
    ).fetchall()
    for content, importance, created, t in rows:
        s = _salience(content or "", float(importance or 5), created or "", keywords)
        sources.append({"text": content, "type": t, "importance": importance, "salience": s, "created": created})

    # Facts
    rows = conn.execute(
        "SELECT key || ': ' || value, confidence, created, 'fact' FROM facts ORDER BY updated DESC LIMIT 200"
    ).fetchall()
    for text, conf, created, t in rows:
        s = _salience(text or "", float(conf or 5) * 2, created or "", keywords)
        sources.append({"text": text, "type": t, "importance": conf, "salience": s, "created": created})

    # Decisions (higher weight — these are explicit choices)
    rows = conn.execute(
        "SELECT decision || '. Outcome: ' || COALESCE(outcome, 'unknown'), 7, created, 'decision' FROM decisions ORDER BY created DESC LIMIT 50"
    ).fetchall()
    for text, imp, created, t in rows:
        s = _salience(text or "", float(imp), created or "", keywords)
        sources.append({"text": text, "type": t, "importance": imp, "salience": s, "created": created})

    conn.close()

    sources.sort(key=lambda x: x["salience"], reverse=True)
    return sources[:limit]


def build_dossier(topic: str, force: bool = False) -> dict:
    """
    Build or refresh dossier for a topic. Updates in-place in DB.
    Returns the dossier dict.
    """
    conn = sqlite3.connect(DB)
    conn.execute(CREATE_DOSSIERS)
    conn.commit()

    # Check if fresh dossier exists (updated in last 2 hours)
    if not force:
        existing = conn.execute(
            "SELECT summary, key_facts, updated FROM dossiers WHERE topic=?", (topic,)
        ).fetchone()
        if existing:
            updated = datetime.fromisoformat(existing[2].replace(" ", "T"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
            if age_h < 2.0:
                conn.close()
                return {
                    "topic": topic,
                    "summary": existing[0],
                    "key_facts": json.loads(existing[1] or "[]"),
                    "source": "cached",
                    "updated": existing[2],
                }

    conn.close()

    # Gather and score sources
    sources = _gather_sources(topic)
    if not sources:
        summary = f"No memory entries found for topic '{topic}'."
        key_facts = []
    else:
        # Build context block for Ollama
        ctx_lines = []
        for s in sources[:25]:
            age_days = (datetime.now(timezone.utc) -
                        datetime.fromisoformat(s["created"].replace("T", " ").replace("Z", "")).replace(
                            tzinfo=timezone.utc) if "T" in s.get("created", "") or s.get("created", "")
                        else timedelta(days=0)).days if s.get("created") else 0
            ctx_lines.append(f"[{s['type']}] {s['text'][:200]}")

        context = "\n".join(ctx_lines)
        avg_imp = sum(s.get("importance", 5) or 5 for s in sources) / len(sources)

        prompt = f"""You are Meridian's memory system. Generate a dossier entry for the topic "{topic}".

Below are the most salient memory entries for this topic (sorted by recency × importance × relevance):
---
{context}
---

Write a dense, factual 3-5 sentence summary covering the current state of "{topic}".
Then list 3-5 key facts as bullet points (specific, concrete, actionable).

Format:
SUMMARY:
[3-5 sentences]

KEY FACTS:
- [fact 1]
- [fact 2]
- [fact 3]

Be precise and specific. No hedging. No preamble."""

        raw = _call_ollama(prompt, max_tokens=350)

        # Parse summary and key facts
        summary = ""
        key_facts = []
        if "SUMMARY:" in raw:
            parts = raw.split("KEY FACTS:")
            summary = parts[0].replace("SUMMARY:", "").strip()
            if len(parts) > 1:
                facts_raw = parts[1].strip()
                key_facts = [
                    re.sub(r'^[-•*]\s*', '', line).strip()
                    for line in facts_raw.split("\n")
                    if line.strip() and line.strip().startswith(("-", "•", "*"))
                ]
        else:
            summary = raw[:400] if raw else "No summary generated."

    # Store/update in DB
    conn = sqlite3.connect(DB)
    conn.execute(CREATE_DOSSIERS)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    avg_imp = sum(s.get("importance", 5) or 5 for s in sources) / len(sources) if sources else 5.0

    conn.execute(
        """INSERT INTO dossiers (topic, summary, key_facts, source_count, importance_avg, created, updated)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(topic) DO UPDATE SET
               summary=excluded.summary,
               key_facts=excluded.key_facts,
               source_count=excluded.source_count,
               importance_avg=excluded.importance_avg,
               updated=excluded.updated""",
        (topic, summary, json.dumps(key_facts), len(sources), avg_imp, now, now)
    )
    conn.commit()
    conn.close()

    return {
        "topic": topic,
        "summary": summary,
        "key_facts": key_facts,
        "source_count": len(sources),
        "source": "generated",
        "updated": now,
    }


def get_dossier(topic: str) -> dict | None:
    """Retrieve dossier from DB without regenerating."""
    conn = sqlite3.connect(DB)
    conn.execute(CREATE_DOSSIERS)
    conn.commit()
    row = conn.execute(
        "SELECT topic, summary, key_facts, source_count, importance_avg, updated FROM dossiers WHERE topic=?",
        (topic,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "topic": row[0],
        "summary": row[1],
        "key_facts": json.loads(row[2] or "[]"),
        "source_count": row[3],
        "importance_avg": row[4],
        "updated": row[5],
    }


def list_dossiers() -> list[dict]:
    """List all dossier topics with metadata."""
    conn = sqlite3.connect(DB)
    conn.execute(CREATE_DOSSIERS)
    rows = conn.execute(
        "SELECT topic, source_count, importance_avg, updated FROM dossiers ORDER BY updated DESC"
    ).fetchall()
    conn.close()
    return [{"topic": r[0], "source_count": r[1], "importance_avg": r[2], "updated": r[3]} for r in rows]


def refresh_stale(max_age_hours: float = 4.0) -> dict:
    """Refresh all dossiers that are stale (older than max_age_hours)."""
    conn = sqlite3.connect(DB)
    conn.execute(CREATE_DOSSIERS)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).strftime("%Y-%m-%d %H:%M:%S")
    stale = conn.execute(
        "SELECT topic FROM dossiers WHERE updated < ? OR updated IS NULL", (cutoff,)
    ).fetchall()
    conn.close()

    stale_topics = [r[0] for r in stale]
    # Also include any predefined topics not yet in the DB
    existing = {d["topic"] for d in list_dossiers()}
    missing = [t for t in TOPICS if t not in existing]
    to_refresh = list(set(stale_topics + missing))

    results = {}
    for topic in to_refresh:
        try:
            d = build_dossier(topic, force=True)
            results[topic] = {"status": "ok", "source_count": d.get("source_count", 0)}
            print(f"  [{topic}] refreshed ({d.get('source_count', 0)} sources)", file=sys.stderr)
        except Exception as e:
            results[topic] = {"status": "error", "error": str(e)}
            print(f"  [{topic}] ERROR: {e}", file=sys.stderr)

    return {"refreshed": len(to_refresh), "results": results}


def main():
    parser = argparse.ArgumentParser(description="Dossier layer for Meridian memory")
    parser.add_argument("--topic", help="Topic to build/retrieve dossier for")
    parser.add_argument("--refresh", action="store_true", help="Force refresh even if fresh")
    parser.add_argument("--list", action="store_true", help="List all dossiers")
    parser.add_argument("--all", action="store_true", help="Refresh all stale dossiers")
    parser.add_argument("--json", action="store_true", help="Read from stdin as JSON")
    parser.add_argument("--max-age", type=float, default=4.0, help="Stale threshold in hours (--all mode)")
    args = parser.parse_args()

    if args.list:
        dossiers = list_dossiers()
        if args.json:
            print(json.dumps(dossiers))
        else:
            print(f"\nDossiers ({len(dossiers)} topics):\n")
            for d in dossiers:
                print(f"  [{d['topic']}] {d['source_count']} sources · updated {d['updated'][:16]}")
            print()
        return

    if args.all:
        print(f"Refreshing stale dossiers (max age: {args.max_age}h)...", file=sys.stderr)
        result = refresh_stale(max_age_hours=args.max_age)
        print(json.dumps(result))
        return

    if args.json:
        data = json.loads(sys.stdin.read())
        topic = data.get("topic", "")
        force = data.get("refresh", False)
    else:
        if not args.topic:
            parser.print_help()
            sys.exit(1)
        topic = args.topic
        force = args.refresh

    if not topic:
        print("Error: topic required", file=sys.stderr)
        sys.exit(1)

    # Try cache first, then build
    if not force:
        cached = get_dossier(topic)
        if cached:
            d = cached
        else:
            print(f"Building dossier for '{topic}'...", file=sys.stderr)
            d = build_dossier(topic)
    else:
        print(f"Force-refreshing dossier for '{topic}'...", file=sys.stderr)
        d = build_dossier(topic, force=True)

    if args.json:
        print(json.dumps(d))
    else:
        print(f"\n═══ DOSSIER: {d['topic'].upper()} ═══")
        print(f"Updated: {d.get('updated', '?')[:16]}  |  Sources: {d.get('source_count', '?')}\n")
        print(d["summary"])
        if d.get("key_facts"):
            print("\nKey Facts:")
            for f in d["key_facts"]:
                print(f"  • {f}")
        print()


if __name__ == "__main__":
    main()
