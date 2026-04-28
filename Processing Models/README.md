# Lithium Supply Chain Technoeconomic Model — Replication Code and Data

Supplementary materials for:

> Economic and environmental implications of onshoring US lithium production
> a working paper in the dissertation "Building Secure and Competitive Clean Technology Supply Chains: Technology and Policy Options for Electric Vehicle Batteries and Critical Minerals"
> Anthony L. Cheng, Carnegie Mellon University, 2026

This repository contains the source code and input data for a process-based technoeconomic assessment (TEA) and environmental impact model of lithium carbonate (Li₂CO₃) production. The model compares three projects across distinct resource pathways:

| Project | Location | Pathway | Nameplate Capacity |
|---|---|---|---|
| Silver Peak | Nevada, USA | Brine evaporation | ~6,000 t Li₂CO₃/yr |
| Thacker Pass | Nevada, USA | Clay — sulfuric acid leach | ~66,000 t Li₂CO₃/yr |
| Jianxiawo | Jiangxi, China | Lepidolite — sulfate roast + water leach | ~46,000 t LCE/yr |


## Model Architecture

The model uses a four-level hierarchy:

```
Supply Chain
 └── Facility (co-located production steps, shared location context)
      └── Production Step (mass/energy transformation with material flows)
           └── Machine Block (equipment sizing, costing, and impact factors)
```

Each **production step** defines a primary input → process unit → primary output transformation, with secondary inputs (reagents, utilities) and secondary outputs (byproducts, wastes, emissions). Equipment sizing, capital cost, labor, and operating cost are handled by the associated **machine block**. **Facilities** aggregate steps in series/parallel and apply location-specific parameters (electricity grid mix, labor rates, material costs). **Transportation routes** connect facilities with mode-specific cost and emission intensities.

All machine blocks and production steps carry three scenario tiers — conservative, midpoint, and optimistic — enabling parametric sensitivity analysis, tornado plots, and scenario comparison.

For full methodological details, see Appendix C of the dissertation.


## Repository Structure

```
├── README.md                    # This file
│
├── run_scenarios.py             # Entry point — project selection, scenario runs, plotting
├── supply_chain.py              # SupplyChain class: network of facilities + transport
├── facility.py                  # Facility class: step aggregation, tailings, sinks
├── production_step.py           # ProductionStep class: mass/energy balance, costing
├── transportation.py            # Transportation and TransportRoute classes
├── helpers.py                   # Data loading, plotting, scenario utilities
│
├── data/                        # Input data directory (CSV files)
│   ├── Project-Specific Data.csv
│   ├── Machine Blocks Data.csv
│   ├── Locational Data.csv
│   ├── Material Data.csv
│   ├── Transportation Data.csv
│   └── [Pathway].csv            # One file per pathway (e.g., "Brine-Evaporation.csv",
│                                #   "Sulfuric Acid Leach.csv", etc.)
│
└── C-Appendix.tex               # Appendix C LaTeX source (methodology + block derivations)
```


## Data Files

| File | Description |
|---|---|
| `Project-Specific Data.csv` | Per-project parameters: production volumes, pathway assignments, chemical compositions, transport distances, and conversion factors for 35 projects (3 actively modeled). |
| `Machine Blocks Data.csv` | Equipment-level parameters for 23 active machine blocks: base volumes, scaling exponents, equipment pricing, labor, utilities, footprint, and process availability — each with conservative/midpoint/optimistic tiers. |
| `Locational Data.csv` | Location-specific cost and impact factors: electricity prices and grid emission intensities, labor rates, water costs, material cost overrides, and utility impact factors across 8 regions. |
| `Material Data.csv` | Reagent and consumable unit costs and environmental impact factors (CO₂, SO₂, etc.). |
| `Transportation Data.csv` | Mode-specific cost and emission intensities for road, rail, and marine freight. |
| `[Pathway].csv` | Step-by-step process definitions for each pathway: material flows (inputs, reagents, outputs), conversion factors, machine block assignments, and step sequencing. |

These data files are aggregated into one xlsx file (`Master Data File.xlsx`), from which csvs can be separated. 

## Requirements

**Python 3.9+** with the following packages:

- `numpy`
- `pandas`
- `matplotlib`

No other dependencies are required. Install with:

```bash
pip install numpy pandas matplotlib
```

## Usage

### Basic Run

From the repository root:

```bash
python run_scenarios.py
```

By default, this evaluates the project(s) specified in the `projects` list near the bottom of `run_scenarios.py` (line ~943). To change which project is evaluated, edit that list:

```python
# Pick project(s) — uncomment one line:
projects = ["Silver Peak"]
# projects = ["Thacker Pass"]
# projects = ["Jianxiawo"]
# projects = ["Jianxiawo", "Silver Peak", "Thacker Pass"]
```

### Configuration Options

Several flags near the bottom of `run_scenarios.py` (lines ~950–965) control output:

| Variable | Values | Effect |
|---|---|---|
| `detail` | `1` | Summary statistics only |
| | `2` | + Step-level production volumes and costs |
| | `2.5` | + Comparison metrics vs. published literature |
| | `3` | + Reagents, utilities, labor, impacts at each step |
| | `4` | + Detailed reagent usage and utility breakdowns |
| | `"tp_debug"` | Thacker Pass–specific debug output |
| `plot` | `0` | No plots |
| | `1` | Aggregated cost and emission bar charts |
| | `2` | Step-by-step breakdown charts |
| | `2.1` / `2.2` | Aggregated step charts for Thacker Pass / Jianxiawo |
| | `3` | Tornado sensitivity plots |
| `write` | `False` | No CSV output |
| | `True` | Write scenario results to CSV |
| | N (e.g. `3` or `5`) | Write top-N restricted sensitivity scenarios |

### A Note on Code Quality

`run_scenarios.py` is a research script, not production software. It contains commented-out lines, hardcoded workarounds (clearly marked with comments like "jank workaround"), and plotting configurations tuned for dissertation figures. The core model classes (`supply_chain.py`, `facility.py`, `production_step.py`, `transportation.py`) are more structured, but the overall codebase reflects the iterative reality of dissertation research. It works, and its outputs are the basis for all results reported in the dissertation — but it is not yet written with external usability as a primary goal.


## Reproducing Dissertation Results

To reproduce the main results reported in the dissertation:

1. Ensure all data files are in the `./data/` directory.
2. Set `projects = ["Jianxiawo", "Silver Peak", "Thacker Pass"]` in `run_scenarios.py`.
3. Run with `detail=2` and `plot=1` to generate key summary outputs and figures. (Silver Peak does not include a wastewater treatment sink; comment out lines 1378–1379 of supply_chain.py when running that project.)
4. For tornado sensitivity analysis, set `plot=3`.
5. For the Jianxiawo non-hazardous waste management subcase, replace line 655 of facility.py with line 656 (substitutes non-hazardous disposal cost for the hazardous impurity sludge stream).


## Citation

If you use this model or data, please cite:

```
Cheng, A. L. (2026) Building Secure and Competitive Clean Technology Supply Chains: Technology and Policy Options for Electric Vehicle Batteries and Critical Minerals [Doctoral Dissertation, Carnegie Mellon University]. ProQuest Dissertations & Theses Global.
```

## License

This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0).
You are free to share and adapt this material for non-commercial purposes, provided you give appropriate credit and distribute any derivative works under the same license.