# Per-brand source notes

What worked (and what bit us) per Kuwait dealer site. **Append a section after every run** — these notes are the
difference between a 45-minute run and a 15-minute one.

## Mitsubishi — mitsubishi-motors.com.kw (AEM/Apollo)
- All page data is in `window.__APOLLO_STATE__`: `scripts/page_state.py <page>.html --dump state.json`.
- Trims + prices: `TablesContainer…tableTabbed.products[]` (name, code, price). Per-trim equipment:
  `tableMixed.products[].detailedSpecifications[]` — an engineering list, in English even on `/ar` pages.
- Grade codes (`GM4WXTSCLW-GC_E30`) map to the brochure's column headers — that's how you tell which spec
  column belongs to which grade.
- Sub-pages `/cars/<model>/{drive,exterior,interior,safety,technology}` hold the marketing copy and most images.
- Brochures: `/en/download-a-brochure` → `/content/dam/.../brochure_files/<model>_<year>.pdf`. The 2026 books
  have a full TECHNICAL SPECIFICATIONS page but an EMPTY grade matrix for equipment.
- Brand pages: `/en/discover/{heritage,philosophy,innovation}`, `/en/owners/warranty` (5 years open mileage),
  `/en/dealer-locator` (Dealer_* objects in the page state carry address, phone, lat/long).
- The Kuwait homepage hero video is an XForce clip with faces — cut them out before using it as a brand hero.
- L200: the dealer site publishes no grade list; the 9 grades live in the brochure spec tables (pp. 19, 21).

## Genesis — genesis.com/kw
- The specs page is script-rendered; the data comes from Genesis's own read-only spec endpoints
  (`/wsvc/me/api/v2/spec/data`, `/specVehicle/data`, `modelCd=<code>`, `en-KW` / `ar-KW`) — per-trim specs AND
  standard features in both languages, which is where the Arabic equipment names come from.
- That spec data can be stale (2021, pre-facelift) while the Kuwait catalogue PDF shows the current car — prefer
  the catalogue/model page for equipment claims and drop conflicting items.
- Kuwait publishes one model-level "Starting MSRP" only (and the home grid can disagree with the model page).
- The Kuwait header logo is white-on-dark: usable as `logo_dark`, but a dark/colour logo must come from elsewhere.

## Changan — changankuwait.com
- No prices and no grade names published for some models; name the trim after the engine and mark it
  price-on-request.
- No Kuwait brochure, so drive type, top speed, 0-100, fuel economy, weight, boot volume and warranty are gaps.
- Kuwait spec numbers can disagree with Changan Qatar/Oman/UAE (e.g. 280 Nm vs 260 Nm) — Kuwait wins, flag it.
- Existing staging `changan` records contain specs that look invented and a Wikipedia-sourced logo — report, don't reuse.

## Honda — hondaalghanim.com (dealer) + honda-mideast.com (manufacturer, Kuwait locale)
- **Prices come from the DEALER, not the manufacturer.** honda-mideast.com has a Kuwait locale (`/en-kw`,
  `/ar-kw`) but its model data carries `"Show Price": false` and an empty price — no Kuwait prices at all.
  Honda Alghanim (hondaalghanim.com, the exclusive Kuwait distributor) publishes everything.
- **curl must use `--http1.1`** — HTTP/2 to hondaalghanim.com hangs until timeout. Occasional timeouts remain,
  so retry with a short backoff (a Python loop; the shell's `sleep` is blocked in this harness).
- Model pages `/en/automobiles/<slug>` (and `/ar/...`) are server-rendered and carry everything in one page:
  "Starting at" price, a spec strip (Engine / Engine Power / Fuel Consumption / Seats), the grade table
  ("Trim and Specs": grade name → "Starting at" → KWD price), colour swatches, feature sections
  (Exterior & Interior / Performance / Safety / Technology / Convenience) with title + paragraph, and a gallery.
  `/en/trim-level/<slug>` renders empty — ignore it.
- Grades: 7 of 9 models publish a grade table; **Accord Hybrid and Civic Type R publish none** (single price →
  single trim). Prices often carry a `*` with no stated condition.
- Only engine / power / fuel consumption / seats are published. **No dimensions, tank, kerb weight, top speed or
  0-100 for any model** — all legitimate gaps. Torque appears only inside Performance paragraphs for some models.
- Watch the spec strip: the HR-V prints "1500 cc" in the **Engine Power** field, and the City's strip (119 hp)
  disagrees with its Performance paragraph (121 hp). The City header teaser (4,999) is below its cheapest grade (5,049).
- Images: `dcjwldocnmeex.cloudfront.net/revamp/...`, referenced both directly and through `/_next/image?url=`
  (decode those). Filenames vary per model (`Gallery`, `Gallary`, `3gallery003`), so download everything and
  screen visually. Keep the URL extension when naming local files — truncating it breaks the uploader's mime check.
- Brand copy: dealer `/en/aboutus` + `/en/vehicle-warranty` (36 months / 100,000 km, transferable), showrooms
  (Al Rai, Shuwaikh, Fahaheel) on `/en/automobile-landing`, phone +965 1822777. History / Honda Sensing copy in
  EN **and AR** on honda-mideast.com `/en-kw/History`, `/en-kw/about-us`, `/en-kw/honda-sensing`.
- Clean Honda logo (red wordmark, transparent, 819×522):
  `edge.sitecorecloud.io/.../media/V2-Images/updated-img/HOnda-logo-resized-updt.png`. The dealer's own logo is a
  Honda+Alghanim lockup. The only Honda MP4 found (`.../Banner-Videos/bannervideo_lowres.mp4`) is full of faces.
- The Kuwait dealer does **not** sell the regular Civic (`/en/automobiles/civic` → 404) even though
  honda-mideast.com's Kuwait site lists a Civic MMC.
