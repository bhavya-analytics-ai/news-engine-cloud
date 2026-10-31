# Reverse lookup — from every big MNQ move in October 2026 back to the headline that preceded it

Question: what actually moves MNQ, who posts it first, how many seconds before the move, and does the headline's direction match the move. Work only from the files below. No web. Write results to `reverse/`. Push when done.

## Inputs
- `data/mnq_1m_oct2026.csv.gz` — MNQ front-month 1-minute bars, UTC timestamps (`ts_utc`), open/high/low/close/volume, Sep 30 to Oct 31 2026.
- `data/stories_oct2026.csv.gz` — every post from 12 feeds in the same window: `ts` (UTC, seconds), `source`, `story_id`, `lag_s` (0 = first arrival of that story; >0 = a relay, seconds after the first), `text`.
- `screen_tags/*.jsonl` — the Sonnet screen's `matters` flag per story id (join on `id` = `story_id`).
- `read_tags_v3/*.jsonl` — Opus's v3 read (`sign`, `channel`, `trade`) for the 163 kept items.

All time-of-day statements in New York time (convert from UTC; October 2026 is EDT, UTC−4).

## Definitions
- **Burst minute:** a 1-minute bar whose high−low is at least 10 points **and** at least 3× the median high−low of the previous 60 bars. Merge consecutive burst minutes into one **burst**; its start = first burst minute's open time; its direction = sign(close of last burst minute − open of first); its size = that difference in points; its 15-minute follow-through = close 15 bars after the start − open of the start.
- **Big burst:** size ≥ 30 points.
- **Candidate headline for a burst:** any first-arrival story (`lag_s == 0`) posted between 600 seconds before the burst start and 60 seconds after it. Lead = burst start − post time, in seconds (positive = the post came first).
- **Power source:** the text names a government, ministry, central bank, head of state, court, official statistic, confirmed military event, or one of Nvidia/Apple/Microsoft/Amazon/Alphabet/Meta/Broadcom/Tesla about itself. Use the Sonnet `matters` flag as the primary definition and a keyword fallback (Fed, FOMC, Treasury, White House, Trump, Iran, IRGC, Hormuz, Saudi, UKMTO, CPI, payrolls, GDP, tariff, China commerce ministry, BoJ) for stories the screen never saw.
- **Scheduled minute:** 08:30, 10:00, 14:00 ET on weekdays. Mark bursts starting within 1 minute of these separately.

## Produce `reverse/REVERSE_RESULT.md` with these sections, every number from the data
1. **Counts.** Bursts, big bursts, by time-of-day bucket (Asia 18–03, London 03–08:30, pre-open 08:30–09:30, NY open 09:30–10:30, midday 10:30–14, close 14–16, after hours 16–18), and how many are scheduled-minute bursts.
2. **Coverage.** Share of bursts and of big bursts that have at least one candidate headline from a power source in the window; the same split by bucket; the same for the Sonnet-kept set only. This is "how much of the market's movement does the feed see coming".
3. **Who is first.** For bursts with a candidate headline: per source, count of times it was the earliest power-source post before the burst, and the median lead in seconds. Also the share of candidate headlines that arrived **after** the burst started (lead < 0): those are the feed being late.
4. **What precedes moves.** For explained big bursts, the category of the earliest headline (use `channel` from read_tags_v3 where available, else a keyword category: fed/data/tariff/geopolitics/china/japan/megacap/crypto/other) against the base rate of that category among all first-arrival stories. Which categories are over-represented before moves.
5. **Direction.** For explained big bursts whose earliest headline has a v3 `sign` ≠ 0: does the sign match the burst direction? Count, hit rate, and the 15-minute follow-through in the headline's direction. Separately for London hours vs the rest.
6. **The table.** Every big burst: start time ET, size, direction, 15-min follow-through, bucket, scheduled-minute flag, earliest power-source headline (source, lead seconds, first 100 characters), v3 sign if any.
7. **Unexplained big bursts.** The ones with no power-source headline within 10 minutes: list them with the nearest story of any kind and its lead. Say plainly what share of October's big moves had no headline the feed carried.

Also write `reverse/bursts.csv` (one row per burst with all fields) and `reverse/burst_headlines.csv` (every candidate headline per burst with lead seconds). Validate that every burst in the table appears in the CSV. Commit and push `reverse/`. Reply with: number of bursts, number of big bursts, share explained, and the single most common earliest source.
