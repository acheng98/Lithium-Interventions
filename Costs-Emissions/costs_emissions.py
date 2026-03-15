import re
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_num(x):
	"""Parse currency/numeric strings to float, returning NaN on failure or zero."""
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


def nanrange(arr):
	"""Return (min, max) of finite values, or (NaN, NaN) if none."""
	finite = arr[np.isfinite(arr)]
	if len(finite) == 0:
		return np.nan, np.nan
	return finite.min(), finite.max()


def nice_tick(data_range, n_ticks_target=6):
	raw       = data_range / n_ticks_target
	magnitude = 10 ** np.floor(np.log10(raw))
	residual  = raw / magnitude
	if residual < 1.5:   nice = 1
	elif residual < 3.5: nice = 2
	elif residual < 7.5: nice = 5
	else:                nice = 10
	return nice * magnitude


def clean_col_label(col):
	"""Strip pandas .N duplicate suffixes and tidy for display."""
	return re.sub(r'\.\d+$', '', col).strip()


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

METADATA_COLS = {"Project", "Company", "Location", "Material", "Dimension"}

OUR_COLS = {
	"low":  "Our Study-Low",
	"mid":  "Our Study-Midpoint",
	"high": "Our Study-High",
}

# Tick ratio: cost units per emissions unit on a major gridline.
# A value of 200 means $2000/t corresponds visually to 10 t CO₂eq/t, etc.
# Both axes are scaled independently to fit their data; this ratio controls
# only the relative spacing of ticks (and thus the angle of iso-cost lines).
TICK_RATIO = 200   # ($/t LCE) per (t CO₂e/t LCE)

# Colour palette by material type
MATERIAL_COLORS = {
	"Brine":      "#4292c6",   # medium blue
	"Brine-DLE":  "#c6dbef",   # pale blue
	"Clay":       "#08519c",   # dark navy blue
	"Spodumene":  "#2ca02c",   # green
	"Lepidolite": "#d62728",   # red
}
DEFAULT_COLOR = "#7f7f7f"

# Style for literature reference lines
LIT_LINE_COLOR  = "#888888"
LIT_LINE_ALPHA  = 0.55
LIT_LINE_WIDTH  = 0.9
LIT_LINE_STYLE  = "--"
LIT_LABEL_COLOR = "#444444"
LIT_LABEL_SIZE  = 6.5


# ---------------------------------------------------------------------------
# Main plotting function
# ---------------------------------------------------------------------------

def plot_cost_vs_emissions(
	csv_path:       str,
	title:          str   = "Cost vs. Emissions by project",
	figsize:        tuple = (9, 6),   # no longer needs to be square
	save_path:      str   = None,     # None → use default; False → don't save
	our_alpha:      float = 0.55,
	lit_alpha:      float = 0.18,
	our_edge_alpha: float = 0.90,
	lit_edge_alpha: float = 0.45,
	show_lit_lines:      bool = False,   # draw dashed reference lines inside boxes
	show_lit_labels:     bool = False,   # label those lines (ignored if show_lit_lines=False)
	show_project_labels: bool = True,    # annotate each project with its name
	top_n:               int  = None,    # if set, use Our Study-Low-{N}/High-{N} as box bounds
):
	# ------------------------------------------------------------------
	# Load & parse
	# ------------------------------------------------------------------
	df = pd.read_csv(csv_path)

	numeric_cols = [c for c in df.columns if c not in METADATA_COLS]
	for c in numeric_cols:
		df[c] = df[c].map(parse_num)

	our_col_set = set(OUR_COLS.values())
	lit_cols    = [c for c in numeric_cols
	               if c not in our_col_set and not c.startswith("Our Study")]

	# Resolve which low/high columns to use for the Our Study bounding box.
	# Midpoint is always the base column regardless of top_n.
	if top_n is None:
		our_lo_col = OUR_COLS["low"]
		our_hi_col = OUR_COLS["high"]
	else:
		our_lo_col = f"Our Study-Low-{top_n}"
		our_hi_col = f"Our Study-High-{top_n}"
		missing = [c for c in (our_lo_col, our_hi_col) if c not in df.columns]
		if missing:
			available = sorted(set(
				c.replace("Our Study-Low-", "").replace("Our Study-High-", "")
				for c in df.columns
				if c.startswith("Our Study-Low-") or c.startswith("Our Study-High-")
			))
			avail_str = ", ".join(available) if available else "(none found)"
			raise SystemExit(
				f"ERROR: --show-top {top_n} requested but column(s) not found in CSV: "
				f"{missing}\n"
				f"Available top-N suffixes: {avail_str}"
			)
	our_lo_col  # noqa — referenced below

	cost_df  = df[df["Dimension"] == "Cost"].copy()
	emiss_df = df[df["Dimension"] == "Emissions"].copy()

	# ------------------------------------------------------------------
	# Identify modelled projects (Our Study data in BOTH dimensions)
	# ------------------------------------------------------------------
	our_vals       = list(OUR_COLS.values())
	cost_our_mask  = cost_df[our_vals].notna().any(axis=1)
	emiss_our_mask = emiss_df[our_vals].notna().any(axis=1)
	cost_with_our  = set(cost_df.loc[cost_our_mask,  "Project"])
	emiss_with_our = set(emiss_df.loc[emiss_our_mask, "Project"])
	both_projects  = cost_with_our & emiss_with_our

	# ------------------------------------------------------------------
	# Build per-project records
	# ------------------------------------------------------------------
	records = []
	for project in sorted(both_projects):
		crow = cost_df[cost_df["Project"] == project].iloc[0]
		erow = emiss_df[emiss_df["Project"] == project].iloc[0]

		material = crow["Material"]

		c_lo  = crow[our_lo_col]
		c_mid = crow[OUR_COLS["mid"]]
		c_hi  = crow[our_hi_col]
		e_lo  = erow[our_lo_col]
		e_mid = erow[OUR_COLS["mid"]]
		e_hi  = erow[our_hi_col]

		lit_cost_vals  = crow[[c for c in lit_cols if c in crow.index]].to_numpy(dtype=float)
		lit_emiss_vals = erow[[c for c in lit_cols if c in erow.index]].to_numpy(dtype=float)

		lit_c_lo, lit_c_hi = nanrange(lit_cost_vals)
		lit_e_lo, lit_e_hi = nanrange(lit_emiss_vals)

		records.append(dict(
			project=project, material=material,
			c_lo=c_lo, c_mid=c_mid, c_hi=c_hi,
			e_lo=e_lo, e_mid=e_mid, e_hi=e_hi,
			lit_c_lo=lit_c_lo, lit_c_hi=lit_c_hi,
			lit_e_lo=lit_e_lo, lit_e_hi=lit_e_hi,
		))

	if not records:
		raise ValueError("No projects found with Our Study data in both cost and emissions.")

	# ------------------------------------------------------------------
	# Collect literature reference values for modelled projects
	# cost_lit_lines : {col: [val, ...]}  → vertical lines (x = cost value)
	# emiss_lit_lines: {col: [val, ...]}  → horizontal lines (y = emiss value)
	# ------------------------------------------------------------------
	modelled_cost  = cost_df[cost_df["Project"].isin(both_projects)]
	modelled_emiss = emiss_df[emiss_df["Project"].isin(both_projects)]

	# {col: {project: val}} — preserves which project each value belongs to
	cost_lit_lines  = {}
	emiss_lit_lines = {}
	for c in lit_cols:
		if c in modelled_cost.columns:
			by_project = modelled_cost.set_index("Project")[c].dropna().to_dict()
			if by_project:
				cost_lit_lines[c] = by_project
		if c in modelled_emiss.columns:
			by_project = modelled_emiss.set_index("Project")[c].dropna().to_dict()
			if by_project:
				emiss_lit_lines[c] = by_project

	# ------------------------------------------------------------------
	# Axis limits: each axis sized tightly to data, tick spacing fixed
	# by TICK_RATIO so $200/t corresponds to 1 t CO₂e/t visually.
	# ------------------------------------------------------------------
	all_c = [r[k] for r in records for k in
			 ("c_lo", "c_mid", "c_hi", "lit_c_lo", "lit_c_hi") if np.isfinite(r[k])]
	all_e = [r[k] for r in records for k in
			 ("e_lo", "e_mid", "e_hi", "lit_e_lo", "lit_e_hi") if np.isfinite(r[k])]

	c_max_data = max(all_c)
	e_max_data = max(all_e)

	# Derive tick_e from the emissions data, then tick_c from the ratio.
	tick_e = nice_tick(e_max_data)
	tick_c = TICK_RATIO * tick_e

	# Axis limits: round up to next tick, independently per axis.
	c_max = tick_c * int(np.ceil(c_max_data / tick_c))
	e_max = tick_e * int(np.ceil(e_max_data / tick_e))

	# ------------------------------------------------------------------
	# Build the list of (box_x_lo, box_x_hi, box_y_lo, box_y_hi) for
	# clipping lit lines. Each record contributes up to two boxes.
	# ------------------------------------------------------------------
	# Only literature bounding boxes — lit lines should not appear in Our Study boxes.
	# Each entry includes the project name so lines are only drawn in their own box.
	boxes = []
	for r in records:
		if (np.isfinite(r["lit_c_lo"]) and np.isfinite(r["lit_c_hi"]) and
				np.isfinite(r["lit_e_lo"]) and np.isfinite(r["lit_e_hi"])):
			boxes.append((r["project"], r["lit_c_lo"], r["lit_c_hi"], r["lit_e_lo"], r["lit_e_hi"]))

	# ------------------------------------------------------------------
	# Plot
	# ------------------------------------------------------------------
	fig, ax = plt.subplots(figsize=figsize)

	# ---- Build letter mapping, pairing -Low/-High cols under one letter ----
	import string

	# Strip known low/high suffixes to a common base name for each column
	_STRIP_SUFFIXES = [
		"-Low", "-High",
		" - Lower Range", " - Upper Range",
		" - Low", " - High",
		" (Low estimate)", " (High estimate)",
	]
	def col_to_base(col):
		name = clean_col_label(col)
		# All Ambrose & Kendall variants collapse to one base
		if name.startswith("Ambrose and Kendall"):
			return "Ambrose and Kendall 2020b"
		for sfx in _STRIP_SUFFIXES:
			if name.endswith(sfx):
				return name[: -len(sfx)].strip(" -–")
		return name

	# Collect unique base names in encounter order (cost first, then emissions)
	all_base_names = []
	for col in list(cost_lit_lines) + list(emiss_lit_lines):
		base = col_to_base(col)
		if base not in all_base_names:
			all_base_names.append(base)

	letters = list(string.ascii_uppercase)
	base_to_letter  = {base: letters[i] for i, base in enumerate(all_base_names)}
	# Map each column directly to its letter for convenient lookup
	col_to_letter   = {col: base_to_letter[col_to_base(col)]
					   for col in list(cost_lit_lines) + list(emiss_lit_lines)}

	if show_lit_labels:
		print("\nLiterature line key:")
		for base, letter in base_to_letter.items():
			print(f"  {letter}  {base}")
		print()

	# ---- Literature reference lines (clipped to lit box interiors) -------
	if show_lit_lines:

		def draw_vline_in_boxes(project, v, display_label):
			"""Vertical line at x=v, drawn only inside the lit box for this project."""
			label_y = None
			for (proj, bx_lo, bx_hi, by_lo, by_hi) in boxes:
				if proj == project and bx_lo <= v <= bx_hi:
					ax.plot([v, v], [by_lo, by_hi],
							color=LIT_LINE_COLOR, alpha=LIT_LINE_ALPHA,
							linewidth=LIT_LINE_WIDTH, linestyle=LIT_LINE_STYLE,
							zorder=4)
					label_y = by_hi if label_y is None else max(label_y, by_hi)
			if show_lit_labels and label_y is not None:
				ax.annotate(display_label, xy=(v, label_y),
							xytext=(0, 2), textcoords="offset points",
							rotation=0, va="bottom", ha="center",
							fontsize=LIT_LABEL_SIZE, color=LIT_LABEL_COLOR,
							clip_on=True, zorder=7)

		def draw_hline_in_boxes(project, v, display_label):
			"""Horizontal line at y=v, drawn only inside the lit box for this project."""
			label_x = None
			for (proj, bx_lo, bx_hi, by_lo, by_hi) in boxes:
				if proj == project and by_lo <= v <= by_hi:
					ax.plot([bx_lo, bx_hi], [v, v],
							color=LIT_LINE_COLOR, alpha=LIT_LINE_ALPHA,
							linewidth=LIT_LINE_WIDTH, linestyle=LIT_LINE_STYLE,
							zorder=4)
					label_x = bx_hi if label_x is None else max(label_x, bx_hi)
			if show_lit_labels and label_x is not None:
				ax.annotate(display_label, xy=(label_x, v),
							xytext=(4, -4), textcoords="offset points",
							va="bottom", ha="left",
							fontsize=LIT_LABEL_SIZE, color=LIT_LABEL_COLOR,
							clip_on=True, zorder=7)

		for col, by_project in cost_lit_lines.items():
			letter = col_to_letter[col]
			for project, v in by_project.items():
				draw_vline_in_boxes(project, v, letter)

		for col, by_project in emiss_lit_lines.items():
			letter = col_to_letter[col]
			for project, v in by_project.items():
				draw_hline_in_boxes(project, v, letter)

	# ---- Per-project boxes and points --------------------------------
	legend_handles = []
	seen_materials = set()

	for r in records:
		color = MATERIAL_COLORS.get(r["material"], DEFAULT_COLOR)
		rgb   = plt.matplotlib.colors.to_rgb(color)

		# Literature bounding box (transparent)
		if (np.isfinite(r["lit_c_lo"]) and np.isfinite(r["lit_c_hi"]) and
				np.isfinite(r["lit_e_lo"]) and np.isfinite(r["lit_e_hi"])):
			ax.add_patch(mpatches.FancyBboxPatch(
				(r["lit_c_lo"], r["lit_e_lo"]),
				r["lit_c_hi"] - r["lit_c_lo"],
				r["lit_e_hi"] - r["lit_e_lo"],
				boxstyle="square,pad=0", linewidth=1.2,
				edgecolor=(*rgb, lit_edge_alpha),
				facecolor=(*rgb, lit_alpha), zorder=2,
			))

		# Our Study bounding box (opaque)
		if (np.isfinite(r["c_lo"]) and np.isfinite(r["c_hi"]) and
				np.isfinite(r["e_lo"]) and np.isfinite(r["e_hi"])):
			ax.add_patch(mpatches.FancyBboxPatch(
				(r["c_lo"], r["e_lo"]),
				r["c_hi"] - r["c_lo"],
				r["e_hi"] - r["e_lo"],
				boxstyle="square,pad=0", linewidth=1.6,
				edgecolor=(*rgb, our_edge_alpha),
				facecolor=(*rgb, our_alpha), zorder=3,
			))

		# Midpoint
		if np.isfinite(r["c_mid"]) and np.isfinite(r["e_mid"]):
			ax.scatter(r["c_mid"], r["e_mid"], color=color, s=70,
					   zorder=5, edgecolors="white", linewidths=0.8)

		# Project label
		if show_project_labels:
			lx = r["c_mid"] if np.isfinite(r["c_mid"]) else (r["c_lo"] + r["c_hi"]) / 2
			ly = r["e_mid"] if np.isfinite(r["e_mid"]) else (r["e_lo"] + r["e_hi"]) / 2
			ax.annotate(r["project"], xy=(lx, ly), xytext=(-18, -15),
						textcoords="offset points", fontsize=8, color=color, zorder=6)

		# Legend entry (one per material type)
		if r["material"] not in seen_materials:
			seen_materials.add(r["material"])
			legend_handles.append(mpatches.Patch(facecolor=color, label=r["material"]))

	# Shared legend proxies
	legend_handles += [
		mpatches.Patch(facecolor="gray", alpha=our_alpha, edgecolor="gray",
					   linewidth=1.6, label="Our Study range"),
		mpatches.Patch(facecolor="gray", alpha=lit_alpha, edgecolor="gray",
					   linewidth=1.2, label="Literature range"),
		Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",
			   markersize=7, markeredgecolor="white", label="Our Study midpoint"),
	]

	# ------------------------------------------------------------------
	# Axes formatting
	# ------------------------------------------------------------------
	ax.set_xlim(0, c_max)
	ax.set_ylim(0, e_max)
	ax.set_xticks(np.arange(0, c_max + tick_c * 0.01, tick_c))
	ax.set_yticks(np.arange(0, e_max + tick_e * 0.01, tick_e))
	ax.set_xlabel("Cost ($/t Li₂CO₃)", fontsize=11)
	ax.set_ylabel("Emissions (t CO₂e / t Li₂CO₃)", fontsize=11)
	ax.set_title(title, fontsize=12, pad=10)
	ax.grid(True, linestyle=":", alpha=0.4)

	ax.legend(handles=legend_handles, loc="upper left", fontsize=8, framealpha=0.85)
	plt.tight_layout()

	if save_path is False:
		save_path = None
	if save_path is not None:
		plt.savefig(save_path, dpi=300, bbox_inches="tight")
		print(f"Saved to {save_path}")

	plt.show()
	return fig


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="Plot cost vs. emissions bounding-box chart."
	)
	parser.add_argument(
		"--lit-lines", action="store_true", default=False,
		help="Draw dashed reference lines inside boxes for each literature study value",
	)
	parser.add_argument(
		"--lit-labels", action="store_true", default=False,
		help="Label the literature reference lines (requires --lit-lines)",
	)
	parser.add_argument(
		"--output", metavar="PATH",
		help="Save figure to this path (e.g. --output chart.png)",
	)
	parser.add_argument(
		"--show-top", dest="top_n", type=int, default=None, metavar="N",
		help=(
			"Use Our Study-Low-{N}/High-{N} as box bounds instead of the full range. "
			"Fails loudly if that suffix is not present in the CSV."
		),
	)
	save_group = parser.add_mutually_exclusive_group()
	save_group.add_argument(
		"--save", dest="save", action="store_true", default=False,
		help="Save the figure to disk",
	)
	save_group.add_argument(
		"--no-save", dest="save", action="store_false",
		help="Display only, do not save (default)",
	)
	label_group = parser.add_mutually_exclusive_group()
	label_group.add_argument(
		"--project-labels", dest="project_labels", action="store_true", default=True,
		help="Show project name labels on the figure (default)",
	)
	label_group.add_argument(
		"--no-project-labels", dest="project_labels", action="store_false",
		help="Hide project name labels",
	)
	args = parser.parse_args()

	if not args.save:
		save_path = False
	elif args.output:
		save_path = args.output
	else:
		save_path = "cost_vs_emissions.png"

	plot_cost_vs_emissions(
		"reported_both.csv",
		save_path=save_path,
		show_lit_lines=args.lit_lines,
		show_lit_labels=args.lit_labels,
		show_project_labels=args.project_labels,
		top_n=args.top_n,
	)