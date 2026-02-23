import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def parse_currency_to_float(x):
	# Parses values like "$3,325", "7,390.00", "", None into float or NaN
	if x is None:
		return np.nan
	s = str(x).strip()
	if s == "" or s.lower() in {"na", "n/a", "null", "-"}:
		return np.nan
	s = s.replace("$", "").replace(",", "")
	try:
		return float(s)
	except ValueError:
		return np.nan

def plot_project_reported_costs(
	csv_path: str,
	value_label: str = "Reported ($/t LCE)",
	title: str = "Reported costs by project",
	figsize=(12, 8),
	save_path: str | None = None,
	add_separators: bool = True,
):
	df = pd.read_csv(csv_path)

	col_map = {
		"Material": "Material",
		"Disclosure": "Disclosure-Reported Cost",
		"Refine Low": "With Spodumene Refining (Low estimate)",
		"Refine High": "With Spodumene Refining (High estimate)",
		"Fleming Lower": "Fleming et al. 2024 - Lower Range",
		"Fleming Upper": "Fleming et al. 2024 - Upper Range",
		"Wesselkamper": "Wesselkamper et al. 2025",
		"Mousavinezhad": "Mousavinezhad et al. 2025",
		"Our Low": "Our Study-Low",
		"Our Mid": "Our Study-Midpoint",
		"Our High": "Our Study-High",
	}

	for k, c in col_map.items():
		if c in df.columns:
			if k == "Material":
				df[c] = df[c].astype(str)
			else:
				df[c] = df[c].map(parse_currency_to_float)

	# Only keep rows where data from 'Our Study' exists
	mask_our = (
		df[col_map["Our Low"]].notna()
		| df[col_map["Our Mid"]].notna()
		| df[col_map["Our High"]].notna()
	)
	df = df.loc[mask_our].copy()
	if df.empty:
		raise ValueError("No rows have 'Our Study' data.")

	df["ProjectLabel"] = df["Project"] + " (" + df["Material"] + ")"

	offsets = {
		"Our Study": 0.12,
		"Disclosure": 0.05,
		"Fleming et al. 2024": 0.00,
		"Wesselkamper et al. 2025": -0.05,
		"Mousavinezhad et al. 2025": -0.10,
	}

	colors = {
		"Our Study": "#000000",					# black
		"Disclosure": "#d62728",				# red
		"Fleming et al. 2024": "#ffa500",		# orange
		"Wesselkamper et al. 2025": "#2ca02c",	# green
		"Mousavinezhad et al. 2025": "#1f77b4",	# blue
	}

	def _range_with_end_dots(ax, x_lo, x_hi, yv, color, label, linewidth, dotsize):
		ax.hlines(yv, x_lo, x_hi, color=color, linewidth=linewidth, zorder=2)
		ax.scatter(x_lo, yv, color=color, s=dotsize, zorder=4)
		ax.scatter(x_hi, yv, color=color, s=dotsize, zorder=4)
		ax.plot([], [], color=color, linewidth=linewidth, label=label)

	fig, ax = plt.subplots(figsize=figsize)

	projects = df["ProjectLabel"].astype(str).tolist()
	y = np.arange(len(projects))

	if add_separators and len(projects) > 1:
		for i in range(len(projects) - 1):
			ax.axhline(i + 0.5, linewidth=0.6, alpha=0.25)

	# =========================
	# OUR STUDY (BLACK)
	# =========================
	x_olo = df[col_map["Our Low"]].to_numpy(dtype=float)
	x_omid = df[col_map["Our Mid"]].to_numpy(dtype=float)
	x_ohi = df[col_map["Our High"]].to_numpy(dtype=float)

	has_lo = np.isfinite(x_olo)
	has_hi = np.isfinite(x_ohi)
	has_mid = np.isfinite(x_omid)

	mask_both = has_lo & has_hi
	if mask_both.any():
		yy = y[mask_both] + offsets["Our Study"]
		_range_with_end_dots(
			ax,
			x_olo[mask_both],
			x_ohi[mask_both],
			yy,
			colors["Our Study"],
			"Our study (low–high) [TEMPORARY]",
			linewidth=3.5,
			dotsize=45,
		)

	# MIDPOINT (always shown if exists)
	mask_mid = has_mid
	if mask_mid.any():
		ax.scatter(
			x_omid[mask_mid],
			y[mask_mid] + offsets["Our Study"],
			color=colors["Our Study"],
			s=70,
			zorder=5,
			label="Our study (midpoint) [TEMPORARY]",
		)

	# =========================
	# DISCLOSURE 
	# =========================
	x_disc = df[col_map["Disclosure"]].to_numpy(dtype=float)
	mask_disc = np.isfinite(x_disc)
	ax.scatter(
		x_disc[mask_disc],
		y[mask_disc] + offsets["Disclosure"],
		color=colors["Disclosure"],
		label="Disclosure-reported cost",
		zorder=3,
	)

	# =========================
	# FLEMING (RANGE ONLY, NO MIDPOINT)
	# =========================
	x_flo = df[col_map["Fleming Lower"]].to_numpy(dtype=float)
	x_fhi = df[col_map["Fleming Upper"]].to_numpy(dtype=float)
	mask_f = np.isfinite(x_flo) & np.isfinite(x_fhi)

	if mask_f.any():
		yy = y[mask_f] + offsets["Fleming et al. 2024"]
		_range_with_end_dots(
			ax,
			x_flo[mask_f],
			x_fhi[mask_f],
			yy,
			colors["Fleming et al. 2024"],
			"Fleming et al. 2024 (range)",
			linewidth=2.0,
			dotsize=22,
		)

	# =========================
	# WESSELKAMPER
	# =========================
	x_w = df[col_map["Wesselkamper"]].to_numpy(dtype=float)
	mask = np.isfinite(x_w)
	ax.scatter(
		x_w[mask],
		y[mask] + offsets["Wesselkamper et al. 2025"],
		color=colors["Wesselkamper et al. 2025"],
		label="Wesselkamper et al. 2025",
		zorder=3,
	)

	# =========================
	# MOUSAVINEZHAD (BLUE)
	# =========================
	x_m = df[col_map["Mousavinezhad"]].to_numpy(dtype=float)
	mask = np.isfinite(x_m)
	ax.scatter(
		x_m[mask],
		y[mask] + offsets["Mousavinezhad et al. 2025"],
		color=colors["Mousavinezhad et al. 2025"],
		label="Mousavinezhad et al. 2025",
		zorder=3,
	)

	ax.set_yticks(y)
	ax.set_ylim(len(projects) - 0.5, -0.5)
	ax.set_yticklabels(projects)
	ax.invert_yaxis()

	ax.set_xlabel(value_label)
	ax.set_xlim(left=0)
	ax.set_title(title)
	ax.grid(True, axis="x", linestyle=":", alpha=0.4)

	# Clean legend
	handles, labels = ax.get_legend_handles_labels()
	seen = set()
	uniq_h = []
	uniq_l = []
	for h, l in zip(handles, labels):
		if l not in seen:
			seen.add(l)
			uniq_h.append(h)
			uniq_l.append(l)

	ax.legend(uniq_h, uniq_l, loc="center left", bbox_to_anchor=(1.02, 0.5))
	plt.tight_layout()
	plt.show()

	return fig

plot_project_reported_costs("reported_costs.csv")
# plot_project_reported_costs("reported_costs.csv", add_separators=True, facet=False, save_path="reported_costs")
# plot_project_reported_costs("reported_costs.csv", facet=True, facet_cols=3)

# Adapt to add error bars
# Adapt to also plot emissions comparison 







