#!/usr/bin/env python3
"""Look things up in the catalog API contract (swagger) — the "check the swagger first" rule, made runnable.

Finding the file, in order:
  1. $NEWCARS_SWAGGER                      (full path to swaggerv2.json)
  2. $NEWCARS_DOCS/swaggerv2.json          (directory holding the project docs)
  3. ./swaggerv2.json, ./docs/swaggerv2.json, ../docs/swaggerv2.json
  4. --swagger <path>
If none exists, this prints how to supply one and exits 3 — ask whoever owns the service for the spec rather
than guessing at endpoints.

Usage:
  api_contract.py paths trim            # endpoints whose path matches "trim"
  api_contract.py schema UpdateTrimInput # a request/response schema's fields
  api_contract.py body /v1/admin/import/trims post   # the request body schema for an operation
  api_contract.py writes                 # every write endpoint (post/put/patch/delete), grouped
"""
import argparse, json, os, sys

CANDIDATES = ["swaggerv2.json", os.path.join("docs", "swaggerv2.json"), os.path.join("..", "docs", "swaggerv2.json")]


def load(explicit=None):
    tries = []
    if explicit:
        tries.append(explicit)
    if os.environ.get("NEWCARS_SWAGGER"):
        tries.append(os.environ["NEWCARS_SWAGGER"])
    if os.environ.get("NEWCARS_DOCS"):
        tries.append(os.path.join(os.environ["NEWCARS_DOCS"], "swaggerv2.json"))
    tries += CANDIDATES
    for p in tries:
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return p, json.load(f)
    sys.exit("No swagger found. Point to it with:\n"
             "  export NEWCARS_SWAGGER=/path/to/swaggerv2.json     (or NEWCARS_DOCS=/path/to/docs)\n"
             "  api_contract.py --swagger /path/to/swaggerv2.json ...\n"
             "The spec is the catalog service's own API contract — get a copy from the team that owns it.")


def defs(d):
    return d.get("definitions") or d.get("components", {}).get("schemas", {})


def ref_name(s):
    if not isinstance(s, dict):
        return None
    if "$ref" in s:
        return s["$ref"].split("/")[-1]
    if s.get("type") == "array" and s.get("items"):
        return ref_name(s["items"])
    return None


def show_schema(d, name, depth=0):
    D = defs(d)
    if name not in D:
        print(f"{'  ' * depth}{name}: not in the spec")
        return
    s = D[name]
    print(f"{'  ' * depth}{name}  required={s.get('required')}")
    for k, v in (s.get("properties") or {}).items():
        r = ref_name(v)
        enum = f"  enum={v['enum']}" if v.get("enum") else ""
        print(f"{'  ' * depth}   {k}: {v.get('type', r or '?')}{enum}")


ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["paths", "schema", "body", "writes"])
ap.add_argument("args", nargs="*")
ap.add_argument("--swagger")
a = ap.parse_args()
path, doc = load(a.swagger)
print(f"# {path}\n")

if a.cmd == "paths":
    q = (a.args[0] if a.args else "").lower()
    for p, v in sorted(doc["paths"].items()):
        if q in p.lower():
            for m, op in v.items():
                if m in ("get", "post", "put", "patch", "delete"):
                    body = [x for x in op.get("parameters", []) if x.get("in") == "body"]
                    print(f"{m.upper():6} {p}  -> {[ref_name(b['schema']) for b in body]}  {op.get('description', '')[:90]}")
elif a.cmd == "schema":
    for n in a.args:
        D = defs(doc)
        hits = [k for k in D if n.lower() in k.lower()]
        for h in hits[:5]:
            show_schema(doc, h)
            print()
elif a.cmd == "body":
    p, m = a.args[0], (a.args[1] if len(a.args) > 1 else "post")
    op = doc["paths"].get(p, {}).get(m)
    if not op:
        sys.exit(f"{m.upper()} {p} is not in the spec")
    for b in [x for x in op.get("parameters", []) if x.get("in") == "body"]:
        show_schema(doc, ref_name(b["schema"]))
elif a.cmd == "writes":
    for p, v in sorted(doc["paths"].items()):
        for m, op in v.items():
            if m in ("post", "put", "patch", "delete"):
                print(f"{m.upper():6} {p}  {op.get('description', '')[:80]}")
