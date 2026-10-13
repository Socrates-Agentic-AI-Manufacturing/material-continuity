"""Recovery Supervisor orchestration over controlled deterministic tools."""

from __future__ import annotations

from core.case_state import CaseStatus, CaseTrigger, create_case
from core.requirements import CandidateDecision

from .models import (
    CandidateAssessment,
    RecoverySummary,
    RecoverySupervisorInputError,
    RecoverySupervisorRequest,
    RecoverySupervisorResult,
    RecoveryWorkflowStatus,
    ScenarioSummary,
    SupervisorTool,
    SupervisorToolTrace,
)
from .tools import RecoverySupervisorTools


def run_recovery_workflow(
    request: RecoverySupervisorRequest,
    *,
    tools: RecoverySupervisorTools,
) -> RecoverySupervisorResult:
    """Run the local recovery workflow without granting action authority."""

    _validate_request(request)
    trace: list[SupervisorToolTrace] = []
    exposure = tools.get_exposure(
        material_id=request.material_id,
        as_of=request.as_of,
    )
    _trace(
        trace,
        SupervisorTool.GET_EXPOSURE,
        request.material_id,
        "EXPOSED" if exposure.shortage_date else "NO_EXPOSURE",
    )
    if exposure.shortage_date is None:
        return RecoverySupervisorResult(
            summary=_summary(
                status=RecoveryWorkflowStatus.NO_EXPOSURE,
                exposure=exposure,
                approved_recovery_sufficient=True,
                candidates=(),
                simulation=None,
            ),
            case=None,
            exposure=exposure,
            recovery_options=None,
            candidates=(),
            simulation=None,
            tool_trace=tuple(trace),
        )
    if request.shortage_at.date() != exposure.shortage_date:
        raise RecoverySupervisorInputError(
            "shortage_at date must match deterministic exposure shortage date"
        )

    required_quantity = sum(
        order.unserved_quantity for order in exposure.affected_orders
    )
    if required_quantity <= 0:
        raise RecoverySupervisorInputError(
            "exposed workflow requires positive unserved quantity"
        )
    recovery_options = tools.find_recovery_options(
        material_id=request.material_id,
        required_quantity=required_quantity,
        need_by=exposure.shortage_date,
        as_of=request.as_of.date(),
    )
    _trace(
        trace,
        SupervisorTool.FIND_RECOVERY_OPTIONS,
        request.material_id,
        (
            "APPROVED_SUFFICIENT"
            if recovery_options.approved_recovery_sufficient
            else "CANDIDATES_REQUIRED"
        ),
    )

    assessments: list[CandidateAssessment] = []
    if not recovery_options.approved_recovery_sufficient:
        requirements = tools.get_requirements(material_id=request.material_id)
        for option in recovery_options.unqualified_candidates:
            if option.candidate_id is None:
                raise RecoverySupervisorInputError(
                    f"unqualified option {option.option_id} has no candidate_id"
                )
            evidence = tools.investigate_candidate(
                candidate_id=option.candidate_id,
                requirements=requirements,
            )
            _trace(
                trace,
                SupervisorTool.EVIDENCE_SPECIALIST,
                option.candidate_id,
                evidence.comparison.decision.value,
            )
            qualification = None
            if (
                evidence.comparison.decision
                is not CandidateDecision.REJECTED_HARD_MISMATCH
            ):
                qualification = tools.get_qualification_graph(
                    candidate_id=option.candidate_id
                )
                _trace(
                    trace,
                    SupervisorTool.QUALIFICATION_GRAPH,
                    option.candidate_id,
                    "FOUND" if qualification else "NOT_FOUND",
                )
            assessments.append(
                CandidateAssessment(
                    candidate_id=option.candidate_id,
                    evidence=evidence,
                    qualification=qualification,
                )
            )

    simulation = tools.simulate_recovery(
        exposure=exposure,
        shortage_at=request.shortage_at,
    )
    _trace(
        trace,
        SupervisorTool.SIMULATE_RECOVERY,
        request.material_id,
        f"{len(simulation.scenarios)}_SCENARIOS",
    )
    case = create_case(
        case_id=request.case_id,
        status=CaseStatus.UNDER_REVIEW,
        trigger=CaseTrigger(
            event_id=request.event_id,
            trigger_type=request.trigger_type,
            material_id=request.material_id,
            detected_at=request.as_of,
            source_reference=request.source_reference,
        ),
        exposure=exposure,
        recovery_options=recovery_options,
        candidate_comparisons=tuple(
            assessment.evidence.comparison for assessment in assessments
        ),
        qualification_graphs=tuple(
            assessment.qualification
            for assessment in assessments
            if assessment.qualification is not None
        ),
        simulation=simulation,
        source_versions=tools.get_source_versions(),
        created_at=request.created_at,
    )
    _trace(
        trace,
        SupervisorTool.CREATE_CASE,
        request.case_id,
        f"VERSION_{case.current.case_version}",
    )
    status = (
        RecoveryWorkflowStatus.APPROVED_RECOVERY_AVAILABLE
        if recovery_options.approved_recovery_sufficient
        else RecoveryWorkflowStatus.CANDIDATE_QUALIFICATION_REQUIRED
    )
    return RecoverySupervisorResult(
        summary=_summary(
            status=status,
            exposure=exposure,
            approved_recovery_sufficient=(
                recovery_options.approved_recovery_sufficient
            ),
            candidates=tuple(assessments),
            simulation=simulation,
        ),
        case=case,
        exposure=exposure,
        recovery_options=recovery_options,
        candidates=tuple(assessments),
        simulation=simulation,
        tool_trace=tuple(trace),
    )


def _summary(
    *,
    status: RecoveryWorkflowStatus,
    exposure,
    approved_recovery_sufficient: bool,
    candidates: tuple[CandidateAssessment, ...],
    simulation,
) -> RecoverySummary:
    rejected = tuple(
        item.candidate_id
        for item in candidates
        if item.evidence.comparison.decision
        is CandidateDecision.REJECTED_HARD_MISMATCH
    )
    conditional = tuple(
        item.candidate_id
        for item in candidates
        if item.evidence.comparison.decision
        is CandidateDecision.BLOCKED_PENDING_EVIDENCE_OR_RELEASE
    )
    scenarios = (
        tuple(
            ScenarioSummary(
                scenario_id=item.scenario_id,
                state=item.state,
                remaining_exposed_quantity=item.remaining_exposed_quantity,
                ready_by_shortage=item.ready_by_shortage,
            )
            for item in simulation.scenarios
        )
        if simulation is not None
        else ()
    )
    return RecoverySummary(
        status=status,
        material_id=exposure.material_id,
        shortage_date=exposure.shortage_date,
        exposed_quantity=sum(
            order.unserved_quantity for order in exposure.affected_orders
        ),
        exposed_order_count=len(exposure.affected_orders),
        approved_recovery_sufficient=approved_recovery_sufficient,
        rejected_candidate_ids=rejected,
        conditional_candidate_ids=conditional,
        scenarios=scenarios,
        human_review_required=status is not RecoveryWorkflowStatus.NO_EXPOSURE,
        production_release_authorized=False,
    )


def _trace(
    trace: list[SupervisorToolTrace],
    tool: SupervisorTool,
    target: str,
    outcome: str,
) -> None:
    trace.append(
        SupervisorToolTrace(
            sequence=len(trace) + 1,
            tool=tool,
            target=target,
            outcome=outcome,
        )
    )


def _validate_request(request: RecoverySupervisorRequest) -> None:
    for name, value in (
        ("case_id", request.case_id),
        ("event_id", request.event_id),
        ("material_id", request.material_id),
        ("source_reference", request.source_reference),
    ):
        if not value.strip():
            raise RecoverySupervisorInputError(f"{name} is required")
    for name, value in (
        ("as_of", request.as_of),
        ("shortage_at", request.shortage_at),
        ("created_at", request.created_at),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise RecoverySupervisorInputError(f"{name} must be timezone-aware")
    if request.created_at < request.as_of:
        raise RecoverySupervisorInputError("created_at cannot predate as_of")
