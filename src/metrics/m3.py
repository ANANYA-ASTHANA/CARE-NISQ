from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class M3Overhead:
    """
    Execution overhead metric:
    - n_subexperiments: number of generated subcircuits
    - n_observables: number of observables evaluated
    - shots_per_exec: shots used per (subcircuit, observable) evaluation
    - total_execs: number of primitive evaluations
    - total_shots: total shots across all evaluations
    """
    n_subexperiments: int
    n_observables: int
    shots_per_exec: int
    total_execs: int
    total_shots: int
    coeff_len: Optional[int] = None
    time_exec_seconds: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "n_subexperiments": int(self.n_subexperiments),
            "n_observables": int(self.n_observables),
            "shots_per_exec": int(self.shots_per_exec),
            "total_execs": int(self.total_execs),
            "total_shots": int(self.total_shots),
        }
        if self.coeff_len is not None:
            d["coeff_len"] = int(self.coeff_len)
        if self.time_exec_seconds is not None:
            d["time_exec_seconds"] = float(self.time_exec_seconds)
        return d


def compute_m3(
    *,
    n_subexperiments: int,
    n_observables: int,
    shots_per_exec: int,
    coeff_len: Optional[int] = None,
    time_exec_seconds: Optional[float] = None,
) -> M3Overhead:
    total_execs = int(n_subexperiments) * int(n_observables)
    total_shots = int(total_execs) * int(shots_per_exec)
    return M3Overhead(
        n_subexperiments=int(n_subexperiments),
        n_observables=int(n_observables),
        shots_per_exec=int(shots_per_exec),
        total_execs=int(total_execs),
        total_shots=int(total_shots),
        coeff_len=int(coeff_len) if coeff_len is not None else None,
        time_exec_seconds=float(time_exec_seconds) if time_exec_seconds is not None else None,
    )
