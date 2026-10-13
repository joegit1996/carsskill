#!/usr/bin/env python3
"""Log in to the staging admin console and cache the JWT in <workdir>/.jwt (8h TTL).

Credentials: --user/--password, or env NEWCARS_ADMIN_USER / NEWCARS_ADMIN_PASS.
The staging credentials are documented in /Users/joe/new_cars/docs/uploader-guide.md (Step 1).
The same token works for the presigned uploader AND /v1/admin/import/* (header `admin-console-token`).
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import LOGIN, http, save_json

ap = argparse.ArgumentParser()
ap.add_argument("--workdir", required=True)
ap.add_argument("--user", default=os.environ.get("NEWCARS_ADMIN_USER"))
ap.add_argument("--password", default=os.environ.get("NEWCARS_ADMIN_PASS"))
a = ap.parse_args()
if not a.user or not a.password:
    sys.exit("Provide --user/--password or NEWCARS_ADMIN_USER/NEWCARS_ADMIN_PASS (see uploader-guide.md).")
st, body = http("POST", LOGIN, {"username": a.user, "password": a.password}, {"Content-Type": "application/json"})
if st != 200 or not isinstance(body, dict) or "token" not in body:
    sys.exit(f"login failed: {st} {str(body)[:200]}")
save_json(os.path.join(a.workdir, ".jwt"), {"token": body["token"], "expiresAt": body.get("expiresAt")})
print(f"JWT cached in {a.workdir}/.jwt (expiresAt {body.get('expiresAt')})")
