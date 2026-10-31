#!/usr/bin/env python
"""Driver table report from driver/per_burst<tag>.csv + driver/fires<tag>.csv.
usage: report.py --tag <"" or _nopoly> --out DRIVER_TABLE_2026-10-31.md --stamp "<NY time line>" --cloud_head <sha>
Every "led" share is shown beside the same share on bucket-matched random non-burst minutes (chance).
"""
import argparse, json, os
import numpy as np, pandas as pd

MON = {"oct2026": "October 2026", "may2025": "May 2025"}
POST_SRC = ["financialjuice", "marketfeed", "WalterBloomberg", "firstsquaw", "insiderpaper", "WatcherGuru", "SCMPNews", "nhkworld",
            "GeoPWatch", "osintdefender", "Megatron_ron", "truth_social"]
OTHER_SRC = ["kalshi>=5c", "kalshi>=10c", "polymarket>=5c", "polymarket>=10c", "btc", "usdjpy", "clock"]
REASONS = ["scheduled clock", "headline", "Kalshi repricing", "Polymarket repricing", "cross-asset same minute only", "NO PUBLIC SIGNAL"]


def pct(a, b): return f"{100*a/b:.0f} %" if b else "–"


def led_sets(P, F):
    """per window: set of sources that LED (post / reprice with lead > 0; cross-asset fired; clock candidate), earliest lead per source"""
    led = {w: {} for w in P.wid}
    for r in F.itertuples():
        if r.kind in ("post", "reprice"):
            if not (np.isfinite(r.lead) and r.lead > 0): continue
        cur = led[r.wid].get(r.source)
        lead = r.lead if np.isfinite(r.lead) else np.nan
        if cur is None or (np.isfinite(lead) and (not np.isfinite(cur["lead"]) or lead > cur["lead"])):
            led[r.wid][r.source] = dict(lead=lead, sign=getattr(r, "sign", np.nan))
        if r.kind == "post":
            cur = led[r.wid].get("any Telegram / president post")
            if cur is None or lead > cur["lead"]: led[r.wid]["any Telegram / president post"] = dict(lead=lead, sign=np.nan)
    return led


def ranking(P, led, burst_mask, chance_mask):
    b = P[burst_mask]; c = P[chance_mask]; rows = []
    for src in ["any Telegram / president post"] + POST_SRC + OTHER_SRC:
        bl = [led[w][src] for w in b.wid if src in led[w]]
        cl = sum(1 for w in c.wid if src in led[w])
        leads = [x["lead"] for x in bl if np.isfinite(x["lead"])]
        hit = "–"
        if src in ("btc", "usdjpy"):
            dirs = dict(zip(b.wid, b.direction)); pairs = [(led[w][src]["sign"], dirs[w]) for w in b.wid if src in led[w]]
            pairs = [(s, d) for s, d in pairs if np.isfinite(s) and s != 0 and d != 0]
            if pairs: hit = f"{sum(s == d for s, d in pairs)}/{len(pairs)} ({pct(sum(s == d for s, d in pairs), len(pairs))})"
        med = f"{np.median(leads):.0f}" if leads else ("UNKNOWN (minute bars)" if src in ("btc", "usdjpy") else "–")
        if src == "clock": med = "0 to −119 (after the mark)"
        rows.append((src, len(bl), len(b), cl, len(c), med, hit))
    return rows


def first_channel(P, F, mask):
    sub = F[(F.kind == "post") & F.wid.isin(P[mask].wid) & (F.lead > 0)]
    if not len(sub): return {}
    first = sub.sort_values("lead", ascending=False).groupby("wid").head(1)
    return first.source.value_counts().to_dict()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=""); ap.add_argument("--out", required=True); ap.add_argument("--stamp", required=True)
    ap.add_argument("--cloud_head", required=True); ap.add_argument("--coverage", default="driver/coverage.json")
    a = ap.parse_args()
    P = pd.read_csv(f"driver/per_burst{a.tag}.csv"); F = pd.read_csv(f"driver/fires{a.tag}.csv")
    if "sign" not in F: F["sign"] = np.nan
    led = led_sets(P, F)
    cov = json.load(open(a.coverage)) if os.path.exists(a.coverage) else {}
    L = [f"### **{a.stamp}**\n",
         f"`HEAD` none (this folder is not a git repo) · cloud repo `bhavya-analytics-ai/news-engine-cloud` `{a.cloud_head}` · bursts from `reverse/bursts.csv` (October 2026) and `may2025/reverse/bursts.csv` (May 2025) · sources only: no brain tags, no screen flags, no earlier signal cells\n",
         "# Burst driver table — October 2026 and May 2025\n",
         "Window: 600 s before to 60 s after the burst minute's open (t0). **Led** = fired before t0 (lead > 0 s). Bitcoin / USDJPY are minute bars, so their lead is UNKNOWN: they count when the burst minute or the minute before moved ≥ 3× the asset's trailing-60-minute median 1-minute move. Clock = t0 inside the 2 minutes after 08:30 / 09:30 / 10:00 / 16:00 (weekdays), 18:00 reopen (Sun–Thu), 14:00 on the FOMC day (2026-10-28, 2025-05-07). Kalshi / Polymarket = a market whose traded price moved ≥ 5 (or 10) cents against its last trade before the window. **Chance** = the same scan on random non-burst minutes, matched by time-of-day bucket, same count as the bursts.\n",
         "BIG = |burst size| ≥ 30 pts (the `big` flag in bursts.csv: size = close of the last burst minute − open of the first). ALL = every burst (1-minute range ≥ 10 pts and ≥ 3× the trailing-60 median range).\n"]
    tiers = [("ALL", "burst", "chance_all", lambda p: p.kind == "burst", lambda p: p.kind == "chance_all"),
             ("BIG", "burst", "chance_big", lambda p: (p.kind == "burst") & p.big, lambda p: p.kind == "chance_big")]
    # ===== A =====
    L.append("## A. Source ranking — bursts each source led, against chance\n")
    for scope, mons in (("October 2026", ["oct2026"]), ("May 2025", ["may2025"]), ("Both months", ["oct2026", "may2025"])):
        for tier, _, _, bm, cm in tiers:
            mm = P.month.isin(mons)
            b_mask = bm(P) & mm; c_mask = cm(P) & mm
            L.append(f"\n### {scope} · {tier} ({int(b_mask.sum())} bursts, {int(c_mask.sum())} chance minutes)\n")
            L.append("| source | bursts led | share | chance minutes led | chance share | median lead s | direction hit |\n|---|---|---|---|---|---|---|")
            for src, nb, Nb, nc, Nc, med, hit in sorted(ranking(P, led, b_mask, c_mask), key=lambda r: -r[1] / max(r[2], 1)):
                L.append(f"| {src} | {nb} of {Nb} | {pct(nb, Nb)} | {nc} of {Nc} | {pct(nc, Nc)} | {med} | {hit} |")
            fc = first_channel(P, F, b_mask); fcc = first_channel(P, F, c_mask)
            if fc:
                L.append(f"\nFirst channel before the burst (earliest post, lead > 0): " + ", ".join(f"{k} {v}" for k, v in sorted(fc.items(), key=lambda x: -x[1])) +
                         f". Same on chance minutes: " + ", ".join(f"{k} {v}" for k, v in sorted(fcc.items(), key=lambda x: -x[1])) + ".")
    # ===== B =====
    L.append("\n## B. Reason distribution — one primary reason per burst, in the fixed order clock → headline → Kalshi → Polymarket → cross-asset → none\n")
    L.append("| month | tier | " + " | ".join(REASONS) + " |\n|---|---|" + "---|" * len(REASONS))
    for mon in ["oct2026", "may2025"]:
        for tier, _, _, bm, cm in tiers:
            for lab, mask in (("bursts", bm(P) & (P.month == mon)), ("chance", cm(P) & (P.month == mon))):
                g = P[mask]; vc = g.primary.value_counts()
                L.append(f"| {MON[mon]} | {tier} {lab} (n={len(g)}) | " + " | ".join(pct(vc.get(r, 0), len(g)) for r in REASONS) + " |")
    nps = {}
    for mon in ["oct2026", "may2025"]:
        for tier, _, _, bm, cm in tiers:
            g = P[bm(P) & (P.month == mon)]; c = P[cm(P) & (P.month == mon)]
            nps[(mon, tier)] = (int((g.primary == "NO PUBLIC SIGNAL").sum()), len(g), int((c.primary == "NO PUBLIC SIGNAL").sum()), len(c))
    L.append("\n**No public signal at all** (nothing from any source in the window, no clock, no cross-asset move): " +
             "; ".join(f"{MON[m]} {t} {a_} of {b_} ({pct(a_, b_)}) vs chance {c_} of {d_} ({pct(c_, d_)})" for (m, t), (a_, b_, c_, d_) in nps.items()) + ".")
    # ===== C =====
    L.append("\n## C. Every BIG burst\n")
    L.append("| time ET | size | dir | primary | sources that fired (lead s; + = before t0) |\n|---|---|---|---|---|")
    big = P[(P.kind == "burst") & P.big].sort_values("t0_utc")
    for r in big.itertuples():
        fires = json.loads(r.fires_json); parts = []
        posts = [f for f in fires if f["kind"] == "post"]
        by_ch = {}
        for f in posts: by_ch.setdefault(f["source"], []).append(f)
        for ch, fs in sorted(by_ch.items(), key=lambda kv: -max(x["lead"] for x in kv[1])):
            e = max(fs, key=lambda x: x["lead"])
            parts.append(f"**{ch}** {e['lead']:+.0f} ({len(fs)}): {e['detail'][:90]}")
        for src in ("kalshi>=10c", "kalshi>=5c", "polymarket>=10c", "polymarket>=5c"):
            fs = sorted([f for f in fires if f["source"] == src], key=lambda x: -x["lead"])
            if fs: parts.append(f"**{src}** {len(fs)} mkts, earliest {fs[0]['lead']:+.0f}: {fs[0]['detail'][:110]}")
        for f in fires:
            if f["kind"] in ("cross", "clock"): parts.append(f"**{f['source']}** {f['detail']}")
        cell = " · ".join(parts).replace("|", "/").replace("\n", " ") or "nothing"
        L.append(f"| {r.t0_et} | {r.size:+.1f} | {'+' if r.direction > 0 else '−'} | {r.primary} | {cell} |")
    # ===== D =====
    L.append("\n## D. Kalshi and Polymarket coverage\n")
    for k, v in cov.items(): L.append(f"- **{k}**: {v}")
    # ===== E =====
    L.append("\n## E. Limits\n")
    L.append("- Telegram posts fire in almost every 11-minute window (see chance column): a post before a burst is the base rate, not evidence, unless its share beats chance.")
    L.append("- Kalshi direction: `kalshi_prior.py` holds series lists per channel, not a Nasdaq sign map, so every Kalshi move is \"sign unknown\".")
    L.append("- Bitcoin / USDJPY are 1-minute bars: lead UNKNOWN; a same-minute move can be reaction, not cause.")
    L.append("- A market that had no trade before the window is not measured in that window (no reference price).")
    L.append("- Chance sets are the same size as the burst sets (85 to 462 minutes), so chance shares on BIG carry a few points of sampling noise.")
    open(a.out, "w").write("\n".join(L) + "\n")
    print("written", a.out)


if __name__ == "__main__":
    main()
