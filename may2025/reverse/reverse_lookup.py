#!/usr/bin/env python3
"""Reverse lookup: big MNQ 1-minute bursts in May 2025 -> headlines that preceded them.
Implements reverse/BRIEF_REVERSE.md. Run from the repo root: python3 -I may2025/reverse/reverse_lookup.py
"""
import glob, json, re
import numpy as np
import pandas as pd

OUT = "may2025/reverse"
WIN_BEFORE, WIN_AFTER = 600, 60
BUCKETS = [("Asia", 18 * 60, 3 * 60), ("London", 3 * 60, 8 * 60 + 30), ("pre-open", 8 * 60 + 30, 9 * 60 + 30),
           ("NY open", 9 * 60 + 30, 10 * 60 + 30), ("midday", 10 * 60 + 30, 14 * 60), ("close", 14 * 60, 16 * 60),
           ("after hours", 16 * 60, 18 * 60)]
BUCKET_ORDER = [b[0] for b in BUCKETS]
SCHED = [8 * 60 + 30, 10 * 60, 14 * 60]

POWER_KW = re.compile(r"\bfed\b|\bfed's\b|federal reserve|\bfomc\b|treasury|white house|trump|\biran|\birgc\b|hormuz|saudi|"
                      r"ukmto|\bcpi\b|payrolls|\bgdp\b|tariff|china.{0,40}commerce ministry|commerce ministry.{0,40}china|"
                      r"mofcom|\bboj\b|bank of japan", re.I)
CHANNEL_TO_CAT = {"rates_fed": "fed", "growth_data": "data", "tariffs_trade": "tariff", "geopolitics_oil": "geopolitics",
                  "china": "china", "japan_yen": "japan", "megacap": "megacap", "credit_crypto": "crypto"}
CAT_KW = [  # first match wins
    ("tariff", r"tariff|section 232|section 301|section 338|trade deal|import dut"),
    ("data", r"\bcpi\b|\bppi\b|\bpce\b|payrolls|nonfarm|\bgdp\b|\bism\b|\bpmi\b|jobless|retail sales|unemployment|"
             r"housing starts|consumer (confidence|sentiment)|michigan|industrial production|import prices|jolts|"
             r"durable goods|actual .*forecast"),
    ("fed", r"\bfed\b|\bfed's\b|federal reserve|\bfomc\b|powell|warsh|rate (hike|cut)|treasury yield|\byields?\b|"
            r"note auction|bond auction|high yield actual"),
    ("megacap", r"nvidia|\bnvda\b|apple|\baapl\b|microsoft|\bmsft\b|amazon|\bamzn\b|alphabet|google|\bgoogl\b|\bmeta\b|"
                r"zuckerberg|broadcom|\bavgo\b|tesla|\btsla\b|musk|nadella"),
    ("japan", r"japan|\bboj\b|bank of japan|\byen\b|\bjgb|nikkei|takaichi|katayama|ueda"),
    ("china", r"china|chinese|beijing|\bpboc\b|taiwan|xi jinping"),
    ("geopolitics", r"\biran|\birgc\b|hormuz|saudi|houthi|yemen|ukmto|israel|gaza|russia|ukrain|putin|missile|drone|"
                    r"strike|attack|tanker|\boil\b|crude|brent|\bwti\b|opec|aramco|military|navy|war\b"),
    ("crypto", r"bitcoin|\bbtc\b|crypto|stablecoin|ethereum|\beth\b|coinbase|binance"),
]
CAT_KW = [(c, re.compile(p, re.I)) for c, p in CAT_KW]


def kw_cat(text):
    for c, p in CAT_KW:
        if p.search(text or ""):
            return c
    return "other"


def bucket_of(minute_of_day):
    for name, lo, hi in BUCKETS:
        if (lo <= minute_of_day < hi) if lo < hi else (minute_of_day >= lo or minute_of_day < hi):
            return name
    raise ValueError(minute_of_day)


def load_jsonl(pattern):
    rows = []
    for f in sorted(glob.glob(pattern)):
        rows += [json.loads(l) for l in open(f) if l.strip()]
    return rows


# ---------- bars and bursts ----------
bars = pd.read_csv("may2025/data/mnq_1m_may2025.csv.gz", parse_dates=["ts_utc"]).reset_index(drop=True)
bars["rng"] = bars.high - bars.low
bars["med60"] = bars.rng.shift(1).rolling(60, min_periods=60).median()
bars["burst_min"] = (bars.rng >= 10) & (bars.rng >= 3 * bars.med60)

bursts = []
i, n = 0, len(bars)
while i < n:
    if not bars.burst_min.iat[i]:
        i += 1
        continue
    j = i
    # consecutive = adjacent bars exactly one minute apart
    while j + 1 < n and bars.burst_min.iat[j + 1] and (bars.ts_utc.iat[j + 1] - bars.ts_utc.iat[j]).total_seconds() == 60:
        j += 1
    o, c = bars.open.iat[i], bars.close.iat[j]
    size = c - o
    ft = bars.close.iat[i + 15] - o if i + 15 < n else np.nan
    bursts.append(dict(start_utc=bars.ts_utc.iat[i], end_utc=bars.ts_utc.iat[j], n_minutes=j - i + 1,
                       open=o, close=c, size=size, direction=int(np.sign(size)), abs_size=abs(size),
                       ft15=ft, max_range=bars.rng.iloc[i:j + 1].max()))
    i = j + 1
B = pd.DataFrame(bursts)
B["start_et"] = B.start_utc.dt.tz_convert("America/New_York")
mod = B.start_et.dt.hour * 60 + B.start_et.dt.minute
B["bucket"] = [bucket_of(m) for m in mod]
B["scheduled"] = [(et.weekday() < 5) and any(abs(m - s) <= 1 for s in SCHED) for et, m in zip(B.start_et, mod)]
B["big"] = B.abs_size >= 30
B["burst_id"] = range(len(B))

# ---------- stories and tags ----------
S = pd.read_csv("may2025/data/stories_may2025.csv.gz")
S["ts"] = pd.to_datetime(S.ts, utc=True)
S["text"] = S.text.fillna("").astype(str)
screen = {o["id"]: o for o in load_jsonl("may2025/screen_tags/*.jsonl")}
v3 = {o["id"]: o for o in load_jsonl("may2025/read_tags_v3/*.jsonl")}
F = S[S.lag_s == 0].copy()
F["screened"] = F.story_id.isin(screen)
F["matters"] = F.story_id.map(lambda k: screen.get(k, {}).get("matters", np.nan))
F["kw_power"] = F.text.fillna("").str.contains(POWER_KW)
F["power"] = np.where(F.screened, F.matters == 1, F.kw_power)
F["kept"] = F.matters == 1
F["v3_sign"] = F.story_id.map(lambda k: v3.get(k, {}).get("sign", np.nan))
F["v3_channel"] = F.story_id.map(lambda k: v3.get(k, {}).get("channel"))
F["category"] = [CHANNEL_TO_CAT.get(ch) or kw_cat(t) for ch, t in zip(F.v3_channel, F.text)]
F = F.sort_values("ts").reset_index(drop=True)
fts = F.ts.values.astype("datetime64[s]").astype(np.int64)

# ---------- candidate headlines ----------
cand = []
for b in B.itertuples():
    t0 = int(b.start_utc.timestamp())
    lo, hi = np.searchsorted(fts, t0 - WIN_BEFORE, "left"), np.searchsorted(fts, t0 + WIN_AFTER, "right")
    for k in range(lo, hi):
        r = F.iloc[k]
        cand.append(dict(burst_id=b.burst_id, burst_start_utc=b.start_utc, story_id=r.story_id, post_utc=r.ts,
                         source=r.source, lead_s=t0 - int(r.ts.timestamp()), power=bool(r.power), kept=bool(r.kept),
                         screened=bool(r.screened), category=r.category, v3_sign=r.v3_sign,
                         text=str(r.text).replace("\n", " ")))
C = pd.DataFrame(cand)
P = C[C.power]

# earliest power-source headline per burst (largest lead in the window)
earliest = P.sort_values(["burst_id", "lead_s"], ascending=[True, False]).groupby("burst_id").head(1).set_index("burst_id")
B["explained"] = B.burst_id.isin(P.burst_id)
B["explained_kept"] = B.burst_id.isin(C[C.kept].burst_id)
B["n_candidates"] = B.burst_id.map(C.groupby("burst_id").size()).fillna(0).astype(int)
B["n_power_candidates"] = B.burst_id.map(P.groupby("burst_id").size()).fillna(0).astype(int)
for col, src in [("first_source", "source"), ("first_lead_s", "lead_s"), ("first_story_id", "story_id"),
                 ("first_category", "category"), ("first_v3_sign", "v3_sign"), ("first_text", "text")]:
    B[col] = B.burst_id.map(earliest[src])


def nearest_any(t0):
    k = np.searchsorted(fts, t0)
    best = None
    for kk in (k - 1, k):
        if 0 <= kk < len(fts) and (best is None or abs(t0 - fts[kk]) < abs(t0 - fts[best])):
            best = kk
    return F.iloc[best], t0 - fts[best]


# ---------- outputs: CSVs ----------
B_out = B.copy()
B_out["start_et"] = B_out.start_et.dt.strftime("%Y-%m-%d %H:%M")
B_out.drop(columns=["start_utc", "end_utc"]).assign(start_utc=B.start_utc.astype(str), end_utc=B.end_utc.astype(str)) \
     .to_csv(f"{OUT}/bursts.csv", index=False)
C.assign(burst_start_utc=C.burst_start_utc.astype(str), post_utc=C.post_utc.astype(str)) \
 .to_csv(f"{OUT}/burst_headlines.csv", index=False)

# ---------- report ----------
L = []
pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0 (–)"
md = lambda x: f"{x:.0f}" if pd.notna(x) else "–"
big = B[B.big]
tape_end_et = bars.ts_utc.iat[-1].tz_convert("America/New_York").strftime("%Y-%m-%d %H:%M")
story_end_et = S.ts.max().tz_convert("America/New_York").strftime("%Y-%m-%d %H:%M")

L.append("# Reverse lookup — May 2025 MNQ bursts back to headlines\n")
L.append(f"Generated by `may2025/reverse/reverse_lookup.py` from `may2025/data/`, `may2025/screen_tags/`, `may2025/read_tags_v3/`. All times New York (EDT).\n")
L.append(f"Data window: bars {bars.ts_utc.iat[0].tz_convert('America/New_York'):%Y-%m-%d %H:%M} to {tape_end_et} "
         f"({len(bars)} bars); stories to {story_end_et} ({len(S)} posts, {len(F)} first arrivals). "
         f"Last bar {tape_end_et} ET; last story {story_end_et} ET.\n")
L.append(f"Power source: Sonnet `matters`=1 for the {int(F.screened.sum())} first-arrival stories the screen saw; "
         f"keyword fallback for the {int((~F.screened).sum())} it did not. Candidate window: {WIN_BEFORE}s before to "
         f"{WIN_AFTER}s after burst start. \"Explained\" = at least one power-source candidate in that window.\n")

L.append("## 1. Counts\n")
L.append(f"- Bursts: **{len(B)}**. Big bursts (|size| ≥ 30): **{len(big)}**.")
L.append(f"- Scheduled-minute bursts (within 1 min of 08:30 / 10:00 / 14:00 ET, weekdays): {int(B.scheduled.sum())} "
         f"of all, {int(big.scheduled.sum())} of big.\n")
L.append("| bucket | bursts | big | scheduled (all) | scheduled (big) |\n|---|---|---|---|---|")
for bk in BUCKET_ORDER:
    s = B[B.bucket == bk]
    L.append(f"| {bk} | {len(s)} | {int(s.big.sum())} | {int(s.scheduled.sum())} | {int((s.big & s.scheduled).sum())} |")
L.append(f"| **total** | {len(B)} | {len(big)} | {int(B.scheduled.sum())} | {int(big.scheduled.sum())} |\n")

L.append("## 2. Coverage — how much of the movement the feed sees coming\n")
L.append(f"- All bursts with a power-source candidate: {pct(int(B.explained.sum()), len(B))}; "
         f"Sonnet-kept only: {pct(int(B.explained_kept.sum()), len(B))}.")
L.append(f"- Big bursts with a power-source candidate: {pct(int(big.explained.sum()), len(big))}; "
         f"Sonnet-kept only: {pct(int(big.explained_kept.sum()), len(big))}.")
nb = B[~B.scheduled]; nbb = big[~big.scheduled]
L.append(f"- Excluding scheduled-minute bursts: all {pct(int(nb.explained.sum()), len(nb))}, "
         f"big {pct(int(nbb.explained.sum()), len(nbb))}.")
L.append(f"- Any first-arrival story at all in the window (no power filter): all {pct(int((B.n_candidates > 0).sum()), len(B))}, "
         f"big {pct(int((big.n_candidates > 0).sum()), len(big))}.\n")
L.append("| bucket | all: power | all: kept | big: power | big: kept |\n|---|---|---|---|---|")
for bk in BUCKET_ORDER:
    s = B[B.bucket == bk]; sb = s[s.big]
    L.append(f"| {bk} | {pct(int(s.explained.sum()), len(s))} | {pct(int(s.explained_kept.sum()), len(s))} | "
             f"{pct(int(sb.explained.sum()), len(sb))} | {pct(int(sb.explained_kept.sum()), len(sb))} |")
L.append("")

L.append("## 3. Who is first\n")
before = P[P.lead_s >= 0]
first_before = before.sort_values(["burst_id", "lead_s"], ascending=[True, False]).groupby("burst_id").head(1)
L.append(f"Bursts with a power-source post at or before the start: {first_before.burst_id.nunique()} "
         f"(of {int(B.explained.sum())} explained). Earliest such post per burst, by source:\n")
L.append("| source | times earliest (all bursts) | median lead s | times earliest (big) | median lead s (big) |\n|---|---|---|---|---|")
fb_big = first_before[first_before.burst_id.isin(big.burst_id)]
for src, g in first_before.groupby("source").size().sort_values(ascending=False).items():
    gg = first_before[first_before.source == src]; gb = fb_big[fb_big.source == src]
    L.append(f"| {src} | {g} | {md(gg.lead_s.median())} | {len(gb)} | {md(gb.lead_s.median())} |")
late_all = (C.lead_s < 0).mean() if len(C) else np.nan
late_pow = (P.lead_s < 0).mean() if len(P) else np.nan
L.append(f"\n- Candidate headlines arriving **after** the burst started (lead < 0): all candidates "
         f"{pct(int((C.lead_s < 0).sum()), len(C))}; power-source candidates {pct(int((P.lead_s < 0).sum()), len(P))}.")
only_late = B.explained & ~B.burst_id.isin(before.burst_id)
L.append(f"- Explained bursts where **every** power-source candidate came after the start (feed late): "
         f"{pct(int(only_late.sum()), int(B.explained.sum()))}; big: "
         f"{pct(int((only_late & B.big).sum()), int(big.explained.sum()))}.\n")

L.append("## 4. What precedes moves\n")
eb = big[big.explained]
cat_b = eb.first_category.value_counts()
base = F.category.value_counts(normalize=True)
L.append(f"Category of the earliest power-source headline for the {len(eb)} explained big bursts, against the base rate "
         f"of that category among all {len(F)} first-arrival stories (v3 `channel` where available, else keyword).\n")
L.append("| category | explained big bursts | share | base rate | ratio |\n|---|---|---|---|---|")
for cat in sorted(set(cat_b.index) | set(base.index), key=lambda c: -cat_b.get(c, 0)):
    sh = cat_b.get(cat, 0) / len(eb) if len(eb) else 0
    br = base.get(cat, 0)
    L.append(f"| {cat} | {cat_b.get(cat, 0)} | {100 * sh:.0f}% | {100 * br:.1f}% | {sh / br:.1f}× |" if br else
             f"| {cat} | {cat_b.get(cat, 0)} | {100 * sh:.0f}% | 0% | – |")
L.append("")

L.append("## 5. Direction\n")
ds = eb[eb.first_v3_sign.fillna(0) != 0].copy()
ds["hit"] = ds.first_v3_sign == ds.direction
ds["ft_dir"] = ds.first_v3_sign * ds.ft15


def dir_line(name, d):
    if not len(d):
        return f"| {name} | 0 | – | – | – |"
    return (f"| {name} | {len(d)} | {int(d.hit.sum())}/{len(d)} ({100 * d.hit.mean():.0f}%) | "
            f"{d.ft_dir.mean():+.1f} | {d.ft_dir.median():+.1f} |")


L.append(f"Explained big bursts whose earliest power-source headline has a v3 `sign` ≠ 0: {len(ds)} "
         f"(of {len(eb)} explained big bursts; the rest have no v3 read or sign 0).\n")
L.append("| set | n | sign matches burst direction | mean 15-min follow-through in headline direction (pts) | median |\n|---|---|---|---|---|")
L.append(dir_line("all", ds))
L.append(dir_line("London (03–08:30)", ds[ds.bucket == "London"]))
L.append(dir_line("rest", ds[ds.bucket != "London"]))
L.append("")

L.append("## 6. The table — every big burst\n")
L.append("| # | start ET | size | dir | 15m FT | bucket | sched | source | lead s | earliest power-source headline (100 chars) | v3 sign |\n"
         "|---|---|---|---|---|---|---|---|---|---|---|")
for b in big.itertuples():
    txt = (str(b.first_text)[:100].replace("|", "/") if b.explained else "— none —")
    L.append(f"| {b.burst_id} | {b.start_et:%m-%d %H:%M} | {b.size:+.2f} | {'+' if b.direction > 0 else '−'} | "
             f"{b.ft15:+.2f} | {b.bucket} | {'Y' if b.scheduled else ''} | {b.first_source if b.explained else ''} | "
             f"{int(b.first_lead_s) if b.explained else ''} | {txt} | "
             f"{int(b.first_v3_sign) if pd.notna(b.first_v3_sign) else ''} |")
L.append("")

L.append("## 7. Unexplained big bursts\n")
ub = big[~big.explained]
L.append("| # | start ET | size | bucket | sched | nearest story (any) source | lead s | text (100 chars) |\n|---|---|---|---|---|---|---|---|")
for b in ub.itertuples():
    r, lead = nearest_any(int(b.start_utc.timestamp()))
    L.append(f"| {b.burst_id} | {b.start_et:%m-%d %H:%M} | {b.size:+.2f} | {b.bucket} | {'Y' if b.scheduled else ''} | "
             f"{r.source} | {int(lead)} | {str(r.text)[:100].replace('|', '/')} |")
L.append(f"\n**{pct(len(ub), len(big))} of May 2025's big moves had no power-source headline in the feed within "
         f"{WIN_BEFORE // 60} minutes before (to {WIN_AFTER}s after) the start.**\n")

L.append("## Caveats\n")
kw_only = set(P[~P.screened].burst_id) - set(P[P.screened].burst_id)
kwC = C[C.text.str.contains(POWER_KW)]
L.append(f"- **Two standards for \"power source\".** The {int(F.screened.sum())} screened stories need Sonnet `matters`=1 "
         f"(strict, ~1% pass); the {int((~F.screened).sum())} unscreened ones pass on a keyword alone (loose). "
         f"{len(kw_only & set(big[big.explained].burst_id))} of the {int(big.explained.sum())} explained big bursts are "
         f"explained only by an unscreened keyword hit. Sensitivity, keyword rule applied to every story: big bursts "
         f"explained {pct(kwC[kwC.burst_id.isin(big.burst_id)].burst_id.nunique(), len(big))}, all bursts "
         f"{pct(kwC.burst_id.nunique(), len(B))}.")
L.append("- **1-minute resolution.** Lead is measured from the burst bar's open, so a post inside the first burst "
         "minute (typical for 08:30 data, which prints a few seconds after 08:30:00) shows a small negative lead.")
o930 = B.start_et.dt.strftime("%H:%M").isin(["09:30", "09:31"])
L.append(f"- **Cash open.** {int(o930.sum())} bursts ({int((o930 & B.big).sum())} big) start at 09:30–09:31 ET: the "
         "cash-open volatility jump clears 3× the quiet pre-market median by construction. They are not scheduled "
         "minutes under the brief and mostly have no headline.")
L.append(f"- **Tape ends {tape_end_et} ET**; stories run to {story_end_et} ET. Nothing after the tape end is measured.\n")

# headline numbers
top = first_before.source.value_counts()
L.append("## Summary\n")
L.append(f"- Bursts: {len(B)}; big bursts: {len(big)}; share of big bursts explained: "
         f"{pct(int(big.explained.sum()), len(big))}; share of all bursts explained: {pct(int(B.explained.sum()), len(B))}.")
L.append(f"- Most common earliest power-source poster before a burst: **{top.index[0]}** ({top.iloc[0]} of {top.sum()}).")
open(f"{OUT}/REVERSE_RESULT.md", "w").write("\n".join(L) + "\n")

# ---------- validation ----------
chk = pd.read_csv(f"{OUT}/bursts.csv")
assert set(big.burst_id) <= set(chk.burst_id), "big burst missing from bursts.csv"
assert len(chk) == len(B) and chk.big.sum() == len(big)
hc = pd.read_csv(f"{OUT}/burst_headlines.csv")
assert set(hc.burst_id) <= set(chk.burst_id) and len(hc) == len(C)
assert set(B[B.explained].burst_id) == set(hc[hc.power].burst_id)
print(f"bursts={len(B)} big={len(big)} explained_big={int(big.explained.sum())}/{len(big)} "
      f"explained_all={int(B.explained.sum())}/{len(B)} top_first={top.index[0]} ({top.iloc[0]}/{top.sum()})")
print("VALIDATION OK: every table burst is in bursts.csv; headline CSV consistent")
