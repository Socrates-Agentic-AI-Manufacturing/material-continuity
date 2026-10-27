"""Offline SAP AI Core adapter tests; no credentials or network calls."""

from io import BytesIO
import json
import unittest
from urllib.error import HTTPError, URLError

from services.llm.openai import MAX_RESPONSE_BYTES, ModelError
from services.llm.sap_ai_core import SAPAICoreClient, SAPAICoreSettings


SETTINGS = SAPAICoreSettings(
    client_id="test-client",
    client_secret="test-secret",
    token_url="https://auth.example.invalid",
    api_url="https://api.example.invalid",
    deployment_id="deployment-123",
    resource_group="demo",
)


class Response(BytesIO):
    pass


class SequencedOpener:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome)


def token_response():
    return json.dumps({"access_token": "fake-access-token"}).encode()


def completion_response():
    return json.dumps({
        "choices": [{"message": {"tool_calls": [{
            "id": "call-1",
            "type": "function",
            "function": {"name": "getExposure", "arguments": "{}"},
        }]}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4},
    }).encode()


class SAPAICoreAdapterTests(unittest.TestCase):
    def test_default_is_off_and_secret_is_never_exposed(self):
        status = SAPAICoreSettings.from_environment({}).status()
        self.assertFalse(status["configured"])
        self.assertNotIn(SETTINGS.client_secret, repr(SETTINGS))
        self.assertNotIn(SETTINGS.client_secret, json.dumps(SETTINGS.status()))

    def test_token_and_chat_completion_wire_contract(self):
        opener = SequencedOpener(token_response(), completion_response())
        result = SAPAICoreClient(SETTINGS, opener=opener).create(
            input_items=[{"role": "user", "content": "review case"}],
            tools=[{"name": "getExposure", "description": "facts", "parameters": {"type": "object"}}],
            timeout=10,
        )

        token_request, token_timeout = opener.requests[0]
        inference_request, inference_timeout = opener.requests[1]
        self.assertEqual("https://auth.example.invalid/oauth/token", token_request.full_url)
        self.assertTrue(token_request.get_header("Authorization").startswith("Basic "))
        self.assertNotIn(SETTINGS.client_secret, token_request.data.decode())
        self.assertIn("/v2/inference/deployments/deployment-123/chat/completions", inference_request.full_url)
        self.assertEqual("Bearer fake-access-token", inference_request.get_header("Authorization"))
        self.assertEqual("demo", inference_request.get_header("Ai-resource-group"))
        payload = json.loads(inference_request.data)
        self.assertEqual("required", payload["tool_choice"])
        self.assertFalse(payload["parallel_tool_calls"])
        self.assertEqual(10, token_timeout)
        self.assertEqual(10, inference_timeout)
        self.assertEqual("getExposure", result["output"][0]["name"])
        self.assertEqual({"input_tokens": 12, "output_tokens": 4}, result["usage"])

    def test_token_and_provider_errors_fail_closed_without_retry(self):
        token_error = HTTPError(SETTINGS.token_url, 401, "secret", {}, BytesIO(b"private"))
        opener = SequencedOpener(token_error)
        with self.assertRaisesRegex(ModelError, "LLM_AUTH_FAILED"):
            SAPAICoreClient(SETTINGS, opener=opener).create(input_items=[], tools=[])
        self.assertEqual(1, len(opener.requests))

        for status, expected in ((401, "LLM_AUTH_FAILED"), (403, "LLM_ACCESS_DENIED"), (429, "LLM_RATE_OR_QUOTA_LIMIT"), (500, "LLM_PROVIDER_ERROR")):
            with self.subTest(status=status):
                provider_error = HTTPError(SETTINGS.api_url, status, "secret", {}, BytesIO(b"private"))
                opener = SequencedOpener(token_response(), provider_error)
                with self.assertRaisesRegex(ModelError, expected):
                    SAPAICoreClient(SETTINGS, opener=opener).create(input_items=[], tools=[])
                self.assertEqual(2, len(opener.requests))

    def test_network_timeout_and_invalid_payloads_fail_closed(self):
        for outcomes, expected in (
            ((TimeoutError("private"),), "LLM_TIMEOUT"),
            ((URLError("private"),), "LLM_NETWORK_ERROR"),
            ((token_response(), TimeoutError("private")), "LLM_TIMEOUT"),
            ((token_response(), URLError("private")), "LLM_NETWORK_ERROR"),
            ((b"x" * (MAX_RESPONSE_BYTES + 1),), "LLM_RESPONSE_LIMIT"),
            ((token_response(), b"not-json"), "LLM_INVALID_RESPONSE"),
            ((token_response(), b'{}'), "LLM_INCOMPLETE_RESPONSE"),
        ):
            with self.subTest(expected=expected), self.assertRaisesRegex(ModelError, expected):
                SAPAICoreClient(SETTINGS, opener=SequencedOpener(*outcomes)).create(input_items=[], tools=[])

    def test_invalid_limits_are_rejected_before_transport(self):
        for env in (
            {"SAP_AI_CORE_TIMEOUT_SECONDS": "nan"},
            {"SAP_AI_CORE_TIMEOUT_SECONDS": "31"},
            {"SAP_AI_CORE_MAX_OUTPUT_TOKENS": "9000"},
        ):
            with self.subTest(env=env), self.assertRaisesRegex(ModelError, "INVALID_LLM_CONFIG"):
                SAPAICoreSettings.from_environment(env)


if __name__ == "__main__":
    unittest.main()
