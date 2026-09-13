"""Build and validate the Phase 5 independent-human annotation table.

Does not overwrite raw GitHub exports or unlabeled extract CSVs.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from oba_revieweval.annotation.phase5_atoms import ATOMS
from oba_revieweval.annotation.schema import HUMAN_LABELS, SELF_LOGIN, in_reference_set
from oba_revieweval.dataset.actors import is_known_bot_login
from oba_revieweval.dataset.corpus import load_recommended

HUMAN_REVIEW_FIELDS = (
    "pr_number",
    "stratum",
    "reviewer",
    "comment_id",
    "source",
    "file",
    "line",
    "original_comment",
    "normalized_issue",
    "class",
    "atomic_issue_id",
    "in_reference_set",
    "annotation_status",
    "notes",
    "is_pr_author",
)

_NO_ISSUES = re.compile(
    r"no issues found\.?\s*checked for bugs and claude\.md compliance",
    re.IGNORECASE,
)
_CODERABBIT_PING = re.compile(r"^@coderabbit(ai)? review\.?$", re.IGNORECASE)
_CHECK_IN = re.compile(
    r"checking in on this (older pr|stack)",
    re.IGNORECASE,
)
_MAKE_TEST = re.compile(r"make sure u run `?make test`?", re.IGNORECASE)
_AARON_COMMENTS = re.compile(r"just needs aaron'?s comments addressed", re.IGNORECASE)
_CONFLICTS = re.compile(
    r"(looks like we have merge conflicts|just needs merge conflicts resolved|"
    r"please fix the items noted in the inline)",
    re.IGNORECASE,
)
_SAME_OPINION = re.compile(r"same opinion as @burma-shave", re.IGNORECASE)
_FINDINGS_POINTER = re.compile(r"^code review findings\.?$", re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_independent_comments(extracted_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(
        extracted_root.glob("*/human_independent_unlabeled.csv"),
        key=lambda item: int(item.parent.name),
    ):
        with path.open(encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def load_comment_lines(raw_root: Path) -> dict[tuple[int, int], str]:
    lines: dict[tuple[int, int], str] = {}
    for comments_path in raw_root.glob("*/comments.json"):
        pr_number = int(comments_path.parent.name)
        payload = json.loads(comments_path.read_text(encoding="utf-8"))
        for key in ("issue_comments", "inline_comments", "review_bodies"):
            for item in payload.get(key) or []:
                comment_id = item.get("id")
                line = item.get("line")
                if comment_id is None or line in (None, ""):
                    continue
                lines[(pr_number, int(comment_id))] = str(line)
    return lines


def is_auto_process(text: str, is_process_only: bool) -> bool:
    if is_process_only:
        return True
    body = (text or "").strip()
    if not body:
        return True
    compact = re.sub(r"\s+", " ", body)
    if _NO_ISSUES.search(compact):
        return True
    if _CODERABBIT_PING.match(compact):
        return True
    if _CHECK_IN.search(compact):
        return True
    if _MAKE_TEST.search(compact):
        return True
    if _AARON_COMMENTS.search(compact):
        return True
    if _CONFLICTS.search(compact):
        return True
    if _SAME_OPINION.search(compact):
        return True
    if _FINDINGS_POINTER.match(compact):
        return True
    return False


def _atom_map() -> dict[tuple[int, int], list[tuple[Any, ...]]]:
    grouped: dict[tuple[int, int], list[tuple[Any, ...]]] = defaultdict(list)
    for atom in ATOMS:
        grouped[(atom[0], atom[1])].append(atom)
    return grouped


def build_human_review_rows(
    *,
    recommended_path: Path | None = None,
    extracted_root: Path | None = None,
    raw_root: Path | None = None,
) -> list[dict[str, str]]:
    root = repo_root()
    recommended_path = recommended_path or root / "data" / "candidates" / "recommended_corpus.csv"
    extracted_root = extracted_root or root / "data" / "extracted" / "prs"
    raw_root = raw_root or root / "data" / "raw" / "prs"

    recommended = load_recommended(recommended_path)
    strata = {int(row["pr_number"]): row["stratum"] for row in recommended}
    comments = load_independent_comments(extracted_root)
    lines = load_comment_lines(raw_root)
    atoms = _atom_map()

    comment_keys = {(int(row["pr_id"]), int(row["comment_id"])) for row in comments}
    extra_atoms = sorted(set(atoms) - comment_keys)
    if extra_atoms:
        raise ValueError(f"atoms reference unknown independent comments: {extra_atoms}")

    out: list[dict[str, str]] = []
    covered: set[tuple[int, int]] = set()
    for row in comments:
        pr_number = int(row["pr_id"])
        comment_id = int(row["comment_id"])
        key = (pr_number, comment_id)
        reviewer = row["author_login"]
        is_pr_author = row["is_pr_author"] == "true"
        source = row["source"]
        path = row.get("path") or ""
        original = row.get("text") or ""
        line = lines.get(key, "")
        stratum = strata.get(pr_number, "")

        if key in atoms:
            for atom in atoms[key]:
                _pr, _cid, seq, klass, normalized, file, atom_line, status, notes, about = atom
                if klass not in HUMAN_LABELS:
                    raise ValueError(f"invalid class {klass} on {key}")
                if status not in {"resolved", "ambiguous"}:
                    raise ValueError(f"invalid annotation_status {status} on {key}")
                in_ref = in_reference_set(
                    klass,
                    reviewer,
                    is_pr_author=is_pr_author,
                    about_the_change=bool(about),
                )
                if status == "ambiguous":
                    in_ref = False
                out.append(
                    {
                        "pr_number": str(pr_number),
                        "stratum": stratum,
                        "reviewer": reviewer,
                        "comment_id": str(comment_id),
                        "source": source,
                        "file": file or path,
                        "line": atom_line or line,
                        "original_comment": original,
                        "normalized_issue": normalized,
                        "class": klass,
                        "atomic_issue_id": f"H-{pr_number}-{comment_id}-{seq}",
                        "in_reference_set": "true" if in_ref else "false",
                        "annotation_status": status,
                        "notes": notes,
                        "is_pr_author": "true" if is_pr_author else "false",
                    }
                )
            covered.add(key)
            continue

        if is_auto_process(original, row.get("is_process_only") == "true"):
            out.append(
                {
                    "pr_number": str(pr_number),
                    "stratum": stratum,
                    "reviewer": reviewer,
                    "comment_id": str(comment_id),
                    "source": source,
                    "file": path,
                    "line": line,
                    "original_comment": original,
                    "normalized_issue": "Process-only or complimentary review text; no independent defect/design issue.",
                    "class": "process_other",
                    "atomic_issue_id": f"H-{pr_number}-{comment_id}-1",
                    "in_reference_set": "false",
                    "annotation_status": "resolved",
                    "notes": "auto-classified process/other",
                    "is_pr_author": "true" if is_pr_author else "false",
                }
            )
            covered.add(key)
            continue

        raise ValueError(
            f"unlabeled independent comment PR={pr_number} comment_id={comment_id} "
            f"author={reviewer} source={source}"
        )

    missing = sorted(comment_keys - covered)
    if missing:
        raise ValueError(f"uncovered independent comments: {missing}")
    return out


def write_human_review_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HUMAN_REVIEW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_human_review_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def annotation_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    classes = Counter(row["class"] for row in rows)
    by_stratum_findings = Counter(row["stratum"] for row in rows)
    by_stratum_ref = Counter(row["stratum"] for row in rows if row["in_reference_set"] == "true")
    by_pr_findings = Counter(row["pr_number"] for row in rows)
    by_pr_comments = Counter()
    for key in {(row["pr_number"], row["comment_id"]) for row in rows}:
        by_pr_comments[key[0]] += 1
    reference = [row for row in rows if row["in_reference_set"] == "true"]
    ambiguous = [row for row in rows if row["annotation_status"] == "ambiguous"]
    return {
        "pr_count": len({row["pr_number"] for row in rows}),
        "independent_comment_count": len({(row["pr_number"], row["comment_id"]) for row in rows}),
        "atomic_finding_count": len(rows),
        "class_counts": dict(classes),
        "primary_reference_set_count": len(reference),
        "ambiguous_count": len(ambiguous),
        "findings_by_stratum": dict(by_stratum_findings),
        "reference_by_stratum": dict(by_stratum_ref),
        "comments_by_pr": dict(sorted(by_pr_comments.items(), key=lambda item: int(item[0]))),
        "findings_by_pr": dict(sorted(by_pr_findings.items(), key=lambda item: int(item[0]))),
        "reference_by_pr": dict(
            sorted(
                Counter(row["pr_number"] for row in reference).items(),
                key=lambda item: int(item[0]),
            )
        ),
        "ambiguous_ids": [row["atomic_issue_id"] for row in ambiguous],
    }


def validate_human_review(
    rows: list[dict[str, str]],
    *,
    recommended_path: Path | None = None,
    extracted_root: Path | None = None,
) -> list[str]:
    root = repo_root()
    recommended_path = recommended_path or root / "data" / "candidates" / "recommended_corpus.csv"
    extracted_root = extracted_root or root / "data" / "extracted" / "prs"
    errors: list[str] = []

    recommended = load_recommended(recommended_path)
    recommended_prs = {row["pr_number"] for row in recommended}
    comments = load_independent_comments(extracted_root)
    comment_index = {(row["pr_id"], row["comment_id"]): row for row in comments}

    if {row["pr_number"] for row in rows} != recommended_prs:
        errors.append("annotation table PR set does not match the recommended corpus")

    seen_ids: set[str] = set()
    covered: set[tuple[str, str]] = set()
    for row in rows:
        if row["class"] not in HUMAN_LABELS:
            errors.append(f"{row['atomic_issue_id']}: invalid class {row['class']}")
        if row["annotation_status"] not in {"resolved", "ambiguous"}:
            errors.append(f"{row['atomic_issue_id']}: invalid annotation_status")
        if row["atomic_issue_id"] in seen_ids:
            errors.append(f"duplicate atomic_issue_id {row['atomic_issue_id']}")
        seen_ids.add(row["atomic_issue_id"])
        covered.add((row["pr_number"], row["comment_id"]))

        extract = comment_index.get((row["pr_number"], row["comment_id"]))
        if extract is None:
            errors.append(f"{row['atomic_issue_id']}: comment not in independent extract")
            continue
        if extract["author_login"] != row["reviewer"]:
            errors.append(f"{row['atomic_issue_id']}: reviewer mismatch")
        if extract["text"] != row["original_comment"]:
            errors.append(f"{row['atomic_issue_id']}: original_comment rewritten")
        if extract["is_pr_author"] == "true":
            errors.append(f"{row['atomic_issue_id']}: PR-author comment in independent table")
        if extract["is_study_author"] == "true" or row["reviewer"].lower() == SELF_LOGIN.lower():
            errors.append(f"{row['atomic_issue_id']}: study-author comment included")
        if is_known_bot_login(row["reviewer"]):
            errors.append(f"{row['atomic_issue_id']}: bot comment included")
        if extract["actor_class"] != "human":
            errors.append(f"{row['atomic_issue_id']}: non-human actor")

        if row["in_reference_set"] == "true":
            if row["class"] not in {"defect", "design"}:
                errors.append(f"{row['atomic_issue_id']}: non-defect/design in reference set")
            if row["annotation_status"] == "ambiguous":
                errors.append(f"{row['atomic_issue_id']}: ambiguous finding forced into gold")
            if row["is_pr_author"] == "true":
                errors.append(f"{row['atomic_issue_id']}: PR author in reference set")
            if row["reviewer"].lower() == SELF_LOGIN.lower():
                errors.append(f"{row['atomic_issue_id']}: study author in reference set")
        if row["class"] == "process_other" and row["in_reference_set"] == "true":
            errors.append(f"{row['atomic_issue_id']}: process comment treated as gold")
        if row["annotation_status"] == "ambiguous":
            errors.append(f"{row['atomic_issue_id']}: unresolved ambiguous finding after freeze")

    extract_keys = {(row["pr_id"], row["comment_id"]) for row in comments}
    if extract_keys != covered:
        missing = sorted(extract_keys - covered)
        extra = sorted(covered - extract_keys)
        if missing:
            errors.append(f"missing independent comments: {missing[:20]}")
        if extra:
            errors.append(f"extra comment keys: {extra[:20]}")

    unlabeled = extracted_root.glob("*/human_independent_unlabeled.csv")
    for path in unlabeled:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("class"):
                    errors.append(f"{path}: extract class column was overwritten")
                    break

    return errors
