"""Stage 3a: contact sheets (4x4, numbered) for production/candid classification.

Numbers on the sheets are row numbers in manifest.csv (1-based), so classifications map back directly.
Usage: python3 stage3_sheets.py [manifest.csv] [out_dir]
"""
import csv, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from common import BUILD, MANIFEST

manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else MANIFEST
out = Path(sys.argv[2]) if len(sys.argv) > 2 else BUILD / "contact_sheets"
COLS, ROWS, TW, TH = 4, 4, 480, 360
rows = list(csv.DictReader(open(manifest, encoding="utf-8-sig")))
out.mkdir(parents=True, exist_ok=True)
for old in out.glob("sheet_*.jpg"):
    old.unlink()
font = ImageFont.load_default(size=36)
for k in range(0, len(rows), COLS * ROWS):
    sheet = Image.new("RGB", (COLS * TW, ROWS * TH), (60, 60, 60))
    for i, r in enumerate(rows[k:k + COLS * ROWS]):
        im = Image.open(manifest.parent / r["קובץ"]).convert("RGB")
        im.thumbnail((TW - 8, TH - 8))
        x = (i % COLS) * TW + (TW - im.width) // 2
        y = (i // COLS) * TH + (TH - im.height) // 2
        sheet.paste(im, (x, y))
        ImageDraw.Draw(sheet).text(((i % COLS) * TW + 8, (i // COLS) * TH + 6), str(k + i + 1),
                                   fill="yellow", font=font, stroke_width=4, stroke_fill="black")
    sheet.save(out / f"sheet_{k // 16 + 1:03d}.jpg", quality=80)
print("sheets:", (len(rows) + 15) // 16, "->", out)
