"""Split the frame signal into static runs (photos) and moving runs (transitions / video clips)."""
import json, sys
import numpy as np
FPS = 24
STATIC = 0.6        # mean abs diff below this = no change
MIN_STILL = 12      # frames (0.5s) for a static run to count as a photo
MIN_CLIP = 48       # frames (2s) of continuous motion = a video clip, shorter = transition
f = np.load(sys.argv[1]).astype(np.int16)
d = np.abs(np.diff(f, axis=0)).mean(axis=1)
d = np.concatenate([[0], d])
static = d < STATIC
segs, i, n = [], 0, len(d)
while i < n:
    j = i
    while j < n and static[j] == static[i]:
        j += 1
    segs.append([bool(static[i]), i, j])
    i = j
# Static runs that are too short belong to motion; merge neighbours of equal type.
for s in segs:
    if s[0] and s[2] - s[1] < MIN_STILL:
        s[0] = False
merged = []
for s in segs:
    if merged and merged[-1][0] == s[0]:
        merged[-1][2] = s[2]
    else:
        merged.append(s)
out = []
for st, a, b in merged:
    kind = "still" if st else ("clip" if b - a >= MIN_CLIP else "transition")
    out.append({"kind": kind, "start": a, "end": b, "sec": round((b - a) / FPS, 2), "t": round(a / FPS, 2)})
json.dump(out, open(sys.argv[2], "w"), indent=0)
from collections import Counter
print(Counter(o["kind"] for o in out))
clips = [o for o in out if o["kind"] == "clip"]
print("clip lengths (s):", sorted(o["sec"] for o in clips))
print("still lengths pct:", np.percentile([o["sec"] for o in out if o["kind"] == "still"], [5, 50, 95]))
