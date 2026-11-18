"""Client request identity headers (User-Agent / x-endor-caller*).

Normative rules: docs/contracts.md § Client identity and
agent-knowledge/contracts/client-identity.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

CALLER_SDK = "endorlabs-sdk"
_IDENTITY_HEADER_NAMES = (
    "User-Agent",
    "x-endor-caller",
    "x-endor-caller-version",
    "x-endor-op-comment",
)


def sdk_package_version() -> str:
    """Installed ``endorlabs`` version, or a dev placeholder when unpackaged."""
    try:
        return pkg_version("endorlabs")
    except PackageNotFoundError:
        return "0.0.0.dev0"


def _header_key_map(headers: Mapping[str, str]) -> dict[str, str]:
    """Map lower-case header name → original key present in ``headers``."""
    return {str(key).lower(): str(key) for key in headers}


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    """Session identity headers for ``Client`` / ``APIClient``.

    Attributes:
        caller: Product plane token for ``x-endor-caller`` (e.g. ``endorlabs-sdk``).
        caller_version: Version string for ``x-endor-caller-version``.
        user_agent: Full ``User-Agent`` value.
        op_comment: Optional ``x-endor-op-comment`` (gateway / Mongo op comment).
    """

    caller: str
    caller_version: str
    user_agent: str
    op_comment: str | None = None

    def __post_init__(self) -> None:
        """Validate caller plane tokens and required identity fields."""
        caller = self.caller.strip()
        if not caller:
            msg = "caller must be a non-empty string"
            raise ValueError(msg)
        if caller == "endorctl" or caller.startswith("endorctl/"):
            msg = "caller must not forge endorctl identity"
            raise ValueError(msg)
        if self.op_comment and "service/endorctl" in self.op_comment:
            msg = "op_comment must not contain service/endorctl"
            raise ValueError(msg)
        if not self.caller_version.strip():
            msg = "caller_version must be a non-empty string"
            raise ValueError(msg)
        if not self.user_agent.strip():
            msg = "user_agent must be a non-empty string"
            raise ValueError(msg)

    def as_headers(self) -> dict[str, str]:
        """Return identity headers to merge into the session."""
        headers = {
            "User-Agent": self.user_agent,
            "x-endor-caller": self.caller,
            "x-endor-caller-version": self.caller_version,
        }
        if self.op_comment:
            headers["x-endor-op-comment"] = self.op_comment
        return headers

    def with_op_comment(self, op_comment: str | None) -> ClientIdentity:
        """Return a copy with ``op_comment`` replaced (validated)."""
        return replace(self, op_comment=op_comment)

    @classmethod
    def sdk(cls, *, op_comment: str | None = None) -> ClientIdentity:
        """Default SDK client identity."""
        ver = sdk_package_version()
        return cls(
            caller=CALLER_SDK,
            caller_version=ver,
            user_agent=f"{CALLER_SDK}/{ver}",
            op_comment=op_comment,
        )

    @classmethod
    def workflow(cls, name: str, *, version: str | None = None) -> ClientIdentity:
        """SDK caller with workflow-named ``x-endor-op-comment``."""
        ver = version or sdk_package_version()
        return cls.sdk(op_comment=f"{name}/{ver}")

    @classmethod
    def custom(
        cls,
        *,
        caller: str,
        caller_version: str,
        user_agent: str | None = None,
        op_comment: str | None = None,
    ) -> ClientIdentity:
        """Host-built identity (any non-endorctl caller plane).

        When ``user_agent`` is omitted, defaults to ``{caller}/{caller_version}``.
        """
        ua = user_agent if user_agent is not None else f"{caller}/{caller_version}"
        return cls(
            caller=caller,
            caller_version=caller_version,
            user_agent=ua,
            op_comment=op_comment,
        )


def merge_identity_headers(
    target: dict[str, str],
    identity: ClientIdentity,
    *,
    existing: Mapping[str, str] | None = None,
) -> None:
    """Apply identity headers into ``target``, skipping keys already in ``existing``.

    When ``existing`` is set (injected httpx client headers), host-provided
    User-Agent / caller headers are preserved. Identity keys are filled only
    when missing from ``existing``.
    """
    present = _header_key_map(existing) if existing is not None else {}
    for key, value in identity.as_headers().items():
        if key.lower() in present:
            continue
        target[key] = value


def identity_header_names() -> tuple[str, ...]:
    """Canonical identity header names (for tests / hosts)."""
    return _IDENTITY_HEADER_NAMES
