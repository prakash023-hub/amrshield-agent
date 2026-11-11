# Hierarchical Bayesian Pharmacokinetic Modeling
### A Python-based open-source framework for deterministic vs stochastic PK analysis

---

## Overview

This repository provides a complete, reproducible Python workflow comparing:
- **Deterministic** nonlinear least-squares (NLS/curve_fit) PK modeling
- **Bayesian single-subject** PK modeling (PyMC)
- **Hierarchical Bayesian population** PK modeling (PyMC)

Applied to the classic **Theophylline** oral PK dataset (12 subjects).

---

## Dataset

**Theophylline** — 12 subjects received a single oral dose; plasma concentrations  
measured at 11 time points each (132 observations total).

Source: Pinheiro & Bates (1995), available via R datasets.

---

## Model

One-compartment oral absorption model:

```
C(t) = (Dose × ka) / (V × (ka − ke)) × (e^(−ke×t) − e^(−ka×t))
```

Parameters:
| Symbol | Description | Units |
|--------|-------------|-------|
| ka | Absorption rate constant | h⁻¹ |
| ke | Elimination rate constant | h⁻¹ |
| V  | Volume of distribution | L/kg |

---

## Repository Structure

```
├── pk_modeling.py          # Main analysis script (all steps)
├── requirements.txt        # Python dependencies
├── README.md
└── outputs/
    ├── fig1_single_subject_comparison.png
    ├── fig2_posterior_distributions.png
    ├── fig3_trace_plots.png
    ├── fig4_all_subjects_deterministic.png
    ├── fig5_forest_plot.png
    ├── fig6_vpc.png
    ├── fig7_parameter_comparison.png
    └── table1_parameter_estimates.csv
```

---

## Installation

```bash
# Create virtual environment (recommended)
python -m venv pk_env
source pk_env/bin/activate   # Windows: pk_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
python pk_modeling.py
```

Or open as a Jupyter notebook and run cell by cell.

---

## Outputs

| Figure | Description |
|--------|-------------|
| Fig 1 | Single-subject: deterministic vs Bayesian posterior predictive |
| Fig 2 | Posterior distributions of ka, ke, V, sigma |
| Fig 3 | MCMC trace plots (convergence diagnostics) |
| Fig 4 | Deterministic NLS fits for all 12 subjects |
| Fig 5 | Forest plot of individual PK parameters (95% HDI) |
| Fig 6 | Visual Predictive Check (VPC) |
| Fig 7 | Side-by-side NLS vs Bayesian parameter estimates |
| Table 1 | Parameter estimates with 95% credible intervals |

---

## Citation

If you use this code in your research, please cite:

> [Authors]. A Python-based open-source framework for hierarchical Bayesian 
> pharmacokinetic modeling: a tutorial using Theophylline. [Journal], [Year].

---

## License

MIT License — free to use, modify, and distribute with attribution.
