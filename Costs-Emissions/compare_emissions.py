import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def parse_number_to_float(x):
	# Parses values like "4.45", "", None into float or NaN
	if x is None:
		return np.nan
	s = str(x).strip()
	if s == "" or s.lower() in {"na", "n/a", "null", "-", "none"}:
		return np.nan
	s = s.replace(",", "")
	try:
		return float(s)
	except ValueError:
		return np.nan

def plot_project_reported_emissions(
	csv_path: str,
	value_label: str = "Reported emissions (t CO2e/t LCE)",
	title: str = "Reported emissions by project",
	figsize=(12, 8),
	save_path: str | None = None,
	legend_loc: str = "center left",
	legend_bbox=(1.02, 0.5),
	show_separators: bool = True,
	xmin: float = 0.0,
):
	df = pd.read_csv(csv_path)

	col_map = {
		"Material": "Material",
		"Our Low": "Our Study-Low",
		"Our Mid": "Our Study-Midpoint",
		"Our High": "Our Study-High",
		"Pieseler 2024": "Pieseler et al. 2024 (Best Guess)",
		"Kelly Low": "Kelly et al. 2021-Low",
		"Kelly High": "Kelly et al. 2021-High",
		"IyerKelly Low": "Iyer and Kelly 2024-Low",
		"IyerKelly High": "Iyer and Kelly 2024-High",
		"Mousavinezhad 2024": "Mousavinezhad et al. 2024",
		"Mousavinezhad 2025": "Mousavinezhad et al. 2025",
		"Sun 2025": "Sun et al. 2025",
		"Khakmardan 2024": "Khakmardan et al. 2024",
		"Roy 2024": "Roy et al. 2024",
		"Liu 2025": "Liu et al. 2025",
		"SchenkerPfister 2025": "Schenker and Pfister 2025",
		"Manjong Low": "Manjong et al. 2021-Low",
		"Manjong High": "Manjong et al. 2021-High",
		"Ambrose High Grade": "Ambrose and Kendall 2020b-High Grade",
		"Ambrose Low Grade": "Ambrose and Kendall 2020b-Low Grade",
		"Ambrose Low Grade Unfavorable": "Ambrose and Kendall 2020b-Low Grade, Unfavorable",
	}

	for k, c in col_map.items():
		if c in df.columns:
			if k == "Material":
				df[c] = df[c].astype(str)
			else:
				df[c] = df[c].map(parse_number_to_float)

	# Only keep rows where data from 'Our Study' exists
	mask_our = (
		df[col_map["Our Low"]].notna()
		| df[col_map["Our Mid"]].notna()
		| df[col_map["Our High"]].notna()
	)
	df = df.loc[mask_our].copy()
	if df.empty:
		raise ValueError("No rows have 'Our Study' data.")

	df["ProjectLabel"] = df["Project"].astype(str) + " (" + df["Material"].astype(str) + ")"

	# Vertical slots (Our Study first)
	study_slots = [
		"Our Study",
		"Pieseler et al. 2024",
		"Kelly et al. 2021",
		"Iyer and Kelly 2024",
		"Mousavinezhad et al. 2025",
		"Mousavinezhad et al. 2024",
		"Sun et al. 2025",
		"Khakmardan et al. 2024",
		"Roy et al. 2024",
		"Liu et al. 2025",
		"Schenker and Pfister 2025",
		"Manjong et al. 2021",
		"Ambrose and Kendall 2020b",	# combined slot
	]

	slot_step = 0.045
	project_gap = 0.70
	slots_per_project = len(study_slots)

	def y_for(project_index: int, slot_index: int) -> float:
		return project_index * (project_gap + slot_step * (slots_per_project - 1)) + slot_index * slot_step

	colors = {
		"Our Study": "#000000",						# black
		"Pieseler et al. 2024": "#7f7f7f",			# gray
		"Kelly et al. 2021": "#ff7f0e",				# orange
		"Iyer and Kelly 2024": "#bcbd22",			# olive
		"Mousavinezhad et al. 2025": "#1f77b4",		# blue
		"Mousavinezhad et al. 2024": "#6baed6",		# light blue
		"Sun et al. 2025": "#2ca02c",				# green
		"Khakmardan et al. 2024": "#d62728",		# red
		"Roy et al. 2024": "#9467bd",				# purple
		"Liu et al. 2025": "#8c564b",				# brown
		"Schenker and Pfister 2025": "#e377c2",		# pink
		"Manjong et al. 2021": "#17becf",			# cyan
		"Ambrose and Kendall 2020b": "#c7c7c7",		# light gray (combined)
	}

	def _range_with_end_dots(ax, x_lo, x_hi, yv, color, label, linewidth, dotsize):
		ax.hlines(yv, x_lo, x_hi, color=color, linewidth=linewidth, zorder=2)
		ax.scatter(x_lo, yv, color=color, s=dotsize, zorder=4)
		ax.scatter(x_hi, yv, color=color, s=dotsize, zorder=4)
		ax.plot([], [], color=color, linewidth=linewidth, label=label)

	def _scatter_points(ax, xs, ys, color, label, size):
		ax.scatter(xs, ys, color=color, s=size, zorder=3, label=label)

	projects = df["ProjectLabel"].astype(str).tolist()
	n_projects = len(projects)

	fig, ax = plt.subplots(figsize=figsize)

	if show_separators and n_projects > 1:
		for i in range(n_projects - 1):
			y_top_of_next = y_for(i + 1, 0)
			y_bottom_of_prev = y_for(i, slots_per_project - 1)
			ax.axhline((y_top_of_next + y_bottom_of_prev) / 2, linewidth=0.6, alpha=0.25)

	y_tick_pos = []
	for i in range(n_projects):
		y_tick_pos.append((y_for(i, 0) + y_for(i, slots_per_project - 1)) / 2)

	# Our Study (range + midpoint)
	slot_our = study_slots.index("Our Study")
	y_our = np.array([y_for(i, slot_our) for i in range(n_projects)], dtype=float)

	x_olo = df[col_map["Our Low"]].to_numpy(dtype=float)
	x_omid = df[col_map["Our Mid"]].to_numpy(dtype=float)
	x_ohi = df[col_map["Our High"]].to_numpy(dtype=float)

	mask_both = np.isfinite(x_olo) & np.isfinite(x_ohi)
	if mask_both.any():
		_range_with_end_dots(
			ax,
			x_olo[mask_both],
			x_ohi[mask_both],
			y_our[mask_both],
			colors["Our Study"],
			"Our study (low–high)",
			linewidth=3.5,
			dotsize=55,
		)

	mask_mid = np.isfinite(x_omid)
	if mask_mid.any():
		_scatter_points(
			ax,
			x_omid[mask_mid],
			y_our[mask_mid],
			colors["Our Study"],
			"Our study (midpoint)",
			size=85,
		)

	def plot_single_series(series_name, col_name, slot_name, size=50):
		xv = df[col_name].to_numpy(dtype=float)
		mask = np.isfinite(xv)
		if not mask.any():
			return
		slot_idx = study_slots.index(slot_name)
		yy = np.array([y_for(i, slot_idx) for i in range(n_projects)], dtype=float)
		ax.scatter(xv[mask], yy[mask], color=colors[series_name], s=size, zorder=3, label=series_name)

	def plot_range_series(series_name, lo_col, hi_col, slot_name, linewidth=2.2, dotsize=26):
		x_lo = df[lo_col].to_numpy(dtype=float)
		x_hi = df[hi_col].to_numpy(dtype=float)
		mask = np.isfinite(x_lo) & np.isfinite(x_hi)
		if not mask.any():
			return
		slot_idx = study_slots.index(slot_name)
		yy = np.array([y_for(i, slot_idx) for i in range(n_projects)], dtype=float)
		_range_with_end_dots(
			ax,
			x_lo[mask],
			x_hi[mask],
			yy[mask],
			colors[series_name],
			f"{series_name} (range)",
			linewidth=linewidth,
			dotsize=dotsize,
		)

	# Literature series
	plot_single_series("Pieseler et al. 2024", col_map["Pieseler 2024"], "Pieseler et al. 2024", size=50)
	plot_range_series("Kelly et al. 2021", col_map["Kelly Low"], col_map["Kelly High"], "Kelly et al. 2021", linewidth=2.2, dotsize=26)
	plot_range_series("Iyer and Kelly 2024", col_map["IyerKelly Low"], col_map["IyerKelly High"], "Iyer and Kelly 2024", linewidth=2.2, dotsize=26)
	plot_single_series("Mousavinezhad et al. 2025", col_map["Mousavinezhad 2025"], "Mousavinezhad et al. 2025", size=55)
	plot_single_series("Mousavinezhad et al. 2024", col_map["Mousavinezhad 2024"], "Mousavinezhad et al. 2024", size=50)
	plot_single_series("Sun et al. 2025", col_map["Sun 2025"], "Sun et al. 2025", size=50)
	plot_single_series("Khakmardan et al. 2024", col_map["Khakmardan 2024"], "Khakmardan et al. 2024", size=50)
	plot_single_series("Roy et al. 2024", col_map["Roy 2024"], "Roy et al. 2024", size=50)
	plot_single_series("Liu et al. 2025", col_map["Liu 2025"], "Liu et al. 2025", size=50)
	plot_single_series("Schenker and Pfister 2025", col_map["SchenkerPfister 2025"], "Schenker and Pfister 2025", size=50)
	plot_range_series("Manjong et al. 2021", col_map["Manjong Low"], col_map["Manjong High"], "Manjong et al. 2021", linewidth=2.2, dotsize=26)

	# -------------------------
	# Ambrose & Kendall combined: one error bar (min..max) + three dots
	# Dots correspond to: High Grade, Low Grade, Low Grade Unfavorable
	# -------------------------
	slot_ak = study_slots.index("Ambrose and Kendall 2020b")
	y_ak = np.array([y_for(i, slot_ak) for i in range(n_projects)], dtype=float)

	x_hg = df[col_map["Ambrose High Grade"]].to_numpy(dtype=float)
	x_lg = df[col_map["Ambrose Low Grade"]].to_numpy(dtype=float)
	x_unf = df[col_map["Ambrose Low Grade Unfavorable"]].to_numpy(dtype=float)

	stack = np.vstack([x_hg, x_lg, x_unf])
	mask_any = np.isfinite(stack).any(axis=0)
	if mask_any.any():
		x_min = np.nanmin(stack[:, mask_any], axis=0)
		x_max = np.nanmax(stack[:, mask_any], axis=0)

		_range_with_end_dots(
			ax,
			x_min,
			x_max,
			y_ak[mask_any],
			colors["Ambrose and Kendall 2020b"],
			"Ambrose & Kendall 2020b",
			linewidth=2.2,
			dotsize=26,
		)

		# Three dots (same y); note ordering HG/LG/Unfavorable
		mask_hg = np.isfinite(x_hg)
		if mask_hg.any():
			ax.scatter(x_hg[mask_hg], y_ak[mask_hg], color=colors["Ambrose and Kendall 2020b"], s=46, zorder=5)

		mask_lg = np.isfinite(x_lg)
		if mask_lg.any():
			ax.scatter(x_lg[mask_lg], y_ak[mask_lg], color=colors["Ambrose and Kendall 2020b"], s=36, zorder=5)

		mask_unf = np.isfinite(x_unf)
		if mask_unf.any():
			ax.scatter(x_unf[mask_unf], y_ak[mask_unf], color=colors["Ambrose and Kendall 2020b"], s=28, zorder=5)

		# Dummy legend entries to communicate dot mapping without cluttering the plot
		ax.scatter([], [], color=colors["Ambrose and Kendall 2020b"], s=46, label="A&K dot: High grade")
		ax.scatter([], [], color=colors["Ambrose and Kendall 2020b"], s=36, label="A&K dot: Low grade")
		ax.scatter([], [], color=colors["Ambrose and Kendall 2020b"], s=28, label="A&K dot: Low grade (unfav)")

	ax.set_yticks(y_tick_pos)
	ax.set_yticklabels(projects)
	ax.set_ylim(y_for(n_projects - 1, slots_per_project - 1) + 0.15, y_for(0, 0) - 0.15)

	ax.set_xlabel(value_label)
	ax.set_title(title)
	ax.set_xlim(left=xmin)
	ax.grid(True, axis="x", linestyle=":", alpha=0.4)

	handles, labels = ax.get_legend_handles_labels()
	seen = set()
	uniq_h = []
	uniq_l = []
	for h, l in zip(handles, labels):
		if l not in seen:
			seen.add(l)
			uniq_h.append(h)
			uniq_l.append(l)

	ax.legend(uniq_h, uniq_l, loc=legend_loc, bbox_to_anchor=legend_bbox)

	plt.tight_layout()
	if save_path is not None:
		plt.savefig(save_path, dpi=300, bbox_inches="tight")
	plt.show()

	return fig

# Example:
plot_project_reported_emissions("reported_emissions.csv")
# plot_project_reported_emissions("reported_emissions.csv", save_path="emissions_compare")










