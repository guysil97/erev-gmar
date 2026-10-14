"""Stage 4: order the slides by the rules in order_rules.py.

Usage: python3 stage4_order.py [--seed N] [--manifest build/manifest.csv] [--out build/order.csv]
Same seed -> same order. Change the seed for a new shuffle.
"""
import argparse, random, time
from pathlib import Path
from common import BUILD, MANIFEST
from order_rules import Problem, load_manifest, write_order

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=2026)
ap.add_argument("--manifest", default=str(MANIFEST))
ap.add_argument("--out", default=str(BUILD / "order.csv"))
ap.add_argument("--restarts", type=int, default=4)
args = ap.parse_args()

prob = Problem(load_manifest(args.manifest))
iters = min(60000, 300 * prob.N)
best, best_c = None, float("inf")
t = time.time()
for k in range(args.restarts):
    rng = random.Random(args.seed * 1000 + k)
    order, c = prob.anneal(prob.initial(rng), rng, iters)
    if c < best_c:
        best, best_c = order, c
write_order(args.out, prob, best, args.seed)
print(f"slides: {prob.N}  hard violations: {len(prob.violations(best))}  cost: {best_c:.2f}  "
      f"seed: {args.seed}  ({time.time() - t:.0f}s) -> {args.out}")
