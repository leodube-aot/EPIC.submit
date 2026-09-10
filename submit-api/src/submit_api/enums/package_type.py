"""Submission package type class.

Manages the package types
"""
from __future__ import annotations

import enum


class PackageTypeEnum(enum.Enum):
    """Enum for package types."""

    MANAGEMENT_PLAN = 'Management Plan'
    IEM = 'IEM'
    ADDITIONAL_INFORMATION = 'Additional Information'


class PackageTypeId(enum.Enum):
    """Enum for package type IDs."""

    MANAGEMENT_PLAN = 1
    IEM = 2


class PackageApprovalType(enum.Enum):
    """Enum for package approval types."""

    A = 'A'
    B = 'B'
    C = 'C'


MANAGEMENT_PLAN_RELATED_TYPES = frozenset(
    {PackageTypeEnum.MANAGEMENT_PLAN.value, PackageTypeEnum.IEM.value}
)
