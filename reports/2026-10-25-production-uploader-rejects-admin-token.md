# Backend issues — production media uploader and delete/recreate semantics

**Reported by:** content team · **Date validated:** 2026-10-25 · **Environment:** production
API `https://services.q84sale.com/api/v1/new-cars-catalog`, uploader `https://services.q84sale.com/api/v1/presigned-uploader`,
login `https://admin-console.4sale.work/api/auth/login`

Context: preparing to replace the content of brand `honda` (id 2027) with a fully researched 9-model / 24-trim
import. Catalog writes work; media upload does not. **Blocked — we cannot host images on production.**

## 1. The production uploader rejects a valid production admin-console token (BLOCKER)

- **Where:** `POST /api/v1/presigned-uploader`
- **Token:** minted from `https://admin-console.4sale.work/api/auth/login` (user `admin`), 8h TTL, 3-segment JWT.
- **The same token is accepted by the catalog admin API:** `GET /v1/admin/attributes` → `200 {"success":true,...}`.
- **The uploader returns:** `401 {"error":"Invalid admin-console-token"}`

Header/convention variants all rejected, so it is not a convention mismatch — the service parses the header and
rejects the token's validity:

| Request | Response |
|---|---|
| `admin-console-token: <jwt>` + `Application-Source: q84sale` | `401 Invalid admin-console-token` |
| `admin-console-token: <jwt>`, no `Application-Source` | `401 Invalid admin-console-token` |
| `admin-console-token: <jwt>` + `Application-Source: 4sale` | `401 Invalid admin-console-token` |
| `admin-console-token: Bearer <jwt>` | `401 Invalid admin-console-token` |
| `Authorization: Bearer <jwt>` | `401 Invalid or expired token` |
| `x-admin-console-token: <jwt>` | `401 Authorization header or admin-console-token is required` |
| no token | `401 Authorization header or admin-console-token is required` |

`admin-console.4sale.work` is the only admin console that resolves; `admin-console.q84sale.com`,
`admin.q84sale.com`, `console.q84sale.com`, `admin-console.4sale.com`, `admin-console-prod.4sale.work`,
`prod-admin-console.4sale.work`, `console.4sale.work` and `newcars-admin.4sale.work` do not.

**Likely related:** every media reference on the existing production `honda` brand (logo, hero) is served from
`https://staging-raw-images.q84sale.com/...`, i.e. production content pointing at staging storage. If whoever
built that brand hit this same wall and uploaded through staging, that would explain it. It is fragile either
way — on 2026-10-25 the staging catalog API and admin console were returning 504 while that media was still
being served from staging.

**What we need:** which credential the production `presigned-uploader` accepts (service account, different
console, or a role/permission on the `admin` account), or confirmation that production media is supposed to be
uploaded by some other route.

## 2. Soft-deleted codes are permanently unusable (delete-then-recreate is impossible)

- **Where:** `DELETE /v1/admin/trims/{id}` followed by `POST /v1/admin/import/trims`
- **Reproduced on:** trim 1012 `honda-pilot-trailsport`

```
DELETE /v1/admin/trims/1012            -> 200 {"status":"deleted"}   (gone from the public list)
POST   /v1/admin/import/trims          -> 200 {"created":0,"updated":0,"failed":1,
   [{"variant_code":"honda-pilot-trailsport", ...}]    "errors":[{"code":"honda-pilot-trailsport",
                                                         "message":"Error 1062 (23000): Duplicate entry ..."}]}
```

The soft-deleted row keeps its `variant_code` in the unique index, so the importer can neither update it (it is
filtered out as deleted) nor insert a new row. **The code is burned.** A raw MySQL error reaching the API
response is itself worth fixing; the behaviour needs a decision (exclude `deleted_at` rows from the unique
index, or have the importer revive a soft-deleted row).

This matters well beyond trims: `DELETE /v1/admin/brands/{brandId}` is documented as soft-deleting the brand
with its models, trims and packages. If the same index behaviour applies there, **deleting a brand and
re-importing it under the same code is unrecoverable** — the brand, every model code and every trim code would
be burned at once. We had been asked to delete and replace brand `honda` and did not, which now looks like the
right call; please confirm before anyone does it to another brand.

**Workaround we verified** (no fix needed from you, recorded for the next person):
`PATCH /v1/admin/trims/{id} {"variant_code": "<code>-legacy-YYYYMM", "slug": ...}` → `DELETE` it → the original
code imports cleanly as a new row. Verified end to end on trim 1007 `honda-cr-v-lx` (recreated as id 1290).

## 3. Still open from 2026-10-13 — `/import/attribute-values` appends instead of upserting

Unchanged and still relevant: re-importing specs onto an existing trim duplicates every row, and no endpoint
deletes an attribute value. With item 2's workaround we can now avoid it by recreating the trim instead, but
the underlying bug is what forces that dance.

## 4. Minor — dead link in the live brand's service links

`service_links[0].href` on brand 2027 is `https://www.hondaalghanim.com/en/showrooms` → **404** as of
2026-10-25. The dealer's live equivalent is `/en/contact`. Our import replaces all four links with verified
ones, so this fixes itself when we publish, but any other brand configured the same way should be checked.

## Changes we made to production while validating

Only the two trims below, both on the agreed delete list, and nothing else — no brand fields, no imports, no media:

| Trim | Action | Net result |
|---|---|---|
| 1012 `honda-pilot-trailsport` | deleted, then re-import attempted (failed 1062) | removed; code burned |
| 1007 `honda-cr-v-lx` | renamed → `honda-cr-v-lx-legacy-202607`, deleted, recreated as 1290, 1290 deleted | removed; code burned |

Neither code is used by our import (ours are `honda-pilot-sport` and `honda-cr-v-lx-2wd`). Brand 2027 is
untouched and still `active` with its original editorial. Pre-change snapshot: `honda-prod/backup/`.
