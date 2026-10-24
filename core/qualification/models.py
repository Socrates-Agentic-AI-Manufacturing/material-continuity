"""Typed qualification tasks, calendars, and graph results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from decimal import Decimal
from core.compat import StrEnum
from typing import Any


class QualificationGraphInputError(ValueError):
    """Raised when qualification graph inputs are structurally invalid."""


class TaskType(StrEnum):
    DELIVERY = "DELIVERY"
    TEST = "TEST"
    ENGINEERING_REVIEW = "ENGINEERING_REVIEW"
    QUALITY_REVIEW = "QUALITY_REVIEW"
    RELEASE = "RELEASE"


class ScheduleStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class QualificationTask:
    task_id: str
    candidate_id: str
    name: str
    task_type: TaskType
    duration_hours: Decimal | None
    predecessor_ids: tuple[str, ...]
    required_resource: str | None
    earliest_start: datetime | None
    requirement_id: str | None
    source_reference: str


@dataclass(frozen=True, slots=True)
class ResourceCalendar:
    resource_id: str
    timezone: str
    working_weekdays: tuple[int, ...]
    workday_start: time
    workday_end: time
    unavailable_dates: tuple[date, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskSchedule:
    task_id: str
    name: str
    task_type: TaskType
    status: ScheduleStatus
    start_time: datetime | None
    end_time: datetime | None
    duration_hours: Decimal | None
    predecessor_ids: tuple[str, ...]
    required_resource: str | None
    requirement_id: str | None
    reason: str | None
    source_reference: str


@dataclass(frozen=True, slots=True)
class QualificationGraphResult:
    candidate_id: str
    resolved: bool
    qualification_complete: datetime | None
    critical_path: tuple[str, ...]
    unresolved_task_ids: tuple[str, ...]
    schedules: tuple[TaskSchedule, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation without custom encoders."""

        def serialize(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, tuple):
                return [serialize(item) for item in value]
            if isinstance(value, list):
                return [serialize(item) for item in value]
            if isinstance(value, dict):
                return {key: serialize(item) for key, item in value.items()}
            return value

        return serialize(asdict(self))
