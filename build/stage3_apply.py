"""Stage 3b: write the category column into manifest.csv.

Input: a text file listing manifest row numbers classified as "הפקה" (production), comma/space/range separated,
e.g. "1, 4-7, 12". Every other row is "הווי" (in doubt -> הווי).
Usage: python3 stage3_apply.py production_rows.txt [manifest.csv]
"""
import csv, re, sys
from pathlib import Path
from common import MANIFEST

prod_file = Path(sys.argv[1])
manifest = Path(sys.argv[2]) if len(sys.argv) > 2 else MANIFEST
prod = set()
for tok in re.findall(r"\d+(?:-\d+)?", prod_file.read_text()):
    a, _, b = tok.partition("-")
    prod.update(range(int(a), int(b or a) + 1))
rows = list(csv.DictReader(open(manifest, encoding="utf-8-sig")))
fields = list(rows[0].keys())
if "קטגוריה" not in fields:
    fields.insert(3, "קטגוריה")
for n, r in enumerate(rows, 1):
    r["קטגוריה"] = "הפקה" if n in prod else "הווי"
with open(manifest, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print("הפקה:", sum(r["קטגוריה"] == "הפקה" for r in rows), "הווי:", sum(r["קטגוריה"] == "הווי" for r in rows))
