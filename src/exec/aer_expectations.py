from __future__ import annotations

from typing import List, Optional

from qiskit_aer.primitives import EstimatorV2 as AerEstimator
from qiskit.quantum_info import SparsePauliOp

from src.config import ExperimentConfig
from src.noise.aer_models import build_noise_model


def estimate_expectations(
    cfg: ExperimentConfig,
    circuit,
    observables: List[SparsePauliOp],
    *,
    noisy: bool,
) -> List[float]:
    noise_model = build_noise_model(cfg) if noisy else None

    est = AerEstimator(
        options={
            "run_options": {"shots": int(cfg.shots.shots_per_exec)},
            "backend_options": {"seed_simulator": int(cfg.rep.seed_simulator)},
            **({"noise_model": noise_model} if noise_model is not None else {}),
        }
    )

    pubs = [(circuit, obs) for obs in observables]
    job = est.run(pubs)
    res = job.result()
    
    return [float(pub_result.data.evs) for pub_result in res]
