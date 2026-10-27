"""Shared helpers for the newcars-brand-enrichment scripts (stdlib only)."""
import json, os, re, time, urllib.request, urllib.error

# Environment. NEWCARS_ENV=staging (default) | prod, or override any host individually.
# Production differs only by dropping the "staging-" prefix, but it is the live consumer site:
# every write under NEWCARS_ENV=prod needs the user's explicit go-ahead for that specific change.
ENV = os.environ.get("NEWCARS_ENV", "staging").strip().lower()
if ENV in ("prod", "production", "live"):
    ENV, _P = "prod", ""
elif ENV in ("staging", "stg", "test"):
    ENV, _P = "staging", "staging-"
else:
    raise SystemExit(f"NEWCARS_ENV must be 'staging' or 'prod', got {ENV!r}")

API = os.environ.get("NEWCARS_API_BASE") or f"https://{_P}services.q84sale.com/api/v1/new-cars-catalog"
UPLOADER = os.environ.get("NEWCARS_UPLOADER") or f"https://{_P}services.q84sale.com/api/v1/presigned-uploader"
LOGIN = os.environ.get("NEWCARS_LOGIN") or f"https://{_P}admin-console.4sale.work/api/auth/login"
# Media refs count as "ours" only on this environment's own CDN — a staging URL in a prod import
# (or the reverse) means the media was never re-uploaded for this environment.
HOSTED_HOSTS = (f"https://{_P}raw-images.q84sale.com/", f"https://{_P}media.q84sale.com/")
SITE = os.environ.get("NEWCARS_SITE") or f"https://{_P}newcars.q84sale.com"
STAGING_HOSTS = HOSTED_HOSTS  # legacy alias


def env_banner():
    return f"[{ENV}] {API}"
ARABIC = re.compile(r"[؀-ۿ]")
BANNED_SOURCE = re.compile(r"wikipedia\.org|wikimedia\.org", re.I)


def load_json(path, default=None):
    if default is not None and not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def http(method, url, body=None, headers=None, raw=False, timeout=90):
    """Returns (status, parsed_json_or_text). Never raises on HTTP errors."""
    data = None
    if body is not None:
        data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            if raw:
                return r.status, payload
            try:
                return r.status, json.loads(payload or b"{}")
            except ValueError:
                return r.status, payload.decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:800]


def public_get(path, retries=2):
    for attempt in range(retries + 1):
        st, body = http("GET", API + path, headers={"Application-Source": "q84sale"})
        if st == 200:
            return body.get("data", body) if isinstance(body, dict) else body
        if attempt < retries:
            time.sleep(2)
    raise RuntimeError(f"GET {path} -> {st}: {str(body)[:300]}")


def as_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return x.get("items") or []
    return []


def admin_headers(jwt):
    return {"Content-Type": "application/json", "Application-Source": "q84sale", "admin-console-token": jwt}


def read_jwt(workdir):
    p = os.path.join(workdir, ".jwt")
    if not os.path.exists(p):
        raise SystemExit(f"No JWT at {p}. Run scripts/get_jwt.py --workdir {workdir} first.")
    tok = json.load(open(p))
    if tok.get("expiresAt") and tok["expiresAt"] / 1000 < time.time() + 300:
        raise SystemExit("JWT expired or about to expire. Re-run scripts/get_jwt.py.")
    return tok["token"]


def is_hosted(ref):
    return isinstance(ref, str) and ref.startswith(HOSTED_HOSTS)


BRAND_MEDIA_KEYS = ["logo", "logo_dark", "hero_video", "hero_image", "featured_image", "banner", "heritage_image", "innovation_image"]


def iter_media(content):
    """Yield every media reference (local path or hosted URL) in content.json."""
    for k in BRAND_MEDIA_KEYS:
        if content["brand"].get("media", {}).get(k):
            yield content["brand"]["media"][k]
    for m in content.get("models", []):
        for k in ("hero_image", "hero_video"):
            if m.get(k):
                yield m[k]
        for g in m.get("gallery", []):
            yield g["file"]
        for h in m.get("highlights", []):
            if h.get("image"):
                yield h["image"]
        for t in m.get("trims", []):
            for k in ("hero_image", "hero_video"):
                if t.get(k):
                    yield t[k]
            for c in t.get("colors", []):
                for k in ("image", "swatch"):
                    if c.get(k):
                        yield c[k]


def model_code(brand_code, model):
    return model.get("code") or f"{brand_code}-{model['slug']}"


def trim_code(mcode, trim):
    return trim.get("variant_code") or f"{mcode}-{trim['slug']}"
