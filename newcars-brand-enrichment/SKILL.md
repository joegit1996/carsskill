---
name: newcars-brand-enrichment
description: Enrich a car brand on the 4Sale New Cars (q84sale) staging catalog end-to-end for the Kuwait market - research every model and trim from official Kuwait sources (dealer site + brochure), author bilingual EN/AR content, screen and upload media through the presigned uploader, import brand/dealers/models/trims/specs/equipment/highlights, score coverage against the brand-import checklist, verify on staging and report frontend/backend issues. Use this whenever the user wants to add, import, upload, enrich, complete or fill in a brand, model, lineup or trims on New Cars / staging-newcars, mentions a Kuwait dealer site (e.g. mitsubishi-motors.com.kw) as a source, asks for kw- test imports, or wants coverage/accuracy of catalog content improved - even if they only name the brand ("do Changan", "add the L200").
---

# New Cars brand enrichment

Turns "enrich <brand>" into a complete, verified, bilingual brand on staging with a measurable coverage score.
The judgment-heavy work (research, choosing images, writing EN/AR copy) is yours; the repeatable work is done
by the bundled scripts, which all read one file: `<workdir>/content.json`.

**Our role:** content agents. We upload content and *report* frontend/backend issues — we never modify code
in `/Users/joe/new_cars` (it's outdated and owned by others). All files we create go under
`/Users/joe/newcars code/` — never into `/Users/joe/new_cars`.

Scripts live in `scripts/` next to this file (call them with `python3 <skill-dir>/scripts/<name>.py`).

## Setup (first run on a new machine)
- **Python 3** (stdlib only for the API scripts). `media_screen.py` needs **Pillow**; video work needs **ffmpeg/ffprobe**;
  brochures need **poppler** (`pdftotext`, `pdftoppm`, `pdfimages`, `pdfinfo`).
- **Credentials** for the staging admin console: `scripts/get_jwt.py --workdir <dir> --user … --password …`, or
  env `NEWCARS_ADMIN_USER` / `NEWCARS_ADMIN_PASS`. The staging pair is documented in the project's
  `docs/uploader-guide.md`.
- **Reference docs this skill cites** (paths as on the original machine; point to your copy if they differ):
  `/Users/joe/new_cars/docs/swaggerv2.json` (API contract — always check it), `docs/uploader-guide.md`,
  `docs/content-upload-guide.md`, and the brand-import checklist. Everything the scripts need at runtime is in
  this skill; those docs are for cross-checking.
- **Where files go:** one workdir per brand (`<brand_code>/`) holding `sources/`, `media/`, `content.json`,
  `payloads/`. Nothing is written outside it except reports.
- Some shells block `sleep`; the scripts use Python timers instead. `curl` may need `--http1.1` for dealer sites.

## Before you start (ask once, then run end-to-end)
1. **Code mode — ask the user:** `test` (codes prefixed `kw-`, e.g. `kw-changan`, `kw-changan-cs75-plus`) or
   `real` (production codes). Record it in `run.code_mode`. Display names never carry the prefix.
2. Scope: whole brand, or specific models? (Default: every model on the Kuwait lineup.)
3. Workdir: `/Users/joe/newcars code/<brand_code>/` with `sources/`, `media/`, `payloads/`.
4. Check staging for this make under ANY code (`/v1/public/brands`), not just yours. Imports are full-record
   upserts — if your code exists you will overwrite it; in `test` mode that's fine for our own `kw-` data,
   anything else needs the user's OK. Note (don't fix) anything wrong in the existing records for the report.
   Also check `references/brand-notes.md` for this brand — it may already tell you where the data lives.
5. Read `references/api-and-gotchas.md` once; get a token: `scripts/get_jwt.py --workdir <dir>`. **Check the
   swagger (`/Users/joe/new_cars/docs/swaggerv2.json`) before using or ruling out any endpoint** — it settles
   what can be written and with which fields, and it is faster than guessing.

After these answers, the run is **fully automatic through import and QA** — don't pause for approval unless
something needs a decision only the user can make (e.g. overwriting non-kw data, a source conflict you
can't resolve from official material).

## Workflow

### 1. Enumerate the lineup (the denominator for coverage)
Open the Kuwait dealer site's model navigation. Put **every** model into `run.source_models` and, per model,
every grade into `source_trims` **with the price the dealer prints for it**. Anything you won't import goes into
`run.excluded` / `excluded_trims` with a reason. This is what makes "100% of models and trims" checkable — and
`price_audit.py` re-checks it against the saved pages, so a self-reported list won't quietly pass.
Save every page you read into `<workdir>/sources/` (HTML, page-state JSON, brochure PDF): the audit can only
verify what was saved.

### 2. Research each model (in series, save as you go)
Follow `references/sources-and-research.md`. Per model: EN + AR model pages and sub-pages, the Kuwait brochure
spec page, per-grade price and equipment. Use `scripts/page_state.py` on saved HTML — dealer sites often hide
all their data in embedded JSON. Write into `content.json` after each model so a long run never loses work.
Research runs in series: the Playwright browser is shared and parallel agents collide.

Accuracy habits that matter most:
- prices and grade names only from the Kuwait dealer; specs from the Kuwait brochure first
- map per-grade brochure columns via grade codes, not by guessing order
- convert units exactly (kW × 1.341 → hp) and note it; never estimate a missing value — add a `gaps` reason
- every value must be published in text: never read a spec off a photo or assume the obvious (seats, model year)
- **Kuwait beats the region:** when the Kuwait dealer publishes a figure, import it even if Qatar/Oman/UAE/Saudi
  disagree; record the difference in `metadata._conflict` and raise it in the final summary
- a model-level "Starting from" price belongs on the entry grade, not nowhere
- only claim features in highlights/descriptions that the Kuwait grades actually have

### 3. Media
Follow `references/media-rules.md`: download → `media_screen.py dupes` → `media_screen.py sheet` and **look**
(no faces in gallery/highlight imagery — hero banners and hero videos may show people — current MY, no UI
screenshots/diagrams) → `shrink` → order gallery (hero first) → pick 6 distinct
highlight images. Hero video only as a downloadable MP4; cut out any face segments with `media_screen.py cut`.

### 4. Author content.json
Schema and field notes: `references/content-schema.md`. Arabic: `references/arabic.md` — every `_ar` field is
authored Arabic, never a copy of the English. Highlights: exactly 6 per model, paraphrased from that model's
official page. Equipment: customer-facing items mapped from the dealer's per-trim spec list.

### 5. Coverage gate + trim/price audit
```
python3 scripts/coverage_report.py --workdir <dir>
python3 scripts/price_audit.py     --workdir <dir>     # checks trims/prices against the SAVED sources
```
The audit is the one that protects grade and price accuracy, because it re-reads `sources/` instead of trusting
what the research wrote down. It fails when an imported grade name or price is absent from the sources, when the
price printed next to a grade doesn't match the one imported, or when a grade is marked price-on-request although
the site prices it; it also lists prices that appear in the sources but sit on no trim (usually a missed grade).
Resolve every finding, or explain it in the run notes — a page that prints all grade prices in one block can
produce a nearby-price false positive, so open the source and confirm before changing data.

Gate = model/trim enumeration 100%, ≥ 90% field coverage at brand/model/trim level (justified gaps excluded
from the denominator), and zero errors. If it fails: research the missing fields; if a value genuinely isn't
published, add a specific `gaps` reason ("brochure p13 lists 0-100 as TBD") — never fill with a guess to pass.
Critical fields (brand logo + hero, model hero, ≥ 13 gallery images after de-dupe, 6 highlights, EN/AR names)
can't be waived with a reason — go and find them. The report also shows raw coverage (every expected field
counted); mention both numbers to the user, since "100% with justified gaps" can still be 75% of fields filled.
Don't import until the gate passes.

### 6. Upload and import
```
python3 scripts/upload_media.py   --workdir <dir>            # de-dupes by md5, verifies every URL
python3 scripts/import_catalog.py --workdir <dir> --dry      # writes payloads/ for a last look
python3 scripts/import_catalog.py --workdir <dir>            # posts in order, verifies stored codes
```
If a stage fails, fix `content.json` and re-run just that stage with `--only <stage>`. One exception:
**`attributes` is not safely re-runnable** — the backend appends instead of upserting attribute values, so a
second run leaves duplicates (see `references/api-and-gotchas.md`). Get the specs right before the first import;
if you do have to re-post, tell the user it will duplicate.

### 7. Verify and QA
```
python3 scripts/verify_staging.py --workdir <dir>
```
Then visual QA in the browser (EN and AR) per `references/qa-and-reporting.md`. For anything wrong: check the
API first; if the API is right, reproduce on an established control brand before calling it a frontend issue.
New issues go into a report in `/Users/joe/newcars code/reports/` (format in the reference). Known issues are
listed there too — don't re-report them as new.

### 8. Tell the user
Finish with a short summary:
- links: brand page + each model page
- coverage table from `coverage.md` (enumeration %, brand/model/trim %) and the justified gaps
- source conflicts and the decisions taken (especially Kuwait vs regional figures the dealer should confirm)
- verification result, and any new issues reported (path to the report), including problems spotted in
  pre-existing catalog records
Then append what you learned about this brand's sources to `references/brand-notes.md`.

## Dry run
If the user asks for a dry run / preview / "don't post anything": do steps 1–5 (including `price_audit.py`),
then `import_catalog.py --dry` (no uploads, no posts) and report coverage, audit findings and where the
payloads are.
