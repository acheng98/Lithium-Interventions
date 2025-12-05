from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import textwrap
import re
from collections import defaultdict

# robust helpers
def load_csv(name):
    return pd.read_csv(f"{name}.csv", dtype=str).fillna("")

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

def parse_numeric(cell):
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

def parse_transport_string(s: str):
	"""
	Parse a transport string of the form:
		"truck: 250; barge: 1000; truck: 400"
	into:
		[("truck", 250.0), ("barge", 1000.0), ("truck", 400.0)]
	Raises ValueError on bad formatting.
	"""
	if not isinstance(s, str):
		raise ValueError("Input must be a string.")
	elif len(s) == 0:
		return []

	results = []

	# Split by semicolon into segments
	for segment in s.split(";"):
		segment = segment.strip()
		if not segment:
			continue  # skip empty segments

		# Expect "key: value"
		if ":" not in segment:
			raise ValueError(f"Invalid segment (missing colon): '{segment}'")

		key, value = map(str.strip, segment.split(":", 1))

		if not key:
			raise ValueError(f"Missing transport mode before colon in segment: '{segment}'")

		# Convert value to float
		try:
			amount = float(value)
		except ValueError:
			raise ValueError(f"Invalid numeric value '{value}' in segment: '{segment}'")

		results.append((key, amount))
	return results	

# building functions
def build_steps_dict(input_data_df) -> Dict[str, Dict[str, str]]:
	"""
	Pivot the row-oriented CSV-style data into step-oriented dicts.
	input_data: list of lists, first row is step headers, first column is variable names, second column is description
	Returns dict mapping step_id → {varname: value}
	"""
	# Convert the DataFrame into list of lists, with header row first
	header_id = list(input_data_df.columns)
	rows_id = input_data_df.values.tolist()
	input_data = [header_id] + rows_id

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
		# If dependent on chemistry or not specified, create row of empty values. Otherwise, take the prescribed constituent fractions
		if chemistry_dependence or len(fractions) == 0: 
			fractions = [""]*len(constituents)
		material_flows["primary_inputs"][in_name] = {
			"constituents": dict(zip(constituents, fractions)),
			"units": step_vars.get(f"primary_input_{i}_constituent_units"),
			"conversion_factor": float(step_vars.get(f"primary_input_{i}_conversion_factor", 1.0)),
			"chemistry_dependence": chemistry_dependence,
			"input_needed": 0,
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
			"conversion_factor": float(step_vars.get(f"primary_output_{i}_conversion_factor", 1.0)),
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
				val = parse_numeric(raw)
				if val is None:
					continue
				loc_dict = locations_dict[loc]
				loc_dict.setdefault("impact_factors", {}).setdefault(utility, {})[category] = val

		# Handle flat variable rows
		else:
			for loc, raw in zip(location_names, values):
				val = parse_numeric(raw)
				if val is None:
					continue
				locations_dict[loc][var_name] = val

	return locations_dict

def build_projects_dict(df):
	"""
	Convert a pandas DataFrame of project inputs into a dict-of-dicts.

	Behavior:
		- First column is used as the project key (e.g., "Project Name").
		- For each column value:
			* Try parse_numeric → float if successful
			* Try safe_bool on true/false-like strings
			* Else store cleaned string or None

	Returns:
		{ project_key : { column_name : typed_value, ... }, ... }
	"""
	if df is None or df.empty:
		return {}

	# Identify the key column (first column in the CSV)
	key_col = df.columns[0] # project name
	key_values = df[key_col].astype(str).str.strip()

	project_dict = {}

	for idx, key in key_values.items():
		if key == "" or key.lower() in {"nan", "none"}:
			continue

		row = df.loc[idx]
		entry = {}

		for col in df.columns[1:]:
			cell = row[col]

			# Convert NaN or None to python None early
			if pd.isna(cell):
				entry[col] = None
				continue

			cell_str = str(cell).strip()

			# 1) Try numeric parse
			num_val = parse_numeric(cell_str)
			if num_val is not None:
				entry[col] = num_val
				continue

			# 2) Try boolean
			if cell_str.lower() in {"true", "t", "yes", "y", "false", "f", "no", "n"}:
				entry[col] = safe_bool(cell_str)
				continue

			# 3) Fallback to cleaned string or None
			if cell_str == "" or cell_str.lower() in {"na", "n/a", "null", "-"}:
				entry[col] = None
			else:
				entry[col] = cell_str

		project_dict[key] = entry

	return project_dict


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

	import numpy as np
	import matplotlib.pyplot as plt

def plot_stacked_bars(labels, series_dict, *, 
	stack_order=None,                 # list of series labels from bottom -> top
	colors=None,                      # dict like {"Fixed": "#f28e2b", "Variable": "#4e79a7"}
	xscale=1, yscale=1,
	title='Cost of Steps',xlab='Step Names',ylab='Total',
	xlims=None, ylims=None,
	fixed_width=None,base_width_per_bar=0.5,
	legend_order='top_to_bottom',     # 'top_to_bottom' or 'bottom_to_top'
	legend_loc='upper right',
	wrap_width=12,
	show=True,
	):
	"""
	labels: sequence of category names (x-axis)
	series_dict: {series_label: iterable of values}, all same length as labels
	stack_order: explicit order bottom->top; defaults to insertion/key order of series_dict
	colors: optional color mapping per series label
	legend_order: 'top_to_bottom' mirrors the visible stack; 'bottom_to_top' follows stacking order
	"""

	labels = list(labels)
	n = len(labels)

	print(series_dict.items())

	# Validate and scale data
	data = {}
	for k, vals in series_dict.items():
		arr = np.asarray(vals, dtype=float)
		if arr.shape[0] != n:
			raise ValueError(f"Series '{k}' length {arr.shape[0]} != number of labels {n}.")
		data[k] = arr * yscale

	# Determine stacking order (bottom -> top)
	if stack_order is None:
		# Preserve dict insertion order (Python 3.7+)
		order = list(series_dict.keys())
	else:
		# Validate provided order
		missing = set(series_dict.keys()) - set(stack_order)
		extra = set(stack_order) - set(series_dict.keys())
		if missing:
			raise ValueError(f"stack_order missing series: {sorted(missing)}")
		if extra:
			raise ValueError(f"stack_order has unknown series: {sorted(extra)}")
		order = list(stack_order)

	# Figure width
	if fixed_width is not None:
		fig_width = fixed_width
	else:
		fig_width = 2 * min(max(6, n * base_width_per_bar * max(xscale, 0.01)), 14)

	fig, ax = plt.subplots(figsize=(fig_width, 6))

	# X positions
	x = np.arange(n)

	# Plot bottom-up
	running_bottom = np.zeros(n, dtype=float)
	handle_map = {}
	for name in order:
		h = ax.bar(
			x, data[name], bottom=running_bottom,
			label=name,
			color=(colors.get(name) if colors and name in colors else None)
		)
		handle_map[name] = h
		running_bottom += data[name]

	# Ticks (uses your _wrap_labels if present, else raw labels)
	try:
		tick_labels = _wrap_labels(labels, width=wrap_width)  # noqa: F821 (assumes you already have this)
	except NameError:
		# Fallback: naive wrap
		def _simple_wrap(s, width):
			return '\n'.join([s[i:i+width] for i in range(0, len(s), width)]) if len(s) > width else s
		tick_labels = [_simple_wrap(str(s), wrap_width) for s in labels]

	ax.set_xticks(x)
	ax.set_xticklabels(tick_labels, ha='center')

	# Labels and title
	ax.set_xlabel(xlab)
	ax.set_ylabel(ylab)
	ax.set_title(title, pad=12)

	# Grid
	ax.grid(axis='y', linestyle=':', alpha=0.4)

	# Limits
	if xlims is not None:
		ax.set_xlim(xlims)
	if ylims is not None:
		ax.set_ylim(ylims)

	# Legend that mirrors the visible stack (top first) or the stacking order (bottom first)
	if legend_order not in ('top_to_bottom', 'bottom_to_top'):
		raise ValueError("legend_order must be 'top_to_bottom' or 'bottom_to_top'")

	legend_labels = (order[::-1] if legend_order == 'top_to_bottom' else order)
	legend_handles = [handle_map[name] for name in legend_labels]
	ax.legend(
		legend_handles, legend_labels,
		frameon=True, loc=legend_loc, handlelength=1.2, handletextpad=0.4, borderpad=0.3,
		facecolor='white', edgecolor='none'
	)

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






















