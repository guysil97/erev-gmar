"""Stage 2: convert kept images to JPEG (EXIF-rotated, long side 2560, q85), write manifest, print summary."""
import csv
import shutil
from collections import Counter

import pillow_heif
from PIL import Image, ImageOps

from common import IMAGES, INVENTORY, MANIFEST

pillow_heif.register_heif_opener()
Image.MAX_IMAGE_PIXELS = None
LONG_SIDE = 2560
QUALITY = 85


def to_rgb(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (0, 0, 0))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def main():
    with open(INVENTORY, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if IMAGES.exists():
        shutil.rmtree(IMAGES)
    IMAGES.mkdir(parents=True)

    manifest = []
    for n, r in enumerate((r for r in rows if r["status"] == "kept"), 1):
        out = IMAGES / f"img_{n:04d}.jpg"
        with Image.open(r["path"]) as im:
            im = to_rgb(ImageOps.exif_transpose(im))
            im.thumbnail((LONG_SIDE, LONG_SIDE), Image.LANCZOS)
            im.save(out, "JPEG", quality=QUALITY, optimize=True)
        manifest.append({"קובץ": f"images/{out.name}", "שולח": r["sender"], "מסלול": r["route"],
                         "מקור": r["logical"]})

    with open(MANIFEST, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["קובץ", "שולח", "מסלול", "מקור"])
        w.writeheader()
        w.writerows(manifest)

    by_sender = Counter((m["מסלול"], m["שולח"]) for m in manifest)
    by_route = Counter(m["מסלול"] for m in manifest)
    print(f"images: {len(manifest)}")
    print("by route:", dict(by_route))
    for (route, sender), c in sorted(by_sender.items()):
        print(f"  {route} / {sender}: {c}")
    print("duplicates removed:", sum(r["status"] == "duplicate" for r in rows))
    skipped = [r for r in rows if r["status"] == "skipped" and not r["reason"].startswith("zip")]
    print("skipped:", len(skipped), dict(Counter(r["reason"] for r in skipped)))


if __name__ == "__main__":
    main()
