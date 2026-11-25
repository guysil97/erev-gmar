"""Cut the clips of the Galit Rosen slideshow into separate muted MP4s, one per video_frame_NN.jpg.

Segment numbering matches extract.py: stills + clips of segments.json, numbered from 1.
The opening video (segments 3-10, incl. its freeze-frames) is one clip. Each clip is trimmed by
0.25 s at the start and 0.5 s at the end so the crossfades into the neighbouring photos are left out.
Usage: python3 clips.py <galit.mov> <out_dir>
"""
import json, subprocess, sys
from pathlib import Path
FPS = 24
HERE = Path(__file__).parent
src, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
segs = [s for s in json.load(open(HERE / "segments.json")) if s["kind"] in ("still", "clip")]
items = [i for i in json.load(open(HERE / "galit_index.json"))["items"] if i["kind"] == "clip"]
for it in items:
    n = it["segment"]
    a, b = segs[n - 1]["start"], segs[n - 1]["end"]
    if n == 3:                       # opening video with freeze-frames
        b = segs[10 - 1]["end"]
    a, b = a + 6, b - 12
    dst = out / it["file"].replace(".jpg", ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a / FPS:.3f}", "-i", src, "-t", f"{(b - a) / FPS:.3f}",
                    "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(dst)], check=True)
    print(dst.name, f"{(b - a) / FPS:.1f}s")
