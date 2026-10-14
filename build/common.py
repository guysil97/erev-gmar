"""Shared paths and helpers for the graduation slideshow pipeline."""
import os
import unicodedata
from pathlib import Path

BUILD = Path(__file__).resolve().parent
ROOT = BUILD.parent
# Source folder with the originals (read-only). Override with SLIDESHOW_SRC.
SRC = Path(os.environ.get("SLIDESHOW_SRC", ROOT / "source"))

EXTRACTED = BUILD / "extracted"      # unzipped archives (copies, never originals)
IMAGES = BUILD / "images"            # processed JPEGs
INVENTORY = BUILD / "inventory.csv"  # every file found, with status
MANIFEST = BUILD / "manifest.csv"

UNKNOWN = "לא ידוע"
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
