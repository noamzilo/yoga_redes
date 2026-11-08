# /// script
# requires-python = ">=3.10"
# dependencies = ["yt-dlp"]
# ///
"""Does YouTube search traffic for a query go to small channels or big ones?

Usage:
    uv run scripts/idea_check.py "yoga para dolor lumbar" "yoga para ciatica" [--n 20] [--small 20000]

For each query: the top N search results, each with views, the channel's
subscribers, views/subscribers, and a verdict on whether a new channel can compete.
No API key: uses yt-dlp. YouTube only.
"""
import argparse
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor

# ponytail: fixed thresholds, guesses. Tune them once we see which videos actually brought Majo messages.
MIN_VIEWS = 1000      # below this a high ratio is noise (50 subs, 300 views)
OUTLIER_RATIO = 3.0   # SMALL outlier: small channel, video seen by 3x more people than it has subscribers
MID_SUBS = 200_000    # MID outlier: channel under this size...
MID_RATIO = 5.0       # ...with a video seen by 5x its subscribers


def score(videos, small):
    """Pure. Adds ratio/small/outlier ("SMALL", "MID" or "") to each video, returns the summary for one query."""
    for v in videos:
        subs = v["subs"] or 0
        v["ratio"] = v["views"] / max(subs, 1)
        v["small"] = subs < small
        big_enough = v["views"] >= MIN_VIEWS
        if v["small"] and big_enough and v["ratio"] >= OUTLIER_RATIO:
            v["outlier"] = "SMALL"
        elif subs < MID_SUBS and big_enough and v["ratio"] >= MID_RATIO:
            v["outlier"] = "MID"
        else:
            v["outlier"] = ""
    total = sum(v["views"] for v in videos) or 1
    small_share = sum(v["views"] for v in videos if v["small"]) / total
    outliers = [v for v in videos if v["outlier"]]
    n_small = sum(v["outlier"] == "SMALL" for v in videos)
    if n_small >= 2 or small_share >= 0.2:
        verdict = "OPEN"
    elif outliers or small_share >= 0.05:
        verdict = "POSSIBLE"
    else:
        verdict = "CLOSED"
    return {"small_share": small_share, "outliers": outliers, "n_small": n_small, "verdict": verdict}


def search(query, n):
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True}) as ydl:
        res = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    return [e["id"] for e in res.get("entries") or [] if e and e.get("id")]


def details(vid):
    import yt_dlp
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            i = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
    except Exception:
        return None  # private, age-gated, removed: skip it
    return {
        "id": vid,
        "title": i.get("title") or "",
        "channel": i.get("channel") or "",
        "subs": i.get("channel_follower_count"),
        "views": i.get("view_count") or 0,
        "date": i.get("upload_date") or "",
        "minutes": round((i.get("duration") or 0) / 60, 1),
    }


def report(query, n, small):
    ids = search(query, n)
    with ThreadPoolExecutor(8) as pool:
        videos = [v for v in pool.map(details, ids) if v]
    s = score(videos, small)
    out = [f"## {query}", "",
           f"Verdict: **{s['verdict']}**. Small channels (<{small:,} subs) get "
           f"{s['small_share']:.0%} of the views in the top {len(videos)}. "
           f"Outliers: {s['n_small']} SMALL, {len(s['outliers']) - s['n_small']} MID.", "",
           "| # | Views | Subs | Views/subs | Outlier | Min | Uploaded | Channel | Title |",
           "|---|---|---|---|---|---|---|---|---|"]
    for k, v in enumerate(videos, 1):
        subs = f"{v['subs']:,}" if v["subs"] is not None else "?"
        title = v["title"].replace("|", "/")
        out.append(f"| {k} | {v['views']:,} | {subs} | {v['ratio']:.1f} | {v['outlier']} | "
                   f"{v['minutes']} | {v['date']} | {v['channel']} | [{title}](https://youtu.be/{v['id']}) |")
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("queries", nargs="+")
    p.add_argument("--n", type=int, default=20, help="search results per query")
    p.add_argument("--small", type=int, default=20000, help="a channel under this many subscribers is small")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console is cp1252; titles have emoji
    print(f"# Idea check, {datetime.date.today()}\n")
    for q in a.queries:
        print(report(q, a.n, a.small))


if __name__ == "__main__":
    main()
