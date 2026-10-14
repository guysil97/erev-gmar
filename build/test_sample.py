"""Trial run only: pick N images per sender from manifest.csv into manifest_sample.csv (fixed seed)."""
import csv, random, sys
from pathlib import Path
src, dst, per, seed = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
rng = random.Random(seed)
by = {}
for r in rows:
    by.setdefault(r["שולח"], []).append(r)
pick = [r for s in sorted(by) for r in rng.sample(by[s], min(per, len(by[s])))]
with open(dst, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(pick)
print(len(pick), "images from", len(by), "senders")
