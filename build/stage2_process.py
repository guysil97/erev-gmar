"""Stage 2: convert kept images to JPEG (EXIF-rotated, long side 2560, q85), write manifest, print summary.

Videos are re-encoded to muted H.264 MP4 (long side <= 1920) with a poster JPEG for the slide and the
contact sheets. Animated GIFs are kept as GIF (PowerPoint plays them), resized if larger than 1280.
"""
import csv
import shutil
import subprocess
from collections import Counter

import pillow_heif
from PIL import Image, ImageOps

from common import IMAGES, INVENTORY, MANIFEST

pillow_heif.register_heif_opener()
Image.MAX_IMAGE_PIXELS = None
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True  # one source file in Drive is cut short by a few bytes
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
        kind, dur, poster = "תמונה", "", ""
        if r.get("media") == "video":
            out = IMAGES / f"vid_{n:04d}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", r["path"], "-an", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "21", "-pix_fmt", "yuv420p",
                            "-vf", "scale='if(gte(iw,ih),min(1920,iw),-2)':'if(gte(iw,ih),-2,min(1920,ih))'",
                            "-movflags", "+faststart", str(out)], check=True)
            poster_path = IMAGES / f"vid_{n:04d}_poster.jpg"
            dur = float(r["duration"])
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(1.0, dur / 2):.2f}", "-i", str(out),
                            "-frames:v", "1", "-q:v", "3", str(poster_path)], check=True)
            kind, poster = "וידאו", f"images/{poster_path.name}"
        else:
            with Image.open(r["path"]) as im:
                if getattr(im, "is_animated", False) and im.format == "GIF":
                    out = IMAGES / f"img_{n:04d}.gif"
                    if max(im.size) > 1280:
                        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", r["path"], "-vf",
                                        "scale='if(gte(iw,ih),1280,-2)':'if(gte(iw,ih),-2,1280)'", str(out)], check=True)
                    else:
                        shutil.copyfile(r["path"], out)
                else:
                    out = IMAGES / f"img_{n:04d}.jpg"
                    im = to_rgb(ImageOps.exif_transpose(im))
                    im.thumbnail((LONG_SIDE, LONG_SIDE), Image.LANCZOS)
                    im.save(out, "JPEG", quality=QUALITY, optimize=True)
        manifest.append({"קובץ": f"images/{out.name}", "שולח": r["sender"], "מסלול": r["route"],
                         "סוג": kind, "משך": dur, "פוסטר": poster, "מקור": r["logical"]})

    with open(MANIFEST, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["קובץ", "שולח", "מסלול", "סוג", "משך", "פוסטר", "מקור"])
        w.writeheader()
        w.writerows(manifest)

    by_sender = Counter((m["מסלול"], m["שולח"]) for m in manifest)
    by_route = Counter(m["מסלול"] for m in manifest)
    print(f"items: {len(manifest)}  ", dict(Counter(m["סוג"] for m in manifest)),
          "  animated GIFs:", sum(m["קובץ"].endswith(".gif") for m in manifest))
    print("by route:", dict(by_route))
    for (route, sender), c in sorted(by_sender.items()):
        print(f"  {route} / {sender}: {c}")
    print("duplicates removed:", sum(r["status"] == "duplicate" for r in rows))
    skipped = [r for r in rows if r["status"] == "skipped" and not r["reason"].startswith("zip")]
    print("skipped:", len(skipped), dict(Counter(r["reason"] for r in skipped)))


if __name__ == "__main__":
    main()
