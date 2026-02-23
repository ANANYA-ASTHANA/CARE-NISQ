from __future__ import annotations

from qiskit.circuit.library import QFT


def make_qft(n: int = 12, do_swaps: bool = False):
    """
    QFT kernel.
    Lock do_swaps explicitly for consistency across all experiments.
    """
    qc = QFT(n, do_swaps=do_swaps).decompose()
    qc.name = f"QFT_{n}"
    return qc
