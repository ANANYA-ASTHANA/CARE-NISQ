from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from qiskit.quantum_info import SparsePauliOp

Observable = SparsePauliOp


def _z_on(n: int, i: int) -> Observable:
    s = ["I"] * n
    s[n - 1 - i] = "Z"  # qiskit uses little-endian in Pauli strings
    return SparsePauliOp("".join(s))


def _zz_on(n: int, i: int, j: int) -> Observable:
    s = ["I"] * n
    s[n - 1 - i] = "Z"
    s[n - 1 - j] = "Z"
    return SparsePauliOp("".join(s))


def build_observables(obs_policy: str, n_qubits: int, obs_cap: int) -> List[Observable]:
    policy = obs_policy.strip()

    if policy != "local_Z_ZZ":
        raise ValueError(f"Unsupported obs_policy='{obs_policy}'. Expected 'local_Z_ZZ'.")

    obs: List[Observable] = []

    # Deterministic order: all Z_i first, then all Z_i Z_{i+1}
    for i in range(n_qubits):
        obs.append(_z_on(n_qubits, i))
        if len(obs) >= obs_cap:
            return obs

    for i in range(n_qubits - 1):
        obs.append(_zz_on(n_qubits, i, i + 1))
        if len(obs) >= obs_cap:
            return obs

    return obs
