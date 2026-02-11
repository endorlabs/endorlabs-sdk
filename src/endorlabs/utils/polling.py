"""Polling utilities for the Endor Labs SDK.

Provides wait_until for blocking until a predicate becomes true with
jittered exponential backoff and configurable timeout.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def wait_until(
    predicate: Callable[[], bool],
    timeout: float = 60,
    poll_interval_max: float = 10,
) -> bool:
    """Block until predicate returns True or timeout is exceeded.

    Uses jittered exponential backoff: starts at ~1s, doubles each poll,
    capped at poll_interval_max. Caller passes a callable that performs
    GET/LIST (or any check) and returns whether the desired state is reached.

    Args:
        predicate: Callable with no args that returns True when done.
        timeout: Maximum seconds to wait. Default 60.
        poll_interval_max: Maximum seconds between polls. Default 10.

    Returns:
        True if predicate returned True before timeout; False if timeout exceeded.

    Example:
        >>> client.wait_until(
        ...     lambda: client.scan_result.get(uuid).spec.status == "COMPLETED",
        ...     timeout=120,
        ... )

    """
    deadline = time.monotonic() + timeout
    interval = 1.0
    while time.monotonic() < deadline:
        if predicate():
            return True
        jitter = interval * 0.1 * (2 * random.random() - 1)
        sleep_for = min(interval + jitter, poll_interval_max)
        sleep_for = max(0, min(sleep_for, deadline - time.monotonic()))
        if sleep_for > 0:
            time.sleep(sleep_for)
        interval = min(interval * 2, poll_interval_max)
    return False
