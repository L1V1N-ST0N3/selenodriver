from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClickResult:
    """Details about the successful stage of a randomized click."""

    method: str
    x: float | None
    y: float | None
    attempts: tuple[str, ...]
    url_before: str
    url_after: str
    verified: bool

