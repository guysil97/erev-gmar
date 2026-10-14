"""Contact sheets: grids of numbered thumbnails."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
src, out = Path(sys.argv[1]), Path(sys.argv[2])
COLS, ROWS, TW, TH = 4, 4, 480, 270
out.mkdir(parents=True, exist_ok=True)
files = sorted(p for p in src.iterdir() if p.suffix == ".png")
font = ImageFont.load_default(size=28)
for k in range(0, len(files), COLS * ROWS):
    sheet = Image.new("RGB", (COLS * TW, ROWS * TH), "gray")
    for i, p in enumerate(files[k:k + COLS * ROWS]):
        im = Image.open(p).convert("RGB")
        im.thumbnail((TW - 6, TH - 6))
        x, y = (i % COLS) * TW + 3, (i // COLS) * TH + 3
        sheet.paste(im, (x, y))
        label = p.stem.split("_")[0] + (" CLIP" if "_clip_" in p.name else "")
        ImageDraw.Draw(sheet).text((x + 6, y + 4), label, fill="yellow", font=font, stroke_width=3, stroke_fill="black")
    sheet.save(out / f"sheet_{k // 16 + 1:02d}.jpg", quality=80)
print("sheets:", (len(files) + 15) // 16)
