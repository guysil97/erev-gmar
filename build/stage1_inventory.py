"""Stage 1: inventory, zip extraction, sender/route attribution, dedup by perceptual hash.

Output: build/inventory.csv with one row per file found (status = kept / duplicate / skipped).
Originals are only read; zips are extracted into build/extracted/.
"""
import csv
import shutil
import zipfile
from pathlib import Path, PurePosixPath

import imagehash
import pillow_heif
from PIL import Image, ImageOps

import re
import subprocess

from common import (AUDIO_EXT, EXCLUDE_SOURCES, EXTRACTED, GALIT_CLIPS, GALIT_FOLDER, INVENTORY, JUNK_NAMES, SRC, UNKNOWN,
                    VIDEO_EXT, classify_route, nfc)

pillow_heif.register_heif_opener()
Image.MAX_IMAGE_PIXELS = None
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True  # one source file in Drive is cut short by a few bytes

PHASH_MAX = 6   # hamming distance thresholds for "same picture"
DHASH_MAX = 8


def safe_extract(zpath: Path, dest: Path) -> list[str]:
    """Extract a zip without path traversal; decode Hebrew names stored as cp437."""
    errors = []
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            name = info.filename
            if not info.flag_bits & 0x800:  # not flagged UTF-8: try to recover
                try:
                    name = name.encode("cp437").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            parts = [p for p in PurePosixPath(name.replace("\\", "/")).parts if p not in ("", ".", "..", "/")]
            if not parts or info.is_dir():
                continue
            target = dest.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with zf.open(info) as s, open(target, "wb") as d:
                    shutil.copyfileobj(s, d)
            except Exception as e:  # corrupt member
                errors.append(f"{name}: {e}")
    return errors


def probe_video(path):
    """(width, height, duration) of a video, rotation applied."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    import json
    j = json.loads(out)
    st = j["streams"][0]
    w, h = st["width"], st["height"]
    rot = next((abs(int(sd.get("rotation", 0))) for sd in st.get("side_data_list", [])), 0)
    if rot in (90, 270):
        w, h = h, w
    return w, h, float(j["format"]["duration"])


def video_frame(path, t):
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    import io
    return Image.open(io.BytesIO(out))


def logical_parts(rel: tuple[str, ...]) -> tuple[str, str]:
    """rel = path parts relative to the logical root, ending with the file name."""
    dirs = [nfc(p) for p in rel[:-1] if not p.startswith("__MACOSX")]
    route = UNKNOWN
    sender = UNKNOWN
    # Find the route folder anywhere in the path (handles an extra wrapping folder).
    for i, d in enumerate(dirs):
        r = classify_route(d)
        if r:
            route = r
            if i + 1 < len(dirs):
                sender = dirs[i + 1]
            break
    return route, sender


def walk(root: Path, logical_prefix: tuple[str, ...], records: list, depth=0):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = logical_prefix + p.relative_to(root).parts
        records.append((p, rel))
        if p.suffix.lower() == ".zip" and depth < 3:
            # Zip contents live logically where the zip is, inside a folder named after it
            # (so "מלא/דנה.zip" -> sender דנה, and a zip inside a sender folder keeps that sender).
            prefix = rel[:-1] + (nfc(p.stem),)
            dest = EXTRACTED.joinpath(*[x for x in rel[:-1]], p.name + "_x")
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True)
            try:
                errs = safe_extract(p, dest)
            except zipfile.BadZipFile as e:
                errs = [str(e)]
            zip_errors[str(p)] = errs
            walk(dest, prefix, records, depth + 1)


zip_errors: dict[str, list[str]] = {}


def main():
    if not SRC.exists():
        raise SystemExit(f"Source folder not found: {SRC}")
    if EXTRACTED.exists():
        shutil.rmtree(EXTRACTED)
    EXTRACTED.mkdir(parents=True)

    found = []
    walk(SRC, (), found)

    rows = []
    for path, rel in found:
        route, sender = logical_parts(rel)
        row = {"path": str(path), "logical": "/".join(rel), "sender": sender, "route": route,
               "status": "", "reason": "", "media": "image", "duration": "", "width": "", "height": "",
               "bytes": path.stat().st_size, "phash": "", "dhash": "", "dup_of": ""}
        name = path.name.lower()
        ext = path.suffix.lower()
        logical = nfc(row["logical"])
        clip = GALIT_CLIPS / (path.stem + ".mp4")
        if GALIT_FOLDER in logical and re.fullmatch(r"video_frame_\d+", path.stem) and clip.exists():
            # A frame that stands for a clip of the Galit Rosen slideshow: use the clip itself.
            row["path"], ext = str(clip), ".mp4"
            path = clip
        if logical in EXCLUDE_SOURCES:
            row.update(status="skipped", reason=EXCLUDE_SOURCES[logical])
        elif ext == ".zip":
            errs = zip_errors.get(str(path), [])
            row.update(status="skipped", reason="zip (חולץ)" + (f"; שגיאות: {len(errs)}" if errs else ""))
        elif name in JUNK_NAMES or path.name.startswith("._") or "__MACOSX" in rel:
            row.update(status="skipped", reason="קובץ מערכת")
        elif ext in AUDIO_EXT or ext.split(" ")[0] in AUDIO_EXT or ".mp3" in path.name.lower():
            row.update(status="skipped", reason="שיר (מוזיקת רקע)")
        elif ext in VIDEO_EXT:
            try:
                w, h, dur = probe_video(path)
                small = video_frame(path, min(1.0, dur / 2)).convert("RGB")
                small.thumbnail((512, 512))
                row.update(status="kept", media="video", width=w, height=h, duration=round(dur, 2),
                           phash=str(imagehash.phash(small)), dhash=str(imagehash.dhash(small)))
            except Exception as e:
                row.update(status="skipped", reason=f"וידאו לא קריא ({type(e).__name__})")
        else:
            try:
                with Image.open(path) as im:
                    im = ImageOps.exif_transpose(im)
                    row["width"], row["height"] = im.size
                    small = im.convert("RGB")
                    small.thumbnail((512, 512))
                    row["phash"] = str(imagehash.phash(small))
                    row["dhash"] = str(imagehash.dhash(small))
                    row["status"] = "kept"
            except Exception as e:
                row.update(status="skipped", reason=f"לא תמונה / לא קריא ({type(e).__name__})")
        rows.append(row)

    # Duplicate detection: union-find over images whose hashes are close.
    imgs = [r for r in rows if r["status"] == "kept"]
    hashes = [(imagehash.hex_to_hash(r["phash"]), imagehash.hex_to_hash(r["dhash"])) for r in imgs]
    parent = list(range(len(imgs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(imgs)):
        for j in range(i + 1, len(imgs)):
            if imgs[i]["media"] != imgs[j]["media"]:
                continue
            if hashes[i][0] - hashes[j][0] <= PHASH_MAX and hashes[i][1] - hashes[j][1] <= DHASH_MAX:
                parent[find(i)] = find(j)

    groups: dict[int, list[int]] = {}
    for i in range(len(imgs)):
        groups.setdefault(find(i), []).append(i)
    for members in groups.values():
        if len(members) < 2:
            continue
        # Highest quality = most pixels, then largest file; prefer a known sender on ties.
        best = max(members, key=lambda k: (float(imgs[k]["duration"] or 0), imgs[k]["width"] * imgs[k]["height"], imgs[k]["bytes"],
                                           imgs[k]["sender"] != UNKNOWN))
        for k in members:
            if k != best:
                imgs[k].update(status="duplicate", reason="כפילות", dup_of=imgs[best]["logical"])

    with open(INVENTORY, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["path"])
        w.writeheader()
        w.writerows(rows)

    kept = sum(r["status"] == "kept" for r in rows)
    dups = sum(r["status"] == "duplicate" for r in rows)
    skipped = sum(r["status"] == "skipped" for r in rows)
    print(f"files: {len(rows)}  kept: {kept}  duplicates: {dups}  skipped: {skipped}")


if __name__ == "__main__":
    main()
