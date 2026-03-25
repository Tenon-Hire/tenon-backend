from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationCompareAccessContext:
    simulation_id: int


__all__ = ["SimulationCompareAccessContext"]
