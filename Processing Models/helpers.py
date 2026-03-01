from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import csv
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import textwrap
import re
from collections import defaultdict

def safe_float(x, default=0.0):
	try:
		if x is None or x == "":
			return float(default)
		return float(x)
	except (TypeError, ValueError):
		return float(default)

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

def parse_keystring(s, key_delim=":"):
	k, v = (x.strip() for x in s.split(key_delim, 1))
	if not k:
		raise ValueError(f"Missing key before '{key_delim}' in segment: '{s}'")
	
	v_num = parse_numeric(v)
	v = v if v_num is None else v_num
	return {k: v}

def parse_keylist_string(s: str, list_delim=";", key_delim=":", on_dup="accumulate"): # "error", "overwrite", "accumulate"
	"""
	Parse a strings of the form:
		"Li; Ca; Mg"
		"truck: 250; barge: 1000; truck: 400"
		"truck: 500"
	into:
		["Li","Ca","Mg"]
		{"truck": 250.0, "barge": 1000.0, "truck", 400.0}
		{"truck": 500.0}
	Raises ValueError on bad formatting.
	"""
	if s is None:
		return s
	if not isinstance(s, str):
		raise ValueError("Input must be a string.")

	s = s.strip()
	if not s:
		return None

	has_list = list_delim in s
	has_key  = key_delim in s

	# If it's not a list (no list_delim), it can still be a single keyed entry.
	if not has_list:
		if not has_key: # If no list or key, single entry. Single entries should have been handled by clean_input_str already 
			return None
		return parse_keystring(s, key_delim=key_delim) # single keyed segment

	parts = [p.strip() for p in s.split(list_delim) if p.strip()] # Split with delimiter
	if not parts:
		return None

	# Simple list
	if not has_key:
		out = []
		for p in parts:
			p_num = parse_numeric(p)
			out.append(p if p_num is None else p_num)
		return out

	# Keyed list (enforce consistency) - no mixed keyed/non-keyed segments
	if any(key_delim not in p for p in parts):
		bad = next(p for p in parts if key_delim not in p)
		raise ValueError(f"Mixed keyed and non-keyed segment: '{bad}'")

	# Else keyed list
	out = {}
	for p in parts:
		kv = parse_keystring(p, key_delim=key_delim)  # {k: v}
		(k, v), = kv.items()

		if k not in out:
			out[k] = v
			continue

		# Duplicate key handling
		if on_dup == "error":
			raise ValueError(f"Duplicate key '{k}' in keyed list: '{s}'")
		elif on_dup == "overwrite":
			out[k] = v
		elif on_dup == "accumulate":
			out[k] += v
		else:
			raise ValueError(f"Invalid on_dup={on_dup!r}; use 'error', 'overwrite', or 'accumulate'.")

	return out

def clean_input_str(cell_str, list_delim=";", key_delim=":"):
	cell_str = str(cell_str).strip()

	# 0) Empty string
	if cell_str == "" or cell_str.lower() in {"na", "n/a", "null", "-"}:
		return None

	# 1) Try numeric parse
	num_val = parse_numeric(cell_str)
	if num_val is not None:
		return num_val

	# 2) Try boolean
	if cell_str.lower() in {"true", "t", "yes", "y", "false", "f", "no", "n"}:
		return safe_bool(cell_str)

	# 3) Try parsing as a list
	output = parse_keylist_string(cell_str, list_delim, key_delim)
	if output is not None:
		return output

	# 4) Fallback to cleaned string
	return cell_str

def ensure_list(val, cast=str, delim=";"):
	if val is None:
		return []

	# Already list/tuple: cast elements
	if isinstance(val, (list, tuple)):
		out = []
		for x in val:
			if x is None or x == "":
				continue
			# If cast is float, allow numbers to pass through
			if cast is float and isinstance(x, (int, float)):
				out.append(float(x))
			else:
				out.append(cast(str(x).strip()) if not isinstance(x, (int, float)) else cast(x))
		return out

	# String: split + cast
	if isinstance(val, str):
		s = val.strip()
		if s == "":
			return []
		return [cast(x.strip()) for x in s.split(delim) if x.strip()]

	# Scalar: wrap
	if cast is float and isinstance(val, (int, float)):
		return [float(val)]
	return [cast(val)]

def format_currency(x):
	# Formats numeric to "$#,###" (rounded to nearest dollar)
	if x is None:
		return ""
	try:
		v = float(x)
	except Exception:
		return ""
	return f"${v:,.0f}"

def build_constituent_dict(constituents, fractions=None):
	"""
	Returns dict: { constituent : fraction }
	Fractions may be missing or empty.
	"""
	if not constituents:
		return {}

	if isinstance(constituents, str):
		clean_consts = clean_input_str(constituents)
		if not isinstance(clean_consts, list) and isinstance(clean_consts,str):
			clean_consts = [clean_consts]
	elif isinstance(constituents, list):
		clean_consts = constituents
	else:
		raise ValueError

	if isinstance(fractions, str):
		clean_fracs = clean_input_str(fractions)
	elif isinstance(fractions, list):
		clean_fracs = fractions
	elif isinstance(fractions,float): # singular float value
		clean_fracs = [fractions]
	elif fractions == None:
		clean_fracs = [""] * len(constituents)
	else:
		raise ValueError

	return dict(zip(clean_consts, clean_fracs))

def build_data_dict(data_folder,file,col=2,param_split=".",skip_rows=["notes", "sources", "key_equation"]):
	"""
	Returns:
		{ column : { row_name : typed_value, ... }, ... }
	When the row_name includes a rank (e.g. ghg_emissions.low) return a nested dict
		{ column : { row_name : {rank: typed_value, rank: typed_value}, ... }, ... }
	Also, when the value includes a key_split, also return a nested dict
		{ column : { row_name : {key: value, key: value}, ... }, ... }
	"""
	with open(data_folder+file+".csv", newline="") as f:
		reader = csv.DictReader(f)
		inputs_dict = {name: {} for name in reader.fieldnames[col:]} # typically, col=2: 0: variable names, 1: descriptions

		var_col = reader.fieldnames[0]
		for row in reader:
			var = row[var_col]
			if var_col in skip_rows: # skip processing all of the rows in skip_rows
				for column in inputs_dict:
					inputs_dict[column][var] = row[column]
			elif param_split in var:
				var_name,rank = var.split(param_split)
				for column in inputs_dict:
					var_dict = inputs_dict[column].setdefault(var_name,{})
					var_dict[rank] = clean_input_str(row[column])
			else:
				for column in inputs_dict:
					inputs_dict[column][var] = clean_input_str(row[column])
	return inputs_dict

def build_locations_dict(data_folder,file,skip_rows=["notes", "sources", "key_equation"]):
	"""
	Returns:
		{ location : { row_name : typed_value, ... }, ... }
	"""
	with open(data_folder+file+".csv", newline="") as f:
		reader = csv.DictReader(f)

		# 0: variable names, 1: descriptions, 2: units
		location_names = reader.fieldnames[3:]
		locations_dict = {name: {} for name in location_names}

		var_col = reader.fieldnames[0]
		for row in reader:
			var = row.get(var_col, "")
			if not var:
				continue

			# Nested impact factors: impact_factor.<utility>.<category>
			if var.startswith("impact_factor."):
				parts = [p.strip() for p in var.split(".")]
				if len(parts) != 3:
					raise ValueError(f"Invalid impact_factor variable_name: '{var}'")

				_, utility, category = parts

				for loc in location_names:
					val = clean_input_str(row.get(loc))
					if val is None:
						continue
					locations_dict[loc].setdefault("impact_factors", {}).setdefault(utility, {})[category] = val

			# Nested material overrides: material.<material_name>.<category>
			elif var.startswith("material."):
				parts = [p.strip() for p in var.split(".")]
				if len(parts) != 3:
					raise ValueError(f"Invalid material override variable_name: '{var}'")

				_, material, category = parts

				for loc in location_names:
					val = clean_input_str(row.get(loc))
					if val is None:
						continue
					locations_dict[loc].setdefault("material", {}).setdefault(material, {})[category] = val

			# Flat variables
			else:
				for loc in location_names:
					if var_col in skip_rows: # skip processing all of the rows in skip_rows
						locations_dict[loc][var] = row.get(loc)
					else:
						locations_dict[loc][var] = clean_input_str(row.get(loc))

		return locations_dict

def build_facility_dict(data_folder,file,skip_rows=["notes", "sources", "key_equation"]):
	"""
	Returns:
		{ location : { row_name : typed_value, ... }, ... }
	"""
	with open(data_folder+file+".csv", newline="") as f:
		reader = csv.DictReader(f)

		# 0: variable names, 1: descriptions
		step_names = reader.fieldnames[2:]
		steps_dict = {name: {"material_flows": {
			"primary_inputs": {},
			"secondary_inputs": {},
			"primary_outputs": {},
			"secondary_outputs": {},
		}} for name in step_names}

		var_col = reader.fieldnames[0]

		for row in reader:
			var = (row.get(var_col) or "").strip()
			if not var:
				continue

			# ---------- Primary inputs: primary_input_<i>_<field> ----------
			m = re.match(r"^primary_input_(\d+)_(.+)$", var)
			if m:
				i, field = m.group(1), m.group(2)
				for step in step_names:
					val = clean_input_str(row.get(step))
					if val is None:
						continue
					steps_dict[step]["material_flows"]["primary_inputs"].setdefault(i, {})[field] = val
				continue

			# ---------- Reagents: reagent_<i>_<field> ----------
			m = re.match(r"^reagent_(\d+)_(.+)$", var)
			if m:
				i, field = m.group(1), m.group(2)
				for step in step_names:
					val = clean_input_str(row.get(step))
					if val is None:
						continue
					steps_dict[step]["material_flows"]["secondary_inputs"].setdefault(i, {})[field] = val
				continue

			# ---------- Primary outputs: primary_output_<i>_<field> ----------
			m = re.match(r"^primary_output_(\d+)_(.+)$", var)
			if m:
				i, field = m.group(1), m.group(2)
				for step in step_names:
					val = clean_input_str(row.get(step))
					if val is None:
						continue
					steps_dict[step]["material_flows"]["primary_outputs"].setdefault(i, {})[field] = val
				continue

			# ---------- Coproducts: coproduct_<i>_<field> ----------
			m = re.match(r"^coproduct_(\d+)_(.+)$", var)
			if m:
				i, field = m.group(1), m.group(2)
				for step in step_names:
					val = clean_input_str(row.get(step))
					if val is None:
						continue
					steps_dict[step]["material_flows"]["secondary_outputs"].setdefault(i, {})[field] = val
				continue

			# ---------- Flat variables ----------
			for step in step_names:
				if var in skip_rows: # skip processing all of the rows in skip_rows
					steps_dict[step][var] = row.get(step)
				else:
					steps_dict[step][var] = clean_input_str(row.get(step))

		# ------------------ 2) Reorganize in-situ: index-keyed -> name-keyed ------------------
		for step in step_names:
			mf = steps_dict[step]["material_flows"]

			# ---- Primary inputs ----
			raw = mf["primary_inputs"]
			new = {}
			for i, block in list(raw.items()):
				name = block.get("name")
				if not name:
					continue

				new[name] = {
					"constituents": build_constituent_dict(block.get("constituents"), block.get("constituent_fractions")),
					"units": block.get("constituent_units"),
					"conversion_factor": safe_float(block.get("conversion_factor"), default=1.0),
					"chemistry_dependence": safe_bool(block.get("chemistry_dependence", False)),
					"input_needed": 0,
				}
			mf["primary_inputs"] = new

			# ---- Reagents (secondary inputs) ----
			raw = mf["secondary_inputs"]
			new = {}
			for i, block in list(raw.items()):
				name = block.get("name")
				if not name:
					continue

				targets = ensure_list(block.get("target_constituents"), cast=str)
				ratios  = ensure_list(block.get("constituent_ratio"), cast=float)
				elims   = ensure_list(block.get("target_constituents_eliminated"), cast=float)

				new[name] = {
					"name_long": block.get("name_long"),
					"targets": dict(
						(t, {"ratio": r, "elim": e, "usage": 0, "abs_usage": 0, "total_cost": 0})
						for t, r, e in zip(targets, ratios, elims)
					),
					"units": block.get("units"),
				}
			mf["secondary_inputs"] = new

			# ---- Primary outputs ----
			raw = mf["primary_outputs"]
			new = {}
			for i, block in list(raw.items()):
				name = block.get("name")
				if not name:
					continue

				new[name] = {
					"next_step": block.get("step"),
					"yield_rate": safe_float(block.get("yield_rate"), default=1.0),
					"conversion_factor": safe_float(block.get("conversion_factor"), default=1.0),
					"units": block.get("units"),
					"constituents": build_constituent_dict(block.get("constituents"), block.get("constituent_fractions")),
					"chemistry_dependence": safe_bool(block.get("chemistry_dependence", False)),
				}
			mf["primary_outputs"] = new

			# ---- Coproducts (secondary outputs) ----
			raw = mf["secondary_outputs"]
			new = {}
			for i, block in list(raw.items()):
				name = block.get("name")
				if not name:
					continue

				new[name] = {
					"sink": block.get("sink"),
					"conversion_factor": safe_float(block.get("conversion_factor"), default=1.0),
					"units": block.get("units"),
					"constituents": build_constituent_dict(block.get("constituents"), block.get("constituent_fractions")),
				}
			mf["secondary_outputs"] = new

		return steps_dict

# SYSTEM UPDATERS
def update_machines(sc, machine_rank):
	"""Update ProductionStep machine blocks across a SupplyChain to a different rank.
	This relies on sc.get_steps() (which should be safe/topologically ordered).
	Ranked machine blocks follow: <base>.<rank>, e.g. brine_pump.low/high.

	Parameters
	----------
	sc : SupplyChain
	machine_rank : str | dict
		If str: apply that rank to all steps.
		If dict: targeted updates for tornado workflows; supports:
			- (fac_id, step_id) -> rank
			- "machine_base" -> rank   (e.g. "brine_pump" -> "low")
		Steps not matched by the dict are left unchanged.

	Returns
	-------
	dict
		(fac_id, step_id) -> {"old": ..., "new": ..., "rank": ...}
	"""
	def _resolve_rank_key(current_block: str, rank: str) -> str:
		if rank is None or str(rank).strip() == "":
			return current_block

		machine_keys = set(getattr(sc, "machine_data", {}).keys())
		cur = current_block
		base = cur.split(".", 1)[0]
		desired = f"{base}.{rank}"

		# Prefer desired rank if it exists
		if desired in machine_keys:
			return desired

		# If no ranks exist, fall back to base if present
		if base in machine_keys:
			return base

		# If the current key itself exists, keep it
		if cur in machine_keys:
			return cur

		# If other ranks exist, use desired if present else first available ranked option
		ranked = sorted([k for k in machine_keys if k.startswith(base + ".")])
		if ranked:
			return desired if desired in ranked else ranked[0]

		raise KeyError(
			f"No machine_data found for machine '{base}' (from '{cur}'). "
			f"Tried '{desired}', '{base}', and '{cur}'."
		)

	is_dict_spec = isinstance(machine_rank, dict)
	updates = {}

	for step in sc.get_steps(transp=False):
		old_block = getattr(step, "machine_block", None)
		if not old_block:
			continue

		fac_id = getattr(getattr(step, "facility", None), "fac_id", None)
		step_id = getattr(step, "step_id", None)

		# Determine rank for this step
		if not is_dict_spec:
			rank_to_apply = machine_rank
		else:
			tup_key = (fac_id, step_id)
			if tup_key in machine_rank:
				rank_to_apply = machine_rank[tup_key]
			else:
				base = old_block.split(".", 1)[0]
				if base in machine_rank:
					rank_to_apply = machine_rank[base]
				else:
					continue  # dict spec but no match → leave unchanged

		rank_to_apply = str(rank_to_apply).strip()
		new_block = _resolve_rank_key(old_block, rank_to_apply)

		# If step has an allowed-list, enforce it here
		allowed = getattr(step, "machine_blocks", None)
		if allowed:
			if new_block not in allowed:
				# If the desired ranked option isn't allowed, fall back to base if allowed
				base = old_block.split(".", 1)[0]
				if base in allowed:
					new_block = base
				else:
					raise ValueError(
						f"Resolved machine_block '{new_block}' not in step.machine_blocks "
						f"for step '{step_id}' (facility '{fac_id}'). Allowed: {allowed}"
					)

		# Apply + reload if changed
		if new_block != old_block:
			step.load_machine_data(machine_block=new_block)

		updates[(fac_id, step_id)] = {"old": old_block, "new": new_block, "rank": rank_to_apply}
	return updates


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

def plot_project_summaries(
	project_summaries: dict,
	*,
	x_key: str = "avg_var_cost",
	y_key: str = "avg_co2",
	size_key: str = "apv",
	center_scenario: str = "midpoint",
	low_scenario: str = "conservative",
	high_scenario: str = "optimistic",
	project_markers=None,
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
	Plot nested project_summaries dict:
	  project_summaries[project][scenario][metric] -> value

	X: cost_key (default avg_cost)
	Y: co2_key  (default avg_co2)
	Size: size_key (default apv)
	Color: scenario
	Marker: project
	"""

	# ----------------------------
	# 1) Flatten to DataFrame
	# ----------------------------
	rows = []
	for project, scenarios in project_summaries.items():
		for scenario, metrics in scenarios.items():
			rows.append(
				{
					"project": project,
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
	piv = df.pivot_table(index="project", columns="scenario", values=[x_key, y_key, size_key], aggfunc="first")

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
		s_c = df[df["scenario"] == center_scenario].set_index("project")[size_key]
	if s_c.isna().any():
		s_any = (
			df.dropna(subset=[size_key])
			  .drop_duplicates(subset=["project"])
			  .set_index("project")[size_key]
		)
		s_c = s_c.fillna(s_any)

	# Drop projects missing center x/y
	ok = x_c.notna() & y_c.notna()
	x_c, y_c, x_lo, x_hi, y_lo, y_hi, s_c = [v[ok] for v in (x_c, y_c, x_lo, x_hi, y_lo, y_hi, s_c)]

	projects = x_c.index.tolist()

	# ----------------------------
	# 2) Markers and size scaling
	# ----------------------------
	if project_markers is None:
		marker_cycle = ["o", "s", "^", "D", "P", "X", "v", "<", ">", "h", "*"]
		project_markers = {p: marker_cycle[i % len(marker_cycle)] for i, p in enumerate(projects)}

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
	# 5) Plot: one errorbar per project (to allow per-project markers)
	# ----------------------------
	for i, project in enumerate(projects):
		ax.errorbar(
			x_c.loc[project],
			y_c.loc[project],
			xerr=np.array([[xerr_low[i]], [xerr_high[i]]]),
			yerr=np.array([[yerr_low[i]], [yerr_high[i]]]),
			fmt=project_markers.get(project, "o"),
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
				project,
				(x_c.loc[project], y_c.loc[project]),
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
	# Marker legend for projects
	project_handles = [
		Line2D([], [], marker=project_markers[p], linestyle="", color="gray", label=p, markersize=8)
		for p in projects
	]
	ax.legend(handles=project_handles, title="Project", loc="upper left", bbox_to_anchor=(1.05, 1.0), frameon=True)

	# ----------------------------
	# 8) Axes formatting
	# ----------------------------
	ax.set_xlabel(x_key)
	ax.set_ylabel(y_key)
	ax.set_title(f"Project Summary (center={center_scenario}, range={low_scenario}→{high_scenario})")

	ax.set_xlim(left=0)
	ax.set_ylim(bottom=0)
	ax.grid(True, linestyle="--", linewidth=0.5, color="gray", alpha=0.3)
	fig.tight_layout(rect=[0, 0, 0.8, 1])

	plt.show()
	
	return fig, ax




















