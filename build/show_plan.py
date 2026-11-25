"""Per-slide durations shared by the pptx and the mp4, so both run in sync with the music.
Photos: photo_sec from show_timing.txt (equal time, show = music length). Videos: their own length (0.1 s up)."""
import csv, math
from common import OUT

def load(order_path=OUT / "order.csv"):
    t = dict(l.strip().split("=", 1) for l in open(OUT / "show_timing.txt") if "=" in l and not l.startswith("song="))
    photo_ms = int(round(float(t["photo_sec"]) * 1000))
    rows = list(csv.DictReader(open(order_path, encoding="utf-8-sig")))
    for r in rows:
        r["ms"] = int(math.ceil(float(r["משך"]) * 10)) * 100 if r["סוג"] == "וידאו" else photo_ms
    return rows, photo_ms

def songs():
    return [l.strip().split("=", 1)[1] for l in open(OUT / "show_timing.txt") if l.startswith("song=")]
