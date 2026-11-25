"""Stage 3 prep: review list = manifest rows sorted by route, sender, shooting time (similar shots end up
next to each other on the contact sheets). Adds era/quality/taken from inventory.csv.
Output: review.csv (row number = number on the contact sheets)."""
import csv
from common import INVENTORY, MANIFEST, OUT
inv = {r["logical"]: r for r in csv.DictReader(open(INVENTORY, encoding="utf-8-sig"))}
rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8-sig")))
for r in rows:
    i = inv[r["מקור"]]
    r["תקופה"], r["איכות"], r["צולם"] = i["era"], i["quality"], i["taken"]
rows.sort(key=lambda r: (r["מסלול"], r["שולח"], r["צולם"] or "9999", r["מקור"]))
with open(OUT / "review.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows -> review.csv")
