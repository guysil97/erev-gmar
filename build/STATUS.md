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

## Open decisions (as of 2026-10-14)
- The files come through the Google Drive connector (folder "מצגת ערב גמר", id 10BjCycOu7W6_U95wVJT28ZSqQTm5F571).
  On 2026-10-14 the folder had no photos: "תסריטאות" was empty and "מלא " held only a single .mov.
- **Do not build anything** until the user says the collection is complete and asks for the slideshow.
- Whether to include videos in the slideshow (the original spec skipped them): to be decided once the collection is complete.
- Format: pptx (python-pptx). Best shown in PowerPoint; Google Slides doesn't support per-slide auto-advance.

## Side task: photos from the "Galit Rosen" slideshow (completed 2026-10-14)
- Source: `מלא /מצגת גלית רוזן_ אחרי תיקונים2.mov` (15:18, 1080p), downloaded to `source_video/` (not in git).
- Scripts in `build/galit/`: `frame_signal.py` → `segment.py` → `extract.py` → `sheets.py` (review) → `finalize.py`.
- Result: 203 photos + 11 video frames (one per clip), black bars cropped, JPEG q95. Index: `build/galit/galit_index.json`.
- Excluded: black opening frame and the title card. The opening video (segments 3–10) counts as one clip.
- Drive folder "תמונות גלית רוזן" created (id 1Vr2VymQuZnrjM-3P9O7c8za0k9BgKWAb); the user uploads the zip contents manually
  (the connector can't upload binary files at this volume).
- Note for later: these frames are 1080p at most, and the pHash dedup in stage 1 will keep an original over them if someone sends one.
  Their route is unknown (the folder isn't under מלא/תסריטאות).

## Trial run: one-minute slideshow (completed 2026-10-14)
- The source snapshot came from Drive via gdown (folder shared by link). "תמונות מתוך גלית רוזן" = the frames extracted from the video
  (the user uploaded them back to Drive).
- Stages 1–2 ran on the full snapshot (519 files → 509 images, 10 duplicates). Then `test_sample.py` picked 4 images per sender (seed 2026),
  and stages 3–7 ran on the 20 sampled images. Outputs in `build/test/` (not in git).
- All test outputs use `SLIDESHOW_OUT=build/test`; the final run uses the default (`build/`).
- The final run (stages 1–7 on everything) has **not** happened yet. Stop after stage 2 and before stage 6 as required.
- Full Drive download finished 2026-10-14 into `source/` (gdown --continue; rerun the same command to pick up new files).
  At that point: אפרת 50, גבי 10, גיא זילברשץ 219, גיא חזם 83, תמונות מתוך גלית רוזן 214 (+ the .mov). תסריטאות still empty.

## Decisions 2026-11-25
- The user asked for the final slideshow (skipping the two checkpoints). Anything that is a video goes into the slideshow **as video**,
  including the 11 clips from the Galit Rosen slideshow (in place of video_frame_XX.jpg).
- **Videos are muted.** Background music is coming (a "מוזיקה" folder in Drive, files numbered 01_, 02_…).
- Proposed: an MP4 of the whole show with the music mixed in, in addition to the pptx (waiting on the user's answer).
- The user is still adding material: rerun the listing (gdown --json) + fetch.py before the final run.

## Instructions collected (2026-11-25) – do NOT start until the user says to build ("תכין")
1. Videos go in as video, muted; videos take priority over photos (never filtered out; in a video/photo duplicate the video wins).
2. Selection: use judgment and include the relatively good photos (not everything).
3. Remove duplicates **and very similar photos** (burst shots / the same moment): keep only the best one.
4. Background music from a "מוזיקה" folder in Drive (if uploaded). Open question: also an MP4 of the whole show?
5. The user is still adding material and instructions.

## Final build (2026-11-25) – done
At the user's request ("prepare the slideshow, export both mp4 and PowerPoint") everything ran without the two checkpoints.
Pipeline (cd build):
  stage1_inventory.py → stage1b_similar.py → stage2_process.py → stage3_review_list.py → stage3_sheets.py review.csv contact_sheets
  → (visual review → review_decisions.txt) → stage3c_select.py → stage4_order.py --seed 2026 --manifest manifest_final.csv
  → stage5_check.py --manifest manifest_final.csv → stage6a_music.py → stage6_pptx.py → stage6b_mp4.py
  → stage7_verify.py --manifest manifest_final.csv → stage7b_summary.py
- review_decisions.txt = the visual decisions per row of review.csv (S strong / X out / P production / FIRST / LAST).
  **If material is added, review.csv numbering changes** – review only the new rows and remap the decisions by "מקור".
- Selection: videos first, 1/3 old (Galit Rosen) / 2/3 new, length = music (20:08), photo = 3.007 s.
- Outputs: graduation_slideshow.pptx (music embedded on slide 1, plays across all slides), graduation_slideshow.mp4, report.md.
- Not verified: actual playback in PowerPoint (no PowerPoint here) – verified the XML structure in code + a LibreOffice render.
