#!/usr/bin/env python3
"""Build API payloads from <workdir>/content.json and import them to staging in dependency order:

  brand -> dealers -> models -> trims -> attribute-values -> trim-hero-stats -> equipment -> model-highlights

After each parent import it reads back the codes the backend ACTUALLY stored (the backend has been seen to
add `-kw` suffixes or double brand prefixes) and uses those for every child row.

/import/* endpoints are FULL-RECORD upserts: every run sends complete records, never partial patches.
/import/equipment REPLACES a trim's whole equipment list, so all categories for a trim go in one call.

Usage:
  import_catalog.py --workdir <dir> --dry            # build payloads/ only (media shown as LOCAL:<path>)
  import_catalog.py --workdir <dir>                  # full import (needs uploads.json + .jwt)
  import_catalog.py --workdir <dir> --only highlights,equipment   # re-run selected stages
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import (admin_headers, as_list, http, is_hosted, load_json, model_code, public_get, read_jwt,
                    save_json, trim_code, API)

STAGES = ["brand", "dealers", "models", "trims", "attributes", "hero_stats", "equipment", "highlights"]
BRAND_KEYS = {"code", "slug", "name_en", "name_ar", "tagline_en", "tagline_ar", "story_en", "story_ar",
              "heritage_title_en", "heritage_title_ar", "heritage_description_en", "heritage_description_ar",
              "heritage_founded", "heritage_milestone_en", "heritage_milestone_ar", "innovation_title_en",
              "innovation_title_ar", "innovation_description_en", "innovation_description_ar", "sustainability_en",
              "sustainability_ar", "country_of_origin", "country_of_manufacturing", "sort_order", "status",
              "is_featured", "editorial_stats", "service_links", "hero_gradient", "home_card_gradient", "logo_inset_tight"}
MODEL_KEYS = {"name_en", "name_ar", "model_year", "body_style_code", "short_description_en",
              "short_description_ar", "is_new", "is_updated", "is_featured", "family_code", "sub_brand_code",
              "primary_node_code", "segment_order", "hero_spec_codes", "compare_attribute_codes", "publish_state", "status"}
TRIM_KEYS = {"display_name_en", "display_name_ar", "trim_badge", "horsepower", "torque", "engine_summary", "engine_code",
             "fuel_type", "powertrain_type", "transmission", "drivetrain", "seats", "doors", "battery_capacity",
             "electric_range", "performance_line", "spec_region", "availability_status", "website_url", "lead_form_url"}
DEALER_KEYS = {"code", "name_en", "name_ar", "address_en", "address_ar", "phone", "latitude", "longitude", "map_url"}
STAT_DEFAULTS = {  # slot -> (attr/field, title_en, title_ar, unit)
    "power": ("horsepower", "Power", "القوة", "hp"),
    "torque": ("torque", "Torque", "عزم الدوران", "Nm"),
    "top_speed": ("top_speed", "Top Speed", "السرعة القصوى", "km/h"),
    "acceleration": ("zero_to_hundred", "0-100 km/h", "من 0 إلى 100 كم/س", "s"),
    "range": ("electric_range", "Range", "المدى", "km"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--workdir", required=True)
ap.add_argument("--dry", action="store_true")
ap.add_argument("--only", default="", help="comma list of stages: " + ",".join(STAGES))
a = ap.parse_args()
only = set(filter(None, a.only.split(","))) or set(STAGES)
W = a.workdir
C = load_json(os.path.join(W, "content.json"))
UP = load_json(os.path.join(W, "uploads.json"), {"by_path": {}, "by_md5": {}})
PAY = os.path.join(W, "payloads")
os.makedirs(PAY, exist_ok=True)
HDR = None if a.dry else admin_headers(read_jwt(W))


def url(ref):
    if not ref:
        return None
    if is_hosted(ref):
        return ref
    if ref in UP["by_path"]:
        return UP["by_path"][ref]
    if a.dry:
        return f"LOCAL:{ref}"
    sys.exit(f"Media not uploaded yet: {ref} (run upload_media.py)")


def clean(d):
    return {k: v for k, v in d.items() if v is not None}


def post(path, rows, label):
    save_json(os.path.join(PAY, f"{label}.json"), rows)
    if a.dry:
        print(f"  [dry] {label}: {len(rows)} rows"); return
    st, body = http("POST", API + path, rows, HDR)
    data = body.get("data", body) if isinstance(body, dict) else body
    print(f"  {label}: HTTP {st} {str(data)[:300]}")
    if st >= 300 or (isinstance(data, dict) and data.get("failed")):
        sys.exit(f"{label} failed - fix content.json and re-run that stage with --only <stage>")


B = C["brand"]
brand_code = B["code"]
print("brand code (requested):", brand_code)

# ---------- brand ----------
if "brand" in only:
    m = B.get("media", {})
    hero_type = "video" if m.get("hero_video") else ("image" if m.get("hero_image") else None)
    payload = clean({**{k: v for k, v in B.items() if k in BRAND_KEYS},
                     "slug": B.get("slug", brand_code), "status": B.get("status", "active"),
                     "is_featured": B.get("is_featured", False), "sort_order": B.get("sort_order", 999),
                     "logo_key": url(m.get("logo")), "logo_dark_key": url(m.get("logo_dark")),
                     "hero_media_type": hero_type, "hero_media_key": url(m.get("hero_video") or m.get("hero_image")),
                     "featured_image_key": url(m.get("featured_image")), "banner_key": url(m.get("banner")),
                     "heritage_image_key": url(m.get("heritage_image")),
                     "innovation_image_key": url(m.get("innovation_image")),
                     "metadata": {**B.get("metadata", {}), "sources": B.get("sources", []), "gaps": B.get("gaps", {})}})
    print("1. brand"); post("/v1/admin/import/brands", [payload], "01-brand")

brand_id = None
if not a.dry:
    bl = as_list(public_get("/v1/public/brands"))
    hit = next((b for b in bl if b["code"] in (brand_code, brand_code + "-kw")), None)
    if not hit:
        sys.exit(f"brand {brand_code} not found in /public/brands after import")
    if hit["code"] != brand_code:
        print(f"  ! backend stored brand code {hit['code']} (requested {brand_code}) - using stored code")
    brand_code, brand_id = hit["code"], hit["id"]
    print(f"  stored brand: {brand_code} (id {brand_id})")

# ---------- dealers ----------
if "dealers" in only and C.get("dealers"):
    print("2. dealers")
    post("/v1/admin/import/dealers", [clean({**{k: v for k, v in d.items() if k in DEALER_KEYS}, "brand_code": brand_code})
                                      for d in C["dealers"]], "02-dealers")


def trim_price(t):
    return None if t.get("price_on_request") or not t.get("starting_price") else t["starting_price"]


# ---------- models ----------
models = C.get("models", [])
if "models" in only and models:
    rows = []
    for mo in models:
        prices = [p for p in (trim_price(t) for t in mo.get("trims", [])) if p]
        start = mo.get("starting_price") or (min(prices) if prices else None)
        hero_img = url(mo.get("hero_image") or (mo["gallery"][0]["file"] if mo.get("gallery") else None))
        hero_vid = url(mo.get("hero_video"))
        rows.append(clean({**{k: v for k, v in mo.items() if k in MODEL_KEYS},
                           "brand_code": brand_code, "code": model_code(brand_code, mo), "slug": model_code(brand_code, mo), "currency": "KWD",
                           "starting_price": start, "price_on_request": start is None,
                           "is_new": mo.get("is_new", True), "is_updated": mo.get("is_updated", False),
                           "is_featured": mo.get("is_featured", False),
                           "publish_state": mo.get("publish_state", "published"), "status": mo.get("status", "active"),
                           "hero_image_key": hero_img, "hero_media_type": "video" if hero_vid else ("image" if hero_img else None),
                           "hero_media_key": hero_vid or hero_img,
                           "images": [clean({"category": g.get("category", "gallery"), "image_key": url(g["file"]),
                                             "sort_order": i + 1, "alt_en": g.get("alt_en"), "alt_ar": g.get("alt_ar")})
                                      for i, g in enumerate(mo.get("gallery", []))],
                           "metadata": {**mo.get("metadata", {}), "kuwait_url": mo.get("kuwait_url"),
                                        "sources": mo.get("sources", []), "gaps": mo.get("gaps", {})}}))
    print("3. models"); post("/v1/admin/import/models", rows, "03-models")

# resolve stored model codes
stored_models = {}
if not a.dry and models:
    sm = as_list(public_get(f"/v1/public/brands/{brand_id}/models"))
    for mo in models:
        want = model_code(brand_code, mo)
        hit = next((x for x in sm if x["code"] == want), None) or \
              next((x for x in sm if x["code"].endswith("-" + mo["slug"]) or x["code"].endswith(mo["slug"])), None)
        if not hit:
            sys.exit(f"model {want} not found after import; stored: {[x['code'] for x in sm]}")
        if hit["code"] != want:
            print(f"  ! model stored as {hit['code']} (requested {want}) - children will use stored code")
        stored_models[mo["slug"]] = (hit["code"], hit["id"])
else:
    stored_models = {mo["slug"]: (model_code(brand_code, mo), None) for mo in models}

# ---------- trims + children ----------
trim_rows, attr_rows, stat_rows, equip_by_trim, hl_rows = [], [], [], {}, []
for mo in models:
    mcode, _ = stored_models[mo["slug"]]
    trims = sorted(mo.get("trims", []), key=lambda t: (trim_price(t) is None, trim_price(t) or 0, t.get("sort_order", 0)))
    for i, t in enumerate(trims):
        tc = trim_code(mcode, t)
        p = trim_price(t)
        hv, hi = url(t.get("hero_video")), url(t.get("hero_image"))
        trim_rows.append(clean({**{k: v for k, v in t.items() if k in TRIM_KEYS},
                                "model_code": mcode, "variant_code": tc, "slug": tc,
                                "trim_badge": t.get("trim_badge", t["display_name_en"]), "spec_region": t.get("spec_region", "gcc"),
                                "availability_status": t.get("availability_status", "available"),
                                "starting_price": p, "price_on_request": p is None, "currency": "KWD",
                                "is_default": i == 0, "sort_order": i + 1,
                                "website_url": t.get("website_url") or mo.get("kuwait_url") or "", "lead_form_url": t.get("lead_form_url", ""),
                                "hero_image_key": hi, "hero_media_type": "video" if hv else ("image" if hi else None),
                                "hero_media_key": hv or hi,
                                "colors": [clean({"name_en": c.get("name_en"), "name_ar": c.get("name_ar"), "hex_code": c.get("hex_code"),
                                                  "image_key": url(c.get("image")), "swatch_key": url(c.get("swatch")),
                                                  "sort_order": n + 1}) for n, c in enumerate(t.get("colors", []))] or None,
                                "metadata": {**t.get("metadata", {}), "sources": t.get("sources", []), "gaps": t.get("gaps", {})}}))
        attrs = dict(t.get("attributes", {}))
        for code, val in attrs.items():
            if val in (None, "", 0):
                continue  # FE shows missing values itself; never post 0/null
            attr_rows.append({"owner_type": "trim", "owner_code": tc, "attr_code": code, "value_json": {"value": val}})
        stats = t.get("hero_stats")
        if stats is None:  # default: power, torque, top speed when known
            stats, n = [], 1
            for slot in ("power", "torque", "top_speed"):
                field, te, ta, unit = STAT_DEFAULTS[slot]
                v = t.get(field) or attrs.get(field)
                if v:
                    stats.append({"slot": slot, "title_en": te, "title_ar": ta, "value": str(v), "unit": unit, "sort_order": n}); n += 1
        stat_rows += [{**s, "trim_code": tc} for s in stats]
        equip_by_trim[tc] = [clean({"trim_code": tc, "category": e["category"], "name_en": e["name_en"], "name_ar": e["name_ar"],
                                    "is_standard": e.get("is_standard", True), "is_optional": e.get("is_optional", False),
                                    "code": e.get("code"), "sort_order": n + 1})
                             for n, e in enumerate(t.get("equipment", []))]
    for h in mo.get("highlights", []):
        hl_rows.append(clean({"model_code": mcode, "section": h["section"], "slot": h["slot"], "sort_order": h.get("sort_order"),
                              "title_en": h["title_en"], "title_ar": h["title_ar"], "description_en": h["description_en"],
                              "description_ar": h["description_ar"], "image_key": url(h.get("image"))}))

if "trims" in only and trim_rows:
    print("4. trims"); post("/v1/admin/import/trims", trim_rows, "04-trims")
if not a.dry and trim_rows:
    for mo in models:
        mcode, mid = stored_models[mo["slug"]]
        stored = {x["variant_code"] for x in as_list(public_get(f"/v1/public/models/{mid}/trims"))}
        want = {r["variant_code"] for r in trim_rows if r["model_code"] == mcode}
        if want - stored:
            sys.exit(f"trims missing after import for {mcode}: {sorted(want - stored)}")
    print("  all trims verified by stored variant_code")
if "attributes" in only and attr_rows:
    print("5. attribute-values"); post("/v1/admin/import/attribute-values", attr_rows, "05-attribute-values")
if "hero_stats" in only and stat_rows:
    print("6. trim-hero-stats"); post("/v1/admin/import/trim-hero-stats", stat_rows, "06-hero-stats")
if "equipment" in only:
    print("7. equipment (one call per trim; the endpoint replaces the trim's list)")
    for tc, rows in equip_by_trim.items():
        if rows:
            post("/v1/admin/import/equipment", rows, f"07-equipment-{tc}")
if "highlights" in only and hl_rows:
    print("8. model-highlights"); post("/v1/admin/import/model-highlights", hl_rows, "08-highlights")

save_json(os.path.join(W, "stored_codes.json"),
          {"brand": {"code": brand_code, "id": brand_id},
           "models": {s: {"code": c, "id": i} for s, (c, i) in stored_models.items()}})
print("DONE" + (" (dry run - nothing posted)" if a.dry else ""))
