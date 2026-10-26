"""SAP AI Core Generative AI Hub chat-completions adapter.

Credentials are read from the process environment or the ignored .env.local
file. The adapter deliberately exposes the same small ``create`` contract as
the OpenAI client so the review workflow does not depend on a provider.
"""

from dataclasses import dataclass, field
import json
import math
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .openai import ModelError, MAX_RESPONSE_BYTES, _NoRedirect


@dataclass(frozen=True, slots=True)
class SAPAICoreSettings:
    provider: str = "sap_ai_core"
    client_id: str = field(default="", repr=False)
    client_secret: str = field(default="", repr=False)
    token_url: str = ""
    api_url: str = ""
    deployment_id: str = ""
    resource_group: str = "default"
    timeout_seconds: float = 20
    max_output_tokens: int = 2048

    @property
    def model(self):
        """Provider-neutral model label used by the review audit record."""
        return self.deployment_id or None

    @classmethod
    def from_environment(cls, environ=None):
        env = os.environ if environ is None else environ
        try:
            settings = cls(
                client_id=env.get("SAP_AI_CORE_CLIENT_ID", "").strip(),
                client_secret=env.get("SAP_AI_CORE_CLIENT_SECRET", "").strip(),
                token_url=env.get("SAP_AI_CORE_TOKEN_URL", "").strip().rstrip("/"),
                api_url=env.get("SAP_AI_CORE_API_URL", "").strip().rstrip("/"),
                deployment_id=env.get("SAP_AI_CORE_DEPLOYMENT_ID", "").strip(),
                resource_group=env.get("SAP_AI_CORE_RESOURCE_GROUP", "default").strip() or "default",
                timeout_seconds=float(env.get("SAP_AI_CORE_TIMEOUT_SECONDS", "20")),
                max_output_tokens=int(env.get("SAP_AI_CORE_MAX_OUTPUT_TOKENS", "2048")),
            )
        except (ValueError, TypeError):
            raise ModelError("INVALID_LLM_CONFIG") from None
        if (
            not math.isfinite(settings.timeout_seconds)
            or not 1 <= settings.timeout_seconds <= 30
            or not 256 <= settings.max_output_tokens <= 4096
            or not settings.resource_group
            or not settings.deployment_id
        ):
            raise ModelError("INVALID_LLM_CONFIG")
        return settings

    def status(self):
        required = {
            "SAP_AI_CORE_CLIENT_ID": self.client_id,
            "SAP_AI_CORE_CLIENT_SECRET": self.client_secret,
            "SAP_AI_CORE_TOKEN_URL": self.token_url,
            "SAP_AI_CORE_API_URL": self.api_url,
            "SAP_AI_CORE_DEPLOYMENT_ID": self.deployment_id,
        }
        return {
            "provider": self.provider,
            "configured": all(required.values()),
            "model": self.deployment_id or None,
            "missing": [name for name, value in required.items() if not value],
            "connection_verified": False,
            "automatic_requests": False,
        }

    def require_configured(self):
        if not self.status()["configured"]:
            raise ModelError("LLM_NOT_CONFIGURED")


class SAPAICoreClient:
    def __init__(self, settings: SAPAICoreSettings, *, opener=None):
        self.settings = settings
        self._opener = opener or build_opener(_NoRedirect())

    def _token(self, timeout):
        body = urlencode({"grant_type": "client_credentials"}).encode("ascii")
        request = Request(
            self.settings.token_url + "/oauth/token",
            data=body,
            method="POST",
            headers={
                "Authorization": "Basic " + _basic(self.settings.client_id, self.settings.client_secret),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with self._opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, OSError, TimeoutError, socket.timeout):
            raise ModelError("LLM_AUTH_FAILED") from None
        try:
            token = json.loads(raw).get("access_token")
        except (ValueError, UnicodeError, AttributeError):
            token = None
        if not isinstance(token, str) or not token:
            raise ModelError("LLM_AUTH_FAILED")
        return token

    def create(self, *, input_items, tools, timeout=None):
        self.settings.require_configured()
        limit = min(timeout or self.settings.timeout_seconds, self.settings.timeout_seconds)
        token = self._token(limit)
        payload = {
            "messages": _chat_messages(input_items),
            "tools": [_chat_tool(tool) for tool in tools],
            "tool_choice": "required",
            "parallel_tool_calls": False,
            "max_completion_tokens": self.settings.max_output_tokens,
        }
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        endpoint = (
            f"{self.settings.api_url}/v2/inference/deployments/"
            f"{self.settings.deployment_id}/chat/completions?api-version=2024-12-01-preview"
        )
        request = Request(endpoint, data=body, method="POST", headers={
            "Authorization": "Bearer " + token,
            "AI-Resource-Group": self.settings.resource_group,
            "Content-Type": "application/json",
        })
        try:
            with self._opener.open(request, timeout=limit) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            code = {401: "LLM_AUTH_FAILED", 403: "LLM_ACCESS_DENIED", 429: "LLM_RATE_OR_QUOTA_LIMIT"}.get(error.code, "LLM_PROVIDER_ERROR")
            error.close()
            raise ModelError(code) from None
        except (URLError, OSError, TimeoutError, socket.timeout):
            raise ModelError("LLM_NETWORK_ERROR") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ModelError("LLM_RESPONSE_LIMIT")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ModelError("LLM_INVALID_RESPONSE") from None
        if not isinstance(result, dict) or not isinstance(result.get("choices"), list):
            raise ModelError("LLM_INCOMPLETE_RESPONSE")
        return _responses_shape(result)


def _basic(client_id: str, client_secret: str) -> str:
    import base64
    return base64.b64encode(f"{client_id}:{client_secret}".encode()).decode("ascii")


def _chat_tool(tool):
    return {"type": "function", "function": {
        "name": tool["name"],
        "description": tool.get("description", ""),
        "parameters": tool["parameters"],
    }}


def _chat_messages(items):
    messages = []
    for item in items:
        if item.get("role") in {"system", "user"}:
            messages.append(item)
        elif item.get("type") == "function_call":
            messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": item["call_id"],
                    "type": "function",
                    "function": {"name": item["name"], "arguments": item["arguments"]},
                }],
            })
        elif item.get("type") == "function_call_output":
            messages.append({
                "role": "tool",
                "tool_call_id": item["call_id"],
                "content": item["output"],
            })
    return messages


def _responses_shape(result):
    choice = result["choices"][0] if result["choices"] else {}
    message = choice.get("message") if isinstance(choice, dict) else None
    if not isinstance(message, dict):
        raise ModelError("LLM_INVALID_RESPONSE")
    calls = message.get("tool_calls") or []
    output = []
    for call in calls:
        function = call.get("function") or {}
        if not call.get("id") or not function.get("name") or not isinstance(function.get("arguments"), str):
            raise ModelError("LLM_INVALID_TOOL_CALL")
        output.append({
            "type": "function_call",
            "call_id": call["id"],
            "name": function["name"],
            "arguments": function["arguments"],
        })
    usage = result.get("usage") or {}
    return {
        "status": "completed",
        "output": output,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }
