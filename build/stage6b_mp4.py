"""Stage 6b: render the same show as an MP4 (1920x1080, 25 fps, H.264 + AAC music).
Same order and per-slide durations as the pptx (show_plan.py); photos/videos fitted on black, no crop;
slide boundaries are rounded to whole frames on the cumulative timeline, so there is no drift against the music."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from common import OUT
from show_plan import load

FPS, W, H = 25, 1920, 1080
rows, _ = load()
seg_dir = OUT / "mp4_segments"
seg_dir.mkdir(exist_ok=True)
fit = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,"
       f"setsar=1,fps={FPS},format=yuv420p")
t, jobs = 0, []
for k, r in enumerate(rows):
    a, t = round(t * FPS / 1000), t + r["ms"]
    frames = round(t * FPS / 1000) - a
    out = seg_dir / f"{k:04d}.mp4"
    src = OUT / r["קובץ"]
    if r["סוג"] == "וידאו":
        cmd = ["-i", str(src), "-vf", fit + ",tpad=stop_mode=clone:stop_duration=1"]
    else:
        cmd = ["-loop", "1", "-framerate", str(FPS), "-i", str(src), "-vf", fit]
    jobs.append(["ffmpeg", "-v", "error", "-y", *cmd, "-frames:v", str(frames), "-an", "-c:v", "libx264",
                 "-preset", "medium", "-crf", "19", "-r", str(FPS), "-video_track_timescale", "12800", str(out)])
with ThreadPoolExecutor(4) as ex:
    list(ex.map(lambda c: subprocess.run(c, check=True), jobs))
lst = seg_dir / "list.txt"
lst.write_text("".join(f"file '{seg_dir / f'{k:04d}.mp4'}'\n" for k in range(len(rows))))
out = OUT / "graduation_slideshow.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(OUT / "music.m4a"),
                "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart", str(out)], check=True)
print("->", out, f"{out.stat().st_size / 1e6:.0f} MB")
