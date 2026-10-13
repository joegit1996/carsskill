# Catalog API, auth and known gotchas

**Check the swagger before you act.** `/Users/joe/new_cars/docs/swaggerv2.json` is the contract: before using an
endpoint, claiming one doesn't exist, or deciding a field can't be set, open it and look. Grep the paths and the
request schema for the operation you need (`python3 -c "import json;d=json.load(open('swaggerv2.json'));print([p for p in d['paths'] if 'trim' in p])"`).
Several wrong turns in past runs came from assuming: that only `/import/*` could write, that PATCH could fix
attribute values, that dealer fields existed on the brand. The swagger answers all three in seconds. Where the
swagger and reality disagree (it happens — see the attribute-values row below), trust the live API and report the
mismatch.

- Catalog API: `https://staging-services.q84sale.com/api/v1/new-cars-catalog` (Swagger:
  `/Users/joe/new_cars/docs/swaggerv2.json`). Public reads need header `Application-Source: q84sale`.
- Admin writes: `/v1/admin/import/*` with headers `admin-console-token: <JWT>` + `Application-Source: q84sale`.
- JWT: `scripts/get_jwt.py` (staging credentials are in `/Users/joe/new_cars/docs/uploader-guide.md`, Step 1).
  8-hour TTL — re-run it for long sessions.
- Uploader: `https://staging-services.q84sale.com/api/v1/presigned-uploader` — see uploader-guide.md.
  Rate-limits around 5 req/s per token; `upload_media.py` throttles and retries 429s.

## Import order (import_catalog.py does this)
brands → dealers → models → trims → attribute-values → trim-hero-stats → equipment → model-highlights

## Gotchas (all hit in real runs)
| Gotcha | Handling |
|---|---|
| `/import/*` are FULL-RECORD upserts: omitted fields get nulled | always send the whole record (the script rebuilds from content.json) |
| Backend may store codes differently (`-kw` suffix, doubled brand prefix when name_en contains the brand) | script reads stored codes back and uses them for children; keep brand out of `name_en` |
| Nested `specs` on the trim payload is silently dropped | deep specs go to `/import/attribute-values` (script does this from `attributes`) |
| `/import/equipment` replaces the trim's entire list | one call per trim with all categories |
| Posting attribute values of 0/null pollutes the DB | script skips them |
| Re-importing models resets `is_featured` if you omit it | script always sends it from content.json |
| `price_on_request=false` with `starting_price=0` renders "0 KWD" | never send 0; script derives both from trims |
| Default trim is trim[0] on the FE | script sorts cheapest priced first and sets `is_default` |
| `/browse` is cached for minutes | verify via `/v1/public/models/<id>` (verify_staging.py does) |
| Staging FE returns occasional 504 | retry after a few seconds |
| trim-hero-stats `title_ar` | real Arabic is accepted now (the old latin1 limit is fixed) |
| **`/import/attribute-values` does NOT upsert** (despite its swagger description) | re-posting the same `(owner_type, owner_code, attr_code)` **adds another row**, even with an identical value, so a trim ends up showing a spec twice in `trim.attributes[]` (`trim.specs` keeps only the latest). **Get a trim's attributes right the first time.** If you must change one, expect a duplicate and say so in the run summary. Reported 2026-10-13 in `/Users/joe/newcars code/reports/`. |
| No way to replace or delete an attribute value | `PATCH /v1/admin/trims/{id}` has no attributes field (top-level trim fields only); `POST /v1/admin/models/{id}/attributes` is model-scoped; the undocumented `POST /v1/admin/trims/{id}/attributes` returns `{"status":"set"}` but **also appends**. The only clean-up is deleting and re-creating the trim — which also drops its equipment and hero stats, so ask the user first. |
| `/import/trims` upserts correctly | re-importing trims returns `updated: N` — safe to re-run, unlike attribute values |

## Useful public endpoints for verification
`/v1/public/brands`, `/brands/{id}`, `/brands/{id}/editorial`, `/brands/{id}/models`, `/brands/{id}/dealers`,
`/models/{id}`, `/models/{id}/trims`, `/models/{id}/branches`, `/trims/{id}/equipment`.
