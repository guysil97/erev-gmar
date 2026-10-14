"""Ordering rules shared by stage 4 (ordering) and stage 5 (validation).

Hard rules (each violation is counted and logged):
  - no two consecutive slides from the same sender
  - no more than two consecutive slides from the same route
  - no more than two consecutive slides from the same category (if classified)
"Unknown" (לא ידוע) sender/route is not treated as one person/route, so it is exempt from the hard rules.

Soft rules (minimized): every sender's photos (and every route's) are spread evenly across the whole show:
the k-th of n photos of a group should sit near position (k + 0.5) * N / n. This also handles
"a much smaller group is spread evenly across the whole length, not alternating".
"""
import csv
import math

import numpy as np
import random
from collections import Counter

from common import UNKNOWN

HARD = 1000.0
W_SENDER, W_ROUTE, W_CAT = 1.0, 0.5, 0.2


def load_manifest(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    for r in rows:
        r.setdefault("קטגוריה", "")
    return rows


class Problem:
    def __init__(self, rows):
        self.rows = rows
        self.N = len(rows)
        self.has_cat = any(r.get("קטגוריה") for r in rows)
        self.attrs = {"sender": [r["שולח"] for r in rows], "route": [r["מסלול"] for r in rows],
                      "cat": [r.get("קטגוריה", "") for r in rows]}
        # Integer codes for fast scoring; exempt values (unknown / empty) get unique negative codes.
        self.codes = {}
        for key, vals in self.attrs.items():
            names = sorted({v for v in vals if v and v != UNKNOWN})
            idx = {v: k for k, v in enumerate(names)}
            self.codes[key] = np.array([idx[v] if v in idx else -(i + 1) for i, v in enumerate(vals)])

    def _hard_mask(self, o):
        """Boolean arrays marking where each hard rule is violated (index = first slide, 0-based)."""
        s, r = self.codes["sender"][o], self.codes["route"][o]
        m_s = s[:-1] == s[1:]
        m_r = (r[:-2] == r[1:-1]) & (r[1:-1] == r[2:])
        if self.has_cat:
            c = self.codes["cat"][o]
            m_c = (c[:-2] == c[1:-1]) & (c[1:-1] == c[2:])
        else:
            m_c = np.zeros(max(0, self.N - 2), bool)
        return m_s, m_r, m_c

    def _spread_fast(self, o, key):
        g = self.codes[key][o]
        total = 0.0
        for v in np.unique(g[g >= 0]):
            ps = np.nonzero(g == v)[0]
            n = len(ps)
            if n < 2:
                continue
            gap = self.N / n
            total += np.abs(ps - (np.arange(n) + 0.5) * gap).sum() / n / gap
        return total

    # ---------- hard violations ----------
    def violations(self, order):
        s = [self.attrs["sender"][i] for i in order]
        r = [self.attrs["route"][i] for i in order]
        c = [self.attrs["cat"][i] for i in order]
        out = []
        for p in range(self.N - 1):
            if s[p] == s[p + 1] and s[p] != UNKNOWN:
                out.append(("שולח רצוף", p + 1, s[p]))
        for p in range(self.N - 2):
            if r[p] == r[p + 1] == r[p + 2] and r[p] != UNKNOWN:
                out.append(("3 רצופות מאותו מסלול", p + 1, r[p]))
            if self.has_cat and c[p] == c[p + 1] == c[p + 2] and c[p]:
                out.append(("3 רצופות מאותה קטגוריה", p + 1, c[p]))
        return out  # positions are 1-based slide numbers

    def lower_bounds(self):
        """Violations that no order can avoid (per rule, ignoring interactions between rules)."""
        lb = {}
        sc = Counter(x for x in self.attrs["sender"] if x != UNKNOWN)
        m = max(sc.values(), default=0)
        lb["שולח רצוף"] = max(0, 2 * m - self.N - 1)
        for key, name in (("route", "3 רצופות מאותו מסלול"), ("cat", "3 רצופות מאותה קטגוריה")):
            cnt = Counter(x for x in self.attrs[key] if x and x != UNKNOWN)
            if key == "cat" and not self.has_cat:
                continue
            lb[name] = sum(max(0, v - 2 * (self.N - v + 1)) for v in cnt.values())
        return lb

    # ---------- spread ----------
    def spread(self, order, key):
        """Per group: mean distance from the ideal even positions, in units of the group's ideal gap."""
        pos = {}
        for p, i in enumerate(order):
            pos.setdefault(self.attrs[key][i], []).append(p)
        res = {}
        for g, ps in pos.items():
            n = len(ps)
            if n < 2 or g == "":
                continue
            gap = self.N / n
            res[g] = sum(abs(p - (k + 0.5) * gap) for k, p in enumerate(ps)) / n / gap
        return res

    def cost(self, order):
        o = np.asarray(order)
        c = HARD * sum(int(m.sum()) for m in self._hard_mask(o))
        c += W_SENDER * self._spread_fast(o, "sender") + W_ROUTE * self._spread_fast(o, "route")
        if self.has_cat:
            c += W_CAT * self._spread_fast(o, "cat")
        return c

    def bad_positions(self, order):
        m_s, m_r, m_c = self._hard_mask(np.asarray(order))
        return np.concatenate([np.nonzero(m_s)[0], np.nonzero(m_r)[0], np.nonzero(m_c)[0]])

    # ---------- optimisation ----------
    def initial(self, rng):
        """Stratified start: each photo gets a jittered ideal slot within its sender, then sort."""
        groups = {}
        for i, s in enumerate(self.attrs["sender"]):
            groups.setdefault(s, []).append(i)
        key = {}
        for g, idx in groups.items():
            rng.shuffle(idx)
            n = len(idx)
            for k, i in enumerate(idx):
                key[i] = (k + rng.random()) / n
        return sorted(range(self.N), key=lambda i: key[i])

    def anneal(self, order, rng, iters):
        order = list(order)
        cur = self.cost(order)
        best, best_c = list(order), cur
        T0, T1 = 2.0, 0.005
        for t in range(iters):
            T = T0 * (T1 / T0) ** (t / max(1, iters - 1))
            v = self.bad_positions(order) if rng.random() < 0.5 else ()
            a = (int(v[rng.randrange(len(v))]) + rng.randrange(3)) if len(v) else rng.randrange(self.N)
            a = min(a, self.N - 1)
            b = rng.randrange(self.N)
            if a == b:
                continue
            order[a], order[b] = order[b], order[a]
            new = self.cost(order)
            if new <= cur or rng.random() < math.exp((cur - new) / T):
                cur = new
                if cur < best_c:
                    best, best_c = list(order), cur
            else:
                order[a], order[b] = order[b], order[a]
        return best, best_c


def write_order(path, prob, order, seed):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["מיקום", "קובץ", "שולח", "מסלול", "קטגוריה", "seed"])
        for p, i in enumerate(order, 1):
            r = prob.rows[i]
            w.writerow([p, r["קובץ"], r["שולח"], r["מסלול"], r.get("קטגוריה", ""), seed])


def read_order(path, prob):
    by_file = {r["קובץ"]: i for i, r in enumerate(prob.rows)}
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    return [by_file[r["קובץ"]] for r in rows], (rows[0]["seed"] if rows else "")
