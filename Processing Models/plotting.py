import textwrap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from scenarios import update_machines, update_materials


# PLOTTING HELPERS
def _wrap_labels(labels, width=14):
	tw = textwrap.TextWrapper(width=width,
							  break_long_words=False,   # don't cut words
							  break_on_hyphens=True)    # allow existing hyphens
	wrapped = []
	for s in map(str, labels):
		if '/' in s:
			parts = [p.strip() for p in s.split('/')]
			parts_wrapped = ['\n'.join(tw.wrap(p)) for p in parts]
			# keep the slash at the end of the line where the break occurs
			wrapped.append(' /\n'.join(parts_wrapped))
		else:
			wrapped.append('\n'.join(tw.wrap(s)))
	return wrapped

def cost_series_colors(series_keys, palette=None):
	keys = list(series_keys)
	if palette and keys and all(k in palette for k in keys):
		return palette
	return None

def plot_stacked_bars(labels, series_dict, *,
	stack_order=None,                 # list of series labels from bottom -> top
	colors=None,                      # dict like {"Fixed": "#f28e2b", "Variable": "#4e79a7"}
	xscale=1, yscale=1,
	title='Cost of Steps', xlab='Step Names', ylab='Total',
	xlims=None, ylims=None,
	xticks=None, 
	fixed_width=None, 
	base_width_per_bar=0.5,
	legend_order='top_to_bottom',     # 'top_to_bottom' or 'bottom_to_top'
	legend_loc='upper right',
	show_legend=False,                # show legend (default False)
	wrap_width=12,
	label_rotation=None,              # degrees; None = auto; ignored in horizontal mode
	label_fontsize=None,              # pt;      None = auto
	top_margin=0.08,                  # fractional whitespace beyond the tallest/widest bar
	err_low=None,                     # array-like len n; downward/leftward extent from bar tip
	err_high=None,                    # array-like len n; upward/rightward extent from bar tip
	orientation='horizontal',         # 'horizontal' | 'vertical'
	bar_thickness=0.8,                # bar height in horizontal mode (0.0–1.0; default 0.6)
	show=True,
	):
	"""
	labels       : sequence of category names
	series_dict  : {series_label: iterable of values}, all same length as labels
	stack_order  : explicit order bottom->top (vertical) / left->right (horizontal)
	orientation  : 'horizontal' (default) or 'vertical'
	"""
 
	labels = list(labels)
	n = len(labels)
	horiz = (str(orientation).lower().strip() == 'horizontal')
 
	# Validate and scale data
	data = {}
	for k, vals in series_dict.items():
		arr = np.asarray(vals, dtype=float)
		if arr.shape[0] != n:
			raise ValueError(f"Series '{k}' length {arr.shape[0]} != number of labels {n}.")
		data[k] = arr * yscale
 
	# Determine stacking order
	if stack_order is None:
		order = list(series_dict.keys())
	else:
		missing = set(series_dict.keys()) - set(stack_order)
		extra   = set(stack_order)   - set(series_dict.keys())
		if missing:
			raise ValueError(f"stack_order missing series: {sorted(missing)}")
		if extra:
			raise ValueError(f"stack_order has unknown series: {sorted(extra)}")
		order = list(stack_order)
 
	# Figure sizing
	if fixed_width is not None:
		fig_w = fixed_width
		fig_h = 6
	elif horiz:
		fig_w = 6
		fig_h = max(4,  n * bar_thickness * 0.6 + 0.8)
	else:
		fig_w = 2 * min(max(6, n * base_width_per_bar * max(xscale, 0.01)), 14)
		fig_h = 6
 
	fig, ax = plt.subplots(figsize=(fig_w, fig_h))
	fig.patch.set_facecolor('none')
	ax.set_facecolor('none')
 
	pos = np.arange(n)
 
	# Draw stacked bars - include negatives
	pos_run = np.zeros(n, dtype=float)
	neg_run = np.zeros(n, dtype=float)
	handle_map = {}
	for name in order:
		clr = (colors.get(name) if colors and name in colors else None)
		v = np.maximum(data[name], 0.0)
		if horiz:
			h = ax.barh(pos, v, left=pos_run, height=bar_thickness, label=name, color=clr)
		else:
			h = ax.bar(pos, v, bottom=pos_run, label=name, color=clr)
		handle_map[name] = h
		pos_run = pos_run + v

	credit_top = pos_run.copy()
	for name in order:
		v = np.minimum(data[name], 0.0)
		if not (v < 0.0).any():
			continue
		clr = (colors.get(name) if colors and name in colors else None)
		k = v < 0.0
		if horiz:
			ax.barh(pos[k], -v[k], left=(credit_top + v)[k], height=bar_thickness,
				facecolor='none', edgecolor=(clr or 'black'), hatch='///', linewidth=1.2, zorder=3)
		else:
			ax.bar(pos[k], -v[k], bottom=(credit_top + v)[k],
				facecolor='none', edgecolor=(clr or 'black'), hatch='///', linewidth=1.2, zorder=3)
		credit_top = credit_top + v
		neg_run = neg_run + v
	running = pos_run + neg_run

	signed = bool((neg_run < 0.0).any())
	if signed:
		m = neg_run < 0.0
		if horiz:
			ax.plot(running[m], pos[m], linestyle='none', marker='D', markersize=8,
				color='black', markeredgecolor='white', markeredgewidth=1.2, zorder=7)
		else:
			ax.plot(pos[m], running[m], linestyle='none', marker='D', markersize=8,
				color='black', markeredgecolor='white', markeredgewidth=1.2, zorder=7)

	# Error bars
	if err_low is not None or err_high is not None:
		_low  = np.asarray(err_low  if err_low  is not None else np.zeros(n), dtype=float) * yscale
		_high = np.asarray(err_high if err_high is not None else np.zeros(n), dtype=float) * yscale
		if horiz:
			ax.errorbar(running, pos, xerr=[_low, _high],
						fmt='none', color='black', capsize=4, linewidth=1.2, zorder=5)
		else:
			ax.errorbar(pos, running, yerr=[_low, _high],
						fmt='none', color='black', capsize=4, linewidth=1.2, zorder=5)
 
	# Tick labels
	if label_fontsize is None:
		fontsize = 9 if n <= 14 else (8 if n <= 20 else 7)
	else:
		fontsize = label_fontsize
 
	try:
		tick_labels = _wrap_labels(labels, width=wrap_width)
	except NameError:
		def _simple_wrap(s, width):
			return '\n'.join([s[i:i+width] for i in range(0, len(s), width)]) if len(s) > width else s
		tick_labels = [_simple_wrap(str(s), wrap_width) for s in labels]
 
	if horiz:
		# For horizontal bars: labels on y-axis, first label at top
		ax.set_yticks(pos)
		ax.set_yticklabels(tick_labels, ha='right', fontsize=fontsize)
		ax.invert_yaxis()
	else:
		# Auto rotation for vertical
		if label_rotation is None:
			rotation = 0 if n <= 10 else (40 if n <= 18 else 60)
		else:
			rotation = label_rotation
 
		if rotation == 0:
			effective_wrap = wrap_width
			ha = 'center'
		else:
			effective_wrap = max(wrap_width, 18)
			ha = 'right'
 
		try:
			tick_labels = _wrap_labels(labels, width=effective_wrap)
		except NameError:
			tick_labels = [_simple_wrap(str(s), effective_wrap) for s in labels]
 
		ax.set_xticks(pos)
		ax.set_xticklabels(tick_labels, ha=ha, rotation=rotation, fontsize=fontsize)
 
		if rotation > 0:
			fig.set_size_inches(fig.get_figwidth(), fig.get_figheight() + 1.5)
 
	# Axis labels and title
	# In horizontal mode xlab labels the category axis (y) and ylab labels the value axis (x)
	if horiz:
		ax.set_xlabel(ylab)
		ax.set_ylabel(xlab)
	else:
		ax.set_xlabel(xlab)
		ax.set_ylabel(ylab)
	ax.set_title(title, pad=12)
 
	# Grid on the value axis
	ax.grid(axis=('x' if horiz else 'y'), linestyle=':', alpha=0.4)
 
	# Limits — xlims/ylims always refer to the category/value axes as labelled by the caller,
	# so we swap them internally for horizontal mode.
	if horiz:
		if ylims is not None:
			ax.set_xlim(ylims)
		else:
			xmin, xmax = ax.get_xlim()
			lo = min(0.0, xmin) * (1 + top_margin)
			ax.set_xlim(lo, xmax * (1 + top_margin))
		if xlims is not None:
			ax.set_ylim(xlims)
	else:
		if xlims is not None:
			ax.set_xlim(xlims)
		if ylims is not None:
			ax.set_ylim(ylims)
		else:
			ymin, ymax = ax.get_ylim()
			lo = min(0.0, ymin) * (1 + top_margin)
			ax.set_ylim(lo, ymax * (1 + top_margin))

	if xticks is not None:
		ax.set_xticks(list(xticks))
 
	# Legend
	if show_legend:
		if legend_order not in ('top_to_bottom', 'bottom_to_top'):
			raise ValueError("legend_order must be 'top_to_bottom' or 'bottom_to_top'")
		legend_labels  = (order[::-1] if legend_order == 'top_to_bottom' else order)
		legend_handles = [handle_map[name] for name in legend_labels]
		ax.legend(
			legend_handles, legend_labels,
			frameon=True, loc=legend_loc, handlelength=1.2, handletextpad=0.4, borderpad=0.3,
			facecolor='white', edgecolor='none'
		)
 
	plt.tight_layout()

	# plt.savefig("output", dpi=300, bbox_inches="tight")
	if show:
		plt.show()
	return fig, ax

def plot_production_curve(apvs,avg_costs,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Unit Cost'):
	fig = plt.figure(figsize=(8, 6))
	plt.scatter(apvs, avg_costs, color='blue', label='Production Volume vs Cost')

	# Add labels and title
	plt.title(title, fontsize=14)
	plt.xlabel(xlab, fontsize=12)
	plt.ylabel(ylab, fontsize=12)
	plt.grid(True, linestyle='--', alpha=0.6)
	plt.legend()
	plt.tight_layout()

	# Display the plot
	plt.show()
	return fig

def plot_pathway_summaries(
	pathway_summaries: dict,
	*,
	x_key: str = "avg_var_cost",
	y_key: str = "avg_co2",
	size_key: str = "apv",
	center_scenario: str = "midpoint",
	low_scenario: str = "conservative",
	high_scenario: str = "optimistic",
	pathway_markers=None,
	size_range=(60, 500),   # scatter "s" (area) range
	alpha=0.85,
	edgecolor="black",
    ecolor="gray",
	elinewidth=1.2,
	capsize=3,
	capthick=1.2,
	reference_lines=None,
	annotate=True,
	ax=None,
	figsize=(10, 6),
):
	"""
	Plot nested pathway_summaries dict:
	  pathway_summaries[pathway][scenario][metric] -> value

	X: cost_key (default avg_cost)
	Y: co2_key  (default avg_co2)
	Size: size_key (default apv)
	Color: scenario
	Marker: pathway
	"""

	# ----------------------------
	# 1) Flatten to DataFrame
	# ----------------------------
	rows = []
	for pathway, scenarios in pathway_summaries.items():
		for scenario, metrics in scenarios.items():
			rows.append(
				{
					"pathway": pathway,
					"scenario": scenario,
					x_key: metrics.get(x_key, np.nan),
					y_key: metrics.get(y_key, np.nan),
					size_key: metrics.get(size_key, np.nan),
				}
			)
	df = pd.DataFrame(rows)

	# Keep only the 3 scenarios we need
	df = df[df["scenario"].isin([low_scenario, center_scenario, high_scenario])].copy()

	# Pivot so we have columns like (avg_cost, midpoint), etc.
	piv = df.pivot_table(index="pathway", columns="scenario", values=[x_key, y_key, size_key], aggfunc="first")

	# Helper to safely extract a series
	def col(metric, scenario):
		try:
			return piv[(metric, scenario)]
		except KeyError:
			return pd.Series(index=piv.index, dtype=float)

	x_c = col(x_key, center_scenario).astype(float)
	y_c = col(y_key, center_scenario).astype(float)

	x_lo = col(x_key, low_scenario).astype(float)
	x_hi = col(x_key, high_scenario).astype(float)
	y_lo = col(y_key, low_scenario).astype(float)
	y_hi = col(y_key, high_scenario).astype(float)

	s_c = col(size_key, center_scenario).astype(float)
	# If size missing at midpoint, fall back to any available size
	if s_c.isna().all():
		s_c = df[df["scenario"] == center_scenario].set_index("pathway")[size_key]
	if s_c.isna().any():
		s_any = (
			df.dropna(subset=[size_key])
			  .drop_duplicates(subset=["pathway"])
			  .set_index("pathway")[size_key]
		)
		s_c = s_c.fillna(s_any)

	# Drop pathway missing center x/y
	ok = x_c.notna() & y_c.notna()
	x_c, y_c, x_lo, x_hi, y_lo, y_hi, s_c = [v[ok] for v in (x_c, y_c, x_lo, x_hi, y_lo, y_hi, s_c)]

	pathways = x_c.index.tolist()

	# ----------------------------
	# 2) Markers and size scaling
	# ----------------------------
	if pathway_markers is None:
		marker_cycle = ["o", "s", "^", "D", "P", "X", "v", "<", ">", "h", "*"]
		pathway_markers = {p: marker_cycle[i % len(marker_cycle)] for i, p in enumerate(pathways)}

	def scale_sizes(values, out_min, out_max):
		v = np.asarray(values, dtype=float)
		finite = np.isfinite(v)
		if not finite.any():
			return np.full_like(v, (out_min + out_max) / 2.0)
		vmin = np.nanmin(v[finite])
		vmax = np.nanmax(v[finite])
		if np.isclose(vmin, vmax):
			return np.where(finite, (out_min + out_max) / 2.0, np.nan)
		return out_min + (v - vmin) * (out_max - out_min) / (vmax - vmin)

	sizes = scale_sizes(s_c.values, size_range[0], size_range[1])

	# ----------------------------
	# 3) Compute asymmetric errors (ensure non-negative)
	# ----------------------------
	# xerr = [[center-low], [high-center]]
	xerr_low = (x_c - x_lo).clip(lower=0).values
	xerr_high = (x_hi - x_c).clip(lower=0).values
	yerr_low = (y_c - y_lo).clip(lower=0).values
	yerr_high = (y_hi - y_c).clip(lower=0).values

	# ----------------------------
	# 4) Figure / axis
	# ----------------------------
	if ax is None:
		fig, ax = plt.subplots(figsize=figsize)
	else:
		fig = ax.figure

	# ----------------------------
	# 5) Plot: one errorbar per pathway (to allow per-pathway markers)
	# ----------------------------
	for i, pathway in enumerate(pathways):
		ax.errorbar(
			x_c.loc[pathway],
			y_c.loc[pathway],
			xerr=np.array([[xerr_low[i]], [xerr_high[i]]]),
			yerr=np.array([[yerr_low[i]], [yerr_high[i]]]),
			fmt=pathway_markers.get(pathway, "o"),
			markersize=np.sqrt(sizes[i]) / 1.8,  # convert scatter area-ish to a reasonable marker size
			mfc="white",
			mec=edgecolor,
			mew=1.2,
			ecolor=ecolor,
			elinewidth=elinewidth,
			capsize=capsize,
			capthick=capthick,
			alpha=alpha,
		)

		if annotate:
			ax.annotate(
				pathway,
				(x_c.loc[pathway], y_c.loc[pathway]),
				textcoords="offset points",
				xytext=(6, 6),
				fontsize=9,
				alpha=0.9,
			)

	# ----------------------------
	# 6) Reference lines (optional)
	# ----------------------------
	# if reference_lines is None:
	# 	reference_lines = {
	# 		2.7: "Generic Brine-Low (Kelly et al. 2021)",
	# 		3.1: "Generic Brine-High (Kelly et al. 2021)",
	# 		20.4: "Generic Spodumene (Kelly et al. 2021)",
	# 		8.9: "US Clays-Low (Iyer and Kelly 2024)",
	# 		16.6: "US Clays-High (Iyer and Kelly 2024)",
	# 		12.0: "US Brines (Iyer and Kelly 2024)",
	# 	}

	# if reference_lines:
	# 	xmax = float(np.nanmax(x_c.values)) if len(x_c) else 1.0
	# 	for y_val, label in reference_lines.items():
	# 		ax.axhline(y=y_val, color="gray", linestyle="dashed", alpha=0.5, linewidth=1.0)
	# 		ax.text(xmax * 0.995, y_val, label, va="center", ha="right", fontsize=9, color="gray")

	# ----------------------------
	# 7) Legends
	# ----------------------------
	# Marker legend for pathways
	pathway_handles = [
		Line2D([], [], marker=pathway_markers[p], linestyle="", color="gray", label=p, markersize=8)
		for p in pathways
	]
	ax.legend(handles=pathway_handles, title="Pathway", loc="upper left", bbox_to_anchor=(1.05, 1.0), frameon=True)

	# ----------------------------
	# 8) Axes formatting
	# ----------------------------
	ax.set_xlabel(x_key)
	ax.set_ylabel(y_key)
	ax.set_title(f"Pathway Summary (center={center_scenario}, range={low_scenario}→{high_scenario})")

	ax.set_xlim(left=0)
	ax.set_ylim(bottom=0)
	ax.grid(True, linestyle="--", linewidth=0.5, color="gray", alpha=0.3)
	fig.tight_layout(rect=[0, 0, 0.8, 1])

	plt.show()
	
	return fig, ax

def plot_tornado(
	tornado_data,
	metric="avg_opex",      # "avg_opex" | "avg_co2" | "avg_var_cost"
	top_n=5,
	title=None,
	xlab=None,
	show=True,
	colors=None,
	):
	colors = colors or {}
	baseline = tornado_data["baseline"][metric]

	# Build flat list of (label, opt_val, con_val)
	entries = []
	for name, vals in tornado_data.get("machines", {}).items():
		con = vals["conservative"][metric]
		opt = vals["optimistic"][metric]
		entries.append((f"Machine: {name}", opt, con))
	for name, vals in tornado_data.get("materials", {}).items():
		con = vals["conservative"][metric]
		opt = vals["optimistic"][metric]
		entries.append((f"Material: {name}", opt, con))

	# Sort by range descending, take top_n, reverse so largest is at top
	entries.sort(key=lambda x: abs(x[2] - x[1]), reverse=True)
	entries = entries[:top_n][::-1]

	print(entries)

	labels   = [e[0] for e in entries]
	opt_vals = np.array([e[1] for e in entries])
	con_vals = np.array([e[2] for e in entries])

	y = np.arange(len(entries))
	fig, ax = plt.subplots(figsize=(10, max(4, len(entries) * 0.7 + 1.5)))

	# Conservative bars — extend right (worse outcome)
	ax.barh(y, con_vals - baseline, left=baseline, color=colors.get("conservative"), label="Conservative", zorder=3)
	# Optimistic bars — extend left (better outcome, negative width)
	ax.barh(y, opt_vals - baseline, left=baseline, color=colors.get("optimistic"), label="Optimistic", zorder=3)

	ax.axvline(baseline, color="black", linewidth=1.0, zorder=4)
	ax.set_yticks(y)
	ax.set_yticklabels(labels, fontsize=9)
	ax.set_title(title or f"Tornado Plot — {metric}", pad=12)
	ax.set_xlabel(xlab or metric)
	ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
	ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="none")

	plt.tight_layout()
	if show:
		plt.show()
	return fig, ax

def _aggregate_step_series(labels, series, groups):
	"""
	Aggregate a (labels, series_dict) pair into presentation groups.

	Parameters
	----------
	labels : list[str]
		Step display names as returned by _build_steps_cost_series or
		_build_steps_impact_series.
	series : dict[str, list[float]]
		Series dict aligned with labels (same length per key).
	groups : list of (display_label: str, step_names: list[str])
		Ordered mapping from group label to the step names it absorbs.
		Steps not matched by any group are silently discarded.
		Steps matched by multiple groups use the first match.

	Returns
	-------
	(agg_labels, agg_series) with the same series keys as input.
	Values for unmatched step names are excluded (not bucketed elsewhere).
	"""
	label_to_idx = {lbl: i for i, lbl in enumerate(labels)}
	grouped = {sname for _, step_names in groups for sname in step_names}
	unmatched = [lbl for lbl in labels if lbl not in grouped]
	if unmatched:
		raise ValueError(f"Steps present in the series but absent from the group table: {unmatched}")
	agg_labels = []
	agg_series = {k: [] for k in series}

	for display_label, step_names in groups:
		agg_labels.append(display_label)
		for k in series:
			total = 0.0
			for sname in step_names:
				idx = label_to_idx.get(sname)
				if idx is not None:
					total += float(series[k][idx])
			agg_series[k].append(total)

	return agg_labels, agg_series

def plot_scenario_step_costs(sc, pathway_data, apv, *,
	view="opex",       # total|variable|fixed|opex|capex  (combo not supported)
	mode="average",       # "total" | "average"
	detail=2,           # 1|2|3 — applied to midpoint bars; conservative/optimistic always get aggregated to detail=1
	transp=True,
	wrap_width=12,
	xscale=1,
	yscale=1,
	title=None,
	xlab='Step Names',
	ylab=None,
	xticks=None,         # explicit tick positions on the value axis
	ylims=None,          # (min, max) for the value axis
	colors=None,
	):
	"""
	Plot midpoint step costs as stacked bars (detail=detail) with asymmetric error bars
	showing the conservative (lower) and optimistic (upper) scenario extents.
 
	The sc object must already have its facilities built (e.g. after evaluate_pathway or
	the relevant lithium_evaporation / clay_lepidolite call).  All three scenarios are
	re-run internally; the sc is left in the optimistic state after the call.
 
	view='combo' is not supported here — use view='opex' or view='capex' separately.
	"""
	import numpy as np
 
	view = str(view).lower().strip()
	if view == "combo":
		raise ValueError("view='combo' is not supported in plot_scenario_step_costs; use 'opex' or 'capex' separately.")
 
	mode = str(mode).lower().strip()
	if mode not in {"total", "average"}:
		raise ValueError("mode must be 'total' or 'average'")
	if mode == "average" and not apv:
		raise ValueError("apv is zero; cannot compute average costs.")
 
	def _get_totals(labels, series):
		"""Sum across all series keys to get one total per step."""
		n = len(labels)
		totals = np.zeros(n)
		for vals in series.values():
			totals += np.asarray(vals, dtype=float)
		return totals
 
	# ---- Conservative ----
	update_machines(sc, "conservative")
	update_materials(sc, pathway_data, "conservative")
	sc.update_apv(apv, recalc=True)
	con_labels, con_series, _ = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	con_totals = _get_totals(con_labels, con_series)
 
	# ---- Optimistic ----
	update_machines(sc, "optimistic")
	update_materials(sc, pathway_data, "optimistic")
	sc.update_apv(apv, recalc=True)
	opt_labels, opt_series, _ = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	opt_totals = _get_totals(opt_labels, opt_series)

	# ---- Midpoint ----
	update_machines(sc, "midpoint")
	update_materials(sc, pathway_data, "midpoint")
	sc.update_apv(apv, recalc=True)
	mid_labels, mid_series, stack_order = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	mid_totals = _get_totals(mid_labels, mid_series)

	# print(con_labels, mid_labels, opt_labels)
	# print(con_totals, mid_totals, opt_totals)
	# Sanity check — all three runs should produce the same step ordering
	if con_labels != mid_labels or opt_labels != mid_labels:
		raise ValueError("Step label mismatch across scenarios; check that all three runs produce the same steps.")
 
	# ---- Compute asymmetric error extents ----
	err_low  = np.maximum(mid_totals - opt_totals, 0.0)  # downward: midpoint -> optimistic
	err_high = np.maximum(con_totals - mid_totals, 0.0)  # upward:   midpoint -> conservative
 
	# ---- Apply mode scaling ----
	divisor = apv if mode == "average" else 1.0
	mid_series = {k: [v / divisor for v in vals] for k, vals in mid_series.items()}
	err_low  = err_low  / divisor
	err_high = err_high / divisor
 
	# ---- Default labels ----
	if title is None:
		base = "Cost of Steps" if mode == "total" else "Average Cost per Unit at each Step"
		title = f"{base} (with scenario range)"
	if ylab is None:
		ylab = "Total Cost" if mode == "total" else "Average Cost ($/t)"
 
	plot_stacked_bars(
		mid_labels, mid_series,
		stack_order=stack_order,
		colors=cost_series_colors(mid_series, colors),
		xscale=xscale, yscale=yscale,
		title=title, xlab=xlab, ylab=ylab,
		wrap_width=wrap_width,
		err_low=err_low,
		err_high=err_high,
		xticks=xticks,
		ylims=ylims
	)

def plot_scenario_step_impacts(sc, pathway_data, apv, *,
	mode="average",         # "total" | "average"
	impact="co2",           # impact category key (e.g. "co2", "ghg")
	transp=True,
	wrap_width=12,
	xscale=1,
	yscale=1,
	title=None,
	xlab='Step Names',
	ylab=None,
	ylims=None,          # (min, max) for the value axis
	xticks=None,         # explicit tick positions on the value axis
	colors=None,
	):
	"""
	Plot midpoint step impacts as stacked scope bars with asymmetric error bars
	showing the conservative (higher emissions) and optimistic (lower emissions) extents.
 
	The sc object must already have its facilities built. All three scenarios are
	re-run internally; the sc is left in the optimistic state after the call.
	"""
	import numpy as np
 
	mode = str(mode).lower().strip()
	if mode not in {"total", "average"}:
		raise ValueError("mode must be 'total' or 'average'")
	if mode == "average" and not apv:
		raise ValueError("apv is zero; cannot compute average impacts.")
 
	def _get_totals(scopes):
		"""Sum across all scope keys to get one total per step."""
		totals = None
		for vals in scopes.values():
			arr = np.asarray(vals, dtype=float)
			totals = arr if totals is None else totals + arr
		return totals if totals is not None else np.zeros(0)
 
	# ---- Conservative ----
	update_machines(sc, "conservative")
	update_materials(sc, pathway_data, "conservative")
	sc.update_apv(apv, recalc=True)
	con_labels, con_scopes, _ = sc._build_steps_impact_series(impact=impact, transp=transp)
	con_totals = _get_totals(con_scopes)
 
	# ---- Optimistic ----
	update_machines(sc, "optimistic")
	update_materials(sc, pathway_data, "optimistic")
	sc.update_apv(apv, recalc=True)
	opt_labels, opt_scopes, _ = sc._build_steps_impact_series(impact=impact, transp=transp)
	opt_totals = _get_totals(opt_scopes)
 
	# ---- Midpoint ----
	update_machines(sc, "midpoint")
	update_materials(sc, pathway_data, "midpoint")
	sc.update_apv(apv, recalc=True)
	mid_labels, mid_scopes, stack_order = sc._build_steps_impact_series(impact=impact, transp=transp)
	mid_totals = _get_totals(mid_scopes)
 
	# Sanity check
	if con_labels != mid_labels or opt_labels != mid_labels:
		raise ValueError("Step label mismatch across scenarios.")
 
	# ---- Compute asymmetric error extents ----
	# Conservative = higher emissions (upward bar), optimistic = lower (downward bar)
	err_high = np.maximum(con_totals - mid_totals, 0.0)
	err_low  = np.maximum(mid_totals - opt_totals, 0.0)
 
	# ---- Apply mode scaling ----
	divisor = apv if mode == "average" else 1.0
	mid_scopes = {k: [v / divisor for v in vals] for k, vals in mid_scopes.items()}
	err_low  = err_low  / divisor
	err_high = err_high / divisor
 
	# ---- Default labels ----
	if title is None:
		base = f"{impact.upper()} Impacts at each Step" if mode == "total" else f"Average {impact.upper()} Impact per Unit at each Step"
		title = f"{base} (with scenario range)"
	if ylab is None:
		ylab = f"Total {impact.upper()} (kg)" if mode == "total" else f"Avg {impact.upper()} (kg/t)"
 
	plot_stacked_bars(
		mid_labels, mid_scopes,
		stack_order=stack_order,
		colors=colors,
		xscale=xscale, yscale=yscale,
		title=title, xlab=xlab, ylab=ylab,
		wrap_width=wrap_width,
		err_low=err_low,
		err_high=err_high,
		xticks=xticks,
		ylims=ylims
	)

