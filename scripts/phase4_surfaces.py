"""Compact Maglev review surfaces collected on 2026-09-14.

Used when the local API cache is incomplete. Bodies are public GitHub
review text needed for eligibility; they are not gold labels.
"""

from __future__ import annotations

from typing import Any


def _review(login: str, body: str, *, user_type: str = "User", state: str = "COMMENTED") -> dict[str, Any]:
    return {
        "id": None,
        "login": login,
        "user_type": user_type,
        "state": state,
        "body": body,
        "submitted_at": None,
    }


def _body(login: str, body: str, *, user_type: str = "User", source: str = "review_body") -> dict[str, Any]:
    return {
        "id": None,
        "source": source,
        "login": login,
        "user_type": user_type,
        "body": body,
        "inline": False,
        "path": None,
        "created_at": None,
    }


def _issue(login: str, body: str, *, user_type: str = "User") -> dict[str, Any]:
    return _body(login, body, user_type=user_type, source="issue")


def collected(
    number: int,
    *,
    title: str,
    author: str,
    merge_sha: str,
    reviews: list[dict[str, Any]],
    issue: list[dict[str, Any]] | None = None,
    files: list[str] | None = None,
) -> dict[str, Any]:
    bodies = [
        _body(r["login"], r.get("body") or "", user_type=r.get("user_type") or "User")
        for r in reviews
    ]
    names = files or ["internal/restapi/handler.go"]
    return {
        "repo": "OneBusAway/maglev",
        "pr_number": number,
        "title": title,
        "state": "closed",
        "merged": True,
        "merge_sha": merge_sha,
        "author": author,
        "author_type": "User",
        "html_url": f"https://github.com/OneBusAway/maglev/pull/{number}",
        "changed_files": names,
        "changed_file_count": len(names),
        "change_kind": "code",
        "files": [{"filename": n, "status": "modified", "additions": 1, "deletions": 0} for n in names],
        "reviews": reviews,
        "review_count": len(reviews),
        "review_bodies": bodies,
        "inline_comments": [],
        "issue_comments": issue or [],
    }


# Reviews inspected from GET /pulls/{n}/reviews on 2026-09-14.
SURFACES: dict[int, dict[str, Any]] = {
    1374: collected(
        1374,
        title="Stop caching real-time responses as static",
        author="ARCoder181105",
        merge_sha="0ef9904ce5da6d4b04e70ce9a134416b272e5969",
        reviews=[_review("burma-shave", "", state="APPROVED")],
        issue=[
            _issue("coderabbitai[bot]", "Review limit reached", user_type="Bot"),
            _issue("sonarqubecloud[bot]", "Quality Gate passed", user_type="Bot"),
        ],
        files=["internal/restapi/stop_handler.go"],
    ),
    1378: collected(
        1378,
        title="Swallowed duplicated trip lookup errors",
        author="priyanshu7739410",
        merge_sha="5563ac9f4a19c757dd5b594025bb9ef4083c8301",
        reviews=[
            _review("burma-shave", "", state="APPROVED"),
            _review("burma-shave", "merge conflicts", state="CHANGES_REQUESTED"),
            _review("burma-shave", "", state="APPROVED"),
        ],
        issue=[_issue("priyanshu7739410", "author follow-up")],
        files=["internal/restapi/trips_for_route_handler.go"],
    ),
    1365: collected(
        1365,
        title="Fix trips-for-location cap regression test to actually detect the cap",
        author="soumajitgh",
        merge_sha="7043c4160a96bbb0039f945e32a6390133a55289",
        reviews=[],
        issue=[
            _issue("coderabbitai[bot]", "Walkthrough", user_type="Bot"),
            _issue("sonarqubecloud[bot]", "Quality Gate passed", user_type="Bot"),
        ],
        files=["internal/restapi/trips_for_location_handler_test.go"],
    ),
    1284: collected(
        1284,
        title="search-route: complete test coverage and spec verification",
        author="ARCoder181105",
        merge_sha="900fdbedce60cd5b7393572b970826714916018c",
        reviews=[
            _review("coderabbitai[bot]", "Actionable comments posted: 1", user_type="Bot"),
            _review("ARCoder181105", ""),
            _review("Ahmedhossamdev", "LGTM!"),
        ],
        files=["internal/restapi/route_search_handler.go"],
    ),
    1386: collected(
        1386,
        title="Headway-based frequencies in schedule-for-stop",
        author="ARCoder181105",
        merge_sha="4843520d82a4e79d51afedd27cf3504514a62b4c",
        reviews=[
            _review(
                "Ahmedhossamdev",
                "The refactor is well-structured: replacing the three parallel maps "
                "with a single directionScheduleGroup accumulator makes the new frequency "
                "path easy to add. Frequency spec steps are correctly implemented.",
            ),
            _review("burma-shave", "", state="APPROVED"),
            _review("coderabbitai[bot]", "Actionable comments posted: 2", user_type="Bot"),
        ],
        files=["internal/restapi/schedule_for_stop_handler.go"],
    ),
    1329: collected(
        1329,
        title="Multi-timezone trip service dates",
        author="soumajitgh",
        merge_sha="f29b603548aee8bf1b6e4999e324c414513ced30",
        reviews=[
            _review(
                "aaronbrethorst",
                "This looks good. Two genuine bugs fixed. The per-agency midnight is "
                "correct. Keying blockTripsMap on (agencyID, blockID) stops agencies "
                "that reuse raw block_id values from linking trips across agencies.",
                state="APPROVED",
            ),
            _review("coderabbitai[bot]", "Actionable comments posted: 1", user_type="Bot"),
        ],
        files=["internal/restapi/trips_for_location_handler.go"],
    ),
    1428: collected(
        1428,
        title="Reset distanceAlongBlock between configurations",
        author="priyanshu7739410",
        merge_sha="239664889cbb9500a4943c4ba5ac386b4fd2b09a",
        reviews=[
            _review(
                "omlahore",
                "Fix looks right to me. I ran the new test against the merge base and "
                "it fails there on the config 1 assertion, so it is a real regression test. "
                "DistanceAlongBlock of 0 for the first configuration and 433750.77 for the "
                "first stop of the second one both go to 0 with your change.",
            )
        ],
        files=["internal/restapi/block_handler.go"],
    ),
    1372: collected(
        1372,
        title="Precompute stop agency at import",
        author="ARCoder181105",
        merge_sha="b50f8aab7c43fee842a565b1106c11be25de5cc3",
        reviews=[
            _review(
                "burma-shave",
                "Right now stop_agencies only keeps one row per stop. That works for "
                "picking a single agency to show, but some stops are served by more than "
                "one agency. If this table stored one row per stop and agency instead of "
                "collapsing to the lowest one, it could back those lookups too.",
                state="CHANGES_REQUESTED",
            ),
            _review("Ahmedhossamdev", "Same opinion as @burma-shave"),
            _review("coderabbitai[bot]", "Actionable comments posted: 3", user_type="Bot"),
        ],
        files=["gtfsdb/schema.sql", "gtfsdb/client.go"],
    ),
    1288: collected(
        1288,
        title="Track referenced trips in buildTripReferences",
        author="3rabiii",
        merge_sha="09946324a7857ef48b85e36bd5f2e3131e495544",
        reviews=[
            _review(
                "aaronbrethorst",
                "Replacing the t.ID == \"\" zero-value heuristic with an explicit set of "
                "referenced trip IDs is a readability win. The refactor is behavior-neutral, "
                "so it doesn't fix #1287. The sql.ErrNoRows to 404 branch is dead.",
            ),
            _review(
                "burma-shave",
                "Spec conformance: verified this refactor is behavior-neutral. I traced all "
                "four referencedTripIDs insertion sites against the old t.ID == \"\" heuristic.",
            ),
            _review("coderabbitai[bot]", "Actionable comments posted: 2", user_type="Bot"),
        ],
        files=["internal/restapi/trips_for_route_handler.go"],
    ),
    1347: collected(
        1347,
        title="Reuse resolved situations for arrivals",
        author="soumajitgh",
        merge_sha="710c2119b679bb54d062b192c9e5361c5ba1437d",
        reviews=[
            _review(
                "ARCoder181105",
                "Traced both paths — the refactor is output-identical, and the perf win is "
                "real. GetAlertsForTrip and situationRefsForTrip both do GetTrip then GetRoute. "
                "The new test passes on the pre-change code too.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "Four lines of production code for a real win. I traced both sides. "
                "GetAlertsForTrip and situationRefsForTrip do the same resolution.",
                state="APPROVED",
            ),
        ],
        files=["internal/restapi/arrivals_and_departures_for_stop_handler.go"],
    ),
    1348: collected(
        1348,
        title="GTFS frequencies API integration",
        author="soumajitgh",
        merge_sha="a201098396751da220cc596f39cd30e94ef592bc",
        reviews=[
            _review(
                "burma-shave",
                "Frequency merge needs to degrade instead of returning 500 when the "
                "frequency table is incomplete. The handler should keep schedule rows.",
                state="CHANGES_REQUESTED",
            ),
            _review("aaronbrethorst", "Checked the frequency window conversion against Java."),
        ],
        files=["internal/restapi/schedule_for_stop_handler.go"],
    ),
    1298: collected(
        1298,
        title="test: add E2E coverage for DUPLICATED real-time trips",
        author="3rabiii",
        merge_sha="fc606b6f08446c715071bf1216ad39eb83afe2bf",
        reviews=[
            _review(
                "aaronbrethorst",
                "The schedule assertions genuinely cover the stripNumericSuffix fallback. "
                "The references.trips block is tautological for the DUPLICATED path.",
                state="CHANGES_REQUESTED",
            ),
            _review("burma-shave", "merge in main and fix conflicts", state="CHANGES_REQUESTED"),
        ],
        files=["internal/restapi/trips_for_route_handler_test.go"],
    ),
    1300: collected(
        1300,
        title="test: add E2E coverage for status sub-object fields",
        author="3rabiii",
        merge_sha="d5e5408c5c652e7bf170782c771f8a4c1055ff09",
        reviews=[
            _review(
                "aaronbrethorst",
                "Most of this test is load-bearing. assert.GreaterOrEqual on "
                "BlockTripSequence can never fail because calculateBlockTripSequence "
                "returns 0 on any failure.",
                state="CHANGES_REQUESTED",
            ),
            _review("burma-shave", "merge main and fix conflicts", state="CHANGES_REQUESTED"),
        ],
        files=["internal/restapi/trips_for_route_handler_test.go"],
    ),
    1407: collected(
        1407,
        title="Extract per-stop arrivals into shared functions",
        author="ARCoder181105",
        merge_sha="ead664441347f7ad0adaa7e61e2a2b5bb3842c47",
        reviews=[
            _review(
                "burma-shave",
                "Frequency support is missing, and this PR conflicts with main's frequency "
                "work. GetStopsByIDs failure now returns a hard 500 instead of degrading "
                "gracefully. This is an undisclosed behavior change.",
                state="CHANGES_REQUESTED",
            ),
            _review("coderabbitai[bot]", "Actionable comments posted: 2", user_type="Bot"),
        ],
        files=["internal/restapi/arrivals_core.go"],
    ),
    1359: collected(
        1359,
        title="routes-for-location spec test gaps",
        author="ARCoder181105",
        merge_sha="dbddfa8ff53816b5c74695da1a407b717a39d614",
        reviews=[
            _review(
                "Ahmedhossamdev",
                "Test coverage is solid and the behavior changes match Java. One thing to "
                "fix before merge: the default-radius test pins 600m, but Java's no-query "
                "default is 500m.",
            ),
            _review(
                "aaronbrethorst",
                "The tests here are genuinely good. The blocker is "
                "TestRoutesForLocationDefaultRadiusMatches600Meters. Issue #1230 says the "
                "fallback is 500m vs 10km.",
            ),
        ],
        files=["internal/restapi/routes_for_location_handler_test.go"],
    ),
    1296: collected(
        1296,
        title="Clock into ParseTimeParameter plus time-edge tests",
        author="3rabiii",
        merge_sha="94b2035020db6a24300c293a4a227d0d03438b8e",
        reviews=[
            _review(
                "aaronbrethorst",
                "Threading api.Clock into ParseTimeParameter is a real fix. This won't "
                "compile once merged because createTestApiWithTripsForRouteFixture was removed.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "The clock threading is complete and consistent. The new tests actually "
                "depend on the change.",
                state="APPROVED",
            ),
        ],
        files=["internal/utils/api.go"],
    ),
    507: collected(
        507,
        title="fix: add panic recovery middleware for HTTP handlers",
        author="tejasva-vardhan",
        merge_sha="8328235a30ac0bdda6b964fae5d475f63af79389",
        reviews=[
            _review(
                "aaronbrethorst",
                "recoveryResponseWriter must also override Write() to track response state. "
                "If a handler calls w.Write(data) and then panics, the recovery code writes "
                "a 500 JSON response on top of the already-committed 200.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "The Write() override, JSON encoding error logging, and panic(error) test "
                "look correct.",
                state="APPROVED",
            ),
        ],
        issue=[
            _issue("ARCoder181105", "Add test for the middleware"),
            _issue("tejasva-vardhan", "Added tests for the middleware as suggested."),
        ],
        files=["internal/restapi/recovery_middleware.go"],
    ),
    702: collected(
        702,
        title="refactor: extract withTransaction helper for GTFS bulk imports",
        author="tejasva-vardhan",
        merge_sha="abebfc2f9193603f67b25ac6b976623623857826",
        reviews=[
            _review(
                "aaronbrethorst",
                "The Stops field addition needs its own PR. db.Begin() to BeginTx(ctx, nil) "
                "is a behavioral change. Wrap errors in withTransaction. "
                "bulkInsertCalendarDates lost its logging.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "Error wrapping with labels, restored logging, godoc update, and clean "
                "separation of the Stops/Trips removal are exactly as requested.",
                state="APPROVED",
            ),
        ],
        issue=[
            _issue("tejasva-vardhan", "I noticed the OpenAPI conformance failures."),
            _issue(
                "aaronbrethorst",
                "Please rebase on top of main and push up the changes.",
            ),
        ],
        files=["gtfsdb/helpers.go"],
    ),
}

ADDITIONAL_ACCEPTED: dict[int, dict[str, Any]] = {
    457: collected(
        457,
        title="Fix data race in routesForAgencyHandler by adding RLock",
        author="tejasva-vardhan",
        merge_sha="e1044a52bfdca7b1297140514df56eb4b1724cf8",
        reviews=[
            _review(
                "aaronbrethorst",
                "Good catch on the missing read lock. FindAgency() and RoutesForAgencyID() "
                "both document that the caller must hold manager.RLock(). Remove the "
                "redundant ValidateID call because withID() already validates.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "The redundant ValidateID call is removed. RLock()/defer RUnlock() before "
                "FindAgency() correctly follows the documented contract.",
                state="APPROVED",
            ),
        ],
        issue=[
            _issue(
                "tejasva-vardhan",
                "Thanks for the review! Removed the redundant ValidateID call.",
            )
        ],
        files=["internal/restapi/routes_for_agency_handler.go"],
    ),
    354: collected(
        354,
        title="fix: resolve race condition in GetAlertsForTrip by adding read lock",
        author="3rabiii",
        merge_sha="0ac83b202744ff53c4295605f18e350010ee2eb1",
        reviews=[
            _review(
                "aaronbrethorst",
                "Nice catch identifying the TOCTOU race. The fix as implemented will "
                "introduce a deadlock: all three callers already hold staticMutex.RLock() "
                "and Go RWMutex is not reentrant.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "The deadlock-inducing RLock() calls are gone, replaced by the documentation "
                "comment making the caller-holds-lock contract explicit.",
                state="APPROVED",
            ),
        ],
        files=["internal/gtfs/gtfs_manager.go"],
    ),
    372: collected(
        372,
        title="perf: Optimize RoutesForAgencyID lookup to O(1) and fix concurrency issues",
        author="ARCoder181105",
        merge_sha="f583f801f83a890fc109cb1e6ebb884221cb5c85",
        reviews=[
            _review(
                "aaronbrethorst",
                "The map-based lookup is clean. You also caught the data race in "
                "AdvancedDirectionCalculator. Changelog-style comments on the mutex "
                "additions should describe what the code does.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "The routesByAgencyID index follows buildLookupMaps. The "
                "AdvancedDirectionCalculator race fix adds real safety.",
                state="APPROVED",
            ),
        ],
        files=["internal/gtfs/gtfs_manager.go", "internal/gtfs/advanced_direction_calculator.go"],
    ),
    541: collected(
        541,
        title="fix: eliminate potential deadlock in VehiclesForAgencyID and enforce lock ordering policy",
        author="AhmedAlian7",
        merge_sha="7b254ab066f5a1b5a4ec253d37d7efae1e980df4",
        reviews=[
            _review(
                "aaronbrethorst",
                "The two-phase locking approach in VehiclesForAgencyID is the right design. "
                "Acquiring and releasing staticMutex before independently acquiring "
                "realTimeMutex eliminates the nested lock pattern. TOCTOU gap between "
                "phases is benign for a read-only API.",
                state="APPROVED",
            )
        ],
        files=["internal/gtfs/gtfs_manager.go"],
    ),
    756: collected(
        756,
        title="fix: eliminate double-locking by replacing lru.Cache with simplelru.LRU",
        author="AhmedAlian7",
        merge_sha="d61a365d2e8e0a4f95e36629de73b101b9a2199a",
        reviews=[
            _review(
                "aaronbrethorst",
                "Switching from thread-safe lru.Cache to raw simplelru.LRU is the right fix "
                "since the external sync.Mutex already provides synchronization. This PR "
                "correctly wraps Stop() with the mutex because Purge() mutates internal state.",
                state="APPROVED",
            )
        ],
        files=["internal/restapi/rate_limit_middleware.go"],
    ),
    691: collected(
        691,
        title="fix: resolve race condition and double HTTP write in location APIs",
        author="AhmedAlian7",
        merge_sha="64bd948f107fbddc03e3e9f02cb16a2db9fc0d78",
        reviews=[
            _review(
                "aaronbrethorst",
                "Moving RLock()/RUnlock() above parseAndValidateRequest in "
                "trips_for_location_handler.go ensures GetAgencies() is safely called "
                "under the read lock. Removing ResponseWriter writes from inside "
                "parseLocationParams fixes the double HTTP write.",
                state="CHANGES_REQUESTED",
            ),
            _review(
                "aaronbrethorst",
                "The nil return on the happy path is in place, and the merge conflicts "
                "are resolved. Race condition fix verified.",
                state="APPROVED",
            ),
        ],
        files=["internal/restapi/trips_for_location_handler.go", "internal/restapi/location_params.go"],
    ),
    271: collected(
        271,
        title="fix(concurrency): add missing RLock in debugIndexHandler",
        author="3rabiii",
        merge_sha="c718a713adabe64fdc201533ea079717aaf15299",
        reviews=[
            _review(
                "aaronbrethorst",
                "The debug handler was violating the GetStaticData() contract which "
                "states the caller must hold manager.RLock() before calling this method.",
                state="APPROVED",
            )
        ],
        files=["internal/webui/debug_index_handler.go"],
    ),
}
