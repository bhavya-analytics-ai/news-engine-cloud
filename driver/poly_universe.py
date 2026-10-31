#!/usr/bin/env python
"""Polymarket market universe per month: every event overlapping the month that carries one of the macro / politics /
geopolitics tags below (sports and crypto-price tags are not in the list), every market in it with lifetime volume >= MIN_VOL.
Public gamma API, no key. usage: poly_universe.py  -> corpus/polymarket/universe_<month>.jsonl
"""
import json, os, time, threading, requests
from concurrent.futures import ThreadPoolExecutor
LOCAL = threading.local()


def sess():
    if not hasattr(LOCAL, "s"): LOCAL.s = requests.Session()
    return LOCAL.s
TAGS = ["economy", "fed", "fed-rates", "finance", "business", "stocks", "economic-policy", "inflation", "tariffs", "trade-war",
        "geopolitics", "world", "middle-east", "china", "iran", "trump", "trump-presidency", "politics"]
MONTHS = {"may2025": ("2025-05-01T00:00:00Z", "2025-05-31T23:59:59Z"), "oct2026": ("2026-10-01T00:00:00Z", "2026-10-31T23:59:59Z")}
MIN_VOL = 50000.0
OUT = "corpus/polymarket"


def get(url, params, tries=6):
    for k in range(tries):
        try:
            r = sess().get(url, params=params, timeout=60)
            if r.status_code == 200: return r.json()
        except Exception: pass
        time.sleep(2 * 2 ** k)
    return None


def fetch_slice(tid, a, b, emin, emax):
    """events with end_date in [emin, emax) overlapping the month; None if the 2,100-offset cap is hit"""
    out = []; off = 0
    while True:
        if off >= 2000: return None
        ev = get("https://gamma-api.polymarket.com/events", dict(limit=100, offset=off, tag_id=tid, end_date_min=emin, end_date_max=emax, start_date_max=b), tries=3)
        if ev is None: return None
        out += [slim(e) for e in ev]
        if len(ev) < 100: return out


def slim(e):
    """keep only what the universe file needs, so threads do not hold full event payloads"""
    return dict(id=e["id"], slug=e.get("slug"), title=e.get("title"), tags=[dict(slug=x.get("slug")) for x in e.get("tags", [])],
                markets=[{k: m.get(k) for k in ("conditionId", "clobTokenIds", "question", "outcomes", "volumeNum", "volume", "startDate", "endDate", "closed")}
                         for m in e.get("markets", [])])


def fetch_tag(mon, a, b, t, tid):
    import pandas as pd
    todo = [(pd.Timestamp(a), pd.Timestamp("2031-01-01T00:00:00Z"))]; out = []; status = "complete"
    while todo:
        lo, hi = todo.pop()
        r = fetch_slice(tid, a, b, lo.strftime("%Y-%m-%dT%H:%M:%SZ"), hi.strftime("%Y-%m-%dT%H:%M:%SZ"))
        if r is not None: out += r; continue
        if hi - lo <= pd.Timedelta(hours=6): status = f"slice {lo}..{hi} still over the cap; partial"; continue
        mid = lo + (hi - lo) / 2; todo += [(lo, mid), (mid, hi)]
    return mon, t, out, status


def main():
    tag_ids = {t: get(f"https://gamma-api.polymarket.com/tags/slug/{t}", {})["id"] for t in TAGS}
    jobs = [(mon, a, b, t, tid) for mon, (a, b) in MONTHS.items() for t, tid in tag_ids.items()]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda j: fetch_tag(*j), jobs))
    notes = []
    for mon in MONTHS:
        events = {}
        for m_, t, evs, status in res:
            if m_ != mon: continue
            notes.append(dict(month=mon, tag=t, events=len(evs), status=status))
            for e in evs:
                events.setdefault(e["id"], e).setdefault("_tags_hit", set()).add(t)
        rows = []
        for e in events.values():
            etags = [x.get("slug") for x in e.get("tags", [])]
            for m in e.get("markets", []):
                v = float(m.get("volumeNum") or m.get("volume") or 0)
                if v < MIN_VOL or not m.get("conditionId") or not m.get("clobTokenIds"): continue
                rows.append(dict(month=mon, event_id=e["id"], event_slug=e.get("slug"), event_title=e.get("title"), event_tags=etags,
                                 tags_hit=sorted(e["_tags_hit"]), condition_id=m["conditionId"], question=m.get("question"),
                                 outcomes=m.get("outcomes"), token_ids=m.get("clobTokenIds"), volume=v,
                                 start=m.get("startDate"), end=m.get("endDate"), closed=m.get("closed")))
        with open(f"{OUT}/universe_{mon}.jsonl", "w") as f:
            for r in rows: f.write(json.dumps(r) + "\n")
        print(mon, "events", len(events), "markets >= vol floor", len(rows), "sum volume", f"{sum(r['volume'] for r in rows):,.0f}")
    json.dump(notes, open(f"{OUT}/universe_notes.json", "w"), indent=1)
    for n in notes:
        if n["status"] != "complete": print("TRUNCATED", n)


if __name__ == "__main__":
    main()
