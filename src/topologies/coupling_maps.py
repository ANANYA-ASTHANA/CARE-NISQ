from __future__ import annotations

from qiskit.transpiler import CouplingMap
import networkx as nx


def line_coupling(n: int) -> CouplingMap:
    """1D line: 0-1-2-...-(n-1)"""
    edges = [(i, i + 1) for i in range(n - 1)]
    return CouplingMap(edges)


def grid_coupling(rows: int, cols: int) -> CouplingMap:
    """2D grid (row-major node numbering)."""
    edges = []

    def idx(r: int, c: int) -> int:
        return r * cols + c

    for r in range(rows):
        for c in range(cols):
            if r + 1 < rows:
                edges.append((idx(r, c), idx(r + 1, c)))
            if c + 1 < cols:
                edges.append((idx(r, c), idx(r, c + 1)))

    return CouplingMap(edges)


def sparse_deg3_coupling(n: int, seed: int = 7) -> CouplingMap:
    """
    Degree-3 random regular graph as a "sparse connectivity proxy".
    Note: requires n*d even (holds for n=10,12 and d=3).
    """
    G = nx.random_regular_graph(d=3, n=n, seed=seed)
    edges = list(G.edges())
    return CouplingMap(edges)


def coupling_map_for(topology: str, n_qubits: int, seed: int = 7) -> CouplingMap:
    """
    Convenience factory aligned to experiment names: line/grid/sparse.
    Grid dims are chosen to match n_qubits used in the study:
      - 12 qubits -> 3x4
      - 10 qubits -> 2x5
    """
    topo = topology.lower()
    if topo == "line":
        return line_coupling(n_qubits)
    if topo == "grid":
        if n_qubits == 12:
            return grid_coupling(3, 4)
        if n_qubits == 10:
            return grid_coupling(2, 5)
        raise ValueError(f"No default grid shape defined for n_qubits={n_qubits}")
    if topo == "sparse":
        return sparse_deg3_coupling(n_qubits, seed=seed)

    raise ValueError(f"Unknown topology '{topology}'. Expected one of: line, grid, sparse.")
