"""Extract one full-res frame from the middle of each still and each clip."""
import json, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
FPS = 24
src, segs_path, outdir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
outdir.mkdir(parents=True, exist_ok=True)
segs = [s for s in json.load(open(segs_path)) if s["kind"] in ("still", "clip")]
jobs = []
for n, s in enumerate(segs, 1):
    mid = (s["start"] + s["end"]) // 2
    name = f"{n:03d}_{'photo' if s['kind'] == 'still' else 'clip'}_{s['t']:07.2f}s.png"
    s["file"], s["frame"] = name, mid
    jobs.append((mid, outdir / name))
def grab(job):
    mid, out = job
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{mid / FPS:.4f}", "-i", src, "-frames:v", "1", str(out)], check=True)
with ThreadPoolExecutor(8) as ex:
    list(ex.map(grab, jobs))
json.dump(segs, open(outdir / "frames.json", "w"), indent=0, ensure_ascii=False)
print(len(jobs), "frames")
