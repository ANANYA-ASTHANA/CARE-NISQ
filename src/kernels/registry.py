from __future__ import annotations

from typing import Literal

from src.kernels.qft import make_qft
from src.kernels.hea import make_hea
from src.kernels.grover import make_grover_block

KernelName = Literal["QFT12", "HEA10", "Grover10"]


def build_kernel(name: KernelName):
    """
    Canonical kernels used in CARE-NISQ.
    """
    if name == "QFT12":
        return make_qft(n=12, do_swaps=False)
    if name == "HEA10":
        return make_hea(n=10, layers=6)
    if name == "Grover10":
        return make_grover_block(n=10, iters=2)

    raise ValueError(f"Unknown kernel '{name}'. Expected one of: QFT12, HEA10, Grover10.")
