# Arabic authoring

Every `_ar` field is real Kuwait-market Modern Standard Arabic written for Arabic readers — not a machine
translation and never a copy of the English. The dealer's own AR pages are the best reference for terminology
(e.g. Mitsubishi KW uses "ادفع طموحك" for "Drive your Ambition"), but their AR spec tables are often still
English, so equipment names usually need authoring.

## Rules
- Same facts as the EN text; natural Arabic sentence order, not word-for-word.
- Brand and technology names: brand names transliterated in prose (ميتسوبيشي، تويوتا); technology/product
  tokens stay Latin inline (MIVEC, CVT, S-AWC, Dynamic Shield, ISOFIX, SRS, LED, 2WD).
- Numbers: Western digits, thousands separator comma (7,999 د.ك, 1,600 كغ). Units: كم/س، نيوتن متر، حصان،
  لتر، مم، كغ، كيلوواط.
- Model names: transliterate (Outlander → أوتلاندر, Tiguan → تيغوان, F-PACE → إف-بيس); alphanumeric names keep
  digits/Latin (296 GTB, X5).
- Highlight titles ≤ ~60 characters; keep the same meaning as the EN title, not a literal translation.

## Trim-name transliterations
| EN | AR | | EN | AR |
|---|---|---|---|---|
| Base Line | بيس لاين | | Premium | بريميوم |
| Mid Line | ميد لاين | | Prestige | برستيج |
| Full Option | فُل أوبشن | | Sport | سبورت |
| Standard | ستاندرد | | Reserve | ريزيرف |
| Comfort | كومفورت | | Presidential | بريزيدنشيال |
| Luxury | لاكشري | | Elegance | إليجانس |
| Life | لايف | | R-Line | آر-لاين |
| Hybrid | هايبرد | | Platinum | بلاتينيوم |
| Limited | ليمتد | | GL / GLS / SE / SEL / HSE / SVR / P400 / 2.0T / V6 | stay Latin |

"+" suffixes stay as-is (بيس لاين +).

## Common equipment terms
ABS مع EBD → نظام مانع انغلاق المكابح ABS مع التوزيع الإلكتروني لقوة الكبح EBD ·
Hill Descent Control → نظام التحكم في النزول من المنحدرات · Hill Start Assist → نظام المساعدة على الانطلاق في المرتفعات ·
Cruise control → مثبّت السرعة · Adaptive cruise → مثبّت سرعة تكيّفي · Dual-zone auto A/C → تكييف أوتوماتيكي ثنائي المناطق ·
Keyless entry → دخول بدون مفتاح · Push-button start → تشغيل المحرك بضغطة زر · Heated seats → مقاعد مُدفأة ·
Ventilated seats → مقاعد مهوّاة · Panoramic sunroof → فتحة سقف بانورامية · Power tailgate → باب خلفي كهربائي ·
Leather upholstery → مقاعد مكسوّة بالجلد · Alloy wheels → جنوط ألمنيوم · Rear camera → كاميرا للرؤية الخلفية ·
Blind spot warning → نظام التحذير من النقطة العمياء · Lane departure warning → نظام التحذير من مغادرة المسار ·
Tyre pressure monitoring → نظام مراقبة ضغط الإطارات · 7 airbags → 7 وسائد هوائية

## Self-check before import
`coverage_report.py` flags AR fields that contain no Arabic or equal the EN text. Also re-read a few AR
paragraphs end-to-end: they should read like copy a Kuwaiti dealer would publish.
