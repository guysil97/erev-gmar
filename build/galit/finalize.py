"""Build the final "תמונות גלית רוזן" set from the segmented video.

- Photos: the middle frame of each still segment, black bars cropped.
- Clips: the sharpest frame from the middle 70% of each clip (one per clip).
- Excluded by visual review: 001 (black opening frame), 002 (title card).
- 003-010 are one opening video with freeze-frames -> treated as a single clip.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
import imagehash
from PIL import Image, ImageFilter
FPS = 24
src, raw, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
segs = json.load(open(raw / "frames.json"))   # numbered 1..N in order
EXCLUDE = {1: "פריים שחור בפתיחה", 2: "כרטיס כותרת"}
MERGE_CLIP = range(3, 11)                      # opening video incl. its freeze-frames
# Clips where the sharpest frame was a poor pick (blurry subject / empty scene): use the middle frame.
USE_MID = {97, 191}
out.mkdir(parents=True, exist_ok=True)

def grab(frame):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{frame / FPS:.4f}", "-i", src, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return Image.frombytes("RGB", (1920, 1080), r.stdout)

def crop_bars(im):
    a = np.asarray(im.convert("L"))
    cols = np.where(a.max(axis=0) > 24)[0]
    rows = np.where(a.max(axis=1) > 24)[0]
    if len(cols) == 0:
        return im
    return im.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))

def sharpness(im):
    return np.asarray(im.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32).var()

clips = []
items = []
for n, s in enumerate(segs, 1):
    if n in EXCLUDE:
        continue
    if n in MERGE_CLIP:
        if n == MERGE_CLIP[0]:
            clips.append((n, segs[MERGE_CLIP[0] - 1]["start"], segs[MERGE_CLIP[-1] - 1]["end"]))
        continue
    if s["kind"] == "clip":
        clips.append((n, s["start"], s["end"]))
    else:
        items.append(("photo", n, s["frame"]))

for n, a, b in clips:
    span = b - a
    cands = np.linspace(a + 0.15 * span, b - 0.15 * span, 12).astype(int)
    best = (a + b) // 2 if n in USE_MID else max(cands, key=lambda k: sharpness(grab(k)))
    items.append(("clip", n, int(best)))

items.sort(key=lambda x: x[2])
rows, hashes = [], []
pc = cc = 0
for kind, n, frame in items:
    im = crop_bars(grab(frame))
    h = imagehash.phash(im)
    dup = next((r["file"] for r, hh in zip(rows, hashes) if h - hh <= 6), "")
    if kind == "photo":
        pc += 1; name = f"photo_{pc:03d}.jpg"
    else:
        cc += 1; name = f"video_frame_{cc:02d}.jpg"
    im.save(out / name, quality=95, subsampling=0)
    rows.append({"file": name, "kind": kind, "segment": n, "time_sec": round(frame / FPS, 2),
                 "size": f"{im.width}x{im.height}", "possible_duplicate_of": dup})
    hashes.append(h)
json.dump({"excluded": EXCLUDE, "items": rows}, open(out.parent / "galit_index.json", "w"), ensure_ascii=False, indent=1)
print("photos:", pc, "clip frames:", cc, "possible dups:", [(r["file"], r["possible_duplicate_of"]) for r in rows if r["possible_duplicate_of"]])
