from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Sequence, Tuple

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit_aer.primitives import Estimator as AerEstimator

from qiskit_addon_cutting import (
    cut_gates,
    find_cuts,
    DeviceConstraints,
    OptimizationParameters,
    generate_cutting_experiments,
    reconstruct_expectation_values,
)

from src.config import ExperimentConfig
from src.kernels.registry import build_kernel
from src.topologies.coupling_maps import coupling_map_for
from src.transpile.routing import compile_k1

from src.observables.policy import build_observables  # returns list-like Pauli observables 
from src.exec.aer_expectations import estimate_expectations  # ideal/noiseless reference
from src.noise.aer_models import build_noise_model

from src.metrics.m1 import m1_mae
from src.metrics.m2 import m2_for_technique
from src.metrics.m3 import compute_m3


# -------------------------
# Helper: fragment width rule
# -------------------------
def _fragment_width_cap(n_qubits: int) -> int:
    """
    Rule-based lenient device width cap for automated cut finding:
      W = ceil(0.75 * n)
    """
    return int(math.ceil(0.75 * int(n_qubits)))


# -------------------------
# Helper: deterministic cut selection for cut_gates
# -------------------------
def _select_first_twoq_gate_ids(compiled: QuantumCircuit, fmax: int) -> List[int]:
    gate_ids: List[int] = []
    for idx, (_inst, qargs, _cargs) in enumerate(compiled.data):
        if len(qargs) == 2:
            gate_ids.append(idx)
            if len(gate_ids) >= int(fmax):
                break
    return gate_ids


def _cut_circuit_deterministic(compiled: QuantumCircuit, cfg: ExperimentConfig) -> Tuple[QuantumCircuit, Dict[str, Any]]:
    """
    Deterministic scheme:
      - Cut the first fmax 2Q gates using cut_gates
    """
    gate_ids = _select_first_twoq_gate_ids(compiled, fmax=int(cfg.cutting.fmax))
    if not gate_ids:
        return compiled, {"note": "no 2Q gates found to cut", "gate_ids": []}

    cut_circ, qpdbases = cut_gates(compiled, gate_ids=gate_ids, inplace=False)
    return cut_circ, {
        "gate_ids": gate_ids,
        "n_cut_gates": len(gate_ids),
        "n_qpd_bases": len(qpdbases),
    }


def _cut_circuit_automated(compiled: QuantumCircuit, cfg: ExperimentConfig) -> Tuple[QuantumCircuit, Dict[str, Any]]:
    """
    Automated scheme (robustness):
      - find_cuts with DeviceConstraints(qubits_per_subcircuit=W)
      - gate_lo=True, wire_lo=False (to avoid wire cutting blow-up)
    """
    W = _fragment_width_cap(cfg.n_qubits)
    constraints = DeviceConstraints(qubits_per_subcircuit=W)

    optimization = OptimizationParameters(
        seed=int(cfg.rep.seed_transpiler),
        gate_lo=True,
        wire_lo=False,
    )

    cut_circ, stats = find_cuts(
        compiled,
        optimization=optimization,
        constraints=constraints,
    )
    meta: Dict[str, Any] = {
        "fragment_width_cap": W,
        "optimization_seed": int(cfg.rep.seed_transpiler),
    }
    # stats is dict[str,float] per our signature
    meta["find_cuts_stats"] = dict(stats)
    return cut_circ, meta


# -------------------------
# Helper: observables to PauliList
# -------------------------
def _to_paulilist(obs_ops: Sequence[Any]) -> PauliList:
    """
    Standardize to PauliList for addon functions.
    Assumes build_observables returns SparsePauliOp-like or label-like entries.
    """
    labels: List[str] = []
    for op in obs_ops:
        if hasattr(op, "paulis"):
            # SparsePauliOp: take the first Pauli term label
            labels.append(op.paulis.to_labels()[0])
        else:
            labels.append(str(op))
    return PauliList(labels)


# -------------------------
# Main T3 entrypoint
# -------------------------
def run(cfg: ExperimentConfig) -> Dict[str, Any]:
    cfg.validate()
    if not cfg.cutting.enabled:
        raise ValueError("T3 requires cutting.enabled=True")
    if cfg.cutting.scheme not in ("deterministic", "automated"):
        raise ValueError(f"Unknown T3 cutting.scheme={cfg.cutting.scheme!r}. Use 'deterministic' or 'automated'.")

    # 1) Build + compile baseline (k=1)
    logical = build_kernel(cfg.kernel)
    cmap = coupling_map_for(cfg.topology, cfg.n_qubits, seed=7)
    compiled = compile_k1(logical, coupling_map=cmap, cfg=cfg)
    print("[DEBUG] Step 1 complete!")
    # 2) Observables
    obs_ops = build_observables(cfg.obs_policy, cfg.n_qubits, cfg.obs_cap)
    obs_paulis = _to_paulilist(obs_ops)
    print("[DEBUG] Step 2 complete!")
    # 3) Ideal reference (no noise) on compiled circuit
    ideal = estimate_expectations(cfg, compiled, obs_ops, noisy=False)
    print("[DEBUG] Step 3 complete!")
    # 4) Apply cutting transform based on scheme
    if cfg.cutting.scheme == "deterministic":
        cut_circuit, cut_meta = _cut_circuit_deterministic(compiled, cfg)
    else:
        cut_circuit, cut_meta = _cut_circuit_automated(compiled, cfg)
    print("[DEBUG] Step 4 complete!")
    # 5) Generate subexperiments + coefficients (depends on T=num_samples)
    subexperiments, coefficients = generate_cutting_experiments(
        circuits=cut_circuit,
        observables=obs_paulis,
        num_samples=int(cfg.cutting.num_samples),
    )
    subcircuits: List[QuantumCircuit] = list(subexperiments)
    print("[DEBUG] Step 5 complete!")
    # 6) Execute subexperiments under noise with Aer Estimator
    noise_model = build_noise_model(cfg)
    est = AerEstimator(
        options={
            "shots": int(cfg.shots.shots_per_exec),
            "seed_simulator": int(cfg.rep.seed_simulator),
            **({"noise_model": noise_model} if noise_model is not None else {}),
        }
    )

    t0 = time.time()
    prim_res = est.run(
        circuits=subcircuits,
        observables=[obs_paulis] * len(subcircuits),
    ).result()
    exec_time = time.time() - t0
    print("[DEBUG] Step 6 complete!")
    # 7) Reconstruct expectation values
    approx = reconstruct_expectation_values(
        results=prim_res,
        coefficients=coefficients,
        observables=obs_paulis,
    )
    approx_vec = [float(x) for x in approx]
    print("[DEBUG] Step 7 complete!")
    # 8) Metrics
    M1 = m1_mae(ideal, approx_vec)
    M2 = m2_for_technique(technique="T3", fragments=subcircuits)

    M3 = compute_m3(
        n_subexperiments=len(subcircuits),
        n_observables=len(obs_paulis),
        shots_per_exec=int(cfg.shots.shots_per_exec),
        coeff_len=len(coefficients),
        time_exec_seconds=float(exec_time),
    ).as_dict()
    print("[DEBUG] Step 8 complete!")
    return {
        "M1": float(M1),
        "M2": M2,
        "M3": M3,
        "scheme": str(cfg.cutting.scheme),
        "fmax": int(cfg.cutting.fmax),
        "num_samples": int(cfg.cutting.num_samples),
        "n_subexperiments": int(len(subcircuits)),
        "coeff_len": int(len(coefficients)),
        "cut_meta": cut_meta,
    }
