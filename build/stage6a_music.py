"""Background music: the songs in the user's order, back to back, trimmed/padded to the show length,
4 s fade-out at the end. Output: music.m4a (AAC 192k)."""
import subprocess
from common import OUT
from show_plan import load, songs

rows, _ = load()
show = sum(r["ms"] for r in rows) / 1000
S = songs()
inputs = sum((["-i", s] for s in S), [])
flt = "".join(f"[{i}:a]" for i in range(len(S))) + f"concat=n={len(S)}:v=0:a=1,apad,atrim=0:{show:.3f}," \
      f"afade=t=out:st={show - 4:.3f}:d=4[a]"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", flt, "-map", "[a]",
                "-c:a", "aac", "-b:a", "192k", str(OUT / "music.m4a")], check=True)
print(f"show {show:.2f}s -> music.m4a")
