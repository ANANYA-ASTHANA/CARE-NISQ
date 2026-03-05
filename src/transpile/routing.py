from __future__ import annotations

from dataclasses import replace
from typing import Callable, List, Tuple

from qiskit import QuantumCircuit
from qiskit import transpile
from qiskit.transpiler import CouplingMap

from src.config import ExperimentConfig


def compile_k1(circuit, coupling_map, cfg):
    return transpile(
        circuit,
        coupling_map=coupling_map,
        basis_gates=list(cfg.routing.basis_gates),
        optimization_level=cfg.routing.optimization_level,
        layout_method=cfg.routing.layout_method,
        routing_method=cfg.routing.routing_method,
        seed_transpiler=cfg.rep.seed_transpiler,
    )


def _score_compiled(
    qc: QuantumCircuit,
    objective: str = "depth_then_cx",
) -> Tuple[int, int, int]:
    """
    Lower is better. We return a tuple so Python does lexicographic comparison.
    """
    ops = qc.count_ops()
    depth = int(qc.depth())
    cx = int(ops.get("cx", 0))
    size = int(qc.size())

    if objective == "depth_then_cx":
        return (depth, cx, size)
    if objective == "cx_then_depth":
        return (cx, depth, size)

    raise ValueError(f"Unknown objective '{objective}'")


def compile_best_of_k(
    circuit: QuantumCircuit,
    *,
    coupling_map: CouplingMap,
    cfg: ExperimentConfig,
    k: int,
    objective: str = "depth_then_cx",
) -> QuantumCircuit:
    """
    Compile k candidates by varying seed_transpiler; pick the best by objective.
    - Only changes transpiler seed (NOT simulator seed).
    - Leaves everything else identical for fairness.
    """
    if k <= 1:
        return compile_k1(circuit, coupling_map=coupling_map, cfg=cfg)

    best_qc = None
    best_score = None

    # Deterministic list of seeds derived from the base transpiler seed
    base_seed = int(cfg.rep.seed_transpiler)
    seeds = [base_seed + i for i in range(k)]

    for s in seeds:
        cfg_s = replace(cfg, rep=replace(cfg.rep, seed_transpiler=int(s)))
        qc = compile_k1(circuit, coupling_map=coupling_map, cfg=cfg_s)
        score = _score_compiled(qc, objective=objective)

        if best_score is None or score < best_score:
            best_score = score
            best_qc = qc

    assert best_qc is not None
    return best_qc
