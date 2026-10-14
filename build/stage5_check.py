"""Stage 5: validate order.csv against the rules; repair avoidable violations; write a check report.

A violation is "avoidable" if the count is above the per-rule lower bound; then we keep annealing
from the current order (more iterations) until it reaches the bound or stops improving.
Usage: python3 stage5_check.py [--manifest ...] [--order ...] [--report ...]
"""
import argparse, random
from collections import Counter
from common import OUT as BUILD, MANIFEST
from order_rules import Problem, load_manifest, read_order, write_order

ap = argparse.ArgumentParser()
ap.add_argument("--manifest", default=str(MANIFEST))
ap.add_argument("--order", default=str(BUILD / "order.csv"))
ap.add_argument("--report", default=str(BUILD / "order_check.md"))
args = ap.parse_args()

prob = Problem(load_manifest(args.manifest))
order, seed = read_order(args.order, prob)
assert sorted(order) == list(range(prob.N)), "order.csv must contain every manifest image exactly once"
lb = prob.lower_bounds()

def avoidable(o):
    cnt = Counter(v[0] for v in prob.violations(o))
    return sum(max(0, cnt[k] - lb.get(k, 0)) for k in cnt)

repairs = 0
rng = random.Random(int(seed or 0) + 99)
while avoidable(order) and repairs < 5:
    new, _ = prob.anneal(order, rng, min(120000, 600 * prob.N))
    if len(prob.violations(new)) >= len(prob.violations(order)):
        break
    order = new
    repairs += 1
if repairs:
    write_order(args.order, prob, order, seed)

viol = prob.violations(order)
cnt = Counter(v[0] for v in viol)
spread = prob.spread(order, "sender")
lines = [f"# בדיקת סדר", "", f"- שקופיות: {prob.N}", f"- seed: {seed}",
         f"- הפרות: {len(viol)} (מתוכן בלתי נמנעות לפי חסם תחתון: {sum(min(cnt[k], lb.get(k, 0)) for k in cnt)})",
         f"- סבבי תיקון: {repairs}", "", "## הפרות לפי כלל"]
for k in ("שולח רצוף", "3 רצופות מאותו מסלול", "3 רצופות מאותה קטגוריה"):
    if k in lb or cnt[k]:
        lines.append(f"- {k}: {cnt[k]} (חסם תחתון {lb.get(k, 0)})")
if viol:
    lines += ["", "## מיקומי הפרות", *[f"- שקופית {p}: {k} ({g})" for k, p, g in viol]]
lines += ["", "## פיזור לפי שולח (0 = פיזור אחיד מושלם, 1 = סטייה של רווח שלם בממוצע)"]
for g, v in sorted(spread.items(), key=lambda x: -x[1]):
    lines.append(f"- {g}: {v:.2f}")
open(args.report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines[:9 + len(lb)]))
