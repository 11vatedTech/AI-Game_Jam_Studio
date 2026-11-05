"""Perception: capture bundles, image transport and probe verification.

Three obligations are kept separate on purpose (spec rev 2 §1): whether pixels
reached the agent, whether the agent could read them, and whether the resulting
finding may decide anything. Nothing in this package may satisfy one obligation
on another's behalf.
"""

from .bundle import CaptureBundle, Verification, compute_grade
from .transport import TransportProfile, TransportLimitExceeded, DEFAULT_PROFILE

__all__ = [
    "CaptureBundle",
    "Verification",
    "compute_grade",
    "TransportProfile",
    "TransportLimitExceeded",
    "DEFAULT_PROFILE",
]
