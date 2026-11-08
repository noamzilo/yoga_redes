"""python scripts/test_idea_check.py  (no network, no dependencies)"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from idea_check import score


def v(views, subs):
    return {"views": views, "subs": subs}


# Big channels take everything: closed.
s = score([v(1_000_000, 2_000_000), v(500_000, 900_000), v(2_000, 50_000)], small=20000)
assert s["verdict"] == "CLOSED", s

# One small channel beats its size, but small channels get little traffic: possible.
s = score([v(1_000_000, 2_000_000), v(2_000, 500)], small=20000)
assert s["verdict"] == "POSSIBLE", s
assert s["outliers"][0]["views"] == 2_000

# Two small channels beat their size: open.
s = score([v(80_000, 5_000), v(30_000, 3_000), v(900_000, 1_000_000)], small=20000)
assert s["verdict"] == "OPEN", s
assert len(s["outliers"]) == 2

# A tiny channel with few views is noise, not an outlier.
s = score([v(500, 10), v(1_000_000, 500_000)], small=20000)
assert s["outliers"] == [] and s["verdict"] == "CLOSED", s

# A mid-size channel far above its size backs an idea, even when giants own the search.
s = score([v(353_000, 46_500), v(3_000_000, 3_700_000)], small=20000)
assert s["verdict"] == "POSSIBLE" and s["outliers"][0]["outlier"] == "MID", s

# A giant with a big ratio is not an outlier: it is just big.
s = score([v(8_000_000, 400_000)], small=20000)
assert s["outliers"] == [], s

# Missing subscriber count does not crash and counts as small.
s = score([v(5_000, None)], small=20000)
assert s["verdict"] == "OPEN", s

print("ok")
