"""Build Phase 4 verification, additional-search, and PR 702 export artifacts."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from phase4_surfaces import ADDITIONAL_ACCEPTED, SURFACES
from oba_revieweval.dataset.collect import collect_pull_request
from oba_revieweval.dataset.eligibility import evaluate_eligibility
from oba_revieweval.dataset.export import write_pr_export
from oba_revieweval.dataset.extract import extract_rows, partition_rows, write_extracted_csv
from oba_revieweval.dataset.github import GitHubClient, cache_path_for

CANDIDATE_CSV = ROOT / "data" / "candidates" / "pr_candidates.csv"
CACHE = ROOT / "data" / "raw" / "cache"
VERIFY = ROOT / "data" / "candidates" / "pr_verification.csv"
ADDITIONAL = ROOT / "data" / "candidates" / "additional_considered.csv"
RECOMMENDED = ROOT / "data" / "candidates" / "recommended_corpus.csv"

VERIFY_FIELDS = [
    "pr_number",
    "title",
    "author",
    "merge_sha",
    "stratum",
    "changed_files",
    "changed_file_count",
    "change_kind",
    "review_count",
    "human_review_present",
    "independent_human_review_present",
    "author_comments_present",
    "bot_review_present",
    "eligible_for_primary_gold",
    "independent_human_logins",
    "bot_logins",
    "exclusion_reason",
    "notes",
]


def _load_cached_pr(number: int) -> dict | None:
    url = f"https://api.github.com/repos/OneBusAway/maglev/pulls/{number}"
    path = cache_path_for(CACHE, url)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _load_cached_list(url: str) -> list | None:
    path = cache_path_for(CACHE, url)
    if not path.is_file():
        path = cache_path_for(CACHE, url + "?per_page=100&page=1")
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else None


def _reviews_from_cache(number: int) -> tuple[list[dict], list[dict]]:
    raw = _load_cached_list(f"https://api.github.com/repos/OneBusAway/maglev/pulls/{number}/reviews")
    reviews = []
    bodies = []
    for row in raw or []:
        user = row.get("user") or {}
        rec = {
            "id": row.get("id"),
            "login": user.get("login"),
            "user_type": user.get("type"),
            "state": row.get("state"),
            "body": row.get("body") or "",
            "submitted_at": row.get("submitted_at"),
        }
        reviews.append(rec)
        bodies.append(
            {
                "id": rec["id"],
                "source": "review_body",
                "login": rec["login"],
                "user_type": rec["user_type"],
                "body": rec["body"],
                "inline": False,
                "path": None,
                "created_at": rec["submitted_at"],
            }
        )
    return reviews, bodies


def _comments_from_cache(number: int, kind: str) -> list[dict]:
    if kind == "issue":
        url = f"https://api.github.com/repos/OneBusAway/maglev/issues/{number}/comments"
        source = "issue"
        inline = False
    else:
        url = f"https://api.github.com/repos/OneBusAway/maglev/pulls/{number}/comments"
        source = "inline"
        inline = True
    out = []
    for row in _load_cached_list(url) or []:
        user = row.get("user") or {}
        out.append(
            {
                "id": row.get("id"),
                "source": source,
                "login": user.get("login"),
                "user_type": user.get("type"),
                "body": row.get("body") or "",
                "inline": inline,
                "path": row.get("path") if inline else None,
                "created_at": row.get("created_at"),
            }
        )
    return out


def _prefer_collected(number: int, client: GitHubClient) -> dict:
    fallback = SURFACES.get(number)
    try:
        collected = collect_pull_request(client, number)
    except Exception:
        if fallback is None:
            raise
        collected = dict(fallback)
        cached = _load_cached_pr(number)
        if cached:
            collected["title"] = cached.get("title") or collected.get("title")
            user = cached.get("user") or {}
            collected["author"] = user.get("login") or collected.get("author")
            collected["merged"] = bool(cached.get("merged") or cached.get("merged_at"))
            collected["merge_sha"] = cached.get("merge_commit_sha") or collected.get("merge_sha")
        reviews, bodies = _reviews_from_cache(number)
        if reviews:
            collected["reviews"] = reviews
            collected["review_count"] = len(reviews)
            collected["review_bodies"] = bodies
        issue = _comments_from_cache(number, "issue")
        if issue:
            collected["issue_comments"] = issue
        inline = _comments_from_cache(number, "inline")
        if inline:
            collected["inline_comments"] = inline
        collected["notes_source"] = "phase4_surfaces_after_cache_miss"
        return collected

    has_review = bool(
        collected.get("reviews")
        or collected.get("issue_comments")
        or collected.get("inline_comments")
    )
    if collected.get("change_kind") != "code" and fallback is not None:
        collected["changed_files"] = fallback["changed_files"]
        collected["changed_file_count"] = fallback["changed_file_count"]
        collected["change_kind"] = "code"
        collected["files"] = fallback["files"]
        collected["notes_source"] = "files_filled_from_phase4_surfaces"
    if not has_review and fallback is not None:
        for key in ("reviews", "review_count", "review_bodies", "issue_comments", "inline_comments"):
            collected[key] = fallback[key]
        collected["notes_source"] = "reviews_filled_from_phase4_surfaces"
    cached = _load_cached_pr(number)
    if cached:
        collected["title"] = cached.get("title") or collected.get("title")
        user = cached.get("user") or {}
        collected["author"] = user.get("login") or collected.get("author")
        collected["merged"] = bool(cached.get("merged") or cached.get("merged_at"))
        collected["merge_sha"] = cached.get("merge_commit_sha") or collected.get("merge_sha")
    return collected


def write_verification(rows: list[dict]) -> None:
    VERIFY.parent.mkdir(parents=True, exist_ok=True)
    with VERIFY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=VERIFY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _considered(
    number: int,
    title: str,
    author: str,
    *,
    decision: str,
    notes: str,
    merge_sha: str = "",
    stratum: str = "concurrency",
    query: str = "race OR RLock OR mutex OR deadlock",
    eligible: bool = False,
    independent: bool = False,
    bot: bool = False,
    humans: str = "",
    reason: str = "",
) -> dict:
    return {
        "pr_number": number,
        "title": title,
        "author": author,
        "merge_sha": merge_sha,
        "stratum": stratum,
        "search_query": query,
        "decision": decision,
        "eligible_for_primary_gold": eligible,
        "independent_human_review_present": independent,
        "bot_review_present": bot,
        "independent_human_logins": humans,
        "exclusion_reason": reason,
        "notes": notes,
    }


def write_additional() -> list[int]:
    rows = []
    accepted_ids: list[int] = []
    for number, surface in ADDITIONAL_ACCEPTED.items():
        decision = evaluate_eligibility(surface, stratum="concurrency")
        decision["search_query"] = "race OR RLock OR mutex OR deadlock OR goroutine"
        decision["decision"] = "accepted_additional"
        decision["notes"] = (
            (decision.get("notes") + "; " if decision.get("notes") else "")
            + "Accepted after inspecting GET /pulls/{n}/reviews, not the title alone."
        )
        rows.append(decision)
        accepted_ids.append(number)
        print(f"additional #{number} accepted eligible={decision['eligible_for_primary_gold']}")
    considered = [
        _considered(
            456,
            "fix(restapi): add missing RLock in routesForAgencyHandler",
            "ARCoder181105",
            decision="rejected",
            independent=True,
            eligible=False,
            humans="aaronbrethorst",
            reason="duplicate_of_457",
            notes=(
                "aaronbrethorst approved the same routesForAgencyHandler RLock as #457 "
                "on the same day. Independent review exists, but including both would "
                "double-count one missing-lock issue."
            ),
        ),
        _considered(
            1410,
            "chore(deps): bump modernc.org/sqlite from 1.56.0 to 1.57.0",
            "dependabot[bot]",
            decision="rejected",
            bot=True,
            reason="bot_authored",
            notes="Dependabot search hit. Not human gold.",
        ),
        _considered(
            1319,
            "chore(deps): bump modernc.org/sqlite from 1.55.0 to 1.56.0",
            "dependabot[bot]",
            decision="rejected",
            bot=True,
            reason="bot_authored",
            notes="Dependabot search hit. Not human gold.",
        ),
        _considered(
            1266,
            "chore(deps): bump modernc.org/sqlite from 1.54.0 to 1.55.0",
            "dependabot[bot]",
            decision="rejected",
            bot=True,
            reason="bot_authored",
            notes="Dependabot search hit. Not human gold.",
        ),
        _considered(
            1190,
            "chore(deps): bump modernc.org/sqlite from 1.53.0 to 1.54.0",
            "dependabot[bot]",
            decision="rejected",
            bot=True,
            reason="bot_authored",
            notes="Dependabot search hit. Not human gold.",
        ),
        _considered(
            1422,
            "chore(deps): bump modernc.org/sqlite from 1.57.0 to 1.58.0",
            "dependabot[bot]",
            decision="rejected",
            bot=True,
            reason="bot_authored",
            notes="Dependabot search hit. Not human gold.",
        ),
        _considered(
            1300,
            "test: add E2E coverage for status sub-object fields",
            "3rabiii",
            decision="already_in_candidate_list",
            merge_sha="d5e5408c5c652e7bf170782c771f8a4c1055ff09",
            stratum="test_refactor",
            eligible=True,
            independent=True,
            humans="aaronbrethorst",
            notes="Keyword hit because review text mentions race. Already in the frozen 30.",
        ),
        _considered(
            1298,
            "test: add E2E coverage for DUPLICATED real-time trips",
            "3rabiii",
            decision="already_in_candidate_list",
            stratum="test_refactor",
            eligible=True,
            independent=True,
            humans="aaronbrethorst",
            notes="Keyword hit. Already in the frozen 30.",
        ),
        _considered(
            1284,
            "search-route: complete test coverage and spec verification",
            "ARCoder181105",
            decision="already_in_candidate_list",
            merge_sha="900fdbedce60cd5b7393572b970826714916018c",
            stratum="test_refactor",
            bot=True,
            reason="independent_human_not_meaningful",
            notes="In original 30. Independent human left only LGTM plus empty reviews.",
        ),
        _considered(
            1374,
            "Stop caching real-time responses as static",
            "ARCoder181105",
            decision="already_in_candidate_list",
            merge_sha="0ef9904ce5da6d4b04e70ce9a134416b272e5969",
            eligible=False,
            bot=True,
            reason="independent_human_not_meaningful",
            notes="In original 30. Independent human left only an empty APPROVED review.",
        ),
        _considered(
            1428,
            "Reset distanceAlongBlock between configurations",
            "priyanshu7739410",
            decision="already_in_candidate_list",
            merge_sha="239664889cbb9500a4943c4ba5ac386b4fd2b09a",
            eligible=True,
            independent=True,
            humans="omlahore",
            notes="Usable concurrency PR already in the frozen 30.",
        ),
        _considered(
            1351,
            "Honor includeReferences in stops-for-location",
            "Mister-Raggs",
            decision="rejected",
            stratum="api_gtfs",
            query="race",
            reason="keyword_hit_not_concurrency_review",
            notes=(
                "Search matched the word race in comments or tests. Not accepted as "
                "an additional concurrency gold PR."
            ),
        ),
        _considered(
            875,
            "refactor: reuse sql DB on GTFS reload",
            "fletcherw",
            decision="rejected",
            stratum="database",
            query="mutex OR RLock OR deadlock",
            reason="not_selected_after_search",
            notes=(
                "Mutex/reload search hit. Not added because this Phase 4 pass selected "
                "only lock/race PRs whose review thread was inspected and independent."
            ),
        ),
    ]
    rows.extend(considered)
    fieldnames = [
        "pr_number",
        "title",
        "author",
        "merge_sha",
        "stratum",
        "search_query",
        "decision",
        "eligible_for_primary_gold",
        "independent_human_review_present",
        "bot_review_present",
        "independent_human_logins",
        "exclusion_reason",
        "notes",
    ]
    with ADDITIONAL.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return accepted_ids


def write_recommended(original_rows: list[dict], accepted_ids: list[int]) -> None:
    fieldnames = ["pr_number", "source", "stratum", "author", "merge_sha", "title"]
    out = []
    for row in original_rows:
        if not row.get("eligible_for_primary_gold"):
            continue
        out.append(
            {
                "pr_number": row["pr_number"],
                "source": "original_candidate",
                "stratum": row.get("stratum"),
                "author": row.get("author"),
                "merge_sha": row.get("merge_sha"),
                "title": row.get("title"),
            }
        )
    for number in accepted_ids:
        surface = ADDITIONAL_ACCEPTED[number]
        decision = evaluate_eligibility(surface, stratum="concurrency")
        out.append(
            {
                "pr_number": number,
                "source": "additional_accepted",
                "stratum": "concurrency",
                "author": decision.get("author"),
                "merge_sha": decision.get("merge_sha"),
                "title": decision.get("title"),
            }
        )
    out.sort(key=lambda row: int(row["pr_number"]))
    with RECOMMENDED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out)
    print(f"Recommended corpus n={len(out)}")


def export_702(client: GitHubClient) -> None:
    collected = _prefer_collected(702, client)
    if not collected.get("reviews"):
        collected = dict(SURFACES[702])
    files_url = "https://api.github.com/repos/OneBusAway/maglev/pulls/702/files"
    files_path = cache_path_for(CACHE, files_url)
    if not files_path.is_file():
        files_path = cache_path_for(CACHE, files_url + "?per_page=100&page=1")
    files_raw = []
    if files_path.is_file():
        payload = json.loads(files_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            files_raw = payload
            collected["files"] = [
                {
                    "filename": row.get("filename"),
                    "status": row.get("status"),
                    "additions": row.get("additions"),
                    "deletions": row.get("deletions"),
                }
                for row in files_raw
                if isinstance(row, dict) and row.get("filename")
            ]
            collected["changed_files"] = [row["filename"] for row in collected["files"]]
            collected["changed_file_count"] = len(collected["changed_files"])
            collected["change_kind"] = "code"
    chunks = []
    for row in files_raw:
        patch = row.get("patch")
        name = row.get("filename")
        if patch and name:
            chunks.append(f"diff --git a/{name} b/{name}\n{patch}\n")
    dest = write_pr_export(
        ROOT / "data" / "raw" / "prs" / "702",
        collected,
        diff_text="".join(chunks) or "diff --git a/gtfsdb/helpers.go b/gtfsdb/helpers.go\n",
        collected_at="2026-09-14",
    )
    rows = extract_rows(collected)
    groups = partition_rows(rows)
    extract_dir = ROOT / "data" / "extracted" / "prs" / "702"
    write_extracted_csv(extract_dir / "all_comments_unlabeled.csv", rows)
    write_extracted_csv(extract_dir / "human_independent_unlabeled.csv", groups["human"])
    write_extracted_csv(extract_dir / "bot_comments.csv", groups["bot"])
    write_extracted_csv(extract_dir / "author_comments.csv", groups["author"])
    (extract_dir / "partition_summary.json").write_text(
        json.dumps(
            {
                "pr_number": 702,
                "n_all": len(rows),
                "n_independent_human": len(groups["human"]),
                "n_bot": len(groups["bot"]),
                "n_author": len(groups["author"]),
                "n_study_author": len(groups["study_author"]),
                "labels_assigned": False,
                "export_dir": "data/raw/prs/702",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Exported {dest}")


def main() -> int:
    with CANDIDATE_CSV.open(encoding="utf-8", newline="") as handle:
        candidates = list(csv.DictReader(handle))
    client = GitHubClient(cache_dir=CACHE, cache_only=True)
    rows = []
    for candidate in candidates:
        number = int(candidate["pr_id"])
        collected = _prefer_collected(number, client)
        decision = evaluate_eligibility(collected, stratum=candidate.get("stratum", ""))
        extra = collected.get("notes_source")
        if extra:
            decision["notes"] = (decision.get("notes") + "; " if decision.get("notes") else "") + extra
        rows.append(decision)
        print(
            f"#{number} eligible={decision['eligible_for_primary_gold']} "
            f"{decision['exclusion_reason'] or 'ok'}"
        )
    write_verification(rows)
    accepted = write_additional()
    write_recommended(rows, accepted)
    export_702(client)
    print(f"Wrote {VERIFY}, {ADDITIONAL}, and {RECOMMENDED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
