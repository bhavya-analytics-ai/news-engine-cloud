#!/usr/bin/env python
"""Burst driver scan: for every MNQ burst (October 2026, May 2025) and for bucket-matched random non-burst minutes,
record every public source that fired in the window [t0 - 600 s, t0 + 60 s], t0 = the burst minute's open.
Sources only: Telegram (11 channels, every post, no filter), president's posts, Kalshi trades, Polymarket trades,
Bitcoin / USDJPY minute bars, the clock. No brain tags, no screen flags, no earlier signal cells.
usage (from the news_engine folder): driver/scan.py --workers 3  -> driver/per_burst.csv, driver/fires.csv
"""
import argparse, glob, json, os, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd

CLOUD = os.path.expanduser("~/news-engine-cloud")
MONTHS = {"oct2026": dict(bursts=f"{CLOUD}/reverse/bursts.csv", bars=f"{CLOUD}/data/mnq_1m_oct2026.csv.gz", fomc="2026-10-28"),
          "may2025": dict(bursts=f"{CLOUD}/may2025/reverse/bursts.csv", bars=f"{CLOUD}/may2025/data/mnq_1m_may2025.csv.gz", fomc="2025-05-07")}
BEFORE, AFTER = 600, 60
MOVE_TIERS = (0.05, 0.10)
BUCKETS = [("Asia", 18 * 60, 3 * 60), ("London", 3 * 60, 8 * 60 + 30), ("pre-open", 8 * 60 + 30, 9 * 60 + 30),
           ("NY open", 9 * 60 + 30, 10 * 60 + 30), ("midday", 10 * 60 + 30, 14 * 60), ("close", 14 * 60, 16 * 60),
           ("after hours", 16 * 60, 18 * 60)]                     # same buckets as reverse/reverse_lookup.py
SEED = 20261031
LOG = "driver/progress.log"


def log(msg):
    with open(LOG, "a") as f: f.write(f"{time.strftime('%H:%M:%S')} scan: {msg}\n")


def bucket_of(m):
    for name, lo, hi in BUCKETS:
        if (lo <= m < hi) if lo < hi else (m >= lo or m < hi): return name


# ---------------- loaders (run in worker processes) ----------------
def load_posts(path):
    ts, tx = [], []
    for l in open(path):
        o = json.loads(l)
        ts.append(o["ts"]); tx.append((o.get("text") or "").replace("\n", " "))
    t = pd.to_datetime(pd.Series(ts), utc=True, format="ISO8601").dt.as_unit("ns").astype("int64").values // 10**9
    order = np.argsort(t, kind="stable")
    return np.asarray(t)[order], [tx[i] for i in order]


def load_kalshi(path):
    tid, tk, ts, p, n = [], [], [], [], []
    for l in open(path):
        o = json.loads(l)
        tid.append(o["trade_id"]); tk.append(o["ticker"]); ts.append(o["created_time"])
        p.append(float(o["yes_price_dollars"])); n.append(float(o.get("count_fp") or 0))
    t = pd.to_datetime(pd.Series(ts), utc=True, format="ISO8601").dt.as_unit("ns").astype("int64").values / 1e9
    return pd.DataFrame(dict(tid=tid, key=tk, ts=t, p=p, n=n))


def load_kalshi_markets(path):
    out = {}
    for l in open(path):
        m = json.loads(l); out[m["ticker"]] = m.get("title") or m["ticker"]
        if m.get("yes_sub_title"): out[m["ticker"]] += f" [{m['yes_sub_title']}]"
    return out


def load_poly(mon):
    files = sorted(glob.glob(f"corpus/polymarket/trades_{mon}*.jsonl"))       # part files hold disjoint markets
    if not files: return pd.DataFrame(columns=["key", "ts", "p", "n"])
    rows = [json.loads(l) for f in files for l in open(f)]
    d = pd.DataFrame(rows)
    d["p"] = np.where(d.oi == 0, d.price, 1 - d.price)              # price of outcome 0 (Yes) for every trade
    return d.rename(columns={"cid": "key", "size": "n"})[["key", "ts", "p", "n"]].astype({"ts": float})


class Book:
    """Trades of many markets: global time order for window slicing, per-market order for the last price before a time."""
    def __init__(self, d):
        d = d.sort_values(["key", "ts"]).reset_index(drop=True)
        self.key = d.key.values; self.ts = d.ts.values; self.p = d.p.values; self.n = d.n.values
        k = pd.Series(self.key); first = ~k.duplicated()
        starts = np.flatnonzero(first.values); ends = np.r_[starts[1:], len(k)]
        self.block = dict(zip(self.key[starts], zip(starts, ends)))
        self.g = np.argsort(self.ts, kind="stable"); self.gts = self.ts[self.g]

    def fires(self, t0, tier):
        lo, hi = np.searchsorted(self.gts, t0 - BEFORE, "left"), np.searchsorted(self.gts, t0 + AFTER, "right")
        out = []
        for key in set(self.key[self.g[lo:hi]]):
            s, e = self.block[key]; ts = self.ts[s:e]
            i0 = np.searchsorted(ts, t0 - BEFORE, "left"); i1 = np.searchsorted(ts, t0 + AFTER, "right")
            if i0 == 0: continue                                     # no trade before the window: cannot measure
            p0 = self.p[s + i0 - 1]; pw = self.p[s + i0:s + i1]
            mv = np.flatnonzero(np.abs(pw - p0) >= tier - 1e-9)
            if len(mv) == 0: continue
            j = mv[0]
            out.append(dict(key=key, lead=float(t0 - ts[i0 + j]), p0=float(p0), p1=float(pw[j]), max_move=float(np.max(np.abs(pw - p0))),
                            n_trades=int(i1 - i0)))
        return out


def init_conf():
    out = {}
    for name, fn in (("btc", "X_BTCUSD.csv.gz"), ("usdjpy", "C_USDJPY.csv.gz")):
        c = pd.read_csv(f"corpus/confirmers/{fn}", usecols=["t_ms", "open", "close"])
        c["t"] = c.t_ms // 1000; c["r"] = (c.close - c.open) / c.open * 100
        c["med60"] = c.r.abs().shift(1).rolling(60, min_periods=30).median()
        out[name] = c.set_index("t")[["r", "med60"]]
    return out


# ---------------- per-window scan ----------------
G = {}


def clock_marks(et, fomc):
    d = et.normalize(); wd = et.weekday(); marks = []
    if wd < 5:
        marks += [("08:30 print", d + pd.Timedelta(hours=8, minutes=30)), ("09:30 open", d + pd.Timedelta(hours=9, minutes=30)),
                  ("10:00 print", d + pd.Timedelta(hours=10)), ("16:00 close", d + pd.Timedelta(hours=16))]
        if et.strftime("%Y-%m-%d") == fomc: marks.append(("14:00 FOMC", d + pd.Timedelta(hours=14)))
    if wd in (6, 0, 1, 2, 3): marks.append(("18:00 reopen", d + pd.Timedelta(hours=18)))
    return marks


def scan_one(w):
    t0 = int(w["t0"]); fires = []
    for ch, (ts, tx) in G["posts"].items():
        lo, hi = np.searchsorted(ts, t0 - BEFORE, "left"), np.searchsorted(ts, t0 + AFTER, "right")
        for k in range(lo, hi):
            fires.append(dict(source=ch, kind="post", lead=float(t0 - ts[k]), detail=tx[k][:300]))
    for book, src in (("kalshi", "kalshi"), ("poly", "polymarket")):
        b = G["books"].get(f"{book}_{w['month']}") if book == "poly" else G["books"]["kalshi"]
        if b is None: continue
        for tier in MOVE_TIERS:
            for f in b.fires(t0, tier):
                title = G["titles"].get(f["key"], f["key"]) if book == "kalshi" else G["poly_q"].get(f["key"], f["key"])
                fires.append(dict(source=f"{src}>={int(tier*100)}c", kind="reprice", lead=f["lead"],
                                  detail=f"{f['key']} | {title} | {f['p0']:.3f}->{f['p1']:.3f} max {f['max_move']:.3f} | {f['n_trades']} trades"))
    for name, c in G["conf"].items():
        rows = [c.loc[t] if t in c.index else None for t in (t0 - 60, t0)]
        for lab, r in zip(("minute before", "burst minute"), rows):
            if r is None or not np.isfinite(r.med60) or r.med60 <= 0: continue
            if abs(r.r) >= 3 * r.med60:
                fires.append(dict(source=name, kind="cross", lead=np.nan, detail=f"{lab} {r.r:+.3f}% (3x trailing median {r.med60:.3f}%)",
                                  sign=int(np.sign(r.r))))
    et = pd.Timestamp(t0, unit="s", tz="UTC").tz_convert("America/New_York")
    for lab, mk in clock_marks(et, w["fomc"]):
        dt_ = (et - mk).total_seconds()
        if 0 <= dt_ < 120: fires.append(dict(source="clock", kind="clock", lead=-dt_, detail=lab))
    # primary reason, in the fixed order of evidence
    led = lambda pred: [f for f in fires if pred(f) and np.isfinite(f["lead"]) and f["lead"] > 0]
    if any(f["kind"] == "clock" for f in fires): primary = "scheduled clock"
    elif led(lambda f: f["kind"] == "post"): primary = "headline"
    elif led(lambda f: f["source"] == "kalshi>=5c"): primary = "Kalshi repricing"
    elif led(lambda f: f["source"] == "polymarket>=5c"): primary = "Polymarket repricing"
    elif any(f["kind"] == "cross" for f in fires): primary = "cross-asset same minute only"
    else: primary = "NO PUBLIC SIGNAL"
    return w["wid"], primary, fires


def init_worker(state):
    G.update(state)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=12); ap.add_argument("--no_poly", action="store_true")
    ap.add_argument("--tag", default=""); a = ap.parse_args(); t_start = time.time()
    # ---- windows ----
    W = []; wid = 0
    rng = np.random.default_rng(SEED)
    for mon, cfg in MONTHS.items():
        B = pd.read_csv(cfg["bursts"], usecols=["start_utc", "end_utc", "size", "direction", "abs_size", "ft15", "max_range", "bucket", "big", "start_et"])
        B["t0"] = pd.to_datetime(B.start_utc, utc=True).dt.as_unit("ns").astype("int64") // 10**9
        B["t1"] = pd.to_datetime(B.end_utc, utc=True).dt.as_unit("ns").astype("int64") // 10**9
        for r in B.itertuples():
            W.append(dict(wid=wid, month=mon, kind="burst", big=bool(r.big), t0=int(r.t0), bucket=r.bucket, size=r.size, direction=int(r.direction),
                          ft15=r.ft15, fomc=cfg["fomc"])); wid += 1
        bars = pd.read_csv(cfg["bars"], usecols=["ts_utc"]); bt = pd.to_datetime(bars.ts_utc, utc=True)
        t = (bt.dt.as_unit("ns").astype("int64") // 10**9).values[60:]               # same 60-bar warm-up as the burst rule
        inb = np.zeros(len(t), bool)
        for s, e in zip(B.t0, B.t1): inb |= (t >= s) & (t <= e)
        et = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York")
        bk = np.array([bucket_of(h * 60 + m) for h, m in zip(et.hour, et.minute)])
        pool = pd.DataFrame(dict(t=t[~inb], bucket=bk[~inb]))
        for kind, sub in (("chance_all", B), ("chance_big", B[B.big])):
            for b, n in sub.bucket.value_counts().items():
                cand = pool[pool.bucket == b].t.values
                for x in rng.choice(cand, n, replace=False):
                    W.append(dict(wid=wid, month=mon, kind=kind, big=kind == "chance_big", t0=int(x), bucket=b, size=np.nan, direction=0,
                                  ft15=np.nan, fomc=cfg["fomc"])); wid += 1
    log(f"windows {len(W)} (bursts {sum(w['kind']=='burst' for w in W)}); loading sources in parallel")
    # ---- sources, loaded in parallel ----
    post_files = sorted(glob.glob("corpus/telegram/*.jsonl")) + ["corpus/truth/truth.jsonl"]
    with ProcessPoolExecutor(min(a.workers, 3)) as ex:              # 8 GB machine: at most 3 loaders at once
        fp = {f: ex.submit(load_posts, f) for f in post_files}
        fk = [ex.submit(load_kalshi, f"{d}/trades.jsonl") for d in ("corpus/kalshi", "corpus/kalshi2")]
        fm = [ex.submit(load_kalshi_markets, f"{d}/markets.jsonl") for d in ("corpus/kalshi", "corpus/kalshi2")]
        fpm = {} if a.no_poly else {m: ex.submit(load_poly, m) for m in MONTHS}
        posts = {}
        for f, fu in fp.items():
            name = "truth_social" if "truth" in f else os.path.basename(f)[:-6]
            posts[name] = fu.result()
        K = pd.concat([x.result() for x in fk]); n_raw = len(K); K = K.drop_duplicates("tid")
        titles = {}
        for x in fm: titles.update(x.result())
        P = {m: fu.result() for m, fu in fpm.items()}
    log(f"loaded: posts {sum(len(v[0]) for v in posts.values())}, kalshi trades {len(K)} (raw {n_raw}), "
        f"polymarket trades {', '.join(f'{m} {len(d)}' for m, d in P.items())}; {time.time()-t_start:.0f}s")
    poly_q = {}
    for m in MONTHS:
        f = f"corpus/polymarket/universe_{m}.jsonl"
        if os.path.exists(f):
            for l in open(f):
                u = json.loads(l); poly_q[u["condition_id"]] = u["question"]
    books = {"kalshi": Book(K)}
    for m, d in P.items():
        if len(d): books[f"poly_{m}"] = Book(d)
    state = dict(posts=posts, books=books, titles=titles, poly_q=poly_q, conf=init_conf())
    log(f"books built; scanning {len(W)} windows with {a.workers} processes; {time.time()-t_start:.0f}s")
    init_worker(state); res = {}                                   # one process: each window is milliseconds, and copying the books to workers would not fit in 8 GB
    for i, w in enumerate(W, 1):
        wid_, primary, fires = scan_one(w); res[wid_] = (primary, fires)
        if i % 200 == 0 or i == len(W):
            el = time.time() - t_start; log(f"scanned {i}/{len(W)} ({100*i/len(W):.0f} %), elapsed {el/60:.1f} min")
    # ---- outputs ----
    rows, long = [], []
    for w in W:
        primary, fires = res[w["wid"]]
        et = pd.Timestamp(w["t0"], unit="s", tz="UTC").tz_convert("America/New_York")
        row = dict(wid=w["wid"], month=w["month"], kind=w["kind"], big=w["big"], t0_utc=pd.Timestamp(w["t0"], unit="s", tz="UTC").strftime("%Y-%m-%d %H:%M:%S"),
                   t0_et=et.strftime("%Y-%m-%d %H:%M"), bucket=w["bucket"], size=w["size"], direction=w["direction"], ft15=w["ft15"], primary=primary,
                   n_fires=len(fires), fires_json=json.dumps(fires, default=float))
        rows.append(row)
        for f in fires: long.append(dict(wid=w["wid"], month=w["month"], wkind=w["kind"], big=w["big"], **f))
    pd.DataFrame(rows).to_csv(f"driver/per_burst{a.tag}.csv", index=False)
    pd.DataFrame(long).to_csv(f"driver/fires{a.tag}.csv", index=False)
    log(f"DONE: per_burst.csv {len(rows)} rows, fires.csv {len(long)} rows; {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
