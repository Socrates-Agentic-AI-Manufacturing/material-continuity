"""Web fixture adapter: fingerprint sources and keep simulation tied to its graph."""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json

from agents.evidence_specialist import MockEvidenceRetriever
from agents.evidence_specialist.fixtures import load_qualification_procedure_fixtures
from agents.recovery_supervisor import FixtureRecoverySupervisorTools
from core.evidence.fixtures import load_evidence_extraction_fixtures
from core.simulation import simulate_recovery
from core.simulation.fixtures import load_simulation_fixtures
from core.simulation.models import ScenarioType
from core.requirements import CandidateDecision
from core.case_state.models import SourceVersion, SourceType
from core.evidence import EvidenceExtraction
from core.evidence.models import ExtractionSupportStatus
from core.exposure import calculate_exposure
from core.exposure.fixtures import load_exposure_fixtures


class WebFixtureTools(FixtureRecoverySupervisorTools):
    def __init__(self, fixture_root, document_root, document_state=(), purchase_order_overrides=()):
        super().__init__(fixture_root)
        self.document_root = document_root
        self.document_state = tuple(document_state)
        self.purchase_order_overrides = {
            item["po_id"]: dict(item) for item in purchase_order_overrides
        }
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
        # An active uploaded candidate dossier replaces prepared technical
        # evidence, never QMS authority. Pending/failed/unreviewed => UNKNOWN.
        replaced = {item["candidate_id"] for item in self.document_state}
        extractions = tuple(item for item in extractions if item.candidate_id not in replaced or item.property == "PLANT_QUALIFICATION_RELEASE")
        uploaded = []
        for document in self.document_state:
            if not document.get("reviewed_by"):
                continue
            for index in document["accepted_rows"]:
                row = document["extraction"]["rows"][index]
                value = Decimal(row["value"]) if row["property"] in ("BORE_DIAMETER", "DYNAMIC_LOAD") else row["value"]
                uploaded.append(EvidenceExtraction(
                    extraction_id=f"{document['revision_id']}:{index}", candidate_id=document["candidate_id"],
                    property=row["property"], value=value, unit=row["unit"],
                    source_document=document["revision_id"] + ".pdf", source_revision=document["revision"],
                    current_source_revision=document["revision"], source_page=str(row["page"]),
                    source_location=row["quote"], applicability=row["applicability"], applicable=True,
                    support_status=ExtractionSupportStatus.SUPPORTED,
                ))
        self._evidence_retriever = MockEvidenceRetriever(
            extractions=extractions + tuple(uploaded),
            procedures=load_qualification_procedure_fixtures(fixture_root),
        )

    def purchase_orders(self):
        rows = json.loads((self._fixture_root / "purchase-orders" / "purchase_orders.json").read_text(encoding="utf-8"))
        return tuple({
            **row,
            **({
                "expected_delivery": self.purchase_order_overrides[row["po_id"]]["expected_delivery"],
                "status": "DELAYED",
                "injected": True,
                "original_expected_delivery": row["expected_delivery"],
            } if row["po_id"] in self.purchase_order_overrides else {
                "injected": False,
                "original_expected_delivery": row["expected_delivery"],
            }),
        } for row in rows)

    def get_exposure(self, *, material_id: str, as_of: datetime):
        material, boms, orders, receipts = load_exposure_fixtures(self._fixture_root, material_id)
        overrides = self.purchase_order_overrides
        receipts = tuple(
            replace(
                receipt,
                expected_delivery=date.fromisoformat(overrides[receipt.po_id]["expected_delivery"]),
                status="DELAYED",
            ) if receipt.po_id in overrides else receipt
            for receipt in receipts
        )
        return calculate_exposure(
            material=material,
            bom_items=boms,
            production_orders=orders,
            receipts=receipts,
            as_of=as_of,
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
        if self.purchase_order_overrides:
            digest.update(json.dumps(self.purchase_order_overrides, sort_keys=True).encode())
        sources = tuple(
            replace(source, content_hash=digest.hexdigest())
            for source in super().get_source_versions()
        )
        for item in getattr(self, "document_state", ()):
            evidence = item["extraction"] if item.get("reviewed_by") else None
            content = {"sha256": item["sha256"], "revision_id": item["revision_id"],
                       "extraction": evidence, "accepted_rows": item["accepted_rows"]}
            fingerprint = sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
            sources += (SourceVersion(
                source_id=f"UPLOAD:{item['candidate_id']}:{item['document_id']}", source_type=SourceType.DOCUMENT,
                version=item["revision"], observed_at=datetime.fromisoformat(item["uploaded_at"]), content_hash=fingerprint,
            ),)
        return sources

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
