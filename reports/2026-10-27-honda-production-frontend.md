# Frontend issues — Honda on production

**Reported by:** content team · **Date validated:** 2026-10-27 · **Environment:** production
`https://newcars.q84sale.com` · API `https://services.q84sale.com/api/v1/new-cars-catalog`

Context: brand `honda` (id 2027) was replaced in place with 9 models / 24 trims / 307 spec rows / 238 media
files. The API read-back passes every check, so everything below is rendering, not data. Each item was
reported on staging on 2026-09-22 and was still open at the 2026-09-24 retest; this confirms all four on
**production**, where the fuller content makes them much more visible than before.

Pages used: `/brand/honda`, `/model/820` (HR-V), in both languages (the language toggle is in the header;
`?lang=en` alone does not switch, and `/en/...` and `/ar/...` paths 404).

## 1. Brand editorial renders in English while the page is in Arabic

- **Where:** `/brand/honda` in Arabic
- **Shown:** "FOUNDED IN 1948", "The Power of Dreams", the whole heritage paragraph and the Honda SENSING
  innovation text, all in English, inside an otherwise Arabic page.
- **Data:** `story_ar`, `heritage_title_ar`, `heritage_description_ar`, `heritage_milestone_ar`,
  `innovation_title_ar` and `innovation_description_ar` are all populated and correct on brand 2027 — the
  API returns them.

## 2. Highlight slot labels are wrong

- **Where:** every model page, both languages
- **Shown:** on `/model/820` the third card ("A cabin built around space and airflow", slot `comfort`) is
  labelled **PERFORMANCE**, directly under a real `performance` card with the same label. In Arabic the
  first card's label renders as the English word "DESIGN" while the others are translated.
- **Data:** each card is imported with its own `section` + `slot`; the API returns the correct slot per card.

## 3. Hero stat tiles show "0" for values that do not exist

- **Where:** model page hero strip
- **Shown:** on `/model/820`, "0 s — Acceleration 0-100 km/h" and "0 km/h — Top speed".
- **Data:** the HR-V has no published 0-100 or top speed, so those attributes are absent. The full spec
  table on the same page handles it correctly ("غير متوفر" / not available) — only the hero strip prints 0.
  A zero acceleration figure on a live car page reads as broken.

## 4. Equipment names render in English in Arabic mode

- **Where:** model page equipment tabs, Arabic
- **Shown:** "Advanced Compatibility Engineering (ACE) body structure", "Hill Descent Control",
  "Electric parking brake with brake hold", "Rear seat occupant reminder", "LaneWatch camera".
- **Data:** every equipment item is imported with both `name_en` and `name_ar`.

## 5. Service links have no Arabic field

- **Where:** `/brand/honda` services section, Arabic
- **Shown:** "Find a showroom", "Book a service", "Vehicle warranty", "Current offers" in English.
- **Cause:** the stored `service_links` objects only carry `title`/`description`, with no `_ar` counterpart,
  so there is nothing for us to populate. Needs a schema change, not a content fix.

## Also worth knowing (API gaps, not rendering)

- **No delete route for model highlights.** `DELETE /v1/admin/trim-highlights/{id}` exists; there is no
  equivalent for model highlights. Seven cards from the July import sat in slots our six do not use, so the
  models showed 7-8 cards. We could only overwrite them (the import upserts by model + section + slot),
  not remove them — so model highlight counts cannot be reduced by anyone, through any endpoint.
- **A soft-deleted code is permanently unusable** — see the 2026-10-25 report. Confirmed again here.
- **`/import/attribute-values` appends instead of upserting** — see 2026-10-13. Still the reason spec
  imports have to be sequenced so carefully.
- Two legacy trims carried `starting_price: 0` (Accord Hybrid EX-L and Touring, ids 1004/1005) before we
  removed them. Worth checking other brands for the same.
