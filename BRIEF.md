# Cloud brief — MNQ news-engine, October 2026 rerun

You are running the model-heavy part of a research pipeline. Everything you need is in this repository. Do not use the web. Do not read or write anything outside this repository. Do not change any input file or any prompt file. Commit and push only validated outputs.

## Phase 1 — screen (do this now)

Inputs: `screen_batches/s_000.jsonl` … `s_041.jsonl` (400 lines each, the last one shorter). Instructions: `prompts/SCREEN_PROMPT.md`.

For **each** batch, run one subagent on the **Sonnet** model (model id `claude-sonnet-5-5`) with this task, 20 subagents at a time at most:

> Read `prompts/SCREEN_PROMPT.md` and follow it exactly. Input: `screen_batches/s_NNN.jsonl`. Write one JSON object per input line, same order, fields `id`, `matters`, `channel`, to `screen_tags/s_NNN.jsonl` with the Write tool. No shell commands, no other files, no web. Reply with one line: lines written and count with matters=1.

When all 42 are done, run:
```
python3 scripts/validate_tags.py screen_batches screen_tags id,matters,channel
```
If it prints anything other than `OK`, rerun **only** the batches it names (delete that tag file first, run the same subagent task again), then validate again. Never edit a tag file by hand.

When it prints `OK`: `git add screen_tags && git commit -m "phase 1: Sonnet screen, 42 batches, validated" && git push`.
Then reply with: the count of matters=1 across all batches, and the validator's last line. Stop and wait.

## Phase 2 — read (only when `read_batches/` appears in the repository after a pull)

Inputs: `read_batches/r_NNN.jsonl` (each line has id, t, src, text, channel_hint, prior, day_context). Two prompts: `prompts/BRAIN_V2_PROMPT.md` and `prompts/BRAIN_V3_PROMPT.md`.

For each read batch, run **two** subagents on the **Opus** model (model id `claude-opus-5-5`):
- one with `prompts/BRAIN_V2_PROMPT.md`, writing to `read_tags_v2/r_NNN.jsonl`, with this one change to the prompt: ignore the sentence "trade = 0 when surprise is 0";
- one with `prompts/BRAIN_V3_PROMPT.md` as written, writing to `read_tags_v3/r_NNN.jsonl`.

Task text for each:
> You are the reading pass of a news desk for MNQ research. Read `<prompt file>` completely and follow it exactly. Input: `<batch file>`. Think carefully about each item: the prior tells you what was already priced, the day_context what was already known. Write exactly one JSON object per input line, same order, with the fields the instructions define, to `<output file>` using the Write tool. No shell commands, no other files, no web. Reply with one line: lines written and count with trade=1.

Validate both:
```
python3 scripts/validate_tags.py read_batches read_tags_v2 id,trade,channel,sign,surprise,magnitude,novelty,duration,confidence
python3 scripts/validate_tags.py read_batches read_tags_v3 id,trade,channel,sign,surprise,magnitude,novelty,duration,confidence
```
Rerun only what the validator names. When both print `OK`: `git add read_tags_v2 read_tags_v3 && git commit -m "phase 2: Opus reads v2 and v3, validated" && git push`. Reply with the two trade counts and the validators' last lines. Stop.

## Rules that are not negotiable
- Subagent model for phase 1 is Sonnet; for phase 2 is Opus. Never substitute.
- Never patch an output by hand; rerun the batch.
- Never push without the validator printing `OK`.
- Nothing outside this repository is touched.
