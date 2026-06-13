"""Shared infrastructure for V1-backed consumer resource facades.

Cutover kinds compose ``V1*`` generated wire types with mixins and helpers from
this package.  Per-kind modules in ``resources/{kind}.py`` stay thin.
"""

from .mixin import ConsumerResourceMixin, ConsumerResourceSerializerMixin
from .registry_fields import (
    immutable_fields_for,
    mutable_fields_for,
    registry_row_for_attr,
)

__all__ = [
    "ConsumerResourceMixin",
    "ConsumerResourceSerializerMixin",
    "immutable_fields_for",
    "mutable_fields_for",
    "registry_row_for_attr",
]
