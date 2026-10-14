"""Decode the video at low resolution and save per-frame difference signal (numpy)."""
import subprocess, sys
import numpy as np
W, H = 160, 90
src, out = sys.argv[1], sys.argv[2]
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={W}:{H}", "-pix_fmt", "gray",
                      "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
frames = []
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H:
        break
    frames.append(np.frombuffer(b, np.uint8))
f = np.stack(frames)
np.save(out, f)
d = np.abs(np.diff(f.astype(np.int16), axis=0)).mean(axis=1)
print(len(f), "frames; diff percentiles", np.percentile(d, [10, 50, 75, 90, 95, 99]).round(2))
