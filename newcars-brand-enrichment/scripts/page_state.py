#!/usr/bin/env python3
"""Pull the embedded page data out of a saved HTML page so specs, trims, prices and copy can be read as JSON.

Many dealer sites ship their content inside the HTML instead of visible text:
  - AEM / Apollo sites (e.g. mitsubishi-motors.com.kw): window.__APOLLO_STATE__ (+ __PRELOADED_STATE__)
  - Next.js: <script id="__NEXT_DATA__">   - Nuxt: window.__NUXT__   - JSON-LD: <script type="application/ld+json">
For Apollo caches, references ({"type":"id","id":...}) are resolved into nested objects.

Usage:
  page_state.py page.html                 -> prints which blobs exist and their top-level keys
  page_state.py page.html --dump out.json -> writes all blobs (Apollo roots resolved) to out.json
  page_state.py page.html --grep "Base Line" -> prints JSON paths whose string values contain the text
"""
import argparse, json, re, sys

dec = json.JSONDecoder()


def blobs(html):
    out = {}
    for m in re.finditer(r"window\.(__[A-Z_]+__)\s*=\s*", html):
        try:
            out[m.group(1)], _ = dec.raw_decode(html, m.end())
        except ValueError:
            pass
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        out["__NEXT_DATA__"] = json.loads(m.group(1))
    ld = [json.loads(x) for x in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S)
          if x.strip().startswith(("{", "["))]
    if ld:
        out["JSON_LD"] = ld
    return out


def resolve(ap, v, depth=0, seen=()):
    if depth > 14:
        return "..."
    if isinstance(v, dict):
        if v.get("type") == "id" and "id" in v:
            return "<cycle>" if v["id"] in seen else resolve(ap, ap.get(v["id"], {}), depth + 1, seen + (v["id"],))
        if v.get("type") == "json" and "json" in v:
            return v["json"]
        return {k: resolve(ap, x, depth + 1, seen) for k, x in v.items() if k != "__typename"}
    if isinstance(v, list):
        return [resolve(ap, x, depth + 1, seen) for x in v]
    return v


def walk(v, path=""):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from walk(x, f"{path}.{k}")
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from walk(x, f"{path}[{i}]")
    else:
        yield path, v


ap_ = argparse.ArgumentParser()
ap_.add_argument("html")
ap_.add_argument("--dump")
ap_.add_argument("--grep")
a = ap_.parse_args()
html = open(a.html, encoding="utf-8", errors="replace").read()
B = blobs(html)
if "__APOLLO_STATE__" in B:
    ap = B["__APOLLO_STATE__"]
    roots = [k for k in ap if not k.startswith("$") and "." not in k and k != "ROOT_QUERY"]
    B["APOLLO_ROOTS"] = {k: resolve(ap, ap[k]) for k in roots}
if not B:
    sys.exit("no embedded state found - fall back to visible text or a real browser (Playwright) for JS-rendered pages")
if a.dump:
    json.dump(B, open(a.dump, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {a.dump}")
if a.grep:
    for name in ("APOLLO_ROOTS", "__NEXT_DATA__", "__NUXT__", "JSON_LD"):
        if name in B:
            for p, v in walk(B[name]):
                if isinstance(v, str) and a.grep.lower() in v.lower():
                    print(f"{name}{p} = {v[:200]}")
if not a.dump and not a.grep:
    for k, v in B.items():
        detail = list(v)[:12] if isinstance(v, dict) else (len(v) if hasattr(v, "__len__") else v)
        print(k, type(v).__name__, detail)
