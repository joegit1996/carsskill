# Sources & research — how to get complete, correct data

## Source priority (cite what you used in `sources`)
0. **Find the right site first.** The manufacturer's regional site and the Kuwait distributor's site are
   different animals. Honda's own Kuwait locale publishes **no prices at all** (`"Show Price": false`), while the
   distributor (hondaalghanim.com) publishes every grade and price. Check both before concluding a brand has no
   published prices; the dealer is usually named on the manufacturer's "dealer/contact" page.
1. **Kuwait dealer site** (model pages, trim/price tables, spec tables) — prices and grade names come ONLY from here.
2. **Brochure PDFs** — the best source for specs, and often the ONLY source for dimensions, tank, kerb weight and
   sometimes transmission. Look on both the dealer site and the manufacturer site (Honda's GCC brochures filled
   nine models' dimensions plus the Pilot's 10-speed auto, the Type R's 6-speed manual and the Accord Hybrid's
   torque, none of which the dealer printed). Brochure spec tables are per-grade: find the page with
   `pdftotext -layout` + keywords ("Wheelbase", "Fuel Tank", "Kerb Weight"), then render it
   (`pdftoppm -f N -l N -r 150 -png`) and read it before trusting a regex.
   **Mapping brochure grades to dealer grades:** only safe when the names match. Otherwise apply figures that are
   identical across all brochure grades, or that split cleanly along a dimension you do know (CR-V: 2WD vs 4WD
   heights). Leave per-grade figures you cannot map (Pilot/Odyssey kerb weights) as gaps. Note the brochure
   name/year in the trim metadata, especially when it is a regional edition (a UAE City brochure for a Kuwait car).
3. Regional GCC/ME manufacturer site (.ae, .sa, .bh, .om, .qa).
4. Global manufacturer press/media site.
5. Trusted editorial (Motor Trend, Car and Driver, Autocar, drivearabia) — last resort, note it in `metadata`.

**Never Wikipedia/Wikimedia**, not even inside a `_note`. If nothing official publishes a value → leave it
empty and add a `gaps` reason. A wrong number is worse than a dash.

## Step-by-step research for one brand
1. **Lineup:** open the KW site navigation/"All vehicles" page. Record every model name in `run.source_models`
   (with price if shown). This is the denominator for model coverage — don't skip models you plan to exclude,
   exclude them with a reason instead.
2. **Per model page:** save EN and AR HTML to `<workdir>/sources/`. Many dealer sites are JS apps that ship the
   data inside the HTML — run `scripts/page_state.py page.html` before scraping visible text. It extracts
   `__APOLLO_STATE__` (AEM sites like Mitsubishi KW), `__NEXT_DATA__`, `__NUXT__`, JSON-LD.
   Use `--grep "<grade name>"` to find where trims/prices live.
   If a page is empty without JS or returns 403/Cloudflare, use the Playwright browser tools.
3. **Grades & prices:** record every grade in `source_trims`. Price = the dealer's "From KWD x" per grade.
4. **Sub-pages:** Exterior/Interior/Drive/Safety/Technology sub-pages carry the marketing copy (for highlights +
   description) and most of the gallery images.
5. **Brochure:** find the brochure link (often `/download-a-brochure` → `.../brochure_files/<model>_<year>.pdf`).
   `pdftotext -layout` the spec page. When per-grade columns are ambiguous, render the page
   (`pdftoppm -f N -l N -r 200 -png`) and read it — column headers (grade codes like GM4WXTSCL) map to the
   dealer's grade codes, which tells you which column is which trim.
6. **Brand pages:** home (hero video), heritage/history, philosophy, innovation/technology, warranty, contact,
   dealer locator (showroom addresses, phones, coordinates are often in the page state JSON).

## Cross-checking (accuracy)
- Every value must be **published in text** by an official source. Never infer a value from a photo, a render or
  "it's obviously a 5-seater" — if the seat count, drivetrain or model year isn't stated anywhere official, it's
  a gap with a reason. An empty field renders as a dash; an invented one is a defect users will see.
- **Kuwait wins for Kuwait.** When the Kuwait dealer publishes a value, it is the value we import, even if the
  Qatar/Oman/UAE/Saudi sites disagree (a regional figure is a different spec, not a correction). Record the
  discrepancy in `metadata._conflict` and mention it in the final report so the dealer can confirm.
  Regional/global sources are for fields Kuwait does not publish at all — note the source in the trim metadata.
- When two Kuwait sources disagree (dealer product card vs dealer spec table vs brochure), prefer the more
  specific and more recent one (a per-grade spec table or the current brochure beats a summary card), and record
  the conflict. Sanity-check the loser: a lone 280 Nm against 260 Nm everywhere else is likely a typo, and
  saying so in the report is more useful than silently picking one.
- Convert units, don't estimate: kW × 1.341 = hp (round), PS × 0.986 = hp, lb-ft × 1.356 = Nm. Note conversions.
- Displacement: attribute `displacement` is in litres (2,488 cc → 2.5).
- Shared specs (length, wheelbase) may apply to all grades; per-grade values (height with bigger wheels, ground
  clearance, seats) must be mapped column-by-column.
- Brochure equipment matrices can be EMPTY (Mitsubishi KW 2026: no grade markers). Don't infer per-grade
  equipment from global marketing — use the dealer's per-trim spec table instead.
- **Read the grade-conditional wording.** Dealer feature text often qualifies a feature: "all grades except the
  LX", "only on the Touring", "EX and Touring". Grep the saved text for `except|only on|all grades|and above`
  before assigning equipment — a feature put on every grade when the page excludes one is a real error that the
  coverage gate cannot catch.
- Marketing sub-pages are often global copy: they describe features (12.3" screen, HUD, sunroof, S-AWC) that
  the Kuwait grades may not have. Only claim a feature in highlights/description if the Kuwait spec data shows
  it on at least one grade (and say which grade when it's not standard).

## Equipment: turn spec-sheet lines into customer items
Dealer spec tables are often engineering lists ("Engine coolant : Standard", "Air cleaner element : no woven
cloth made"). Map the meaningful lines to customer-facing items with a small rules table
(`match substring → category, name_en, name_ar`), apply it per trim, and drop the noise. Aim for 5–10 items
per category per trim. Author the Arabic yourself — dealer AR pages often leave spec tables in English.
Keep one call per trim (the endpoint replaces the trim's whole list).

## Coverage targets
- 100% of official models and grades imported or excluded with a reason.
- ≥ 90% of expected fields filled wherever the sources publish them (see `coverage_report.py`).
- Gallery 18–20 distinct images per model (≥ 13 visible after hero/highlight de-dupe). If the dealer site runs
  short, `pdfimages -j` the brochure — it often holds extra face-free shots.
- Typical legit gaps: 0–100 and fuel economy "TBD" in GCC brochures, curb weight (only GVW published), luggage litres.
- **Prices:** when the dealer publishes only a model-level "Starting from KWD x", assign it to the entry (lowest)
  grade and leave the others price-on-request, noting it in that trim's metadata. Otherwise every trim tab shows
  "Price on Request" while the model shows a price, which looks broken. If the price is a promotion
  ("back-to-school offer"), say so in the metadata.
- **Critical fields can't be waived:** brand logo + brand hero, model hero image, ≥ 13 gallery images after
  de-dupe, 6 highlight cards, and EN/AR names. A `gaps` reason does not excuse them — find another source
  (global press pool, brochure images via `pdfimages -j`, a different logo file).

## Before you start: what already exists on staging
Check `/v1/public/brands` for the same make under ANY code (e.g. an old `genesis` next to your `kw-genesis`),
and read that brand's models/trims. You are not there to fix it, but you should:
- avoid overwriting anything that isn't ours (only `kw-` codes are ours in test mode),
- reuse nothing from it blindly — earlier imports contain wrong specs and Wikipedia-sourced logos,
- list what looks wrong (duplicate trims, prices of 0, impossible dimensions, banned-source logos) in the final
  report so the owning team can clean it up.
