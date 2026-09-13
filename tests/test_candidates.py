from pathlib import Path

CANDIDATE_CSV = Path(__file__).resolve().parents[1] / "data" / "candidates" / "pr_candidates.csv"


def test_candidate_list_has_thirty_unique_prs():
    rows = CANDIDATE_CSV.read_text(encoding="utf-8").strip().splitlines()[1:]
    pr_ids = [int(line.split(",", 1)[0]) for line in rows if line.strip()]
    assert len(pr_ids) == 30
    assert len(set(pr_ids)) == 30


def test_author_prs_are_only_those_with_independent_humans():
    rows = CANDIDATE_CSV.read_text(encoding="utf-8").strip().splitlines()[1:]
    author_prs = {
        int(line.split(",", 1)[0])
        for line in rows
        if ",tejasva-vardhan," in line
    }
    assert author_prs == {507, 702}
