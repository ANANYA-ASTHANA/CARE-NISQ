from __future__ import annotations

from src.kernels.registry import build_kernel
from src.topologies.coupling_maps import coupling_map_for
from src.transpile.dbase import compute_dbase


def main():
    # Build canonical kernels
    qft12 = build_kernel("QFT12")
    hea10 = build_kernel("HEA10")
    grv10 = build_kernel("Grover10")

    # Use a fixed transpiler seed for consistent D_base reporting
    seed_transpiler = 11

    # QFT12: 12-qubit maps
    for topo in ["line", "grid", "sparse"]:
        cmap = coupling_map_for(topo, n_qubits=12, seed=7)
        D, gates = compute_dbase(qft12, cmap, seed_transpiler=seed_transpiler)
        print("QFT12", topo, "depth=", D, "gates=", gates)

    # HEA/Grover: 10-qubit maps
    for topo in ["line", "grid", "sparse"]:
        cmap = coupling_map_for(topo, n_qubits=10, seed=7)
        D, gates = compute_dbase(hea10, cmap, seed_transpiler=seed_transpiler)
        print("HEA10", topo, "depth=", D, "gates=", gates)

    for topo in ["line", "grid", "sparse"]:
        cmap = coupling_map_for(topo, n_qubits=10, seed=7)
        D, gates = compute_dbase(grv10, cmap, seed_transpiler=seed_transpiler)
        print("Grover10", topo, "depth=", D, "gates=", gates)


if __name__ == "__main__":
    main()
