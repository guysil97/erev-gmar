"""Shared paths and helpers for the graduation slideshow pipeline."""
import os
import unicodedata
from pathlib import Path

BUILD = Path(__file__).resolve().parent
ROOT = BUILD.parent
# Source folder with the originals (read-only). Override with SLIDESHOW_SRC.
SRC = Path(os.environ.get("SLIDESHOW_SRC", ROOT / "source"))

# Output folder (override with SLIDESHOW_OUT, e.g. build/test for a trial run).
OUT = Path(os.environ.get("SLIDESHOW_OUT", BUILD))
EXTRACTED = OUT / "extracted"      # unzipped archives (copies, never originals)
IMAGES = OUT / "images"            # processed JPEGs
INVENTORY = OUT / "inventory.csv"  # every file found, with status
MANIFEST = OUT / "manifest.csv"

GALIT_CLIPS = OUT / "galit_clips"   # muted MP4 clips cut from the Galit Rosen slideshow (galit/clips.py)

UNKNOWN = "לא ידוע"

# Source files left out on purpose (logical path -> reason).
EXCLUDE_SOURCES = {
    "מלא/מצגת גלית רוזן_ אחרי תיקונים2.mov":
        "המצגת הקודמת (גלית רוזן) – התמונות והקטעים ממנה נכנסו בנפרד דרך 'תמונות מתוך גלית רוזן'",
}
GALIT_FOLDER = "תמונות מתוך גלית רוזן"
ROUTES = {"מלא", "תסריטאות"}

VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".wmv", ".webm", ".mts", ".m2ts", ".mpg", ".mpeg"}
JUNK_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def classify_route(name: str) -> str | None:
    n = nfc(name)
    for r in ROUTES:
        if n == r or n.startswith(r):
            return r
    return None
