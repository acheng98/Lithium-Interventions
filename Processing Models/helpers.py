from typing import Dict, Any, List, Optional
import numpy as np
import matplotlib.pyplot as plt
import textwrap
import re

# robust helpers
def safe_float(x, default=0.0):
	try:
		if x is None or x == "":
			return default
		return float(x)
	except (TypeError, ValueError):
		return default

def safe_bool(x, default=False):
	if x is None:
		return default
	if isinstance(x, bool):
		return x
	s = str(x).strip().lower()
	if s in {"true", "t", "yes", "y"}:
		return True
	if s in {"false", "f", "no", "n"}:
		return False
	return default

def _parse_numeric(cell):
	"""
	Parse a CSV cell into float. Handles $, commas, parentheses-negative, %, sci-notation.
	Returns (value, is_percent_flag) where value is float or None if blank.
	Raises ValueError if non-numeric, non-blank content remains.
	"""
	if cell is None:
		return None

	s = str(cell).strip()
	if s == "" or s.lower() in {"na", "n/a", "null"}:
		return None

	# Handle negative in parentheses (e.g., (1,234))
	is_negative = s.startswith("(") and s.endswith(")")
	if is_negative:
		s = s[1:-1].strip()

	# Remove currency symbols and commas
	s = s.replace("$", "").replace(",", "")
	has_percent = s.endswith("%")
	if has_percent:
		s = s[:-1].strip()

	# Try parsing as float
	try:
		val = float(s)
	except ValueError:
		return None

	if is_negative:
		val = -val
	if has_percent:
		val /= 100.0

	return val

# Split delimiter-separated strings into a typed list.
def parse_list_field(val: str, delim =";", cast=str) -> List[Any]:
	if not val or val.strip() == "":
		return []
	return [cast(x.strip()) for x in val.split(delim)]

# building functions
def build_steps_dict(input_data: List[List[str]]) -> Dict[str, Dict[str, str]]:
	"""
	Pivot the row-oriented CSV-style data into step-oriented dicts.
	input_data: list of lists, first row is step headers, first column is variable names
	Returns dict mapping step_id → {varname: value}
	"""
	header = [head for head in input_data[0][2:] if len(head) > 1]  # step IDs/names - start at 2 because first two rows are var_names and description; get rid of columns without any text
	rows = input_data[1:]       # all rows except header

	steps_dict = {step: {} for step in header}
	for row in rows:
		varname = row[0]
		description = row[1] # Human readable description for each variable. Probably not needed in code
		values = row[2:]
		for step, val in zip(header, values):
			steps_dict[step][varname] = val
	return steps_dict


def build_material_flows(step_vars: Dict[str, str]) -> Dict[str, Any]:
	"""
	Construct material flows (inputs, outputs, reagents, coproducts) from parsed step variables.
	This is outside of the ProductionStep class but called within the ProductionStep class, which is a bit improper but OK for now
	"""
	material_flows = {
		"primary_inputs": {},
		"secondary_inputs": {},
		"primary_outputs": {},
		"secondary_outputs": {}
	}

	# Primary inputs
	i = 1
	while f"primary_input_{i}_name" in step_vars:
		in_name = step_vars.get(f"primary_input_{i}_name")
		if not in_name: # Assumes that inputs are listed in order, e.g. no skipping from 1 to 3
			break
		constituents = parse_list_field(step_vars.get(f"primary_input_{i}_constituents", ""))
		chemistry_dependence = str(step_vars.get(f"primary_input_{i}_chemistry_dependence", "False")).strip().lower() in ("true", "yes", "1") # All strings always return as TRUE
		fractions = parse_list_field(step_vars.get(f"primary_input_{i}_constituent_fractions", ""), cast=float)
		if chemistry_dependence or len(fractions) == 0: # If not dependent on chemistry, we take the prescribed constituent fractions
			fractions = [""]*len(constituents)
		material_flows["primary_inputs"][in_name] = {
			"constituents": dict(zip(constituents, fractions)),
			"units": step_vars.get(f"primary_input_{i}_constituent_units"),
			"conversion_factor": float(step_vars.get(f"primary_input_{i}_conversion_factor", 1.0)),
			"chemistry_dependence": chemistry_dependence,
		}
		i += 1

	# Reagents
	i = 1
	while f"reagent_{i}_name" in step_vars:
		r_name = step_vars.get(f"reagent_{i}_name")
		if not r_name:
			break
		targets = parse_list_field(step_vars.get(f"reagent_{i}_target_constituents", ""))
		ratios = parse_list_field(step_vars.get(f"reagent_{i}_constituent_ratio", ""), cast=float)
		eliminated = parse_list_field(step_vars.get(f"reagent_{i}_target_constituents_eliminated", ""), cast=float)
		material_flows["secondary_inputs"][r_name] = {
			"name_long": step_vars.get(f"reagent_{i}_name_long"),
			# Usage and total cost to be calculated later
			"targets": dict(zip(targets, [{"ratio": r, "elim": e, "usage": 0, "abs_usage": 0, "total_cost": 0} for r, e in zip(ratios, eliminated)])),
			"units": step_vars.get(f"reagent_{i}_units"),
		}
		i += 1

	# Primary outputs
	i = 1
	while f"primary_output_{i}_name" in step_vars:
		out_name = step_vars.get(f"primary_output_{i}_name")
		if not out_name:
			break
		constituents = parse_list_field(step_vars.get(f"primary_output_{i}_constituents", ""))
		fractions = parse_list_field(step_vars.get(f"primary_output_{i}_constituent_fractions", ""), cast=float)
		chemistry_dependence = str(step_vars.get(f"primary_output_{i}_chemistry_dependence", "False")).strip().lower() in ("true", "yes", "1") # All strings always return as TRUE
		if len(fractions) == 0: # If constituent fractions not defined, they must be calculated from a defined chemistry
			fractions = [""]*len(constituents)
		material_flows["primary_outputs"][out_name] = {
			"next_step": step_vars.get(f"primary_output_{i}_step"),
			"yield_rate": float(step_vars.get(f"primary_output_{i}_yield_rate", 1.0)),
			"units": step_vars.get(f"primary_output_{i}_units"),
			"constituents": dict(zip(constituents, fractions)),
			"chemistry_dependence": chemistry_dependence,
		}
		i += 1

	# Co-products
	i = 1
	while f"coproduct_{i}_name" in step_vars:
		co_name = step_vars.get(f"coproduct_{i}_name")
		if not co_name:
			break
		constituents = parse_list_field(step_vars.get(f"coproduct_{i}_constituents", ""))
		fractions = parse_list_field(step_vars.get(f"coproduct_{i}_constituent_fractions", ""), cast=float)
		if len(fractions) == 0: # If constituent fractions not defined, they must be calculated from a defined chemistry
			fractions = [""]*len(constituents)
		material_flows["secondary_outputs"][co_name] = {
			"sink": step_vars.get(f"coproduct_{i}_sink"),
			"conversion_factor": float(step_vars.get(f"coproduct_{i}_conversion_factor", 1.0)),
			"units": step_vars.get(f"coproduct_{i}_units"),
			"constituents": dict(zip(constituents, fractions)),
		}
		i += 1

	return material_flows

def build_locations_dict(locational_data: List[List[str]]) -> Dict[str, Any]:
	"""
	"""
	header = locational_data[0]
	location_names = [str(h).strip() for h in header[3:]]
	locations_dict = {loc: {} for loc in location_names}

	for row in locational_data[1:]:
		if not row or len(row) < 4:
			continue

		var_name = str(row[0]).strip()
		if not var_name:
			continue

		values = row[3:]

		# Handle impact_factors rows
		if var_name.startswith("impact_factor."):
			parts = [p.strip() for p in var_name.split(".")]
			if len(parts) != 3:
				continue  # ignore malformed rows

			_, utility, category = parts
			for loc, raw in zip(location_names, values):
				val = _parse_numeric(raw)
				if val is None:
					continue
				loc_dict = locations_dict[loc]
				loc_dict.setdefault("impact_factors", {}).setdefault(utility, {})[category] = val

		# Handle flat variable rows
		else:
			for loc, raw in zip(location_names, values):
				val = _parse_numeric(raw)
				if val is None:
					continue
				locations_dict[loc][var_name] = val

	return locations_dict


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

def plot_breakdown(labels, variable_costs, fixed_costs,
					xscale=1, yscale=1, title='Cost of Steps', xlab='Step Names', ylab='Total Cost', 
					xlims=None, ylims=None, fixed_width=None, base_width_per_bar=0.5, show=True):
	labels = list(labels)
	v = np.asarray(variable_costs, dtype=float) * yscale
	f = np.asarray(fixed_costs, dtype=float) * yscale
	n = len(labels)

	# Compute figure width dynamically or use fixed width
	if fixed_width is not None:
		fig_width = fixed_width
	else:
		# Adaptive width so bars are never cramped or overly spaced
		fig_width = 2 * min(max(6, n * base_width_per_bar), 14)

	fig, ax = plt.subplots(figsize=(fig_width, 6))

	# X positions for bars
	x = np.arange(n)

	# Plot stacked bars
	ax.bar(x, fixed_costs, label="Fixed Cost", color="#f28e2b")
	ax.bar(x, variable_costs, bottom=fixed_costs, label="Variable Cost", color="#4e79a7")
	
	# Label formatting
	ax.set_xticks(x)
	ax.set_xticklabels(_wrap_labels(labels, width=12), ha='center')

	# Labels and title
	ax.set_xlabel(xlab)
	ax.set_ylabel(ylab)
	ax.set_title(title, pad=12)

	# Add light grid and legend
	ax.grid(axis='y', linestyle=':', alpha=0.4)

	# Optional limits
	if xlims is not None:
		ax.set_xlim(xlims)
	if ylims is not None:
		ax.set_ylim(ylims)

	handles, labels_ = ax.get_legend_handles_labels()
	order = [labels_.index("Variable Cost"), labels_.index("Fixed Cost")]
	ax.legend([handles[i] for i in order], [labels_[i] for i in order], 
			frameon=True, loc='upper right', handlelength=1.2, handletextpad=0.4, borderpad=0.3, 
			facecolor='white', edgecolor='none')

	plt.tight_layout()
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






















