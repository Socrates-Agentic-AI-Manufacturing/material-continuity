"""Small runtime compatibility helpers for supported deployment runtimes."""

from enum import Enum

try:  # Python 3.11+
    from enum import StrEnum  # type: ignore
except ImportError:  # Python 3.10 buildpacks
    class StrEnum(str, Enum):
        """Backport of enum.StrEnum sufficient for this project."""

        def __str__(self) -> str:
            return self.value
