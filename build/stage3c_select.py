"""Stage 3c: choose what goes into the show, from review.csv + review_decisions.txt.

Rules (user, 2026-11-25):
- Show length = total length of the songs in מלא/שירים (it is ~20 min; the user asked for 15-20 min and
  then "the length of the music"). Photos get equal time: (music - videos) / n_photos, ~3 s.
- Videos first: every video not marked X goes in (X = redundant with another video / unusable).
- About 1/3 of the items "old" (frames/clips from the Galit Rosen slideshow), 2/3 "new" (everything else).
- Within each era: S (strong) photos first, then the rest by measured quality; never X.
  New photos are split between senders by quota ~ available^0.75 so the big senders (one-day photo shoots)
  don't swamp the show; תסריטאות (one group, no sender folders) gets all its usable photos for route balance.
Output: manifest_final.csv (+ קטגוריה, תקופה), selection_log.csv (every candidate: in/out + reason).
"""
import csv, math, re, subprocess
from collections import Counter, defaultdict
from pathlib import Path
from common import OUT, SRC

PHOTO_SEC_MIN = 3.0
R = list(csv.DictReader(open(OUT / "review.csv", encoding="utf-8-sig")))
dec = defaultdict(set)
for line in open(OUT / "review_decisions.txt", encoding="utf-8"):
    line = line.split("#")[0].strip()
    if ":" in line:
        k, v = line.split(":", 1)
        dec[k.strip()].update(int(x) for x in v.split())
for i, r in enumerate(R, 1):
    r["n"] = i
    r["קטגוריה"] = "הפקה" if i in dec["P"] else "הווי"
    r["grp"] = "תסריטאות" if r["מסלול"] == "תסריטאות" else r["שולח"]
    r["mark"] = "X" if i in dec["X"] else "S" if i in dec["S"] else ""
    r["pin"] = "first" if i in dec["FIRST"] else "last" if i in dec["LAST"] else ""

songs = sorted((p for p in (SRC / "מלא" / "שירים").iterdir() if ".mp3" in p.name.lower()),
               key=lambda p: int(re.search(r"(\d+)\s*$", p.name).group(1)))
def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)
music = sum(dur(p) for p in songs)

videos = [r for r in R if r["סוג"] == "וידאו" and r["mark"] != "X"]
vid_sec = sum(math.ceil(float(r["משך"]) * 10) / 10 for r in videos)
n_photos = int((music - vid_sec) // PHOTO_SEC_MIN)
n_items = n_photos + len(videos)
old_target = round(n_items / 3)
old_videos = [r for r in videos if r["תקופה"] == "ישן"]
n_old_photos = old_target - len(old_videos)
n_new_photos = n_photos - n_old_photos

def rank(rows):
    return sorted(rows, key=lambda r: (r["mark"] != "S", -float(r["איכות"] or 0)))

photos = [r for r in R if r["סוג"] == "תמונה" and r["mark"] != "X"]
old_pool = rank([r for r in photos if r["תקופה"] == "ישן"])
chosen = old_pool[:n_old_photos]

new_pool = defaultdict(list)
for r in photos:
    if r["תקופה"] == "חדש":
        new_pool[r["grp"]].append(r)
avail = {g: len(v) for g, v in new_pool.items()}
# quota ~ avail^0.75, at least all S photos, at most avail; distribute the remainder by largest fraction
w = {g: a ** 0.75 for g, a in avail.items()}
w["תסריטאות"] = avail["תסריטאות"] * 2   # the smaller route: take all of its usable photos (route balance)
quota = {g: max(sum(r["mark"] == "S" for r in new_pool[g]), min(avail[g], int(n_new_photos * w[g] / sum(w.values()))))
         for g in avail}
while sum(quota.values()) < n_new_photos:
    g = max((g for g in avail if quota[g] < avail[g]), key=lambda g: n_new_photos * w[g] / sum(w.values()) - quota[g])
    quota[g] += 1
while sum(quota.values()) > n_new_photos:
    g = max((g for g in avail if quota[g] > sum(r["mark"] == "S" for r in new_pool[g])), key=lambda g: quota[g] / w[g])
    quota[g] -= 1
for g, rows in new_pool.items():
    chosen += rank(rows)[:quota[g]]
chosen += videos
chosen_ids = {r["n"] for r in chosen}

photo_sec = (music - vid_sec) / n_photos
fields = ["קובץ", "שולח", "מסלול", "קטגוריה", "תקופה", "סוג", "משך", "פוסטר", "מקור", "pin"]
with open(OUT / "manifest_final.csv", "w", newline="", encoding="utf-8-sig") as f:
    wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    wr.writeheader()
    wr.writerows(sorted(chosen, key=lambda r: r["n"]))
with open(OUT / "selection_log.csv", "w", newline="", encoding="utf-8-sig") as f:
    wr = csv.writer(f)
    wr.writerow(["מס", "מקור", "שולח", "תקופה", "סוג", "סימון", "איכות", "נבחר", "סיבה"])
    for r in R:
        why = ("" if r["n"] in chosen_ids else
               "חלשה/מיותרת בסקירה הוויזואלית" if r["mark"] == "X" else "מחוץ למכסה (איכות נמוכה יחסית בקבוצה)")
        wr.writerow([r["n"], r["מקור"], r["שולח"], r["תקופה"], r["סוג"], r["mark"], r["איכות"],
                     "כן" if r["n"] in chosen_ids else "לא", why])
open(OUT / "show_timing.txt", "w").write(f"music_sec={music:.3f}\nphoto_sec={photo_sec:.4f}\n" +
                                         "".join(f"song={p}\n" for p in songs))
print(f"music {music:.1f}s ({music/60:.2f} min), videos {len(videos)} = {vid_sec:.1f}s, photos {n_photos} x {photo_sec:.3f}s")
c = Counter((r["תקופה"]) for r in chosen); print("era:", dict(c), f"old share {c['ישן']/len(chosen):.1%}")
print("route:", dict(Counter(r["מסלול"] for r in chosen)), " category:", dict(Counter(r["קטגוריה"] for r in chosen)))
print("quota new:", {g: f"{quota[g]}/{avail[g]}" for g in sorted(avail)})
print("songs:", [p.name for p in songs])
