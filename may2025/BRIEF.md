# Cloud brief — MNQ news-engine, May 2025 blind month

You are running the model-heavy part of a research pipeline. Everything you need is in this repository. Do not use the web. Do not read or write anything outside this repository. Do not change any input file or any prompt file. Commit and push only validated outputs.

This is the same method as the October 2026 run (`BRIEF.md` at the repository root), applied to **May 2025** with frozen rules. All May 2025 files live under `may2025/`. Never touch the October 2026 folders (`screen_batches/`, `screen_tags/`, `read_batches/`, `read_tags_v2/`, `read_tags_v3/`, `reverse/`, `data/`) or `prompts/`.

## Phase 1 — screen (do this now)

Inputs: `may2025/screen_batches/s_000.jsonl` … `s_050.jsonl` (400 lines each, the last one shorter). Instructions: `prompts/SCREEN_PROMPT.md`.

For **each** batch, run one subagent on the **Sonnet** model (model id `claude-sonnet-5-5`) with this task, 20 subagents at a time at most:

> Read `prompts/SCREEN_PROMPT.md` and follow it exactly. Input: `may2025/screen_batches/s_NNN.jsonl`. Write one JSON object per input line, same order, fields `id`, `matters`, `channel`, to `may2025/screen_tags/s_NNN.jsonl` with the Write tool. No shell commands, no other files, no web. Reply with one line: lines written and count with matters=1.

When all 51 are done, run:
```
python3 scripts/validate_tags.py may2025/screen_batches may2025/screen_tags id,matters,channel
```
If it prints anything other than `OK`, rerun **only** the batches it names (delete that tag file first, run the same subagent task again), then validate again. Never edit a tag file by hand.

When it prints `OK`: `git add may2025/screen_tags && git commit -m "May 2025 phase 1: Sonnet screen, 51 batches, validated" && git push`.
Then reply with: the count of matters=1 across all batches, and the validator's last line. Stop and wait.

## Phase 2 — read (only when `may2025/read_batches/r_*.jsonl` appears in the repository after a pull)

Inputs: `may2025/read_batches/r_NNN.jsonl` (each line has id, t, src, text, channel_hint, prior, day_context). One prompt only this time: `prompts/BRAIN_V3_PROMPT.md`. There is **no v2 pass** for May 2025.

For each read batch, run **one** subagent on the **Opus** model (model id `claude-opus-5-5`) with `prompts/BRAIN_V3_PROMPT.md` as written, writing to `may2025/read_tags_v3/r_NNN.jsonl`.

Task text:
> You are the reading pass of a news desk for MNQ research. Read `prompts/BRAIN_V3_PROMPT.md` completely and follow it exactly. Input: `may2025/read_batches/r_NNN.jsonl`. Think carefully about each item: the prior tells you what was already priced, the day_context what was already known. Write exactly one JSON object per input line, same order, with the fields the instructions define, to `may2025/read_tags_v3/r_NNN.jsonl` using the Write tool. No shell commands, no other files, no web. Reply with one line: lines written and count with trade=1.

Validate:
```
python3 scripts/validate_tags.py may2025/read_batches may2025/read_tags_v3 id,trade,channel,sign,surprise,magnitude,novelty,duration,confidence
```
Rerun only what the validator names. When it prints `OK`: `git add may2025/read_tags_v3 && git commit -m "May 2025 phase 2: Opus read v3, validated" && git push`. Reply with the trade count and the validator's last line. Then go straight on to Phase 3.

## Phase 3 — reverse lookup (after Phase 2 is pushed)

Same question and the same definitions as `reverse/BRIEF_REVERSE.md` (October 2026), applied to May 2025. Only the inputs, the output folder and the month change.

### Inputs
- `may2025/data/mnq_1m_may2025.csv.gz` — MNQ front-month 1-minute bars, UTC timestamps (`ts_utc`), open/high/low/close/volume, Apr 30 to May 30 2025 (the tape's last bar is 2025-05-30 20:59 UTC).
- `may2025/data/stories_may2025.csv.gz` — every post from the 12 feeds plus the president's posts in the same window: `ts` (UTC, seconds), `source`, `story_id`, `lag_s` (0 = first arrival of that story; >0 = a relay, seconds after the first), `text`. Apr 30 to May 31 2025.
- `may2025/screen_tags/*.jsonl` — the Sonnet screen's `matters` flag per story id (join on `id` = `story_id`).
- `may2025/read_tags_v3/*.jsonl` — Opus's v3 read (`sign`, `channel`, `trade`) for the kept items.

All time-of-day statements in New York time (convert from UTC; May 2025 is EDT, UTC−4).

### Definitions
- **Burst minute:** a 1-minute bar whose high−low is at least 10 points **and** at least 3× the median high−low of the previous 60 bars. Merge consecutive burst minutes into one **burst**; its start = first burst minute's open time; its direction = sign(close of last burst minute − open of first); its size = that difference in points; its 15-minute follow-through = close 15 bars after the start − open of the start.
- **Big burst:** size ≥ 30 points.
- **Candidate headline for a burst:** any first-arrival story (`lag_s == 0`) posted between 600 seconds before the burst start and 60 seconds after it. Lead = burst start − post time, in seconds (positive = the post came first).
- **Power source:** the text names a government, ministry, central bank, head of state, court, official statistic, confirmed military event, or one of Nvidia/Apple/Microsoft/Amazon/Alphabet/Meta/Broadcom/Tesla about itself. Use the Sonnet `matters` flag as the primary definition and a keyword fallback (Fed, FOMC, Treasury, White House, Trump, Iran, IRGC, Hormuz, Saudi, UKMTO, CPI, payrolls, GDP, tariff, China commerce ministry, BoJ) for stories the screen never saw.
- **Scheduled minute:** 08:30, 10:00, 14:00 ET on weekdays. Mark bursts starting within 1 minute of these separately.

### How to run it
Reuse `reverse/reverse_lookup.py`. **Do not edit the original.** Copy it to `may2025/reverse/reverse_lookup.py` and in the copy change only:
- the input paths: `data/mnq_1m_oct2026.csv.gz` → `may2025/data/mnq_1m_may2025.csv.gz`, `data/stories_oct2026.csv.gz` → `may2025/data/stories_may2025.csv.gz`, `screen_tags/*.jsonl` → `may2025/screen_tags/*.jsonl`, `read_tags_v3/*.jsonl` → `may2025/read_tags_v3/*.jsonl`;
- `OUT = "reverse"` → `OUT = "may2025/reverse"`;
- month wording in the report text ("October 2026" / "Oct 2026" / "October's" → "May 2025" / "May 2025's"), and the October-specific sentence about where the tape stops (replace it with the actual last bar and last story times the script already computes; say nothing about Oct 29–31).

Change no definition, threshold, window, bucket, regex or category. Run from the repository root: `python3 -I may2025/reverse/reverse_lookup.py`.

### Produce `may2025/reverse/REVERSE_RESULT.md` with these sections, every number from the data
1. **Counts.** Bursts, big bursts, by time-of-day bucket (Asia 18–03, London 03–08:30, pre-open 08:30–09:30, NY open 09:30–10:30, midday 10:30–14, close 14–16, after hours 16–18), and how many are scheduled-minute bursts.
2. **Coverage.** Share of bursts and of big bursts that have at least one candidate headline from a power source in the window; the same split by bucket; the same for the Sonnet-kept set only. This is "how much of the market's movement does the feed see coming".
3. **Who is first.** For bursts with a candidate headline: per source, count of times it was the earliest power-source post before the burst, and the median lead in seconds. Also the share of candidate headlines that arrived **after** the burst started (lead < 0): those are the feed being late.
4. **What precedes moves.** For explained big bursts, the category of the earliest headline (use `channel` from read_tags_v3 where available, else a keyword category: fed/data/tariff/geopolitics/china/japan/megacap/crypto/other) against the base rate of that category among all first-arrival stories. Which categories are over-represented before moves.
5. **Direction.** For explained big bursts whose earliest headline has a v3 `sign` ≠ 0: does the sign match the burst direction? Count, hit rate, and the 15-minute follow-through in the headline's direction. Separately for London hours vs the rest.
6. **The table.** Every big burst: start time ET, size, direction, 15-min follow-through, bucket, scheduled-minute flag, earliest power-source headline (source, lead seconds, first 100 characters), v3 sign if any.
7. **Unexplained big bursts.** The ones with no power-source headline within 10 minutes: list them with the nearest story of any kind and its lead. Say plainly what share of May 2025's big moves had no headline the feed carried.

Also write `may2025/reverse/bursts.csv` (one row per burst with all fields) and `may2025/reverse/burst_headlines.csv` (every candidate headline per burst with lead seconds). Validate that every burst in the table appears in the CSV. `git add may2025/reverse && git commit -m "May 2025 phase 3: reverse lookup" && git push`. Reply with: number of bursts, number of big bursts, share explained, and the single most common earliest source.

## Rules that are not negotiable
- Subagent model for phase 1 is Sonnet; for phase 2 is Opus. Never substitute.
- Never patch an output by hand; rerun the batch.
- Never push without the validator printing `OK`.
- Never edit `prompts/`, `reverse/reverse_lookup.py` or any October 2026 file.
- Nothing outside this repository is touched.
