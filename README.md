# CARE-NISQ  
## Constraint-Aware Regime Evaluation for NISQ Systems

CARE-NISQ is a structured experimental framework for systematically evaluating quantum circuit execution regimes under interacting compilation, connectivity, noise, and resource constraints.

This repository contains the full experimental framework, implementation, and reproducibility artifacts for a systematic study of compilation- and mitigation-aware execution regimes in noisy intermediate-scale quantum (NISQ) systems.

We compare four technique pipelines:

- **T1** – Baseline SABRE routing  
- **T2** – Enhanced routing (best-of-k selection)  
- **T3** – QPD-based circuit cutting with classical reconstruction  
- **T4** – Circuit cutting with zero-noise extrapolation (ZNE)  

The study evaluates correctness, complexity, sampling overhead, and estimator stability across:

- Three canonical algorithmic kernels (QFT, HEA, Grover)
- Multiple connectivity topologies (line, grid, sparse)
- Controlled depth budgets
- Parametric noise levels

---

## Core Metrics

- **M1** – Observable-based correctness (ideal-referenced)
- **M2** – Depth and two-qubit gate inflation
- **M3** – Effective sampling overhead
- **M4** – Variance / estimator stability

---

## Repository Structure

- `src/` – Core implementation (kernels, routing, cutting, mitigation, metrics)
- `configs/` – Experimental definitions and parameters
- `results/` – Raw and processed outputs
- `plots/` – Generated figures
- `paper/` – LaTeX manuscript source
- `docs/` – Methodology notes and reproducibility documentation

---

## Installation

### Option A: Conda (Recommended)

```bash
conda env create -f environment.yaml
conda activate care-nisq
```

### Option B: pip

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Reproducibility Workflow

### 1. Calibrate cutting sampling budget

```bash
python -m src.cli calibrate
```

### 2. Run full experimental grid

```bash
python -m src.cli run-main
```

### 3. Run robustness subsets

```bash
python -m src.cli run-robustness
```

### 4. Generate summaries and plots

```bash
python -m src.cli summarize
python -m src.cli plot
```

---

## License

MIT License — see `LICENSE`.

---

## Citation

If you use this repository, please cite it via the metadata provided in `CITATION.cff`.

---

## Research Intent

This project investigates *regime boundaries* between routing, circuit cutting, and mitigation strategies under realistic constraint interactions — rather than optimizing any single technique in isolation.

The goal is to provide principled guidance for execution strategy selection under connectivity, noise, and depth limitations.
