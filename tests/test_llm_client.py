import io
import json
import urllib.error
from pathlib import Path

import pytest

from oba_revieweval.models.artifacts import SecretLeakError, artifact_has_secret, write_json, write_text
from oba_revieweval.models.client import OpenAIChatClient, TransportError
from oba_revieweval.models.secrets import MissingAPIKey, load_openai_api_key, redact_secret


class _FakeHTTPError(urllib.error.HTTPError):
    def __init__(self, code: int, body: bytes = b"{}"):
        super().__init__(
            url="https://api.openai.com/v1/chat/completions",
            code=code,
            msg="err",
            hdrs=None,
            fp=io.BytesIO(body),
        )


class _SeqOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.headers_seen = []

    def open(self, req, timeout=None):
        self.calls += 1
        self.headers_seen.append(dict(req.headers))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        status, payload = item

        class _Resp:
            def __init__(self):
                self.status = status
                self.headers = {"x-request-id": "req-1"}

            def read(self):
                return json.dumps(payload).encode("utf-8")

            def getcode(self):
                return status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return _Resp()


def _ok_payload(text: str) -> dict:
    return {
        "model": "gpt-4o-2024-11-20",
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _client(opener, retries=1) -> OpenAIChatClient:
    return OpenAIChatClient(
        "sk-secret-test-key",
        endpoint="https://api.openai.com/v1/chat/completions",
        model="gpt-4o-2024-11-20",
        temperature=0,
        max_tokens=128,
        timeout_seconds=5,
        transport_retries=retries,
        opener=opener,
        sleeper=lambda _s: None,
    )


def test_successful_completion_parses_usage():
    opener = _SeqOpener([(200, _ok_payload('{"findings":[]}'))])
    result = _client(opener).complete([{"role": "user", "content": "hi"}])
    assert result.text == '{"findings":[]}'
    assert result.prompt_tokens == 10
    assert result.retried is False
    assert result.attempts == 1
    assert "sk-secret-test-key" not in json.dumps(result.raw)


def test_transport_error_retries_once():
    opener = _SeqOpener(
        [
            TransportError("HTTP 429"),
            (200, _ok_payload('{"findings":[]}')),
        ]
    )
    # URLError path: raise HTTP 429 via HTTPError
    opener.responses[0] = _FakeHTTPError(429, b'{"error":"rate"}')
    result = _client(opener).complete([{"role": "user", "content": "hi"}])
    assert opener.calls == 2
    assert result.retried is True
    assert result.text == '{"findings":[]}'


def test_non_retryable_api_error_does_not_retry():
    opener = _SeqOpener([_FakeHTTPError(400, b'{"error":"bad"}')])
    result = _client(opener).complete([{"role": "user", "content": "hi"}])
    assert opener.calls == 1
    assert result.error
    assert result.text == ""
    assert "sk-secret-test-key" not in result.error


def test_missing_key_raises():
    with pytest.raises(MissingAPIKey):
        load_openai_api_key(env={}, dotenv_path=Path("does-not-exist.env"))


def test_artifacts_never_store_the_key(tmp_path: Path):
    secret = "sk-secret-test-key"
    write_json(tmp_path / "run.json", {"auth": f"Bearer {secret}"}, secret)
    write_text(tmp_path / "raw.txt", f"token={secret}", secret)
    assert "***REDACTED***" in (tmp_path / "run.json").read_text(encoding="utf-8")
    assert secret not in (tmp_path / "run.json").read_text(encoding="utf-8")
    assert artifact_has_secret(tmp_path, secret) == []


def test_write_refuses_if_redaction_fails(tmp_path: Path, monkeypatch):
    from oba_revieweval.models import artifacts

    monkeypatch.setattr(artifacts, "redact_obj", lambda value, secret: value)
    with pytest.raises(SecretLeakError):
        write_json(tmp_path / "bad.json", {"k": "sk-secret-test-key"}, "sk-secret-test-key")


def test_redact_secret():
    assert redact_secret("Bearer sk-abc", "sk-abc") == "Bearer ***REDACTED***"
