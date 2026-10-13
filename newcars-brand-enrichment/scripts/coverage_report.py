#!/usr/bin/env python3
"""Score content.json for coverage and accuracy against the brand-import checklist.

Coverage   = filled fields / (expected fields - justified gaps), per level (brand / models / trims).
             A justified gap is a field listed in the entity's "gaps": {"field": "reason"} - e.g. the Kuwait
             brochure says TBD. Unjustified empty fields are listed so they can be researched or justified.
Enumeration = models/trims imported vs the lists found on the official source (run.source_models,
             model.source_trims) - anything not imported must be in run.excluded / model.excluded_trims with a reason.
Accuracy checks (errors) = rules the checklist makes non-negotiable (real Arabic, no Wikipedia, no external
             media, no brand prefix in model names, highlight rules, price/default-trim rules, ...).

GATE (exit 0 only if all true): enumeration 100%, coverage >= 90% at every level, zero errors.
Writes <workdir>/coverage.md and coverage.json.  Usage: coverage_report.py --workdir <dir>
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import ARABIC, BANNED_SOURCE, is_hosted, iter_media, load_json, save_json

GATE_PCT = 90.0
EQUIP_CATS = {"Safety", "Comfort", "Technology", "Exterior", "Interior", "Performance"}
FE_EQUIP_CATS = {"Safety", "Comfort", "Technology", "Exterior", "Interior"}
BODY = {"sedan", "suv", "coupe", "pickup", "hatchback", "van", "wagon", "convertible"}
FUEL = {"petrol", "diesel", "hybrid", "plugin_hybrid", "electric"}
DRIVE = {"fwd", "rwd", "awd"}

BRAND_FIELDS = ["name_en", "name_ar", "tagline_en", "tagline_ar", "story_en", "story_ar", "heritage_title_en",
                "heritage_title_ar", "heritage_description_en", "heritage_description_ar", "heritage_founded",
                "heritage_milestone_en", "heritage_milestone_ar", "innovation_title_en", "innovation_title_ar",
                "innovation_description_en", "innovation_description_ar", "country_of_origin",
                "media.logo", "media.logo_dark", "media.hero", "media.featured_image", "media.heritage_image",
                "media.innovation_image", "dealers"]
MODEL_FIELDS = ["name_en", "name_ar", "model_year", "body_style_code", "short_description_en", "short_description_ar",
                "kuwait_url", "price", "hero_image", "hero_video", "gallery_13", "highlights_6", "sources"]
TRIM_FIELDS = ["display_name_en", "display_name_ar", "price", "horsepower", "torque", "engine_summary", "fuel_type",
               "transmission", "drivetrain", "seats", "equipment",
               "attr.length_mm", "attr.width_mm", "attr.height_mm", "attr.wheelbase_mm", "attr.top_speed",
               "attr.engine_type", "attr.displacement", "attr.cylinders", "attr.zero_to_hundred",
               "attr.fuel_economy_combined", "attr.curb_weight_kg", "attr.trunk_volume_liters", "attr.warranty",
               "attr.fuel_tank_liters"]
EV_SWAP = {"attr.fuel_tank_liters": "battery_capacity", "attr.fuel_economy_combined": "electric_range",
           "attr.displacement": None, "attr.cylinders": None}

ap = argparse.ArgumentParser()
ap.add_argument("--workdir", required=True)
a = ap.parse_args()
C = load_json(os.path.join(a.workdir, "content.json"))
B, models, run = C["brand"], C.get("models", []), C.get("run", {})
errors, warnings = [], []


def filled(v):
    return v not in (None, "", [], {}, 0)


def real_ar(ar, en, allow_latin=False):
    if not ar:
        return False
    if ARABIC.search(ar):
        return ar.strip() != (en or "").strip()
    return allow_latin and ar == en  # short letter/engine codes (SE, P400, 2.0T) may stay Latin


# Fields that cannot be waived with a "gaps" reason: the page is visibly broken or thin without them, and in
# practice they are always obtainable (a different logo file, more gallery images, authoring 6 highlight cards).
CRITICAL = {"media.logo", "media.hero", "hero_image", "gallery_13", "highlights_6", "name_en", "name_ar",
            "display_name_en", "display_name_ar"}


def score(entity, fields, getter, label):
    gaps = entity.get("gaps", {})
    got, missing, justified = 0, [], []
    for f in fields:
        if getter(f):
            got += 1
        elif f in CRITICAL:
            missing.append(f)
            if f in gaps or f.split(".")[-1] in gaps:
                errors.append(f"{label}: '{f}' is a critical field - it cannot be waived with a gaps reason")
        elif f in gaps or f.split(".")[-1] in gaps:
            justified.append(f"{f} ({gaps.get(f) or gaps.get(f.split('.')[-1])})")
        else:
            missing.append(f)
    denom = len(fields) - len(justified)
    return {"label": label, "filled": got, "expected": len(fields), "justified": justified, "missing": missing,
            "pct": round(100.0 * got / denom, 1) if denom else 100.0,
            "raw_pct": round(100.0 * got / len(fields), 1) if fields else 100.0}


# ---------------- brand ----------------
bm = B.get("media", {})
def bget(f):
    if f == "media.hero":
        return bm.get("hero_video") or bm.get("hero_image")
    if f.startswith("media."):
        return bm.get(f[6:])
    if f == "dealers":
        return any(d.get("phone") for d in C.get("dealers", []))
    return filled(B.get(f))
brand_score = score(B, BRAND_FIELDS, bget, B.get("code", "brand"))
if not bm.get("hero_video"):
    warnings.append("brand: no hero video (checklist prefers video; image fallback used)")
for f in [x for x in BRAND_FIELDS if x.endswith("_ar")]:
    if B.get(f) and not real_ar(B[f], B.get(f[:-3] + "_en")):
        errors.append(f"brand.{f}: not real Arabic or identical to EN")
if not B.get("code", "").strip():
    errors.append("brand.code missing")

# ---------------- models / trims ----------------
model_scores, trim_scores = [], []
featured = 0
brand_names = {n.lower() for n in [B.get("name_en", ""), B.get("code", "").replace("kw-", "")] if n}
for mo in models:
    tag = mo.get("slug", "?")
    featured += bool(mo.get("is_featured"))
    trims = mo.get("trims", [])
    hl = mo.get("highlights", [])
    gal = [g["file"] for g in mo.get("gallery", [])]
    hero = mo.get("hero_image") or (gal[0] if gal else None)
    visible = set(gal) - {hero} - {h.get("image") for h in hl}
    priced = [t for t in trims if not t.get("price_on_request") and filled(t.get("starting_price"))]

    def mget(f):
        if f == "price":
            return bool(priced) or filled(mo.get("starting_price"))
        if f == "gallery_13":
            return len(visible) >= 13
        if f == "highlights_6":
            return len(hl) == 6
        return filled(mo.get(f))
    s = score(mo, MODEL_FIELDS, mget, tag)
    s["gallery_unique_after_dedupe"] = len(visible)
    model_scores.append(s)

    if any(mo.get("name_en", "").lower().startswith(n + " ") for n in brand_names):
        errors.append(f"{tag}: name_en starts with the brand name (causes doubled codes)")
    if not real_ar(mo.get("name_ar"), mo.get("name_en"), allow_latin=bool(re.search(r"\d", mo.get("name_en", "")))):
        errors.append(f"{tag}: name_ar is not an Arabic transliteration")
    if mo.get("short_description_ar") and not real_ar(mo["short_description_ar"], mo.get("short_description_en")):
        errors.append(f"{tag}: short_description_ar not real Arabic")
    if mo.get("body_style_code") and mo["body_style_code"] not in BODY:
        errors.append(f"{tag}: body_style_code '{mo['body_style_code']}' not in {sorted(BODY)}")
    if len(gal) != len(set(gal)):
        errors.append(f"{tag}: duplicate gallery files")
    if hl:
        imgs = [h.get("image") for h in hl]
        if len(hl) != 6:
            errors.append(f"{tag}: {len(hl)} highlight cards (need exactly 6)")
        if len(set(imgs)) != len(imgs) or None in imgs:
            errors.append(f"{tag}: highlight images must be 6 distinct files")
        want = {("parallax", "design"), ("parallax", "performance"), ("parallax", "comfort"),
                ("featured", "technology"), ("featured", "efficiency"), ("featured", "comfort")}
        if {(h["section"], h["slot"]) for h in hl} != want:
            errors.append(f"{tag}: highlight section/slot set must be {sorted(want)}")
        for h in hl:
            if len(h.get("title_en", "")) > 60 or len(h.get("description_en", "")) > 400:
                errors.append(f"{tag}/{h['slot']}: title >60 or description >400 chars")
            if not real_ar(h.get("title_ar"), h.get("title_en")) or not real_ar(h.get("description_ar"), h.get("description_en")):
                errors.append(f"{tag}/{h['section']}.{h['slot']}: AR highlight text missing or copied from EN")
    if not mo.get("hero_video"):
        warnings.append(f"{tag}: no model hero video (image hero only)")
    # enumeration of trims
    src_trims = mo.get("source_trims") or []
    excl = {x["name"]: x.get("reason") for x in mo.get("excluded_trims", [])}
    names = {t.get("display_name_en") for t in trims}
    for n in src_trims:
        nm = n.get("name") if isinstance(n, dict) else n   # source_trims may be {name, price, source} or a bare name
        if nm not in names and nm not in excl:
            errors.append(f"{tag}: source trim '{nm}' neither imported nor excluded with a reason")
    if not src_trims:
        errors.append(f"{tag}: source_trims not recorded - grade coverage cannot be verified (list every grade the "
                      f"official source shows, with its price, or the 100% is meaningless)")

    for t in trims:
        ttag = f"{tag}/{t.get('slug', '?')}"
        at = t.get("attributes", {})
        ev = t.get("fuel_type") == "electric"
        fields = [EV_SWAP.get(f, f) if ev else f for f in TRIM_FIELDS]
        fields = [f for f in fields if f]

        def tget(f):
            if f == "price":
                return (not t.get("price_on_request")) and filled(t.get("starting_price"))
            if f == "equipment":
                return len(t.get("equipment", [])) > 0
            if f.startswith("attr."):
                return filled(at.get(f[5:]))
            return filled(t.get(f)) or filled(at.get(f))
        trim_scores.append(score(t, fields, tget, ttag))
        allow = len(t.get("display_name_en", "")) <= 6 and " " not in t.get("display_name_en", "")
        if not real_ar(t.get("display_name_ar"), t.get("display_name_en"), allow_latin=allow):
            errors.append(f"{ttag}: display_name_ar not Arabic (only short letter/engine codes may stay Latin)")
        if t.get("fuel_type") and t["fuel_type"] not in FUEL:
            errors.append(f"{ttag}: fuel_type '{t['fuel_type']}' not in {sorted(FUEL)}")
        if t.get("drivetrain") and t["drivetrain"] not in DRIVE:
            errors.append(f"{ttag}: drivetrain '{t['drivetrain']}' not in {sorted(DRIVE)}")
        for k in ("horsepower", "torque", "seats"):
            if t.get(k) == 0:
                errors.append(f"{ttag}: {k}=0 (leave empty + justify instead of 0)")
        cats = {e.get("category") for e in t.get("equipment", [])}
        if cats - EQUIP_CATS:
            errors.append(f"{ttag}: unknown equipment categories {sorted(cats - EQUIP_CATS)}")
        if "Performance" in cats:
            warnings.append(f"{ttag}: 'Performance' equipment is not shown by the current frontend tabs")
        for e in t.get("equipment", []):
            if not real_ar(e.get("name_ar"), e.get("name_en"), allow_latin=True) or not ARABIC.search(e.get("name_ar", "")):
                errors.append(f"{ttag}: equipment '{e.get('name_en')}' lacks real Arabic"); break
        if not t.get("sources") and not mo.get("sources"):
            errors.append(f"{ttag}: no sources recorded")

if models and not any(not t.get("price_on_request") and t.get("starting_price") for m in models for t in m.get("trims", [])):
    warnings.append("no priced trims at all - every model will show Price on Request")
if len(models) >= 3 and featured != 3:
    errors.append(f"brand has {featured} featured models (need exactly 3)")

# enumeration of models
src_models = run.get("source_models") or []
excluded = {x["name"]: x.get("reason") for x in run.get("excluded", [])}
imported = {m.get("name_en") for m in models}
not_covered = [n for n in src_models if n not in imported and n not in excluded]
enum_pct = round(100.0 * (len(src_models) - len(not_covered)) / len(src_models), 1) if src_models else 0.0
if not src_models:
    errors.append("run.source_models is empty - record the official model list so enumeration can be verified")
for n in not_covered:
    errors.append(f"model '{n}' is on the official source but neither imported nor excluded with a reason")

# global rules
blob = json.dumps(C, ensure_ascii=False)
if BANNED_SOURCE.search(blob):
    errors.append("Wikipedia/Wikimedia appears in content.json (banned as a source, even in notes)")
for r in iter_media(C):
    if r.startswith("http") and not is_hosted(r):
        errors.append(f"external media URL: {r}")
    elif not r.startswith("http") and not os.path.exists(os.path.join(a.workdir, r)):
        errors.append(f"media file missing on disk: {r}")
if re.search(r"youtube\.com|youtu\.be|vimeo\.com", blob):
    errors.append("YouTube/Vimeo reference found (hero video must be a downloaded MP4)")


def level(scores, key="pct"):
    if not scores:
        return 0.0
    return round(sum(s[key] for s in scores) / len(scores), 1)


lv = {"brand": brand_score["pct"], "models": level(model_scores), "trims": level(trim_scores)}
raw = {"brand": brand_score["raw_pct"], "models": level(model_scores, "raw_pct"), "trims": level(trim_scores, "raw_pct")}
passed = enum_pct == 100.0 and all(v >= GATE_PCT for v in lv.values()) and not errors
out = {"gate_passed": passed, "gate": f"enumeration 100%, each level >= {GATE_PCT}%, 0 errors",
       "enumeration_pct": enum_pct, "levels": lv, "levels_raw": raw, "errors": errors, "warnings": warnings,
       "brand": brand_score, "models": model_scores, "trims": trim_scores}
save_json(os.path.join(a.workdir, "coverage.json"), out)

L = [f"# Coverage report - {B.get('code')}", "",
     f"**Gate: {'PASSED' if passed else 'FAILED'}** ({out['gate']})", "",
     "| Level | Coverage (justified gaps excluded) | Raw fields filled | Entities |", "|---|---|---|---|",
     f"| Model enumeration | {enum_pct}% | - | {len(src_models) - len(not_covered)}/{len(src_models)} official models covered |",
     f"| Brand | {lv['brand']}% | {raw['brand']}% | 1 |",
     f"| Models | {lv['models']}% | {raw['models']}% | {len(model_scores)} |",
     f"| Trims | {lv['trims']}% | {raw['trims']}% | {len(trim_scores)} |", "",
     "Raw = every expected field counted, including ones no official source publishes.", ""]
if errors:
    L += ["## Errors (must fix)", *[f"- {e}" for e in errors], ""]
if warnings:
    L += ["## Warnings", *[f"- {w}" for w in sorted(set(warnings))], ""]
L += ["## Gaps", ""]
for s in [brand_score, *model_scores, *trim_scores]:
    if s["missing"] or s["justified"]:
        L.append(f"- **{s['label']}** {s['pct']}% - missing: {', '.join(s['missing']) or 'none'}"
                 + (f"; justified: {'; '.join(s['justified'])}" if s["justified"] else ""))
for s in model_scores:
    L.append(f"- {s['label']}: {s['gallery_unique_after_dedupe']} gallery images visible after de-dupe (need >= 13)")
open(os.path.join(a.workdir, "coverage.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:12]))
print(f"... full report: {a.workdir}/coverage.md")
sys.exit(0 if passed else 2)
