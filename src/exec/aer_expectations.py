from __future__ import annotations

from typing import List, Optional

from qiskit_aer.primitives import Estimator as AerEstimator
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
            "shots": int(cfg.shots.shots_per_exec),
            "seed_simulator": int(cfg.rep.seed_simulator),
            **({"noise_model": noise_model} if noise_model is not None else {}),
        }
    )

    job = est.run([circuit] * len(observables), observables)
    res = job.result()
    # Aer Estimator returns .values aligned to observables
    return [float(v) for v in res.values]
