# CCD / Filtration Block: Conversion Factor Estimation

## Problem Statement

The CCD step converts leach slurry (34 wt% solids) into a clarified pregnant leach solution (PLS). We need the conversion factor (CF) relating m³ of input leach slurry to m³ of output PLS. This requires estimating PLS volume and density from a mass and water balance across the combined CCD + filtration block.

## Input Characterization

Per **1 m³ of 34 wt% solids leach slurry**:

| Parameter | Value | Derivation |
|---|---|---|
| ρ_solids | 2.6 t/m³ | Smectite clay particle density |
| ρ_liquid | ~1.0 t/m³ | Aqueous phase (simplification) |
| ρ_slurry | 1.265 t/m³ | 1/(0.34/2.6 + 0.66/1.0) |
| Solids mass | 430.0 kg | 0.34 × 1265 |
| Liquid mass | 834.6 kg | 0.66 × 1265 |
| Li in solids | 1,091 g | 430.0 kg × 2,538 ppm |

## Dissolution During Leaching

Sulfuric acid dissolves the octahedral cations (Mg, Al, Fe, Li) from the smectite lattice, leaving an amorphous silica residue. For hectorite-type clays, approximately 30% of the ore mass dissolves (the non-silica fraction).

| Parameter | Value |
|---|---|
| Dissolution fraction (f_d) | 0.30 |
| Undissolved residue (M_residue) | 301.0 kg |
| Dissolved mass (as oxides) | 129.0 kg |

The dissolved oxides react with H₂SO₄ to form sulfate salts (MgSO₄, Al₂(SO₄)₃, Fe₂(SO₄)₃, Li₂SO₄) which are roughly 2–3× heavier than the oxide precursors. Combined with residual free acid, the total dissolved solids (TDS) mass depends on the acid dose but is estimated at 100–250 kg per m³ of leach slurry for acid doses in the 200–500 kg H₂SO₄/t ore range. TDS determines PLS density but does not control PLS volume, which is governed by the water balance.

## CCD Water Balance

The CCD circuit separates the leach slurry into washed solids (filter cake) and PLS (first thickener overflow). The key mass balance is on water:

**Water in PLS = Water in leach slurry + Wash water added − Water retained in filter cake**

### Filter Cake (62 wt% solids, per disclosure)

| Parameter | Value | Derivation |
|---|---|---|
| Residue solids | 301.0 kg | M_solids × (1 − f_d) |
| Water in cake | 184.5 kg | 301.0 × (1 − 0.62) / 0.62 |

### CCD Underflow (33 wt% solids per stage, per disclosure)

The liquid retained per stage in the CCD underflow determines the wash water requirement:

| Parameter | Value | Derivation |
|---|---|---|
| Underflow liquid | 611.1 kg | 301.0 × (1 − 0.33) / 0.33 |

### Wash Ratio (R_w)

The wash ratio is defined as the mass of wash water added to the circuit divided by the mass of liquid in the underflow. For an 8-stage CCD at 95% stage efficiency (per disclosure), the McCabe-Thiele relationship gives:

**Recovery = 1 − 1 / (1 + R_w × η)^N**

| R_w | Li Recovery |
|---|---|
| 0.50 | 95.5% |
| 0.75 | 98.7% |
| 1.00 | 99.5% |
| 1.25 | 99.8% |
| 1.50 | 99.9% |

Wash ratios below 1.0 sacrifice meaningful lithium recovery; above 1.5 provides diminishing returns. **R_w = 1.0** represents a reasonable central estimate, balancing high recovery (99.5%) against PLS dilution.

## Conversion Factor Derivation

PLS volume per m³ of leach slurry, as a function of wash ratio:

```
Wash water = R_w × 611.1 kg
PLS water  = 834.6 + Wash water − 184.5 kg
PLS volume ≈ PLS water / ρ_PLS_liquid  (≈ L, since ρ ≈ 1.0–1.08)
CF         = PLS volume / 1000          (m³ PLS per m³ slurry)
```

| R_w | Recovery | PLS Volume (L) | **CF** | Li in PLS (g/L) | R_conc to 4563 ppm |
|---|---|---|---|---|---|
| 0.50 | 95.5% | 956 | 0.96 | 0.98 | 4.9× |
| 0.75 | 98.7% | 1,108 | 1.11 | 0.87 | 5.5× |
| **1.00** | **99.5%** | **1,261** | **1.26** | **0.77** | **6.2×** |
| 1.25 | 99.8% | 1,414 | 1.41 | 0.69 | 6.9× |
| 1.50 | 99.9% | 1,567 | 1.57 | 0.63 | 7.7× |

## Cross-Check: Lithium Mass Balance

Working forward from the ore:

| Parameter | Value |
|---|---|
| Li in 1 m³ leach slurry | 1,091 g |
| Li after 90% leach extraction | 982 g |
| Li in PLS (at R_w = 1.0, 99.5% CCD recovery) | ~977 g |
| Li concentration in PLS | 0.77 g/L |

Working backward from 4,563 ppm Li post-impurity-removal (assuming 95% yield through impurity removal):

**Required concentration ratio = 4.563 / (0.77 × 0.95) ≈ 6.2×**

This implies the impurity removal block (including MgSO₄ crystallization) must reduce PLS volume by approximately 6×. This is plausible if the MgSO₄ crystallization circuit involves evaporative concentration steps, which is consistent with the disclosure's description of a dedicated crystallization circuit with cooling.

## PLS Density

The PLS is a clarified sulfate solution carrying dissolved Li, Mg, K, Na, Al, and Fe sulfates plus residual free acid. Density depends on total dissolved solids:

| Acid Dose (kg/t ore) | Estimated TDS in PLS (g/L) at R_w = 1.0 | Approximate PLS Density (t/m³) |
|---|---|---|
| 200 | 80 | 1.05 |
| 300 | 120 | 1.07–1.08 |
| 400 | 160 | 1.10 |

For a central acid dose estimate (~300 kg/t), **PLS density ≈ 1.07 t/m³**.

Note: The disclosure states the CCD overflow is cooled before downstream distribution, indicating elevated temperature from the leach circuit. A hot PLS (60–80°C) is ~1–2% less dense than at ambient temperature. For cost modeling purposes this is negligible.

## Recommended Values

| Parameter | Recommended Value | Notes |
|---|---|---|
| **CF (m³ PLS / m³ leach slurry)** | **1.26** | Central estimate at R_w = 1.0 |
| PLS density | 1.07 t/m³ | At ~120 g/L TDS |
| Li in PLS | ~0.77 g/L | Before impurity removal |
| CCD Li recovery | 99.5% | 8 stages, 95% efficiency, R_w = 1.0 |

## Key Sensitivities

The conversion factor is most sensitive to the **wash ratio**, which controls PLS volume. The acid dose affects TDS and PLS density but has negligible impact on the CF itself, because acid mass is small relative to total liquid mass.

The dissolution fraction (assumed 30%) affects the residue mass and therefore the cake water retention. Varying dissolution between 25–35% shifts the CF by approximately ±0.05.

The 6× concentration ratio required during impurity removal to reach 4,563 ppm Li is the main cross-check on this estimate. If the actual impurity removal process achieves less concentration (e.g., 3–4×), the CCD wash ratio should be reconsidered downward toward 0.5, yielding CF ≈ 0.96 and a more concentrated PLS.
