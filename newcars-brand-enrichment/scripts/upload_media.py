#!/usr/bin/env python3
"""Upload every local media file referenced in content.json through the presigned uploader.

Flow per file (docs/uploader-guide.md): presign {mime, exact size, type:new_cars} -> PUT bytes with the
identical Content-Type -> HEAD the public URL. Results go to <workdir>/uploads.json:
  {"by_path": {"media/x.jpg": url}, "by_md5": {md5: url}}
Identical bytes are uploaded once (md5 de-dupe), so re-runs and duplicates cost nothing.

Usage: upload_media.py --workdir <dir> [--dry]
"""
import argparse, hashlib, json, mimetypes, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import UPLOADER, http, iter_media, is_hosted, load_json, read_jwt, save_json

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
        ".svg": "image/svg+xml", ".mp4": "video/mp4", ".webm": "video/webm", ".gif": "image/gif"}

ap = argparse.ArgumentParser()
ap.add_argument("--workdir", required=True)
ap.add_argument("--dry", action="store_true", help="only list what would be uploaded")
a = ap.parse_args()
content = load_json(os.path.join(a.workdir, "content.json"))
man_path = os.path.join(a.workdir, "uploads.json")
man = load_json(man_path, {"by_path": {}, "by_md5": {}})

refs = []
for r in iter_media(content):
    if r not in refs:
        refs.append(r)
local = [r for r in refs if not is_hosted(r)]
bad = [r for r in refs if r.startswith("http") and not is_hosted(r)]
if bad:
    sys.exit("External URLs are not allowed in content.json (download + reference the local file):\n  " + "\n  ".join(bad))
missing = [r for r in local if not os.path.exists(os.path.join(a.workdir, r))]
if missing:
    sys.exit("Missing local media files:\n  " + "\n  ".join(missing))
print(f"{len(refs)} media refs, {len(local)} local files")
if a.dry:
    for r in local:
        print("  would upload" if r not in man["by_path"] else "  cached", r)
    sys.exit(0)

jwt = read_jwt(a.workdir)
hdr = {"Application-Source": "q84sale", "Accept-Language": "en", "Accept": "application/json",
       "Content-Type": "application/json", "admin-console-token": jwt}
failed = 0
for r in local:
    body = open(os.path.join(a.workdir, r), "rb").read()
    md5 = hashlib.md5(body).hexdigest()
    if r in man["by_path"] and man["by_md5"].get(md5) == man["by_path"][r]:
        continue
    if md5 in man["by_md5"]:
        man["by_path"][r] = man["by_md5"][md5]
        print(f"  dedupe {r} -> {man['by_md5'][md5]}")
        save_json(man_path, man)
        continue
    mime = MIME.get(os.path.splitext(r)[1].lower()) or mimetypes.guess_type(r)[0]
    if not mime:
        print(f"  ! unknown mime, skipped: {r}"); failed += 1; continue
    for attempt in range(4):
        st, res = http("POST", UPLOADER, {"files": [{"mime": mime, "size": len(body), "type": "new_cars"}]}, hdr)
        if st == 200:
            break
        if st == 429 and attempt < 3:
            time.sleep(2 * (attempt + 1)); continue
        break
    if st != 200:
        print(f"  ! presign {st} {str(res)[:150]} for {r}"); failed += 1; continue
    item = res["results"][0]
    pst, _ = http("PUT", item["uploadUrl"], body, {"Content-Type": mime}, raw=True, timeout=300)
    url = item["publicUrls"]["url"]
    time.sleep(1.5)
    hst, _ = http("HEAD", url, raw=True)
    if pst not in (200, 204) or hst != 200:
        print(f"  ! PUT {pst} / HEAD {hst} for {r}"); failed += 1; continue
    man["by_path"][r] = url
    man["by_md5"][md5] = url
    save_json(man_path, man)
    print(f"  {len(body)//1024:>6} KB {r} -> {url}")
    time.sleep(0.3)  # uploader rate-limits around 5 req/s per token
print(f"done: {len(local) - failed} ok, {failed} failed. Manifest: {man_path}")
sys.exit(1 if failed else 0)
