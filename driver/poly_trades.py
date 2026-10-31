#!/usr/bin/env python
"""Pull every Polymarket trade (second stamps) for the universe markets inside each month, in parallel.
data-api /trades with market + start/end (unix s); the API caps offset at 10,000, so a full page splits the time range.
usage: poly_trades.py <month> <workers>  -> corpus/polymarket/trades_<month>.jsonl ; progress in driver/progress.log
"""
import json, sys, time, threading, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
MONTH_RANGE = {"may2025": (1746057600 - 2 * 86400, 1748735999 + 120), "oct2026": (1790812800 - 2 * 86400, 1793491199 + 120)}  # month start UTC minus 2 days (bursts.csv starts Apr 30 / Sep 30)
LOCAL = threading.local(); LOCK = threading.Lock(); STATS = {"calls": 0, "err": 0}


def sess():
    if not hasattr(LOCAL, "s"): LOCAL.s = requests.Session()
    return LOCAL.s


def page(cid, a, b, off):
    for k in range(8):
        try:
            r = sess().get("https://data-api.polymarket.com/trades", params=dict(market=cid, start=a, end=b, limit=500, offset=off), timeout=60)
            with LOCK: STATS["calls"] += 1
            if r.status_code == 200:
                return [dict(ts=x["timestamp"], cid=x["conditionId"], asset=x["asset"], outcome=x.get("outcome"), oi=x.get("outcomeIndex"),
                             price=x["price"], size=x["size"], side=x.get("side"), tx=x.get("transactionHash"), w=x.get("proxyWallet"))
                        for x in r.json()]
            if r.status_code == 400 and "offset" in r.text: return None
        except Exception: pass
        with LOCK: STATS["err"] += 1
        time.sleep(min(30, 1.5 * 2 ** k))
    raise RuntimeError(f"failed {cid} {a} {b} {off}")


def pull_range(cid, a, b):
    out = []; off = 0
    while True:
        t = page(cid, a, b, off)
        if t is None or (off >= 9500 and len(t) == 500):       # range too dense: split
            mid = (a + b) // 2
            if mid <= a: break
            return pull_range(cid, a, mid) + pull_range(cid, mid + 1, b)
        out += t
        if len(t) < 500: return out
        off += 500
    return out


def main():
    mon, workers = sys.argv[1], int(sys.argv[2]); a, b = MONTH_RANGE[mon]
    U = [json.loads(l) for l in open(sys.argv[3] if len(sys.argv) > 3 else f"corpus/polymarket/universe_{mon}.jsonl")]
    t0 = time.time(); done = 0; n_tr = 0
    outf = f"corpus/polymarket/trades_{mon}{sys.argv[4] if len(sys.argv) > 4 else ''}.jsonl"
    with open(outf, "w") as f, ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(pull_range, u["condition_id"], a, b): u for u in U}
        for fu in as_completed(futs):
            u = futs[fu]; tr = fu.result(); seen = set()
            for x in tr:
                key = (x["tx"], x["asset"], x["price"], x["size"], x["ts"], x["side"], x["w"])
                if key in seen: continue
                seen.add(key)
                f.write(json.dumps({k: x[k] for k in ("ts", "cid", "asset", "outcome", "oi", "price", "size", "side")}) + "\n")
            n_tr += len(seen); done += 1
            if done % 25 == 0 or done == len(U):
                el = time.time() - t0; eta = el / done * (len(U) - done)
                with open("driver/progress.log", "a") as lg:
                    lg.write(f"{time.strftime('%H:%M:%S')} polymarket {mon}: {done}/{len(U)} markets ({100*done/len(U):.0f} %), {n_tr} trades, "
                             f"{STATS['calls']} calls, {STATS['err']} retries, elapsed {el/60:.1f} min, ETA {eta/60:.1f} min\n")
    print(mon, "markets", len(U), "trades", n_tr, "calls", STATS["calls"], "retries", STATS["err"], f"{(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
