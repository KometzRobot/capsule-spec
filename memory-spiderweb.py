#!/usr/bin/env python3
"""
memory-spiderweb.py — Weighted associative graph over memory.db

Concept (Joel Loop 3228):
  Facts + observations live in flat tables. The spiderweb adds dynamic
  connections between nodes: edges strengthen when nodes are accessed
  together (Hebbian co-activation), and decay when unused. Paths that
  get traversed become highways; dead paths prune themselves.

Architecture:
  - `connections` table: (node_a, node_b, weight, activated_count, last_activated)
  - Context window: set of nodes activated in same session
  - commit_context(): creates/strengthens edges between all co-activated nodes
  - decay(): weight *= rate; removes edges below threshold
  - spread(): spreading activation query — find strongly-connected neighbors

Usage:
  web = MemorySpiderweb()
  web.activate("facts", 42)
  web.activate("observations", 17)
  web.commit_context()  # links them, strengthens if already linked

  # Find what's strongly associated with fact 42
  neighbors = web.spread("facts", 42, threshold=0.15, depth=2)

  # Run nightly
  web.decay(rate=0.95, prune_below=0.01)
  pruned = web.stats()
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
MEMDB = os.path.join(BASE, "memory.db")


class MemorySpiderweb:
    def __init__(self, db_path=None):
        self.db = db_path or MEMDB
        self._context = []  # nodes activated this session: [(table, id), ...]
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_a_table TEXT NOT NULL,
                    node_a_id INTEGER NOT NULL,
                    node_b_table TEXT NOT NULL,
                    node_b_id INTEGER NOT NULL,
                    weight REAL DEFAULT 1.0,
                    activated_count INTEGER DEFAULT 1,
                    last_activated TEXT,
                    created TEXT,
                    UNIQUE(node_a_table, node_a_id, node_b_table, node_b_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conn_a
                ON connections(node_a_table, node_a_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conn_b
                ON connections(node_b_table, node_b_id)
            """)
            conn.commit()

    # ── ACTIVATION ────────────────────────────────────────────────

    def activate(self, table, node_id):
        """Mark a node as active in the current context."""
        key = (str(table), int(node_id))
        if key not in self._context:
            self._context.append(key)

    def commit_context(self, activation_strength=1.0):
        """
        Create or strengthen edges between all co-activated nodes.
        Call this at end of a retrieval session.
        Returns number of connections updated.
        """
        if len(self._context) < 2:
            self._context = []
            return 0

        now = datetime.now().isoformat()
        updated = 0

        with sqlite3.connect(self.db) as conn:
            # Create or strengthen edge for every pair
            for i, (ta, ia) in enumerate(self._context):
                for (tb, ib) in self._context[i+1:]:
                    # Canonical order: smaller table+id first
                    if (ta, ia) > (tb, ib):
                        ta, ia, tb, ib = tb, ib, ta, ia

                    existing = conn.execute("""
                        SELECT id, weight, activated_count
                        FROM connections
                        WHERE node_a_table=? AND node_a_id=?
                          AND node_b_table=? AND node_b_id=?
                    """, (ta, ia, tb, ib)).fetchone()

                    if existing:
                        # Strengthen: weight grows by activation_strength,
                        # capped at 10.0 to prevent runaway growth
                        new_weight = min(existing[1] + activation_strength, 10.0)
                        conn.execute("""
                            UPDATE connections
                            SET weight=?, activated_count=activated_count+1,
                                last_activated=?
                            WHERE id=?
                        """, (new_weight, now, existing[0]))
                    else:
                        conn.execute("""
                            INSERT INTO connections
                            (node_a_table, node_a_id, node_b_table, node_b_id,
                             weight, activated_count, last_activated, created)
                            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                        """, (ta, ia, tb, ib, activation_strength, now, now))
                    updated += 1
            conn.commit()

        self._context = []
        return updated

    def clear_context(self):
        """Discard current context without committing."""
        self._context = []

    # ── SPREADING ACTIVATION ──────────────────────────────────────

    def spread(self, table, node_id, threshold=0.1, depth=2, max_results=20):
        """
        Spreading activation query: find nodes connected to (table, node_id)
        with weight >= threshold. Follows connections up to `depth` hops.

        Returns list of dicts:
          [{"table": str, "id": int, "weight": float, "hops": int, "path": list}, ...]
        sorted by weight descending.
        """
        visited = set()
        results = []
        queue = [(str(table), int(node_id), 0, 1.0, [])]  # (table, id, hops, path_weight, path)

        with sqlite3.connect(self.db) as conn:
            while queue:
                cur_table, cur_id, hops, path_weight, path = queue.pop(0)
                key = (cur_table, cur_id)

                if key in visited:
                    continue
                visited.add(key)

                if hops > 0:  # Don't include the origin node
                    results.append({
                        "table": cur_table,
                        "id": cur_id,
                        "weight": path_weight,
                        "hops": hops,
                        "path": path
                    })

                if hops >= depth:
                    continue

                # Find all connections involving this node
                neighbors = conn.execute("""
                    SELECT node_b_table, node_b_id, weight
                    FROM connections
                    WHERE node_a_table=? AND node_a_id=? AND weight >= ?
                    UNION ALL
                    SELECT node_a_table, node_a_id, weight
                    FROM connections
                    WHERE node_b_table=? AND node_b_id=? AND weight >= ?
                    ORDER BY weight DESC
                """, (cur_table, cur_id, threshold,
                      cur_table, cur_id, threshold)).fetchall()

                for nb_table, nb_id, edge_weight in neighbors:
                    nb_key = (nb_table, nb_id)
                    if nb_key not in visited:
                        combined_weight = path_weight * edge_weight
                        queue.append((nb_table, nb_id, hops + 1,
                                     combined_weight,
                                     path + [(cur_table, cur_id)]))

        # Sort by weight desc, return top results
        results.sort(key=lambda x: -x["weight"])
        return results[:max_results]

    def enrich_results(self, spread_results):
        """
        Annotate spreading activation results with actual content from memory.db.
        Returns results with a 'content' field added.
        """
        enriched = []
        with sqlite3.connect(self.db) as conn:
            for r in spread_results:
                table = r["table"]
                row_id = r["id"]
                content = None
                try:
                    if table == "facts":
                        row = conn.execute(
                            "SELECT key, value FROM facts WHERE id=?", (row_id,)
                        ).fetchone()
                        if row:
                            content = f"{row[0]}: {row[1][:80]}"
                    elif table == "observations":
                        row = conn.execute(
                            "SELECT content, category FROM observations WHERE id=?", (row_id,)
                        ).fetchone()
                        if row:
                            content = f"[{row[1]}] {row[0][:80]}"
                    elif table == "events":
                        row = conn.execute(
                            "SELECT description FROM events WHERE id=?", (row_id,)
                        ).fetchone()
                        if row:
                            content = row[0][:80]
                    elif table == "decisions":
                        row = conn.execute(
                            "SELECT decision FROM decisions WHERE id=?", (row_id,)
                        ).fetchone()
                        if row:
                            content = row[0][:80]
                    elif table == "creative":
                        row = conn.execute(
                            "SELECT title, type FROM creative WHERE id=?", (row_id,)
                        ).fetchone()
                        if row:
                            content = f"[{row[1]}] {row[0]}"
                except Exception:
                    pass
                enriched.append({**r, "content": content or f"({table}#{row_id})"})
        return enriched

    # ── DECAY ─────────────────────────────────────────────────────

    def decay(self, rate=0.95, prune_below=0.01):
        """
        Decay all connection weights by `rate`. Prune edges below `prune_below`.
        Call nightly.

        Returns: {"decayed": int, "pruned": int, "remaining": int}
        """
        with sqlite3.connect(self.db) as conn:
            # Decay
            conn.execute("UPDATE connections SET weight = weight * ?", (rate,))
            # Prune
            pruned = conn.execute(
                "DELETE FROM connections WHERE weight < ?", (prune_below,)
            ).rowcount
            conn.commit()
            remaining = conn.execute(
                "SELECT COUNT(*) FROM connections"
            ).fetchone()[0]
            decayed = conn.execute(
                "SELECT COUNT(*) FROM connections"
            ).fetchone()[0]

        return {"rate": rate, "pruned": pruned, "remaining": remaining}

    # ── STATS ─────────────────────────────────────────────────────

    def stats(self):
        """Return summary statistics about the connection graph."""
        with sqlite3.connect(self.db) as conn:
            total = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
            avg_weight = conn.execute(
                "SELECT AVG(weight) FROM connections"
            ).fetchone()[0] or 0
            max_weight = conn.execute(
                "SELECT MAX(weight) FROM connections"
            ).fetchone()[0] or 0
            top_nodes = conn.execute("""
                SELECT node_a_table, node_a_id, SUM(weight) as total_w,
                       COUNT(*) as degree
                FROM connections
                GROUP BY node_a_table, node_a_id
                ORDER BY total_w DESC
                LIMIT 5
            """).fetchall()
            recent = conn.execute("""
                SELECT node_a_table, node_a_id, node_b_table, node_b_id,
                       weight, last_activated
                FROM connections
                ORDER BY last_activated DESC
                LIMIT 5
            """).fetchall()
        return {
            "total_connections": total,
            "avg_weight": round(avg_weight, 3),
            "max_weight": round(max_weight, 3),
            "top_nodes": [
                {"table": r[0], "id": r[1],
                 "total_weight": round(r[2], 3), "degree": r[3]}
                for r in top_nodes
            ],
            "recent_activations": [
                {"a": f"{r[0]}#{r[1]}", "b": f"{r[2]}#{r[3]}",
                 "weight": round(r[4], 3), "when": r[5]}
                for r in recent
            ]
        }

    def graph_summary(self, min_weight=0.5):
        """Return all significant edges as an adjacency list (for visualization)."""
        with sqlite3.connect(self.db) as conn:
            edges = conn.execute("""
                SELECT node_a_table, node_a_id, node_b_table, node_b_id,
                       weight, activated_count
                FROM connections
                WHERE weight >= ?
                ORDER BY weight DESC
            """, (min_weight,)).fetchall()
        return [
            {
                "a": f"{r[0]}#{r[1]}",
                "b": f"{r[2]}#{r[3]}",
                "weight": round(r[4], 3),
                "count": r[5]
            }
            for r in edges
        ]


# ── CLI ───────────────────────────────────────────────────────────

def _run_tests():
    """Self-test the spiderweb module. Returns True if all pass."""
    import tempfile, os
    print("Running MemorySpiderweb tests...")
    errors = []

    # Use a temp DB so we don't pollute memory.db
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        tmp_db = f.name

    try:
        # Seed some facts into the temp DB
        with sqlite3.connect(tmp_db) as conn:
            conn.execute("""
                CREATE TABLE facts (
                    id INTEGER PRIMARY KEY, key TEXT, value TEXT,
                    tags TEXT, agent TEXT, confidence REAL,
                    note TEXT, created TEXT, updated TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE observations (
                    id INTEGER PRIMARY KEY, agent TEXT, content TEXT,
                    category TEXT, importance INTEGER, created TEXT
                )
            """)
            conn.executemany(
                "INSERT INTO facts (id,key,value) VALUES (?,?,?)",
                [(1,"capsule","state snapshot"),
                 (2,"relay","inter-agent messaging"),
                 (3,"Cinder","gatekeeper model"),
                 (4,"Joel","operator/director")]
            )
            conn.executemany(
                "INSERT INTO observations (id,agent,content,category) VALUES (?,?,?,?)",
                [(1,"Meridian","loop count increasing","system"),
                 (2,"Cinder","briefing written","loop")]
            )
            conn.commit()

        web = MemorySpiderweb(tmp_db)

        # Test 1: Schema created
        with sqlite3.connect(tmp_db) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        if "connections" not in tables:
            errors.append("FAIL test1: connections table not created")
        else:
            print("  PASS test1: connections table created")

        # Test 2: Activate + commit_context
        web.activate("facts", 1)
        web.activate("facts", 2)
        web.activate("observations", 1)
        n = web.commit_context()
        if n != 3:  # 3 pairs from 3 nodes: (1,2),(1,obs1),(2,obs1)
            errors.append(f"FAIL test2: expected 3 connections, got {n}")
        else:
            print(f"  PASS test2: {n} connections committed")

        # Test 3: Repeated activation strengthens weight
        web.activate("facts", 1)
        web.activate("facts", 2)
        web.commit_context(activation_strength=1.0)
        with sqlite3.connect(tmp_db) as conn:
            row = conn.execute("""
                SELECT weight, activated_count FROM connections
                WHERE (node_a_table='facts' AND node_a_id=1
                       AND node_b_table='facts' AND node_b_id=2)
                   OR (node_a_table='facts' AND node_a_id=2
                       AND node_b_table='facts' AND node_b_id=1)
            """).fetchone()
        if row and row[0] == 2.0 and row[1] == 2:
            print(f"  PASS test3: weight={row[0]}, count={row[1]}")
        else:
            errors.append(f"FAIL test3: expected weight=2.0 count=2, got {row}")

        # Test 4: Spreading activation
        neighbors = web.spread("facts", 1, threshold=0.5, depth=1)
        nb_tables_ids = [(n["table"], n["id"]) for n in neighbors]
        if ("facts", 2) in nb_tables_ids:
            print(f"  PASS test4: spreading activation found facts#2 from facts#1")
        else:
            errors.append(f"FAIL test4: spread didn't find facts#2. Got: {nb_tables_ids}")

        # Test 5: Decay
        result = web.decay(rate=0.5, prune_below=0.01)
        with sqlite3.connect(tmp_db) as conn:
            row = conn.execute("""
                SELECT weight FROM connections
                WHERE (node_a_table='facts' AND node_a_id=1
                       AND node_b_table='facts' AND node_b_id=2)
                   OR (node_a_table='facts' AND node_a_id=2
                       AND node_b_table='facts' AND node_b_id=1)
            """).fetchone()
        # After 2 activations (weight=2.0) then decay * 0.5 = 1.0
        if row and abs(row[0] - 1.0) < 0.001:
            print(f"  PASS test5: decay correct (weight={row[0]:.3f})")
        else:
            errors.append(f"FAIL test5: expected weight≈1.0 after decay, got {row}")

        # Test 6: Prune removes weak connections
        web2 = MemorySpiderweb(tmp_db)
        web2.activate("facts", 3)
        web2.activate("facts", 4)
        web2.commit_context(activation_strength=0.005)  # Below prune threshold after decay
        web2.decay(rate=1.0, prune_below=0.01)  # rate=1 = no change, just prune
        with sqlite3.connect(tmp_db) as conn:
            weak = conn.execute("""
                SELECT COUNT(*) FROM connections WHERE weight < 0.01
            """).fetchone()[0]
        if weak == 0:
            print(f"  PASS test6: weak connections pruned")
        else:
            errors.append(f"FAIL test6: {weak} connections below threshold not pruned")

        # Test 7: Stats
        stats = web.stats()
        if "total_connections" in stats and stats["total_connections"] > 0:
            print(f"  PASS test7: stats() works ({stats['total_connections']} connections)")
        else:
            errors.append(f"FAIL test7: stats() broken: {stats}")

        # Test 8: enrich_results
        neighbors = web.spread("facts", 1, threshold=0.1, depth=1)
        enriched = web.enrich_results(neighbors)
        if enriched and "content" in enriched[0]:
            print(f"  PASS test8: enrich_results() adds content fields")
        else:
            errors.append(f"FAIL test8: enrich_results() broken: {enriched}")

    finally:
        os.unlink(tmp_db)

    if errors:
        print(f"\n{len(errors)} FAILURE(S):")
        for e in errors:
            print(f"  {e}")
        return False
    else:
        print(f"\nAll 8 tests passed.")
        return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Memory Spiderweb — associative graph")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    parser.add_argument("--stats", action="store_true", help="Show graph stats")
    parser.add_argument("--decay", action="store_true", help="Run decay pass")
    parser.add_argument("--spread", nargs=2, metavar=("TABLE", "ID"),
                        help="Spreading activation query")
    parser.add_argument("--threshold", type=float, default=0.1,
                        help="Minimum weight threshold for spread (default: 0.1)")
    parser.add_argument("--graph", action="store_true", help="Print graph summary")
    args = parser.parse_args()

    if args.test:
        success = _run_tests()
        sys.exit(0 if success else 1)

    web = MemorySpiderweb()

    if args.stats:
        import json
        print(json.dumps(web.stats(), indent=2))

    elif args.decay:
        result = web.decay()
        print(f"Decay complete: pruned={result['pruned']}, remaining={result['remaining']}")

    elif args.spread:
        table, node_id = args.spread[0], int(args.spread[1])
        neighbors = web.spread(table, node_id, threshold=args.threshold, depth=2)
        enriched = web.enrich_results(neighbors)
        if not enriched:
            print(f"No connections found for {table}#{node_id} (threshold={args.threshold})")
        else:
            print(f"Neighbors of {table}#{node_id} (threshold={args.threshold}):")
            for n in enriched:
                print(f"  [{n['hops']} hop(s), w={n['weight']:.3f}] "
                      f"{n['table']}#{n['id']}: {n['content']}")

    elif args.graph:
        import json
        edges = web.graph_summary()
        print(f"Graph: {len(edges)} significant edges")
        for e in edges[:20]:
            print(f"  {e['a']} <-> {e['b']}  w={e['weight']} (x{e['count']})")

    else:
        parser.print_help()
