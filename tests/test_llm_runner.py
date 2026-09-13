from pathlib import Path

from oba_revieweval.models.client import CompletionResult
from oba_revieweval.models.constants import PILOT_PRS
from oba_revieweval.models.runner import analyze_pr, estimate_cost_usd


class _FakeClient:
    def __init__(self, result: CompletionResult):
        self.result = result
        self.messages = None

    def complete(self, messages):
        self.messages = messages
        return self.result


def test_pilot_prs_are_the_documented_three():
    assert PILOT_PRS == (1404, 702, 1428)


def test_analyze_pr_preserves_raw_and_parses(tmp_path: Path, monkeypatch):
    from oba_revieweval.models import runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "build_review_context",
        lambda **kwargs: {
            "pr_number": 1428,
            "title": "fix block",
            "commit_sha": "sha",
            "diff": "diff",
            "changed_files": ["internal/restapi/block_handler.go"],
            "excerpts": [],
            "user_message": "1. PR title\nfix block\n",
            "user_message_chars": 20,
            "surrounding_lines_per_file": 200,
        },
    )
    raw = '{"findings":[{"title":"x","severity":"low","category":"concurrency","path":"internal/restapi/block_handler.go","line":3,"rationale":"why","recommendation":"fix"}]}'
    client = _FakeClient(
        CompletionResult(
            text=raw,
            raw={"choices": [{"message": {"content": raw}}], "model": "gpt-4o-2024-11-20"},
            model="gpt-4o-2024-11-20",
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            retried=False,
            attempts=1,
            status_code=200,
        )
    )
    dest = tmp_path / "1428"
    result = analyze_pr(
        pr_number=1428,
        merge_sha="sha",
        client=client,
        config={
            "tool": "llm_a",
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4o-2024-11-20",
            "temperature": 0,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
            "surrounding_lines_per_file": 200,
            "input_usd_per_million": 2.5,
            "output_usd_per_million": 10.0,
        },
        secret="sk-secret-test-key",
        dest_dir=dest,
        raw_pr_dir=tmp_path / "missing",
        system_prompt="frozen prompt",
        prompt_digest="sha256:abc",
    )
    assert result["run"]["execution_status"] == "ok"
    assert result["run"]["parse_status"] == "ok"
    assert result["findings"][0]["path_in_changed_files"] == "true"
    assert (dest / "raw.txt").read_text(encoding="utf-8") == raw
    assert (dest / "raw_response.json").exists()
    assert (dest / "request.json").exists()
    assert (dest / "findings.json").exists()
    assert "sk-secret-test-key" not in (dest / "request.json").read_text(encoding="utf-8")
    assert client.messages[0]["content"] == "frozen prompt"
    assert "human review" not in client.messages[1]["content"].lower()


def test_malformed_response_is_recorded_not_rewritten(tmp_path: Path, monkeypatch):
    from oba_revieweval.models import runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "build_review_context",
        lambda **kwargs: {
            "pr_number": 702,
            "title": "t",
            "commit_sha": "sha",
            "diff": "diff",
            "changed_files": ["gtfsdb/helpers.go"],
            "excerpts": [],
            "user_message": "title",
            "user_message_chars": 5,
            "surrounding_lines_per_file": 200,
        },
    )
    client = _FakeClient(
        CompletionResult(
            text="not json",
            raw={"choices": [{"message": {"content": "not json"}}]},
            model="gpt-4o-2024-11-20",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            retried=False,
            attempts=1,
            status_code=200,
        )
    )
    dest = tmp_path / "702"
    result = analyze_pr(
        pr_number=702,
        merge_sha="sha",
        client=client,
        config={
            "tool": "llm_a",
            "endpoint": "https://example.test",
            "model": "gpt-4o-2024-11-20",
            "temperature": 0,
            "max_tokens": 16,
            "input_usd_per_million": 0,
            "output_usd_per_million": 0,
        },
        secret="sk-secret-test-key",
        dest_dir=dest,
        raw_pr_dir=tmp_path,
        system_prompt="p",
        prompt_digest="sha256:x",
    )
    assert result["run"]["execution_status"] == "parse_error"
    assert result["findings"] == []
    assert (dest / "raw.txt").read_text(encoding="utf-8") == "not json"
    assert (dest / "parse_error.txt").exists()


def test_api_failure_is_recorded(tmp_path: Path, monkeypatch):
    from oba_revieweval.models import runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "build_review_context",
        lambda **kwargs: {
            "pr_number": 1404,
            "title": "t",
            "commit_sha": "sha",
            "diff": "diff",
            "changed_files": [],
            "excerpts": [],
            "user_message": "title",
            "user_message_chars": 5,
            "surrounding_lines_per_file": 200,
        },
    )
    client = _FakeClient(
        CompletionResult(
            text="",
            raw={},
            model="gpt-4o-2024-11-20",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            retried=True,
            attempts=2,
            status_code=0,
            error="HTTP 429",
        )
    )
    result = analyze_pr(
        pr_number=1404,
        merge_sha="sha",
        client=client,
        config={
            "tool": "llm_a",
            "endpoint": "https://example.test",
            "model": "gpt-4o-2024-11-20",
            "temperature": 0,
            "max_tokens": 16,
            "input_usd_per_million": 0,
            "output_usd_per_million": 0,
        },
        secret="sk-secret-test-key",
        dest_dir=tmp_path / "1404",
        raw_pr_dir=tmp_path,
        system_prompt="p",
        prompt_digest="sha256:x",
    )
    assert result["run"]["execution_status"] == "failed"
    assert result["run"]["parse_status"] == "api_error"
    assert result["run"]["retried"] is True


def test_unknown_file_is_kept_and_flagged(tmp_path: Path, monkeypatch):
    from oba_revieweval.models import runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "build_review_context",
        lambda **kwargs: {
            "pr_number": 1,
            "title": "t",
            "commit_sha": "sha",
            "diff": "diff",
            "changed_files": ["real.go"],
            "excerpts": [],
            "user_message": "title",
            "user_message_chars": 5,
            "surrounding_lines_per_file": 200,
        },
    )
    raw = '{"findings":[{"title":"x","path":"missing.go","line":1,"rationale":"why"}]}'
    client = _FakeClient(
        CompletionResult(
            text=raw,
            raw={},
            model="m",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            retried=False,
            attempts=1,
            status_code=200,
        )
    )
    result = analyze_pr(
        pr_number=1,
        merge_sha="sha",
        client=client,
        config={
            "tool": "llm_a",
            "endpoint": "e",
            "model": "m",
            "temperature": 0,
            "max_tokens": 8,
            "input_usd_per_million": 0,
            "output_usd_per_million": 0,
        },
        secret="sk-secret-test-key",
        dest_dir=tmp_path / "1",
        raw_pr_dir=tmp_path,
        system_prompt="p",
        prompt_digest="sha256:x",
    )
    assert result["findings"][0]["file"] == "missing.go"
    assert result["findings"][0]["path_in_changed_files"] == "false"


def test_cost_estimate():
    assert estimate_cost_usd(1_000_000, 1_000_000, input_usd_per_million=2.5, output_usd_per_million=10) == 12.5
