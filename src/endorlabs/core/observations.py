"""Optional host request observation hooks (SDK-010).

Observers must not receive secret-bearing bodies. Failures in observers must
not turn API failures into success. Disabled/absent observers export nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

ObservationKind = Literal["attempt", "retry", "page", "terminal"]


@dataclass(frozen=True, slots=True)
class RequestObservation:
    """Sanitized transport observation for host telemetry adapters."""

    kind: ObservationKind
    method: str
    url: str
    attempt: int | None = None
    status_code: int | None = None
    elapsed_ms: float | None = None
    stop_reason: str | None = None
    error_type: str | None = None
    correlation: dict[str, str] | None = None


@runtime_checkable
class RequestObserver(Protocol):
    """Host-supplied observer; implementations must be side-effect safe."""

    def on_observation(self, observation: RequestObservation) -> None:
        """Receive one sanitized observation."""
        ...


def safe_notify(
    observer: RequestObserver | None,
    observation: RequestObservation,
    *,
    logger: Any | None = None,
) -> None:
    """Invoke observer; swallow observer exceptions so API outcome is unchanged."""
    if observer is None:
        return
    try:
        observer.on_observation(observation)
    except Exception as exc:
        if logger is not None:
            logger.debug("RequestObserver failed: %s", exc)
