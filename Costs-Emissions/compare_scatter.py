import re
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METADATA_COLS = {"Project", "Company", "Location", "Material", "Dimension"}

OUR_COLS = {
	"low":  "Our Study-Low",
	"mid":  "Our Study-Midpoint",
	"high": "Our Study-High",
}

RANGE_SUFFIX_PAIRS = [
	("-Low",  "-High"),
]

DIMENSION_DEFAULTS = {
	"Cost": {
		"value_label": "Reported ($/t LCE)",
		"title":       "Reported costs by project",
		"figsize":     (14, 8),
		"save_path":   "cost_compare.png",
		"xmin":        0.0,
	},
	"Emissions": {
		"value_label": "Reported emissions (t CO₂e/t LCE)",
		"title":       "Reported emissions by project",
		"figsize":     (14, 9),
		"save_path":   "emissions_compare.png",
		"xmin":        0.0,
	},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_num(x):
	"""Parse currency/numeric strings → float, NaN on failure or zero."""
	if x is None:
		return np.nan
	s = str(x).strip().replace(",", "").replace("$", "")
	if s.lower() in {"", "na", "n/a", "null", "-", "none"}:
		return np.nan
	try:
		v = float(s)
		return np.nan if v == 0 else v
	except ValueError:
		return np.nan


def clean_label(col):
	"""Strip pandas duplicate suffixes (.1, .2, …) from column names."""
	return re.sub(r'\.\d+$', '', col).strip()


def detect_lit_series(df_filtered, lit_cols):
	"""
	Dynamically group literature columns into range pairs and singles.
	Only includes series with at least one finite value in df_filtered.

	Returns a list of dicts:
	  {"label": str, "type": "range"|"ak_group"|"single", "cols": [col, ...]}
	"""
	remaining = list(lit_cols)
	series = []

	# --- Exception: Ambrose & Kendall — all columns grouped into one range series ---
	ak_cols = [c for c in remaining if c.startswith("Ambrose and Kendall")]
	if ak_cols:
		if any(df_filtered[c].notna().any() for c in ak_cols):
			series.append({"label": "Ambrose and Kendall 2020b", "type": "ak_group", "cols": ak_cols})
		for c in ak_cols:
			remaining.remove(c)

	# --- Detect range pairs via known suffix patterns ---
	for lo_sfx, hi_sfx in RANGE_SUFFIX_PAIRS:
		for col in list(remaining):
			if not col.endswith(lo_sfx):
				continue
			base   = col[: -len(lo_sfx)]
			hi_col = base + hi_sfx
			if hi_col not in remaining:
				continue
			label    = clean_label(base).strip(" -–")
			has_data = df_filtered[col].notna().any() or df_filtered[hi_col].notna().any()
			if has_data:
				series.append({"label": label, "type": "range", "cols": [col, hi_col]})
			remaining.remove(col)
			remaining.remove(hi_col)

	# --- Detect pandas-duplicate pairs (same name + .N suffix) ---
	dup_bases = {}
	for col in list(remaining):
		m = re.match(r'^(.+)\.\d+$', col)
		if m:
			base_col = m.group(1)
			if base_col in remaining:
				dup_bases[base_col] = col
	for base_col, dup_col in dup_bases.items():
		label    = clean_label(base_col)
		has_data = df_filtered[base_col].notna().any() or df_filtered[dup_col].notna().any()
		if has_data:
			series.append({"label": label, "type": "range", "cols": [base_col, dup_col]})
		remaining.remove(base_col)
		remaining.remove(dup_col)

	# --- Remaining columns are singles ---
	for col in remaining:
		if df_filtered[col].notna().any():
			series.append({"label": clean_label(col), "type": "single", "cols": [col]})

	return series


# ---------------------------------------------------------------------------
# Main plot function
# ---------------------------------------------------------------------------

def plot_project_scatter(
	csv_path:    str,
	dimension:   str  = "Cost",          # "Cost" or "Emissions"
	value_label: str  = None,
	title:       str  = None,
	figsize:     tuple = None,
	save_path:   str  = None,
	legend_loc:  str  = "center left",
	legend_bbox:  tuple = (1.02, 0.5),
	show_separators: bool = True,
	xmin:        float = None,
):
	# Fill defaults from dimension config
	defaults = DIMENSION_DEFAULTS.get(dimension, DIMENSION_DEFAULTS["Cost"])
	if value_label is None: value_label = defaults["value_label"]
	if title       is None: title       = defaults["title"]
	if figsize     is None: figsize     = defaults["figsize"]
	if save_path   is None: save_path   = defaults["save_path"]  # use dimension default
	if save_path  is False: save_path   = None                    # False = suppress saving
	if xmin        is None: xmin        = defaults["xmin"]

	# ------------------------------------------------------------------
	# Load & filter
	# ------------------------------------------------------------------
	df = pd.read_csv(csv_path)

	numeric_cols = [c for c in df.columns if c not in METADATA_COLS]
	for c in numeric_cols:
		df[c] = df[c].map(parse_num)

	df = df[df["Dimension"] == dimension].copy()

	our_vals = list(OUR_COLS.values())
	df = df[df[our_vals].notna().any(axis=1)].copy()
	if df.empty:
		raise ValueError(f"No '{dimension}' rows have 'Our Study' data.")

	df["ProjectLabel"] = (
		df["Project"].astype(str) + " (" + df["Material"].astype(str) + ")"
	)

	# ------------------------------------------------------------------
	# Detect literature series
	# ------------------------------------------------------------------
	our_col_set = set(OUR_COLS.values())
	lit_cols    = [c for c in numeric_cols if c not in our_col_set]
	lit_series  = detect_lit_series(df, lit_cols)

	# ------------------------------------------------------------------
	# Slot layout
	# ------------------------------------------------------------------
	all_slots   = ["Our Study"] + [s["label"] for s in lit_series]
	slot_step   = 0.045
	project_gap = 0.70
	n_slots     = len(all_slots)

	def y_for(proj_idx, slot_idx):
		return proj_idx * (project_gap + slot_step * (n_slots - 1)) + slot_idx * slot_step

	# ------------------------------------------------------------------
	# Colors
	# ------------------------------------------------------------------
	color_cycle = [
		"#d62728", "#ffa500", "#2ca02c", "#1f77b4", "#9467bd",
		"#8c564b", "#e377c2", "#17becf", "#bcbd22", "#ff7f0e",
		"#c7c7c7", "#aec7e8",
	]
	colors = {"Our Study": "#000000"}
	for i, s in enumerate(lit_series):
		colors[s["label"]] = color_cycle[i % len(color_cycle)]

	# ------------------------------------------------------------------
	# Plot helpers
	# ------------------------------------------------------------------
	def _range_with_end_dots(ax, x_lo, x_hi, yv, color, label, linewidth, dotsize):
		ax.hlines(yv, x_lo, x_hi, color=color, linewidth=linewidth, zorder=2)
		ax.scatter(x_lo, yv, color=color, s=dotsize, zorder=4)
		ax.scatter(x_hi, yv, color=color, s=dotsize, zorder=4)
		ax.plot([], [], color=color, linewidth=linewidth, label=label)

	# ------------------------------------------------------------------
	# Draw
	# ------------------------------------------------------------------
	projects   = df["ProjectLabel"].astype(str).tolist()
	n_projects = len(projects)

	fig, ax = plt.subplots(figsize=figsize)

	if show_separators and n_projects > 1:
		for i in range(n_projects - 1):
			mid = (y_for(i + 1, 0) + y_for(i, n_slots - 1)) / 2
			ax.axhline(mid, linewidth=0.6, alpha=0.25)

	y_tick_pos = [
		(y_for(i, 0) + y_for(i, n_slots - 1)) / 2 for i in range(n_projects)
	]

	# Our Study (range + midpoint)
	y_our = np.array([y_for(i, 0) for i in range(n_projects)], dtype=float)

	x_lo  = df[OUR_COLS["low"]].to_numpy(dtype=float)
	x_mid = df[OUR_COLS["mid"]].to_numpy(dtype=float)
	x_hi  = df[OUR_COLS["high"]].to_numpy(dtype=float)

	mask_range = np.isfinite(x_lo) & np.isfinite(x_hi)
	if mask_range.any():
		_range_with_end_dots(
			ax, x_lo[mask_range], x_hi[mask_range], y_our[mask_range],
			colors["Our Study"], "Our study (low–high)", linewidth=3.5, dotsize=55,
		)
	mask_mid = np.isfinite(x_mid)
	if mask_mid.any():
		ax.scatter(
			x_mid[mask_mid], y_our[mask_mid],
			color=colors["Our Study"], s=85, zorder=3, label="Our study (midpoint)",
		)

	# Literature series
	for s in lit_series:
		label    = s["label"]
		color    = colors[label]
		slot_idx = all_slots.index(label)
		yy       = np.array([y_for(i, slot_idx) for i in range(n_projects)], dtype=float)

		if s["type"] == "ak_group":
			vals = np.vstack([df[c].to_numpy(dtype=float) for c in s["cols"]])
			any_finite = np.isfinite(vals).any(axis=0)
			x_l = np.where(any_finite, np.nanmin(np.where(np.isfinite(vals), vals,  np.inf), axis=0), np.nan)
			x_h = np.where(any_finite, np.nanmax(np.where(np.isfinite(vals), vals, -np.inf), axis=0), np.nan)
			mask = np.isfinite(x_l) & np.isfinite(x_h)
			if mask.any():
				_range_with_end_dots(
					ax, x_l[mask], x_h[mask], yy[mask],
					color, label, linewidth=2.2, dotsize=26,
				)
			for c in s["cols"]:
				xv = df[c].to_numpy(dtype=float)
				m  = np.isfinite(xv)
				if m.any():
					ax.scatter(xv[m], yy[m], color=color, s=30, zorder=5)

		elif s["type"] == "range":
			lo_col, hi_col = s["cols"]
			x_l  = df[lo_col].to_numpy(dtype=float)
			x_h  = df[hi_col].to_numpy(dtype=float)
			mask = np.isfinite(x_l) & np.isfinite(x_h)
			if mask.any():
				_range_with_end_dots(
					ax, x_l[mask], x_h[mask], yy[mask],
					color, f"{label} (range)", linewidth=2.2, dotsize=26,
				)
			for xv in [x_l, x_h]:
				solo = np.isfinite(xv) & ~mask
				if solo.any():
					ax.scatter(xv[solo], yy[solo], color=color, s=30, zorder=3)

		else:
			xv   = df[s["cols"][0]].to_numpy(dtype=float)
			mask = np.isfinite(xv)
			if mask.any():
				ax.scatter(xv[mask], yy[mask], color=color, s=50, zorder=3, label=label)

	# ------------------------------------------------------------------
	# Axes
	# ------------------------------------------------------------------
	ax.set_yticks(y_tick_pos)
	ax.set_yticklabels(projects)
	ax.set_ylim(y_for(n_projects - 1, n_slots - 1) + 0.15, y_for(0, 0) - 0.15)
	ax.set_xlabel(value_label)
	ax.set_title(title)
	ax.set_xlim(left=xmin)
	ax.grid(True, axis="x", linestyle=":", alpha=0.4)

	handles, labels = ax.get_legend_handles_labels()
	seen, uniq_h, uniq_l = set(), [], []
	for h, l in zip(handles, labels):
		if l not in seen:
			seen.add(l); uniq_h.append(h); uniq_l.append(l)
	ax.legend(uniq_h, uniq_l, loc=legend_loc, bbox_to_anchor=legend_bbox)

	plt.tight_layout()
	if save_path is not None:
		plt.savefig(save_path, dpi=300, bbox_inches="tight")
	plt.show()
	return fig


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="Plot cost or emissions comparison scatter chart."
	)
	group = parser.add_mutually_exclusive_group()
	group.add_argument(
		"--costs", dest="dimension", action="store_const", const="Cost",
		help="Plot costs (default)",
	)
	group.add_argument(
		"--emissions", dest="dimension", action="store_const", const="Emissions",
		help="Plot emissions",
	)
	parser.set_defaults(dimension="Cost")
	parser.add_argument(
		"--output", metavar="PATH",
		help="Override the default save path (e.g. --output my_chart.png)",
	)
	save_group = parser.add_mutually_exclusive_group()
	save_group.add_argument(
		"--save", dest="save", action="store_true", default=False,
		help="Save the figure to disk",
	)
	save_group.add_argument(
		"--no-save", dest="save", action="store_false",
		help="Display only, do not save to disk (default)",
	)
	args = parser.parse_args()

	# Resolve save path: None suppresses saving, explicit --output overrides default
	if not args.save:
		save_path = False  # sentinel: suppress saving
	elif args.output:
		save_path = args.output
	else:
		save_path = None   # None → use dimension default

	plot_project_scatter("reported_both.csv", dimension=args.dimension, save_path=save_path)