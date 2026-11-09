Previous Claude Project Instructions:
# Project Instructions

## Authority
1. Hierarchy: (a) files uploaded in the current chat; (b) text pasted in the current chat; (c) `/mnt/project/` copies — presumed stale. When working from (c), state so once and get my confirmation before proceeding. A re-upload supersedes all earlier in-chat versions; never reference superseded copies.
2. Never use `project_knowledge_search` for `main.tex` or `Master_Data_File.xlsx`. Read the authoritative copy per rule 1 directly: targeted `view` ranges for `.tex`; openpyxl for the xlsx, reading comments, formulas, and evaluated values together. Never diagnose a cell from a CSV. Before calling a cell a defect, check the step's prose in `main.tex`; a sheet–prose disagreement is itself the finding — flag it, do not pick a side.
3. Never use `conversation_search` or `recent_chats` unless I name a specific chat. Prior chats hold superseded versions.

## Session
4. Sole opener: if my session header (FILES / CHANGED SINCE LAST SESSION / UNCHANGED / CLUSTER / WHAT I WANT) is absent, request it. This is the only permitted "what should we do" question. UNCHANGED matters as much as CHANGED: code fixed against cells that did not move is a finding.
5. Echo-back before work: ≤10 lines stating the file versions, specific values, and conventions you are operating on. Proceed on my confirmation, or immediately only if the task is trivial.
6. One cluster per session — the smallest change that can be independently verified and independently landed. Do not open a new cluster while one is unverified; do not generate findings faster than fixes land. Out-of-cluster observations become one-line `[?]` queue items, not elaborated findings.
7. Batch audits are two passes. Pass 1: sweep table only (`item / value / check / PASS-FLAG`), mechanical checks defined by me in the request, no edits, no analysis. Pass 2: one flag adjudicated per session with full evidence.

## Claims
8. Every quantitative or structural claim about a file ships with its check in the same message: the snippet or command, expected output, observed output. No check → label it HYPOTHESIS. Reproduce before diagnosing; recompute headline numbers, never carry them from prose.
9. Verdict vocabularies — my fixes: CONFIRMED (correct and complete — say so plainly; a confirmed fix is a finding) / INCOMPLETE (something downstream must now move) / INCORRECT. Queue items: STANDS / RESOLVED (strike it) / CHANGED (stop, re-derive; do not proceed from the document). CONFIRMED is reserved for fixes.
10. Show equations and intermediate steps for every derived value; flag assumptions inline; math and variables only, minimal connective prose.
11. No confabulation. Project gaps: "cannot verify from project sources." External gaps: "no reliable source found." Never fill either with an estimate or range. Distinguish verified cited figure / general rule-of-thumb / unverified value. Treat my numbers as hypotheses to test; retract unsupported assertions — mine or yours — immediately and say so.
12. Anchor findings on content (quoted string, cell, parameter name), never on line numbers. When citing a location, quote the content alongside it.

## Execution and output
13. Pre-approved without asking: read-only diagnostics on authoritative files — openpyxl reads, comment dumps, greps, and model runs per continuation_prompt.md "Running the Model"; single targeted searches for one missing fact. Approval required first: creating or modifying files, and any multi-query or deep search (state terms and why, ≤50 words).
14. continuation_prompt.md holds durable conventions — prescriptive, no change history; unresolved conventions are stated as unresolved, never silently decided. handoff_open_items.md is a hypothesis queue — every item re-verified in the session that acts on it. Propose edits when items close or findings land; apply only on my approval.
15. Code: tabs, not spaces. No development-history or reasoning comments in generated code or text. Flags mandated by continuation_prompt.md (assumption flags, source-unverified flags, gap sentences) are content, not commentary.
16. No follow-on suggestions or next-step questions; rule 4 is the sole exception.
17. No comments or notes about development history or reasoning in generated code or text, unless I ask for them.


# Handoff: Open Items

**Reorganized 2026-08-25 for manuscript finalization.** The priority stack P1-P7 is retired and
replaced by two sections. **Section A — headline refreeze and text rewrite** is the work that must
land before this version of the manuscript freezes, and is the former P1 (numbers move) and P6
(prose, comment and label hygiene). **Section B — accepted debt** is everything knowingly carried
into the next version: **B1** the open clusters, **B2** the sourcing gaps and the deferred defects
(former P5 and P7). Nothing in B is worked this cycle.

**Three retractions stand from the 2026-08-25 pass:** the SP residue-conversion estimate, the SP
pond CAPEX shortfall, and the SP cake wet-density figure. None reproduced under any basis. Each is
named in the entry that supersedes it; do not reintroduce them.

**Four further retractions from the 2026-08-26 lime pass.** A `slaked_lime` material key and its
`Material Data` column: no step in the workbook purchases hydrated lime, both liming blocks carry a
slaker in their bill of equipment. A USGS-derived quicklime price band: the user's `material_cost`
figures are sourced and stand. `Brine-Solvent Extraction-Boron` `C24` / `C26`: **that sheet is
outdated, do not touch it and do not propose edits to it.** And the TP recovery / ore-intensity
figures, dropped by declaration. Do not reintroduce any of them.

**Gate status 2026-08-26, post-lime.** `helpers.check_workbook_formula_cache` returns EMPTY. All
three projects hold the 18/18 gate and are leak gates; every figure was re-measured after the lime
basis and factor work and is recorded at the top of A1. All six restricted brackets, all three
tornado rankings and the JX non-compliance delta are measured on this stack.

A `[RUN]` tag means a counterfactual pass or the full `run_all`. `run_all` was executed 2026-08-26;
the S4 run is closed. Measuring a gate residual needs no CCF harness — read it off the
`SupplyChain` objects after a midpoint rebuild.

**Anchor on content** — the quoted string, the cell, the parameter name. Line numbers are dead.

**Acceptance gates** live in `continuation_prompt.md` → Stream Conventions. Five gates plus the
SP/JX bit-identical leak gate close a cluster; the project ranking is not a gate.

**Status legend:** `[ ]` open · `[?]` re-verify before acting · `[x]` closed · `[!]` take ahead of
dependency order · `[-]` deferred, see B2.

**Per-session protocol:** read the workbook comments first (`continuation_prompt.md` → "Reading the
workbook"); re-verify and report STANDS / RESOLVED / CHANGED; fix; run the gates; strike on the
user's declaration. One cluster per session.

---

## Section A — Headline refreeze and text rewrite

Everything that must land before this version freezes. A1 moves numbers; A2 does not.

### A1 — Blocks the S4 headline freeze

**Gate frozen 2026-08-26** on the uploaded `.py` set and workbook, after the lime basis and factor
work: `Brine-Batch Chemical Purificati` `C28` = `=M_CaO/M_Mg*1.2` = 2.768664884, `C40` =
`=C34*C28*M_Ca/M_CaO` = 6.279454598, `Material Data` `C9` = 1.16, `Project-Specific Data` rows
85/86/87 = 1.25 / 1.16 / 1.04. `check_workbook_formula_cache` EMPTY, zero `CLIP` warnings.
`avg_opex` mid / cons / opt, then `avg_co2` t/t, at ten decimals:

SP 5520.1696381123 / 6897.4930655233 / 4372.5410503398 and 6.0120217244 / 7.3229819730 / 4.6721262621
TP 8703.2254504699 / 15171.8229710104 / 6214.3200500757 and 16.6714571902 / 20.4978879436 / 12.7184769936
JX 12139.5438669622 / 15621.5275213242 / 10136.0843217773 and 30.2576339783 / 42.7720656195 / 22.8081154983

18/18. TP and JX `avg_opex` are bit-identical across all three scenarios to the pre-lime gate — the
leak gate proving the work touched only mass and factor, not the TP dose or any JX cost path. SP
soda ash 5056.8242 kg/t is bit-identical before and after the `C28`/`C40` pair, which is the
invariance those two edits exist to preserve. Every SP figure recorded before 2026-08-26 is
superseded; do not quote 5584.265379 or 5585.498705.

**Restricted top-3, ranked per metric.** Cost bracket from `run_topn_scenarios(top_n=3,
metric="avg_opex")`, emissions bracket from the same call at `metric="avg_co2"`:

SP [4469.990682 - 6775.830260] and [4.697869 - 7.291314]
TP [7064.628135 - 13903.394181] and [13.540477 - 19.417922]
JX [11187.278086 - 13887.682838] and [24.479302 - 40.356116]

**Tornado rankings, all three projects, spread in $/t and kg/t.**
SP cost: `evaporation_pond_unlined` 969.1537, `soda_ash` 960.7966, `brine_pump` 375.8893, `lime`
104.5831, `drying_packaging_propane` 47.9827. SP emissions: `soda_ash` 2022.7297, `brine_pump`
326.6885, `lime` 244.0272, `drying_packaging_propane` 36.2142, `precipitator` 10.5347.
TP cost: `sulfur` 5034.1389, `process_water` 911.4658, `lime` 893.1614, `soda_ash` 688.7134,
`excavation_loading_generic` 516.1904. TP emissions: `sulfur` 2343.4784 (15456.3202 → 17799.7987),
`lime` 2084.0432 (15480.5754 → 17564.6186), `soda_ash` 1449.9230, `sulfur_burner` 794.1987,
`excavation_loading_generic` 436.5792. **Sulfur now leads TP emissions uncertainty, not lime.**
JX cost: `soda_ash` 965.4805, `sodium_sulfate` 936.7366, `sulfate_roasting_train_lepidolite`
798.1876, `excavation_loading_generic` 648.4074, `water_leach` 311.6866. JX emissions:
`sodium_sulfate` 7806.1386, `sulfate_roasting_train_lepidolite` 4208.7535, `soda_ash` 3861.9220,
`high_energy_grinding_mill` 1112.4193, `lime` 983.5735.

**JX hazardous-waste non-compliance, midpoint.** `avg_opex` 11672.702543, delta −466.841324 $/t
against the compliant 12139.543867; `avg_co2` 30.257634 unchanged.

**Midpoint cost buildup, sums exactly to `avg_opex` on all three.** Reagents / utilities / labor /
sinks / transport / maintenance / fixed overhead:
SP 1518.3890 / 585.1658 / 2401.6506 / 26.2297 / 0 / 404.4912 / 584.2433 = 5520.169638
TP 5125.6676 / 83.1728 / 1326.4513 / 1564.5375 / 0.1907 / 454.1731 / 149.0325 = 8703.225450
JX 5192.3243 / 2422.8918 / 427.7871 / 2816.6014 / 291.8560 / 775.4882 / 212.5951 = 12139.543867

One counterfactual is recorded but NOT landed: unrounding `brine_pump` `electricity_base_total`
from 117 / 108 / 99 to the exact 115.65149 / 106.75522 / 97.85895 moves SP `avg_opex` by
−6.370033 / −6.900861 / −5.839206 and `avg_co2` by −0.022592 / −0.024475 / −0.020709. The sheet
still holds the rounded values; the gate above is measured against them.

`mother_liquor` closes on both projects — TP 8,768,228.15 m^3/yr to `process_water_recycle`,
JX 10,009,626.53 m^3/yr to `wastewater_discharge_cn`.

`NORM_AXES` headroom measured on this stack, zero `CLIP` warnings emitted. Per-step bars, not
totals: JX conservative emissions max step `Roasting of lepidolate with sulfate salts` 29974.6687
kg/t against the 30000 cap, 25.3313 kg/t of headroom; TP conservative cost max step
`Sulfur burning` 6163.9745 $/t against the 7000 cap.

- `[?]` **Summary major-numbers table — landed, one sentence unfinished.**
  `tab:04-summary-majornumbers` is in place under `\subsection{Additional Results and Model
  Outputs}`, carrying 5,520 / 8,703 / 12,140 and 6.01 / 16.67 / 30.26, reagents 1,518 / 5,126 /
  5,192, lime 1,162 / 9,924 / 4,684, with a single footnote `Dosed as \ce{CaO}; purchased as
  quicklime and slaked on site.` scoped to the Silver Peak cell only. **Blocking:** `main.tex`
  L778 reads `Table \ref{tab:04-summary-majornumbers} also summarizes key costs ` — the sentence
  ends mid-clause with no terminal punctuation. A1 does not close until it does.

### A2 — Prose, comment and label hygiene

Landed after the headline freeze. Verified 2026-08-25 unless noted.

- `[?]` **The smallness claim.** `Given these waste emissions are expected to be small relative to
  the Scope 2 and Scope 3 terms that dominate all three pathways, this omission is unlikely to
  affect the comparative results materially` — still present, still covering terms whose magnitude
  is not established (placement diesel, gate haulage, impoundment construction, land use). Six of
  eleven sinks return 0.0 kg CO2/m^3 — re-measured 2026-08-26: `slag_stack_cn_65`,
  `conc_stack_cn_60`, `sludge_gate_cn_50`, `sludge_stack_cn_50`, `rock_pile_cn_100` and
  `rock_pile_nv_100`, all `train=[]` with placement kWh 0.0. The five with nonzero draw are
  `gangue_stack_nv_20`, `gangue_impound_cn_30`, `claycake_stack_nv_62`, `sludge_stack_nv_50` and
  `mgcake_stack_nv_35`. The seven-of-ten count predates `sludge_stack_cn_50` and reproduces against
  neither the old nor the current set.
- `[?]` **`tab:wastewater-routings` orders `\centering` then `\small` then `\caption`**, against the
  caption-first template rule. Confirmed.
- `[?]` **`get_step_cost_report(detail=1)` names the sink row `Sink Costs`** where both builders
  name it `Tailings Management`. **Gate 3 itself passes**: measured 2026-08-25, `_build_steps_cost_series`
  and `_build_steps_impact_series` return identical label lists for all three projects at
  `detail=2`, and the impact builder takes no `detail` argument at all. Report-API naming only,
  not a plotting defect.
- `[?]` **Sink gate table mixes bases. CHANGED — the anchor is gone; re-derive, do not proceed from
  the document.** `grep '$/t DS' continuation_prompt.md` returns zero hits and none of the six
  figures below appear anywhere in it. The "Sink naming" section now states the registration basis
  as `ds_per_m3(s_in, rho_s)`, and the doc elsewhere records `TAILINGS_SINK_PARAMS` entries as
  `$/m^3`. Prior measurement, retained only as the thing to re-derive against: measured
  2026-08-24 on `59c7f65a`: `gangue_stack_nv_20` 3.8323 $/t DS and 0.8740 $/m^3, 13.8584 kWh/t DS
  and 3.1607 kWh/m^3; `claycake_stack_nv_62` 4.9109 / 4.9231, 3.8253 / 3.8348;
  `sludge_stack_nv_50` re-measures at 9.9403 $/t DS. The per-m^3 and kWh legs of all three sinks
  need re-measuring on the current stack before a basis is picked. `[RUN]`
- `[?]` **`Sulfuric Acid Leach` `F62` comment cites dead cells** — it reads
  `F46 + F56 = 1.000000 exactly` while the live formula references `F52` and both `F46` and `F56`
  are empty. Physics is correct: F52 + F62 = 0.1987673344 + 0.8012326656. Confirmed.
- `[ ]` **`precipitator` basis label mismatch.** `base_volume_unit` `L polished brine/h` and
  `step_basis` `polish_brine_throughput` against the sulfate sheet's `polish_pls_throughput`.
  Confirmed on all three ranks. `scaling_exponent_throughput` = 0.6, a sublinear ROW 9 utility
  exponent — the same defect corrected on `classifier_generic`, which now reads 1.0.
- `[ ]` **`tp_debug` ore throughput** = `leach_pv * 430 / 1000`, hardcoded and decoupled from
  `step_ccf`; the value is leach-feed solids. Confirmed verbatim.
- `[ ]` **`tp_debug` prints `avg_co2` under a `t CO₂/t LCE` label; the value is kg/t LCE.**
  Confirmed: `print(f"  {'avg_co2 (t CO₂/t LCE)':<40} {avg_co2:>14,.2f}")` with no `/1000`, while
  the `evaluate_project` return and the `topn` path both scale correctly.
- `[?]` **`Brine-Evaporation` `D45`** (`evap_ponds` `primary_output_1_yield_rate`) is blank,
  intended to load at runtime, covered by a `default=1.0`. Confirmed blank. Silver Peak crashes if
  the default is tightened without populating it.
- `[?]` **`rom_ore_feed` is labeled `rock` on the producing side and `ore` on the receiving side.**
  Both may be correct, since waste leaves at `excav_load`. Re-checked 2026-08-26: `Blast Mining`
  `primary_output_1_units` = `m^3 rock to be transported`; `Sulfuric Acid Leach` Crushing
  `primary_input_1_units` = `m^3 loose ore feed`; `Sulfate Roast-Water Leach` Crushing =
  `m^3 loose ore`. A third label the item never recorded: `Non-Blast Excavating`
  `primary_output_1_units` = `tonnes`, a different dimension from both.
- `[?]` `main.tex` prints `1.472` where 0.912 × 1.613 = 1.471056.
- `[?]` `continuation_prompt.md` → "Sink naming" reads `for all ten names`; `TAILINGS_SINK_PARAMS`
  carries 11.
- `[?]` `Locational Data` `aux_equip` = 0.0 in all six populated jurisdictions — `aux_equip_cost` is
  structurally dead in `tot_capex` and in the `fixed_over` base.
- `[?]` `opex_fraction_of_capex` = 0.0 in all 85 `Machine Blocks Data` columns — `opex_excess` is
  structurally dead.

---

## Section B — Accepted debt

Carried into the next version by decision. Do not work these this cycle; do not re-derive them.

### B1 — Open clusters

Not incorporated into the priority stack when they should have been. Time cost unscoped, which is
the reason they are here rather than in Section A.

**C4c — reduce `clay_lepidolite` to wiring.** `[ ]` **Scope halved 2026-08-25.** `S_STACK` and
`S_TAILS` no longer need moving: `run_scenarios.py` reads
`S_STACK = sink_s_out("gangue_stack_nv_20")` and `S_TAILS = sink_s_out("gangue_impound_cn_30")`,
retiring both literals. What remains: `RHO_GRAIN = 2.6` and `RHO_GRAIN = 2.7`, still hard literals
in the two branches, and the Clays precipitation ccf construction. `grade_ratio` is already
parameterised (`rom_comp["Li"] / project_data["Intermediate Concentration"]["Li"]`) and the
classifier reject conversion is set at runtime, which is why `Sulfuric Acid Leach` `E62` is blank.
Acceptance: no numeric literal in either branch other than unit conversions; no derived quantity
computed in a branch that a `Constants & Derivations` cell carries; every cross-sheet reference a
named range; all three projects bit-identical.

**C5f-3 — JX hazard classification.** `[ ]` The model prices `sludge_gate_cn_50` (offsite gate,
`gate="NDRC_HAZ_JX"` at 280 $/t wet) against `slag_stack_cn_65` and `gangue_impound_cn_30`, both
unlined and storage-priced. A `sludge_stack_cn_50` row now exists in `TAILINGS_SINK_PARAMS`,
labelled for the non-compliance scenario — but there is still **no lined nonhazardous route**, which
is the missing category. Yichun lithium slag leaches Tl at 13-14 µg/L across pH 3-8 and Be to
789 ppb (WET) / 404 ppb (TCLP) against EPA MCLs of 2 and 4 ppb, pH-INDEPENDENT where ore and
tailings leaching is pH-dependent. Sensitivity on the leach residue alone: 8.60 $/t DS unlined /
~15 lined / 373.33 hazardous-gated. The JX constituent vector carries no Tl or Be, so the exposure
is invisible to the model. Sources: Yan et al. 2012 *Int. J. Miner. Process.* 110-111:1-5; National
Science Open 2025 NSO20250028; *Water Research* 2026 S0043135426000679; *J. Hazard. Mater.* 2025
S0304389425035253; Yicai Global 2022-12-08; *Sci. Rep.* 2025 s41598-025-16048-8.

**C5i — TP leach ledger.** `[ ]` **`I52` has CHANGED and the cluster text must be re-derived.** It
now reads `=(salts_CCD_TP/TDS_TP - s_cake_CCD_TP*(1-s_CCDs_TP)/s_CCDs_TP) * ((1-TDS_TP)/Rho_water +
TDS_TP/Rho_Grain_Rock) * I10*10^3 / I51` = **1.233175362**,
and `TDS_TP` = 0.1606888016 is itself the quadratic solution of the wash-water balance at
`w_r_TP` = 3.3. Both moved again with `f_Neut_TP`; re-derive the cluster text on the current stack. The open questions: (a) the dosed acid and limestone are still booked at
zero into the solids ledger, and booking acid-derived SO4 as TDS raises V while gypsum precipitation
adds cake mass and cuts it back — both directions live, neither bounded from the sheet; (b) acid
*strength* is unmodelled, the dose being on a 100 wt% basis while `G10` already carries the acid
volume as a third phase and `G34` nets it out of the water draw. `J62` is now a formula with a
sourced comment, so the "ten significant figures and no source" objection is **resolved**.

**Water audit.** `[?]` **Purchase side re-measured 2026-08-25:**
JX `process_water` **407.9424 m^3/t LCE = 18.7654 Mm^3/yr** plus
`recycled_process_water` 255.0636; TP `process_water` **224.1743 m^3/t = 14.9748 Mm^3/yr** plus
recycled 481.9582; SP purchases 0.0908 m^3/t and draws 24,563,504,282.6 L raw brine. The accounted
side and the closure percentages still need `li_water_ledger.py`, so the ~83% JX closure and the
TP +0.0 unattributed figure are **not** re-verified. `[RUN]` Do not quote the benchmark comparison
until the ledger is rebuilt — every TP volume has moved.

**Workbook colour status.** `[ ]` **Recounted 2026-08-25 on `21894626`.** Green `FF93C47D` validated / orange `FFF6B26B` partial / red `FFFF0000`
assumption. Totals **866 G / 912 O / 82 R**.

| Sheet | G | O | R |
|---|---|---|---|
| **Lime basis, factor band and the `C28` cascade** | **2026-08-26** | The `lime` material key was dosed on two chemical bases across sheets — `kg CaO` on `Sulfuric Acid Leach` `J30`, `kg Ca(OH)2 per kg Mg` on `Brine-Batch Chemical Purificati` `C30` — while carrying one price and one GHG factor. `batch_treatment_generic`'s bill of equipment lists a detention slaker and milk-of-lime storage, so Silver Peak buys quicklime and slakes on site; the hydroxide dose was the defect, not the material key. Landed: `C28` `=M_CaOH2/M_Mg*1.2` → `=M_CaO/M_Mg*1.2` = 2.768664884, `C30` and `C26` relabelled, `C3` `step_name` relabelled. **The cascade was one cell**: `C40` `=C34*C28*M_Ca/M_CaOH2` converts the lime dose to released calcium and sets the soda-ash polish; on the old divisor it fell to 4.752645029, under-dosing SP soda ash by 24.3% and costing 166.612177 $/t and 0.320408 t/t. `=C34*C28*M_Ca/M_CaO` restores 6.279454598 and SP soda ash returns bit-identical at 5056.8242 kg/t. A whole-workbook formula sweep for `C28`, `M_CaO` and `M_CaOH2` returns only `C40`; `Sulfuric Acid Leach` `J62`'s `J28*M_Ca/M_CaO` was already correct. Factor band: 0.83 was not GREET quicklime — GREET 2021 `Inputs` row 1515 gives `Quicklime (CaO)` col L and `Lime` col AQ at 1,163,545 g/t and `Calcium hydroxide` col AS at 880,521 g/t, the latter derived from the former by mass allocation (0.756757) with no slaking burden. 0.83 is hydroxide-shaped and reproduces in no GREET 2021 cell — **cannot verify from project sources**, most likely another vintage. Landed 1.04 / 1.16 / 1.25 at `Material Data` `C9` and `Project-Specific Data` 85/86/87, cited to the RFF greenhouse-gas index gas and coal kilns and GREET 2021 respectively, with Roy et al. / ecoinvent 1.1954 sitting inside the band and the process share 0.784796/1.16 = 67.7% still supporting the two-thirds claim. Prices untouched — the user's `material_cost` figures are sourced. `main.tex` landed across 21 hunks. ✋ |
| **Case sensitivity of material keys** | **2026-08-26** | `Sulfate Roast-Water Leach` `I31` was briefly `Lime` against `lime`; `production_step.py` raises `KeyError: "Reagent 'Lime' does not have associated data at the facility level."` at build time and Jianxiawo does not construct. Reverted. One character, one whole project, no partial result to notice. |
| **S4 run** | **2026-08-26** | Closed by user declaration 2026-08-26. `run_all(...)` executed on the current stack; every headline cell, both restricted brackets per project, the TP tornado ranking and the JX non-compliance delta are measured and recorded at the top of A1. `check_workbook_formula_cache` EMPTY, zero `CLIP` warnings. No code change was owed: `.astype(object)` in `write_project_outputs_to_csv`, the paired `run_topn_scenarios(..., metric="avg_opex")` / `metric="avg_co2"` calls, the `/1000` scaling inside `run_topn_scenarios`, the `os.makedirs` and `CLIP` guard in `_save_open_figures` are all present and verified. **Figure assembly is by hand and outside the run** — `main.tex` includes `04-{project}-Steps-Summary.png`, `04-{project}-Sensitivity.png`, `04-costemissions.png` and `c-fullres.png`, none of which is an emitted filename; `run_all` emits `-Steps-Cost` / `-Steps-Emissions` / `-Sensitivity-Cost` / `-Sensitivity-Emissions` as inputs to that assembly, and `04-costemissions.png` and `c-fullres.png` have no builder at all. The composites carry the midpoints and both bracket sets, all six of which moved this session, so they move with the run. Artifact state in the user's tree was not verifiable from the uploads and is accepted on declaration. |
| Machine Blocks Data | 520 | 699 | 20 |
| Sulfate Roast-Water Leach | 73 | 9 | 2 |
| Project-Specific Data | 57 | 72 | 4 |
| Sulfuric Acid Leach | 57 | 8 | 0 |
| Solution Processing-Sulfate | 37 | 1 | 0 |
| Solution Processing-Chloride | 33 | 1 | 0 |
| Locational Data | 25 | 31 | 4 |
| Sulfuric Acid Plant | 19 | 1 | 0 |
| Brine-Evaporation | 14 | 0 | 0 |
| Brine-Batch Chemical Purificati | 14 | 3 | 0 |
| Blast Mining | 11 | 0 | 0 |
| Non-Blast Excavating | 4 | 0 | 0 |
| Transportation Data | **0** | 72 | **42** |
| Material Data | **0** | 13 | **5** |
| Brine-Solvent Extraction-Boron | 0 | 0 | 4 |

Movement since 2026-07-28: `Sulfuric Acid Leach` 35 → 57 G and 12 → 8 O with all four reds cleared;
`Sulfate Roast-Water Leach` 63 → 73 G; `Machine Blocks Data` +45 G, +15 O. `Transportation Data` and
`Material Data` are unmoved and remain the two zero-green sheets.

Red cells in runtime-consumed data, re-read 2026-08-25:
- `Transportation Data` `fixed_cost`, `fuel_usage`, `labor_fraction` and `maintenance` are 0.0 for
  all six modes while `operating_cost.*` is populated. **Sub-question answered:** `transportation.py`
  reads `self.ghg_emissions_pkm = mode_data["ghg_emissions"]`, so `fuel_usage = 0` does **not** zero
  transport emissions.
- `Material Data` dispersant `raw_cost` = 1.0 $/kg with `co2` blank; `sulfur` now `co2` = 0.3 under
  `kg CO2e/kg` (the D-3 unit disagreement is closed).
- `Locational Data` `utility_impact.steam.co2` 0.15 and `cooling_water.co2` 0.08 — **uniform across
  all eight jurisdictions**, not a Nevada/Jiangxi pair.
- `precipitator.compressed_air_base_total` = 2.0 Nm^3/h on all three ranks.
- JX `Swell Factor` 1.75, validation status unchecked.

Cross-cutting orange families, one memo each (~500 of 912 orange cells): `proc_avail_factor` +
`unplanned_downtime` + `scheduled_maintenance`; `footprint_base` / `_scaling_exponent`;
`prim_equip_life`; `base_volume` / `oversizing_factor` / `scaling_exponent_throughput`;
`prim_equip_price_base`. Note the first and fourth families both contain fields shown to be dead —
`proc_avail_factor`, `oversizing_factor` — both now recorded in B2b; write those memos against the
B2b entries, not against the live cell values.

### B2 — Sourcing gaps and deferred defects

#### B2a — `[SOURCE]`

- **Ca(OH)2 solubility in concentrated salar brine at batch-treatment pH.** `Brine-Batch` `C28` =
  `=M_CaOH2/M_Mg*1.2` = 3.6581115 confirms the model encodes 1.20 eq/mol Mg (all dosed lime);
  the alternative is 0.95 eq (reacted lime only). `main.tex`'s residue derivation implies 1.14 eq,
  which is 1.2 × 0.95 and has no mechanism. Spread across the fork is 142.759 $/t and
  274.536 kg CO2eq/t midpoint.
  **Now also load-bearing on `V_res_SP`** (`Constants & Derivations`): the fork sets the CaCO3 term
  at 93.2898 g/L (all dosed Ca reports to the cake) or 74.4252 g/L (reacted Ca only), i.e.
  `Brine-Batch Chemical Purificati` `D56` = 0.2833721 or 0.2434469. The sheet carries the
  reacted-basis value.
- **A disclosed lepidolite-PLS Li concentration and density.** The derived pair has CHANGED and is
  now formula-driven: `c_PLS_JX` = **909.937832 ppm** and `rho_PLS_JX` = **1.049490518 t/m3**,
  Absent a source, ship the derived pair flagged.
- **TP liquor grade.** `AB21` = 1,289.8 ppm, derived through `c_PLS_TP` from `Li_int_TP` and the
  `Sulfuric Acid Leach` I-column chain. Resolve only against a disclosed stream table with the
  plant boundary pinned.
- **Unsourced parameters load-bearing on the JX water leach and roast.** Confirmed on
  `Constants & Derivations`: `s_cake_JX` = 0.65, `r_res_JX` = 0.01, plus the kiln efficiency band
  0.40-0.60 and the ~0.50 GJ/t reaction enthalpy (31% of demand), both now stated as estimates in
  the roasting writeup. `x_hyd` = 0.0 on `slag_stack_cn_65` against lime-derived CaSO4 in the cake.
- **cp for SP concentrated brine, TP sulfate PLS and JX sulfate PLS** (spans 30% of the preheat duty
  across 3.2-4.18 kJ/kg·K) and **precipitation operating temperature** on all three. Blocks the
  preheat `[DECIDE]`.
- **CEPCI 2025 annual average** — closed 2026-08-25; see Closed.
- **Cross-cutting orange families** — see the colour item under B1.

#### B2b — Deferred defects

Known, confirmed, and consciously not fixed for this draft. Do not re-derive; do not re-open
without a reason that is not already stated here.

- `[ ]` **`main.tex` L227 lime paragraph is provisional.** Reads `lime overwhelmingly dominates
  emissions, with a range between $\sim$15.5-17.6 t \ce{CO2eq}/t`. The range is correct but is the
  project total at lime-optimistic and lime-conservative, not lime's contribution, which is
  11908.8 kg/t of 16671.5 = 71.4%. Lime still dominates the emissions **level** at TP; it no longer
  dominates the **uncertainty** — `sulfur` leads at 2343.4784 against lime's 2084.0432. Held by the
  user pending the figure pass; rewrite the two claims separately.
- `[ ]` **`Sulfate Roast-Water Leach` `I31` chemical basis is unverified and now unflagged.** `I34`
  = 75 with `I36` = `kg/tonne roaster_mix`, attributed to Yan et al. 2012, which does not state
  whether it reports quicklime or hydrated lime. **Cannot verify from project sources.** If
  hydrated, JX lime mass falls by 0.756856. The summary table's footnote carrying this caveat was
  dropped in the 2026-08-26 consolidation to a single footnote, so nothing in the manuscript now
  flags that JX's 4,684 kg/t is not on a stated basis.
- `[ ]` **Slaking water is unbooked.** Slaking consumes 0.32 kg H2O per kg CaO and no water term
  appears against the slaker in `batch_treatment_generic`. At Silver Peak that is
  1162.0342 × 0.32 = 371.85 kg/t LCE of process water not in the balance.
- `[ ]` **`Brine-Solvent Extraction-Boron` `C24` = `=74.093/24.305*1.15` and `C26` =
  `kg Ca(OH)2 per kg Mg`** carry the same hydroxide-basis defect `C28` had, and `74.093` is a stale
  literal against `M_CaOH2` = 74.092. **The sheet is outdated — do not touch it.** Recorded so the
  defect is not rediscovered and proposed again.

Known, confirmed, and consciously not fixed for this draft. Do not re-derive; do not
re-open without a reason that is not already stated here.

- `[-]` **TP `impurity_removal` yield = 0.99** rests on 97.2% single-stage displacement. `J46` =
  `=J62*(1-(DS/ρ_s))-(1-J51)` = 0.3470161596, whose comment states the perfect-single-displacement
  assumption explicitly and notes a real press circulates 1-1.5 displacement volumes with filtrate
  return. Recorded so it is not rediscovered. **Deferred 2026-08-25.**
- `[-]` **`ccd` gate-2 volumetric residual 0.0434996924 per basis, 4.3500%.** Reproduced twice, from the sheet and from the
  model's own objects: `ccd.step_pv` 7,600,155.3307 + `process_water` `abs_usage` 7,160,371.2519
  − `acid_leaching` `recycled_process_water` `abs_usage` 2,288,600.1479 = 12,471,926.4347 against
  `impurity_removal.step_pv` 9,278,601.0582 + `filter_cake` `volume` 2,862,720.9575 =
  12,141,322.0157, residual 330,604.4190 m^3/yr. IPCF at the seam is 1.0, so no input conversion
  factor enters; CCFs are gate-1 carriers and do not appear. Water closes to −1.2e-10, so gate 3
  is clean and the whole residual sits on the non-water side: IN ore grain + acid 0.3096526845
  against OUT PLS salts + cake solids + cake liquor salts 0.2432675297 = 0.0663851548, less the
  `I62` / `ds_per_m3` convention offset 0.0228854626. **Definitional, not a defect.** `G10` builds
  the basis as ore grain at `Rho_Grain_Rock` plus water plus *liquid* acid at `Rho_H2SO4` = 1.84,
  and `I10 = $G$10` carries that unchanged to a step where the acid has already reacted; its
  sulfate travels as `salts_CCD_TP` and as gypsum inside `s_cake_CCD_TP`, both counted at 2.6, and
  the contraction has no term. Closing it needs either an explicit contraction term or an
  acid-exclusive `CCD_feed_throughput`, which would re-base `G10`, `H10`, `I10`, `G18`, `G28`,
  `H28` and every dose written per m^3 of slurry. **`I62` must not be "corrected" in isolation**:
  it and `facility.py` `ds_per_m3(w_s, rho_s)` share the `1/(w_s/rho_s+(1-w_s)/rho_w)` convention
  and the pair reproduces the cake dry-solids mass exactly — 2,862,720.9575 m^3/yr x 1.002488
  t/m^3 = 2,869,842.15 t DS/yr = `ore` x `s_cake_CCD_TP` = 42.961709 t DS/t LCE, the recorded
  claycake figure. Moving `I62` alone under-bills `claycake_stack_nv_62` by 6.08%.
  **Deferred 2026-08-25.**
- `[-]` **SPS `wash_purif_step` gate-2 residual +1.0000%.** `Solution Processing-Sulfate` `E45`
  = 0.99, `E46` = 1.0, `E56` = 0.1 against an additive `E28` dose of 0.1: 0.99 x 1.0 + 0.1 = 1.09
  against 1 + 0.1 = 1.1. The gap is the uncompensated (1 - y) x POCF = 0.01. Above the 0.5% band;
  closing it needs a coupled edit to `E45`/`E46` and is not worth it for this draft.
  **Deferred 2026-08-25.**
- `[-]` **`f_carb_TP`** — acid consumed by ore carbonate to in-leach gypsum. Confirmed absent from
  `Constants & Derivations`; the sheet instead carries `f_Neut_TP` = 0.079 for the bulk
  neutralization duty. Candidate, not correction; reopens the CCD closure (`salts_CCD_TP`,
  `s_cake_CCD_TP`, `TDS_TP`, `I52`, `I62`, `I34`, `I57`, `J10`, `J22`, `J57`, `c_PLS_TP` → `AB21`).
  Sandbox g = 0.10 / 0.20 / 0.30: opex 10487.323 / 10144.084 / 9801.670, co2 24.083 / 21.785 /
  19.538 — all pre-S3. Plausible ore carbonate is 5-10 wt%; reproducing the pre-S1 headline needs
  g ≈ 0.6 = 30 wt%, which is not defensible.
- `[-]` **The magnesium-crystallization route is OUT OF SCOPE by decision.** Boundary in
  `continuation_prompt.md` → "Active Pathways and Machine Blocks".
- `[-]` **`Test Cases and Back-Calculation` is out of scope.** Reports `True` while adrift on superseded
  yields. Do not audit or repair.
- `[-]` **`get_step_cost_report` keys sink totals as `total_cost` under `view="opex"`**, where
  production and transport records key `opex_total`. The under-report symptom is resolved in
  `_build_steps_cost_series`; latent API inconsistency only. Any new consumer reading
  `opex_total` alone still drops every sink. **Deferred 2026-08-25.**
- `[-]` **Labour is charged 7,875 h per FTE.** `facility.py`
  `self.plt = self.dpy * self.spd * (self.hps - self.ub)` = 350 x 3 x 7.5, and
  `production_step.py` `self.labor_cost = self.facility.wage * self.labor_required * self.plt`.
  The shift factor applies twice against `main.tex`'s `applying a staffing factor of 4.5`:
  $393,750/FTE/yr against a 1,800-2,080 h person-year, 3.0x against a 2,625 h shift-year.
  TP 228.88 FTE at 66,800 t/yr against the disclosed 626 at full build (`Workforce (Disclosure)`
  `AB105`). Model-wide; moves no rank order. **Deferred 2026-08-25.**
- `[-]` **`lta` deducts shift breaks from continuously-operating plants.**
  `self.lta = self.wlt * (1 - self.unplanned_downtime - self.scheduled_maintenance)` with
  `self.wlt = self.dpy * self.spd * (self.hps - self.ub - self.pb)`. 6,762 h/yr at TP, 77% of
  8,760; inflates the hourly rate used for equipment scaling by 1.183x. **Deferred 2026-08-25.**
- `[-]` **`register_sink_cost` returns silently.** `all_sinks = {sink for fac in self.facilities.values() for sink in fac.sinks}` then `if sink_name not in all_sinks: return`. Silver Peak registers a subset while `sc.sink_elec` carries all ten tailings sinks; a registration for a sink no facility declares is dropped with no error. **Deferred 2026-08-25.**
- `[-]` **Limestone neutralization process CO2 is unbooked.** `Sulfuric Acid Leach` column H (`neutralization`) has no `coproduct_1_name`, so nothing routes to a sink while `CaCO3 + H2SO4 + H2O -> CaSO4.2H2O + CO2` releases CO2 under full conversion. Booking it needs a dedicated sink (`atmosphere` cannot carry it: `impact_factors["atmosphere"]` would multiply the `evaporated_water` coproducts at `Sulfate Roast-Water Leach` `I61`, `Brine-Evaporation` `D55` and both `Drying & Packaging` `F55` cells, breaking the SP/JX leak gate), plus a `Locational Data` `utility_impact.<sink>.co2` row and a `run_scenarios.py` sinks-list entry. Size at 2949.9709 kg limestone/t LCE x M_CO2/M_CaCO3 = 1297.13 kg CO2/t LCE = 1.2971 t/t, +7.60% on TP `avg_co2`. **Deferred 2026-08-25** - calibrating a mass-basis coproduct on a volume-basis step is out of scope for this draft.
- `[-]` **`aggregate_inputs` now rebases but still sums unweighted.**
  `rebase = (ccf / ipcf) / self.step_ccf` then `total_consts[const] += float(amount)*rebase`.
  Adding ppm across primary inputs remains mass-blind. Latent — no step declares a second primary
  input. **Formula updated 2026-08-25.** No step declares a second primary input: no `primary_input_2_name` row exists on any live pathway sheet, and `max(len(step.primary_inputs))` = 1 across all steps of all three projects, so the sum has one term. **Deferred 2026-08-25.**
- `[-]` **`apply_reagents` accumulates `per_unit_usage`.** Confirmed verbatim:
  `tprops["per_unit_usage"] = tprops.get("per_unit_usage", 0.0) + ratio * base_amount`. Not costed;
  any writeup quoting it is wrong by the call count. `per_unit_usage` is written at `production_step.py` and read nowhere in the six modules; costs run off `abs_usage`. Zero hits in `main.tex`. **Deferred 2026-08-25.**
- `[-]` **`get_constituent_amount_at_steps` returns `val * pv`** — confirmed verbatim,
  `out.append([s["step_id"], val * pv])`. ppm × PV, no CCF. Not a mass. Any ledger claim sourced to
  it is unsupported. Its only call sites are two commented-out prints in `run_scenarios.py`; zero hits in `main.tex`. **Deferred 2026-08-25.**
- `[-]` **`helpers.clean_input_str` splits on `;` only.** Sheet side **resolved** —
  `Project-Specific Data` `K9` is semicolon-delimited throughout. Code side STANDS: `list_delim=";"`
  with no comma guard, and `parse_keylist_string` returns `None` for an unsplittable string, so the
  comma form still falls through to the raw-string branch. Close only when a guard lands. No comma-delimited keylist exists in the workbook: every comma-bearing string is free text in a `*_name_long` or `coproduct_*_constituents` cell, none parsed as a list. **Deferred 2026-08-25.**
- `[-]` **TP composition vectors are Li-only.** Confirmed on column `AB`: `AB9` `Li: 2538`, `AB15`
  `Li: 4033`, `AB21` `Li: 1299.5`, with `K: 0; Mg: 0; Ca: 0; Na: 0; B: 0; SO4: 0; Si: 0; Rb: 0;
  F: 0; Cs: 0` in all three. Root cause of every TP reagent dose being a calibration. Blocks the
  stoichiometric leg of C5i. Moves no number today: every TP reagent targets a step basis (`slurry_being_neutralized`, `pregnant_solution_throughput`, `CCD_feed_throughput`), never a constituent name, and every dose derives from `TDS_TP` / `Dose_H2SO4_TP` / `Ca_res_TP`. What it costs is verifiability - `f_imp_TP` = 0.86 stands in for an assay and scales `J28` directly. Still blocks C5i. **Deferred 2026-08-25.**
- `[-]` **JX `sulfate_roasting` POCF 0.875** loses the cake moisture (0.625 x 0.20 = 0.125 t/t) as
  vapour. `fluorine_offgas` = 0 is defensible for F-mass only. **Deferred 2026-08-25.**
- `[-]` **Precipitation preheat duty is unmodeled on all three projects.** `precipitator` carries
  `natural_gas_base_total`, `propane_base_total` and `steam_base_total` all 0.0 in all three ranks
  against `main.tex`'s `Thermal requirements are modeled generically`. Sheet-prose disagreement.
  Preheat HYPOTHESIS at dT = 70 K, `V*rho*cp*dT/(LHV*0.80)`: at cp = 4.0, SP 118.58 gal/t
  (116.71 $/t), TP 87.440 MMBTU/t (440.70 $/t), JX 83.407 MMBTU/t (708.96 $/t); at cp = 3.2,
  94.86 / 69.952 / 66.726. SP + drying reconciles the disclosed 150 gal/t to −4.5% at cp = 4.18.
  Asymmetry is volumetric: SP precipitates from 23.44 m^3/t LCE, TP 251.03, JX 239.27. Three coupled
  decisions: (1) FUEL — propane for SP, natural gas for TP/JX, per the existing two-drying-block
  split; (2) STRUCTURE — `precipitator` is one block instantiated by both `Solution Processing`
  sheets, so any thermal row lands the same fuel on all three, and the fix edits the pathway roster
  in `continuation_prompt.md`; (3) SOURCE — TP's acid plant is exothermic and JX has 800-950 °C kiln
  offgas, so the sulfate entry may be a steam draw. `wash_purify_combo` carries
  `compressed_air_base_total` = 1.0 and zero thermal utilities for the same shared-instantiation
  reason.
- `[-]` **The 0.4 wt% product moisture spec has no home.** Restated on both `Solution Processing` sheets
  at `F46` `=0.7/(1-0.004)`, `F51` `=0.996/1000` and `F56` `=1-0.7/(1-0.004)`. Needs a
  `Constants & Derivations` row before those cells can be rewired.
- `[-]` **`tooling_cost_base` is charged annually.** Confirmed: no `tool_life` row exists on
  `Machine Blocks Data`, so `safe_float(machine_data.get("tool_life"), 1.0) or None` yields 1.0 and
  `calc_crf(dr, 1)` = 1.0, making `tool_cost` the full figure every year. It reaches `avg_opex` only
  through `fixed_over` at 10%. Add a `tool_life` row or document it as an annual consumable charge.
  The acid plant deliberately routes its V2O5 charge as a reagent instead.
- `[-]` **`oversizing_factor` is dead.** Read once at `production_step.py`
  `self.oversizing_factor: float = safe_float(machine_data.get("oversizing_factor"), 1.0)` and
  referenced nowhere else across the six modules. Live values include `multi_stage_ccd_thickening`
  1.15 and `precipitator` 1.2. Decide between wiring it into the sizing path as a design margin on
  `volume_ratio` and striking the column; sweep any `main.tex` passage describing a design margin.
- `[-]` **`proc_avail_factor` is dead.** Read once at
  `self.proc_avail_factor: float = safe_float(machine_data.get("proc_avail_factor"), 1.0)`,
  referenced nowhere else; availability enters only via `unplanned_downtime` and
  `scheduled_maintenance`. Values 0.9-0.92 are set across the workbook **and described in eight
  `main.tex` passages** as live (e.g. `\texttt{proc\_avail\_factor} = 0.92, with
  \texttt{unplanned\_downtime} = 0.03 and \texttt{scheduled\_maintenance} = 0.05`), so striking it
  is a prose edit too. If wired in, every block's `lta` and every capex figure moves.
- `[-]` **`dedicated_line` is inert on continuous blocks.** Confirmed: it is consulted only inside
  `_calc_batch_scaling`; `_calc_cont_scaling` sets `self.machines_required = 1` unconditionally.
  `TRUE` on `attrition_scrubber`, `classifier_generic`, `flotation_generic` and
  `classifier_flotation`, all continuous. Decide between moving them to the batch path and clearing
  the flag; cost impact is not zero if they move.
- `[-]` **SP residue wet density.** `Constants & Derivations` `rho_res_SP` = 1.35 reproduces under
  neither cake-density construction: (0.35/2.4 + 0.65/1.25)^-1 = 1.50188 with brine liquor,
  (0.35/2.4 + 0.65/1.0)^-1 = 1.25654 with water. Adopting 1.50188 would move `V_res_SP` to
  0.218826. Parked as one cell, flagged in its own `Source`. An earlier cake wet-density figure
  from this item is retracted; it reproduces under neither construction. **Deferred 2026-08-25.**
- `[-]` **SP `sls_step` closure.** `Brine-Batch Chemical Purificati` 0.995 + 0.2434469 = 1.2384469.
  Named excess is 0.124069 — 0.047929 precipitated solids at grain 2.4 plus 0.076140 dosed reagents
  at solid density — against 0.238447 required, so the step does not close under the
  `main.tex` L1523 naming test. Separately, `D12` `volume_defining_basis` = `D8` `step_basis` makes
  this **Case 1**, so `D45` = 0.995 is a bulk volume split, while `main.tex` L1358 reads it as
  `a yield rate of 0.995, reflecting a 0.5\% lithium loss to solids during filtration` — a Case-2
  mass reading. Sheet-prose disagreement, unadjudicated. **Deferred 2026-08-25.**
- `[-]` **SP precipitation mother liquor.** Accepted by decision: recycled, zero cost. Exit point
  corrected — the precipitator separates nothing, so the liquor leaves physically at
  `thicken_dewater`, not at `precipitation_step`. `Solution Processing-Chloride` `C54`/`C55`/`C56`
  stay empty. Owed instead: a second coproduct on the `thicken_dewater` column, `D60`
  `coproduct_2_name` = `mother_liquor`, `D61` `coproduct_2_sink` = `process_water_recycle`,
  `D63` `coproduct_2_units` = `m^3 mother liquor / m^3 20% Li2CO3 slurry`. `D62`
  `coproduct_2_conversion_factor` is set at runtime, since it needs the live PLS and slurry
  chemistries: with
      V_s = y * c_PLS * ccf_PLS / (c_slurry * ccf_slurry)      [m^3 slurry per L PLS]
      ml_conv = 1/1000 - V_s                                   [m^3 liquor per L PLS]
  the value on the thickener basis is `ml_conv / V_s`. This is `run_scenarios.py` L204's residual
  rebased from L PLS to m^3 slurry and reassigned from `precip_step` to the thickening step; the
  sulfate branches at L204-205 and L270-272 are unaffected. `D56` = `=1-D45*D46` stands — pressed
  water and mother liquor are two streams on the same basis, not one. Magnitude not
  computed: requires a run. The `C51` 20 wt% declaration that creates the upstream phantom removal
  remains open. **Deferred 2026-08-25.**

---

## Session scripts, recreate as needed

Environment and constructor signature in `continuation_prompt.md` → "Running the Model".
- `ccf_test.py` — recomputes every CCF from parsed wt% strings; checks step-to-step CCF/chemistry
  handoff continuity.
- `li_water_ledger.py` — runs all three projects; per-step lithium ledger
  (`A_k = step_pv × c_Li × step_ccf`) and a water in/out ledger with sink volumes.

---

## Closed

✋ = do not re-open. Items marked **2026-08-25** were closed by the verification pass.

| Item | Closed | Outcome |
|---|---|---|
| **A2-1 maintenance basis** | **2026-08-26** | The count was wrong: five sites carried `maintenance rate of 5\% of CAPEX`, four more carried the same defect in other wording, and the methods-level source at `Maintenance is estimated as an annual cost, as a percentage of all-in fixed-capital investment costs` contradicted `we multiply here by the scaled machine costs` and `expressed as a fraction of scaled equipment cost` in the same chapter. Ten sites landed. Three of them — `liming_system`, `batch_treatment_generic`, `wash_purify_combo` — asserted `inherits zero maintenance cost`, the inverse of the code: `maint_override` is populated on 5 of 39 block families only, so a blank inherits `facility.maint` = 0.05. `sulfate_roasting_train_lepidolite` carried the same claim as `both zero in the current parameterization`. Scope also corrected `project-level` → `facility-level`. `continuation_prompt.md` attribute 13 already stated the correct basis and needed no edit. ✋ |
| **A2-2 unit notation** | **2026-08-26** | The item counted two families; three were live. `textsuperscript{3}` 154, `m$^3$` 108, `\text{…m}^3` 3, plus `m$^2$` 7 and `textsuperscript{2}` 4 on the square-metre leg, and 9 split forms `\si{m^3}/{h,yr,batch}`. Convention decided and swept: literal-with-caret `\si{}`, matching the pre-existing majority. `\si{` 318 → 574; every competing form now zero. One siunitx behaviour recorded: `\si{kg Li/m^3}` collapses the interword space to `kgLi/m³`; `\si{kg~Li/m^3}` and `\si{kg\,Li/m^3}` both render correctly, `per-mode=symbol` does not fix it. Nine `(\si{m^3} $\cdot$ ppm)` unit products left split across the macro boundary by decision. Chemistry folded in the same pass: 4 `textsubscript`, 6 `CO$_2$e`, `SO$_4$`, `CO$_3$`, `\text{H}_2\text{O}` → `\ce{}`; 17 bare `CO2` and 6 `\ce{CO2}e` → `\ce{CO2eq}`; three `\ce{\text{…\ce{` nestings unwound to mhchem arrow syntax. One compile break found and fixed: orphaned `}` at `= 74.09/24.305$}`. ✋ |
| **A2-13 the `73` scrubbing sentence** | **2026-08-26** | RESOLVED, no edit owed. The tex half reads `18.2 m³ arrives with the classifier recycle and 73.0 m³ is dosed`, which is net demand and correct. 0.912 × 1.613 = 1.471056; 0.2 × 1.613 × 0.912 = 0.294211; difference 1.176845 ≈ the 1.177 dose. Per 100 m³ output at 100/1.613 = 61.996 basis: 91.20 / 18.24 / 72.96. ✋ |
| **SP six re-measure and 18/18 gate restore** | **2026-08-26** | Cluster closed. `check_workbook_formula_cache` EMPTY. SP 5585.498705 / 6979.621035 / 4421.071214 and 6.506474 / 8.480523 / 4.737946; TP and JX bit-identical to the prior gate, so the four SP edits did not leak. SP delta is scenario-invariant at +1.233326 $/t and +0.000822 t/t. `V_res_SP` reproduces to 10 dp from its named-range operands: Mg(OH)2 40.603449 + CaCO3 74.425231 = 115.028680 kg/m^3, / (0.35 × 1.35 × 10^3) = 0.2434469419. `Solution Processing-Chloride` `D56` = `=1-D45*D46` = 0.8002920702 and `E56` = `=1+E28-E45*E46` = 0.11 both CONFIRMED, both to `process_water_recycle` at `sc.register_sink_cost("process_water_recycle", 0)`. Attribution of the +1.233326 to a single edit was not measured and remains a HYPOTHESIS. ✋ |
| **Eight stale TP anchors** | **2026-08-26** | All eight landed. Abstract, `fig:04-cost-emissions` alt text and results now read TP `\$8,700 [\$7,100---13,900]/t` and `17.1 [11.5---23.9]`; sensitivity alt text and caption `$\sim$8,700/t` and `$\sim$17.1`. Item 6 resolved not as a swap but as a boundary decision — the three named steps are 73.420824 + 2003.798130 + 906.646025 = 2983.864979 = 34.2846% of 8703.225450, landed as `approximately \$3,000/t` and `about one third`, with the acid plant named separately at 1974.522640 + 148.435800 = 2122.958440 = 24.3928%. Item 7 landed at `$\sim$\$765/t` = 150.843506 + 210.979816 + 403.118582, excluding `waste_pile` 799.595590. Item 8 landed at `$\sim$13.4-22.0`. The prior 898.9586 $/t and 16.2942---27.5201 t/t did not reproduce and are retracted. Note the surviving L207 claim `The single largest cost is that of sulfuric acid production` holds only at facility granularity — at step granularity `Impurity Removal` 2003.798130 exceeds `Sulfur burning` 1974.522640, and L209's `despite ranking second in cost` rests on the same grouping. |
| **Line-205 paragraph rewrite** | **2026-08-26** | Landed. The inversion is stated: 8703.225450 against the disclosure's 8039 = +664.225450, +8.2626%. Lime landed at `approximately 9,900 kg \ce{CaO}/t` against the measured 9924.0152 (`lime` `abs_usage` 662,924,213.9735 / 66,800). The grade-degradation direction was corrected to `our estimate understates life-of-mine costs and further widens the gap against these figures`. **User decision 2026-08-26: `renders our estimate to be notably higher what is reported in the disclosure` stands as written, no edit.** The prior lime figure 12903.3155 kg/t did not reproduce and is retracted. ✋ |
| **Impurity-removal emissions quartet** | **2026-08-26** | All four re-measured on a clean midpoint rebuild and landed. Impurity Removal 12450.3582 kg/t = 12.4504 t/t (s2 303.5096, s3 12146.8486), landed as `$\sim$12.5` and still the largest emissions contributor. Acid Leaching 139.1397 kg/t = 0.1391 t/t, entirely scope 2, landed as `$\sim$0.14`. Sulfur burning scope 3 = 2606.3817 kg/t = 2.6064 t/t, landed as `2.61`. The `free \`clean' power` claim is supported as written: Sulfur burning scope 1 = 0.0000 and scope 2 = −1320.5862 kg/t, a credit. Step co2 `SUM` = 17068.4178 kg/t closes exactly on `avg_co2`. |
| **Tornado caption drivers** | **2026-08-26** | Re-measured; three of four claims need no edit. `sulfur` leads cost at 5034.1389, 5.52× the next driver, so `The dominant source of cost uncertainty ... is sulfuric acid` stands. `process_water` 911.4658 is second, so `the second largest cost driver overall` stands, margin 18.3044 over `lime` 893.1614 (2.05%). `lime` 893.1614 against `soda_ash` 688.7134 = 1.2968×, so `similar magnitude to one another` stands; ordering is lime above soda ash, both below process water. Only the lime emissions range moved, landed at `$\sim$13.4-22.0` from 13396.5322 → 22030.4254 kg/t. |
| **Substitution finding** | **2026-08-26** | Landed at the SP-adjacent TP paragraph, not at line 205: the disclosure removes magnesium via evaporative crystallization at higher thermal energy demand, the generic model precipitates it with quicklime at 9,900 kg \ce{CaO}/t against the disclosed 2,630. The Li-only caveat landed as `As the Thacker Pass process composition does not specify constituent ions, the modeled quicklime dose are calibrated against the disclosed magnesium removal duty rather than any assay-derived stoichiometry.` **User decision 2026-08-26: no explicit not-like-for-like sentence is owed — the flowsheets differ, so the comparison is self-evidently not like-for-like.** Basis resolved: `Sulfuric Acid Leach` `reagent_1_name_long` = `CaO` and `reagent_1_units` = `kg CaO / m^3 pregnant_solution_throughput …`, so the TP figure is CaO-basis and the `\ce{CaO}` labels are correct; the same `lime` material key is dosed as Ca(OH)2 on `Brine-Batch Chemical Purificati` and `Brine-Solvent Extraction-Boron`. |
| **Disclosure vintage at every comparison** | **2026-08-26** | Closed by user declaration 2026-08-26. `rothFeasibilityStudyNational2022` is named at the $88/t on-site acid comparison; `sgscanadaincSK1300Technical2024` appears at 50 anchors including the 66,800 t/yr water-intensity comparison. |
| **Disclosure cost-category mapping (Tables 19-3 / 18-25)** | **2026-08-26** | Closed by user declaration 2026-08-26. `135,092`, `18-25` and `19-3` all return zero hits in `main.tex`; no host sentence exists and none is owed. The surviving scope note is retired with it. |
| **`main.tex` L1362, SP residue paragraph** | **2026-08-26** | Landed. `0.232` → `0.2434` at both occurrences and `Mg: 12,960 ppm; Ca: 1,535 ppm` → `Mg: 14,250 ppm; Ca: 1,688 ppm`. The doses stand verified live on the sheet — `reagent_1_constituent_ratio` 3.6581115 at `reagent_1_target_constituents_eliminated` 0.95, `reagent_2_constituent_ratio` 3.173439792 at 0.9. `40.6` / `74.4` / `115.0` reproduce at the new chemistry (40.603449 / 74.425231 / 115.028680) and did not move. `1.35 g/cm\textsuperscript{3}` remains B2b debt. The disclosed 1.3 t \ce{CaO}/t cross-validation is not re-stated in the text; measured SP consumption is 1535.3432 kg Ca(OH)2/t LCE = 1.1620 t CaO/t equivalent, 10.6% under it. |
| **`main.tex` L1285, pond CCF sentence** | **2026-08-26** | Landed. Reads `and is defined as brine density multiplied by evaporation rate` and `a CCF of 9.4225 $\times$ 10\textsuperscript{-4} kg brine/(m\textsuperscript{2} $\cdot$ year) per ppm`, with the `A = \dot m_{\text{Li}}/(c \cdot \text{CCF})` sentence. **User decision 2026-08-26: the `(0.8906~m/yr)` and `(1058 kg/m\textsuperscript{3})` unit parentheticals are not wanted, no edit.** |
| **TP overall recovery, ore intensity and the S2 precipitation-recovery claim** | **2026-08-26** | Dropped by user declaration 2026-08-26; do not raise again. All four prior figures were superseded and did not reproduce: on the current stack recovery is 0.791831 (12,549.9743 t Li produced / 15,849.3069 t Li in fresh ore, at `crushing` 6,244,801.7769 t/yr and `Initial Concentration` Li 2,538 ppm), fresh ore 93.4851 t/t LCE, `V_leach` 7,600,155.3289 m^3/yr, leach-feed solids 48.9232 t/t LCE. The recorded 0.73473 / 100.7559 / 58.3340 / 8,191,263.9807 are retracted. The S2 mechanism remains closed and must not be re-opened. ✋ |
| **SP brine chemistry conflict (P4)** | **2026-08-25** | `Project-Specific Data` `K15` STANDS at Mg 14,250 / Ca 1,688. `main.tex` L1285 prose and the L2133 `Strong Brine` row both agree with the sheet; the defect was the L1362 parenthetical `(Mg: 12,960 ppm; Ca: 1,535 ppm)`, whose provenance **cannot be verified from project sources**. Landed: `Brine-Batch Chemical Purificati` `D56` = `=V_res_SP` = 0.2434469419 off a live reacted-basis chemical balance; `Constants & Derivations` rows 63-65 `s_res_SP` / `rho_res_SP` / `V_res_SP`; named ranges `Rho_SP_IC`, `f_Mg_SP`, `f_Ca_SP`. The L1362 CaCO3 term reproduced under none of seven dose bases and is retracted. `main.tex` L1362 rewrite owed — see A1. |
| **SP evaporation pond CCF (P4)** | **2026-08-25** | No defect. `Brine-Evaporation` `D10` = `='Project-Specific Data'!K11/10^6*('Project-Specific Data'!K23*365)` = 0.0009422548 is correct, and `main.tex` L1285's value `approximately 0.000942` agrees with it. Prose errors only: `density divided by evaporation rate` (should be multiplied) and the unit `kg $\cdot$ year/m\textsuperscript{2}` (should be kg/(m^2·year), as `D11` already states). rho/E is dimensionally impossible — (kg/m^3)/(m/yr) = kg·yr/m^4 — and reverses the area-vs-rate direction that L2543 states correctly. The pond CAPEX shortfall claim is retracted. `main.tex` L1285 rewrite owed — see A1. |
| **Chloride `pressed_water` (P4)** | **2026-08-25** | `Solution Processing-Chloride` `D56` = `=1-D45*D46` = 0.8002920702, sink `process_water_recycle`, zero-cost at `facility.py` `sc.register_sink_cost("process_water_recycle", 0)`. Closes 0.1997079298 + 0.8002920702 = 1.0000000000. Mass cross-check per m^3 slurry at rho = 1.117585: 223.517 kg Li2CO3, cake 319.310 kg = 0.2017252 m^3 (reproduces `D46`), water expressed 798.275 kg; the 0.002 gap to 0.800292 is the 1% bulk yield loss carried out with the water. |
| **Chloride wash water (P4)** | **2026-08-25** | `Solution Processing-Chloride` `E56` = `=1+E28-E45*E46` = 0.11, same sink. `E28` = 0.1 is basis-additive per `continuation_prompt.md`, so closure is 1.0 + 0.1 in against 0.99 + 0.11 out. `E28` stays 0.1 gross; netting the purchased dose against the recycle remains the separate accounting question. |
| **CCF-row mismatches** | **2026-08-25** | Swept. Chloride `D11` is populated with `kg Li2CO3 / m^3 20% Li2CO3 slurry • 1/PPM`, identical to `D23`. The shifted numbering (yield 51 / conversion factor 52 / coproduct conversion 62) is `Sulfuric Acid Leach` only; every other pathway sheet runs 45 / 46 / 56, and all eight remaining addresses resolved without relocation. Five strings agree directly with their paired CCF construction. The three on runtime-overwritten cells — `Sulfuric Acid Leach` `C23`, `Sulfate Roast-Water Leach` `C23`, `Solution Processing-Sulfate` `C11` — describe the live value, not the sheet literal. **User decision 2026-08-25: all three are correct as written, no edit.** ✋ |
| **Dose-placement / yield-semantics declarations** | **2026-08-25** | Swept against every declared step. Volumetric closure reproduced at JX `classifying` (0.0000% against `1/(1+CL)` = 1/3), JX `flotation` (Case 2, 0.1839361 + 0.8160639 = 1.0000000000), JX `crushing` and `grinding` (exact), TP `acid_leaching` (`=1/G51`, 1.0000000002), JX `water_leach` (Case 2, +0.0000% against 1 + wash), JX `impurity_removal`, SPS `precipitation_step` (closes by construction), SPS `thicken_dewater` (+0.2017%, in band), `excav_load` (exact, symbolic). Resolved into three `continuation_prompt.md` edits: the `(1-y)` wording, JX `crushing` added to the unit trap, JX `grinding` moved to the physical-split list. TP `classifying` survives as a queue item. |
| **SP electricity kWh/m^3 claim** | **2026-08-25** | The recorded "3,395,635.23 kWh/yr" and "565.9392 kWh/t LCE" were the `cost` and `output_avg_cost` fields of `sc.get_total_utilities()["electricity"]` — $/yr and $/t read as energy. `cost/consumed` = 0.09 = `elec_price`, the uniform 11.111111 factor. Measured: 37,729,280.3596 kWh/yr, 6,288.213393 kWh/t LCE, `brine_pump` 1.500000 kWh/m^3 raw brine, 97.657% of SP electricity. Derivation checks bottom-up: E = 1058 x 9.81 x 300 / (0.70 x 3.6e6) = 1.235592857 from `K11` `Initial Density`; the sheet's 108 kWh/h = 1.500000 kWh/m^3 is that relation at H = 303.498 m or η = 0.691932 at H = 300 m, both inside the stated 90-550 m band. Sole residual: prose rounds P_base 88.962686 → 90 kW, +1.1660%; correcting moves SP opex −6.370033/−6.900861/−5.839206 and co2 −0.022592/−0.024475/−0.020709. `K107` unusable, unit string `Mmw/h total (?)`. ✋ |
| **CEPCI 2025 = 810** | **2026-08-25** | Stands as a flagged assumption at `Constants & Derivations` `B48`, `D48` `Assumed 2025 CEPCI value`. The data-file half is retracted: no CEPCI 2025 = 800 exists anywhere in the workbook. Full sweep of every formula and comment on all 19 sheets returns six consumers, all formula-linked to the named range — `Machine Blocks Data` `CL30:CQ30`, the `sulfur_burner` / `acid_absorption` pair at `=…*CEPCI_2025/CEPCI_2005*0.6` and `*0.4`. All four 800-based instances were `main.tex` prose escalating to literal cells, now landed at 810 with the 390 / 389.5 reconciliation settled on 389.5: `$810/389.5 \approx 2.08$` at `thickener_generic`, `\$437,100` / `\$567,100` / `\$1,701,300` / `\$1,700,000` in its midpoint derivation, `($\times$2.08)` at `multi_stage_ccd_thickening`, and `\$303,600` with `\$757K--\$894K` at `mechanical_dewatering`. Zero cell edits and zero metric movement — 1,701,300 still rounds to the `BA30` literal 1,700,000, and `BF30`/`BG30`/`BH30` are selected against the Porvoo cross-checks, not this chain. No `CEPCI_1998` cell exists, so which of 390 / 389.5 is the published annual **cannot be verified from project sources**. |
| **TP `impurity_removal` yield = 0.99** | **2026-08-25** | Accepted debt; see B2b. |
| **`ccd` gate-2 volumetric residual** | **2026-08-25** | Live residual 0.0434996924 per basis, reproduced from the sheet and independently from the model's own objects. Adjudicated definitional, not a defect; accepted debt with the full attribution in B2b. |
| **JX seam `excav_load -> crushing` dev 0.42502** | **2026-08-25** | Not a defect. Gate 5 exact at both steps: `R = ccf_in/(IPCF*step_ccf)` = 1.000000000000 at `excav_load` and at `crushing`. Volumetric seam exact — `excav_load` forward exit 53,836,087.9328 x 0.95 x 0.108024691 = 5,524,845.4437 m^3/yr equals `crushing.step_pv`/IPCF to 0.000e+00. Gate 1 closes once the loop is deflated: `excav_load` exit 15,837,679.8017 kg Li/yr at the `rom_ore_feed` grade 1,858 ppm, `crushing` raw forward exit 47,037,909.0110 ÷ loop 3 = 15,679,303.0037 = exit x `y_crushing` 0.99, dev 0.000e+00; `classifying` exit 14,581,751.7920 against 14,581,751.7934, dev 1.0e-10. Loop closure `y*POCF+(1-y)*POCF+(1-POCF)` = 1.000000000000 and entry inflation x exit deflation = 3 x 0.3333333333. 0.42502 does not reproduce; the nearest exact quantity is 0.425000000 = `(1-dilution) x POCF_excav_load x IPCF_crushing` = 0.85 x 0.108024691 x 4.628571429, the raw internal edge with the x3 recirculation left in and the 0.95 mining recovery omitted — the read the recirculation convention forbids. The residual 4.7e-5 gap is unexplained and not fitted. **The exit deflation sits on `classifying`'s POCF, not `crushing`'s**, so both step_pv are x3 loaded: JX mine size is 8,524,047.2560 t ore/yr on 53,836,087.9328 t/yr moved at strip 5, NOT the 25,572,141.77 `crushing` figure. Independent closure: 8,524,047.256 t x 1,858 ppm = 84,299.5361 t LCE contained against `apv` 46,000, overall recovery 0.545673 against the product of the thirteen declared step yields 0.543491. ✋ |
| **`main.tex` sludge dewatering ceilings** | **2026-08-25** | Prose-only; `x_hyd` = 0.26 is correct and no model change was owed. `s_ceil` and `S_CEIL_PURE` verified against the other sink's paragraph — `mgcake_stack_nv_35` at `x_hyd` = 0.50 returns 0.235714 / 0.375000 / 0.667857 against `main.tex`'s 0.236 / 0.375 / 0.668. The quoted 0.446 / 0.772 share no single `x` (0.087444 and 0.185233 respectively), so there was no `x_hyd` to move them to. `facility.py` raises on `s_out > cap + 1e-9` and never has: at `x_hyd` = 0.26 the train targets 0.30 and 0.50 sit under ceilings 0.324803 and 0.744427. Every cost figure in the sentence already reproduced at 0.26 — thicken dW 1.691792, 0.383491 $/t DS, 2.323387 kWh/t DS; press dW 1.333333, 5.280667 $/t DS, 17.013333 kWh/t DS; `sc.sink_elec["sludge_stack_nv_50"]` 19.336720. `main.tex` now reads `blended ceilings of 0.325 and 0.744` and `blended pressure-filtration ceiling of 0.744`. Zero cell, code or metric movement. |
| **`waste_pile` never registered** | **2026-08-25** | Registered at 1.5 $/t on the tonnage basis via `WASTE_ROCK_COST` in `tailings_handling`, TP and JX. Residual of the TP 2024 S-K 1300 Table 12-4 waste-and-topsoil rate of 2.71 $/t excl. D&B less the model's own blasting and loading on the same tonnage. Model all-in mining then reads 2.5155 $/t mined against the disclosed 2.5 in Table 18-20 and 1,698.70 $/t product against 1,767. Reuse of `rock_pile_*` was rejected: those register as $/m^3 and the stream is tonnes. |
| **TP lime dosed on total dissolved sulfate** | **2026-08-25** | `f_imp_TP` = 0.86 at `Constants & Derivations` B90, applied in `J28` and the Mg(OH)2 term of `J62`; `J46` and `sludge_stack_nv_50` `s_feed` = 0.206 follow. Sulfate paired with interlayer K/Na needs no hydroxide precipitation; share derived from illite charge stoichiometry, bracket 0.83-0.92, taken at the Srodon et al. (2009) value. Explicitly NOT fitted: matching disclosed lime needs 0.204, matching disclosed opex needs 0.381, and the two cannot both hold. ✋ |
| **Precipitation yield asymmetry** | **2026-08-25** | TP 0.97 calibrated to the disclosed 80.4% LOM recovery (chain returns 78.9%) and consistent with 2022 Table 15-2 circuit losses; JX 0.90 on lab-review values. Carried per project through `Carbonate Recovery Factor`, read in both branches of `clay_lepidolite` before `ml_conv`, guarded on `not in (None, "-")`. Neither is a single-pass equilibrium yield: at `c_PLS_TP` the feed is 7.71 g/L as Li2CO3 against ~8.3 g/L solubility at 90 C, so both presuppose liquor recycle. |
| **`rock_pile_*` commented out of `TAILINGS_SINK_PARAMS`** | **2026-08-25** | Opened and closed the same day. While commented, JX `crushing -> dust_fines -> rock_pile_cn_100` priced at zero via `sink_costs.get(sink, 0.0)`. Both entries restored; confirmed live by the +3.868488 $/t LCE JX move. |
| **`mother_liquor` conversion factor dropped** | **2026-08-25** | Opened and closed the same day. Three lines were lost in the `Carbonate Recovery Factor` edit: the `set_conversion_factor("mother_liquor", ml_conv, ...)` call in both branches and the `wastewater_discharge_cn` sink assignment in the Lepidolite branch. `ml_conv` was computed and discarded, so both projects fell back to `C56` = 0.0 and `C55` = `process_water_recycle`; JX lost 217.600577 $/t LCE and TP lost 8.77 Mm^3/yr from its water balance, neither raising an error. All three restored and verified. |
| **`multi_stage_ccd_thickening` landing record** | **2026-08-25** | Not a defect: live 110/90/70 and 7.8M/6.6M/5.3M reproduce exactly from the `main.tex` derivation on the 877 tpd cake-solids basis, a basis of ore solids charged is a different quantity and must not be substituted for it. ✋ |
| **Precipitation soda ash `C28`** | **2026-08-25** | Doses stand as engineering estimates at 16.55 (sulfate) and 11.5 (chloride) kg/kg Li = 2.1677x and 1.5062x stoichiometric; `main.tex` and both `C5` notes rewritten to match, measured consumption 3510.838171 kg/t LCE (TP and JX precipitation) and 2263.504848 (SP). ✋ |
| **Sandbox emissions non-reproduction** | **2026-08-25** | Full run in a clean sandbox: no `Attribute utility_impact ... is not defined as a facility attribute` error, and 9/9 `avg_co2` bit-identical to the gate. Environmental, not a model defect. |
| **Gate-3 builder label mismatch** | **2026-08-25** | `_build_steps_cost_series` and `_build_steps_impact_series` return identical label lists for all three projects at `detail=2`; the impact builder has no `detail=1` mode. Residual is a `detail=1` naming inconsistency inside `get_step_cost_report`, moved to A2. |
| **Swell factors sourced; no delta owed** | **2026-08-25** | `AB28` 1.2 anchors on the 2022 Table 17-1 transport density, 1.9/1.2 = 1.583333 vs 1.6 t/m^3; `AJ28` 1.75 on the toolbox granite band. S reaches only the `rom_ore_feed` loose-volume stream. No effect delta is owed; the `[RUN]` tag is retired. ✋ |
| **TP total tailings tonnage** | **2026-08-25** | Re-measured 122.8763 t DS/t LCE — `gangue_stack_nv_20` 39.3606, `claycake_stack_nv_62` 42.9617, `sludge_stack_nv_50` 40.5540. Sink unit costs 3.8323 / 4.9109 / 9.9403 $/t DS. |
| **Tailings prose figures** | **2026-08-25** | All four `main.tex` figures reproduce: coarse gangue 3.8323 and clay cake 4.9109 $/t DS, impurity sludge 9.9403, clay cake 42.9617 t DS/t LCE. |
| **TP limestone calibration target** | **2026-08-25** | `f_Neut_TP` = 0.109 at `B85`, `H28` = 25.92816142 kg/m^3 slurry, delivered 2949.97087172497 kg/t LCE against the 2.95 t/t target, −0.001%. `f_Neut_TP` also enters `salts_CCD_TP` and `s_cake_CCD_TP` → `TDS_TP`, so the response is not linear and the target closes only once `AB21` is re-transcribed by hand. ✋ |
| **TP limestone wrong basis and wrong reagent name** | **2026-08-25** | `H28` is no longer the literal `11.2`. It reads `=f_Neut_TP*Dose_H2SO4_TP*M_CaCO3/M_H2SO4*G10*10^6` = 18.7919702 and moves with the acid dose; the comment reads `aim for ~2.95 tonne limestone / tonne LCE`. **The calibration-target half REOPENED the same day** — delivered is 2.3043 t/t, −21.9% — and is closed above. |
| **Mixed-basis emissions brackets** | **2026-08-25** | `main.tex` now reads TP `14.0 [8.9---20.0]`, matching the recorded co2-ranked `[8.872134 - 19.968181]`, on the same basis as SP `6.5 [4.8---8.4]` and JX `27.6 [21.7---38.8]`. All three co2-ranked; only re-measurement remains, inside the S4 batch. |
| **Sweep coverage was results-scoped** | **2026-08-25** | Whole-file greps return zero hits for `9,200` and for a 95% evaporation claim. Both appendix duplicates are gone. |
| **`main.tex` Classification writeup stale** | **2026-08-25** | Rewritten: the runtime split is stated as `0.109 m³ per m³ of step basis` make-up and `0.091` from thickener overflow, with the `process_water` dose set to zero claim removed. |
| **JX roasting natural gas** | **2026-08-25** | Writeup now states `Fired duty is therefore $q_\text{demand}/\eta$` with a 1.59 GJ/t demand and an explicit 0.40 / 0.50 / 0.60 band; `thermodynamically consistent` is gone. The band and the ~0.50 GJ/t enthalpy remain flagged as estimates — a P5 item, not a defect. |
| **C3e prose defects** | **2026-08-25** | `21,630` and `tailings_65` both return zero hits in `main.tex`. |
| **Two distinct 92% figures on the TP chain** | **2026-08-25** | No conflation: the classification writeup reads `The yield rate is set to 0.92, matching the 8\% loss to coarse gangue`, the leach writeup `The output yield rate is 0.92, the disclosure's expected average lithium extraction`. Note the row anchors moved — yield is now row 51, so the old `E45`/`G51` pair is `E51`/`G51`. |
| **CCD cake solids 62 or 65 wt%** | **2026-08-25** | `main.tex` now reads `leaves the CCD step as thickened underflow at $s_{\text{feed}} = 0.33$ and is pressed to $s = 0.62$`. No 65 wt% claim survives. |
| **SP soda ash prose/sheet transposition** | **2026-08-25** | No defect. `Brine-Batch` carries three reagent rows — lime→Mg at `=M_CaOH2/M_Mg*1.2` = 3.6581115, soda ash→Ca at `=M_Na2CO3/M_Ca*1.2` = 3.173439792, soda ash→Mg at `=C34*C28*M_Ca/M_CaOH2` = 6.279454598 with 0.0 elimination — and `main.tex` derives all three with the dosing-basis rationale stated. |
| **`J62` ten significant figures, no source** | **2026-08-25** | Now a formula with a stoichiometric comment naming each term. |
| **`_build_steps_cost_series` drops sinks** | **2026-08-25** | Guarded: `rec.get("total_cost", rec.get("variable_costs", 0.0))` with bucketing to `Tailings Management` / `Wastewater Treatment`. The API inconsistency itself is downgraded and closed. |
| **`D34` comment "73"** | **2026-08-25** | Comment rewritten to `Total water needs here are 1.177 m³ water / m³ 30 wt% basis slurry`. The tex half of the item stays open in A2. |
| **`Material Data` sulfur CO2 unit (C5e D-3)** | 2026-08-23 | `co2` 0.30 under `kg CO2e/kg`, confirmed 2026-08-25. |
| CD — `Constants & Derivations` build | 2026-08-07 | Sheet built and internally correct. |
| CD2 — consumption pass | 2026-08-07 | Workbook rewired onto the roster; zero error cells. |
| CD3 — JX PLS carrier pair + IR restructure | 2026-08-08 | R = 1.000000 at every JX primary-input seam; the ×4.5925 was Case-2 sizing at `water_leach`. |
| Mixing rule for solution densities | 2026-08-07 | O1 decided: ideal volume additivity at grain density. |
| C0 / C1 / C2 | — | Unit-carrier audit, coproduct convention, and the classification/flotation/thickening rebuild. |
| C3a / C3b / C3c / C3d / C3g | — | Carrier handoff at CCD; beneficiation upgrade on the POCF with a routed reject; recirculation loop; JX roast ratio; acid-leach identities. For C3g the VALUE of `I52` belongs to C5i — do not gate on the number. |
| C4a / C4b / C4b-1…4 | 2026-08-04 / 08-06 | Circuits close to 0.0000%; structural make-up replaces `f_r`, retired. |
| C4d — `main.tex` "Modeling of Water" | 2026-08-11 | `app:04-methods-system-water` written. |
| C5e — TP sulfuric acid | — | Dose anchored on leach feed solids; `ReagentFacility` route. |
| C5f-1 / C5f-1b / C5f-2 / C5f-4 | 2026-08-08 / 08-09 | `TAILINGS_SINK_PARAMS` + registration loop; staged dewatering train; `S_CEIL_PURE`, `TSF_OPEX`, `STORAGE_CAPACITY_COST`. **Note the live params have drifted from the record**: the JX leach-residue sink is `slag_stack_cn_65`, not `slag_stack_cn_75`, and `sludge_stack_nv_50` reads `x_hyd` 0.26 (recorded 0.28) and `s_feed` 0.229990 (recorded 0.094899). |
| C5g — tailings sink emissions link | 2026-08-09 | Scope-1 fall equals scope-2 rise to 1e-4. Residual members moved to A2. |
| C5j — wastewater sink rework | 2026-08-11 | Split by jurisdiction, value-neutral at $1/m^3. Impact factors permanently out of scope. |
| C5k — TP on-site acid plant fidelity | 2026-08-23 | Both blocks costed and written up. |
| C6 / C7 | 2026-08-11 | Headline sweep-and-fix; JX tailings claim landed at both anchors. |
| S1 — impurity-removal doses | 2026-08-24 | Confirmed on the sheet 2026-08-25: `J28` = `=TDS_TP*f_imp_TP*M_CaO/M_MgSO4*J10*10^6` = 71.44656935, `J34` = `=Ca_res_TP*M_Na2CO3/M_Ca` = 2.64453316, both stoichiometric formulas with sourced comments. The old carrier-drift `[!]` on `J28`/`J34`/`J62` is closed with it. |
| S3 — ore and acid intensity | 2026-08-24 | Grade chain parameterised; `AB15` 4,033, `AB21` 1,299.5, `c_PLS_TP` 1299.486526, all confirmed 2026-08-25. ✋ |
| §2b — tailings cost breakpoint | 2026-08-08 | Breakpoint tables deleted; cost continuous. |
| SP soda ash dose contradiction | 2026-08-12 | Two root causes landed in `helpers.py` and `apply_reagents`. |
| TP top-3 emissions range | 2026-08-20 | A ranking mismatch, not a defect. |
| JX water leach residue conversion | 2026-08-08 | `J56` `=(1-J46)`; agreement to 2.6e-10. |
| TP classifier feed / ore and acid intensity | 2026-08-24 | Closed by S3. ✋ |
| Acid plant electricity | 2026-08-23 | Moved to the disclosed net export of 476.5 kWh/t S. ✋ |
| TP lithium-processing electricity gap | 2026-08-23 | 0.2959x adjudicated a flowsheet difference. ✋ |
| Sulfuric acid plant writeup | 2026-08-23 | Both blocks and the facility section written. |
| `sulfur_burner.conservative` `CL16` sign | 2026-08-23 | Corrected to −17,100.0. Any run quoted from `1de75b10` conservative is wrong. |
| Residue dewatering at the sink | 2026-08-23 | `s_feed` mechanism. The electricity estimate from this item is retracted. |
| CCD basis excludes wash water | 2026-08-23 | The defect was the closure: `w_r_TP` = 3.3 declared, `TDS_TP` derived. |
| `Locational Data` `diesel_price` US_NV | 2026-08-09 | `=4.2/3.785` = 1.109643329, confirmed 2026-08-25. TP-only, −774.06 $/t LCE. |
| IPCF / POCF unit sweep | — | All seven live pathway sheets swept. |
| `rom_ore_feed` unit contradiction | — | Convention in `continuation_prompt.md`. |
| TP crushing `C22` | — | Input CCF set in code as `ipcf * step_ccf`. |
| Drying & Packaging 0.70 vs 0.7028 | 2026-08-06 | APV basis = packaged product at 0.4 wt% moisture; `F46`/`F51`/`F56` confirmed formula-encoded 2026-08-25. |
| Roasting / `water_leach` prose literals | — | CCF half at C4b, prose half at C3d. |
| TDS comments and unit strings at 7.5 wt% | 2026-08-24 | `I57`/`J10`/`J22`/`J57` all restated on `TDS_TP`; confirmed identical formulas 2026-08-25. |
| JX ROM moisture | 2026-08-06 | Declared 0% as a stated conservatism. |
| TP `classifying` dilution water | — | 0.2004648 m^3/m^3, the 20→15 wt% dilution. |
| `main.tex` swell-factor writeup | — | Landed at four anchors; the bib key is tertiary. |
| `excavation_loading_generic` 7 t/cycle | — | Prose claim deleted; the sheet's 10.0 stands. |
| `excav_load` output CCF | — | `loading.step_ccf * rho_loose`, confirmed in `run_scenarios.py` 2026-08-25. |
| `Machine Blocks Data` `F42:K42` | — | An FTE-per-m² staffing factor for the evaporation ponds, NOT a grain density. |
