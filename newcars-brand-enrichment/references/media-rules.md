# Media rules

All media is downloaded to `<workdir>/media/...`, screened, then uploaded with `scripts/upload_media.py`
(presigned uploader → staging-raw-images / staging-media hosts). Nothing external is ever referenced.

## Selection
- **No human faces in car imagery** — gallery images, highlight-card images, trim/colour shots and feature
  images. Hands on a steering wheel are fine but low value.
- **Hero banners are exempt**: a brand hero video, a brand hero/banner image and a model hero banner MAY show
  people. These are marketing creative where people are expected, so use the manufacturer's real hero clip
  rather than cutting it down. Everything else still follows the no-faces rule.
- **Current model year** for the Kuwait market (folder names like `my26`, `26MY`, `GCC` are good signals).
- Prefer action/lifestyle exteriors, then detail shots, then interiors. Skip UI screenshots, spec diagrams,
  seat-configuration renders, third-party press images (e.g. filenames with `usnews`), and B&W stock photos.
- **Logo:** the coloured/dark version from a light-background header (e.g. `nav-logo-black.svg`), never a
  white favicon. Also take the light version as `logo_dark` for dark backgrounds. Check SVG fills
  (`grep -o 'fill="[^"]*"'`): all-white fills = reject.
- **Hero video:** downloadable MP4 from the manufacturer/dealer only (no YouTube/Vimeo). Faces are fine in a
  hero video — use the clip as published. `media_screen.py cut` is still there if you need to trim a very long
  clip or drop an unrelated segment.
- **Heritage / innovation images:** from the brand's heritage/innovation pages; same face rule.

## Workflow
1. Download originals (keep the source URL list in `media/SOURCES.json` or in `gallery[].source`).
   **Keep the file extension** when naming local copies — truncating a long filename past its `.webp`/`.jpg`
   makes the uploader reject it ("unknown mime"). Images may also be referenced through a framework proxy
   (`/_next/image?url=<encoded>`): decode those too or you will miss half the gallery.
2. `media_screen.py dupes media/<model>` — byte-identical files look different in thumbnails; remove them.
3. `media_screen.py sheet media/<model> --out media/<model>/_sheet.jpg` → **open the sheet and look at every
   image** (faces, wrong model/generation, UI screenshots). Record rejects and why.
4. `media_screen.py shrink media/<model> --max 2560` — keeps uploads reasonable (6000-px originals exist).
5. Order the gallery: hero first, exteriors, then interiors. Pick the 6 highlight images from it (distinct).
6. Count: gallery minus hero minus 6 highlight images must be ≥ 13 (target 18–20 total).

## Frontend status (2026-09-24)
The old brand-video-on-model-page bug is fixed: a model with an image hero now shows its own image. So a brand
hero video is safe again, and a model hero video plays on the model page. Report anything new, don't work around it.
