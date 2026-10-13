# Frontend retest — staging-newcars.q84sale.com

**Reported by:** content team · **Retested:** 2026-09-24 (after the tech team's fixes)
**Against:** the 9 issues in `2026-09-22-frontend-issues-staging.md`
**Test records:** brand `kw-mitsubishi` (id 3120), model `kw-mitsubishi-outlander` (id 1375, trims 5218–5221); controls: `/brand/toyota`, `/model/644`, `/model/817`

**Result: 7 of 9 fixed.** 2 still open, and 3 new (smaller) issues found.

## Fixed — thank you

| # | Issue | Verified now |
|---|---|---|
| 2 | Equipment section empty | Renders with category tabs (Safety / Comfort / Technology / Exterior / Interior) and the items per trim |
| 3 | Brand video played on model pages | The model page now uses the model's own hero image; no `<video>` on the page |
| 4 | Missing values shown as 0; petrol car labelled "Electric" | Missing values show "—" / "غير متوفر"; no "Zero emissions"; no "0s", "0kg", "0L" anywhere |
| 5 | Imported highlight cards not shown | All 6 cards render, in English and Arabic |
| 6 | Dealers missing under "Authorized Branches" | Shows name, address, phone and an "open in maps" link |
| 8 | `?trim=` ignored | `/model/1375?trim=5221` opens Full Option with 12,200 KWD |
| 9 | `/brand/toyota` showed no models | Lists its models (32 model links on the page) |

Also noticed: the language choice now persists across page loads, which makes Arabic much easier to check.

## Still open

### 1. Brand editorial stays English in Arabic mode
- **Repro:** `/brand/kw-mitsubishi` in Arabic (page loads with `lang="ar"`, `dir="rtl"`)
- **Expected:** `heritage_title_ar` = "قرن من صناعة السيارات", plus Arabic heritage description, innovation and sustainability — all present in `/v1/public/brands/3120`
- **Actual:** "A CENTURY OF AUTOMOBILES", the English heritage paragraph, "Super All-Wheel Control" and the English sustainability text
- **Also on:** `/brand/toyota` in Arabic (its Arabic fields are populated too)

### 7. Brand story not displayed
- **Repro:** `/brand/kw-mitsubishi`, `/brand/toyota`, either language
- **Expected:** `story_en` / `story_ar` from the API
- **Actual:** not rendered anywhere on the page
- **Question:** if this is deliberate, which field should carry the Kuwait brand story? We're authoring it every import.

## New issues

### 10. Highlight slot labels are wrong and partly untranslated
- **Repro:** `/model/1375`, the highlight cards, either language
- **Expected:** the 6 cards' labels follow their slots: design, performance, comfort (parallax) and technology, efficiency, comfort (featured), translated in Arabic
- **Actual:** the labels read `design` (lowercase, untranslated in Arabic), then **Performance twice** — the third card ("A quieter, more welcoming cabin" / "مقصورة أكثر هدوءاً") is labelled Performance / الأداء instead of Comfort, and no efficiency label appears. The card text itself is correct.
- **Data:** `/v1/public/models/1375` returns the correct `slot` for each card.

### 11. Equipment names show English in Arabic mode
- **Repro:** `/model/1375` in Arabic → Equipment
- **Expected:** `name_ar`, e.g. "نظام مانع انغلاق المكابح ABS مع التوزيع الإلكتروني لقوة الكبح EBD"
- **Actual:** "ABS with EBD and brake assist" — English names with Arabic "قياسي" labels beside them. Every item has `name_ar` in `/v1/public/trims/5218/equipment`.
- Related: equipment in the **Performance** category still isn't shown (the tabs are Safety / Comfort / Technology / Exterior / Interior). We can stop sending that category if it will never render — please confirm.

### 12. Arabic translation corrupts a stored spec value
- **Repro:** `/model/1375` in Arabic → Specifications → Engine
- **Actual:** `2.5L DOHC 4 أسطواناتinder Direct-Injection`
- **Cause:** it looks like a find-and-replace of "cyl" → "أسطوانات" runs inside the stored string, leaving the "inder" of "4-cylinder" behind. The stored value is `2.5L DOHC 4-cylinder Direct-Injection` (English, correct) in `/v1/public/trims/5218`.
- The compare table renders the same value correctly, so it's specific to the specifications section.
