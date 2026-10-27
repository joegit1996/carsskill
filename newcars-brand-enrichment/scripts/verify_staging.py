#!/usr/bin/env python3
"""Read the imported brand back through the PUBLIC API and compare it with content.json.

Checks: stored codes, Arabic round-trip (no '???' / mojibake), prices + default trim, trim count, trim specs
reaching `trim.specs`, hero stats, equipment counts per trim, highlight count, gallery count, dealer/branches,
and that every media URL answers 200. Also pings the staging pages.
Writes <workdir>/verify.md; exit 0 when everything matches.  Usage: verify_staging.py --workdir <dir>
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import ARABIC, ENV, SITE, as_list, http, load_json, public_get, trim_code

ap = argparse.ArgumentParser()
ap.add_argument("--workdir", required=True)
ap.add_argument("--skip-media", action="store_true")
a = ap.parse_args()
W = a.workdir
C = load_json(os.path.join(W, "content.json"))
S = load_json(os.path.join(W, "stored_codes.json"))
fails, oks, notes = [], [], []


def check(cond, msg):
    (oks if cond else fails).append(msg)


def note(msg):
    """Something a human should look at, that is not a pass/fail of our own data."""
    notes.append(msg)


def ar_ok(s):
    return bool(s) and bool(ARABIC.search(s)) and "??" not in s


bid = S["brand"]["id"]
b = public_get(f"/v1/public/brands/{bid}")
check(b["code"] == S["brand"]["code"], f"brand code {b['code']}")
for f in ("name_ar", "tagline_ar", "story_ar", "heritage_title_ar", "heritage_description_ar", "innovation_title_ar"):
    if C["brand"].get(f):
        check(ar_ok(b.get(f)), f"brand.{f} Arabic round-trip")
check(bool(b.get("logo_key")), "brand logo stored")
check(bool(b.get("hero_media_key")), f"brand hero stored ({b.get('hero_media_type')})")
dealers = as_list(public_get(f"/v1/public/brands/{bid}/dealers"))
check(len(dealers) >= len(C.get("dealers", [])), f"dealers: {len(dealers)} stored / {len(C.get('dealers', []))} sent")

media = [b.get("logo_key"), b.get("hero_media_key")]
for mo in C.get("models", []):
    sc = S["models"][mo["slug"]]
    m = public_get(f"/v1/public/models/{sc['id']}")
    tag = m["code"]
    check(ar_ok(m.get("name_ar")) or m.get("name_ar") == mo.get("name_ar"), f"{tag} name_ar")
    check(ar_ok(m.get("short_description_ar")), f"{tag} short_description_ar Arabic")
    trims_src = mo.get("trims", [])
    priced = sorted(t["starting_price"] for t in trims_src if not t.get("price_on_request") and t.get("starting_price"))
    if priced:
        check(m.get("starting_price") == priced[0] and not m.get("price_on_request"),
              f"{tag} starting_price {m.get('starting_price')} == cheapest trim {priced[0]}")
    gal = m.get("gallery_images") or []
    check(len(gal) == len(mo.get("gallery", [])), f"{tag} gallery {len(gal)}/{len(mo.get('gallery', []))}")
    hl = m.get("highlights") or {}
    live_hl = {(sec, c.get("slot")) for sec, cards in (hl.items() if isinstance(hl, dict) else [])
               for c in (cards or [])}
    want_hl = {(c["section"], c["slot"]) for c in mo.get("highlights", [])}
    # Every card we authored must be live. Extra slots are reported, not failed: a model can carry cards
    # from an earlier import in slots ours don't use, and there is no DELETE for model highlights.
    check(want_hl <= live_hl, f"{tag} highlights: ours live {len(want_hl & live_hl)}/{len(want_hl)}"
                              + (f", missing {sorted(want_hl - live_hl)}" if want_hl - live_hl else ""))
    if live_hl - want_hl:
        note(f"{tag} carries {len(live_hl - want_hl)} highlight slot(s) we do not author: "
             f"{sorted(live_hl - want_hl)} - no API route deletes model highlights, so verify their content by hand")
    check(m.get("is_featured") == bool(mo.get("is_featured")), f"{tag} is_featured={m.get('is_featured')}")
    media += [m.get("hero_image_key"), m.get("hero_media_key")] + [g.get("image_key") for g in gal]
    st = as_list(public_get(f"/v1/public/models/{sc['id']}/trims"))
    by_code = {t["variant_code"]: t for t in st}
    check(len(st) == len(trims_src), f"{tag} trims {len(st)}/{len(trims_src)}")
    default = [t for t in st if t.get("is_default")]
    if priced and default:
        check(default[0].get("starting_price") == priced[0], f"{tag} default trim is the cheapest priced trim")
    for t in trims_src:
        tc = trim_code(sc["code"], t)
        x = by_code.get(tc)
        if not x:
            fails.append(f"{tc} missing"); continue
        check(ar_ok(x.get("display_name_ar")) or x.get("display_name_ar") == t.get("display_name_ar"), f"{tc} display_name_ar")
        want_attrs = {k for k, v in t.get("attributes", {}).items() if v not in (None, "", 0)}
        specs = x.get("specs") or {}
        # some attributes (horsepower, torque, transmission...) surface as top-level trim fields, not in specs
        missing = sorted(k for k in want_attrs if specs.get(k) in (None, "", 0) and x.get(k) in (None, "", 0))
        check(not missing, f"{tc} specs populated" + (f" (missing {missing})" if missing else ""))
        from collections import Counter
        dups = {k: n for k, n in Counter(a["code"] for a in (x.get("attributes") or [])).items() if n > 1}
        check(not dups, f"{tc} attribute values not duplicated" + (f" (duplicates: {dups})" if dups else ""))
        check(len(x.get("equipment") or []) == len(t.get("equipment", [])),
              f"{tc} equipment {len(x.get('equipment') or [])}/{len(t.get('equipment', []))}")
        check(len(x.get("hero_stats") or []) >= 1 or not (t.get("horsepower") or t.get("torque")), f"{tc} hero stats present")
    br = as_list(public_get(f"/v1/public/models/{sc['id']}/branches"))
    check(len(br) >= min(1, len(C.get("dealers", []))), f"{tag} branches endpoint returns {len(br)} dealer(s)")

if not a.skip_media:
    bad = []
    for u in {u for u in media if u}:
        st, _ = http("HEAD", u, raw=True)
        if st != 200:
            bad.append(f"{st} {u}")
    check(not bad, f"media URLs answer 200 ({len({u for u in media if u})} checked)" + (f": {bad[:5]}" if bad else ""))

site = SITE
pages = [f"{site}/brand/{S['brand']['code']}"] + [f"{site}/model/{v['id']}" for v in S["models"].values()]
for p in pages:
    st, _ = http("GET", p, raw=True)
    check(st == 200, f"page {p} -> {st}")

L = [f"# Catalog verification - {S['brand']['code']} ({ENV})", "", f"**{'ALL CHECKS PASSED' if not fails else f'{len(fails)} FAILED'}** "
     f"({len(oks)} passed, {len(notes)} to review)", ""]
if fails:
    L += ["## Failed", *[f"- {f}" for f in fails], ""]
if notes:
    L += ["## To review by hand", *[f"- {n}" for n in notes], ""]
L += ["## Passed", *[f"- {o}" for o in oks], "", "## Pages to QA visually (EN + AR)", *[f"- {p}" for p in pages]]
open(os.path.join(W, "verify.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:3 + (len(fails) + 2 if fails else 0) + (len(notes) + 2 if notes else 0)]))
print(f"full report: {W}/verify.md")
sys.exit(1 if fails else 0)
