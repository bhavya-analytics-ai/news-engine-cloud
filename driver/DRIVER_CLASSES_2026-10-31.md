### **Saturday, October 31, 2026 — 5:21 AM EDT**

`HEAD` none (this folder is not a git repo) · cloud repo `bhavya-analytics-ai/news-engine-cloud` `433db0c` · same bursts and chance minutes as `DRIVER_TABLE_2026-10-31.md` (`driver/per_burst.csv`) · post classes measured from the data only: no model tags, no keyword list

# Post classes against bursts — October 2026 and May 2025

Window 600 s before to 60 s after the burst minute's open; **led** = the class's event came before t0. Chance = the same on random non-burst minutes matched by time-of-day bucket, same count.

| class | definition |
|---|---|
| relay3 | story posted by ≥ 3 sources within 60 s (time of the 3rd) |
| relay5 | story posted by ≥ 5 sources within 60 s (time of the 5th) |
| surge_all | all sources pooled: posts in trailing 120 s above their 2-year 99th percentile |
| surge_channel | any one channel above its own 2-year 99th percentile of posts per 120 s |
| new_story | first arrival with no similar post (word Jaccard ≥ 0.3) in the previous hour |

99th-percentile thresholds, posts per 120 s: ALL 33, GeoPWatch 3, Megatron_ron 2, SCMPNews 3, WalterBloomberg 5, WatcherGuru 1, financialjuice 11, firstsquaw 9, insiderpaper 2, marketfeed 32, nhkworld 19, osintdefender 3, truth_social 10.

## 1. Bursts led by each class, against chance


### October 2026

| class | tier | bursts led | share | chance led | chance share | gap (pts) | median lead s |
|---|---|---|---|---|---|---|---|
| relay3 | ALL | 56 of 392 | 14 % | 60 of 392 | 15 % | -1 | 347 |
| relay3 | BIG | 29 of 137 | 21 % | 33 of 137 | 24 % | -3 | 360 |
| relay5 | ALL | 0 of 392 | 0 % | 0 of 392 | 0 % | +0 | – |
| relay5 | BIG | 0 of 137 | 0 % | 0 of 137 | 0 % | +0 | – |
| surge_all | ALL | 13 of 392 | 3 % | 5 of 392 | 1 % | +2 | 219 |
| surge_all | BIG | 6 of 137 | 4 % | 0 of 137 | 0 % | +4 | 254 |
| surge_channel | ALL | 14 of 392 | 4 % | 7 of 392 | 2 % | +2 | 226 |
| surge_channel | BIG | 8 of 137 | 6 % | 2 of 137 | 1 % | +4 | 285 |
| new_story | ALL | 369 of 392 | 94 % | 367 of 392 | 94 % | +1 | 524 |
| new_story | BIG | 135 of 137 | 99 % | 131 of 137 | 96 % | +3 | 537 |

### May 2025

| class | tier | bursts led | share | chance led | chance share | gap (pts) | median lead s |
|---|---|---|---|---|---|---|---|
| relay3 | ALL | 9 of 462 | 2 % | 7 of 462 | 2 % | +0 | 343 |
| relay3 | BIG | 4 of 85 | 5 % | 2 of 85 | 2 % | +2 | 430 |
| relay5 | ALL | 0 of 462 | 0 % | 0 of 462 | 0 % | +0 | – |
| relay5 | BIG | 0 of 85 | 0 % | 0 of 85 | 0 % | +0 | – |
| surge_all | ALL | 13 of 462 | 3 % | 13 of 462 | 3 % | +0 | 273 |
| surge_all | BIG | 4 of 85 | 5 % | 1 of 85 | 1 % | +4 | 270 |
| surge_channel | ALL | 9 of 462 | 2 % | 9 of 462 | 2 % | +0 | 271 |
| surge_channel | BIG | 3 of 85 | 4 % | 1 of 85 | 1 % | +2 | 367 |
| new_story | ALL | 434 of 462 | 94 % | 437 of 462 | 95 % | -1 | 502 |
| new_story | BIG | 79 of 85 | 93 % | 82 of 85 | 96 % | -4 | 508 |

### Both months

| class | tier | bursts led | share | chance led | chance share | gap (pts) | median lead s |
|---|---|---|---|---|---|---|---|
| relay3 | ALL | 65 of 854 | 8 % | 67 of 854 | 8 % | -0 | 343 |
| relay3 | BIG | 33 of 222 | 15 % | 35 of 222 | 16 % | -1 | 360 |
| relay5 | ALL | 0 of 854 | 0 % | 0 of 854 | 0 % | +0 | – |
| relay5 | BIG | 0 of 222 | 0 % | 0 of 222 | 0 % | +0 | – |
| surge_all | ALL | 26 of 854 | 3 % | 18 of 854 | 2 % | +1 | 248 |
| surge_all | BIG | 10 of 222 | 5 % | 1 of 222 | 0 % | +4 | 254 |
| surge_channel | ALL | 23 of 854 | 3 % | 16 of 854 | 2 % | +1 | 271 |
| surge_channel | BIG | 11 of 222 | 5 % | 3 of 222 | 1 % | +4 | 291 |
| new_story | ALL | 803 of 854 | 94 % | 804 of 854 | 94 % | -0 | 508 |
| new_story | BIG | 214 of 222 | 96 % | 213 of 222 | 96 % | +0 | 528 |

## 2. Which channel surged, both months (windows with that channel above its own 99th percentile before t0)

| channel | ALL bursts | chance | BIG bursts | chance |
|---|---|---|---|---|
| SCMPNews | 0 % | 0 % | 0 % | 0 % |
| WalterBloomberg | 0 % | 0 % | 1 % | 0 % |
| financialjuice | 1 % | 0 % | 3 % | 1 % |
| firstsquaw | 0 % | 1 % | 0 % | 0 % |
| marketfeed | 1 % | 1 % | 1 % | 0 % |

## 3. BIG bursts with a relay-5 or surge-all event before them

| time ET | size | classes (lead s) |
|---|---|---|
| 2025-05-06 12:20 | -33.8 | surge_all +166: 34 posts/120s; surge_channel +160: marketfeed; new_story +493: financialjuice: Trump on Carney: We have a lot of things in common./FJ |
| 2025-05-07 14:05 | -122.2 | surge_all +374: 34 posts/120s; surge_channel +367: marketfeed; new_story +563: financialjuice: Trump: We had a good outcome with Houthis./FJ |
| 2025-05-12 03:12 | +32.8 | surge_all +139: 34 posts/120s; new_story +564: SCMPNews: Nearly 30% of Hong Kong secondary pupils thought of self-harm, suicide |
| 2025-05-19 09:30 | +42.5 | surge_all +561: 34 posts/120s; surge_channel +559: marketfeed; new_story +596: SCMPNews: China’s economic resilience muffles speculations over imminent fiscal  |
| 2026-09-30 08:36 | -35.5 | surge_all +288: 34 posts/120s; surge_channel +291: financialjuice; new_story +529: marketfeed: 🇺🇸US PRE-MARKET MOVERS🇺🇸 ES +0.1% NQ -0.1% RTY FLAT   $CNXC -10%: RE |
| 2026-10-15 08:39 | +57.5 | surge_all +465: 34 posts/120s; surge_channel +475: financialjuice; new_story +531: firstsquaw: US INITIAL JOBLESS CLAIMS ACTUAL: 199K VS 197K PREVIOUS; EST 200K (@ |
| 2026-10-28 09:48 | -51.0 | surge_all +62: 34 posts/120s; surge_channel +80: financialjuice; new_story +498: SCMPNews: US midterms could trigger a debt ceiling showdown worse than 2011  htt |
| 2026-10-28 14:41 | +54.8 | relay3 +515: 579129; surge_all +123: 34 posts/120s; surge_channel +498: WalterBloomberg; new_story +588: WalterBloomberg: $ORCL  - ORACLE TARGETS $225 BILLION IN REVENUE BY 2030  Oracle |
| 2026-10-28 14:44 | -57.5 | surge_all +303: 34 posts/120s; surge_channel +315: financialjuice; new_story +553: WalterBloomberg: WARSH: NOT SURPRISED BY FINANCIAL MARKET VOLATILITY (@WalterBlo |
| 2026-10-29 08:35 | -31.8 | surge_all +219: 34 posts/120s; surge_channel +216: financialjuice; new_story +564: firstsquaw: MERZ: PROCESS TO FIND LAGARDE SUCCESSOR TO COMPLETE BY YR-END (@Firs |

## 4. Limits

- No direction: these classes say a story is loud or new, not which way it points.
- Relays are matched by the corpus de-duplication (`story_id`); a story reworded by a channel counts as a different story.
- Thresholds are percentiles over two years of posts, set once, not tuned on the bursts.
- Chance sets are the same size as the burst sets; a gap of a few points on BIG (85 to 222 windows) is inside sampling noise.
