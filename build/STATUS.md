# STATUS – graduation slideshow

## How to run
1. Put the original Drive folder (containing "מלא" and "תסריטאות") in `source/` at the repo root,
   or point `SLIDESHOW_SRC` at it. Originals are only read.
2. `pip install pillow pillow-heif python-pptx imagehash`
3. `cd build && python3 stage1_inventory.py && python3 stage2_process.py`

## Stages
- [ ] Stage 0 – getting the files: **blocked**. The environment's network policy blocks `drive.google.com`
      (403 from the proxy) and the Google Drive connector isn't connected.
- [~] Stage 1 – inventory (`stage1_inventory.py`): written and tested on synthetic data; not yet run on the real files.
- [~] Stage 2 – processing + manifest (`stage2_process.py`): written and tested on synthetic data; not yet run on the real files.
- [ ] Stop for approval after stage 2
- [ ] Stage 3 – production/candid classification (contact sheets)
- [ ] Stage 4 – ordering (seed)
- [ ] Stage 5 – order validation
- [ ] Stop before stage 6 (wait for "בנה מצגת")
- [ ] Stage 6 – pptx
- [ ] Stage 7 – final check + report.md

## Notes
- Duplicates: pHash ≤ 6 and dHash ≤ 8 (on EXIF-rotated images); keep the copy with the most pixels, then the largest file.
- Zips are extracted to `build/extracted/`; their contents are treated as if they sit where the zip is,
  inside a folder named after the zip.
- Route = the "מלא"/"תסריטאות" folder anywhere in the path; sender = the folder directly under it.
- manifest.csv also has a "מקור" column (source path) for traceability.
