from __future__ import annotations

from typing import Any, Dict, List, Optional

from qiskit import QuantumCircuit


def _count_2q_ops(qc: QuantumCircuit) -> int:
    """
    Count 2-qubit operations robustly (not only 'cx').
    This stays valid even if other 2Q ops appear transiently.
    """
    n2 = 0
    for inst, qargs, _cargs in qc.data:
        if len(qargs) == 2:
            n2 += 1
    return int(n2)


def circuit_complexity(qc: QuantumCircuit) -> Dict[str, Any]:
    """
    M2 for a single (full) circuit: depth + size + 2Q count + CX count + gate histogram.
    Used for T1/T2.
    """
    ops = qc.count_ops()
    return {
        "depth": int(qc.depth()),
        "size": int(qc.size()),
        "twoq": int(_count_2q_ops(qc)),
        "cx": int(ops.get("cx", 0)),
        "ops": {str(k): int(v) for k, v in ops.items()},
    }


def fragments_complexity(fragments: List[QuantumCircuit]) -> Dict[str, Any]:
    """
    M2 for cutting-based techniques (T3/T4): fragment-level complexity summary.
    This aligns M2 with the *unit of execution* for cutting (fragments, not the full circuit).
    """
    if not fragments:
        return {
            "n_fragments": 0,
            "frag_depth_max": 0,
            "frag_depth_mean": 0.0,
            "frag_size_total": 0,
            "frag_size_max": 0,
            "frag_size_mean": 0.0,
            "frag_twoq_total": 0,
            "frag_twoq_max": 0,
            "frag_twoq_mean": 0.0,
            "frag_cx_total": 0,
            "frag_cx_max": 0,
            "frag_cx_mean": 0.0,
        }

    depths = [int(f.depth()) for f in fragments]
    sizes = [int(f.size()) for f in fragments]
    twoqs = [int(_count_2q_ops(f)) for f in fragments]
    cxs = [int(f.count_ops().get("cx", 0)) for f in fragments]
    n = len(fragments)

    return {
        "n_fragments": int(n),

        # Depth (critical-path proxy)
        "frag_depth_max": int(max(depths)),
        "frag_depth_mean": float(sum(depths) / n),

        # Gate volume
        "frag_size_total": int(sum(sizes)),
        "frag_size_max": int(max(sizes)),
        "frag_size_mean": float(sum(sizes) / n),

        # 2Q pressure (noise/time hotspot indicator)
        "frag_twoq_total": int(sum(twoqs)),
        "frag_twoq_max": int(max(twoqs)),
        "frag_twoq_mean": float(sum(twoqs) / n),

        # CX-specific (since we compile to rz/sx/x/cx)
        "frag_cx_total": int(sum(cxs)),
        "frag_cx_max": int(max(cxs)),
        "frag_cx_mean": float(sum(cxs) / n),
    }


def m2_for_technique(
    *,
    technique: str,
    compiled_circuit: Optional[QuantumCircuit] = None,
    fragments: Optional[List[QuantumCircuit]] = None,
) -> Dict[str, Any]:
    """
    Single entrypoint so technique files can call one function consistently.

    - For T1/T2: pass compiled_circuit
    - For T3/T4: pass fragments
    """
    tech = technique.strip().upper()

    if tech in ("T1", "T2"):
        if compiled_circuit is None:
            raise ValueError(f"M2 for {tech} requires compiled_circuit")
        out = circuit_complexity(compiled_circuit)
        out["scope"] = "full_circuit"
        return out

    if tech in ("T3", "T4"):
        if fragments is None:
            raise ValueError(f"M2 for {tech} requires fragments")
        out = fragments_complexity(fragments)
        out["scope"] = "fragments"
        return out

    raise ValueError(f"Unknown technique '{tech}' for M2 computation")
