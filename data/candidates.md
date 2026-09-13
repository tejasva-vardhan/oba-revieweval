# Candidate corpus (n = 30)

**Repository:** [OneBusAway/maglev](https://github.com/OneBusAway/maglev)  
**Discovery date:** 2026-09-13  
**Discovery method:** GitHub Search API, unauthenticated.

1. Author-merged PRs (`author:tejasva-vardhan org:OneBusAway is:pr is:merged`) — 12 hits. Issue-comment humans (bots removed): independent humans only on `#507` (ARCoder181105) and `#702` (aaronbrethorst). `#1346` is docs-only (excluded). Other author PRs have no independent human issue/inline comments in the public comment APIs and are **excluded from the gold set** until Phase 4 checks `/pulls/{n}/reviews`.
2. Other merged Maglev PRs with `comments:>=2`, Dependabot excluded. First search page used; 453 total matches exist — this is a **sample**, not a random sample of all Maglev history.

**Phase 4 must drop** any candidate whose remaining discussion is bot-only (CodeRabbit, etc.). Titles below are public PR titles.

| # | Stratum | Author | Why listed | URL |
|---|---|---|---|---|
| 1277 | api_gtfs | other | Spec interaction `includeTrip` / `includeStatus`; 16 issue comments | https://github.com/OneBusAway/maglev/pull/1277 |
| 1317 | api_gtfs | other | Scheduled trips without real-time vehicle | https://github.com/OneBusAway/maglev/pull/1317 |
| 1316 | api_gtfs | other | Service date of a trip instance | https://github.com/OneBusAway/maglev/pull/1316 |
| 1352 | api_gtfs | other | Time formats in stops-for-location | https://github.com/OneBusAway/maglev/pull/1352 |
| 1404 | api_gtfs | other | `readableTime` timezone | https://github.com/OneBusAway/maglev/pull/1404 |
| 1313 | api_gtfs | other | Situation references on every endpoint | https://github.com/OneBusAway/maglev/pull/1313 |
| 1380 | api_gtfs | other | Agency stop fetch polluted by other agencies | https://github.com/OneBusAway/maglev/pull/1380 |
| 1286 | api_gtfs | other | `serviceDate` after midnight | https://github.com/OneBusAway/maglev/pull/1286 |
| 1281 | api_gtfs | other | trip-for-vehicle includeReferences | https://github.com/OneBusAway/maglev/pull/1281 |
| 1385 | api_gtfs | other | Validate schedule-for-stop date | https://github.com/OneBusAway/maglev/pull/1385 |
| 1375 | api_gtfs | other | Parent route agency references | https://github.com/OneBusAway/maglev/pull/1375 |
| 1315 | api_gtfs | other | Schedule timezone / outOfRange | https://github.com/OneBusAway/maglev/pull/1315 |
| 1348 | api_gtfs | other | GTFS frequencies API integration | https://github.com/OneBusAway/maglev/pull/1348 |
| 1386 | api_gtfs | other | Headway-based frequencies in schedule-for-stop | https://github.com/OneBusAway/maglev/pull/1386 |
| 1329 | api_gtfs | other | Multi-timezone trip service dates | https://github.com/OneBusAway/maglev/pull/1329 |
| 1374 | concurrency | other | Stop caching real-time responses as static | https://github.com/OneBusAway/maglev/pull/1374 |
| 1428 | concurrency | other | Reset `distanceAlongBlock` between configurations | https://github.com/OneBusAway/maglev/pull/1428 |
| 1372 | database | other | Precompute stop agency at import | https://github.com/OneBusAway/maglev/pull/1372 |
| 1378 | database | other | Swallowed duplicated trip lookup errors | https://github.com/OneBusAway/maglev/pull/1378 |
| 1288 | database | other | Track referenced trips in `buildTripReferences` | https://github.com/OneBusAway/maglev/pull/1288 |
| 1347 | database | other | Reuse resolved situations for arrivals | https://github.com/OneBusAway/maglev/pull/1347 |
| 702 | database | tejasva-vardhan | Transaction helper; independent commenter aaronbrethorst | https://github.com/OneBusAway/maglev/pull/702 |
| 1298 | test_refactor | other | E2E coverage for DUPLICATED real-time trips | https://github.com/OneBusAway/maglev/pull/1298 |
| 1300 | test_refactor | other | E2E coverage for status sub-object | https://github.com/OneBusAway/maglev/pull/1300 |
| 1407 | test_refactor | other | Extract per-stop arrivals into shared functions | https://github.com/OneBusAway/maglev/pull/1407 |
| 1359 | test_refactor | other | routes-for-location spec test gaps | https://github.com/OneBusAway/maglev/pull/1359 |
| 1365 | test_refactor | other | trips-for-location cap regression test | https://github.com/OneBusAway/maglev/pull/1365 |
| 1296 | test_refactor | other | Clock into ParseTimeParameter + time-edge tests | https://github.com/OneBusAway/maglev/pull/1296 |
| 1284 | test_refactor | other | search-route tests and spec verification | https://github.com/OneBusAway/maglev/pull/1284 |
| 507 | api_gtfs | tejasva-vardhan | Panic recovery middleware; independent commenter ARCoder181105 | https://github.com/OneBusAway/maglev/pull/507 |

Stratum counts in this list: api_gtfs 16 (incl. 507), concurrency 2, database 5 (incl. 702), test_refactor 7.

**Known imbalance:** concurrency is thin because few high-comment Maglev PRs in the search page were race/lock PRs, and the author's `#457` (data race + RLock) has **no independent human comments** in the APIs we called. Phase 4 should search review threads or additional PRs (`race`, `lock`, `mutex`, `concurrent`) rather than force `#457` into gold.

Machine-readable copy of the discovery dump: `data/candidates_raw.json` (search hits, not the final 30).
