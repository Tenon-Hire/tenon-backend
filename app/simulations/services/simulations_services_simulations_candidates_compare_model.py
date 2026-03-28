"""Application module for simulations services simulations candidates compare model workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationCompareAccessContext:
    """Represent simulation compare access context data and behavior."""

    simulation_id: int


__all__ = ["SimulationCompareAccessContext"]
