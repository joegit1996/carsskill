# Frontend issues — staging-newcars.q84sale.com

**Reported by:** content team (found during the `kw-mitsubishi` test import)
**Date validated:** 2026-09-22
**Environment:** https://staging-newcars.q84sale.com, API `https://staging-services.q84sale.com/api/v1/new-cars-catalog` (header `Application-Source: q84sale`)

Every issue below was checked on the live staging site against the public API, using established brands as controls. In each case the API returns the correct data and the page does not display it correctly, so these are frontend problems, not data problems.

Test records used: brand `kw-mitsubishi` (id 3120), model `kw-mitsubishi-outlander` (id 1375, trims 5218–5221).

---

## 1. Brand editorial stays English in Arabic mode
- **Where:** brand page → Heritage, Technology & Innovation, and Sustainability sections
- **Repro:** open https://staging-newcars.q84sale.com/brand/toyota → click **AR**
- **Expected:** heading and text in Arabic (API `/v1/public/brands/1998` returns `heritage_title_ar` = "تأسست عام 1937", `innovation_title_ar`, `sustainability_ar`, etc.)
- **Actual:** the site menus switch to Arabic, but these sections stay English ("FOUNDED IN 1937", English paragraphs)
- **Also seen on:** `/brand/kw-mitsubishi`, `/brand/kw-soueast`

## 2. Equipment section is empty on the model page
- **Where:** model page → "Equipment."
- **Repro:** https://staging-newcars.q84sale.com/model/1375 (any trim)
- **Expected:** equipment by category. `/v1/public/trims/5218/equipment` returns 41 items (Comfort, Exterior, Interior, Performance, Safety, Technology), and Full Option (5221) returns 57
- **Actual:** only "No differences from base trim in this category." None of the item names appear anywhere on the page, in either toggle mode
- **Also seen on:** `/model/1374` (kw-soueast S06, 48 items in the API)
- **Note:** across all 512 staging models, only these two have equipment data, so there is no working example to compare against. The API side is confirmed correct.

## 3. Brand hero video plays on the model page instead of the model's own hero
- **Where:** model page hero
- **Repro:** https://staging-newcars.q84sale.com/model/1375
- **Expected:** the Outlander hero image (model `hero_media` = image; each trim `hero_media` is also set to the image)
- **Actual:** the brand's video plays (an XForce clip), so the Outlander page shows a different car
- **Also seen on:** `/model/768` (Porsche 911) and `/model/644` (Toyota Camry) also play their brand video instead of the model image
- **Question:** if this is intended, please confirm. For brands with a generic brand video, it shows the wrong car on model pages.

## 4. Missing values shown as 0, and petrol cars labelled "Electric"
- **Where:** model page (hero stats, "Performance/Design/Efficiency" copy, compare table, specifications) and the trims listing
- **Repro:** https://staging-newcars.q84sale.com/model/1375 and `/model/1375/trims`
- **Expected:** missing values shown as "—" or hidden, and fuel shown according to `fuel_type`
- **Actual:**
  - "0s" for 0–100 km/h (the API returns `zero_to_hundred: null`), plus "0kg", "0L of cargo space"
  - "EFFICIENCY — Zero emissions. Pure electric power." and "Fuel Economy: Electric" for all 4 trims, although `fuel_type` = `petrol` and the same page shows a "Petrol" chip. It happens when `fuel_economy_combined` is missing.
  - The trims listing (`/model/1375/trims`) labels every trim "Electric" and "0s 0-100"
- **Control:** `/model/1374` (has fuel economy) shows "7.3 L/100km" correctly, but still shows "0s", "0 km/h", "0kg" for its missing values

## 5. Model highlight cards from the API are not shown
- **Where:** model page → Highlights
- **Repro:** https://staging-newcars.q84sale.com/model/768
- **Expected:** the API cards (`/v1/public/models/768` → `highlights.parallax/featured`, e.g. "Six Decades, One Silhouette", "Flat-Six Twin-Turbo", "8-Speed PDK")
- **Actual:** none of the API card titles appear; the section shows auto-generated text instead
- **Also seen on:** `/model/644` (Camry), `/model/1375` (6 cards imported)

## 6. Dealers/branches not shown under "Authorized Branches"
- **Where:** model page → "Authorized Branches."
- **Repro:** https://staging-newcars.q84sale.com/model/817 (GMC Acadia)
- **Expected:** the branch returned by `/v1/public/models/817/branches` ("Behbehani Automotive - GMC", 1884411)
- **Actual:** only the heading and generic text; no branch listed
- **Also seen on:** `/model/1375`, whose branches endpoint returns "Mitsubishi Motors Showroom - Al Rai"

## 7. Brand story not displayed
- **Where:** brand page
- **Repro:** https://staging-newcars.q84sale.com/brand/toyota
- **Expected:** `story_en` / `story_ar` from the API ("Toyota Motor Corporation has built one of the broadest vehicle ranges…")
- **Actual:** not displayed anywhere on the page
- **Question:** if this is by design, which field should brand story content go into?

## 8. "View Details" trim links open the base trim
- **Where:** trims listing → "View Details"
- **Repro:** https://staging-newcars.q84sale.com/model/644?trim=4629 (Camry GLE)
- **Expected:** the selected trim (GLE)
- **Actual:** the page opens on the base trim ("Full technical specifications for the Camry E trim"); `?trim=` is ignored. Also on `/model/1375?trim=5221`, where the page shows the 7,999 base price instead of 12,200
- **Note:** clicking the trim tab on the model page works correctly

## 9. Toyota brand page shows no models
- **Repro:** https://staging-newcars.q84sale.com/brand/toyota
- **Actual:** "No models match your filters", although the API lists Toyota models (e.g. `/model/644`)
- **Note:** observed only; the cause was not investigated

---

## Backend note (not a bug)
`/v1/admin/import/trim-hero-stats` now accepts real Arabic in `title_ar`. The brand-import checklist still says the column is latin1, so the checklist can be updated.
