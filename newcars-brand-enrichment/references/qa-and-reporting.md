# QA on staging and issue reporting

We are content agents: we upload content and **report** frontend/backend problems. We never edit the
frontend/backend code (`/Users/joe/new_cars/app` is outdated and owned by other teams — don't cite its source
lines as proof of deployed behaviour).

## 1. API read-back
`scripts/verify_staging.py --workdir <dir>` → `verify.md`. Fix every data failure (re-run
`import_catalog.py --only <stage>`), then re-verify.

## 2. Visual QA (browser tools), EN and AR
For `https://staging-newcars.q84sale.com/brand/<code>` and each `/model/<id>`:
- logo visible in the round avatar; brand hero plays/loads; heritage + innovation sections present
- featured models show image + price; model hero loads; gallery has photos; trim tabs switch price/specs
- no `null`, `undefined`, `N/A` in the page text (`get_page_text`)
- toggle **AR** (top-right) and repeat — note that the language is not persisted across navigation, so
  toggle again after each page load
Grab facts with `javascript_tool` (e.g. which `<video>` src plays, whether a text string is present) rather
than eyeballing screenshots.

## 3. Is it our data or the frontend? — validate before reporting
For every problem:
1. Check the API: does the public endpoint return the correct value? If not → it's our data (fix it) or a
   backend bug (report it).
2. If the API is correct, find a **control**: an established brand/model that has the same kind of data
   (e.g. a brand with a video hero + image model hero, a model with highlights, a model with branches).
   Confirm the control has the data in the API first — a control without the data proves nothing.
3. Same wrong behaviour on the control → frontend issue, report it. Correct on the control → look at our data again.

Known frontend issues after the 2026-09-24 retest (reports in `/Users/joe/newcars code/reports/`):
**still open** — brand editorial (heritage/innovation/sustainability) stays English in AR mode; brand `story_*`
is never rendered; highlight slot labels are wrong/untranslated (the comfort card reads "Performance");
equipment names render in English in AR although `name_ar` exists; the AR specifications section corrupts the
engine string ("4 أسطواناتinder"); the "Performance" equipment category has no tab.
**fixed** — equipment renders, model hero image is used (no brand-video fallback), missing values render "—",
imported highlight cards render, branches show, `?trim=` works, brand pages list models, language persists.
Re-check before reporting; only add NEW findings to a new report.

## 4. Report format (save to `/Users/joe/newcars code/reports/YYYY-MM-DD-<topic>.md`)
```markdown
# <Frontend|Backend> issues — <scope>
**Reported by:** content team · **Date validated:** · **Environment:** staging URLs + API base

## N. <one-line title>
- **Where:** page → section
- **Repro:** URL (+ steps, e.g. click AR)
- **Expected:** what the API returns (endpoint + field + value)
- **Actual:** what the page shows
- **Also seen on:** control URLs
- **Note/Question:** only if needed (e.g. "if intended, please confirm")
```
