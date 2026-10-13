"""Controlled tool interface and local fixture-backed implementation."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from agents.evidence_specialist import (
    EvidenceInvestigationRequest,
    EvidenceSpecialistResult,
    MockEvidenceRetriever,
    investigate_candidate,
)
from agents.evidence_specialist.fixtures import load_qualification_procedure_fixtures
from core.case_state import SourceVersion
from core.case_state.fixtures import load_source_version_fixtures
from core.evidence.fixtures import load_evidence_extraction_fixtures
from core.exposure import ExposureResult, calculate_exposure
from core.exposure.fixtures import load_exposure_fixtures
from core.qualification import QualificationGraphResult, build_qualification_graph
from core.qualification.fixtures import load_qualification_fixtures
from core.recovery_options import (
    RecoverySearchRequest,
    RecoverySearchResult,
    find_recovery_options,
)
from core.recovery_options.fixtures import load_recovery_option_fixtures
from core.requirements import Requirement
from core.requirements.fixtures import load_requirement_fixtures
from core.simulation import RecoverySimulationResult, simulate_recovery
from core.simulation.fixtures import load_simulation_fixtures


class RecoverySupervisorTools(Protocol):
    def get_exposure(self, *, material_id: str, as_of: datetime) -> ExposureResult: ...

    def find_recovery_options(
        self,
        *,
        material_id: str,
        required_quantity: int,
        need_by: date,
        as_of: date,
    ) -> RecoverySearchResult: ...

    def get_requirements(self, *, material_id: str) -> tuple[Requirement, ...]: ...

    def investigate_candidate(
        self,
        *,
        candidate_id: str,
        requirements: Sequence[Requirement],
    ) -> EvidenceSpecialistResult: ...

    def get_qualification_graph(
        self, *, candidate_id: str
    ) -> QualificationGraphResult | None: ...

    def simulate_recovery(
        self,
        *,
        exposure: ExposureResult,
        shortage_at: datetime,
    ) -> RecoverySimulationResult: ...

    def get_source_versions(self) -> tuple[SourceVersion, ...]: ...


class FixtureRecoverySupervisorTools:
    """Local adapter over deterministic engines and synthetic fixtures."""

    def __init__(self, fixture_root: Path) -> None:
        self._fixture_root = fixture_root
        self._evidence_retriever = MockEvidenceRetriever(
            extractions=load_evidence_extraction_fixtures(fixture_root),
            procedures=load_qualification_procedure_fixtures(fixture_root),
        )

    def get_exposure(self, *, material_id: str, as_of: datetime) -> ExposureResult:
        material, boms, orders, receipts = load_exposure_fixtures(
            self._fixture_root, material_id
        )
        return calculate_exposure(
            material=material,
            bom_items=boms,
            production_orders=orders,
            receipts=receipts,
            as_of=as_of,
        )

    def find_recovery_options(
        self,
        *,
        material_id: str,
        required_quantity: int,
        need_by: date,
        as_of: date,
    ) -> RecoverySearchResult:
        return find_recovery_options(
            request=RecoverySearchRequest(
                material_id=material_id,
                required_quantity=required_quantity,
                need_by=need_by,
                as_of=as_of,
            ),
            options=load_recovery_option_fixtures(self._fixture_root),
        )

    def get_requirements(self, *, material_id: str) -> tuple[Requirement, ...]:
        requirements, _ = load_requirement_fixtures(self._fixture_root)
        return requirements

    def investigate_candidate(
        self,
        *,
        candidate_id: str,
        requirements: Sequence[Requirement],
    ) -> EvidenceSpecialistResult:
        return investigate_candidate(
            EvidenceInvestigationRequest(
                candidate_id=candidate_id,
                requirements=tuple(requirements),
            ),
            retriever=self._evidence_retriever,
        )

    def get_qualification_graph(
        self, *, candidate_id: str
    ) -> QualificationGraphResult | None:
        tasks, calendars = load_qualification_fixtures(self._fixture_root)
        candidate_tasks = tuple(
            task for task in tasks if task.candidate_id == candidate_id
        )
        if not candidate_tasks:
            return None
        return build_qualification_graph(
            candidate_id=candidate_id,
            tasks=candidate_tasks,
            calendars=calendars,
        )

    def simulate_recovery(
        self,
        *,
        exposure: ExposureResult,
        shortage_at: datetime,
    ) -> RecoverySimulationResult:
        return simulate_recovery(
            exposure=exposure,
            shortage_at=shortage_at,
            scenarios=load_simulation_fixtures(self._fixture_root),
        )

    def get_source_versions(self) -> tuple[SourceVersion, ...]:
        return load_source_version_fixtures(self._fixture_root)
