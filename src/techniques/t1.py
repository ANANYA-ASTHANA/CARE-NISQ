from __future__ import annotations

from typing import Any, Dict

from src.config import ExperimentConfig
from src.kernels.registry import build_kernel
from src.topologies.coupling_maps import coupling_map_for
from src.transpile.routing import compile_k1
from src.observables.policy import build_observables
from src.exec.aer_expectations import estimate_expectations
from src.metrics.m1 import m1_mae


def run(cfg: ExperimentConfig) -> Dict[str, Any]:
    cfg.validate()

    logical = build_kernel(cfg.kernel)
    cmap = coupling_map_for(cfg.topology, cfg.n_qubits, seed=7)

    compiled = compile_k1(logical, coupling_map=cmap, cfg=cfg)

    observables = build_observables(cfg.obs_policy, cfg.n_qubits, cfg.obs_cap)

    ideal = estimate_expectations(cfg, compiled, observables, noisy=False)
    noisy = estimate_expectations(cfg, compiled, observables, noisy=True)

    m1 = float(m1_mae(ideal, noisy))

    return m1
