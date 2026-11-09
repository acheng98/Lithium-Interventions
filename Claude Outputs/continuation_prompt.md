# Continuation Prompt: Lithium Technoeconomic Model Block Writeups

## Context

I am finishing a scientific manuscript on the technoeconomics of lithium carbonate production, comparing three projects:

- **Silver Peak** — Nevada brine evaporation, ~6,000 t Li₂CO₃/yr
- **Thacker Pass** — Nevada clay sulfuric acid leach, ~66,000 t/yr
- **Jianxiawo** — Jiangxi China lepidolite sulfate roast–water leach, ~46,000 t LCE/yr

My model uses a hierarchical structure: supply chain → facility → production step → machine block. I need help writing up the **machine block** layer in LaTeX, in addition to validating the inputs used in the model and model outputs, following the format and methodology established in prior work (described below).

---

## ⚠️ Critical: Do Not Trust Data Values

**Do not trust any numerical values I give you without independently deriving or cross-checking them.** Numbers in my spreadsheet, writeup notes, or casual conversation may be:

- Derived at the wrong throughput basis
- LLM-estimated with unclear provenance
- Copied from an inapplicable source (e.g. road freight costs applied to mine haulage)
- Unit errors (e.g. Btu/gal misread as Btu/L)
- Scaled incorrectly (e.g. wrong reference scale, wrong exponent)

For every numerical value: **verify the derivation, show intermediate steps, flag assumptions, and explicitly state when a number cannot be independently verified.** If a value looks wrong, say so and re-derive it. Do not simply accept values because I present them.

---

## Active Pathways and Machine Blocks

Eight pathways are modeled. **Verify this roster against the `machine_default` row of each pathway sheet before use.**

| Pathway | Blocks |
|---|---|
| Brine-Evaporation | `brine_pump`, `evaporation_pond` (lined + unlined) |
| Blast Mining | `blasting_generic`, `excavation_loading_generic` |
| Non-Blast Excavating | `excavation_loading_generic` |
| Brine-Batch Chemical Purification | `batch_treatment_generic`, `thickener_generic` |
| Sulfuric Acid Leach | `crushing_cycle`, `attrition_scrubber`, `classifier_generic`, `acid_leach_circuit`, `thickener_generic`, `multi_stage_ccd_thickening`, `staged_neutralization` |
| Sulfate Roast–Water Leach | `crushing_cycle`, `classifier_generic`, `flotation_generic`, `thickener_generic`, `high_energy_grinding_mill`, `mechanical_dewatering`, `sulfate_roasting_train_lepidolite`, `water_leach`, `staged_neutralization`, `solid_liquid_separation` |
| Solution Processing–Chloride | `thickener_generic`, `precipitator`, `wash_purify_combo`, `drying_packaging_propane` |
| Solution Processing–Sulfate | `thickener_generic`, `precipitator`, `wash_purify_combo`, `drying_packaging_generic` |
| Sulfuric Acid Plant | `sulfur_burner`, `acid_absorption` — Thacker Pass only, via `reagent_plant.sulfuric_acid`. Both written up as of `main.tex` `6b63b3d4`; electricity is disclosure-anchored on `sulfur_burner`, and `acid_absorption` carries none. |

A block writeup that exists for a block no pathway instantiates is a finding. Inactive blocks are either developed, deleted, or explicitly marked deprecated — never left live and unused.

**Deprecated pathway sheets — do not audit, do not write up, do not treat as evidence.** The
following sheets in `Master_Data_File.xlsx` are not instantiated by any of the three modeled
projects and are no longer relevant:

- `Non-Blast Excavating` — Silver Peak, Thacker Pass, and Jianxiawo all carry a numeric
  `Powder Factor`, so `clay_lepidolite()` takes the blasting branch and mining runs off
  `Blast Mining` in every case. `Non-Blast Excavating` is dead for the modeled set.
- `Brine-Solvent Extraction-Boron` — not referenced by any modeled project.

Both sheets are still named in the `Pathway` rows of `Project-Specific Data` for non-modeled
catalog projects (`Non-Blast Excavating`: Bonnie Claire 2024, TLC, Clayton Valley (Angel Island);
`Brine-Solvent Extraction-Boron`: Salar de Atacama-Albemarle, Salar de Atacama-SQM), so deleting
the sheets would break those rows. Leave them in place and ignore them. A unit string, CCF, or
conversion factor on a deprecated sheet is not a finding, and a contradiction between a deprecated
sheet and a live one is resolved by the live sheet alone — the deprecated cell carries no
evidentiary weight.

**The Thacker Pass case is a generic clay flowsheet by decision, not by omission.** The modeled
route precipitates all magnesium with quicklime; the project's own design removes the same magnesium
by evaporative crystallization and recycles it, which is a different flowsheet with a different cost
structure. Do not treat the difference between the two as a defect, do not tune a modeled parameter
to close it, and state the divergence wherever a disclosure comparison is made. The generic route is
what makes the clay case transferable to the other Nevada clay projects, which is the paper's stated
reason for modeling it that way.

**The crystallization route is out of scope. Three reasons, so it is not re-scoped:**
- It is not in project sources. The disclosure material available describes it only as magnesium
  crystallization, ion exchange, and zero-liquid-discharge evaporation, with magnesium compounds
  recycled as reagents. No stream table, evaporator duty, crystallizer configuration or IX
  specification exists to build from.
- The magnesium recycle is structurally blocked. `production_step.py` costs every reagent as
  `abs_usage * material_data[reagent_name]["cost"]`, so a reagent cannot be sourced from an internal
  step's output; the route needs a second `ReagentFacility`, as the acid plant did.
- Its apparent cost advantage rests on a coproduct the model cannot price. The magnesium leaves as
  roughly 73 t of \ce{MgSO4.7H2O} per tonne of product, for which no market or disposal route is
  established. A crystallization route landed without that leg is not cheaper — it is a route with
  an unpriced coproduct several times the mass of the product.

If it is ever revisited, it is built as an alternative case — one block and one step column run as a
scenario against the generic base — never as a replacement for it, so that it prices the
reagents-for-electricity substitution without retiring the generic framing.

**Undeveloped block columns are not instantiable.** `machine_default` requires a `.conservative` /
`.midpoint` / `.optimistic` suffix, so a single-column block on `Machine Blocks Data` cannot be
addressed by any pathway sheet. Several such columns exist and carry only a handful of populated
rows against roughly 45 on a developed block. Treat them as placeholders: a new unit operation is a
full three-scenario derivation, not a column to fill in.

---

## Attributes Each Block Writeup Must Cover

For each block, address the following — **only include what can be independently justified; flag anything that cannot**:

1. **Sources** — primary references
2. **Process description + equation of merit** — what the block does and the key sizing relationship with units
3. **Bill of Equipment (BOE)** — three tiers: primary equipment (with anchor model/source), secondary systems, balance-of-plant auxiliaries. Three columns, `Equipment | Machine data used | Source(s)`. The middle column states what the row contributes to the model — usually `Unit count (staffing)`. Use "Not explicit → inferred" with `---` where assumed. **Do not state equipment dimensions that feed no modeled quantity.** Quoting a source's dimensions is not false precision, but it is detail no other block carries and it invites defence of numbers nothing reads; state a dimension only where it derives a cell. If the table needs a paragraph beneath it explaining what it does not contain, it is the wrong table.
4. **Sizing basis** — how `base_volume` maps to physical throughput
5. **CAPEX** — anchor equipment bare cost with source, installation multiplier (bare → installed) with justification, auxiliary adder breakdown (itemized with % ranges), total installed cost by scenario
6. **Electricity** — anchor load with load factor, auxiliary adder breakdown, scope definition
7. **Thermal utilities** — NatGas / diesel / propane (thermodynamic or empirical derivation with combustion efficiency applied explicitly)
8. **Other utilities** — steam, cooling water, compressed air (derived, not just flagged)
9. **Consumables** — equipment-tied OPEX (grinding media, filter cloth, flocculant, etc.). Note: some consumables (flotation reagents, grinding media) may be better modeled at the production step level; flag this distinction.
10. **Labor** — FTE base per Calculation Standards → Labor, plus scaling exponent with physical justification
11. **Footprint** — plot area and scaling exponent
12. **Availability** — availability factor and downtime fractions with justification
13. **Maintenance** — `maint_override` status. Blocks with a blank `maint_override` inherit the facility-level rate from `Locational Data` (`maint` = 0.05). The code computes `maint_cost = scaled_equip_cost × maint`, so this is a fraction of **scaled main-equipment cost**, not of total installed CAPEX. Describe it that way — never as "5% of CAPEX."
14. **Key measurements and cross-checks** — validation against at least one disclosed or published value

Use these headings and this order. Omit any section the block has nothing to say about, but **do not
invent new ones.** A `Declarations` section was introduced in the acid plant writeups, attracted
vague prose because it was a bucket with no defined content, and was removed; zeroed utilities belong
in `Other utilities`, and step-level mass balance declarations belong in the facility-level pathway
section, not repeated per block.

---

## Writing Style

- **Derivations: be concise.** State the source, list the per-shift components, show the equation, stop. Do not explain what shift factors are or justify conventions the reader already knows, especially for Labor.
- **Cross-checks and flags: keep brief.** State what was checked and whether it passes. Flag only if something is actually wrong or unverifiable. Do not write a mini-essay on the topic.
- **No spreadsheet update references in the LaTeX.** The `.tex` file is pure appendix prose. Any notes about spreadsheet field changes go in the chat message only.
- **No prior-state references in deliverables.** Cell comments and `.tex` prose describe the model as it stands. Never write what a value used to be, what a superseded parameterization implied, or that something was corrected. Change history should generally be avoided; if it is absolutely required, it belongs in `handoff_open_items.md` only.
- **No superseded numbers in the working documents either.** `handoff_open_items.md` and `continuation_prompt.md` carry the current measurement and nothing else. When a figure is invalidated, delete it and say what needs re-measuring; never record what it was, and never write `X superseding Y`, `Y struck`, `against Y on record`, or `Y retracted` with the number attached. A retraction is stated without its figure. Deltas against a disclosure or a calibration target are not prior state and stay.
- **Banned phrasing: "rather than."** State what the thing is. Where a contrast is genuinely load-bearing, make it its own sentence.
- **Tail sections (utilities, consumables, maintenance, footprint, availability) — happy medium.** These should be neither bare field dumps nor over-explained. The calibration:
  - **Utilities**: Combine "Thermal utilities" and "Other utilities" into a single "Other utilities" section when both are "none." State what *is* consumed but not tracked, meaning draws that are out of the model's scope (e.g., dust suppression water). Water leaving with a coproduct is not an untracked term: state the reclaim and the declared loss under the sink or block that carries the stream, per gate 3, rather than listing fates per block.
  - **Consumables**: When unpopulated, name the relevant consumable in one sentence, state `tooling_cost_base = 0`, and note what data is needed. "Flagged as a gap" is acceptable here.
  - **Maintenance**: One sentence stating whether `maint_override` is populated or inherits a default. Do not elaborate extensively on what maintenance covers; a short explanation is only needed when it is not inheriting a default. 
  - **Footprint**: Field values, then one sentence listing what the plot area covers. No itemized m² breakdown necessary.
  - **Availability**: Field values plus one sentence of justification. No more.
- **No unsourced "published" claims.** Never write "published values range from X–Y" without specifying the source. Find the source or remove the claim.
- **Sizing basis: weave fields into prose.** Do not list field values as a bare dump. Instead, integrate them into natural sentences with brief justifications. For example, write `The \texttt{scaling\_exponent} = 0.67, close to the six-tenths rule; there is no oversizing (\texttt{oversizing\_factor} = 1.0), and lines must be dedicated (\texttt{dedicated\_line = TRUE}).` A bare dump reads `\texttt{scaling\_exponent} = 0.67, \texttt{oversizing\_factor} = 1.0, \texttt{dedicated\_line = TRUE}.` and is not acceptable.
- **Combined blocks:** Flag any step that lumps multiple significant unit operations into one machine block, as `classification_flotation` does. State which operations are combined and what the combination costs in sizing fidelity. 
- **BOE sourcing: distinguish explicit from inferred.** In the Bill of Equipment table, only mark items as "Not explicit → inferred" if they genuinely have no data anchor. If equipment data, dosage rates, or circuit configurations are taken from literature or vendor data, cite the source and use a descriptive machine data entry (e.g., "Mechanical flotation cells," "Dosages from literature"). 
- **Citation keys.** Use `\citet{}` or `\citep{}` for references. Always flag citation keys that need verification against the `.bib` file.

---

## Spreadsheet and Existing Writing — Mandatory Checks

### Reading the workbook

> ## ⚠️ PLEASE READ THE COMMENTS IN `Master_Data_File.xlsx` ⚠️
>
> **Before analyzing any cell, dump every comment on the sheet.** The comments carry the modeling
> intent — which carrier a CCF weighs, why a factor carries an extra term, what a yield is measured
> against, which values are placeholders, which cells are overridden at runtime. A cell read
> without its comment is routinely misdiagnosed, and a "defect" called without reading the comment
> is the single most common way this project generates false findings.
>
> This is not optional and it is not satisfied by reading formulas, values, unit strings, or
> `main.tex`. Dump the comments programmatically, every session, before the first claim.

- Dump every comment on a sheet before analyzing it, programmatically rather than by eye: `openpyxl.load_workbook(path, data_only=False)`, then `cell.comment.text` across `ws.iter_rows()`.
- **CSV export drops comments, and Excel's export drops precision.** The model now reads `./data/Master Data File.xlsx` directly (see "Running the Model"). Never diagnose a cell from a CSV.
- Read both the formula (`data_only=False`) and the evaluated value (`data_only=True`); they answer different questions.
- **`Constants & Derivations` sources live in column D, not in cell comments.** The sheet has `Name | Quantity | Unit | Source` headers. Reading only openpyxl cell comments there returns nothing and makes a fully sourced constant look unsourced. Pathway sheets are the opposite — their provenance is in cell comments. Check both before calling anything unsourced.
- Row order may not be uniform across pathway sheets. Read every cell by its column-A label, never by a row index carried over from another sheet.
- Cross-check against the step's own prose in `main.tex` before calling anything a defect. Where the sheet and the appendix disagree, that disagreement is the finding — flag it, do not pick a side.
- Grade overwrites via `add_target_comp` terminate propagation at the named step. Composition upstream of an overwrite does not reach the model's outputs and is not diagnostic; a ledger read there tests nothing.
- **Grade and CCF are a pair.** A carrier change is landed only when `c`, the step CCF, the input CCF and any code-side override move in the same edit; the sizing anchor (`precipitation_step.step_ccf`) rescales the whole plant if moved alone.
- A reagent whose `target_constituents` names the step basis gets `base_amount = 1` and is independent of any CCF. Only constituent-targeted reagents depend on `step_ccf`, and in a Case-2 step those cancel against `step_pv`, leaving absolute usage invariant.
- **Sink cost bases are not uniform.** `TAILINGS_SINK_PARAMS` entries register as **$/m^3** — `register_sink_cost(name, cost_tds * ds_per_m3(s_in, rho_s))` — and the routed coproduct volume must be m^3. `waste_pile` registers as **$/t as-routed** via `WASTE_ROCK_COST`, because `Blast Mining` `D57` declares `tonnes waste / tonne loose rock` and every disclosed waste-mining anchor is $/t. Routing a tonnage stream to a `TAILINGS_SINK_PARAMS` sink overcharges by rho_s. `register_sink_cost`'s `if sink_name not in all_sinks: return` guard is load-bearing: the unconditional `waste_pile` call is safe only because Silver Peak builds no `Mining` facility.
- **Per-project overrides beat pathway-sheet values.** `Project-Specific Data` rows override a pathway sheet cell at runtime where one sheet serves two projects — `Pond Recovery Efficiency` and `Carbonate Recovery Factor` are the live cases. Three rules. The sheet value is the fallback and must stay defensible for whichever project is not overridden. The override must be applied before anything downstream reads the field: at `precipitation_step`, `ml_conv` reads `slurry["yield_rate"]`, so the yield override must precede it. And guard on `not in (None, "-")`, since `Project-Specific Data` uses `'-'` as its null for inapplicable rows.
- **`clay_lepidolite`'s precipitation block sets four things and drops any of them silently.** `pls_post_polishing` ccf, `step_basis` ccf, the `mother_liquor` conversion factor, and — Lepidolite only — the `mother_liquor` sink. A missing `set_conversion_factor("mother_liquor", ...)` falls back to the sheet's `C56` = 0.0, zeroing the liquor volume with no error; a missing sink assignment falls back to `C55` = `process_water_recycle`, silently deleting JX's wastewater discharge worth 217.60 $/t LCE. Both failures cost money and neither raises. Re-read the whole block after any edit to it.
- **A closure question is answered from uploaded files or not at all.** If the user asks whether
  something is closed and the relevant file was not uploaded in the current chat, do not re-run the
  analysis, do not re-derive from `/mnt/project/` copies, and do not answer from the prior session's
  measurements: name the missing file, say it was not uploaded, and request it. A verdict measured
  against a superseded copy is worse than no verdict, because it reads as confirmation.
- **Read the reporting helper before quoting its output.** Verified: `get_constituent_amount_at_steps`
  returns `val * pv` — ppm x PV, no CCF. It is not a mass and is not comparable across steps carrying
  different bases. A ledger claim sourced to it is unsupported.
- **Known-wrong labels — correct them, do not work around them.** `tp_debug` `Ore throughput (t ore/yr)`
  is a hardcoded literal decoupled from `step_ccf`; the value is leach-feed solids, not ore, and the
  literal is stale in value as well as in kind whenever the leach density moves. The `tp_debug` summary line prints `avg_co2` under a `t CO₂/t LCE` label while the value is
  kg/t LCE; this is a third site, distinct from the plot axes covered under "Running the Model".

### Machine Blocks Data spreadsheet

**Before writing any block, read the `Machine Blocks Data` sheet of the authoritative `Master_Data_File.xlsx` via openpyxl (comments, formulas, and evaluated values).** CSVs are for model runs only; never pull block parameters from a CSV or from `project_knowledge_search`. Pull every non-null parameter for the block being written and cross-check each value against your derivation. Specifically:

- Confirm `base_volume` and `base_volume_unit` — the base volume may not be what it appears (e.g. the `drying_packaging` blocks use a base volume of 2.5 that refers to wet feed cake, but the unit describing it may not be explicit)
- Pull all three scenario columns (`.conservative`, `.midpoint`, `.optimistic`) before beginning any calculation — do not assume values match your derivation until verified
- Flag any spreadsheet value that cannot be traced to a defensible derivation, and propose a correction with full work shown
- Note any fields that are blank, zero, or `False` where a non-zero value is physically expected — these are gaps that need filling or flagging

### Appendix consistency

**All block writeups must be internally consistent with the existing prose in the supplementary appendix (in `main.tex`).** Before writing:

- Grep the relevant sections of `main.tex` to identify terminology, notation, and methodology already established. Do not read `main.tex` end-to-end.
- Use the same variable names, unit conventions, and equation forms as the existing appendix
- Do not introduce new notation or redefine existing terms
- Where the existing appendix text is ambiguous or inconsistent with your derivation, flag the discrepancy explicitly rather than silently overriding it
- Facility-level step writeups and block-level writeups describe the same physics in two places and can disagree. When they do, instead of treating either as ground truth, flag it with me and ask how to approach next. Do not overwrite anything. 

---

## Spreadsheet Structure

Each block has three scenario columns: `.conservative`, `.midpoint`, `.optimistic`. Key parameters include:

`base_volume`, `base_volume_unit`, `step_basis`, `electricity_base_total`, `natural_gas_base_total`, `propane_base_total`, `prim_equip_price_base`, `prim_equip_scaling_exponent`, `labor_base`, `labor_scaling_exponent`, `footprint_base`, `proc_avail_factor`, `opex_fraction_of_capex`

Reagent rows on pathway sheets are parsed dynamically (`reagent_(\d+)_` in `helpers.py`); the count
per step is unbounded and non-uniform — `Sulfuric Acid Leach` `impurity_removal` carries four, with
`reagent_4` = cake wash water at $0 drawn from the declared mother-liquor return. Row positions
below the reagent block differ across sheets accordingly; read by column-A label only.

---

## LaTeX Formatting Rules

These are strictly enforced by the `cmu-thesis` template. Violating them causes compilation errors or template rejections.

- **No `\field{}` command** — use `\texttt{field\_name}` with escaped underscores throughout
- **No `L{...}` column type** — use `>{\raggedright\arraybackslash}p{...}` for wrapped table columns
- **No `\paragraph{}`** — use `\medskip\noindent\textbf{Title.}\quad` for section headers, and add an additional new line after this section header (two new lines after each section header total)
- **Captions strictly above tables** — `\caption{}` must be the first thing after `\begin{table}[h!]`, before `\centering` and `\begin{tabular}`
- **No `\begin{document}` or preamble** — all files are bare snippets for `\input{}` inclusion
- **No tildes for spacing** — do not use `~` to create space between words in text
- **No commas inside braces** — write `{,}` as just `,`
- **All units through `\si{}`, literal-with-caret** — write `\si{m^3}`, `\si{kg/m^3}`, `\si{m^3/h}`. Never `textsuperscript{3}`, `m$^3$`, or `\text{t/m}^3`. Compound units go inside one macro: `\si{m^3/h}`, not `\si{m^3}/h`. Bare in running text — `\si{m^2}`, not `$\si{m^2}$` — and `\si{}` is valid inside math and inside subscripts.
- **`\si{}` eats interword spaces.** `\si{kg Li/m^3}` renders `kgLi/m³`. Use `\si{kg~Li/m^3}`; the "no tildes for spacing" rule does not reach inside a `\si{}` unit argument.
- **American English** — no British spellings
- **No "Table" before `\ref{tab:...}`** — the template auto-prefixes "Table" to table references, so `\ref{tab:foo}` compiles to "Table C.31". Writing "Table \ref{tab:foo}" produces "Table Table C.31". Use bare `\ref{tab:...}` only.
- **BOE table column widths** — approximately `p{5.2cm}`, `p{4cm}`, `p{4.5cm}`
- **Chemical formulas** — always `\ce{}` from `mhchem` v4. Never `textsubscript`, `CO$_2$`, or `\text{H}_2\text{O}`. Do not nest `\ce{}` inside `\ce{}`, and use mhchem's own arrows (`->`, `v` for precipitate), not `\rightarrow`. `CO2`-equivalent is `\ce{CO2eq}`, not `\ce{CO2}e` or `\ce{CO2}-equivalent`.
- **Available packages**: `booktabs`, `array`, `amsmath`, `siunitx`, `mhchem` (v4), `parskip`, `enumitem`, `xcolor`

---

## Stream Conventions (CCFs, coproducts, chemistry flags, water)

This is the highest-error-density area of the model. Check every rule below explicitly when writing or verifying a step.

### The input-side identity (read this before touching any CCF or IPCF)

IPCF is defined by `needed = step_pv / conversion_factor`, so it is **step-basis units per input-stream unit**. Constituent mass entering per basis unit is therefore `ccf_in * c_in / IPCF`, and by definition of the basis pair that equals `step_ccf * c_step`. The code applies this in `aggregate_inputs`:

	c_step = c_in * R,    R = ccf_in / (IPCF * step_ccf)

This is conservation of constituent mass, not an assumption. Because `c` is ppm **per kilogram of carrier**, `R = 1` if and only if the carrier is the same material on both sides of the boundary. Consequences:

- **R = 1 is the expected state at every primary input.** It is a theorem about unchanged carriers, not a definition, and `ccf_in` remains an independently authored descriptor.
- **R != 1 is reserved for a declared carrier change** (solids -> liquor, ore -> clinker). At such a step `c` must be re-based to the new carrier in the same edit; changing the CCF alone recomputes the grade against a carrier `c` is not measured in.
- Where the carrier is unchanged, the three cells are not independently free: any two determine the third. A slurry dilution's IPCF is the ratio of the two CCFs.
- Multiple primary inputs give `step_ccf = sum_i(ccf_i / IPCF_i)`; no single input reads R = 1.

**IPCF may absorb non-mass edge cases** (recirculation inflation, reagent mass gain, unit and density conversion). Where it carries a non-mass factor, `ccf_in` must carry the same factor so the grade passes through unchanged. Write that compensation as a **formula referencing the IPCF cell**, never a literal — a literal goes stale the next time the inflation changes, and a compensated cell is then indistinguishable from a defective one. State the factor in the units string.

**Where the compensation must be entered depends on the facility boundary.** `propagate_chemistry` writes `next_step.primary_inputs[name]["ccf"] = output_ccf`, so within a facility the `primary_input_n_ccf` cell is overwritten at runtime and editing it does nothing — the live cell is the **upstream step's `primary_output_n_ccf`**. Propagation does not cross facility boundaries, so at a facility-entry step the input cell (or a `set_conversion_factor` override) is authoritative. Establish which case applies before editing.

**The rebase is opt-in.** A model with every R != 1 site compensated is numerically identical to one that ignores input CCFs entirely. The rebase acts only where a site is deliberately left uncompensated, which is why an uncompensated non-carrier-change site is always a defect.

### Mining volume basis and swell

`loose_rock_throughput` is a **mass** basis (tonnes, ore plus waste). `rom_ore_feed` leaves
`excav_load` as a **volume** (m^3 loose rock), because haulage is sized on volume
(`trip_number = ceil(input_volume / ref_volume)`). The conversion sits on the POCF:

	POCF_rom = 1 / ((1 + strip_ratio) * rho_loose),    rho_loose = rho_bank / swell_factor

- `rho_loose` appears again as the crushing IPCF with the opposite sign, so **it cancels from the
  material balance**. The swell factor governs haulage volume, trips, and transport cost and
  emissions only — never mine tonnage, waste tonnage, explosives, or anything downstream of crushing.
- The crushing IPCF cell holds the **dimensionless loop factor only** (1 where there is no
  recirculating circuit, `1 + CL` where there is). `run_scenarios.py` reads that cell and multiplies
  by `rho_loose`. Never restate a density in the cell. The same product appears with the opposite
  sign on the `excav_load` output CCF, set in code as `loading.step_ccf * rho_loose`. Both are
  runtime-set.
- The crushing input CCF is set in the same code block as `ipcf * step_ccf`, forcing `R = 1`.
  The sheet's `primary_input_1_ccf` cell at crushing is therefore **inert** — say so in its comment,
  or the next reader will diagnose it as a defect or, worse, "fix" it.
- Fill factor belongs to equipment, not to material. It is already inside
  `excavation_loading_generic.base_volume` (t/cycle) and, if it is ever made live for haulage,
  belongs on `haul_truck.base_volume`. It must never appear in `rho_loose` or in a mass-basis
  unit string.
- The waste coproduct factor stays on the unchanged tonnes basis. Closure across this step is
  therefore stated in tonnes, not summed across measures: `V_out * rho_loose + V_waste = 1.000`.

### Sink naming

- Pattern: `{material}_{method}_{jurisdiction}_{s_in x 100}`. The trailing number is **s_in** — the solids fraction of the m^3 that the pathway sheet's `coproduct_N_conversion_factor` generates, which is also the registration basis, `ds_per_m3(s_in, rho_s)`.
- A sink serves **one material class, one method, one jurisdiction**. A stream from a second jurisdiction gets its own sink row; never share one across locations, because pi and the gate regime are jurisdictioned and the shared row silently prices one project at the other's rates.
- Method is `impound` (hydraulic deposition behind containment), `stack` (spread, compact, no containment), or `offsite_gate` (per-wet-tonne tariff, no on-site storage term).
- Each sink declares a `train`: an ordered list of `(mechanism, s_out)` pairs from `thicken`, `vacuum`, `press`, empty where the stream arrives at a solids fraction the sink does not improve. Each stage costs `C_m + c_w*dW` and `E_m + e_w*dW` with `dW = 1/s_in - 1/s_out`, so a stage is priced for the water it removes and not for its target alone. `s_final` is the in-place solids after consolidation or air-dry; it is reported, not costed. Storage volume is charged at the train's outlet, or at `rho_dry_final` where a density is disclosed — never at `s_final`. Consolidation drainage is too diffuse to collect and is a loss, not a reclaim: the water balance reads `sink_s_out()`. Where the emitting machine block contains no separation unit, the sink also declares `s_feed`, the solids fraction at which the stream physically leaves the step. The train then starts at `s_feed` and `dW = 1/s_prev - 1/s_out` reads it as the first `s_prev`, while `s_in` stays the registration basis, the routed-volume basis and the trailing number in the sink's name. Absent, the train starts at `s_in` and the two are one quantity. Landed 2026-08-23 on `facility.py` `168066e3` for `sludge_stack_nv_50` (`staged_neutralization` has no press) and `claycake_stack_nv_62` (0.33, the CCD block's press is capitalized there but its duty is priced here). `sink_s_out()` is unaffected by an `s_feed` declaration, so the facility water balance does not move.
- Every `s_out` is checked against `S_CEIL_PURE` blended at `x_hyd` on retained water, `m_w_ceil = x*m_w_hyd + (1-x)*m_w_cry`, `s_ceil = 1/(1+m_w_ceil)`. Exceeding it raises. `x_hyd` sets what a mechanism can physically achieve; it mass-weights the `STAGE` coefficients as a secondary effect, and that blend is a floor, since the compressible fraction also degrades the crystalline fraction's filterability. Every train target, every `x_hyd`, `S_CEIL_PURE` and the `STAGE` coefficients are declared allowances under the rule above.
- The sink's mechanical and placement electricity reaches emissions as a flat sink impact factor, not as step utility consumption: `tailings_handling` writes `fac.impact_factors[name] = {cat: sink_elec[name] * ds_per_m3(s_in, rho_s) * f}` for every category the facility's `electricity` factor carries, rebinding `fac.impact_factors` rather than mutating it, since `helpers` hands one dict object to every facility at a location. Write it after the sink loop closes: the comprehension reads `sc.sink_elec` for all ten names and raises `KeyError` if it runs inside the loop. The factor is per-facility, so the sink is billed at the owning facility's grid intensity, not at `p["jur"]` — the two coincide only because each modeled project's facilities share one location. `scope_two_sinks` carries the names to `production_step`, which files them under Scope 2; a sink whose factor is not electricity-derived must not be added to that set.
- Wastewater sinks are named `wastewater_discharge_{jurisdiction}` and carry a price only: `WASTEWATER_SINK_PARAMS` in `facility.py`, registered in the same loop shape as the tailings rows. The `wastewater` prefix is load-bearing — `supply_chain.py` branches twice on `sink_name.startswith("wastewater")`, so a rename that drops it removes the sink from both plot paths silently. The `jur` field is declarative and unenforced; only `cost` is read.
- **Impact factors for wastewater sinks — water, eutrophication, or any other category — are permanently out of scope.** Blank `utility_impact.wastewater.*` rows on `Locational Data` and the `Facility` default `"wastewater": {...0.0}` are the intended state, not a gap, not a finding, not a queue item. Do not raise them, in any session, in any form.

### Constituent Conversion Factors (CCFs)

- CCF is a property of the **carrier**, not of a constituent. One CCF per step basis, shared by every constituent in the vector. It states the mass of constituent-bearing material per unit of step basis; the constituent identity is supplied by $c$, never by the CCF. For slurries it is $\text{CCF} = w_s \cdot \rho_{\text{mix}} / 10^3$ with $\rho_{\text{mix}}$ from the mixing formula.
- **$c$ and its CCF are one quantity in two cells.** Only $c \times \text{CCF}$ (kg constituent per step-basis unit) is physically meaningful. Never change one without re-deriving the other — a correction to a CCF alone is not a partial fix, it is a new error.
- **A ppm figure is meaningless without its carrier.** The same lithium reads at different ppm on ore, on beneficiated solids, on slurry, and on PLS. Never compare two grades across a carrier change; convert both to $c \times \text{CCF}$ first.
- Each constituent moves independently. Impurities are removed by design (`target_constituents_eliminated`); lithium is invariant except where the step is designed to upgrade or reject it. Steps therefore need distinct values for every element of $c$ as well as a distinct CCF.
- **At a carrier identity change** (slurry → PLS, ore → clinker, solution → crystal), the handoff is a pair: the downstream step's $c$ and CCF must both be re-based to the new carrier in the same edit. Re-basing one side while leaving the other creates or destroys lithium.
- **Runtime overrides supersede sheet cells.** Where `run_scenarios.py` sets a CCF via `set_conversion_factor(..., field="ccf")`, the sheet cell is inert. Fix both, or the model will not move.
- **On an inert CCF cell the unit string describes the live value, not the literal.** This is correct and is not a finding. Three cases: `Sulfuric Acid Leach` `C23` and `Sulfate Roast-Water Leach` `C23` both read `kg ore / m^3 loose rock` against literals of 0.001 and `=1/1000*C18` = 0.003, because the live value is `rho_loose * loop_factor * step_ccf` (1.5833333333e-3 on TP, 4.6285714286e-3 on JX) and `rho_loose` = `Initial Density`/`Swell Factor` is project-specific and cannot sit on a shared pathway sheet; `Solution Processing-Sulfate` `C11` reads `kg PLS / L polished PLS` against a literal of 2.288135593e-7 (a 20 wt% solids-slurry CCF) because both branches overwrite it — Clays with `impurity_removal` `pls_post_polishing` ccf / 10^3 = 1.109736784e-6, Lepidolite with `stream_clarification` `pls_post_polishing` ccf = 1.049490518e-6. Read the cell comment before judging any unit string whose paired value is overwritten.
- **The unit string, the basis label, and the value must all agree on the same carrier, the same wt%, and the same volume unit.** Check for: a value derived at one wt% sitting under a label stating another; a per-liter CCF (×10⁻⁶ family) on a per-m³ basis; a solids-slurry CCF applied to a PLS stream.
- **Complete the unit and carrier sweep before editing any of them.** Establish, for every step, which carrier its CCF weighs and which carrier $c$ is measured per, and record it — then edit. Each cell is judged on its own terms; a fault in one implies nothing about the next. The reason to sweep first is coupling, not contagion: a cell that is wrong on its own terms may still be the only thing holding a downstream seam closed, so a correction landed alone can move the model further from correct rather than closer. Know the whole map before moving any piece, and land coupled corrections together.
- **`Sulfuric Acid Plant` carries constituents as mass fractions, not ppm**, and its CCFs are unity by construction rather than members of the ×10⁻⁶ family. This is a declared divergence: the plant's constituents are major components (0.4005 kg S/kg SO3, 1.0 kg H2SO4/kg acid) and the plant carries no ppm-based grade anchor. Do not apply the ppm reading to `C10`, `D10`, `C20`, `D20`, `C22`, `D22`, `C49`, `C51`, `D51`.
- Redundant copies exist: a step's `step_ccf`, its `primary_input_1_ccf`, and the upstream step's `primary_output_1_ccf` must agree. The code can propagate output→input, so divergence hides in the redundant cells.
- **A grade change belongs in the conversion factors, never in `yield_rate`.** `yield_rate` is the
  constituent recovery $R$; the mass split is derived, $Y = R \cdot f/c$, and is carried by the POCF.
  In a Case-1 step the two factorizations are numerically identical, since `compute_step_pv` uses
  only the product $y \times \text{POCF}$ — so this is a readability and auditability rule, not an
  arithmetic one. It is still the rule: a `yield_rate` that silently encodes a mass split cannot be
  read against a disclosed recovery.
- Li fraction of \ce{Li2CO3} = $2(6.941)/73.891 = 0.18787$. Derive, do not round.
- **Benchmark through the product, not through a derived intermediate — but set the parameter on its own
  basis.** These are different operations. A *check* should reach a disclosure quantity by the route that
  passes through the fewest model-derived denominators; a *setting* is authored on the basis the parameter
  physically has, and its product-side consequence is then an output to be compared, not a target to be hit.
  Setting a process intensity by back-solving from a product-side disclosure quantity buries whatever error
  the model carries in the intervening tonnages into the parameter itself, and the parameter stops being
  independently checkable. TP acid is the worked case both ways: the dose is set as kg reagent per kg feed
  solids, and the product-side sulfur and the per-tonne-of-ore figure are then two independent checks on it.

### POCF vs. concentrations: what actually sizes a step

In a **constituent-driven (Case 2)** step, `step_pv = (target/y) × (c_out × CCF_out) / (c_in × CCF_step)` — **the POCF cancels out of the step's own sizing, and it does not set the output volume either.** `compute_step_pv` takes `target_volume` from `next_step.primary_inputs[vdo]["input_needed"]`, so the forward volume comes from downstream demand and the mass split is carried by the grade pair. **At a Case-2 step the POCF cell is inert: editing it moves nothing.** Do not "fix" it to a volumetric share, and comment it as inert so the next reader does not diagnose a defect that is not there. Therefore:

- The POCF cell states the **physical volume ratio** of output stream to step basis — not $c_{\text{in}}/c_{\text{out}} \times y$, and not the output's volumetric share of the feed. For a stream leaving at the same density it entered, the POCF is **1.0**.
- Where the POCF is a density/unit bridge, write it as `=step_ccf/output_ccf` referencing the two CCF cells (`=E10/E51`, `=F10/F51`, `=H10/H51`) rather than restating the density algebra as literals.
- In a **flow-defined (Case 1)** step, the POCF *is* live for sizing. Establish which case a step is before touching the cell.

**The leach basis is pinned downstream; upstream mass is back-solved.** On the TP clay chain the solve runs `APV` → `washed_pregnant_leach_solution` Li target → `V_leach` → x `step_ccf` → leach solids → ÷ `mass_yield` → ROM → blasting. `V_leach` is invariant under perturbation of `step_ccf`, `Intermediate Concentration` alone, and any reagent ratio, because the PLS Li target pins it. It moves only when `Second Intermediate Concentration` moves with the leach grade: the two are linked on the sheet through `c_PLS_TP` but not at runtime, so a grade sandbox that changes only `Intermediate Concentration` tests nothing. Consequences:

- `step_ccf` at `acid_leaching` sets the **ore requirement**, not the pulp density of a fixed solids stream. Raising it 10.64% raised `crushing` 10.64% and left `V_leach` unmoved.
- Raising the rejection fraction through `Intermediate Concentration` raises ROM instead of reducing leach feed.
- **Overall Li recovery is emergent, never assumed.** It is the product `R_ov = R_class x R_down`, so it is invariant under the leach feed grade: raising the grade lowers leach solids and the classifier reject in step. The model's conservatism relative to a disclosure is therefore not a chosen quantity.

Until recovery is an input, leach feed solids and ROM are unsuitable as benchmark denominators. Establish a quantity's position in this solve order before using it as a denominator, and confirm it is not itself derived from the parameter under test.

### Derived quantities belong on the sheet

Every derived quantity is encoded once, as a sheet formula computing from named inputs on
`Constants & Derivations`. A quantity is computed in `run_scenarios.py` only where two or more
MODELED projects share the cell and no selector exists — currently the `Solution
Processing-Sulfate` precipitation overrides. A grade-dependent cell is not an exception: a shared
pathway sheet with one modeled user encodes that user's values, and the grade reaches the formula
through the `Constants & Derivations` extraction of the `Project-Specific Data` field
(`Li_ROM_JX`, `Li_int_JX`), not through the sheet's own constituent-fraction cell.

Constituent-fraction cells (`primary_*_constituent_fractions`) are overwritten at runtime by
`add_target_comp` and are therefore left **blank**, not populated as caches. A formula needing a
grade references the extraction name instead. A populated constituent-fraction cell is a stale
copy of a value the model has already discarded, and is a finding.

A ratio derived from other ratios references those cells, never their expansion. `Brine-Batch Chemical
Purificati!C40` is the pattern: the soda ash dose against Mg is `=C34*C28*M_Ca/M_CaOH2`, not
`=M_Na2CO3/M_Mg*1.2*1.2`. Both evaluate identically, but the collapsed form hard-codes the excess factors
belonging to C34 and C28 and goes stale the moment either moves. Where molar masses cancel out of an
algebraic identity, that cancellation is the signal that source cells are being inlined.

Determine the case from `volume_defining_basis`: equal to `step_basis` → **Case 1**; a constituent → **Case 2**. Establish this before interpreting any `yield_rate`.

- **Case 1**: `yield_rate` is a bulk/volume split. $V_{\text{out}} = \text{step\_pv} \times y \times \text{POCF}$. The constituent flow is whatever $c \times \text{CCF}$ states on each side; conservation is a constraint to be checked, not an identity.
- **Case 2**: `yield_rate` is the *volume-defining constituent's* recovery. $A_{\text{out}} = y \cdot A_{\text{in}}$ holds identically for that constituent, so the ledger cannot fail inside the step. The bulk split is derived: $Y_{\text{conc}} = R \cdot f/c$. Never read a Case-2 `yield_rate` as a mass yield.

### `chemistry_dependence` flags

These control **composition propagation only**, never sizing.

- On an **output**: TRUE = "overwrite my output constituents with the post-reagent input composition." Set TRUE only where the step does not change the stream's composition (pure densification, size classification at feed grade).
- On an **input**: the flag gates only whether the cascade continues (`apply_reagents` + recursive `propagate_chemistry`). Acceptance of the upstream composition and CCF is **unconditional** and happens regardless of the flag's value.
- **Set the output flag FALSE at any step that changes grade** (e.g. flotation). TRUE at a grade-changing step overwrites the concentrate grade with the feed grade and balloons the output volume.

### Unit operations own their duties

A coproduct leaves from the step whose machine block performs the operation that produces it. Solid–liquid separation belongs to the separator, not to the reactor upstream of it. Check `machine_default` before assigning a coproduct: a neutralisation reactor does not emit a filter cake.

Where a reactor already emits one anyway, three encodings exist and only one is available in any given case. **(1)** The block owns the separator: coproduct leaves at cake density, sink train empty, block electricity and capex carry the duty. **(2)** The block owns nothing: coproduct leaves at the block's discharge density and the sink's train performs the separation. **(3)** The separation is its own step with its own block. Option 2 is unavailable when the coproduct is not a side stream but one of two products of separating the whole flow, because the forward stream and the coproduct would both claim the same liquor — the TP `impurity_removal` sludge is 1.149 m³ of slurry per m³ of PLS against a forward output of 0.99, so writing it as a side stream at 0.0949 double-books. The `s_feed` mechanism under "Sink naming" resolves that case without option 3's new step: the volume basis stays at `s_in` while the train runs from `s_feed`. Volumetric closure is not the test — TP `impurity_removal` closes to 1e-11 and is still wrong about who does the pressing.

### Declared allowances

Where no assay or disclosure exists, author a round figure at one significant figure, state in the cell comment the basis it is NOT derived from, and record the sensitivity coefficient. Never wrap an allowance in a formula chain of sourced constants — the product acquires the appearance of a derivation it does not have. A formula whose inputs include an allowance inherits that allowance's precision, however many digits it evaluates to.

A reagent dose is derivable only where the composition vector carries the constituents that consume it. `Project-Specific Data` `Initial`, `Intermediate` and `Second Intermediate Concentration` for Thacker Pass are Li-only — `K`, `Mg`, `Ca`, `Na`, `B`, `SO4`, `Si`, `Rb`, `F`, `Cs` all zero. These are **source** vectors, not the runtime-overwritten `primary_*_constituent_fractions` caches, so blankness here is a gap and not the intended state. The TP acid dose is not a calibration — it is the disclosure's kg reagent per kg feed solids applied to the flowsheet's own solids — and since S1 neither is the impurity-removal lime dose, which is stoichiometric on the dissolved sulfate the acid charge fixes and therefore needs no cation assay. What remains declared on this pathway is `Ca_res_TP`, the residual dissolved Ca at 1 kg/m^3 PLS, and it sets the soda ash polish alone. A blank composition vector still blocks any dose whose driver is an ore constituent rather than a reagent already inside the model's own balance.

Solid reagent doses are assumed not to move the basis volume materially and are dosed at zero volume by default. The assumption is declared per step and holds only while the dose is small against the stream it enters; a liquid dose of comparable magnitude is not covered by it.

### Reagent rows: keying and dose basis

Reagent blocks are index-keyed on the sheet (`reagent_1_*`, `reagent_2_*`) and re-keyed by `name` in
`build_facility_dict`. Two rows may share a `name` — they merge into one entry whose `targets` dict is
the union, which is how a single reagent dosed against two different constituents is expressed. Two rows
sharing both `name` and a target is an error and raises. Adding a reagent row therefore requires checking
whether its `name` already appears in that step column.

Every dose is computed against the step's **feed** composition, snapshotted before any reagent in the step
fires. Elimination fractions still apply cumulatively to the running composition, so a later reagent sees a
reduced stream for its own removal but not for its dose. A dose intended to scale with a constituent that
an earlier reagent removes must therefore be authored against the feed quantity, not the residual.

### Reagent price basis

A reagent parameter is not calibrated until **both** its quantity and its price basis are stated. Where the project produces a reagent on site, the merchant price is the wrong basis; any co-product credit (power, steam) is carried as a separate line rather than netted into the unit price.

Quantity and price are never tuned against a single observed cost. Two errors of opposite sign in one cell are indistinguishable from a correct cell. TP acid was the worked case: a dose calibrated against a merchant acid price for an acid the project makes from sulfur while exporting power, where correcting either half alone would have replaced a compensated error with an uncompensated one. Landed under C5e.

On-site production is modelled as a `ReagentFacility` — a `Facility` subclass with its own location, sinks and pathway sheet, declared in `Project-Specific Data` as `reagent_plant.<reagent>.sheet`, `.location` and `.facilities` (a `;`-list of consumer sheet names). Pathway sheets are addressed as `Facility 1` / `Facility 2` / `Facility 3`. Mechanism, all load-bearing:

- `build_data_dict` materialises the nested dict in every project column, so a blank plant reads `{'sheet': None, ...}`, never `None`; the loader guards on `if not spec.get("sheet"): continue`.
- `ReagentFacility.demand()` sums `props["abs_usage"]` at the reagent level. The `usage` / `abs_usage` / `total_cost` keys nested inside `props["targets"]` are seeded by `build_facility_dict` and never written; reading them returns 0.
- `SupplyChain.update_apv` skips reagent facilities in the `cur_apv` threading loop and evaluates them in a second pass, after consumer `abs_usage` exists and before `get_sink_handling_costs()`.
- Consumers zero the reagent via `Facility.onsite_reagents`, guarded in `scale_reagents` and in `calculate_environmental_impacts`; `abs_usage` is retained so the plant sizes itself and reagent reporting still shows tonnage. The credit lands in the plant's own utilities, i.e. Scope 2.
- An isolated plant node sorts last in `Facility.topo_order`, so `sc.rev[0]` is not the chain terminal; `tailings_handling` resolves `ep` past reagent facilities.

### Shared machine blocks share equipment, not chemistry

Blocks used by more than one pathway provide the equipment-level cost and utility basis only. Ionic loading, reagent dosages, elimination fractions and constituent declarations are defined per pathway at the production-step level. When reading a shared block's process description, treat its stated stream composition as belonging to whichever pathway it was written for, and verify against that pathway's own assay before using it to size anything.

This extends to fuel. A block shared across pathways cannot carry a fuel-specific utility row where the
pathways burn different fuels — the row lands on every user identically. The established pattern is two
named blocks differing only in fuel (`drying_packaging_propane` for the chloride route,
`drying_packaging_generic` for the sulfate route), with the pathway roster above pointing each sheet at
the right one. Check the roster before adding any `*_base_total` to a shared block.

A step takes one machine block; `machine_options` lists scenario variants of a single family. Where a step performs a duty a second block already describes, fold that block's base quantities into the first. Both blocks defined at the same `base_volume` add directly with no rescaling. State the exponent mismatch: the sum is exact at base volume and drifts with throughput. `water_leach` carries `mechanical_dewatering` on this basis.

### Coproducts

- **Coproduct conversion factors are FEED-BASIS**: m³ of coproduct per unit of **step basis**, derived from the step's own mass balance. They are not yield-coupled. The code computes `coproduct_volume = step_pv × conv`.
- **Every step must close volumetrically**, but the closure identity depends on two per-step declarations, and the sum is only meaningful in a single unit system.
	- **Dose placement.** Each volumetric reagent dose is *basis-inclusive* (the step basis is defined after the addition, so the dose is already inside it — e.g. JX classification, where the process water is what makes the slurry 30 wt%; TP acid leaching, where the thickened feed, the dilution water and the dosed acid all sit inside the basis and sum to it; and JX `water_leach`, where the leach water is inside the 20 wt% basis but the cake-wash increment on the same reagent row is not — `J28` states the split in its own units string) or *basis-additive* (the basis is defined before the addition, so the dose sits on top — e.g. `wash_purif_step`, basis is the cake and wash water is added to it; TP classification, where both water rows are additive on the 20 wt% basis and both are set at runtime, `E28` to `makeup` and `E34` to `dilution - makeup`, with `dilution = fwd_vol + reject_vol + (1 - recycle_retention) - 1.0` — the 0.0 literals on the sheet are placeholders, not a zero dose, and `E34`'s units string says `additive, set at runtime`; TP `impurity_removal` `J46`, `additive; retained in filter cake`; TP `ccd` `I34`, additive per Reagent timing below). The `step_basis_unit` string should make this unambiguous.
	- **Yield semantics.** `yield_rate` is either a *physical split* (the lost fraction itself leaves as a real stream and must be routed as a coproduct — JX classification 0.93 → reject; JX flotation 0.75 → `gangue_impound_cn_30`; JX `crushing` 0.99 → `dust_fines`; JX `grinding` 0.995 → `mill_discharge`; `excav_load` → waste) or an *efficiency abstraction* (constituent recovery; no volume leaves **via $(1-y)$**, though a coproduct row may still route a real stream at the same step — TP acid leaching, `water_leach`, `impurity_removal`, `precipitation_step`, `thicken_dewater`, `wash_purif_step`, TP `crushing` (y = 1.0), `sls_step`, `ccd`). The test is what $(1-y)$ denotes, not whether the step has a coproduct: eight of the ten abstractions above route one.
	- **Compensating an efficiency abstraction.** At a flow→flow step only the product $y \cdot \text{POCF}$ is visible to the code, so an efficiency abstraction must set $\text{POCF} = V_{\text{physical}} / y$ or it silently deletes $(1-y)$ of the stream with no route (TP `acid_leaching` G52 = `=1/G51`; TP `ccd` I52 = closure/I51). The recovery may appear in the grade anchor and in the POCF compensation; it must never appear in the grade anchor *and* an uncompensated $y$ on the same chain segment, which double-counts and over-demands upstream volume.
	- **When compensation is the wrong fix.** $\text{POCF} = 1/y$ is legitimate only where a downstream grade anchor's *value itself encodes* the constituent loss (TP `acid_leaching`, the x0.9108). Where the next anchor is an independently measured concentration that knows nothing about the loss — JX Second Intermediate 21,630 ppm from Garrett, which encodes no comminution loss — compensation does not relocate the loss, it **deletes it**: $y \cdot \text{POCF} = 1$ preserves both volume and constituent, and the yield becomes a dead parameter that reads as a loss while doing nothing. In that case either route the loss as a coproduct at `conv` = $1-y$ at unchanged grade (the `impurity_removal` `=1-K45` pattern; JX `crushing` `dust_fines` 0.01, JX `grinding` `mill_discharge` 0.005) or set $y = 1.0$ and strike the loss from the prose. A yield of $y<1$, a compensating POCF, and prose asserting a loss must never coexist.
	- **A grade anchor does not absorb a mass loss.** An anchor pins a composition; upstream yields are expressed as inflated upstream volume, not as a grade change. Do not reason that a downstream anchor "catches" an unrouted yield.
	- **Over-determined step volumes.** Where a step's volume is fixed by both a concentration spec and a ratio-style operating parameter, only one can be an input. Pin the one that is load-bearing elsewhere and let the other fall out as a diagnostic. At the TP CCD the TDS basis appears in `I57`, `J10`/`J22`/`J57`, the precipitation CCF and a `run_scenarios.py` literal, while the wash ratio appears nowhere else — so TDS is the constraint and the wash ratio is the check.
	- **The hybrid case (TP `classifying`).** A step may carry an efficiency abstraction in
	  `yield_rate` while a real stream still leaves, routed through the coproduct row rather than
	  through $(1-y)$. Closure is then $y \cdot \text{POCF} + \text{conv} + \text{recycle} = 1$ on the
	  step basis, and `conv` is deliberately **not** $(1-y)\cdot\text{POCF}$ — it is feed-basis and
	  not yield-coupled. Comment the cell to that effect or the next auditor will read the
	  mismatch as an arithmetic error.
	- **Unit consistency (the trap).** The POCF is only a volume ratio when the output leaves in the same measure as the basis. Where the POCF is a **mass** ratio (e.g. JX `dewatering`, tonnes cake per m³ slurry), `Vout + Σcoproducts` is dimensionally void — do not compute it. State closure as the sum of *volumes* directly: for `dewatering`, V_cake + V_filtrate = 1.000. JX `crushing` is a second site: `C46` = 1.0 is tonnes per tonne while `C56` is m³ per tonne, so state closure on mass — 0.99 + 0.01 = 1.000 exactly. Confirm POCF units before writing any closure sum.
	- **Identity** (all terms in m³ per step basis): $V_{\text{out}} + \sum V_{\text{coproduct}} = 1.000 \times \text{step basis} + \sum(\text{basis-additive doses})$, with $V_{\text{out}} = y \cdot \text{POCF}$ for a physical split and $V_{\text{out}} = \text{POCF}$ for an efficiency abstraction.
- Two-product formula for a beneficiation step: $Y_{\text{conc}} = R \cdot f/c$ (recovery × feed grade ÷ concentrate grade); reject mass fraction is $1 - Y_{\text{conc}}$. If the reject leaves at feed density, the volume fraction equals the mass fraction.
- **Coproduct constituent fractions on waste streams are low-priority.** Populate a
  `coproduct_n_constituent_fractions` cell only where a sink impact factor or a ledger check
  consumes it; while sink impact factors are undefined, a blank fraction on a tailings or sludge
  stream is not a finding. (User decision, 2026-08-04.)
- **Sink choice is a physical declaration.** Route a coproduct to the sink whose declared solids
  fraction, hazard class and placement method match the stream as it leaves the step. Sink unit
  costs carry no evidentiary weight in that choice.
- **Every stream that physically leaves a step must be routed.** A conversion factor of 0 is valid ONLY as an explicit recycle policy, stated in a comment on the cell that names the receiver. Whether the receiving step's reagent dose is netted down is a separate accounting question and not a condition on the zero: an un-netted dose overstates purchased reagent, it does not break the mass balance. Record it, do not chase it. A zero with no stated receiver — "this water disappears" — is a mass-balance break and not a modeling choice.

### Reagent timing decides where its volume appears

`IPCF = ccf_in / step_ccf` is the constituent-rebase bridge and nothing else. It carries a reagent's volume only when that reagent is part of the material the basis measures, at the point the basis is measured.

- Added **before** the basis is weighed — the roast salts blended into `roasting_mix`, the leach water making a 20 wt% slurry — the volume is in the IPCF and the reagent row is basis-inclusive.
- Added **after** — a cake wash at a filter — the IPCF stays at the bridge value and the added volume surfaces on the output side. Product and coproduct then sum to `1 + wash`, not to 1. `ccd` and `impurity_removal` on `Sulfuric Acid Leach` both do this; `ccd`'s POCF exceeds unity for exactly this reason.

Putting a post-basis reagent into the IPCF forces `step_ccf` off its declared solids fraction and breaks the upstream bridge.

### Book each loss once

A constituent loss lives either in the step's `yield_rate` or in the downstream grade anchor, never in both. Where a hand-entered composition string on `Project-Specific Data` sets the output grade and the yield sets the constituent balance, the two are a pair and move together. The test is one line after a run:

```
Li_out = step_pv * POCF * ccf_out * c_out      against      y * step_pv * step_ccf * c_in
```

Agreement to rounding means the loss is booked once. A ratio equal to some other factor in the sheet names the term that is booked twice.

A literature recovery carries its measurement conditions. An extraction figure assayed on a filtered and washed leachate already contains the liquor recovery; booking a separate cake-liquor loss against it double-counts.

### Locked and declared factors and balances (each entry carries its verification run; declared-basis entries are marked NOT locked)
- **TP leach feed grade, LOCKED.** `Li_int_TP` 4,033 ppm = 2,538 x 0.92/(1 - 611.8/1,056.7), all
  three terms 2024 SK-1300 (Table 14-6, Sec. 22.6.2, Table 13-4). `Li_grade_TP` 1,299.5 follows
  through `c_PLS_TP`. Verification run: acid 28.5837, S 9.3546 t/t LCE, 1.022x the disclosed 9.15;
  independent cross-check 611.8/11.5 x 0.49 = 26.07 t H2SO4/t LCE. No upgrading ratio is imported
  from any other disclosure vintage.

- **Coproduct conversion factors, feed basis, sheet-verified**: TP crushing `rejected_coarse` 0 (closed circuit); TP `ccd` `filter_cake` 0.300 (62 wt% cake per `s_CCDs_TP`, sink `claycake_stack_nv_62`); TP `classifying` `rejected_coarse_gangue` 0.2726233766 (20 wt% reject, sink `gangue_stack_nv_20`); `drying_packaging` `evaporated_water` 0.2972 = 0.30 − 0.70·wf/(1−wf) at wf = 0.4%, both pathways; JX `sulfate_roasting` `fluorine_offgas` 0 (F-mass only) and `evaporated_water` `=0.2/I18` = 0.125 to `atmosphere` (mass ratio — closure in tonnes only: 0.875 + 0.125 = 1.000000); JX `crushing` `dust_fines` `=0.01/Rho_Grain_Hardrock` = 0.003703703704 m^3 solid per tonne crushed_ore_throughput (sink `rock_pile_cn_100`; the volumetric sink registration requires m^3, so the step's closure is readable in tonnes only: 0.99 + 0.01 = 1.000000, and the coproduct cell is not summable against the POCF) and JX `grinding` `mill_discharge` 0.005 to `conc_stack_cn_60` (`=1-y` in form, closing at 1.000000); JX `impurity_removal` `impurity_sludge` 0.05 and `stream_clarification` 0.005 (order-of-magnitude, keep orange); JX `dewatering` `press_filtrate` 0.4017857143 (POCF here is a mass ratio — state closure as volumes: 0.598214 + 0.401786 = 1.000000, never POCF + coproduct); Sulfate `thicken_dewater` `pressed_water` 0.7982748184 (volumetric; 0.99·POCF + 0.798275 = 0.997983, residual 0.20% < gate); Chloride `thicken_dewater` `pressed_water` 0.0 (declared recycle policy — standing chloride-recycle DECIDE, not a closure defect).
- **TP thickening `thickener_overflow` (verified 2026-08-04)**: `Sulfuric Acid Leach` F62 = `=(1/(0.15/2.6+0.85/1))*0.85-F52*(1/(0.55/2.6+0.45/1))*0.45` = 0.8012326656 m^3 per m^3 thickening basis, sink `process_water_recycle` at $0 — not a purchase and not a discharge. Closure F52 + F62 = 0.1987673344 + 0.8012326656 = 1.0000000000.
- **TP CCD PLS volume (C3g; declared basis, NOT locked — pending C5i)**: `Sulfuric Acid Leach` I52 = 1.4737566735 with I51 = 0.99, i.e. a physical volume ratio of 1.4590191068, replacing the former literal 1.31. The identity is $V = (S_{\text{feed}} - S_{\text{cake}})/c_{\text{TDS}} - \ell_c$ at 7.5 wt% TDS given the 0.300 cake conv at 62 wt%, which books reagent mass into the dissolved load at zero — the assumption C5i must close. I34's third term is `(1/G18)`, not `(1/(G18*G51))`; `Second Intermediate Concentration` = 906.81 ppm = 995.62 × 0.92 × 0.99, a stored literal that does not recompute when I52 or I62 move.
- **TP PLS carrier (locked by C3a, verified on the run of that session)**: the solids carrier ends at the CCD overflow. `Sulfuric Acid Leach` I10 stays 4.2996108950e-4 (34 wt% slurry); J10, J22, I51, J51 are the PLS family 1.048387097e-3 = 1/(0.075/2.6+0.925/1)/10^3 at 75 g/L TDS; `Second Intermediate Concentration` is set by the TP CCD PLS volume entry above. Precipitation runs 1.0483870968e-6 on the Clays branch and 2.288135593e-7 on the Lepidolite branch — the two projects legitimately carry different families at that step. The 75 g/L TDS is a sheet assumption, not disclosed, and is contested by the open TP acid-dose item.
- **TP classification (locked by C3b, verified on the run of that session)**: `Sulfuric Acid Leach`
  E45 = 0.92 (once-through Li recovery, the disclosed 8% coarse-gangue loss), E46 =
  `=(1/(0.15*1/(0.15/2.6+0.85/1)))/(1/(0.2*1/(0.2/2.6+0.8/1)))*(1-0.2)` = 1.104093567 (density
  20->15 wt% x fresh-feed fraction 0.80), multiplied at runtime by $f/c$ = ROM grade / leach-feed
  grade to give POCF 0.791131980. Coproduct `rejected_coarse_gangue` conv 0.2726233766 at
  595.810976 ppm Li; E49, E56 and E59 are BLANK and inert — all three are runtime-set from
  `Project-Specific Data`, so edit the code, not the cells. Solids split per classifier basis
  0.527377 forward / 0.272623 reject / 0.200000 recycle = 1.000000; per fresh solids 0.659221 /
  0.340779, reject grade $f(1-R)/(1-Y)$ = 595.811 ppm. The reject sink is `gangue_stack_nv_20`
  (C5f-1b): the stream leaves at 20 wt% per E63 and the E61 comment, is dewatered at the sink to
  `S_STACK` = 0.85 and dry-stacked, and the reclaim is credited at the classification make-up.
- **TP impurity removal (locked by S1, verified on the run of 2026-08-24)**: `Sulfuric Acid Leach`
  J51 = 0.99 is simultaneously the volume split and the Li recovery — the step carries no grade
  change (J22 = J10 = J51_ccf = 1.115279771e-3, all reagents `elim` = 0.0, output
  `chemistry_dependence` TRUE), so the 1% leaves as cake-entrained PLS. **The lime dose is
  stoichiometric on the dissolved sulfate, not on an assayed Mg grade**: J28 =
  `=TDS_TP*f_imp_TP*M_CaO/M_MgSO4*J10*10^6` = 71.44656935 kg CaO/m^3 PLS, one mole of CaO per mole of dissolved
  sulfate. It is CATION-INDEPENDENT — the acid charge fixes the sulfate, so `salts_CCD_TP`'s all-Mg
  declaration reaches the sludge speciation and nothing else — and it carries NO excess factor,
  since the whole cation load already sits inside `salts_CCD_TP`. J34 soda ash =
  `=Ca_res_TP*M_Na2CO3/M_Ca` = 2.64453316 kg/m^3 stays concentration-driven and does NOT scale with
  the lime dose. Sludge conv J62 = 0.4136139263 from the step's own speciation (74.3 Mg(OH)2 +
  215.1 gypsum + 2.5 CaCO3 + 0.1 flocculant = 292.0 kg/m^3 PLS ÷ DS 705.88 kg/m^3 at s = 0.50,
  ρ_s = 2.4). Wash J46 = 0.2819627715 raw `process_water`, formula-linked to J62 so it tracks any
  change in s. Closure: 0.99 + 0.4136 = 1 + 0.2820 + 0.1217, the last term being
  precipitated-solids volume entering as mass without tracked volume. Sink `sludge_stack_nv_50`,
  registered in `facility.py` with `ds_per_m3(..., rho_s=2.4)` to match the sheet's precipitate
  density — the function default 2.7 would bill dry solids 3.4% high against a volume derived at
  2.4 — with `s_feed` = 0.199 (291.96 kg precipitate in 1465.89 kg slurry per m^3 PLS) and
  `x_hyd` = 0.26 (1 − gypsum fraction 0.7366).
- **JX beneficiation circuit (locked by C4b-2; conditional on `S_TAILS`)**: `Sulfate Roast-Water Leach` D28 = `=0.7*1/(0.3/2.7+0.7)*1/3` = 0.2876712329, the water content of the fresh feed at 30 wt% (0.863013699 m³/m³) deflated by the loop factor 3. Split at runtime in `run_scenarios.py` `clay_lepidolite`, Lepidolite branch, into `process_water` 0.097676328 and `recycled_process_water` 0.189994905; the sheet cell remains authoritative for the total and is read before being overwritten. Make-up terms: impounded 0.083616554 + roaster cake 0.005246053 + press-filtrate bleed 0.008743422 + mill discharge 0.000070299. Returns: `thickener_overflow` (F55 = `process_water_recycle`) + TSF decant at `S_TAILS` = 0.55. Both doses target `classified_slurry_throughput` and are basis-inclusive, so `step_pv` is unmoved. D31–D36 hold the `recycled_process_water` row at a populated 0.0. Purchased 18,811,037.3 m³/yr = 408.9 m³/t LCE. Independent cross-check: beneficiation tails 170.8 + leach residue 38.5 = 209.4 t/t LCE against a patent's "nearly 200 t per t Li₂CO₃".
- **JX roast mass balance**: additions 0.5 / 0.15 / 0.10 t per t concentrate (Yan et al. 2012; lime +50% per Luong et al. 2013); f_ore = 0.8/(0.8 × 1.75) = 0.571429; `I51` = `J22` = 5.714285714e-4; `J10` = 0.229 × 0.571429 / 10³ = 1.307506053e-4.
- **JX precipitation mother liquor (locked by C4b-3, verified on the run of 2026-08-06)**:
  `Solution Processing-Sulfate` C56 = 0.0 and inert on both branches; conv set in
  `run_scenarios.py` as `1/1000 - y*c_in*ccf_in/(c_out*ccf_out)` = 9.78e-4 m^3/L (TP,
  13.4 Mm^3/yr) and 9.0571164581e-4 (JX, 2,008,977.9 m^3/yr, 1.0929 kg Li/m^3). Sink is
  per project: `process_water_recycle` at $0 on Clays (Nevada zero-discharge permit),
  `wastewater_treatment` on Lepidolite. Gate 2 closes on physical volumes, not on `y*POCF`:
  209,142.9688 + 2,008,977.9289 = 2,218,120.8978 = 1.000000 x basis; the POCF 1e-3 is a unit
  bridge and inert at this Case-2 step. No credit is taken for the 20% Li in the liquor; the
  Na2SO4/ZLD crystallizer that would recover it is a named out-of-scope gap.

### Recirculation loops (closed circuits)

When two steps form a closed circuit (e.g. a crusher and classifier with oversize recirculated for re-processing), the recycle is modeled at the step level — there is no separate loop object.

- **Basis inflation.** The looped steps are sized on the full recirculating throughput. With circulating load $\mathrm{CL}$ (recycle ÷ fresh feed), throughput is $(1+\mathrm{CL})$ × fresh feed. Inflate the entry step's IPCF by $(1+\mathrm{CL})$ and set the exit step's forwarding POCF to $1/(1+\mathrm{CL})$, so `step_pv` is $(1+\mathrm{CL})\,F$ for both looped steps while fresh input and forward output are held. Naive single-cell IPCF inflation on an ore-credit input *reduces* the step instead of loading it — inflate the basis, not the credit.
- **Deflate every `step_pv`-scaled quantity by the same $(1+\mathrm{CL})$.** Coproduct conversion factors and volumetric doses multiply against the inflated `step_pv`; each needs a compensating $1/(1+\mathrm{CL})$ or its absolute quantity inflates with the basis. A once-through reject tonnage or water dose otherwise runs $(1+\mathrm{CL})$ × over. Intensive quantities (CCFs, grades) are unchanged — they do not scale with basis.
- **Loop closure identity.** For the exit step, forward + reject + recycle sum to one on the raw basis: $y\cdot\mathrm{POCF} + (1-y)\cdot\mathrm{POCF} + (1-\mathrm{POCF}) = 1$. The $(1-\mathrm{POCF})$ term is the internal recycle — a declared internal circuit stream, not a sink-routed coproduct.
- **Entry inflation and exit deflation are a single edit.** An IPCF inflated by $(1+\mathrm{CL})$ without the matching $1/(1+\mathrm{CL})$ on the exit step's forwarding POCF forwards $(1+\mathrm{CL})$ × the fresh feed downstream and inflates the implied recovery. Verify both cells together; neither is correct alone.
- **TP scrubbing–classifying, worked.** 20% of classifier throughput recirculates, so the basis is
  $1/0.80 = 1.25\times$ fresh solids and $\mathrm{CL}$ (recycle / fresh) $= 0.25$. Entry inflation
  sits on D18 and D22; exit deflation is the `*(1-0.2)` term in E46; the coproduct conversion
  factor carries the same 0.80. Do not read the 20% as $\mathrm{CL}$ — $1/(1+0.20) = 0.833$, not
  0.80.
- **JX crushing–classifying, worked.** `loop_factor` = 3 is carried on `Sulfate Roast-Water Leach`
  `C18` (200% recirculation, Reja et al. 2022), so CL = 2 and the basis is 3x fresh feed. Entry
  inflation is applied in code, not on the sheet: `run_scenarios.py` sets
  `ipcf = rho_loose * loop_factor` and then `crushing.set_conversion_factor("rom_ore_feed",
  ipcf * crushing.step_ccf, field="ccf")`, so gate 5 holds by construction and measures
  1.000000000000. **The exit deflation sits on `classifying`'s POCF (0.3333333333), not
  `crushing`'s, which forwards at 1.0** — so BOTH `crushing.step_pv` and `classifying.step_pv` are
  3x loaded. Entry x exit = 3 x 0.3333333333 = 1.0. Consequence for any JX mine-size claim:
  `crushing.step_pv` 25,572,141.77 t/yr is loaded throughput; fresh ore is 8,524,047.2560 t/yr, and
  total material moved is 53,836,087.9328 t/yr at strip 5. Independent closure: 8,524,047.256 t x
  1,858 ppm = 84,299.5361 t LCE contained against `apv` 46,000, overall recovery 0.545673 against
  the product of the thirteen declared step yields 0.543491.
- **Reading the lithium ledger across a loop.** The raw interior seam reads $y\cdot\mathrm{POCF}$ (e.g. $0.93 \times 1/3$), which looks like a large loss but is not — the "missing" fraction recirculates. Evaluate the ledger on the loop's **forward-output exit** (`step_pv × POCF`), never on the raw internal edge.

### Water accounting

- **A separator's output volume is set by its wash requirement, not by an assumed product TDS.**
  The TP CCD declares `w_r_TP` on the tails-liquor basis and derives `TDS_CCD_TP` from the
  wash-water balance, all of it scale-free per kg of ore solids so nothing on
  `Constants & Derivations` needs the m3 basis. Do not declare `TDS_TP` and back-solve PLS volume
  from the ore-basis dissolved mass: that makes plant size hostage to the residue fraction across
  the 0.658-0.838 acid-stoichiometry bracket for `f_res_TP`, and omits acid-derived sulfate from
  the TDS pool. Where a
  separator's cake carries reagent-derived solids, they belong in the cake CF alongside the
  process residue (`s_cake_CCD_TP`), not nowhere: the complement of any sulfate removed from
  solution must appear as a solid.
- **Dose basis follows the driver (CD3, 2026-08-08).** A dose written per unit volume of a
  carrier moves whenever the carrier is re-encoded. Only concentration-driven duties (flocculant,
  pH control, trace-metal polishing) belong on the m³-liquor basis; mass-driven quantities belong
  on a feed-mass basis or as a formula on named constants.
- Every `process_water` dose states whether it is **gross** (full slurry water) or **net of recycle**. The choice may differ by project where the operating context differs, but must be stated in `main.tex` as a modeling choice, never left incidental. TP: net of recycle, sized structurally, justified by the Nevada zero-discharge water pollution control permit. JX: net of recycle in the beneficiation circuit, sized structurally; leach circuit gross by declaration, since every stream leaving it is Li-bearing or contaminant-laden. JX recycles less than TP by design, not by omission — no zero-discharge obligation, water at $0.35/m³ midpoint, and a flotation circuit that needs a bleed to hold selectivity.
- **Size make-up structurally; do not use a recycle fraction.** A recycle fraction is a free parameter requiring a source; a make-up requirement is derived. For any closed sub-circuit, raw water in equals water leaving in solid streams and vapour. Decompose a pathway into sub-circuits, give each one make-up entry, and place that entry where the disclosure places it.
- **Every draw is dosed explicitly; internal returns are dosed at $0.** A step that physically adds water carries a dose stating its full requirement, as `process_water` where the water is bought and as `recycled_process_water` (cost 0) where it comes from a declared return. Leaving a step at zero hides which step draws how much and makes the largest draw in a flowsheet invisible; the TP scrubbing draw, 30,284,307.9 m³/yr, sat unstated under the older reading. Gate 3 is met by dosing every draw and balancing the returns per circuit, not by naming a deficit. Where a make-up entry is placed at the circuit level rather than at the drawing step (TP `classifying`, `ccd`), the cell means *circuit make-up*, not that step's own draw — say so in the units string, since the two differ.
- **Water volume per m³ of stream** $= 1 - w_{\text{nonwater}} \cdot \rho_{\text{mix}}/\rho_s$. **Which substitution the CCF permits depends on what the CCF weighs; establish that before applying either form.**
	- **Solids CCF** ($\text{ccf} = w_s \rho_{\text{mix}}/10^3$, the slurry families): reduces to $1 - (\text{ccf} \times 10^3)/\rho_{\text{grain}}$. Prefer this form here to $(1-w)/w$ forms: it needs only the ccf already on the object plus the grain density, and $w_s$ cannot be recovered from a ccf without $\rho_{\text{grain}}$ anyway.
	- **Whole-carrier CCF** ($\text{ccf} = \rho_{\text{mix}}/10^3$, the TP PLS family, where $c$ is measured per kg of liquor and the solids are dissolved): does **not** reduce. Use $(1 - w_{\text{TDS}}) \cdot \text{ccf} \times 10^3$, equivalently $1 - w_{\text{TDS}} \cdot \text{ccf} \times 10^3/\rho_{\text{grain}}$.
	- The two are not interchangeable. On TP PLS the solids form returns 0.5967742 against the correct 0.9697581 m³/m³, understating water by 38.5% and reading as a 33.5% circuit-B closure failure that does not exist.
	- $\rho_{\text{grain}} = 2.6$ t/m³ model-wide; 2.11 for Li₂CO₃ streams; 2.4 for the TP impurity-sludge precipitate composite.
- **Solution-density mixing rule for PLS-family CCFs — DECIDED 2026-08-07: O1, ideal volume
  additivity at grain density**, $\rho = 1/(w/\rho_s + (1-w)/\rho_w)$. Landed as
  `Constants & Derivations` `rho_PLS_JX` =
  `=1/(w_TDS_JX_wt/Rho_Grain_Hardrock+(1-w_TDS_JX_wt)/Rho_water)` = 1.050826224 t/m^3 at
  $w$ = 0.07681955526, and as `POCF_leach_JX` = 0.943461645 m^3 PLS per m^3 20 wt% leach slurry
  (liquor water volume plus the grain volume of the dissolved third). Thacker Pass already encoded
  O1 at $\rho_s$ = 2.6 (`Sulfuric Acid Leach` J10, now
  `=(1/(TDS_TP/Rho_Grain_Rock+(1-TDS_TP)/1)/10^3)`), so the decision moves nothing on TP. A water-volume
  basis and an empirical-correlation basis are both rejected. The grade is unaffected by the
  choice: $c$ is a mass ratio, so `c_PLS_JX` = 949.1877567 ppm holds under any of the three.
- **Dewatering credit belongs at the facility that dewaters**, not in the upstream process block. If a block contains no dewatering unit, its coproduct leaves at the block's own discharge density and the sink receives that full volume; credit the reclaimed water through the make-up term instead. This keeps water cost and sink cost from moving together on a single parameter.
- **Closed modeled set; sheet formulas are the default encoding.** There is no project selector and no per-project override column. The modeled set is closed to Silver Peak, Thacker Pass, and Jianxiawo; generality to catalog projects is out of scope. Catalog columns and catalog-only rows are inert — their correctness is not audited, and a defect confined to them is not a finding. Every derived quantity is encoded exactly once, as a sheet formula computing from named inputs; code literals and sheet literals are both fallbacks. A shared pathway sheet encodes its single modeled user's values; declare that in the comment of every formula cell that does so. Rules for the encoding:
	- Cross-sheet references use workbook named ranges, never positional addresses; a positional cross-sheet reference in a new or modified formula is a finding. Where the referenced value is a field inside a composite cell (the `Li: ...; K: ...` constituent strings), the named range names a single extraction cell on the `Constants & Derivations` sheet — the only permitted on-sheet parse of that string — with a delimiter-count check cell beside it. Delimiter counts are per source string, not a shared constant: the Silver Peak intermediate carries a `Cl:` field the Jianxiawo strings do not, and single-field strings carry none. `helpers.clean_input_str` splits on `;` only: a `,` delimiter silently folds the following key-value pair into the preceding value **as a string** and drops the constituent entirely. Verified — `'Cl: 76811, SO4: 3597'` parses to `{'Cl': '76811, SO4: 3597'}` with `SO4` absent and `Cl` non-numeric. The delimiter-count cells catch this on the sheet; nothing catches it at load.
	- **Derivation flows one way.** Source data flows sheet → scalar on `Constants & Derivations`. Composite cells are never written back to from a scalar, and a composite cell that carries a derived value keeps that value as a literal. The consequence is stated rather than hidden: runtime write-backs into parsed vectors are **not**
  eliminated by this rule. A derived quantity whose only route into the model is a composite lands
  as a manually entered literal in that composite, with its derivation kept on
  `Constants & Derivations` and the composite value treated as a literal at freeze — the
  `c_PLS_JX` → `Project-Specific Data` AJ21 `Li: 949.19` pattern. This
  satisfies the no-write-back rule.
	- Derivation content lives on the `Constants & Derivations` sheet, which is outside the input schema: no sheet name appears anywhere in the code, and `helpers.py` `build_data_dict`, `build_locations_dict` and `build_facility_dict` all read `data/*.csv`. Three labeled contiguous sections, colored under section 6: **physical constants**; **project-data extractions** (one parsed field per row, named range per cell, delimiter-count check per source string); **derived intermediates**. No derivation cells on any loader-read sheet, no new rows or columns in any parsed region, never scattered helper cells.
	- Basis annotation is the sheet's `Source` column, not a cell comment. Columns are `Name / Quantity / Unit / Source`; the `Source` column discharges the commented-literal requirement below and is visible without hovering. An unsourced derived literal is a finding.
	- Field extraction uses `REGEXEXTRACT`, pattern `(?:^|;)\s*<label>:\s*([0-9.]+)`. The leading `(?:^|;)` is load-bearing: without it a bare `B:` matches the `b:` inside `Rb:`. `TEXTAFTER`/`TEXTBEFORE` are unavailable in Sheets and must not be used.
	- CCF and density formulas reference midpoint dose cells. The resulting scenario inconsistency (a conservative run carrying a midpoint-derived density) is a declared accepted approximation, stated in the cell comment; it matches the pre-existing single-CCF-across-scenarios structure and loses nothing against it.
	- Where a formula is infeasible, the literal carries a comment naming its derivation inputs and their values at freeze, so staleness is detectable by comparing the comment against the live cells. An uncommented derived literal is a finding.
	- **Do not consolidate `Project-Specific Data` `AJ11` = 2.7 into `Rho_Grain_Hardrock`.** `AJ11` is *Initial Density*, the in-situ rock density used with the swell factor, not a grain density.
	- Runtime computation survives only where two or more MODELED projects share the sheet and no selector exists — currently the `Solution Processing-Sulfate` precipitation overrides (TP and JX carry different CCF families at that step) and the three sulfate-route wastewater sinks (`precipitation_step.mother_liquor`, `thicken_dewater.pressed_water`, `wash_purif_step.wash_water`), where the sheet encodes the Clays reading `process_water_recycle` under the Nevada zero-discharge WPCP and the Lepidolite branch overrides all three to `wastewater_discharge_cn`. It lands per the C4b-3 pattern: sheet cell populated 0.0 — not blank, since `set_reagents` raises `KeyError` on an absent row — with a comment pointing at the code. Branch bodies otherwise reduce to `add_target_comp` wiring plus the C4b-2 split of the D28-authoritative total; a new numeric literal or derived quantity in either `clay_lepidolite` branch is a finding unless it cites this rule.
- **A recycle stream is only reusable where it is free of the tracked constituent.** Precipitation
  mother liquor carries the lithium not recovered at the precipitation yield (TP: 0.2378 kg Li/m³)
  and must never be dosed as wash or make-up water — doing so returns constituent to the stream it
  was removed from and silently breaks the receiving step's yield. Route such a stream for water
  closure only, take no credit for its constituent, and source washes from raw water or from a
  demonstrably constituent-free circuit (e.g. pre-leach beneficiation overflow). Where the
  disclosure recovers the liquor through equipment outside the model's scope (a ZLD crystallizer),
  say so and leave the energy and capital as a named gap rather than implying free clean water.
- **Cake washing is what decouples a coproduct's volume from its constituent loss.** A solids
  stream leaving at solids fraction $s$ carries $(1-s)/s$ kg liquor per kg solids by arithmetic;
  whether that liquor is product-bearing is a flowsheet choice. Model the wash as a basis-additive
  dose equal to the retained cake liquor less the declared residual, so the yield states the
  constituent loss and the coproduct conversion factor states the wet volume, independently. State
  that perfect single displacement is assumed where it is.
- **The recycled-draw acceptance test is per circuit, and admits only constituent-free returns.**
  Σ(recycled doses in a circuit) ≤ Σ(returns available to that circuit). Do not sum over the
  `process_water_recycle` sink: precipitation mother liquor routes there but is constituent-bearing
  (previous bullet) and not available to any draw, so a sink-wide sum passes
  spuriously — on TP by 13,407,912.4 m³/yr. Where a circuit's return is internal to one step and
  has no coproduct row (the TP CCD wash solution feeding the leach repulp), bound the test by a
  computable proxy and state the assumption rather than inventing a route.
- **Recycle streams route to `process_water_recycle` at 0 $/m³**, registered in `facility.py` `tailings_handling` AND added to the `Facility` constructor sinks list in `run_scenarios.py`. `ProductionStep.__init__` validates coproduct sinks against the constructor list, so registering the cost alone raises `KeyError` at construction.
- **A flotation circuit needs a bleed, and the bleed is asserted, not derived.** Recirculating process water in silicate-lithium flotation accumulates dissolved Al³⁺/Fe³⁺/Mg²⁺ and residual collector, suppressing collector adsorption and degrading recovery over successive cycles (`sauberEffectRecycledProcess2025`, spodumene, six cycles — abstract-level read, unverified against the `.bib`). Sizing a bleed on contaminant load needs a dissolution rate that is not in hand, so take a whole stream as the bleed at the circuit's most concentrated point and say plainly that its magnitude follows from the mass balance rather than from a contaminant limit. Take a whole stream, not a fraction: a coproduct row carries one sink, so a fractional bleed requires splitting the stream into two rows.
- **The reclaim credited to a make-up term depends on a declared placement solids fraction.** Where no disclosure fixes it, carry it as a named open assumption with its cost span, as with `S_STACK`; JX `S_TAILS` = 0.55, span 0.55–0.85 = $38.37/t LCE. Do not substitute a recycle percentage for it.
- **Fluoride and the lepidolite contamination burden sit on the leach circuit, not on beneficiation.** Beneficiation is mechanical and reagent-light; the F is in the concentrate lattice and mobilizes at roasting and leaching. This is a reason to keep the two circuits' waters separate, not a reason to under-recycle in beneficiation.
- Implied water addition at a density change: $W = M_{\text{solids}}\left(\frac{1-w_{\text{out}}}{w_{\text{out}}} - \frac{1-w_{\text{in}}}{w_{\text{in}}}\right)$. Compare against the dosed water at every step; a mismatch is either free water or double-counting.
- **JX water-leach PLS pair (landed 2026-08-07 `86ca597a`; completed by CD3 2026-08-08
  `fb4a02b8`)**: `Sulfate Roast-Water Leach` J46 = `=J45*POCF_leach_JX` = 0.8962885628 (physical
  0.9434616450 at yield 0.95); J51 = `=rho_PLS_JX/10^3` = 1.050826224e-3; J56 = `=(1-J46)` =
  0.1037114372, decomposing as insoluble grain 0.0565383550 + 5% of the liquor 0.0471730823,
  implied cake solids 0.7549, sink `slag_stack_cn_75`. K10/K22/K51/L10/L22 = `=rho_PLS_JX/10^3` and L51 = `=rho_PLS_JX/10^6`
  (CD3). R = 1.000000 at every primary-input seam, including `water_leach -> impurity_removal`, in
  both the half-landed and completed states; the earlier high reading was Case-2 sizing inflation at
  `water_leach`, not a seam R.
- **SP pond evaporation is routed in code**: `evap.set_conversion_factor("evaporated_water", evap_rate)`. This over-closes by 0.579%; the exact form is `evap_rate*(1 - y*c_in*CCF_in/(c_out*CCF_out))` = 885.474 for SP. Within the 0.5%–1% band: recorded, not chased.

### Acceptance gates for any new or modified step

1. **Lithium ledger.** With $A_k = \text{step\_pv} \times c_{\text{Li}} \times \text{CCF}$:
	- The general invariant at every step is $A_{\text{in}} = A_{\text{out}} + \sum A_{\text{coproduct}} + \text{declared loss}$, to <0.5%.
	- $A_{k+1} = y_k \cdot A_k$ is the *special case* where the step neither upgrades nor rejects grade and $y$ is a bulk split at feed grade. Do not apply it elsewhere.
	- In a Case-2 step this relation is an algebraic identity for the volume-defining constituent and tests nothing. The live test there is whether the step's ($c$, CCF) pair agrees with the upstream output's pair.
	- **A grade rise with no mass leaving is a defect at any magnitude.** An upgrade is legitimate only if a routed coproduct carries the complementary mass at the complementary grade, and the two-product formula closes.
	- Across a recirculation loop, evaluate at the loop's forward-output exit (`step_pv × POCF`), not the raw internal seam (see Recirculation loops).
2. **Volumetric closure**: with dose placement and yield semantics declared (see Coproducts), $V_{\text{out}} + \sum V_{\text{coproduct}} = 1.000 \times \text{step basis} + \sum(\text{basis-additive doses})$, all terms in the same unit — verify the POCF is a volume ratio, not a mass ratio, before summing. A residual ≤ 0.5% of the step basis closes the step: record it, do not chase it. Above 0.5% is a finding. A stream *declared physical* with no coproduct row is a finding at any magnitude — a missing route is structural, not a residual.
	- **A circuit-level make-up dose is not the step's own draw and cannot enter this sum as written.** Where the cell means circuit make-up (TP `classifying`, `ccd`), net the internal return the basis already contains before summing: at `ccd` the raw draw is `I34 - G34` = 0.9421348565 − 0.3011254440 = 0.6410094125, and `I34`'s subtracted thickened-feed water plus `G34` reconstructs the basis water 0.6903473156 exactly. Using `I34` raw inflates the residual from 4.3500% to 34.46%.
	- **A step whose basis is defined on a phase that no longer exists cannot close this gate, and that is not a defect.** The TP `ccd` basis is `acid-inclusive` because `I10 = $G$10` and `G10` builds volume from ore grain plus water plus *liquid* `H2SO4` at `Rho_H2SO4` = 1.84, while at CCD the acid has reacted and its sulfate is counted at grain density inside `salts_CCD_TP` and `s_cake_CCD_TP`. The contraction has no term and the step carries a standing 0.0434996924 per basis. Deferred as accepted debt with the full attribution; do not re-derive, and do not close it by moving a cell.
	- **`I62`-family cake volumes and `facility.py` `ds_per_m3` are a matched pair.** Both use `1/(w_s/rho_s + (1-w_s)/rho_w)`, pricing entrained liquor at water density. The pair reproduces cake dry-solids mass exactly (TP claycake 2,869,842.15 t DS/yr = `ore` x `s_cake_CCD_TP` = 42.961709 t DS/t LCE). "Correcting" either one alone to a true liquor density breaks the tailings tonnage — TP claycake would under-bill by 6.08%. Change both or neither.
3. **Water closure**: step-level water balance exact to 0.1%; where gates 2 and 3 both apply to a water-dominated stream, gate 3 governs the water sub-ledger and gate 2 governs total volumetric closure; facility-level residual two-sided and attributed, with unattributed residual < 1%. Declared internal-return nodes are named and balanced individually; a step-level deficit matching a named return is not a failure. Water crossing a step boundary inside the flowsheet is tracked — carried on a stream, dose, or coproduct — and a term newly brought into tracking lands with everything it moves in the same edit. Water leaving with a coproduct to a sink need not be resolved into its ultimate fates: the reclaim credited back to the plant is whatever the sink's declared solids fraction releases, and the balance is declared lost. State that declaration in the writeup of the block or sink that carries the stream; do not itemize evaporation, seepage, or entrainment separately unless a parameter depends on the split.
4. **Scenario monotonicity**: conservative ≥ midpoint ≥ optimistic for every cost and consumption parameter (flag physically justified inversions explicitly).
5. **Input-side identity**: `R = ccf_in / (IPCF * step_ccf)` equals 1 at every primary input, except where a carrier change is declared and `c` has been re-based in the same edit. The model has two declared carrier changes. The TP CCD boundary is the first; since C3a it is cleared (R = 1 at `impurity_removal`). The second is `Sulfuric Acid Plant` `acid_absorption`, where SO3 gas becomes liquid H2SO4: `R = ccf_in / (IPCF * step_ccf) = 1 / 1.225010304 = 0.8163197`, and `c` re-bases exactly to `M_S/M_H2SO4 = 0.3269438` kg S per kg acid. `R = 1` is unattainable there without stating the S fraction per kg SO3 against a kg H2SO4 basis, which is wrong chemistry. A new R != 1 remains a defect unless the carrier physically changes at that seam and `c` is re-based in the same cell.

---

## Calculation Standards

- **Show all intermediate steps** and flag every assumption explicitly
- **Derive before proposing.** Establish the governing physics or accounting identity first, then read off what value it implies. Never select a value and assemble support for it afterward. A number that arrives before its derivation is a hypothesis and must be labeled one. Two symptoms that this has happened: an assumed parameter that lands on a conveniently round result, and a justification that appeals to what another cell or label already says instead of to a mechanism.
- **Existing parameters are decisions, not evidence.** Sink labels, block names, registered solids fractions and prior cell values record what was chosen. If one of them appears to confirm a derivation, the confirmation is circular unless that value was itself derived from the same physics. When an existing cell is the only support for a proposed value, the proposal has no support.
- **No guessing or confabulation** — if a value cannot be sourced or derived, say so
- **Combustion efficiency** — always divide net thermal duty by 0.80 to get fuel input. This applies to consistency checks as well: a scenario's fuel input is compared against net duty ÷ 0.80, never against net duty.
- **A heat balance is process demand, not fuel.** Sum the sensible, latent and reaction terms to get demand, then fired duty is demand/η. The assumed efficiency is the declared input and the duty falls out of it, which keeps the efficiency round and the duty precise. Demand excludes flue-gas loss, shell loss and heat leaving in solids discharged at process temperature. State the exhaust temperature any superheat term assumes: a demand computed to a stack temperature already contains the feed preheater, and dividing it by an efficiency that also credits preheat counts it twice.
- **Propane conversion** — HHV = 24,174 Btu/L; therefore 1 MMBTU = 41.37 L propane
- **CAPEX methodology** — anchor bare equipment cost (vendor data, regression, or EverBatt) → installation multiplier → auxiliary adder breakdown (itemized %) → total installed. Prefer primary references (specific spec sheets, recent vendor data) to secondary references (e.g. references like Peters & Timmerhaus (1991), Ulrich & Vasudevan (2004)) wherever possible. 
- **Electricity auxiliary adders** — use reasonable, physically grounded percentage ranges; the CAPEX/electricity adder distinction is stated once under Key principles
- **Labor** — derive from Ulrich & Vasudevan operator-per-shift factors × 4.5 shift factor (3 shifts/day × 1.5 relief factor); justify scaling exponent physically. If I don't provide the labor breakdown, ask me for it. 
- **Six-tenths rule** — `prim_equip_scaling_exponent = 0.60` unless stated otherwise (six-tenths rule); refer to the number used in the `Machine Blocks Data` sheet. 
- **A cost exponent is not a utility exponent.** `Machine Blocks Data` row 32 `prim_equip_scaling_exponent` scales purchased equipment cost; row 9 `scaling_exponent_throughput` scales every utility in `_calc_cont_scaling` (electricity, gas, diesel, propane, cooling water, steam, compressed air). The six-tenths rule and every published cost-capacity exponent belong in row 32 only. Specific energy is an intensity: absent a measured specific-energy-versus-size curve, row 9 is **1.0** for continuous blocks. A sublinear row 9 makes the modeled kWh per unit fall as the plant grows, which no unit operation does, and it silently breaks the block's own electricity derivation — `classifier_generic` derived 0.15/0.25/0.40 kWh/m³ and delivered 0.1054 at TP scale until this was corrected (2026-08-23, `Master_Data_File.xlsx` `43ee158f`, `X9`/`Y9`/`Z9` 0.67 → 1.0, sourced to parallel-cluster scaling at fixed pressure drop). Batch blocks scale on `ltr` and never read row 9. When correcting a row-9 exponent, check the block's `base_volume` and `electricity_base_total` describe the same plant first: on `crushing_cycle` they do not, and the correction there would compound an existing overstatement rather than fix one.
- **One block, one throughput basis.** A block's electricity, capital, footprint and labor derivations all read the same solids or volumetric loading. Where a `step_ccf` comment names a degenerate reduction — `Sulfuric Acid Leach` `I10` reduces to the two-phase form 4.2996e-4 "at zero dose" against the live acid-inclusive 4.7572e-4 — the degenerate value is the trap, not the operating one, and a derivation built on it under-sizes everything downstream of it. On `multi_stage_ccd_thickening` this ran 1.1064x through the settling area, the thickener diameter, the rake drive and the underflow pump at once (2026-08-23, `bb0b00f2`). Check the two loadings agree before auditing any single parameter of a block.
- **CEPCI inflation** — 2019 = 607.5 (published). Verify the current-year index each session before inflating any published cost; do not reuse a previously assumed current-year value.
- **Slurry density** — always derive from the mixing formula: $1/\rho_{\text{mix}} = w_s/\rho_s + (1-w_s)/\rho_w$, where $w_s$ is the solids mass fraction, $\rho_s$ is the grain density (typically 2.7 t/m³ for hard rock), and $\rho_w = 1.0$ t/m³. Show the derivation when first used in a block.
- **Li₂O ↔ Li ppm conversion** — Li/Li₂O mass ratio = $2(6.941)/29.881 = 0.4646$. Always derive, do not round or approximate.
- **Verifying existing writeups** — when asked to check a previously written block, systematically verify every numerical value (conversion factors, mass balances, cost arithmetic, specific energy intensities) before accepting. Do not assume prior work is correct.
- **Sink routing is judged on physical representation, never on cost.** Choose a sink by whether
  its declared solids fraction, hazard class, and placement method approximate what physically
  leaves the step. Every sink unit cost carries unsourced parameters owned by C5f-2
  (pi US_NV, x_hyd, s_final, stack placement), so a cost difference between two candidate sinks is not
  evidence about either one and does not belong in a routing argument in either direction. Do not
  quote a tailings cost as a result and do not tune an assumed s to move one. A cake at or above roughly 80 wt% solids is treated as
  approximately solid and stacked where the material is nonhazardous. Hazard class is a separate
  declaration from solids fraction, resolved against the disclosure and the governing waste
  standard, not against the price.
- **`maint_override` vs. `opex_fraction_of_capex`** — these are distinct fields. `maint_override` is annual maintenance as a fraction of scaled equipment cost. `opex_fraction_of_capex` is a separate operating cost adder. Do not confuse them.
- **Claude never writes to project files or the workbook.** Every change ships as exact proposed
  text — code with its insertion anchor, cell comments verbatim, LaTeX as a replacement block — and
  the user lands it and re-uploads. Sandbox copies may be patched to measure gates, and the patch
  must be stated as a sandbox measurement, never as a landed edit.

### Resolution and tolerance

This is a screening-level technoeconomic model. It exists to rank pathways and locate the dominant cost and emissions drivers.

- **State the tolerance before chasing a discrepancy.** A term worth pursuing moves a headline figure by more than roughly 1%, or changes which driver ranks first. Below that, record a one-line queue item and move on.
- **A residual is not a defect.** Volume, mass and constituent balances carry small remainders from rounding, ideal-additivity density models and declared allowances. State the residual and its size; do not restructure the sheet to eliminate it.
- **Prefer the smaller edit.** Where a defensible approximation and an exact restructure both fit, take the approximation and record what it costs. Adding a step, a constant or a machine block to remove a sub-1% error is a net loss: it adds parameters that then need sourcing and maintenance.
- **Answer at the scale asked.** When the request names a resolution — "the forest," "high level," "significant" — that is the resolution of the answer. Detail below it goes in the queue.

---

## Three-Scenario Structure

Every parameter in the spreadsheet has three columns: `.conservative`, `.midpoint`, and `.optimistic`. These do not represent probability distributions — they represent a structured uncertainty envelope around the central estimate, suitable for sensitivity analysis. The scenarios should be derived consistently:

### What drives scenario variation by parameter type

**CAPEX**
- *Conservative*: premium material specification (e.g. corrosion-resistant alloys, fluorine-resistant refractory), high installation complexity, first-of-kind contingency, high-end auxiliary adder fractions
- *Midpoint*: standard equipment specification, typical installation complexity, central adder fractions from Peters & Timmerhaus
- *Optimistic*: simplified specification, domestic/low-cost fabrication, minimal contingency, low-end adder fractions

**Electricity**
- *Conservative*: high load factor on primary motor, large auxiliary electrical adder (additional pumps, fans, instrumentation), conservative scope (all peripheral loads included)
- *Midpoint*: typical load factor, central auxiliary adder
- *Optimistic*: lean load factor, minimal auxiliaries, tight scope definition

**Thermal utilities (NatGas / propane / diesel)**
- *Conservative*: low thermal efficiency, high overheating/exhaust penalty, less heat recovery
- *Midpoint*: typical industrial efficiency for the equipment class
- *Optimistic*: best-practice efficiency, full heat recovery integration

**Labor**
- Base FTE is derived from Ulrich & Vasudevan operator-per-shift factors and is held constant across scenarios (it is a physical staffing minimum, not an uncertainty parameter)
- The scaling exponent (typically 0.5) is also held constant
- Scenario variation in labor cost comes from wage rate assumptions at the facility level, not from the machine block

**Availability**
- Typically held constant across scenarios within a block (e.g. 90% or 92%)
- Scenario variation in throughput comes from the production step level, not the machine block availability

**Scenario bands describe design and capital choices, not equipment condition.** A cost-minimising operator does not run a broken exchanger or an untuned circuit, so a band spanning "working" to "not working" is not an uncertainty envelope. Span integration depth, vintage, or the presence of an optional recovery stage, and name the physical constraint that caps the optimistic end.

### Key principles (reiterated where needed) 

- **Auxiliary adders for CAPEX and electricity are not necessarily the same percentages.** CAPEX adders are highest for mechanically intensive systems (multiple drive trains); electricity auxiliary adders are highest for thermal systems (exhaust fans, combustion air blowers, induced-draft fans can rival the primary drive's draw).
- **The optimistic scenario must be physically achievable.** If an optimistic thermal value implies greater than ~100% heat recovery efficiency, it must be flagged or rejected. State the implied heat-recovery requirement explicitly and check it against the ÷0.80 fuel floor, not against net duty.
- **Scenario ranges should reflect real engineering uncertainty, not arbitrary ±X%.** Where an anchor cost comes from a published source (e.g. EverBatt), ±30% is a reasonable Class 4–5 envelope. Where the anchor is itself uncertain (e.g. a regression with R²=0.78), the range should be wider.
- **All three scenarios must be independently derivable.** A scenario value that is simply "midpoint × 1.3" with no physical justification is weaker than one anchored to a specific efficiency assumption, material specification, or installation factor.
- **Diesel consumption for mobile equipment fleets must account for all machines in the block.** When a block encompasses multiple machines (e.g., excavator + loader + dozer), the diesel total must reflect the full fleet using duty-appropriate load factors from vendor telematics data (e.g., Cat Performance Handbook), not just the primary machine.
- **Power-based scaling for crushers and mills.** When anchor pricing is per-unit at a known motor power, scale to required power using the six-tenths rule, then apply installation multipliers. Do not scale installed cost directly.
- **Cell-volume-based sizing for flotation.** Size flotation circuits from required cell volume ($V = \dot{V} \times \tau / 60$), then cost individual cells using published cost models (e.g., Arfania et al. 2017). Do not estimate flotation CAPEX as a lump.

---

## Source Handling

**Any source found during research — whether from web search, project knowledge, or prior context — must be recorded in the Sources section of the relevant block writeup.** Specifically:

- Every claim, benchmark, cost figure, or technical parameter that is not derived from first principles must be attributed to a specific source
- Include a direct URL or DOI link wherever one exists. Format as: `Author(s) Year, \textit{Title}, \url{https://...}`
- If a source was found via web search, include the URL of the specific page or document retrieved, not just the domain
- If a source is a project disclosure (feasibility study, technical report, NI 43-101, etc.), name the project, the issuing company, and the year
- If a source is a vendor datasheet or product page, name the vendor, product line, and the URL if accessible
- Do not cite a source you have not actually read or verified — if a value is described as coming from a source but the source was not checked, flag it as "attributed to X but not verified"
- Do not cite McKinnon & Piecyk or similar logistics references for mine haul costs — these cover road freight only and are not applicable to mining equipment

**Prefer a disclosed ratio over a derived chain.** Where a disclosure reports the quantity directly,
take it and stop. A derivation whose every intermediate step is a declared allowance is not more
rigorous than the measurement it reproduces — it is less, because tuning the allowances until the
answer matches and then citing the match as validation is circular. The acid plant electricity line
was built three different ways from the same steam-cycle chain, moving 267 -> 310 -> 269 kWh/t acid,
before being replaced by the disclosed net export; none of those moves was new information. When a
cross-check "confirms" a derivation, ask which of the derivation's inputs were free.

**Normalise a borrowed ratio on the source's own denominator.** When transferring an intensity from a
disclosure into the model, numerator and denominator must both come from the disclosure, and the
result should be expressed on the receiving block's own `step_basis`. The acid plant power figure is
per tonne of **sulfur** — the burner's basis — computed from the disclosure's 9.15 t S/t Li2CO3, then
applied to the model's 9.478. Dividing disclosed GWh/y by the model's intensity would have understated
the credit by 3.5%.

**Single-point anchors take a parametric +/-30% band.** Where a quantity rests on one disclosed
operating point and no range exists, apply the Class 4-5 envelope already used for capital anchors,
and say in the text that it is a statement about estimate confidence rather than about plant
performance. Do not manufacture a range by ranking unsourced intermediate parameters — that produces
a spread which measures the parameters, not the plant.

**Name the disclosure vintage at every cross-check.** For Thacker Pass the $88/t on-site acid figure
is `rothFeasibilityStudyNational2022` at ~66,000 t/yr, while Tables 14-4, 18-15, 18-25 and 19-3 are
`sgscanadaincSK1300Technical2024` at 135,092 t/yr average product. The model runs 66,800 t/yr. Any
comparison states which disclosure and which scale, because economies of scale mean the model should
sit **above** the 2024 tables per tonne on every sublinear term — so landing below is a larger anomaly
than the raw difference suggests.

Sources that cannot be located or verified should be listed as: `[Source not verified — value flagged for review]` rather than omitted or silently accepted.

`Project-Specific Data` holds disclosure benchmark consumptions (propane, soda ash, quicklime, electricity)
for the modeled projects in the block beginning at the `Reported Data` label and running through `Other?`.
Anchor on labels, not row numbers: three `material_impact.sulfur.co2.*` rows were inserted above it and
shifted the whole block. Any claim about a project-level consumption rate is checked against that row before
it is written, and a divergence is reported as a finding rather than absorbed.

---

## Running the Model (environment notes)

> ## ⚠️ `evaluate_project` LEAVES `sc` AT OPTIMISTIC ⚠️
>
> `evaluate_project` leaves the `SupplyChain` in its last scenario pass, which is **optimistic**.
> `run_topn_scenarios` does restore midpoint. Any `_build_steps_cost_series` or
> `_build_steps_impact_series` call made directly after `evaluate_project` returns **optimistic**
> figures, not midpoint. The three-call reset — `helpers.update_machines(sc, "midpoint")`,
> `helpers.update_materials(sc, project_data, "midpoint")`, `sc.update_apv(apv)` — does **not**
> work: it returns the optimistic `avg_opex` and zeroes `maint_cost` and `fixed_over_cost`. Rebuild
> the midpoint pass instead: `clay_lepidolite(sc, p, f)` (or the pathway's builder) →
> `tailings_handling(sc)` → `helpers.update_materials(sc, p, "midpoint")` → `sc.update_apv(apv)`.
> Confirm the returned `avg_opex` matches the midpoint headline before trusting anything downstream.

The model reads sheets directly from `./data/Master Data File.xlsx` via `helpers._open_table`, which
dispatches on the path: a `.xlsx`/`.xlsm` path reads the workbook, a directory path falls back to
`<dir>/<Sheet Name>.csv`. `_resolve_sheet` handles Excel's 31-character truncation, so
`Brine-Batch Chemical Purification` resolves to the stored `Brine-Batch Chemical Purificati`
without a rename table.

> ## ⚠️ NEVER ROUND-TRIP THE WORKBOOK THROUGH OPENPYXL ⚠️
>
> `openpyxl.load_workbook(...); wb.save(...)` strips the cached values of **every** formula in the
> workbook, not just the cells touched. On 2026-08-26 a two-cell counterfactual saved this way left
> 844 formula cells with no cached value and `check_workbook_formula_cache` returned 844 misses, so
> the run could not proceed. To build a counterfactual, patch the parsed structures at load time —
> monkeypatch `helpers.build_facility_dict` and edit the returned dict — never the file.

> ## ⚠️ NEVER EXPORT SHEETS THROUGH EXCEL "SAVE AS CSV" ⚠️
>
> Excel writes the *displayed* value, not the stored one — rounded to the cell's number format, with
> `$`, `%` and thousands separators retained. On 2026-08-20 a single such cell
> (`Sulfate Roast-Water Leach`, `primary_output_1_ccf` / `stream_clarification`, exported as
> `0.0000011` against the stored `1.050826224e-06`, relative error 4.68e-02) moved JX `avg_opex` by
> −400.60 $/t and `avg_co2` by −1.0042 t/t, and silently invalidated a full figure set. The same
> export rounded 59 cells on that sheet, 49 on `Sulfuric Acid Leach`, 30 on `Solution Processing-Sulfate`
> and 27 on `Solution Processing-Chloride`. If a CSV folder is ever needed, generate it with openpyxl
> writing `ws.cell().value`, never through Excel.

- Entry point is `python3 run_scenarios.py`, which calls `run_all(...)` and emits 18 PNGs to `figures/` plus `../Costs-Emissions/reported_both.csv`. No manual comment-toggling.
- `helpers.check_workbook_formula_cache(path)` must return empty before a run. `data_only=True` reads Excel's cached results and openpyxl does not evaluate formulas, so recalculate and save in Excel first. `data_only=False` returns the formula string, which is the usual cause of a run that "reads the formulas instead of the numbers".
- Constructor signature: `SupplyChain(transp_data, loc_data, machine_data, material_data)`, then `run_scenarios.evaluate_project(sc, projects_data[proj], data_folder, detail=0, plot=0)`.
- `evaluate_project` returns a dict keyed `midpoint` / `conservative` / `optimistic`; `avg_opex`
  and `avg_co2` live one level down, inside each scenario.
- Headline metrics: cost = `avg_opex` ($/t LCE), emissions = `avg_co2`/1000 (t CO₂eq/t). Never carry a headline number from prose — recompute it.
- **`get_total_utilities()` returns three fields per carrier and only one is energy.** `consumed` is the physical quantity, `cost` is $/yr, `output_avg_cost` is $/t LCE. Reading `cost` or `output_avg_cost` as energy divides every figure by the facility's `elec_price` and the error is uniform, so per-unit intensities look self-consistent and nothing flags. This produced a false SP electricity record on 2026-08-25 — 3,395,635.23 "kWh/yr" and 565.9392 "kWh/t LCE" against the true 37,729,280.3596 kWh/yr and 6,288.213393 kWh/t LCE, a clean 1/0.09 factor throughout. Quote `consumed`, and state the unit next to any number pulled from this accessor.
- **Restricted ranges are ranked per metric.** The cost bracket comes from `run_topn_scenarios(top_n=3, metric="avg_opex")`, the emissions bracket from the same call with `metric="avg_co2"`. An unqualified call silently uses the opex ranking for both. Tornado `top_n=5` is display-only, slicing an already-complete tornado, and is independent of `top_n_range`.
- Impact plots are emitted in **kg/t**; the t CO₂eq/t axis on published figures is a hand relabel.
- Figures are emitted as separate `-Steps-Cost` / `-Steps-Emissions` and `-Sensitivity-Cost` / `-Sensitivity-Emissions` files. The two-panel figures in `main.tex` are assembled by hand, including panel titles, row annotations and legends — the code writes none of those, so a regenerated figure needs every annotation re-checked against the run, not just the bars.
- `Transport` is its own cost series in `_build_steps_cost_series` at `view="opex"`; transport records carry no `material_costs` / `labor_costs` / `utility_costs` decomposition, so without it the hauling bar reads zero and the plotted bars under-sum `avg_opex`. Per-step plots pass no `colors` and take matplotlib's default cycle; `cost_colors` in the aggregated plotters is pinned to the same seven hexes so both views agree. Hand-built legends need a `Transportation` entry.
- The condensed 7-row aggregated views (`plot=2.1` Thacker Pass, `plot=2.2` Jianxiawo) exist for talks, not the manuscript. Any new flowsheet step must be added to the corresponding group table or `_aggregate_step_series` raises.
- **The `lime` material key is CaO-basis everywhere.** Any dose written on a `Ca(OH)2` mass must be converted at `M_CaO/M_CaOH2` = 0.756856, and any formula converting a lime dose to the calcium it releases divides by `M_CaO`, not `M_CaOH2`. Silver Peak buys quicklime and slakes on site — `batch_treatment_generic` carries a detention slaker and milk-of-lime storage in its bill of equipment — and no step in the workbook purchases hydrated lime, so a `slaked_lime` key is wrong everywhere. Thacker Pass is not known to slake on site; do not assert it.
- **Material keys are case-sensitive.** `Lime` against `lime` raises `KeyError` in `production_step.py` at facility construction, before any scenario pass, and takes the whole project down with no partial result to notice. Same for every other reagent, sink and utility key.
- **`Brine-Solvent Extraction-Boron` is outdated. Do not touch it and do not propose edits to it.** Its `C24` / `C26` carry a known hydroxide-basis defect and a stale `74.093` literal; both are recorded in `handoff_open_items.md` B2b precisely so they are not rediscovered and re-proposed.
- **Figure assembly is outside `run_all`.** `main.tex` includes `04-{project}-Steps-Summary.png`, `04-{project}-Sensitivity.png`, `04-costemissions.png` and `c-fullres.png`. Not one is an emitted filename: `run_all` writes `-Steps-Cost` / `-Steps-Emissions` / `-Sensitivity-Cost` / `-Sensitivity-Emissions` as inputs to a hand-assembly step, and the last two have no builder at all. A headline move invalidates the composites even though the run "succeeded".
- pandas ≥3 requires `.astype(object)` on the `read_csv` in `write_project_outputs_to_csv`; the cost row writes a formatted string and the emissions row a float into the same column, which 3.x rejects on a `str`-typed column.

Gate frozen 2026-08-26 on the uploaded `.py` set and workbook, after the lime basis and factor
work: `Brine-Batch Chemical Purificati` `C28` = `=M_CaO/M_Mg*1.2`, `C40` = `=C34*C28*M_Ca/M_CaO`,
`Material Data` `C9` = 1.16, `Project-Specific Data` rows 85/86/87 = 1.25 / 1.16 / 1.04.
`check_workbook_formula_cache` EMPTY, zero `CLIP` warnings.
`avg_opex` mid / cons / opt, then `avg_co2` t/t:
SP 5520.169638 / 6897.493066 / 4372.541050 and 6.012022 / 7.322982 / 4.672126;
TP 8703.225450 / 15171.822971 / 6214.320050 and 16.671457 / 20.497888 / 12.718477;
JX 12139.543867 / 15621.527521 / 10136.084322 and 30.257634 / 42.772066 / 22.808115.
SP conservative is 6897.4930655233, a knife-edge at six decimals — it will print as either
6897.493065 or 6897.493066 depending on rounding. Compare at ten decimals before calling a drift.
Every SP figure recorded before 2026-08-26 is superseded; do not quote 5584.265379 or 5585.498705.
Not landed but measured: unrounding `brine_pump` `electricity_base_total` from 117 / 108 / 99 to
the exact 115.65149 / 106.75522 / 97.85895 moves SP `avg_opex` −6.370033 / −6.900861 / −5.839206
and `avg_co2` −0.022592 / −0.024475 / −0.020709. SP electricity on this stack:
37,729,280.3596 kWh/yr = 6,288.213393 kWh/t LCE, `brine_pump` 1.500000 kWh/m^3 raw brine and
97.657% of the total, `evaporation_pond` zero. `Project-Specific Data` `K107` = 13.3 is unusable as
a benchmark — its unit string reads `Mmw/h total (?)`.
Top-3 brackets, ranked per metric:
SP [4469.990682 - 6775.830260] and [4.697869 - 7.291314];
TP [7064.628135 - 13903.394181] and [13.540477 - 19.417922];
JX [11187.278086 - 13887.682838] and [24.479302 - 40.356116].
JX hazardous-waste non-compliance, midpoint: `avg_opex` 11672.702543, delta −466.841324 $/t.
Tornado rankings measured on this stack for all three projects; TP emissions is led by `sulfur`
2343.4784, not `lime` 2084.0432. Sink unit costs, tailings tonnages and reagent intensities are as
recorded, not re-measured.

### Verification gate for plot-builder edits

Any change to `_build_steps_cost_series` or `_build_steps_impact_series` ships with three checks in the same message:

1. `avg_opex` and `avg_co2` reproduce bit-identically for all three projects across all three scenarios — 9/9 and 9/9.
2. `sum(plotted)` equals `avg_co2` exactly, summing every bar across every scope. The impact builder debits sink emissions from the routing step and credits them to the sink row; this equality is the only check that catches a double-count when the debit and credit fall out of step.
3. The two builders return identical label lists for every project.

A builder edit without all three is a HYPOTHESIS, not a landed change.

### Verification gate for parameter-effect claims

No claim about the effect of a parameter change ships without the run in the same message. A structural inference about model behaviour is a HYPOTHESIS and carries no number in a results table.

The 2026-08-12 session produced four retractions of one shape: predicting a re-solve without first establishing the solve order. Establish which quantities are pinned and which are back-solved (see "The leach basis is pinned downstream" above), then run, then claim.

---

## How to Proceed

I will name the block and provide my notes and raw numbers per session. Cross-check every value before including it in the writeup, show your working, and flag anything that cannot be independently corroborated.

**File authority, session opening, verification verdicts, and execution approval are governed by the project instructions.** Do not act on `/mnt/project/` copies without the staleness warning required there; anchor all findings on content, never line numbers.

### Response shape for landing checks

When asked whether edits landed:

- **All landed** — confirm in one or two lines with the verification run's headline figures. Nothing else.
- **Some outstanding** — a table of the outstanding items only: file, content anchor, required change. No commentary on what did land.
- **Landed differently in a way that changes a result** — this is the only case that gets prose, and only the mechanism and its size.

### Re-upload accounting for proposed edits

When I propose edits to a file and you tell me some or all landed, the files you re-upload are the
only evidence. If a file I proposed edits to is not re-uploaded in that message, do not re-derive
it, do not re-run the model, and do not assume the edits are absent. Reply with one line naming the
missing files — `not all files I proposed edits to were re-uploaded: <names>` — and nothing else. Do
not restate the pending edits, re-verify the files that were uploaded, or begin any other work in
that message.

Never propose reverting a landed value to one measured against a file version I have not uploaded in
the current message. Two bad revert suggestions in the 2026-08-23 session came from exactly that.

Override: if my message says explicitly that I do not want to re-upload, or names the state to
assume, act on that statement without asking again. Record which file states you are assuming in the
echo-back, and treat every claim resting on an unuploaded file as HYPOTHESIS for the rest of the
session.

### Close-out protocol

When I call for a close-out (CLOSE OUT), do not write the closure record first. Verify, then write, in this order:

1. **Re-verify every edit claimed in the session against the uploaded files.** An edit I said I made is a hypothesis until it is read back out of the file. Re-run the model and compare to the session's opening figures. If a claimed edit is not present, or the files predate it, say so and stop — do not close on described-but-unuploaded work.
2. **Close only if everything has landed.** If anything is outstanding, tag the cluster `[?]`, name the single blocking edit with its exact replacement text, and do not use CLOSED or CONFIRMED anywhere in the record.
3. **Only if step 2 closed the cluster, propose edits** to `handoff_open_items.md` and `continuation_prompt.md`. If anything is outstanding, propose nothing and STOP at the `[?]` tag: strike what resolved, record what deferred with its owner, and add any dependency the session discovered. Apply on my approval; show the hunk count and the changed line ranges.
4. **Report back a CHANGED and UNCHANGED pair**, in the shape of my session header, but keep it **very succinct**. CHANGED: file tags before and after, the specific cells, lines and constants that moved, and every headline figure that moved with its delta. UNCHANGED: file tags that did not move, the figures that are bit-identical and the gate that proves no edit leaked cross-project, and the defects still standing that a reader might otherwise assume were fixed. UNCHANGED matters as much as CHANGED — it is what the next session's opening header is checked against.
