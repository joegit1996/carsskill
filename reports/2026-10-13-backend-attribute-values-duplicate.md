# Backend issue — `/v1/admin/import/attribute-values` duplicates instead of upserting

**Reported by:** content team · **Found:** 2026-10-13 · **Environment:** `https://staging-services.q84sale.com/api/v1/new-cars-catalog`

## What the API promises
The swagger description for `POST /v1/admin/import/attribute-values` says:

> Upserts attribute values by owner code + attribute code

## What happens
Posting the same `(owner_type, owner_code, attr_code)` a second time **creates a second row** instead of updating
the existing one. The response reports them as created, never updated.

**Repro (what we did):**
1. Imported `kw-honda` trims and attribute values — response `{"created": 156, "updated": 0, "failed": 0}`.
2. Later enriched the same trims with dimensions and re-posted the full attribute set for each trim — response
   `{"created": 298, "updated": 0, "failed": 0}`. Every previously-sent code was sent again with the same
   `owner_code` and `attr_code`.
3. `GET /v1/public/models/1379/trims` now returns each of those attributes **twice** in `attributes[]`, with the
   old and new values side by side:

```
('displacement', 1.5)   ('displacement', 1.498)
('horsepower', 194)     ('horsepower', 194)
('warranty', '3 years / 100,000 km')  ('warranty', '3 years / 100,000 km')
```

Duplicates appear even when the value is byte-identical (see `warranty`), so this is a plain insert, not a
"new value → new row" behaviour.

**Scope observed:** 24 of 24 `kw-honda` trims, 6–8 duplicated attribute codes each. `kw-mitsubishi` (imported
once, never re-imported) has none — consistent with the duplication coming from the second post.

## Impact
- `trim.specs` (the flattened object the model page reads) shows only the latest value, so the page looks
  correct today.
- `trim.attributes[]` carries both rows, so anything reading that array — compare tables, "view all
  specifications", exports — can show a spec twice, with two different values.
- Any corrective re-import makes it worse, since each run adds another row. We have stopped re-posting
  attribute values for this brand until this is resolved.

## Other write paths we tested (none fix it)
| Route | Result |
|---|---|
| `PATCH /v1/admin/trims/{trimId}` | Works, but `UpdateTrimInput` has **no attributes/specs field** — it only covers top-level trim fields (horsepower, torque, transmission, price, …). It cannot touch attribute values. |
| `POST /v1/admin/import/trims` | Upserts correctly — our re-import returned `{"created": 0, "updated": 24}`. Only attribute values misbehave. |
| `POST /v1/admin/models/{modelId}/attributes` | Documented as "sets or updates an attribute value" — but it is **model-scoped**; there is no documented trim equivalent. |
| `POST /v1/admin/trims/{trimId}/attributes` (undocumented; GET returns 405, so the route exists) | Accepts `{attribute_definition_id, value_json}` and returns `{"status":"set"}` — but it **also inserts a new row** instead of replacing. Testing it on trim 5233 (`kw-honda-accord-1-lx`, displacement) left three rows: `1.5, 1.5, 1.498`. |

So every available write path adds rows; none replaces them. The only cleanup route we can see is deleting and
re-creating the trim.

## What we need
1. Make the endpoint upsert on `(owner_type, owner_code, attr_code)` as documented.
2. A way to clean up existing duplicates — either a dedupe on your side, or a documented delete for attribute
   values (swagger currently has no delete for them; the only route we found was deleting and re-creating the
   whole trim).

## Note
We can delete and re-create the 24 `kw-honda` trims to clear this if you prefer, but that also removes their
equipment and hero stats until we re-import, so we would rather not do it on a schedule you do not control.
