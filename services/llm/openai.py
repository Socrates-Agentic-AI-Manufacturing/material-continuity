"""Small server-only Responses API adapter using the existing stdlib stack.

No request is made during configuration/startup. No provider errors, headers,
request bodies or credentials are logged or returned to the browser.
"""

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ENV_NAMES = (
    "MATERIAL_CONTINUITY_LLM_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL",
    "OPENAI_TIMEOUT_SECONDS", "OPENAI_MAX_OUTPUT_TOKENS",
)
ENDPOINT = "https://api.openai.com/v1/responses"
MAX_RESPONSE_BYTES = 1_048_576


class ModelError(Exception):
    """Safe, application-owned failure code; never contains upstream text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def load_local_environment(root: Path) -> None:
    """Read an optional ignored .env.local; process environment takes priority.

    Deliberately not a shell/dotenv interpreter: no interpolation, commands,
    exports or multiline values. Only this integration's allowlisted names load.
    """
    path = root / ".env.local"
    if not path.is_file():
        return
    if path.is_symlink() or path.stat().st_size > 16_384:
        raise ModelError("INVALID_LLM_CONFIG")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        name, sep, value = line.strip().partition("=")
        if not sep or name.strip() not in ENV_NAMES:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(name.strip(), value)


@dataclass(frozen=True, slots=True)
class OpenAISettings:
    provider: str = "fixtures"
    api_key: str = field(default="", repr=False)
    model: str = ""
    timeout_seconds: float = 20
    max_output_tokens: int = 2048

    @classmethod
    def from_environment(cls, environ=None):
        env = os.environ if environ is None else environ
        try:
            settings = cls(
                provider=env.get("MATERIAL_CONTINUITY_LLM_PROVIDER", "fixtures").strip(),
                api_key=env.get("OPENAI_API_KEY", "").strip(),
                model=env.get("OPENAI_MODEL", "").strip(),
                timeout_seconds=float(env.get("OPENAI_TIMEOUT_SECONDS", "20")),
                max_output_tokens=int(env.get("OPENAI_MAX_OUTPUT_TOKENS", "2048")),
            )
        except (ValueError, TypeError):
            raise ModelError("INVALID_LLM_CONFIG") from None
        if (
            settings.provider not in ("fixtures", "openai")
            or not math.isfinite(settings.timeout_seconds)
            or not 1 <= settings.timeout_seconds <= 30
            or not 256 <= settings.max_output_tokens <= 4096
            or len(settings.model) > 120
            or (settings.model and not re.fullmatch(r"[A-Za-z0-9._:-]+", settings.model))
        ):
            raise ModelError("INVALID_LLM_CONFIG")
        return settings

    def status(self):
        return {
            "provider": self.provider,
            "configured": self.provider == "openai" and bool(self.api_key and self.model),
            "model": self.model or None,
            "missing": [name for name, value in (("OPENAI_API_KEY", self.api_key), ("OPENAI_MODEL", self.model)) if not value],
            "connection_verified": False,
            "automatic_requests": False,
        }

    def require_configured(self):
        if not self.status()["configured"]:
            raise ModelError("LLM_NOT_CONFIGURED")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the Authorization header to another origin.
        return None


class OpenAIResponsesClient:
    def __init__(self, settings: OpenAISettings, *, opener=None):
        self.settings = settings
        self._opener = opener or build_opener(_NoRedirect())

    def create(self, *, input_items, tools, timeout=None):
        self.settings.require_configured()
        payload = {
            "model": self.settings.model,
            "input": input_items,
            "tools": tools,
            "tool_choice": "required",
            "parallel_tool_calls": False,
            "store": False,
            "include": ["reasoning.encrypted_content"],
            "max_output_tokens": self.settings.max_output_tokens,
        }
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        if len(body) > 196_608:
            raise ModelError("LLM_CONTEXT_LIMIT")
        request = Request(ENDPOINT, data=body, method="POST", headers={
            "Authorization": "Bearer " + self.settings.api_key,
            "Content-Type": "application/json",
        })
        try:
            with self._opener.open(request, timeout=min(timeout or self.settings.timeout_seconds, self.settings.timeout_seconds)) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            code = {401: "LLM_AUTH_FAILED", 403: "LLM_ACCESS_DENIED", 429: "LLM_RATE_OR_QUOTA_LIMIT"}.get(error.code, "LLM_PROVIDER_ERROR")
            error.close()
            raise ModelError(code) from None
        except (TimeoutError, socket.timeout):
            raise ModelError("LLM_TIMEOUT") from None
        except (URLError, OSError):
            raise ModelError("LLM_NETWORK_ERROR") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ModelError("LLM_RESPONSE_LIMIT")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ModelError("LLM_INVALID_RESPONSE") from None
        if not isinstance(result, dict) or result.get("status") != "completed" or not isinstance(result.get("output"), list):
            raise ModelError("LLM_INCOMPLETE_RESPONSE")
        return result
