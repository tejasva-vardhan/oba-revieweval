import subprocess
from pathlib import Path

import pytest

from oba_revieweval.dataset.git_anchor import (
    GitAnchorError,
    first_parent_paths,
    list_changed_files,
    merge_diff,
    paths_mentioned_in_diff,
    resolve_merge_commit,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "maglev"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "research@example.test")
    _git(repo, "config", "user.name", "research")
    (repo / "a.go").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "a.go")
    _git(repo, "commit", "-m", "base")
    return repo


def test_squash_commit_diff(tmp_path: Path):
    repo = _init_repo(tmp_path)
    (repo / "a.go").write_text("two\n", encoding="utf-8")
    (repo / "b.go").write_text("new\n", encoding="utf-8")
    _git(repo, "add", "a.go", "b.go")
    _git(repo, "commit", "-m", "change")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    merge = resolve_merge_commit(repo, sha)
    assert merge.diff_mode == "squash_first_parent"
    files = {item.filename: item for item in list_changed_files(repo, merge)}
    assert set(files) == {"a.go", "b.go"}
    assert files["b.go"].status == "added"
    assert files["a.go"].status == "modified"
    diff = merge_diff(repo, merge)
    assert "a.go" in paths_mentioned_in_diff(diff)
    assert "b.go" in paths_mentioned_in_diff(diff)


def test_rename_and_delete(tmp_path: Path):
    repo = _init_repo(tmp_path)
    _git(repo, "mv", "a.go", "renamed.go")
    (repo / "gone.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "gone.txt")
    _git(repo, "commit", "-m", "add gone")
    _git(repo, "rm", "gone.txt")
    _git(repo, "commit", "-m", "delete and keep rename")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    merge = resolve_merge_commit(repo, sha)
    # First-parent of this commit is only the delete.
    files = list_changed_files(repo, merge)
    names = {item.filename: item for item in files}
    assert "gone.txt" in names
    assert names["gone.txt"].status == "removed"
    diff = merge_diff(repo, merge)
    assert "gone.txt" in paths_mentioned_in_diff(diff)


def test_binary_file_is_flagged(tmp_path: Path):
    repo = _init_repo(tmp_path)
    (repo / "blob.bin").write_bytes(bytes(range(256)))
    _git(repo, "add", "blob.bin")
    _git(repo, "commit", "-m", "binary")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    merge = resolve_merge_commit(repo, sha)
    files = {item.filename: item for item in list_changed_files(repo, merge)}
    assert files["blob.bin"].binary is True
    diff = merge_diff(repo, merge)
    assert "blob.bin" in diff


def test_missing_sha_raises(tmp_path: Path):
    repo = _init_repo(tmp_path)
    with pytest.raises(GitAnchorError):
        resolve_merge_commit(repo, "deadbeef" * 5)


def test_two_parent_merge_uses_three_dot_when_first_parent_empty(tmp_path: Path):
    repo = _init_repo(tmp_path)
    default_branch = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
    ).strip()
    _git(repo, "checkout", "-b", "feature")
    (repo / "a.go").write_text("locked\n", encoding="utf-8")
    _git(repo, "add", "a.go")
    _git(repo, "commit", "-m", "feature lock")
    _git(repo, "checkout", default_branch)
    # Same tree change already landed on main, so the merge is a no-op.
    (repo / "a.go").write_text("locked\n", encoding="utf-8")
    _git(repo, "add", "a.go")
    _git(repo, "commit", "-m", "already on main")
    _git(repo, "merge", "--no-ff", "-m", "merge feature", "feature")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    merge = resolve_merge_commit(repo, sha)
    assert merge.diff_mode == "merge_parents_three_dot"
    assert first_parent_paths(repo, merge) == []
    files = {item.filename: item for item in list_changed_files(repo, merge)}
    assert "a.go" in files
    diff = merge_diff(repo, merge)
    assert "a.go" in paths_mentioned_in_diff(diff)
