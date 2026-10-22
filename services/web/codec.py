"""Lossless, allowlisted JSON storage for immutable domain aggregates.

Canonical public JSON deliberately flattens Decimal, enum, and date types.
Storage keeps these tags so reopening a case never changes comparisons/hashes.
No pickle or type names imported from stored data are used.
"""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json

from core.case_state import models as cases
from core.exposure import models as exposure
from core.qualification import models as qualification
from core.recovery_options import models as recovery
from core.requirements import models as requirements
from core.simulation import models as simulation


TYPES = {
    f"{value.__module__}.{value.__name__}": value
    for module in (cases, exposure, qualification, recovery, requirements, simulation)
    for value in vars(module).values()
    if isinstance(value, type)
    and value.__module__ == module.__name__
    and (is_dataclass(value) or issubclass(value, Enum))
}


def _encode(value):
    if isinstance(value, Enum):
        return {"$enum": f"{type(value).__module__}.{type(value).__name__}", "value": value.value}
    if is_dataclass(value):
        return {
            "$type": f"{type(value).__module__}.{type(value).__name__}",
            "fields": {field.name: _encode(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}
    if isinstance(value, tuple):
        return {"$tuple": [_encode(item) for item in value]}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    return value


def _decode(value):
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    if "$type" in value:
        cls = TYPES[value["$type"]]
        return cls(**{key: _decode(item) for key, item in value["fields"].items()})
    if "$enum" in value:
        return TYPES[value["$enum"]](value["value"])
    if "$datetime" in value:
        return datetime.fromisoformat(value["$datetime"])
    if "$date" in value:
        return date.fromisoformat(value["$date"])
    if "$decimal" in value:
        return Decimal(value["$decimal"])
    if "$tuple" in value:
        return tuple(_decode(item) for item in value["$tuple"])
    return {key: _decode(item) for key, item in value.items()}


def dumps(value):
    return json.dumps({"schema_version": 1, "data": _encode(value)}, ensure_ascii=False)


def loads(payload):
    envelope = json.loads(payload)
    if envelope["schema_version"] != 1:
        raise ValueError("unsupported case storage schema")
    return _decode(envelope["data"])
