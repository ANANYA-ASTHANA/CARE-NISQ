from __future__ import annotations

from qiskit_aer.noise import NoiseModel, depolarizing_error

from src.config import ExperimentConfig


def build_noise_model(cfg: ExperimentConfig) -> NoiseModel | None:
    """
    Minimal Aer noise model.
    If cfg.noise.level == 0, returns None (ideal simulation).
    """
    p = float(cfg.noise.level)
    if p <= 0.0:
        return None

    model = cfg.noise.model.lower()

    if model != "depolarizing":
        raise ValueError(f"Unsupported noise model '{cfg.noise.model}'. Only 'depolarizing' is implemented.")

    # Simple, standard assumption: 2Q gates are noisier than 1Q gates
    p1 = p
    p2 = min(0.2, 10.0 * p)

    e1 = depolarizing_error(p1, 1)
    e2 = depolarizing_error(p2, 2)

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(e1, ["rz", "sx", "x"])
    noise_model.add_all_qubit_quantum_error(e2, ["cx"])

    return noise_model
