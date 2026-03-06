from __future__ import annotations

from typing import Any, Dict

from src.config import ExperimentConfig
from src.kernels.registry import build_kernel
from src.topologies.coupling_maps import coupling_map_for
from src.transpile.routing import compile_best_of_k
from src.observables.policy import build_observables
from src.exec.aer_expectations import estimate_expectations
from src.metrics.m1 import m1_mae
from src.metrics.m2 import m2_for_technique


def run(cfg: ExperimentConfig) -> Dict[str, Any]:
    cfg.validate()

    logical = build_kernel(cfg.kernel)
    cmap = coupling_map_for(cfg.topology, cfg.n_qubits, seed=7)

    k = int(cfg.routing.best_of_k)
    compiled = compile_best_of_k(
        logical,
        coupling_map=cmap,
        cfg=cfg,
        k=k,
        objective="depth_then_cx",
    )

    observables = build_observables(cfg.obs_policy, cfg.n_qubits, cfg.obs_cap)

    ideal = estimate_expectations(cfg, compiled, observables, noisy=False)
    noisy = estimate_expectations(cfg, compiled, observables, noisy=True)

    M1 = m1_mae(ideal, noisy)
    M2 = m2_for_technique(technique="T2", compiled_circuit=compiled)

    return {
        "M1": float(M1),
        "M2": M2,
        "best_of_k": k,
    }
