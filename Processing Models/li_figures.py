import os
import numpy as np
import matplotlib.pyplot as plt

from transportation import Transportation
from scenarios import update_machines, update_materials
from plotting import plot_stacked_bars, plot_scenario_step_costs, plot_scenario_step_impacts, _aggregate_step_series
from config import COST_SERIES_COLORS, SCOPE_COLORS, TORNADO_COLORS, FAC_SLOTS, WASTE_GROUP, SINK_SLOTS, SLOT_KEYS

# ---------------------------------------------------------------------------
# Thacker Pass presentation aggregation
# ---------------------------------------------------------------------------

# Canonical step-group mapping.
# Each entry: (display_label, [step_names_to_aggregate]).
# Step names must match the labels produced by _build_steps_cost_series and
# _build_steps_impact_series (i.e. step.step_name / transport.name / normalised
# sink names "Waste Rock Pile", "Tailings Management" and "Wastewater Treatment").
# Both "Hauling" and "Ore transport via truck" are included so the mapping
# is robust regardless of which name the transport leg uses.
_THACKER_PASS_GROUPS = [
	("Blast mining &\ntransport",
		["Blasting with drilling and explosives", "Loading with excavator", "Hauling",
		 "Ore transport via truck"]),
	("Acid leaching",
		["Acid Leaching"]),
	("Impurity removal",
		["Impurity Removal"]),
	("Other leach\nsolution steps",
		["Crushing", "Attrition Scrubbing", "Classification", "Thickening",
		 "Neutralization", "Counter-Current Decantation and Thickening"]),
	("Li\u2082CO\u2083\nprecipitation",
		["Soda ash precipitation (Li2CO3)"]),
	("Other Li\u2082CO\u2083\nproduction steps",
		["Thickening and dewatering", "Washing & purification", "Drying & packaging"]),
	("Tailings &\nwater management",
		["Waste Rock Pile", "Tailings Management", "Wastewater Treatment"]),
	("On-site acid\nplant",
		["Sulfur burning", "Acid absorption"]),
]

def thacker_pass_steps_aggregated(
	sc,
	pathway_data,
	apv,
	*,
	view="opex",
	impact="co2",
	mode="average",
	transp=True,
	groups=None,
	title_cost=None,
	title_emissions=None,
	ylab_cost=None,
	ylab_emissions=None,
	show_legend=False,
	wrap_width=18,
	ylims_cost=None,
	xticks_cost=None,
	ylims_emissions=None,
	xticks_emissions=None,
	cost_colors=None,
	imp_colors=None,
):
	"""
	Plot Thacker Pass costs and emissions with steps aggregated into
	presentation-friendly groups, with asymmetric scenario error bars.

	Mirrors plot_scenario_step_costs / plot_scenario_step_impacts but
	collapses the full step list into the seven groups defined in
	_THACKER_PASS_GROUPS (or a caller-supplied override via ``groups``).
	Both cost and emissions plots are produced in sequence.

	Parameters
	----------
	sc           : SupplyChain  (facilities already built via evaluate_pathway)
	pathway_data : dict
	apv          : float        annual production volume (kg Li2CO3)
	view         : str          cost view for _build_steps_cost_series (default "opex")
	impact       : str          impact category key (default "co2")
	mode         : str          "average" | "total"
	transp       : bool         include transport steps
	groups       : list | None  override _THACKER_PASS_GROUPS if supplied
	show_legend  : bool
	wrap_width   : int          y-axis label wrap width (chars)
	"""
	import numpy as np

	if groups is None:
		groups = _THACKER_PASS_GROUPS

	mode = str(mode).lower().strip()
	if mode not in {"total", "average"}:
		raise ValueError("mode must be 'total' or 'average'")
	if mode == "average" and not apv:
		raise ValueError("apv is zero; cannot compute average costs/impacts.")

	def _row_totals(series_dict):
		"""Sum all series keys element-wise → 1-D total array."""
		n = len(next(iter(series_dict.values())))
		totals = np.zeros(n)
		for vals in series_dict.values():
			totals += np.asarray(vals, dtype=float)
		return totals

	# ------------------------------------------------------------------
	# Conservative scenario
	# ------------------------------------------------------------------
	update_machines(sc, "conservative")
	update_materials(sc, pathway_data, "conservative")
	sc.update_apv(apv, recalc=True)

	con_labels, con_cost_raw, _ = sc._build_steps_cost_series(
		view=view, detail=2, transp=transp, top_n=None)
	_, con_imp_raw, _ = sc._build_steps_impact_series(
		impact=impact, transp=transp)

	_, con_cost_agg = _aggregate_step_series(con_labels, con_cost_raw, groups)
	_, con_imp_agg  = _aggregate_step_series(con_labels, con_imp_raw,  groups)
	con_cost_totals = _row_totals(con_cost_agg)
	con_imp_totals  = _row_totals(con_imp_agg)

	# ------------------------------------------------------------------
	# Optimistic scenario
	# ------------------------------------------------------------------
	update_machines(sc, "optimistic")
	update_materials(sc, pathway_data, "optimistic")
	sc.update_apv(apv, recalc=True)

	opt_labels, opt_cost_raw, _ = sc._build_steps_cost_series(
		view=view, detail=2, transp=transp, top_n=None)
	_, opt_imp_raw, _ = sc._build_steps_impact_series(
		impact=impact, transp=transp)

	_, opt_cost_agg = _aggregate_step_series(opt_labels, opt_cost_raw, groups)
	_, opt_imp_agg  = _aggregate_step_series(opt_labels, opt_imp_raw,  groups)
	opt_cost_totals = _row_totals(opt_cost_agg)
	opt_imp_totals  = _row_totals(opt_imp_agg)

	# ------------------------------------------------------------------
	# Midpoint scenario  (defines bar values and stack order)
	# ------------------------------------------------------------------
	update_machines(sc, "midpoint")
	update_materials(sc, pathway_data, "midpoint")
	sc.update_apv(apv, recalc=True)

	mid_labels, mid_cost_raw, cost_stack_order = sc._build_steps_cost_series(
		view=view, detail=2, transp=transp, top_n=None)
	_, mid_imp_raw, imp_stack_order = sc._build_steps_impact_series(
		impact=impact, transp=transp)

	agg_labels, mid_cost_agg = _aggregate_step_series(mid_labels, mid_cost_raw, groups)
	_,           mid_imp_agg  = _aggregate_step_series(mid_labels, mid_imp_raw,  groups)
	mid_cost_totals = _row_totals(mid_cost_agg)
	mid_imp_totals  = _row_totals(mid_imp_agg)

	# Sanity-check that all three runs produced identical raw label sets
	if con_labels != mid_labels or opt_labels != mid_labels:
		raise ValueError(
			"Step label mismatch across scenarios — check that conservative, "
			"midpoint, and optimistic runs all produce the same step ordering.")

	# ------------------------------------------------------------------
	# Asymmetric error bars
	#   cost:      conservative (higher) → upward;  optimistic (lower) → downward
	#   emissions: same convention
	# ------------------------------------------------------------------
	cost_err_low  = np.maximum(mid_cost_totals - opt_cost_totals, 0.0)
	cost_err_high = np.maximum(con_cost_totals - mid_cost_totals, 0.0)
	imp_err_low   = np.maximum(mid_imp_totals  - opt_imp_totals,  0.0)
	imp_err_high  = np.maximum(con_imp_totals  - mid_imp_totals,  0.0)

	# ------------------------------------------------------------------
	# Per-unit scaling
	# ------------------------------------------------------------------
	divisor = float(apv) if mode == "average" else 1.0
	mid_cost_agg = {k: [v / divisor for v in vals]
					for k, vals in mid_cost_agg.items()}
	mid_imp_agg  = {k: [v / divisor for v in vals]
					for k, vals in mid_imp_agg.items()}
	cost_err_low  /= divisor;  cost_err_high /= divisor
	imp_err_low   /= divisor;  imp_err_high  /= divisor

	# ------------------------------------------------------------------
	# Prune stack_order to series that actually exist after aggregation
	# and carry at least one non-zero value
	# ------------------------------------------------------------------
	cost_stack_order = [
		k for k in cost_stack_order
		if k in mid_cost_agg and any(v != 0.0 for v in mid_cost_agg[k])
	]
	imp_stack_order = [
		k for k in imp_stack_order
		if k in mid_imp_agg and any(v != 0.0 for v in mid_imp_agg[k])
	]

	# ------------------------------------------------------------------
	# Default axis labels
	# ------------------------------------------------------------------
	if title_cost is None:
		title_cost = (
			"Average cost per tonne Li\u2082CO\u2083 — Thacker Pass"
			if mode == "average" else
			"Total cost — Thacker Pass"
		)
	if title_emissions is None:
		title_emissions = (
			f"Average {impact.upper()} impact per tonne Li\u2082CO\u2083 — Thacker Pass"
			if mode == "average" else
			f"Total {impact.upper()} impact — Thacker Pass"
		)
	if ylab_cost is None:
		ylab_cost = (
			"Average cost ($/t Li\u2082CO\u2083)"
			if mode == "average" else "Total cost ($)"
		)
	if ylab_emissions is None:
		ylab_emissions = (
			f"Average {impact.upper()} (kg/t Li\u2082CO\u2083)"
			if mode == "average" else f"Total {impact.upper()} (kg)"
		)

	# ------------------------------------------------------------------
	# Plot 1: costs
	# ------------------------------------------------------------------
	plot_stacked_bars(
		agg_labels, mid_cost_agg,
		stack_order=cost_stack_order,
		colors=cost_colors,
		title=title_cost,
		ylab=ylab_cost,
		err_low=cost_err_low,
		err_high=cost_err_high,
		show_legend=show_legend,
		wrap_width=wrap_width,
		ylims=ylims_cost,
		xticks=xticks_cost,
	)

	# ------------------------------------------------------------------
	# Plot 2: emissions
	# ------------------------------------------------------------------
	plot_stacked_bars(
		agg_labels, mid_imp_agg,
		stack_order=imp_stack_order,
		colors=imp_colors,
		title=title_emissions,
		ylab=ylab_emissions,
		err_low=imp_err_low,
		err_high=imp_err_high,
		show_legend=show_legend,
		wrap_width=wrap_width,
		ylims=ylims_emissions,
		xticks=xticks_emissions,
	)

# ---------------------------------------------------------------------------
# Jianxiawo presentation aggregation
# ---------------------------------------------------------------------------

_JIANXIAWO_GROUPS = [
	("Blast mining &\ntransport",
		["Blasting with drilling and explosives", "Loading with excavator", "Hauling",
		 "Ore transport via truck"]),
	("Classification\n& flotation",
		["Classification", "Froth Flotation circuit", "Thickening"]),
	("Sulfate roasting",
		["Roasting of lepidolate with sulfate salts"]),
	("Other roast-leach\nsteps",
		["Crushing", "Grinding via mill", "Dewatering to allow for high-temp roasting",
		 "Water leaching", "Impurity Removal", "Lithium Stream Clarification"]),
	("Li\u2082CO\u2083\nprecipitation",
		["Soda ash precipitation (Li2CO3)"]),
	("Other Li\u2082CO\u2083\nproduction steps",
		["Thickening and dewatering", "Washing & purification", "Drying & packaging"]),
	("Tailings &\nwater management",
		["Waste Rock Pile", "Tailings Management", "Wastewater Treatment"]),
]

def jianxiawo_steps_aggregated(
	sc,
	pathway_data,
	apv,
	*,
	view="opex",
	impact="co2",
	mode="average",
	transp=True,
	groups=None,
	title_cost=None,
	title_emissions=None,
	ylab_cost=None,
	ylab_emissions=None,
	show_legend=False,
	wrap_width=18,
	ylims_cost=None,
	xticks_cost=None,
	ylims_emissions=None,
	xticks_emissions=None,
	cost_colors=None,
	imp_colors=None,
):
	"""
	Plot Jianxiawo costs and emissions with steps aggregated into
	presentation-friendly groups, with asymmetric scenario error bars.

	Mirrors thacker_pass_steps_aggregated but uses _JIANXIAWO_GROUPS,
	which separates Classification & Flotation as its own row to highlight
	the pathway-specific beneficiation burden of low-grade lepidolite ore.

	Parameters
	----------
	sc           : SupplyChain  (facilities already built via evaluate_pathway)
	pathway_data : dict
	apv          : float        annual production volume (kg Li2CO3)
	view         : str          cost view for _build_steps_cost_series (default "opex")
	impact       : str          impact category key (default "co2")
	mode         : str          "average" | "total"
	transp       : bool         include transport steps
	groups       : list | None  override _JIANXIAWO_GROUPS if supplied
	show_legend  : bool
	wrap_width   : int          y-axis label wrap width (chars)
	"""
	import numpy as np

	if groups is None:
		groups = _JIANXIAWO_GROUPS

	mode = str(mode).lower().strip()
	if mode not in {"total", "average"}:
		raise ValueError("mode must be 'total' or 'average'")
	if mode == "average" and not apv:
		raise ValueError("apv is zero; cannot compute average costs/impacts.")

	def _row_totals(series_dict):
		n = len(next(iter(series_dict.values())))
		totals = np.zeros(n)
		for vals in series_dict.values():
			totals += np.asarray(vals, dtype=float)
		return totals

	# ------------------------------------------------------------------
	# Conservative scenario
	# ------------------------------------------------------------------
	update_machines(sc, "conservative")
	update_materials(sc, pathway_data, "conservative")
	sc.update_apv(apv, recalc=True)

	con_labels, con_cost_raw, _ = sc._build_steps_cost_series(
		view=view, detail=2, transp=transp, top_n=None)
	_, con_imp_raw, _ = sc._build_steps_impact_series(
		impact=impact, transp=transp)

	_, con_cost_agg = _aggregate_step_series(con_labels, con_cost_raw, groups)
	_, con_imp_agg  = _aggregate_step_series(con_labels, con_imp_raw,  groups)
	con_cost_totals = _row_totals(con_cost_agg)
	con_imp_totals  = _row_totals(con_imp_agg)

	# ------------------------------------------------------------------
	# Optimistic scenario
	# ------------------------------------------------------------------
	update_machines(sc, "optimistic")
	update_materials(sc, pathway_data, "optimistic")
	sc.update_apv(apv, recalc=True)

	opt_labels, opt_cost_raw, _ = sc._build_steps_cost_series(
		view=view, detail=2, transp=transp, top_n=None)
	_, opt_imp_raw, _ = sc._build_steps_impact_series(
		impact=impact, transp=transp)

	_, opt_cost_agg = _aggregate_step_series(opt_labels, opt_cost_raw, groups)
	_, opt_imp_agg  = _aggregate_step_series(opt_labels, opt_imp_raw,  groups)
	opt_cost_totals = _row_totals(opt_cost_agg)
	opt_imp_totals  = _row_totals(opt_imp_agg)

	# ------------------------------------------------------------------
	# Midpoint scenario
	# ------------------------------------------------------------------
	update_machines(sc, "midpoint")
	update_materials(sc, pathway_data, "midpoint")
	sc.update_apv(apv, recalc=True)

	mid_labels, mid_cost_raw, cost_stack_order = sc._build_steps_cost_series(
		view=view, detail=2, transp=transp, top_n=None)
	_, mid_imp_raw, imp_stack_order = sc._build_steps_impact_series(
		impact=impact, transp=transp)

	agg_labels, mid_cost_agg = _aggregate_step_series(mid_labels, mid_cost_raw, groups)
	_,           mid_imp_agg  = _aggregate_step_series(mid_labels, mid_imp_raw,  groups)
	mid_cost_totals = _row_totals(mid_cost_agg)
	mid_imp_totals  = _row_totals(mid_imp_agg)

	if con_labels != mid_labels or opt_labels != mid_labels:
		raise ValueError(
			"Step label mismatch across scenarios — check that conservative, "
			"midpoint, and optimistic runs all produce the same step ordering.")

	# ------------------------------------------------------------------
	# Asymmetric error bars
	# ------------------------------------------------------------------
	cost_err_low  = np.maximum(mid_cost_totals - opt_cost_totals, 0.0)
	cost_err_high = np.maximum(con_cost_totals - mid_cost_totals, 0.0)
	imp_err_low   = np.maximum(mid_imp_totals  - opt_imp_totals,  0.0)
	imp_err_high  = np.maximum(con_imp_totals  - mid_imp_totals,  0.0)

	# ------------------------------------------------------------------
	# Per-unit scaling
	# ------------------------------------------------------------------
	divisor = float(apv) if mode == "average" else 1.0
	mid_cost_agg = {k: [v / divisor for v in vals]
					for k, vals in mid_cost_agg.items()}
	mid_imp_agg  = {k: [v / divisor for v in vals]
					for k, vals in mid_imp_agg.items()}
	cost_err_low  /= divisor;  cost_err_high /= divisor
	imp_err_low   /= divisor;  imp_err_high  /= divisor

	# ------------------------------------------------------------------
	# Prune stack_order to series present and non-zero after aggregation
	# ------------------------------------------------------------------
	cost_stack_order = [
		k for k in cost_stack_order
		if k in mid_cost_agg and any(v != 0.0 for v in mid_cost_agg[k])
	]
	imp_stack_order = [
		k for k in imp_stack_order
		if k in mid_imp_agg and any(v != 0.0 for v in mid_imp_agg[k])
	]

	# ------------------------------------------------------------------
	# Default axis labels
	# ------------------------------------------------------------------
	if title_cost is None:
		title_cost = (
			"Average cost per tonne Li\u2082CO\u2083 — Jianxiawo"
			if mode == "average" else
			"Total cost — Jianxiawo"
		)
	if title_emissions is None:
		title_emissions = (
			f"Average {impact.upper()} impact per tonne Li\u2082CO\u2083 — Jianxiawo"
			if mode == "average" else
			f"Total {impact.upper()} impact — Jianxiawo"
		)
	if ylab_cost is None:
		ylab_cost = (
			"Average cost ($/t Li\u2082CO\u2083)"
			if mode == "average" else "Total cost ($)"
		)
	if ylab_emissions is None:
		ylab_emissions = (
			f"Average {impact.upper()} (kg/t Li\u2082CO\u2083)"
			if mode == "average" else f"Total {impact.upper()} (kg)"
		)

	# ------------------------------------------------------------------
	# Plot 1: costs
	# ------------------------------------------------------------------
	plot_stacked_bars(
		agg_labels, mid_cost_agg,
		stack_order=cost_stack_order,
		colors=cost_colors,
		title=title_cost,
		ylab=ylab_cost,
		err_low=cost_err_low,
		err_high=cost_err_high,
		show_legend=show_legend,
		wrap_width=wrap_width,
		ylims=ylims_cost,
		xticks=xticks_cost,
	)

	# ------------------------------------------------------------------
	# Plot 2: emissions
	# ------------------------------------------------------------------
	plot_stacked_bars(
		agg_labels, mid_imp_agg,
		stack_order=imp_stack_order,
		colors=imp_colors,
		title=title_emissions,
		ylab=ylab_emissions,
		err_low=imp_err_low,
		err_high=imp_err_high,
		show_legend=show_legend,
		wrap_width=wrap_width,
		ylims=ylims_emissions,
		xticks=xticks_emissions,
	)

def _value_axis_extent(ax):
	import numpy as np
	hi = float(ax.dataLim.intervalx[1])
	for coll in ax.collections:
		get_segs = getattr(coll,"get_segments",None)
		if get_segs is None:
			continue
		for seg in get_segs():
			seg = np.asarray(seg,dtype=float)
			if seg.size:
				hi = max(hi,float(np.max(seg[:,0])))
	return hi, float(ax.get_xlim()[1])

def _save_open_figures(paths):
	import matplotlib.pyplot as plt
	nums = plt.get_fignums()
	if len(nums) != len(paths):
		raise RuntimeError(f"open figures {len(nums)} != expected {len(paths)}: {[os.path.basename(p) for p in paths]}")
	for num,path in zip(nums,paths):
		fig = plt.figure(num)
		os.makedirs(os.path.dirname(path),exist_ok=True)
		for ax in fig.get_axes():
			data_hi,axis_hi = _value_axis_extent(ax)
			if data_hi > axis_hi*(1+1e-9):
				print(f"CLIP  {os.path.basename(path)}: data extent {data_hi:,.4f} exceeds axis limit {axis_hi:,.4f}")
		fig.savefig(path,dpi=300,bbox_inches="tight")
	plt.close("all")

def _step_summary_figures(pathway,sc,pathway_data,apv,axes,fig_dir,suffix):
	plot_scenario_step_costs(sc,pathway_data,apv,view="opex",mode="average",detail=2,transp=True,
		ylims=axes["ylims_cost"],xticks=axes["xticks_cost"],colors=COST_SERIES_COLORS)
	plot_scenario_step_impacts(sc,pathway_data,apv,mode="average",impact="co2",
		ylims=axes["ylims_emissions"],xticks=axes["xticks_emissions"],colors=SCOPE_COLORS)
	_save_open_figures([
		os.path.join(fig_dir,f"04-{pathway}-Steps-Cost{suffix}.png"),
		os.path.join(fig_dir,f"04-{pathway}-Steps-Emissions{suffix}.png"),
	])

def _slot_name(pathway_data, slot):
	return pathway_data[slot] if slot in SLOT_KEYS else slot

def _facility_index(sc, pathway_data, labels):
	nodes = sc.get_steps(transp=True)
	groups = []
	for i, node in enumerate(nodes):
		if isinstance(node, Transportation):
			name, grp = node.name, pathway_data["Facility 1"]
		else:
			fac_id = node.facility.fac_id
			name, grp = node.step_name, _slot_name(pathway_data, FAC_SLOTS.get(fac_id, fac_id))
		got = labels[i] if i < len(labels) else None
		if got != name:
			raise ValueError(f"Label {i}: expected '{name}', got '{got}'")
		groups.append(grp)
	for lbl in labels[len(nodes):]:
		if lbl not in SINK_SLOTS:
			raise ValueError(f"Unmapped sink label '{lbl}'")
		groups.append(_slot_name(pathway_data, SINK_SLOTS[lbl]))
	head = [pathway_data[k] for k in SLOT_KEYS if pathway_data.get(k)]
	tail = [g for g in dict.fromkeys(groups) if g not in head and g != WASTE_GROUP]
	order = [g for g in head + tail + [WASTE_GROUP] if g in groups]
	return groups, order

def _aggregate_by_facility(groups, order, series):
	import numpy as np
	pos = {g: i for i, g in enumerate(order)}
	out = {k: np.zeros(len(order)) for k in series}
	for k, vals in series.items():
		for g, v in zip(groups, vals):
			out[k][pos[g]] += float(v)
	return out

def facility_panel_data(sc, pathway_data, apv, *, view="opex", impact="co2", co2_scale=1.0, fold_transport=False):
	import numpy as np
	runs = {}
	for rank in ("conservative", "optimistic", "midpoint"):
		update_machines(sc, rank)
		update_materials(sc, pathway_data, rank)
		sc.update_apv(apv, recalc=True)
		runs[rank] = {
			"cost": sc._build_steps_cost_series(view=view, detail=2, transp=True, top_n=None),
			"co2":  sc._build_steps_impact_series(impact=impact, transp=True),
		}
	out = {}
	for kind, scale in (("cost", 1.0), ("co2", co2_scale)):
		mid_labels, _, mid_stack = runs["midpoint"][kind]
		for rank in ("conservative", "optimistic"):
			if runs[rank][kind][0] != mid_labels:
				raise ValueError(f"{kind}: step label mismatch between {rank} and midpoint")
		groups, order = _facility_index(sc, pathway_data, mid_labels)
		agg = {rank: _aggregate_by_facility(groups, order, runs[rank][kind][1]) for rank in runs}
		if kind == "cost" and fold_transport:
			for rank in agg:
				if "Transport" in agg[rank]:
					agg[rank]["Other"] = agg[rank].get("Other", 0.0) + agg[rank].pop("Transport")
		tot = {rank: sum(agg[rank].values()) for rank in agg}
		div = float(apv) / scale
		series = {k: v / div for k, v in agg["midpoint"].items()}
		out[kind] = {
			"labels":   order,
			"series":   series,
			"stack":    [k for k in mid_stack if k in series and np.any(series[k] != 0.0)],
			"err_low":  np.maximum(tot["midpoint"] - tot["optimistic"], 0.0) / div,
			"err_high": np.maximum(tot["conservative"] - tot["midpoint"], 0.0) / div,
		}
	return out

def tornado_entries(tornado, metric, top_n):
	entries = []
	for kind, prefix in (("machines", "Machine"), ("materials", "Material")):
		for name, vals in tornado.get(kind, {}).items():
			entries.append((f"{prefix}: {name}", vals["optimistic"][metric], vals["conservative"][metric]))
	entries.sort(key=lambda e: abs(e[2] - e[1]), reverse=True)
	return entries[:top_n]

def _bar_extent(d):
	import numpy as np
	vals = np.array(list(d["series"].values()))
	net = vals.sum(axis=0)
	hi = max(np.maximum(vals, 0.0).sum(axis=0).max(), (net + d["err_high"]).max())
	lo = min(0.0, (net - d["err_low"]).min())
	return lo, hi

def _pad(lo, hi, margin):
	span = hi - lo
	return (float(lo - span * margin if lo != 0 else lo), float(hi + span * margin))

def _finish_panel(fig, ax, width, row_height, rect, n_rows, ticklabels, path, dpi, fontsize):
	l, b, r, t = rect
	h = b + t + n_rows * row_height
	fig.set_size_inches(width, h)
	ax.set_position([l / width, b / h, 1 - (l + r) / width, 1 - (b + t) / h])
	ax.set_ylim(n_rows - 0.5, -0.5)
	ax.set_title("")
	ax.set_xlabel("")
	ax.set_ylabel("")
	ax.tick_params(axis="x", labelsize=fontsize)
	if not ticklabels:
		ax.set_yticklabels([])
	os.makedirs(os.path.dirname(path), exist_ok=True)
	fig.savefig(path, dpi=dpi, transparent=True)
	plt.close(fig)

def _plot_tornado_panel(entries, baseline, xlim, width, row_height, rect, ticklabels, path, dpi, scale, fontsize):
	fig, ax = plt.subplots(figsize=(width, 1.0))
	fig.patch.set_facecolor("none")
	ax.set_facecolor("none")
	y = np.arange(len(entries))
	b = baseline * scale
	opt = np.array([e[1] for e in entries]) * scale
	con = np.array([e[2] for e in entries]) * scale
	ax.barh(y, con - b, left=b, color=TORNADO_COLORS["conservative"], zorder=3)
	ax.barh(y, opt - b, left=b, color=TORNADO_COLORS["optimistic"], zorder=3)
	ax.axvline(b, color="black", linewidth=1.0, zorder=4)
	ax.set_yticks(y)
	ax.set_yticklabels([e[0] for e in entries], fontsize=fontsize)
	ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
	ax.set_xlim(xlim)
	_finish_panel(fig, ax, width, row_height, rect, len(entries), ticklabels, path, dpi, fontsize)

def _plot_combined_tornado(torn, bands, pathways, metric, scale, *, colors, styles, show_band, band_alpha,
	group_gap, xlim, xticks, margin, width, row_height, rect, path, dpi, fontsize):
	pos, y = {}, 0.0
	for p in pathways:
		n = len(torn[p][metric][1])
		pos[p] = [y + k for k in range(n)]
		y += n + group_gap
	extent = y - group_gap
 
	pts = [v * scale for p in pathways for v in [torn[p][metric][0]] + [x for e in torn[p][metric][1] for x in (e[1], e[2])]]
	if show_band:
		pts += [v * scale for p in pathways for v in bands[p][metric]]
	lim = tuple(xlim) if xlim is not None else _pad(min(pts), max(pts), margin)
 
	fig, ax = plt.subplots(figsize=(width, 1.0))
	fig.patch.set_facecolor("none")
	ax.set_facecolor("none")
	for p in pathways:
		clr = colors.get(p, "gray")
		b = torn[p][metric][0] * scale
		top, bot = pos[p][0] - 0.5, pos[p][-1] + 0.5
		if show_band:
			lo, hi = sorted(v * scale for v in bands[p][metric])
			ax.fill_betweenx([top, bot], lo, hi, color=clr, alpha=band_alpha, linewidth=0, zorder=1)
		for yk, (name, opt, con) in zip(pos[p], torn[p][metric][1]):
			ax.barh(yk, con * scale - b, left=b, height=0.8, color=clr, zorder=3, **styles["conservative"])
			ax.barh(yk, opt * scale - b, left=b, height=0.8, color=clr, zorder=3, **styles["optimistic"])
		ax.vlines(b, top, bot, color="black", linewidth=1.0, zorder=4)
	ax.set_yticks([])
	ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
	ax.set_xlim(lim)
	if xticks is not None:
		ax.set_xticks(list(xticks))
	_finish_panel(fig, ax, width, row_height, rect, extent, False, path, dpi, fontsize)
 
	print(f"\nCombined tornado {metric} (scale={scale}), x-limits {lim}")
	for p in pathways:
		b = torn[p][metric][0] * scale
		for k, (name, opt, con) in enumerate(torn[p][metric][1]):
			print(f"  {p:<13} rank {k + 1}  {name:<45} opt {opt * scale:,.1f}  mid {b:,.1f}  con {con * scale:,.1f}")
		if show_band:
			lo, hi = sorted(v * scale for v in bands[p][metric])
			print(f"  {p:<13} joint top-{len(torn[p][metric][1])} band  {lo:,.1f} - {hi:,.1f}")
	return lim

