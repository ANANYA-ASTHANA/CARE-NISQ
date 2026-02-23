from __future__ import annotations

from qiskit import QuantumCircuit


def make_hea(n: int = 10, layers: int = 6):
    """
    Simple HEA: (RZ,SX,RZ on each qubit) + entangling brickwork.
    Parameters are fixed placeholders; can make symbolic later if needed.
    """
    qc = QuantumCircuit(n, name=f"HEA_{n}_L{layers}")

    for l in range(layers):
        for q in range(n):
            qc.rz(0.1 * (l + 1), q)
            qc.sx(q)
            qc.rz(0.2 * (l + 1), q)

        # Entanglers: nearest-neighbor chain (logical); physical mapping handled by transpile
        start = 0 if (l % 2 == 0) else 1
        for q in range(start, n - 1, 2):
            qc.cx(q, q + 1)

    return qc
