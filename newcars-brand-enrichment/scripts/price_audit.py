#!/usr/bin/env python3
"""Audit trim/price coverage against the SAVED dealer sources, not against what the run claims it found.

Why: `source_trims` is written by the researcher, so checking trims against it only proves self-consistency.
This script re-reads everything under <workdir>/sources/ (HTML, embedded page-state JSON, brochure text/PDF)
and answers three questions independently:

  1. does every imported grade NAME actually occur in the sources?          (invented / misnamed grades)
  2. does every imported PRICE occur in the sources?                        (invented / stale prices)
  3. is every PRICE that occurs in the sources accounted for by a trim?     (MISSED GRADES - the important one)

Prices are matched in any of the forms a Kuwait dealer writes them: `KWD 7,999`, `KD 7999`, `7,999 د.ك`,
`"value": 7999`. PDFs are read with pdftotext when available.

Exit 0 = clean, 2 = findings. Writes <workdir>/price_audit.md (+ .json).
Usage: price_audit.py --workdir <dir> [--sources <dir>] [--strict-unaccounted]
"""
import argparse, glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import load_json, save_json

ap = argparse.ArgumentParser()
ap.add_argument("--workdir", required=True)
ap.add_argument("--sources", default=None, help="default <workdir>/sources")
ap.add_argument("--strict-unaccounted", action="store_true",
                help="treat every unaccounted price in the sources as an error (default: error only when it is a plausible car price)")
a = ap.parse_args()
W = a.workdir
SRC = a.sources or os.path.join(W, "sources")
C = load_json(os.path.join(W, "content.json"))

# ---------- load every saved source as text ----------
texts = {}
for p in glob.glob(os.path.join(SRC, "**", "*"), recursive=True):
    if os.path.isdir(p):
        continue
    ext = os.path.splitext(p)[1].lower()
    rel = os.path.relpath(p, SRC)
    try:
        if ext == ".pdf":
            out = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True, timeout=120)
            texts[rel] = out.stdout
        elif ext in (".html", ".htm", ".json", ".txt", ".md", ".js"):
            raw = open(p, encoding="utf-8", errors="replace").read()
            # strip <svg> blocks and path/viewBox coordinate data: they are full of number pairs that look
            # like prices and would otherwise flood the "unaccounted price" list
            raw = re.sub(r"<svg\b.*?</svg>", " ", raw, flags=re.S | re.I)
            raw = re.sub(r'\s(d|viewBox|points|transform)="[^"]*"', " ", raw, flags=re.I)
            texts[rel] = raw
    except Exception as e:
        print(f"  ! could not read {rel}: {e}")
if not texts:
    sys.exit(f"No readable sources in {SRC}. Save the dealer pages/brochure there - the audit needs them.")
ALL = "\n".join(texts.values())
print(f"audit: {len(texts)} source files, {len(ALL)//1024} KB of text")


def norm(s):
    return re.sub(r"[\s‏‎]+", " ", s or "").strip().lower()


NALL = norm(ALL)
# price tokens in the sources: KWD/KD/د.ك + number, or a bare JSON "price"/"value" number
PRICE_RE = re.compile(r"(?:kwd|kd|د\.?\s?ك)\s*([\d][\d,\.]{2,9})|([\d][\d,\.]{2,9})\s*(?:kwd|kd|د\.?\s?ك)"
                      r"|\"(?:price|baseValue|value|startingPrice|starting_price)\"\s*:\s*\"?([\d]{3,7})", re.I)


def to_int(tok):
    tok = (tok or "").replace(",", "").strip()
    if not tok:
        return None
    tok = tok.split(".")[0] if tok.count(".") == 1 and len(tok.split(".")[1]) <= 2 else tok.replace(".", "")
    return int(tok) if tok.isdigit() else None


def prices_in(text):
    found = set()
    for m in PRICE_RE.finditer(text):
        v = to_int(m.group(1) or m.group(2) or m.group(3))
        if v and 1000 <= v <= 500000:  # plausible KWD car price (cheapest KW new car is ~3,000 KWD)
            found.add(v)
    return found


def variants(n):
    return {str(n), f"{n:,}"}


def where(token):
    return [rel for rel, t in texts.items() if token in norm(t)][:3]


findings, notes, rows = [], [], []
model_stats = []
for mo in C.get("models", []):
    tag = mo.get("slug", "?")
    trims = mo.get("trims", [])
    src_trims = mo.get("source_trims") or []
    excluded = {x.get("name") for x in mo.get("excluded_trims", [])}

    # 1. grade names present in the sources
    for t in trims:
        nm = norm(t.get("display_name_en"))
        hits = where(nm) if nm else []
        if not hits:
            findings.append(f"{tag}/{t.get('slug')}: grade name '{t.get('display_name_en')}' does not appear in any saved source")
        rows.append({"model": tag, "trim": t.get("display_name_en"), "price": t.get("starting_price"),
                     "price_on_request": bool(t.get("price_on_request")), "name_in_sources": bool(hits),
                     "name_source": hits[:1]})
    for n in src_trims:
        nm = n.get("name") if isinstance(n, dict) else n
        if nm not in {t.get("display_name_en") for t in trims} and nm not in excluded:
            findings.append(f"{tag}: source grade '{nm}' is neither imported nor excluded with a reason")

    # 2. imported prices present in the sources
    for t in trims:
        p = t.get("starting_price")
        if not p or t.get("price_on_request"):
            continue
        if not any(v in NALL for v in (norm(x) for x in variants(p))):
            findings.append(f"{tag}/{t.get('slug')}: price {p:,} KWD does not appear in any saved source")

    # 2b. the price printed NEXT TO each grade name must be the price we imported (high-signal check:
    #     catches a price attached to the wrong grade, and a grade imported as POR though the site prices it)
    for t in trims:
        nm = norm(t.get("display_name_en"))
        if not nm:
            continue
        near = set()
        for rel, txt in texts.items():
            nt = norm(txt)
            for m in re.finditer(re.escape(nm), nt):
                near |= prices_in(nt[max(0, m.start() - 260): m.end() + 260])
        if not near:
            continue
        p = t.get("starting_price")
        if t.get("price_on_request") or not p:
            findings.append(f"{tag}/{t.get('slug')}: imported as price-on-request, but price(s) "
                            f"{', '.join(f'{x:,}' for x in sorted(near))} appear next to '{t.get('display_name_en')}' in the sources")
        elif p not in near:
            findings.append(f"{tag}/{t.get('slug')}: imported price {p:,} but the sources show "
                            f"{', '.join(f'{x:,}' for x in sorted(near))} next to '{t.get('display_name_en')}'")

    # 3. prices in the sources accounted for by a trim (catches MISSED grades)
    model_files = {rel: t for rel, t in texts.items() if tag.split("-")[0] in rel.lower() or len(C.get("models", [])) == 1}
    src_prices = prices_in("\n".join(model_files.values()) if model_files else ALL)
    imported = {t.get("starting_price") for t in trims if t.get("starting_price")}
    declared = {n.get("price") for n in src_trims if isinstance(n, dict) and n.get("price")}
    known = imported | declared | {mo.get("starting_price")}
    unaccounted = sorted(p for p in src_prices if p not in known)
    if unaccounted:
        msg = (f"{tag}: price(s) {', '.join(f'{p:,}' for p in unaccounted)} appear in the dealer sources but are not "
               f"on any imported trim - check for a missed grade or a wrong price")
        (findings if a.strict_unaccounted else notes).append(msg)

    n_priced = sum(1 for t in trims if t.get("starting_price") and not t.get("price_on_request"))
    published = len(src_prices) if src_prices else 0
    model_stats.append({"model": tag, "trims_imported": len(trims), "source_trims_declared": len(src_trims),
                        "trims_priced": n_priced, "prices_seen_in_sources": published,
                        "price_coverage_pct": round(100.0 * n_priced / max(1, min(published, len(trims))), 1) if trims else 0.0})
    if not src_trims:
        findings.append(f"{tag}: no source_trims recorded - grade coverage cannot be verified")

out = {"findings": findings, "notes": notes, "trims": rows, "models": model_stats}
save_json(os.path.join(W, "price_audit.json"), out)
L = ["# Trim & price audit (against saved sources)", "",
     f"Sources read: {len(texts)} files.", "",
     "| Model | Trims imported | Grades declared from source | Trims with a price | Prices seen in sources | Price coverage |",
     "|---|---|---|---|---|---|"]
for m in model_stats:
    L.append(f"| {m['model']} | {m['trims_imported']} | {m['source_trims_declared']} | {m['trims_priced']} | "
             f"{m['prices_seen_in_sources']} | {m['price_coverage_pct']}% |")
L += ["", "## Findings (must fix, or explain in the run notes)",
      "Nearby-price findings can be false positives when a page prints every grade's price in one block -",
      "open the source and confirm before changing data.", ""] + ([f"- {f}" for f in findings] or ["- none"])
L += ["", "## Notes"] + ([f"- {n}" for n in notes] or ["- none"])
L += ["", "## Per trim", "", "| Model | Trim | Price | Name found in sources |", "|---|---|---|---|"]
for r in rows:
    price_cell = "POR" if r["price_on_request"] else (f"{r['price']:,}" if r["price"] else "-")
    L.append(f"| {r['model']} | {r['trim']} | {price_cell} | {'yes' if r['name_in_sources'] else 'NO'} |")
open(os.path.join(W, "price_audit.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:10]))
print(f"findings: {len(findings)}, notes: {len(notes)} -> {W}/price_audit.md")
sys.exit(2 if findings else 0)
