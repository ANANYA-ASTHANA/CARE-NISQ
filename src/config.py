from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal
import json
import pathlib

import yaml


TechniqueName = Literal["T1", "T2", "T3", "T4"]
KernelName = Literal["QFT12", "HEA10", "Grover10"]
TopologyName = Literal["line", "grid", "sparse"]
CutScheme = Literal["none", "heuristic", "optimized"]
ZNEModel = Literal["none", "linear", "richardson"]


@dataclass(frozen=True)
class RoutingSpec:
    layout_method: str = "sabre"
    routing_method: str = "sabre"
    optimization_level: int = 1
    basis_gates: Tuple[str, ...] = ("rz", "sx", "x", "cx")

    # T2: best-of-k routing
    best_of_k: int = 1  # T1=1, T2=5
    objective: Tuple[str, str] = ("depth", "twoq_count")  # lexicographic objective

    def validate(self) -> None:
        if self.best_of_k < 1:
            raise ValueError("RoutingSpec.best_of_k must be >= 1")
        if self.optimization_level not in (0, 1, 2, 3):
            raise ValueError("RoutingSpec.optimization_level must be 0..3")
        if len(self.basis_gates) == 0:
            raise ValueError("RoutingSpec.basis_gates cannot be empty")


@dataclass(frozen=True)
class CuttingSpec:
    enabled: bool = False
    scheme: CutScheme = "none"
    fmax: int = 0                      # max cuts (level axis)
    qmin: int = 3                      # min qubits per fragment (global lock)
    num_samples: int = 0               # T_global after calibration

    def validate(self) -> None:
        if self.enabled:
            if self.scheme not in ("heuristic", "optimized"):
                raise ValueError("CuttingSpec.scheme must be 'heuristic' or 'optimized' when enabled")
            if self.fmax not in (2, 4):
                raise ValueError("CuttingSpec.fmax must be one of {2,4} (locked)")
            if self.qmin != 3:
                raise ValueError("CuttingSpec.qmin is locked to 3")
            if self.num_samples <= 0:
                raise ValueError("CuttingSpec.num_samples must be > 0 when cutting is enabled")
        else:
            # enforce consistency
            if self.scheme != "none":
                raise ValueError("CuttingSpec.scheme must be 'none' when cutting is disabled")


@dataclass(frozen=True)
class ZNESpec:
    enabled: bool = False
    model: ZNEModel = "none"
    scales: Tuple[float, ...] = (1.0, 2.0, 3.0)

    def validate(self) -> None:
        if self.enabled:
            if self.model not in ("linear", "richardson"):
                raise ValueError("ZNESpec.model must be 'linear' or 'richardson' when enabled")
            if len(self.scales) < 2:
                raise ValueError("ZNESpec.scales must have at least 2 scale factors when enabled")
            if any(s < 1.0 for s in self.scales):
                raise ValueError("ZNESpec.scales must be >= 1.0")
        else:
            if self.model != "none":
                raise ValueError("ZNESpec.model must be 'none' when ZNE is disabled")


@dataclass(frozen=True)
class NoiseSpec:
    model: str = "depolarizing"
    level: float = 1e-3  # noise parameter p

    def validate(self) -> None:
        if self.level <= 0:
            raise ValueError("NoiseSpec.level must be > 0")
        if self.model.strip() == "":
            raise ValueError("NoiseSpec.model cannot be empty")


@dataclass(frozen=True)
class DepthSpec:
    multiplier: float = 1.5  # e.g., 1.5x D_base

    def validate(self) -> None:
        if self.multiplier <= 0:
            raise ValueError("DepthSpec.multiplier must be > 0")


@dataclass(frozen=True)
class ShotSpec:
    shots_per_exec: int = 2048  # per executed circuit

    def validate(self) -> None:
        if self.shots_per_exec <= 0:
            raise ValueError("ShotSpec.shots_per_exec must be > 0")


@dataclass(frozen=True)
class ReplicationSpec:
    replicate_id: int = 1

    # Controls SABRE/layout stochasticity (passed to transpile(seed_transpiler=...))
    seed_transpiler: int = 11

    # Controls Aer sampling stochasticity (passed to AerSampler/run(seed_simulator=...))
    seed_simulator: int = 11

    R_total: int = 1

    def validate(self) -> None:
        if self.replicate_id < 1:
            raise ValueError("ReplicationSpec.replicate_id must be >= 1")
        if self.R_total < 1:
            raise ValueError("ReplicationSpec.R_total must be >= 1")


@dataclass(frozen=True)
class ExperimentConfig:
    """
    One fully-specified configuration = one row-group (over R replicates).
    Each replicate is represented by the same config + different ReplicationSpec.
    """
    # Identity
    kernel: KernelName
    topology: TopologyName
    n_qubits: int

    # Core constraints
    depth: DepthSpec
    noise: NoiseSpec

    # Technique
    technique: TechniqueName
    routing: RoutingSpec = field(default_factory=RoutingSpec)
    cutting: CuttingSpec = field(default_factory=CuttingSpec)
    zne: ZNESpec = field(default_factory=ZNESpec)

    # Resource knobs
    shots: ShotSpec = field(default_factory=ShotSpec)

    # Observables
    obs_policy: str = "local_Z_ZZ"
    obs_cap: int = 20

    # Replication
    rep: ReplicationSpec = field(default_factory=ReplicationSpec)

    # Misc
    tags: Tuple[str, ...] = ()

    def validate(self) -> None:
        # Kernel/qubits sanity
        if self.kernel == "QFT12" and self.n_qubits != 12:
            raise ValueError("QFT12 must have n_qubits=12")
        if self.kernel in ("HEA10", "Grover10") and self.n_qubits != 10:
            raise ValueError(f"{self.kernel} must have n_qubits=10")

        # Validate sub-specs
        self.depth.validate()
        self.noise.validate()
        self.routing.validate()
        self.cutting.validate()
        self.zne.validate()
        self.shots.validate()
        self.rep.validate()

        # Technique-specific consistency
        if self.technique in ("T1", "T2"):
            if self.cutting.enabled or self.zne.enabled:
                raise ValueError(f"{self.technique} must not enable cutting or ZNE")
        if self.technique == "T3":
            if not self.cutting.enabled or self.zne.enabled:
                raise ValueError("T3 must enable cutting and disable ZNE")
        if self.technique == "T4":
            if not self.cutting.enabled or not self.zne.enabled:
                raise ValueError("T4 must enable cutting and ZNE")

        # T2 best-of-k lock
        if self.technique == "T2" and self.routing.best_of_k != 5:
            raise ValueError("T2 routing.best_of_k must be 5 (locked)")
        if self.technique == "T1" and self.routing.best_of_k != 1:
            raise ValueError("T1 routing.best_of_k must be 1 (locked)")

        # ZNE main grid lock (optional: relax in robustness subset via tags)
        if self.zne.enabled and self.zne.model == "linear":
            if self.zne.scales != (1.0, 2.0, 3.0) and ("robustness" not in self.tags):
                raise ValueError("Main grid ZNE scales locked to (1,2,3); use tags=('robustness',) to override")

        # Observables lock
        if self.obs_policy != "local_Z_ZZ":
            raise ValueError("obs_policy locked to 'local_Z_ZZ'")
        if self.obs_cap != 20:
            raise ValueError("obs_cap locked to 20")

    def to_json(self) -> str:
        # Useful for logging run metadata
        return json.dumps(asdict(self), indent=2, default=str)


# ----------------------------
# YAML loader helpers
# ----------------------------

def _read_yaml(path: str | pathlib.Path) -> Dict[str, Any]:
    p = pathlib.Path(path)
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _require(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise KeyError(f"Missing required config key: '{key}'")
    return d[key]


def build_configs_for_main_grid(
    base_cfg_path: str,
    main_cfg_path: str,
    calibration_json_path: Optional[str] = None,
) -> List[ExperimentConfig]:
    """
    Builds the list of ExperimentConfig objects for main grid runs.
    """
    base = _read_yaml(base_cfg_path)
    main = _read_yaml(main_cfg_path)

    # Load calibrated T_global if provided
    T_global = None
    if calibration_json_path:
        p = pathlib.Path(calibration_json_path)
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                T_global = json.load(f).get("T_global")

    kernels: List[str] = _require(main, "kernels")
    topologies: List[str] = _require(main, "topologies")
    depth_multipliers: List[float] = _require(main, "depth_multipliers")
    noise_levels: List[float] = _require(main, "noise_levels")
    fmax_levels: List[int] = _require(main, "fmax_levels")
    techniques: List[str] = _require(main, "techniques")
    R_total: int = int(_require(main, "R_total"))

    # Shots per kernel
    shots_by_kernel: Dict[str, int] = _require(main, "shots_per_kernel")

    # Seeds list
    seeds: List[int] = _require(main, "seeds")
    seed_transpiler_fixed = int(seeds[0])  # fixed for all runs (main grid consistency)
  
    num_samples_default = int(base.get("num_samples_default", 0))
  
    configs: List[ExperimentConfig] = []

    for k in kernels:
        n = 12 if k == "QFT12" else 10
        for topo in topologies:
            for alpha in depth_multipliers:
                for p in noise_levels:
                    for fmax in fmax_levels:
                        for tech in techniques:
                            for r_idx in range(1, R_total + 1):
                                seed_sim = int(seeds[r_idx - 1])  # varies across replicates
                                routing = RoutingSpec(
                                    best_of_k=5 if tech == "T2" else 1
                                )

                                cutting_enabled = tech in ("T3", "T4")
                                zne_enabled = tech == "T4"

                                # num_samples only matters for cutting
                                if cutting_enabled:
                                    if T_global is not None:
                                        ns = int(T_global)
                                    else:
                                        ns = num_samples_default
                                    if ns <= 0:
                                        raise ValueError(
                                            "Cutting enabled but no calibrated T_global found and "
                                            "num_samples_default is not set (>0). Run calibration first."
                                        )
                                else:
                                    ns = 0

                                cutting = CuttingSpec(
                                    enabled=cutting_enabled,
                                    scheme="optimized" if cutting_enabled else "none",
                                    fmax=fmax if cutting_enabled else 0,
                                    qmin=3,
                                    num_samples=ns,
                                )

                                zne = ZNESpec(
                                    enabled=zne_enabled,
                                    model="linear" if zne_enabled else "none",
                                    scales=(1.0, 2.0, 3.0),
                                )

                                cfg = ExperimentConfig(
                                    kernel=k,  # type: ignore
                                    topology=topo,  # type: ignore
                                    n_qubits=n,
                                    depth=DepthSpec(multiplier=float(alpha)),
                                    noise=NoiseSpec(model=base.get("noise_model", "depolarizing"), level=float(p)),
                                    technique=tech,  # type: ignore
                                    routing=routing,
                                    cutting=cutting,
                                    zne=zne,
                                    rep=ReplicationSpec(
                                       replicate_id=r_idx,
                                       seed_transpiler=seed_transpiler_fixed,
                                       seed_simulator=seed_sim,
                                       R_total=R_total,
                                    ),
                                    obs_policy="local_Z_ZZ",
                                    obs_cap=20,
                                    tags=(),
                                )
                                cfg.validate()
                                configs.append(cfg)

    return configs


def build_stress_set_for_calibration(
    base_cfg_path: str,
    main_cfg_path: str,
) -> List[ExperimentConfig]:
    """
    Builds the stress set configs for calibration.
    We vary only sampling seeds (replicates) to measure stability, not to produce per-seed T values.
    Output: list of configs (stress points × R replicates).
    """
    base = _read_yaml(base_cfg_path)
    main = _read_yaml(main_cfg_path)

    # Locked stress set specs
    stress = [
        ("QFT12", "line", 2.0, 1e-3, 4),
        ("QFT12", "sparse", 2.0, 1e-3, 4),
        ("HEA10", "line", 2.0, 1e-3, 4),
        ("Grover10", "line", 2.0, 1e-3, 4),
    ]

    shots_by_kernel: Dict[str, int] = _require(main, "shots_per_kernel")
    seeds: List[int] = _require(main, "seeds")

    # Calibration replicate count
    R_cal = min(3, len(seeds))
    calib_seeds = seeds[:R_cal]

    out: List[ExperimentConfig] = []
  
    for (k, topo, alpha, p, fmax) in stress:
        n = 12 if k == "QFT12" else 10

        for ridx, s in enumerate(calib_seeds, start=1):
            cfg = ExperimentConfig(
                kernel=k,  # type: ignore
                topology=topo,  # type: ignore
                n_qubits=n,
                depth=DepthSpec(multiplier=alpha),
                noise=NoiseSpec(model=base.get("noise_model", "depolarizing"), level=p),

                # Calibration runs cutting only; ZNE not needed to calibrate T
                technique="T3",

                # IMPORTANT: for fairness we locked T3/T4 to baseline routing k=1
                routing=RoutingSpec(best_of_k=1),

                # num_samples is a placeholder here; calibration runner overwrites it per candidate T
                cutting=CuttingSpec(enabled=True, scheme="optimized", fmax=fmax, qmin=3, num_samples=1),

                zne=ZNESpec(enabled=False, model="none"),
                shots=ShotSpec(shots_per_exec=int(shots_by_kernel[k])),

                rep=ReplicationSpec(
                    replicate_id=ridx,
                    seed_transpiler=int(calib_seeds[0]),  # keep transpiler seed fixed for calibration
                    seed_simulator=int(s),
                    R_total=R_cal,
                ),

                obs_policy="local_Z_ZZ",
                obs_cap=20,
                tags=("calibration",),
            )

            # Do NOT call cfg.validate() here because cutting.num_samples=1 is a placeholder.
            # The calibration runner will set a candidate num_samples and validate before running.
            out.append(cfg)

    return out
