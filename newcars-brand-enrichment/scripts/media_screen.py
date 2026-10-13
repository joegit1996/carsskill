#!/usr/bin/env python3
"""Media screening helpers - you still LOOK at the output; the script just makes that fast.

  media_screen.py sheet <dir-or-files...> --out sheet.jpg     contact sheet (numbered, with size) for face/quality review
  media_screen.py dupes <dir>                                 byte-identical duplicates (md5)
  media_screen.py frames <video.mp4> --out frames.jpg [--fps 1]  tiled frames to spot faces in a video
  media_screen.py cut <video.mp4> --keep 0-2.7,7.6-15 --out clean.mp4   keep only face-free segments, drop audio, H.264
  media_screen.py shrink <dir> --max 2560                     downscale images whose long edge > max (in place)

Needs Pillow for sheet/shrink and ffmpeg/ffprobe for video commands.
"""
import argparse, glob, hashlib, os, subprocess, sys
from collections import defaultdict

IMG = (".jpg", ".jpeg", ".png", ".webp")


def files_of(paths):
    out = []
    for p in paths:
        out += sorted(f for f in glob.glob(os.path.join(p, "*")) if f.lower().endswith(IMG)) if os.path.isdir(p) else [p]
    return out


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("sheet"); s.add_argument("paths", nargs="+"); s.add_argument("--out", required=True); s.add_argument("--cols", type=int, default=5)
d = sub.add_parser("dupes"); d.add_argument("dir")
f = sub.add_parser("frames"); f.add_argument("video"); f.add_argument("--out", required=True); f.add_argument("--fps", default="1")
c = sub.add_parser("cut"); c.add_argument("video"); c.add_argument("--keep", required=True); c.add_argument("--out", required=True)
r = sub.add_parser("shrink"); r.add_argument("dir"); r.add_argument("--max", type=int, default=2560)
a = ap.parse_args()

if a.cmd == "sheet":
    from PIL import Image, ImageDraw
    fs = files_of(a.paths)
    W, H = 360, 240
    for start in range(0, len(fs), 20):
        chunk = fs[start:start + 20]
        rows = (len(chunk) + a.cols - 1) // a.cols
        sheet = Image.new("RGB", (a.cols * W, rows * (H + 24)), "white")
        dr = ImageDraw.Draw(sheet)
        for i, fn in enumerate(chunk):
            im = Image.open(fn); size = im.size; im = im.convert("RGB"); im.thumbnail((W - 6, H))
            x, y = (i % a.cols) * W, (i // a.cols) * (H + 24)
            sheet.paste(im, (x, y))
            dr.text((x + 4, y + H + 5), f"{start + i}: {os.path.basename(fn)[:28]} {size[0]}x{size[1]}", fill="black")
        out = a.out if len(fs) <= 20 else a.out.replace(".jpg", f"-{start // 20}.jpg")
        sheet.save(out, quality=80)
        print(out, f"({len(chunk)} images)")
elif a.cmd == "dupes":
    groups = defaultdict(list)
    for fn in files_of([a.dir]):
        groups[hashlib.md5(open(fn, "rb").read()).hexdigest()].append(fn)
    d = [g for g in groups.values() if len(g) > 1]
    print("\n".join(" == ".join(g) for g in d) or "no duplicates")
elif a.cmd == "frames":
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", f"fps={a.fps},scale=240:-1,tile=8x4",
                    "-frames:v", "1", a.out], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video],
                         capture_output=True, text=True).stdout.strip()
    print(f"{a.out} (duration {dur}s, {a.fps} frame/s, read left-to-right)")
elif a.cmd == "cut":
    segs = [tuple(map(float, x.split("-"))) for x in a.keep.split(",")]
    parts = "".join(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}];" for i, (s, e) in enumerate(segs))
    concat = "".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[v]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-filter_complex", parts + concat, "-map", "[v]", "-an",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    a.out], check=True)
    print(f"{a.out} written - re-run `frames` on it to confirm no faces remain")
elif a.cmd == "shrink":
    from PIL import Image
    for fn in files_of([a.dir]):
        im = Image.open(fn)
        if max(im.size) > a.max:
            im.thumbnail((a.max, a.max))
            im.save(fn, quality=88) if fn.lower().endswith((".jpg", ".jpeg")) else im.save(fn)
            print("shrunk", fn, im.size)
