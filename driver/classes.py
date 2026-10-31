#!/usr/bin/env python
"""Post classes measured from the data only (no model tags, no keyword list), scored on the same burst and chance windows
as driver/scan.py (driver/per_burst.csv). Window [t0 - 600 s, t0 + 60 s]; led = event time before t0.
Classes:
  relay3 / relay5   a story posted by >= 3 (>= 5) distinct sources within 60 s of its first arrival; event time = the 3rd (5th) source's post
  surge_channel     a post at which its own channel has more posts in the trailing 120 s than in 99 % of that channel's posts (2 years)
  surge_all         the same on all sources pooled
  new_story         a first arrival whose word set has Jaccard < 0.3 with every post of the previous hour (any source)
Progress: driver/classes_progress.log (done/total, %, elapsed, ETA). Each window's result is appended to driver/classes_fires.jsonl
as it finishes; a rerun skips windows already there.
usage: classes.py
"""
import json, os, re, time
import numpy as np, pandas as pd

BEFORE, AFTER = 600, 60
LOG = "driver/classes_progress.log"; OUT = "driver/classes_fires.jsonl"
WORD = re.compile(r"[a-z]{4,}")


def log(msg):
    with open(LOG, "a") as f: f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def main():
    t_start = time.time()
    log("START: expected 5-10 min; loading items")
    W = pd.read_csv("driver/per_burst.csv", usecols=["wid", "month", "kind", "big", "t0_utc"])
    W["t0"] = pd.to_datetime(W.t0_utc, utc=True).dt.as_unit("ns").astype("int64") // 10**9
    lo_all, hi_all = W.t0.min() - BEFORE - 3600 - 86400, W.t0.max() + AFTER + 60
    I = pd.read_csv("corpus/items.csv.gz", usecols=["ts", "source", "story_id", "lag_s", "text"])
    I["t"] = pd.to_datetime(I.ts, utc=True, format="ISO8601").dt.as_unit("ns").astype("int64") // 10**9
    I = I.sort_values("t").reset_index(drop=True); I["text"] = I.text.fillna("").astype(str)
    log(f"items {len(I)} loaded, {time.time()-t_start:.0f}s; building classes")
    # ---- relay events ----
    R = I.sort_values(["story_id", "lag_s", "t"]).drop_duplicates(["story_id", "source"])
    R["rank"] = R.groupby("story_id").cumcount()
    ev = {}
    for k, name in ((2, "relay3"), (4, "relay5")):
        e = R[(R["rank"] == k) & (R.lag_s <= 60)]
        ev[name] = (e.t.values, e.story_id.values)
    # ---- surges (2-year thresholds) ----
    thr = {}; surge_t, surge_src = [], []
    for src, g in I.groupby("source"):
        t = g.t.values; cnt = np.arange(len(t)) - np.searchsorted(t, t - 120, "right") + 1
        thr[src] = float(np.percentile(cnt, 99)); m = cnt > thr[src]
        surge_t.append(t[m]); surge_src += [src] * int(m.sum())
    st = np.concatenate(surge_t); o = np.argsort(st, kind="stable"); ev["surge_channel"] = (st[o], np.array(surge_src, dtype=object)[o])
    t = I.t.values; cnt = np.arange(len(t)) - np.searchsorted(t, t - 120, "right") + 1
    thr["ALL"] = float(np.percentile(cnt, 99)); m = cnt > thr["ALL"]; ev["surge_all"] = (t[m], np.array([f"{c} posts/120s" for c in cnt[m]], dtype=object))
    json.dump(thr, open("driver/classes_surge_thresholds.json", "w"), indent=1)
    log(f"relay3 {len(ev['relay3'][0])}, relay5 {len(ev['relay5'][0])}, surge_channel {len(ev['surge_channel'][0])}, surge_all {len(ev['surge_all'][0])} events; "
        f"{time.time()-t_start:.0f}s")
    # ---- per window (new_story computed only for posts inside windows) ----
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT): done.add(json.loads(l)["wid"])
    todo = W[~W.wid.isin(done)]
    log(f"windows {len(W)}, already on disk {len(done)}, to do {len(todo)}")
    words = {}
    def wset(i):
        if i not in words: words[i] = set(WORD.findall(I.text.iat[i].lower()))
        return words[i]
    first = (I.lag_s.values == 0); sid = I.story_id.values; src = I.source.values
    t0w = time.time()
    with open(OUT, "a") as f:
        for n, w in enumerate(todo.itertuples(), 1):
            t0 = int(w.t0); fires = []
            for name, (et, lab) in ev.items():
                a, b = np.searchsorted(et, t0 - BEFORE, "left"), np.searchsorted(et, t0 + AFTER, "right")
                for k in range(a, b): fires.append(dict(cls=name, lead=int(t0 - et[k]), what=str(lab[k])))
            a, b = np.searchsorted(t, t0 - BEFORE, "left"), np.searchsorted(t, t0 + AFTER, "right")
            for i in range(a, b):
                if not first[i]: continue
                ws = wset(i)
                if len(ws) < 3: continue
                p0 = np.searchsorted(t, t[i] - 3600, "left"); new = True
                for j in range(p0, i):
                    if sid[j] == sid[i]: continue
                    wj = wset(j)
                    if wj and len(ws & wj) / len(ws | wj) >= 0.3: new = False; break
                if new: fires.append(dict(cls="new_story", lead=int(t0 - t[i]), what=f"{src[i]}: {I.text.iat[i][:120]}"))
            f.write(json.dumps(dict(wid=int(w.wid), fires=fires)) + "\n"); f.flush()
            if n % 100 == 0 or n == len(todo):
                el = time.time() - t0w; log(f"windows {n}/{len(todo)} ({100*n/len(todo):.0f} %), elapsed {el/60:.1f} min, ETA {el/n*(len(todo)-n)/60:.1f} min")
            if len(words) > 400000: words.clear()
    log(f"DONE {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
