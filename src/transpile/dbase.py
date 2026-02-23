from __future__ import annotations

from typing import Iterable, Tuple, Optional

from qiskit import transpile
from qiskit.transpiler import CouplingMap


def compute_dbase(
    circuit,
    coupling_map: CouplingMap,
    *,
    basis_gates: Iterable[str] = ("rz", "sx", "x", "cx"),
    optimization_level: int = 1,
    layout_method: str = "sabre",
    routing_method: str = "sabre",
    seed_transpiler: Optional[int] = 11,
) -> Tuple[int, int]:
    """
    Compute D_base and base gate count for a given logical circuit and device coupling.
    Returns (depth, size).
    """
    tqc = transpile(
        circuit,
        coupling_map=coupling_map,
        basis_gates=list(basis_gates),
        optimization_level=optimization_level,
        layout_method=layout_method,
        routing_method=routing_method,
        seed_transpiler=seed_transpiler,
    )
    return tqc.depth(), tqc.size()
