#!/usr/bin/env python
"""Report for driver/classes.py: per class, bursts led vs bucket-matched chance minutes, per month and tier, plus per-channel surge.
usage: classes_report.py --out DRIVER_CLASSES_2026-10-31.md --stamp "<NY time>" --cloud_head <sha>
"""
import argparse, json
import numpy as np, pandas as pd

MON = {"oct2026": "October 2026", "may2025": "May 2025"}
CLS = ["relay3", "relay5", "surge_all", "surge_channel", "new_story"]
DESC = {"relay3": "story posted by ≥ 3 sources within 60 s (time of the 3rd)", "relay5": "story posted by ≥ 5 sources within 60 s (time of the 5th)",
        "surge_all": "all sources pooled: posts in trailing 120 s above their 2-year 99th percentile", "surge_channel": "any one channel above its own 2-year 99th percentile of posts per 120 s",
        "new_story": "first arrival with no similar post (word Jaccard ≥ 0.3) in the previous hour"}


def pct(a, b): return f"{100*a/b:.0f} %" if b else "–"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--stamp", required=True); ap.add_argument("--cloud_head", required=True)
    a = ap.parse_args()
    W = pd.read_csv("driver/per_burst.csv", usecols=["wid", "month", "kind", "big", "t0_et", "size", "direction"])
    rows = [json.loads(l) for l in open("driver/classes_fires.jsonl")]
    led = {r["wid"]: {} for r in rows}
    for r in rows:
        for f in r["fires"]:
            if f["lead"] > 0:
                cur = led[r["wid"]].get(f["cls"])
                if cur is None or f["lead"] > cur["lead"]: led[r["wid"]][f["cls"]] = f
    chans = {}
    for r in rows:
        for f in r["fires"]:
            if f["cls"] == "surge_channel" and f["lead"] > 0: chans.setdefault(r["wid"], set()).add(f["what"])
    thr = json.load(open("driver/classes_surge_thresholds.json"))
    L = [f"### **{a.stamp}**\n",
         f"`HEAD` none (this folder is not a git repo) · cloud repo `bhavya-analytics-ai/news-engine-cloud` `{a.cloud_head}` · same bursts and chance minutes as `DRIVER_TABLE_2026-10-31.md` (`driver/per_burst.csv`) · post classes measured from the data only: no model tags, no keyword list\n",
         "# Post classes against bursts — October 2026 and May 2025\n",
         "Window 600 s before to 60 s after the burst minute's open; **led** = the class's event came before t0. Chance = the same on random non-burst minutes matched by time-of-day bucket, same count.\n",
         "| class | definition |\n|---|---|"] + [f"| {c} | {DESC[c]} |" for c in CLS]
    L.append("\n99th-percentile thresholds, posts per 120 s: " + ", ".join(f"{k} {v:.0f}" for k, v in sorted(thr.items())) + ".\n")
    tiers = [("ALL", lambda w: w.kind == "burst", lambda w: w.kind == "chance_all"), ("BIG", lambda w: (w.kind == "burst") & w.big, lambda w: w.kind == "chance_big")]
    L.append("## 1. Bursts led by each class, against chance\n")
    for scope, mons in (("October 2026", ["oct2026"]), ("May 2025", ["may2025"]), ("Both months", ["oct2026", "may2025"])):
        L.append(f"\n### {scope}\n\n| class | tier | bursts led | share | chance led | chance share | gap (pts) | median lead s |\n|---|---|---|---|---|---|---|---|")
        for c in CLS:
            for tier, bm, cm in tiers:
                b = W[bm(W) & W.month.isin(mons)]; ch = W[cm(W) & W.month.isin(mons)]
                nb = [led[w][c]["lead"] for w in b.wid if c in led.get(w, {})]; nc = sum(1 for w in ch.wid if c in led.get(w, {}))
                gap = 100 * len(nb) / len(b) - 100 * nc / len(ch)
                L.append(f"| {c} | {tier} | {len(nb)} of {len(b)} | {pct(len(nb), len(b))} | {nc} of {len(ch)} | {pct(nc, len(ch))} | {gap:+.0f} | {np.median(nb):.0f} |" if nb else
                         f"| {c} | {tier} | 0 of {len(b)} | 0 % | {nc} of {len(ch)} | {pct(nc, len(ch))} | {gap:+.0f} | – |")
    L.append("\n## 2. Which channel surged, both months (windows with that channel above its own 99th percentile before t0)\n")
    L.append("| channel | ALL bursts | chance | BIG bursts | chance |\n|---|---|---|---|---|")
    allch = sorted({c for s in chans.values() for c in s})
    for chn in allch:
        cells = []
        for tier, bm, cm in tiers:
            b = W[bm(W)]; ch = W[cm(W)]
            cells += [pct(sum(1 for w in b.wid if chn in chans.get(w, ())), len(b)), pct(sum(1 for w in ch.wid if chn in chans.get(w, ())), len(ch))]
        L.append(f"| {chn} | " + " | ".join(cells) + " |")
    L.append("\n## 3. BIG bursts with a relay-5 or surge-all event before them\n\n| time ET | size | classes (lead s) |\n|---|---|---|")
    big = W[(W.kind == "burst") & W.big].sort_values("t0_et")
    for w in big.itertuples():
        d = led.get(w.wid, {}); hit = [c for c in ("relay5", "surge_all") if c in d]
        if hit: L.append(f"| {w.t0_et} | {w.size:+.1f} | " + "; ".join(f"{c} {d[c]['lead']:+d}: {d[c]['what'][:80]}".replace("|", "/") for c in CLS if c in d) + " |")
    L.append("\n## 4. Limits\n")
    L.append("- No direction: these classes say a story is loud or new, not which way it points.")
    L.append("- Relays are matched by the corpus de-duplication (`story_id`); a story reworded by a channel counts as a different story.")
    L.append("- Thresholds are percentiles over two years of posts, set once, not tuned on the bursts.")
    L.append("- Chance sets are the same size as the burst sets; a gap of a few points on BIG (85 to 222 windows) is inside sampling noise.")
    open(a.out, "w").write("\n".join(L) + "\n"); print("written", a.out)


if __name__ == "__main__":
    main()
