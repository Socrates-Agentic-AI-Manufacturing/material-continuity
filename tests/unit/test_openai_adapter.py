"""Offline transport/configuration checks; no real key or paid requests."""

from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from services.llm.openai import (
    ENDPOINT, MAX_RESPONSE_BYTES, ModelError, OpenAIResponsesClient,
    OpenAISettings, _NoRedirect, load_local_environment,
)
from tests.openai_fakes import SETTINGS, function_response


class Response(BytesIO):
    pass


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.requests = response, error, []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return Response(self.response)


class OpenAIAdapterTests(unittest.TestCase):
    def test_default_is_off_and_key_is_not_in_settings_repr_or_status(self):
        self.assertFalse(OpenAISettings.from_environment({}).status()["configured"])
        self.assertNotIn(SETTINGS.api_key, repr(SETTINGS))
        self.assertNotIn(SETTINGS.api_key, json.dumps(SETTINGS.status()))
        self.assertFalse(SETTINGS.status()["connection_verified"])

    def test_key_presence_alone_does_not_enable_paid_requests(self):
        settings = OpenAISettings.from_environment({"OPENAI_API_KEY": SETTINGS.api_key, "OPENAI_MODEL": "test-model"})
        opener = FakeOpener()
        with self.assertRaisesRegex(ModelError, "LLM_NOT_CONFIGURED"):
            OpenAIResponsesClient(settings, opener=opener).create(input_items=[], tools=[])
        self.assertEqual([], opener.requests)

    def test_model_is_required_and_config_limits_are_validated(self):
        self.assertFalse(OpenAISettings.from_environment({"MATERIAL_CONTINUITY_LLM_PROVIDER": "openai", "OPENAI_API_KEY": SETTINGS.api_key}).status()["configured"])
        for env in ({"MATERIAL_CONTINUITY_LLM_PROVIDER": "other"}, {"OPENAI_TIMEOUT_SECONDS": "nan"}, {"OPENAI_TIMEOUT_SECONDS": "31"}, {"OPENAI_MAX_OUTPUT_TOKENS": "99999"}, {"OPENAI_MODEL": "bad\nmodel"}):
            with self.subTest(env=env), self.assertRaisesRegex(ModelError, "INVALID_LLM_CONFIG"):
                OpenAISettings.from_environment(env)

    def test_local_env_loads_only_allowlisted_names_without_shell_expansion(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"OPENAI_MODEL": "existing"}, clear=True):
            root = Path(directory)
            (root / ".env.local").write_text('OPENAI_API_KEY="test-dummy"\nOPENAI_MODEL=ignored\nUNRELATED_SECRET=do-not-load\nOPENAI_TIMEOUT_SECONDS=15\n', encoding="utf-8")
            load_local_environment(root)
            self.assertEqual("test-dummy", os.environ["OPENAI_API_KEY"])
            self.assertEqual("existing", os.environ["OPENAI_MODEL"])
            self.assertNotIn("UNRELATED_SECRET", os.environ)

    def test_responses_wire_contract_and_server_only_bearer_header(self):
        opener = FakeOpener(json.dumps(function_response("getExposure")).encode())
        result = OpenAIResponsesClient(SETTINGS, opener=opener).create(input_items=[{"role": "user", "content": "case"}], tools=[], timeout=10)
        request, timeout = opener.requests[0]
        body = json.loads(request.data)
        self.assertEqual(ENDPOINT, request.full_url)
        self.assertEqual("POST", request.method)
        self.assertEqual("Bearer " + SETTINGS.api_key, request.get_header("Authorization"))
        self.assertNotIn(SETTINGS.api_key, request.data.decode())
        self.assertFalse(body["store"])
        self.assertFalse(body["parallel_tool_calls"])
        self.assertEqual("required", body["tool_choice"])
        self.assertEqual(["reasoning.encrypted_content"], body["include"])
        self.assertEqual(10, timeout)
        self.assertEqual("completed", result["status"])

    def test_upstream_errors_are_redacted_and_not_retried(self):
        for status, expected in ((401, "LLM_AUTH_FAILED"), (403, "LLM_ACCESS_DENIED"), (429, "LLM_RATE_OR_QUOTA_LIMIT"), (500, "LLM_PROVIDER_ERROR"), (302, "LLM_PROVIDER_ERROR")):
            with self.subTest(status=status):
                opener = FakeOpener(error=HTTPError(ENDPOINT, status, "sensitive-provider-message", {}, BytesIO(b"secret upstream body")))
                with self.assertRaises(ModelError) as error:
                    OpenAIResponsesClient(SETTINGS, opener=opener).create(input_items=[], tools=[])
                self.assertEqual(expected, str(error.exception))
                self.assertEqual(1, len(opener.requests))
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))

    def test_network_timeout_and_invalid_payloads_fail_closed(self):
        for upstream, expected in ((URLError("private message"), "LLM_NETWORK_ERROR"), (TimeoutError("private message"), "LLM_TIMEOUT")):
            with self.assertRaisesRegex(ModelError, expected):
                OpenAIResponsesClient(SETTINGS, opener=FakeOpener(error=upstream)).create(input_items=[], tools=[])
        for payload, expected in ((b"not-json", "LLM_INVALID_RESPONSE"), (b'{"status":"incomplete","output":[]}', "LLM_INCOMPLETE_RESPONSE"), (b"x" * (MAX_RESPONSE_BYTES + 1), "LLM_RESPONSE_LIMIT")):
            with self.assertRaisesRegex(ModelError, expected):
                OpenAIResponsesClient(SETTINGS, opener=FakeOpener(payload)).create(input_items=[], tools=[])
