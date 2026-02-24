from __future__ import annotations

import csv
import json
import math
import pathlib
from dataclasses import replace
from typing import Any, Dict, List, Tuple, Optional

from src.config import (
    ExperimentConfig,
    build_stress_set_for_calibration,
    _read_yaml,  # internal helper is fine to reuse inside repo
)
from src.techniques import t3


def _ensure_dir(path: str | pathlib.Path) -> pathlib.Path:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _default_T_candidates() -> List[int]:
    # Conservative, log-scale-ish sweep
    return [50, 100, 200, 400, 800]


def _load_T_candidates(base_cfg_path: str) -> List[int]:
    base = _read_yaml(base_cfg_path)
    cands = base.get("T_candidates", None)
    if cands is None:
        return _default_T_candidates()
    # sanitize
    out = []
    for x in cands:
        try:
            xi = int(x)
            if xi > 0:
                out.append(xi)
        except Exception:
            continue
    return out if out else _default_T_candidates()


def _stress_key(cfg: ExperimentConfig) -> Tuple[Any, ...]:
    # Group by stress-point identity (replicate varies under cfg.rep)
    return (
        cfg.kernel,
        cfg.topology,
        float(cfg.depth.multiplier),
        float(cfg.noise.level),
        int(cfg.cutting.fmax),
    )


def _ci_halfwidth_95(values: List[float]) -> float:
    """Normal-approx 95% CI half-width; adequate for R=3 in calibration context."""
    n = len(values)
    if n <= 1:
        return float("inf")
    mu = sum(values) / n
    var = sum((x - mu) ** 2 for x in values) / (n - 1)
    sd = math.sqrt(var)
    return 1.96 * sd / math.sqrt(n)


def _passes_stability(
    m1_values: List[float],
    *,
    eps_abs: float,
    eps_rel: float,
    floor: float = 1e-9,
) -> Dict[str, Any]:
    """
    Decide whether a stress point is 'stable enough' at a given T.
    - eps_abs: absolute CI halfwidth threshold
    - eps_rel: relative CI halfwidth threshold w.r.t. mean magnitude
    """
    mu = sum(m1_values) / len(m1_values)
    hw = _ci_halfwidth_95(m1_values)
    rel = hw / max(abs(mu), floor)
    ok = (hw <= eps_abs) or (rel <= eps_rel)
    return {"mean": mu, "ci_halfwidth_95": hw, "rel_halfwidth": rel, "ok": ok}


def run():
    """
    Stress-set calibration for cutting sampling budget (T = num_samples).
    Produces:
      - results/calibration.json
      - results/calibration_trials.csv (optional but recommended)
    """

    base_cfg_path = "configs/base.yaml"
    main_cfg_path = "configs/experiments_robustness.yaml"

    # --- thresholds (can later be moved to base.yaml) ---
    # Interpretation: we want M1 to be stable across simulator-seed replicates.
    # Keep these conservative; tighten later once M1 definition is finalized.
    eps_abs = 0.02   # absolute 95% CI halfwidth
    eps_rel = 0.05   # OR relative 95% CI halfwidth (5%)

    T_candidates = _load_T_candidates(base_cfg_path)

    stress_cfgs = build_stress_set_for_calibration(
        base_cfg_path=base_cfg_path,
        main_cfg_path=main_cfg_path,
    )

    print(f"[calibrate] Stress configs: {len(stress_cfgs)} (includes replicates)")
    print(f"[calibrate] T candidates: {T_candidates}")
    print(f"[calibrate] Stability thresholds: eps_abs={eps_abs}, eps_rel={eps_rel}")

    # DEBUG
    print("Calibration stress configs seeds:")
    for c in stress_cfgs[:10]:
        print(c.kernel, c.topology, c.rep.replicate_id, c.rep.seed_transpiler, c.rep.seed_simulator)

    # Output files
    json_out = _ensure_dir("results/calibration.json")
    csv_out = _ensure_dir("results/calibration_trials.csv")

    # CSV header
    csv_rows: List[Dict[str, Any]] = []

    chosen_T: Optional[int] = None
    chosen_summary: Dict[str, Any] = {}

    # Pre-group stress points so we can enforce "all stress points stable"
    stress_points = sorted(set(_stress_key(c) for c in stress_cfgs))

    for T in T_candidates:
        # Collect per stress-point replicate M1 values
        per_point: Dict[Tuple[Any, ...], List[float]] = {k: [] for k in stress_points}

        print(f"\n[calibrate] Testing T={T} ...")

        for cfg in stress_cfgs:
            cfgT = replace(cfg, cutting=replace(cfg.cutting, num_samples=int(T)))
            cfgT.validate()

            # Calibration uses T3 only by design
            out = t3.run(cfgT)

            if "M1" not in out or out["M1"] is None:
                raise RuntimeError(
                    "Calibration requires technique T3 to return a numeric 'M1'. "
                    "Currently got missing/None. Implement M1 in T3 before calibration."
                )

            m1 = float(out["M1"])
            key = _stress_key(cfgT)
            per_point[key].append(m1)

            csv_rows.append(
                {
                    "T": T,
                    "kernel": cfgT.kernel,
                    "topology": cfgT.topology,
                    "depth_mult": float(cfgT.depth.multiplier),
                    "noise_level": float(cfgT.noise.level),
                    "fmax": int(cfgT.cutting.fmax),
                    "replicate_id": int(cfgT.rep.replicate_id),
                    "seed_transpiler": int(cfgT.rep.seed_transpiler),
                    "seed_simulator": int(cfgT.rep.seed_simulator),
                    "M1": m1,
                }
            )

        # Evaluate stability for this T across all stress points
        point_summaries: Dict[str, Any] = {}
        all_ok = True

        for k in stress_points:
            vals = per_point[k]
            if len(vals) < 2:
                all_ok = False
                summary = {"ok": False, "reason": "insufficient replicates", "values": vals}
            else:
                summary = _passes_stability(vals, eps_abs=eps_abs, eps_rel=eps_rel)
                summary["values"] = vals

            point_summaries[str(k)] = summary
            if not summary.get("ok", False):
                all_ok = False

        print(f"[calibrate] T={T} pass={all_ok}")

        if all_ok and chosen_T is None:
            chosen_T = T
            chosen_summary = {
                "T_global": chosen_T,
                "eps_abs": eps_abs,
                "eps_rel": eps_rel,
                "stress_points": point_summaries,
                "T_candidates": T_candidates,
            }
            # Smallest T that passes is selected; stop early.
            break

    # If nothing passed, choose max T and record summaries for last run
    if chosen_T is None:
        chosen_T = max(T_candidates)
        chosen_summary = {
            "T_global": chosen_T,
            "eps_abs": eps_abs,
            "eps_rel": eps_rel,
            "warning": "No candidate passed stability thresholds; using max(T_candidates).",
            "T_candidates": T_candidates,
        }
        print(f"[calibrate] WARNING: no T passed; selecting T_global={chosen_T}")

    # Write outputs
    json_out.write_text(json.dumps(chosen_summary, indent=2), encoding="utf-8")
    print(f"[calibrate] Wrote {json_out}")

    with csv_out.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "T",
            "kernel",
            "topology",
            "depth_mult",
            "noise_level",
            "fmax",
            "replicate_id",
            "seed_transpiler",
            "seed_simulator",
            "M1",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(csv_rows)
    print(f"[calibrate] Wrote {csv_out}")

    print(f"[calibrate] Done. Selected T_global={chosen_T}")
