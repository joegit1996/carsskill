# content.json — the single source of truth for a brand run

Everything the research produces goes into `<workdir>/content.json`. The scripts read only this file (plus
`uploads.json`, which is generated). Media fields hold **local file paths relative to the workdir** (e.g.
`media/outlander/hero.jpg`); already-hosted staging URLs are also accepted. Never put external URLs here.

Omit a field instead of writing `null`/`0`. When a field is empty because the official source doesn't publish
it (or sources conflict), record it in that entity's `gaps` object as `"field": "reason"` — this is what makes
the coverage score honest and tells the next person why it's empty.

## Contents
1. Top level and `run`
2. `brand`
3. `dealers`
4. `models[]`
5. `models[].trims[]`
6. `models[].highlights[]`
7. Field vocabularies
8. Minimal example

## 1. Top level

```json
{
  "run": {
    "market": "KW",
    "code_mode": "test",                      // "test" = kw- prefixed codes, "real" = production codes (ask the user)
    "kuwait_dealer_url": "https://www.mitsubishi-motors.com.kw/en",
    "source_models": ["Mirage", "Attrage", "Outlander", "L200"],   // EVERY model on the official KW lineup page
    "excluded": [{"name": "Mirage", "reason": "discontinued - removed from KW site nav on 2026-09-21"}],
    "notes": "free text: conflicts found, decisions taken"
  },
  "brand": {...}, "dealers": [...], "models": [...]
}
```
`source_models` + `excluded` drive the enumeration score: every official model must be imported or excluded with a reason.

## 2. brand

| key | notes |
|---|---|
| `code`, `slug` | `kw-<brand>` in test mode; real brand code otherwise. slug = code |
| `name_en`, `name_ar` | Arabic script (ميتسوبيشي) |
| `tagline_en/_ar` | only if the brand publishes one — never invent |
| `story_en/_ar` | 2–4 sentences, Kuwait context (distributor, showrooms, warranty) |
| `heritage_title_en/_ar`, `heritage_description_en/_ar`, `heritage_founded` ("1870"), `heritage_milestone_en/_ar` | |
| `innovation_title_en/_ar`, `innovation_description_en/_ar` | name a proprietary technology |
| `sustainability_en/_ar` | optional |
| `country_of_origin`, `country_of_manufacturing` | |
| `is_featured` (default false), `sort_order` (default 999) | |
| `media` | `{logo, logo_dark, hero_video, hero_image, featured_image, banner, heritage_image, innovation_image}` — local paths |
| `sources` | list of URLs actually used |
| `gaps`, `metadata` | `metadata._note` = short provenance note |

## 3. dealers
```json
[{"code": "kw-mitsubishi-al-rai", "name_en": "...", "name_ar": "...", "address_en": "...", "address_ar": "...",
  "phone": "+96522055888", "latitude": 29.31, "longitude": 47.93, "map_url": "https://www.google.com/maps?q=29.31,47.93"}]
```
Phone in E.164. Only showrooms (not parts/service-only sites) unless the user asks otherwise.

## 4. models[]

| key | notes |
|---|---|
| `slug` | e.g. `outlander`; model code becomes `<brand_code>-<slug>` (override with `code` only if needed) |
| `name_en` | **without** the brand name ("Outlander", not "Mitsubishi Outlander") |
| `name_ar` | Arabic transliteration (أوتلاندر); alphanumeric names keep digits/Latin ("296 GTB") |
| `model_year` | integer, latest MY sold in Kuwait |
| `body_style_code` | see vocab |
| `short_description_en/_ar` | 3–6 sentences, paraphrased from the KW model page; AR authored, not mirrored |
| `kuwait_url` | the model's dealer page |
| `starting_price` | optional — the importer uses the cheapest priced trim automatically |
| `is_featured` | exactly 3 per brand when the brand has ≥ 3 models |
| `hero_image`, `hero_video` | local paths; video only if the manufacturer publishes a downloadable MP4 |
| `gallery` | `[{"file", "category": "exterior|interior", "alt_en", "alt_ar"}]` — 18–20 distinct files (≥ 13 must remain after removing hero + highlight images) |
| `hero_spec_codes` | default `["horsepower","torque","top_speed"]` — only codes that have values |
| `compare_attribute_codes` | only codes that have attribute values on ≥ 1 trim (+ `seats`) |
| `source_trims` | EVERY grade on the official source, as `[{"name": "Full Option", "price": 12200, "source": "<url>"}]` (a bare name is accepted but weaker). `price` = what the dealer prints for that grade, omitted when none is shown. This is the denominator for grade **and** price coverage, and `price_audit.py` checks it against the saved pages |
| `excluded_trims` | `[{"name", "reason"}]` |
| `sources`, `gaps`, `metadata` | |
| `trims`, `highlights` | below |

## 5. models[].trims[]

| key | notes |
|---|---|
| `slug` | e.g. `full-option`; variant code = `<model_code>-<slug>` |
| `display_name_en/_ar` | AR transliterated (فُل أوبشن); short letter/engine codes stay Latin (SE, P400, 2.0T) |
| `starting_price` (KWD int) / `price_on_request` | never send 0 |
| `horsepower` (int hp), `torque` (int Nm) | kW → hp: × 1.341, round; note the conversion in `metadata` |
| `engine_summary` ("2.5L MIVEC DOHC 4-cyl"), `engine_code`, `fuel_type`, `powertrain_type` (ice/hev/phev/bev), `transmission` ("CVT", "8-speed AT"), `drivetrain`, `seats`, `doors` | |
| `battery_capacity` (kWh), `electric_range` (km) | EV / PHEV |
| `attributes` | deep specs → `/import/attribute-values`: `length_mm, width_mm, height_mm, wheelbase_mm, top_speed, engine_type, displacement (L), cylinders, zero_to_hundred, fuel_economy_combined, fuel_economy_city, fuel_economy_highway, curb_weight_kg, trunk_volume_liters, fuel_tank_liters, warranty, transmission, drive_type, horsepower, torque` |
| `hero_stats` | optional; default = power/torque/top_speed from the values above, with Arabic titles |
| `equipment` | `[{"category", "name_en", "name_ar", "is_standard", "is_optional"}]` — customer-facing wording, see sources-and-research.md |
| `hero_image`, `hero_video`, `colors[{name_en,name_ar,hex_code,image,swatch}]` | optional |
| `sources`, `gaps`, `metadata` | put conflicts in `metadata._conflict` |

Trim order and `is_default` are set by the importer (cheapest priced first).

## 6. models[].highlights[] — exactly 6
```json
{"section": "parallax", "slot": "design", "sort_order": 1, "image": "media/outlander/g05.jpg",
 "title_en": "≤ 60 chars", "title_ar": "...", "description_en": "≤ 400 chars", "description_ar": "..."}
```
Slots: parallax = design, performance, comfort · featured = technology, efficiency, comfort. Six distinct images,
all from the model's gallery. Keep the slot value but re-word when the page lacks the topic (pickups:
efficiency → capability; hypercars: efficiency → aerodynamics).

## 7. Vocabularies
- body_style_code: sedan, suv, coupe, pickup, hatchback, van, wagon, convertible
- fuel_type: petrol, diesel, hybrid, plugin_hybrid, electric
- drivetrain: fwd, rwd, awd (4x4/4WD/on-demand 4WD → awd; 2WD → fwd or rwd per layout)
- equipment category: Safety, Comfort, Technology, Exterior, Interior, Performance
  (the current frontend has no Performance tab — still allowed, the report warns)

## 8. Minimal example
```json
{
 "run": {"market": "KW", "code_mode": "test", "kuwait_dealer_url": "https://x.com.kw/en",
         "source_models": ["Outlander"], "excluded": []},
 "brand": {"code": "kw-mitsubishi", "name_en": "Mitsubishi", "name_ar": "ميتسوبيشي",
           "media": {"logo": "media/brand/logo.svg", "hero_video": "media/brand/hero.mp4"},
           "sources": ["https://x.com.kw/en"], "gaps": {"tagline_en": "no tagline published"}},
 "dealers": [],
 "models": [{
   "slug": "outlander", "name_en": "Outlander", "name_ar": "أوتلاندر", "model_year": 2026, "body_style_code": "suv",
   "kuwait_url": "https://x.com.kw/en/cars/outlander", "is_featured": true,
   "gallery": [{"file": "media/outlander/g01.jpg", "category": "exterior", "alt_en": "...", "alt_ar": "..."}],
   "source_trims": [{"name": "Base Line", "price": 7999, "source": "https://x.com.kw/en/cars/outlander"}],
   "trims": [{"slug": "base-line", "display_name_en": "Base Line", "display_name_ar": "بيس لاين",
              "starting_price": 7999, "horsepower": 181, "torque": 244, "fuel_type": "petrol", "drivetrain": "fwd",
              "seats": 5, "attributes": {"length_mm": 4720}, "equipment": [],
              "gaps": {"attr.zero_to_hundred": "brochure p13 says TBD"}}],
   "highlights": [], "sources": ["https://x.com.kw/en/cars/outlander"]
 }]
}
```
