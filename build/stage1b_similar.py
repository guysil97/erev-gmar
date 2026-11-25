"""Stage 1b: quality score per image + removal of near-identical shots (bursts, the same moment twice).

Adds to inventory.csv: quality (0-100), sharpness, brightness, taken (EXIF time), era (ישן/חדש), group.
Near-identical = (pHash <= 10 and dHash <= 12), or same sender within 20 s with pHash <= 14 and dHash <= 18.
Greedy best-first (videos first, then by quality); no chaining.
"""
import csv, datetime as dt
import numpy as np
import imagehash
import pillow_heif
from PIL import Image, ImageFile, ImageFilter, ImageOps
from common import GALIT_FOLDER, INVENTORY

pillow_heif.register_heif_opener()
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

rows = list(csv.DictReader(open(INVENTORY, encoding="utf-8-sig")))
kept = [r for r in rows if r["status"] == "kept"]


def exif_time(im):
    try:
        ex = im.getexif()
        v = ex.get_ifd(0x8769).get(36867) or ex.get(306)
        return dt.datetime.strptime(v.strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


for r in kept:
    r["era"] = "ישן" if GALIT_FOLDER in r["logical"] else "חדש"
    if r["media"] == "video":
        r.update(quality=100, sharpness="", brightness="", taken="")
        continue
    im = Image.open(r["path"])
    t = exif_time(im)
    im = ImageOps.exif_transpose(im).convert("L")
    im.thumbnail((1000, 1000))
    a = np.asarray(im, dtype=np.float32)
    lap = np.asarray(im.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], 1, 128)), np.float32) - 128
    sharp = float(lap.var())
    bright = float(a.mean())
    clipped = float(((a < 8) | (a > 247)).mean())
    mp = int(r["width"]) * int(r["height"]) / 1e6
    q = (min(1, np.log1p(sharp) / np.log1p(400)) * 55          # sharpness
         + (1 - min(1, abs(bright - 120) / 120)) * 20           # exposure
         + (1 - min(1, clipped * 3)) * 10                       # blown/crushed areas
         + min(1, mp / 3) * 15)                                 # resolution (3 MP+ = full)
    r.update(quality=round(q, 1), sharpness=round(sharp, 1), brightness=round(bright), taken=t.isoformat() if t else "")

# near-identical: greedy, best first. Each item is compared directly with the items already kept
# (no chaining through intermediate photos, which merged different shots of the same location).
H = [(imagehash.hex_to_hash(r["phash"]), imagehash.hex_to_hash(r["dhash"])) for r in kept]
T = [dt.datetime.fromisoformat(r["taken"]) if r["taken"] else None for r in kept]
def close(i, j):
    dp, dd = H[i][0] - H[j][0], H[i][1] - H[j][1]
    if dp <= 10 and dd <= 12:
        return True
    return (kept[i]["sender"] == kept[j]["sender"] and T[i] and T[j]
            and abs((T[i] - T[j]).total_seconds()) <= 20 and dp <= 14 and dd <= 18)
order = sorted(range(len(kept)), key=lambda k: (kept[k]["media"] != "video", -float(kept[k]["quality"])))
winners = []
n_sim = 0
for k in order:
    w = next((w for w in winners if close(k, w)), None)
    if w is None:
        winners.append(k)
    else:
        kept[k].update(status="similar", reason="דומה מאוד", dup_of=kept[w]["logical"])
        n_sim += 1
for g, k in enumerate(winners):
    kept[k]["group"] = g

fields = list(rows[0].keys())
for c in ("quality", "sharpness", "brightness", "taken", "era", "group"):
    if c not in fields:
        fields.append(c)
with open(INVENTORY, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
from collections import Counter
print("near-identical removed:", n_sim, " remaining:", Counter((r["era"], r["media"]) for r in kept if r["status"] == "kept"))
