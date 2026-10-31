#!/usr/bin/env python
"""Coverage notes for section D: Kalshi and Polymarket markets / trades per month and the resolution obtained.
usage: coverage.py -> driver/coverage.json
"""
import json, os
import pandas as pd

MONTHS = {"oct2026": ("2026-09-30", "2026-11-01", "October 2026"), "may2025": ("2025-04-30", "2025-06-01", "May 2025")}
out = {}
tk, ts = [], []
for d in ("corpus/kalshi", "corpus/kalshi2"):
    for l in open(f"{d}/trades.jsonl"):
        o = json.loads(l); tk.append(o["ticker"]); ts.append(o["created_time"][:19])
K = pd.DataFrame(dict(tk=tk, ts=ts)).drop_duplicates()
mk = set()
for d in ("corpus/kalshi", "corpus/kalshi2"):
    for l in open(f"{d}/markets.jsonl"): mk.add(json.loads(l)["ticker"])
for m, (a, b, name) in MONTHS.items():
    g = K[(K.ts >= a) & (K.ts < b)]
    out[f"Kalshi, {name}"] = (f"{g.tk.nunique():,} markets traded, {len(g):,} trades (window {a} to {b} UTC); corpus total {len(mk):,} markets, "
                              f"trade stamps to the microsecond; series are the macro / tariff / geopolitics list in corpus_build/kalshi_pull.py, not every Kalshi market")
notes = json.load(open("corpus/polymarket/universe_notes.json")) if os.path.exists("corpus/polymarket/universe_notes.json") else []
for m, (a, b, name) in MONTHS.items():
    uf = f"corpus/polymarket/universe_{m}.jsonl"; tf = f"corpus/polymarket/trades_{m}.jsonl"
    if not os.path.exists(uf): out[f"Polymarket, {name}"] = "NOT PULLED"; continue
    U = [json.loads(l) for l in open(uf)]
    s = f"universe {len(U):,} markets (lifetime volume ≥ $50k) in events tagged economy / fed / fed-rates / finance / business / stocks / economic-policy / inflation / tariffs / trade-war / geopolitics / world / middle-east / china / iran / trump / trump-presidency / politics and overlapping the month"
    trunc = [n for n in notes if n["month"] == m and n["status"] != "complete"]
    if trunc: s += "; TRUNCATED tags: " + ", ".join(f"{n['tag']} ({n['status']})" for n in trunc)
    tfs = sorted(__import__("glob").glob(f"corpus/polymarket/trades_{m}*.jsonl"))
    if tfs:
        n = 0; cids = set(); lo = hi = None
        for l in (l for f_ in tfs for l in open(f_)):
            o = json.loads(l); n += 1; cids.add(o["cid"]); t = o["ts"]; lo = t if lo is None or t < lo else lo; hi = t if hi is None or t > hi else hi
        s += (f"; trades pulled {n:,} on {len(cids):,} markets (data-api /trades per market with start/end, second stamps), "
              f"{pd.Timestamp(lo, unit='s', tz='UTC'):%Y-%m-%d %H:%M} to {pd.Timestamp(hi, unit='s', tz='UTC'):%Y-%m-%d %H:%M} UTC")
    else:
        s += "; trades NOT pulled"
    out[f"Polymarket, {name}"] = s
out["Polymarket endpoints"] = ("CLOB prices-history returns 1-minute points for a closed May 2025 market when startTs/endTs are given, but returned nothing for "
                               "another closed market and for interval=max; data-api /trades with market + start/end returns second-stamped trades back to May 2025 "
                               "(offset capped at 10,000, handled by splitting the time range); without a market filter it ignores start/end and returns today's trades; "
                               "the Goldsky orderbook subgraph URL returned 404 (not found) under every version tried. Used: data-api trades (finest).")
json.dump(out, open("driver/coverage.json", "w"), indent=1)
for k, v in out.items(): print(k, ":", v)
