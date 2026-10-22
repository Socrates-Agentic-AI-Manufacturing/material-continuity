"""Web fixture adapter: fingerprint sources and keep simulation tied to its graph."""

from dataclasses import replace
from datetime import datetime
from hashlib import sha256

from agents.evidence_specialist import MockEvidenceRetriever
from agents.evidence_specialist.fixtures import load_qualification_procedure_fixtures
from agents.recovery_supervisor import FixtureRecoverySupervisorTools
from core.evidence.fixtures import load_evidence_extraction_fixtures
from core.simulation import simulate_recovery
from core.simulation.fixtures import load_simulation_fixtures
from core.simulation.models import ScenarioType
from core.requirements import CandidateDecision


class WebFixtureTools(FixtureRecoverySupervisorTools):
    def __init__(self, fixture_root, document_root):
        super().__init__(fixture_root)
        self.document_root = document_root
        versions = {source.source_id: source.version for source in self.get_source_versions()}
        document_sources = {
            "Candidate_A_Datasheet_Rev2.pdf": "SRC-CAND-A-DATASHEET",
            "Candidate_B_Datasheet.pdf": "SRC-CAND-B-DATASHEET",
        }
        extractions = tuple(
            replace(item, current_source_revision=versions[document_sources[item.source_document]])
            if item.source_document in document_sources else item
            for item in load_evidence_extraction_fixtures(fixture_root)
        )
        self._evidence_retriever = MockEvidenceRetriever(
            extractions=extractions,
            procedures=load_qualification_procedure_fixtures(fixture_root),
        )

    def get_source_versions(self):
        # The entire small local dataset is a single consistent input boundary.
        # Conservatively invalidate approvals if any input changes; fine-grained
        # upstream connector revisions can replace this in a later adapter.
        digest = sha256()
        paths = sorted(self._fixture_root.rglob("*.json"))
        if hasattr(self, "document_root"):
            paths += sorted(self.document_root.glob("*.pdf"))
        for path in paths:
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
        return tuple(
            replace(source, content_hash=digest.hexdigest())
            for source in super().get_source_versions()
        )

    def simulate_recovery(self, *, exposure, shortage_at: datetime):
        scenarios = load_simulation_fixtures(self._fixture_root)
        updated = []
        for scenario in scenarios:
            if scenario.scenario_type is ScenarioType.SUBSTITUTE_QUALIFICATION:
                references = [ref for ref in scenario.source_references if ref.startswith("qualification-graph:")]
                candidate = references[0].split(":", 1)[1] if len(references) == 1 else None
                graph = self.get_qualification_graph(candidate_id=candidate) if candidate else None
                complete = graph.qualification_complete if graph and graph.resolved else None
                rejected = candidate and self.investigate_candidate(
                    candidate_id=candidate,
                    requirements=self.get_requirements(material_id=exposure.material_id),
                ).comparison.decision is CandidateDecision.REJECTED_HARD_MISMATCH
                if rejected:
                    complete = None
                scenario = replace(
                    scenario,
                    ready_at=complete,
                    qualification_complete=complete,
                    unresolved_conditions=scenario.unresolved_conditions + (
                        ("Candidate rejected for a hard mismatch; substitute recovery blocked",)
                        if rejected else (() if complete else ("Qualification timing unresolved",))
                    ),
                )
            updated.append(scenario)
        return simulate_recovery(exposure=exposure, shortage_at=shortage_at, scenarios=tuple(updated))
