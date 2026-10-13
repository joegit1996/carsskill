# newcars-brand-enrichment

A Claude Code skill that takes a car brand from "nothing on staging" to a complete, verified, bilingual
(English + Arabic) brand on the **4Sale New Cars** catalog for the Kuwait market — with a coverage score and an
independent trim/price audit at the end.

It was built from, and proven on, two real imports: `kw-mitsubishi` (Outlander) and `kw-honda` (9 models,
24 trims, every one priced).

## What it does

```
ask code mode → enumerate the lineup → research each model → screen media → author content.json
      → coverage gate + price audit → upload media → import → verify on staging → report issues
```

The judgment work (research, picking images, writing EN/AR copy) is the agent's. Everything repeatable is done by
the bundled scripts, which all read one file: `<workdir>/content.json`.

## Install

Copy `newcars-brand-enrichment/` into your skills directory (e.g. `.claude/skills/` in your project, or your
user-level skills folder) and invoke it by name. `SKILL.md` has a **Setup** section listing the dependencies
(Python 3, Pillow, poppler, ffmpeg) and the credentials it needs.

The skill is machine-independent: it hard-codes no local paths. Work is written relative to the directory the
agent runs in (`./<brand_code>/` per brand, `./reports/` for issue reports), and everything the scripts need at
runtime ships inside the skill.

## Configuration (all optional, all env vars)

| Variable | Used for |
|---|---|
| `NEWCARS_ADMIN_USER` / `NEWCARS_ADMIN_PASS` | staging admin login, instead of `get_jwt.py --user/--password` |
| `NEWCARS_SWAGGER` | full path to the catalog service's `swaggerv2.json` |
| `NEWCARS_DOCS` | directory holding `swaggerv2.json`, `uploader-guide.md`, `content-upload-guide.md`, the brand-import checklist |

The API contract is not redistributed here. `scripts/api_contract.py` looks for it at `$NEWCARS_SWAGGER`, then
`$NEWCARS_DOCS/swaggerv2.json`, then `./swaggerv2.json` and `./docs/swaggerv2.json`, and tells you how to point
it at your copy if it finds none — get the spec from the team that owns the service rather than guessing at
endpoints.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The workflow: setup questions, 8 steps, what to tell the user at the end |
| `references/content-schema.md` | `content.json` — the single source of truth for a run |
| `references/sources-and-research.md` | Source priority, accuracy rules, how to read dealer sites and brochures |
| `references/arabic.md` | Arabic authoring rules, trim-name transliterations, equipment glossary |
| `references/media-rules.md` | Image/video selection, screening, the no-faces rule and its exemptions |
| `references/api-and-gotchas.md` | Catalog API, auth, and every gotcha hit in real runs |
| `references/qa-and-reporting.md` | Staging QA, how to tell a data bug from a frontend bug, report format |
| `references/brand-notes.md` | Per-brand source notes (Mitsubishi, Genesis, Changan, Honda) — append after each run |
| `scripts/` | get_jwt · upload_media · import_catalog · coverage_report · price_audit · verify_staging · page_state · media_screen · api_contract |
| `reports/` | Issue reports filed with the frontend and backend teams |

## The two gates

- **`coverage_report.py`** — scores the content against the brand-import checklist. Passes only when model/trim
  enumeration is 100%, every level is ≥ 90% (gaps with a written reason excluded), and there are no errors.
  Critical fields (logo, hero, model hero, ≥ 13 gallery images, 6 highlights, EN/AR names) can't be waived.
- **`price_audit.py`** — the one that protects grade and price accuracy. It re-reads the **saved source pages**
  rather than trusting what the research wrote down, and fails when an imported grade name or price is absent
  from the sources, when the price printed next to a grade doesn't match the imported one, or when a grade is
  marked price-on-request although the site prices it.

## House rules the skill enforces

- Prices and grade names come only from the Kuwait dealer; specs from the Kuwait/GCC brochure.
- Never invent a value. If no official source publishes it, it's a gap **with a reason**.
- Kuwait beats the region: when the Kuwait dealer publishes a figure, import it and flag any regional conflict.
- Every `_ar` field is authored Arabic, never a copy of the English.
- No faces in gallery/highlight car imagery (hero banners and hero videos are exempt). No Wikipedia. No YouTube.
- All media is re-hosted through the presigned uploader — no external URLs.
- We upload content and **report** frontend/backend problems; we don't fix other teams' code.

## Results on the Honda run

9 models, 24 trims (100% priced), 156 spec values, 54 highlight cards, 237 media files, 3 showrooms.
Coverage: enumeration 100%, brand 100%, models 100%, trims 100% with justified gaps excluded (82% raw).
Price audit: 0 findings. Staging verification: 198/198 checks passed.
