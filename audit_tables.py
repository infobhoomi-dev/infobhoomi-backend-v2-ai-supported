"""
DB Field Audit Script — InfoBhoomi
====================================
Connects to the local PostgreSQL DB and for every table:
  1. Counts total rows and null % per column
  2. Checks if the column appears in models.py, serializers.py, views.py
  3. Assigns a "cleanup priority" score
  4. Outputs a JSON report + a summary CSV

Run from the backend root:
    venv\\Scripts\\python.exe audit_tables.py

Output files:
    audit_report.json   — full detail per table
    audit_summary.csv   — one row per column, sorted by priority
"""

import json
import csv
import re
import os
import sys

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    sys.exit("psycopg2 not found. Run:  venv\\Scripts\\pip install psycopg2-binary")

# ── DB config (mirrors .env) ───────────────────────────────────────────────
DB = dict(
    host="127.0.0.1",
    port=5432,
    dbname="infobhoomi_dev",
    user="postgres",
    password="POST@info#box2024",
)

# ── Source directories to cross-reference ─────────────────────────────────
BASE = os.path.dirname(__file__)
SOURCE_DIRS = {
    "models":      os.path.join(BASE, "user", "models"),
    "serializers": os.path.join(BASE, "user", "serializers"),
    "views":       os.path.join(BASE, "user", "views"),
}

# Tables to skip (Django internals, PostGIS metadata, auth framework)
SKIP_TABLES = {
    "django_migrations", "django_content_type", "django_admin_log",
    "django_session", "auth_permission", "auth_group",
    "auth_group_permissions", "auth_user_groups", "auth_user_user_permissions",
    "spatial_ref_sys", "geometry_columns", "geography_columns",
    "raster_columns", "raster_overviews",
}

# ── Load source files once ────────────────────────────────────────────────
def load_sources():
    sources = {}
    for key, dirpath in SOURCE_DIRS.items():
        parts = []
        if os.path.isdir(dirpath):
            for fname in sorted(os.listdir(dirpath)):
                if fname.endswith(".py") and not fname.startswith("backup"):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            parts.append(f.read())
                    except Exception as e:
                        print(f"  WARNING: could not read {fpath}: {e}")
        else:
            # Fallback: try single file (legacy layout)
            fpath = dirpath + ".py"
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    parts.append(f.read())
            else:
                print(f"  WARNING: {dirpath} not found — skipping cross-check for {key}")
        sources[key] = "\n".join(parts)
    return sources

def col_in_source(col_name, source_text):
    """True if the column name appears as a word in the source text."""
    pattern = r'\b' + re.escape(col_name) + r'\b'
    return bool(re.search(pattern, source_text, re.IGNORECASE))

# ── Priority scoring ──────────────────────────────────────────────────────
def priority_score(null_pct, in_model, in_serializer, in_views, row_count):
    """
    Returns (score, label):
      HIGH   — very likely safe to remove
      MEDIUM — worth investigating
      LOW    — probably needed, verify first
    """
    score = 0
    if null_pct == 100:
        score += 40   # always null = never populated
    elif null_pct >= 95:
        score += 25
    elif null_pct >= 80:
        score += 10

    if not in_model:
        score += 30   # not even declared in Django model
    if not in_serializer:
        score += 15   # not exposed in any API response
    if not in_views:
        score += 10   # not read/written in any view

    if row_count == 0:
        score -= 10   # empty table — hard to judge null %

    if score >= 50:
        label = "HIGH"
    elif score >= 25:
        label = "MEDIUM"
    else:
        label = "LOW"

    return score, label

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print("Connecting to database…")
    try:
        conn = psycopg2.connect(**DB)
    except Exception as e:
        sys.exit(f"DB connection failed: {e}")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("Loading source files…")
    sources = load_sources()

    # Get all user tables
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    all_tables = [r["table_name"] for r in cur.fetchall()]
    tables = [t for t in all_tables if t not in SKIP_TABLES]
    print(f"Found {len(tables)} tables to audit (skipped {len(all_tables) - len(tables)} system tables)\n")

    report = {}
    csv_rows = []

    for i, table in enumerate(tables, 1):
        print(f"  [{i:>3}/{len(tables)}] {table}", end="", flush=True)

        # Row count
        try:
            cur.execute(f'SELECT COUNT(*) as cnt FROM "{table}"')
            row_count = cur.fetchone()["cnt"]
        except Exception:
            conn.rollback()
            print(" — SKIP (query error)")
            continue

        # Column info
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        columns = cur.fetchall()

        table_data = {
            "row_count": row_count,
            "column_count": len(columns),
            "columns": [],
        }

        high_count = 0
        for col in columns:
            col_name = col["column_name"]

            # Null percentage
            if row_count > 0:
                try:
                    cur.execute(
                        f'SELECT COUNT(*) as cnt FROM "{table}" WHERE "{col_name}" IS NULL'
                    )
                    null_count = cur.fetchone()["cnt"]
                    null_pct = round(null_count / row_count * 100, 1)
                except Exception:
                    conn.rollback()
                    null_pct = -1  # unknown
                    null_count = -1
            else:
                null_pct = 100.0
                null_count = 0

            # Code cross-reference
            in_model      = col_in_source(col_name, sources["models"])
            in_serializer = col_in_source(col_name, sources["serializers"])
            in_views      = col_in_source(col_name, sources["views"])

            score, label = priority_score(
                null_pct, in_model, in_serializer, in_views, row_count
            )

            if label == "HIGH":
                high_count += 1

            col_data = {
                "column":        col_name,
                "data_type":     col["data_type"],
                "nullable":      col["is_nullable"] == "YES",
                "has_default":   col["column_default"] is not None,
                "null_pct":      null_pct,
                "null_count":    null_count,
                "in_model":      in_model,
                "in_serializer": in_serializer,
                "in_views":      in_views,
                "priority":      label,
                "score":         score,
            }
            table_data["columns"].append(col_data)

            csv_rows.append({
                "table":         table,
                "column":        col_name,
                "data_type":     col["data_type"],
                "nullable":      col["is_nullable"],
                "row_count":     row_count,
                "null_pct":      null_pct,
                "in_model":      in_model,
                "in_serializer": in_serializer,
                "in_views":      in_views,
                "priority":      label,
                "score":         score,
            })

        table_data["high_priority_columns"] = high_count
        report[table] = table_data

        flag = f"  *** {high_count} HIGH-priority columns" if high_count else ""
        print(f"  ({row_count} rows, {len(columns)} cols){flag}")

    conn.close()

    # ── Write JSON report ─────────────────────────────────────────────────
    json_path = os.path.join(BASE, "audit_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report  -> {json_path}")

    # ── Write CSV summary (sorted by score desc) ──────────────────────────
    csv_path = os.path.join(BASE, "audit_summary.csv")
    csv_rows.sort(key=lambda r: -r["score"])
    fieldnames = [
        "priority", "score", "table", "column", "data_type",
        "nullable", "null_pct", "row_count",
        "in_model", "in_serializer", "in_views",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"CSV summary  -> {csv_path}")

    # ── Print top 20 candidates ───────────────────────────────────────────
    high_rows = [r for r in csv_rows if r["priority"] == "HIGH"]
    med_rows  = [r for r in csv_rows if r["priority"] == "MEDIUM"]
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(high_rows)} HIGH  |  {len(med_rows)} MEDIUM  priority columns found")
    print(f"{'='*60}")
    print(f"\nTop 20 cleanup candidates:\n")
    print(f"{'Table':<35} {'Column':<30} {'Null%':>6}  {'Priority'}")
    print("-" * 85)
    for r in csv_rows[:20]:
        print(f"{r['table']:<35} {r['column']:<30} {str(r['null_pct']):>6}%  {r['priority']}")

    print(f"\nOpen audit_summary.csv to review all columns sorted by cleanup priority.")
    print("Then paste one table block from audit_report.json into Claude to review.\n")

if __name__ == "__main__":
    main()
