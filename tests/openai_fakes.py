"""Non-network test doubles. Never load developer credentials."""

from copy import deepcopy
import json

from services.llm.openai import OpenAISettings


SETTINGS = OpenAISettings(provider="openai", api_key="test-only-not-a-real-key", model="test-model")


def function_response(name, args=None):
    return {"status": "completed", "output": [{
        "type": "function_call", "call_id": "call-test", "name": name,
        "arguments": json.dumps(args or {}),
    }], "usage": {"input_tokens": 100, "output_tokens": 20}}


REVIEW = {
    "summary": "Kandidat B ditolak. Kandidat A masih membutuhkan bukti dan kualifikasi. Bandingkan fallback dengan reviewer manusia.",
    "candidate_ids": ["CAND-A", "CAND-B", "CAND-C"],
    "next_steps": ["REVIEW_EVIDENCE_GAPS", "REVIEW_RECOVERY_SCENARIOS", "REQUEST_HUMAN_REVIEW"],
}


class ScriptedClient:
    settings = SETTINGS

    def __init__(self, responses=None):
        self.requests = []
        self.responses = deepcopy(responses if responses is not None else [
            function_response("getExposure"),
            function_response("findRecoveryOptions"),
            function_response("getCandidateEvidence", {"candidate_id": "CAND-C"}),
            function_response("getCandidateEvidence", {"candidate_id": "CAND-B"}),
            function_response("getCandidateEvidence", {"candidate_id": "CAND-A"}),
            function_response("getQualificationDependencies", {"candidate_id": "CAND-A"}),
            function_response("simulateRecovery"),
            function_response("finishReview", REVIEW),
        ])

    def create(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        return self.responses.pop(0)
