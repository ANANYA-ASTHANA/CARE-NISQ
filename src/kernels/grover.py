from __future__ import annotations

from qiskit import QuantumCircuit


def make_grover_block(n: int = 10, iters: int = 2):
    """
    Minimal Grover-style block: oracle (phase flip on |11..1>) + diffusion.
    Uses MCX (decomposes heavily; acceptable since D_base is measured post-transpile).
    """
    qc = QuantumCircuit(n, name=f"Grover_{n}_I{iters}")

    def oracle(qc_: QuantumCircuit):
        qc_.h(n - 1)
        qc_.mcx(list(range(n - 1)), n - 1)  # multi-controlled X
        qc_.h(n - 1)

    def diffusion(qc_: QuantumCircuit):
        qc_.h(range(n))
        qc_.x(range(n))
        qc_.h(n - 1)
        qc_.mcx(list(range(n - 1)), n - 1)
        qc_.h(n - 1)
        qc_.x(range(n))
        qc_.h(range(n))

    for _ in range(iters):
        oracle(qc)
        diffusion(qc)

    return qc
