"""OpenAI Chat Completions client. Does not log the API key."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from oba_revieweval.models.secrets import redact_secret

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class TransportError(RuntimeError):
    """Retryable network or HTTP failure."""


class APIError(RuntimeError):
    """Non-retryable API failure."""


@dataclass
class CompletionResult:
    text: str
    raw: dict[str, Any]
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    retried: bool
    attempts: int
    status_code: int
    error: str = ""
    request_id: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout: int,
    opener: Any | None,
) -> tuple[int, dict[str, Any], str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        if opener is not None:
            handle = opener.open(req, timeout=timeout)
        else:
            handle = urllib.request.urlopen(req, timeout=timeout)
        with handle:
            raw = handle.read()
            status = getattr(handle, "status", None) or handle.getcode()
            request_id = ""
            try:
                request_id = handle.headers.get("x-request-id") or ""
            except Exception:
                request_id = ""
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        text = raw.decode("utf-8", errors="replace")
        if exc.code in RETRYABLE_STATUS:
            raise TransportError(f"HTTP {exc.code}") from exc
        raise APIError(f"HTTP {exc.code}: {text[:300]}") from exc
    except urllib.error.URLError as exc:
        raise TransportError(f"network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise TransportError("timeout") from exc
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as exc:
        raise APIError("non-JSON API body") from exc
    return int(status), parsed, request_id


class OpenAIChatClient:
    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
        response_format: dict[str, Any] | None = None,
        transport_retries: int = 1,
        opener: Any | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.response_format = response_format
        self.transport_retries = transport_retries
        self._opener = opener
        self._sleep = sleeper or time.sleep

    def complete(self, messages: list[dict[str, str]]) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if self.response_format:
            payload["response_format"] = self.response_format
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "oba-revieweval-phase6b",
        }
        max_attempts = 1 + max(self.transport_retries, 0)
        attempts = 0
        last_error = ""
        while attempts < max_attempts:
            attempts += 1
            try:
                status, raw, request_id = _post_json(
                    self.endpoint,
                    payload,
                    headers,
                    timeout=self.timeout_seconds,
                    opener=self._opener,
                )
                text = _message_text(raw)
                usage = raw.get("usage") or {}
                return CompletionResult(
                    text=text,
                    raw=raw,
                    model=str(raw.get("model") or self.model),
                    prompt_tokens=int(usage.get("prompt_tokens") or 0),
                    completion_tokens=int(usage.get("completion_tokens") or 0),
                    total_tokens=int(usage.get("total_tokens") or 0),
                    retried=attempts > 1,
                    attempts=attempts,
                    status_code=status,
                    request_id=request_id,
                )
            except TransportError as exc:
                last_error = str(exc)
                if attempts < max_attempts:
                    self._sleep(1.0)
                    continue
                return CompletionResult(
                    text="",
                    raw={},
                    model=self.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    retried=attempts > 1,
                    attempts=attempts,
                    status_code=0,
                    error=last_error,
                )
            except APIError as exc:
                return CompletionResult(
                    text="",
                    raw={},
                    model=self.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    retried=attempts > 1,
                    attempts=attempts,
                    status_code=0,
                    error=redact_secret(str(exc), self._api_key),
                )
        return CompletionResult(
            text="",
            raw={},
            model=self.model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            retried=attempts > 1,
            attempts=attempts,
            status_code=0,
            error=last_error or "exhausted retries",
        )


def _message_text(raw: dict[str, Any]) -> str:
    choices = raw.get("choices") or []
    if not choices or not isinstance(choices, list):
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    return ""
