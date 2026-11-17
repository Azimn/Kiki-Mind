"""Read-only Windows laptop readiness probe for Kiki integration. Python 3.10+."""
import argparse
import json
import sqlite3
import urllib.request
from pathlib import Path

ENDPOINTS = {
    "jan": "http://127.0.0.1:1337/v1/models",
    "ollama": "http://127.0.0.1:11434/api/tags",
}

def probe(url, timeout=2):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=timeout) as response:
            data = json.load(response)
            if not isinstance(data, dict):
                return {"reachable": True, "valid_json_object": False}
            models = data.get("data", data.get("models", []))
            return {"reachable": True, "valid_json_object": True,
                    "model_count": len(models) if isinstance(models, list) else None,
                    "model_ids": [str(m.get("id", m.get("name", "unknown"))) for m in models if isinstance(m, dict)] if isinstance(models, list) else []}
    except (OSError, ValueError, TimeoutError) as exc:
        return {"reachable": False, "error_type": type(exc).__name__}

def inspect_sqlite(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"exists": False}
    try:
        conn = sqlite3.connect(p.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=2)
        try:
            check = conn.execute("PRAGMA quick_check").fetchone()[0]
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            return {"exists": True, "quick_check": check, "table_count": len(tables),
                    "canonical_identity_confirmed": False}
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"exists": True, "sqlite_error_type": type(exc).__name__, "canonical_identity_confirmed": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", action="append", default=[], help="Explicit SQLite path; repeatable")
    parser.add_argument("--output", default="kiki-readiness.json")
    args = parser.parse_args()
    result = {"schema": 1, "scope": "read-only local inventory",
              "deployment_verified": False, "identity_verified": False,
              "services": {name: probe(url) for name, url in ENDPOINTS.items()},
              "databases": [inspect_sqlite(path) for path in args.sqlite],
              "next_step": "Verify actual Jan Kiki configuration and Control Room SQLite authority before integration or writes."}
    out = Path(args.output)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Readiness report written:", out)
    print("No installation, model inference, or database writes performed.")

if __name__ == "__main__":
    main()
