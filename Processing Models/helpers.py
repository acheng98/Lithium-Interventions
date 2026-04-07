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
	if s in {"true", "yes", "y"}:
		return True
	if s in {"false", "no", "n"}:
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
	if cell_str.lower() in {"true", "yes", "y", "false", "no", "n"}:
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
				parts = var.split(param_split)
				rank = parts[-1]		# last segment is always the rank
				key_path = parts[:-1]	# all preceding segments form the nested path
				for column in inputs_dict:
					target = inputs_dict[column]
					for key in key_path[:-1]: # navigate / create intermediate dicts
						target = target.setdefault(key, {})
					target.setdefault(key_path[-1], {})[rank] = clean_input_str(row[column])
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
			if var.startswith("utility_impact."):
				parts = [p.strip() for p in var.split(".")]
				if len(parts) != 3:
					raise ValueError(
						f"Invalid utility_impact variable_name: '{var}' -- "
						f"must be utility_impact.<utility>.<category> (e.g. utility_impact.electricity.co2)."
					)

				_, utility, category = parts
				for loc in location_names:
					val = clean_input_str(row.get(loc))
					if val is None:
						continue
					locations_dict[loc].setdefault("impact_factors", {}).setdefault(utility, {})[category] = val

			# Nested material overrides: material_impact.<material_name>.<category>
			elif var.startswith("material_impact."):
				parts = [p.strip() for p in var.split(".")]
				if len(parts) != 3:
					raise ValueError(
						f"Invalid material_impact variable_name: '{var}' -- "
						f"must be material_impact.<material>.<category> (e.g. material_impact.soda_ash.co2)."
					)

				_, material, category = parts
				for loc in location_names:
					val = clean_input_str(row.get(loc))
					if val is None:
						continue
					locations_dict[loc].setdefault("material", {}).setdefault(material, {})[category] = val

			# Material cost override: material_cost.<material>  -> material_data_overrides dict
			elif var.startswith("material_cost."):
				parts = [p.strip() for p in var.split(".")]
				if len(parts) != 2:
					raise ValueError(f"Invalid material_cost variable_name: '{var}' — expected 2 parts.")
				
				_, material = parts
				for loc in location_names:
					val = clean_input_str(row.get(loc))
					if val is None:
						continue
					locations_dict[loc].setdefault("material_data_overrides", {}).setdefault(material, {})["cost"] = val

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
					"ccf": safe_float(block.get("ccf"), default=1.0),
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
					"ccf": safe_float(block.get("ccf"), default=1.0),
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

def update_materials(sc, project_data, rank):
	"""Apply project-specific material cost and impact overrides at a given rank.

	Reads from two keys in project_data (populated by build_data_dict):
	  material_cost.<material>.<rank>              -> facility.material_data[material]["cost"]
	  material_impact.<material>.<category>.<rank> -> facility.material_data[material][category]

	Applies to all facilities in the supply chain.
	Silently skips entries where the ranked value is None, 0, or the material
	is not present in a facility's material_data.

	Parameters
	----------
	sc          : SupplyChain
	project_data: dict   -- single-project slice from build_data_dict
	rank        : str    -- "optimistic", "midpoint", or "conservative"
	"""
	cost_overrides = project_data.get("material_cost",   {}) or {}
	impact_overrides = project_data.get("material_impact", {}) or {}
	base_mat_data = sc.material_data

	for fac in sc.facilities.values():
		mat_data = fac.material_data

		# material_cost.<material>.<rank>
		for material, ranks in cost_overrides.items():
			if material not in mat_data:
				print(f"update_materials: material '{material}' not in facility '{fac.fac_id}' material_data; skipping.")
				continue
			val = (ranks or {}).get(rank)
			if val is not None and val != 0:
				mat_data[material]["cost"] = val
			else: # Reset to base so prior rank's mutation does not persist
				mat_data[material]["cost"] = (base_mat_data.get(material) or {}).get("cost", mat_data[material].get("cost"))

		# material_impact.<material>.<category>.<rank>
		for material, categories in impact_overrides.items():
			if material not in mat_data:
				print(f"update_materials: material '{material}' not in facility '{fac.fac_id}' material_data; skipping.")
				continue
			for category, ranks in (categories or {}).items():
				val = (ranks or {}).get(rank)
				if val is not None and val != 0:
					mat_data[material][category] = val
				else: # Reset to base so prior rank's mutation does not persist
					mat_data[material][category] = (base_mat_data.get(material) or {}).get(category, mat_data[material].get(category))


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
 
	# Draw stacked bars
	running = np.zeros(n, dtype=float)
	handle_map = {}
	for name in order:
		clr = (colors.get(name) if colors and name in colors else None)
		if horiz:
			h = ax.barh(pos, data[name], left=running, height=bar_thickness, label=name, color=clr)
		else:
			h = ax.bar(pos, data[name], bottom=running, label=name, color=clr)
		handle_map[name] = h
		running += data[name]
 
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
			xmax = ax.get_xlim()[1]
			ax.set_xlim(0, xmax * (1 + top_margin))
		if xlims is not None:
			ax.set_ylim(xlims)
	else:
		if xlims is not None:
			ax.set_xlim(xlims)
		if ylims is not None:
			ax.set_ylim(ylims)
		else:
			ymax = ax.get_ylim()[1]
			ax.set_ylim(0, ymax * (1 + top_margin))

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

	plt.savefig("output", dpi=300, bbox_inches="tight")
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

def plot_tornado(
	tornado_data,
	metric="avg_opex",      # "avg_opex" | "avg_co2" | "avg_var_cost"
	top_n=5,
	title=None,
	xlab=None,
	show=True,
	):
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
	ax.barh(y, con_vals - baseline, left=baseline, color="#f28e2b", label="Conservative", zorder=3)
	# Optimistic bars — extend left (better outcome, negative width)
	ax.barh(y, opt_vals - baseline, left=baseline, color="#4e79a7", label="Optimistic", zorder=3)

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



# ---------------------------------------------------------------------------
# Thacker Pass presentation aggregation
# ---------------------------------------------------------------------------

# Canonical step-group mapping.
# Each entry: (display_label, [step_names_to_aggregate]).
# Step names must match the labels produced by _build_steps_cost_series and
# _build_steps_impact_series (i.e. step.step_name / transport.name / normalised
# sink names "Tailings" and "Wastewater Treatment").
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
		["Tailings", "Wastewater Treatment"]),
]


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


def thacker_pass_steps_aggregated(
	sc,
	project_data,
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
	sc           : SupplyChain  (facilities already built via evaluate_project)
	project_data : dict
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
	update_materials(sc, project_data, "conservative")
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
	update_materials(sc, project_data, "optimistic")
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
	update_materials(sc, project_data, "midpoint")
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
	# Colors — match existing dissertation figure convention
	# ------------------------------------------------------------------
	cost_colors = {
		"Material Costs":      "#4e79a7",
		"Labor Costs":         "#f28e2b",
		"Utility Costs":       "#59a14f",
		"Other":               "#e15759",
		"Tailings":            "#7b5ea7",
		"Wastewater Treatment":"#b09bc7",  # lighter purple — adjacent to tailings
	}
	imp_colors = {
		"Scope One":   "#f28e2b",
		"Scope Two":   "#4e79a7",
		"Scope Three": "#76b7b2",
	}

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
		["Classification"]),
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
		["Tailings", "Wastewater Treatment"]),
]

def jianxiawo_steps_aggregated(
	sc,
	project_data,
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
):
	"""
	Plot Jianxiawo costs and emissions with steps aggregated into
	presentation-friendly groups, with asymmetric scenario error bars.

	Mirrors thacker_pass_steps_aggregated but uses _JIANXIAWO_GROUPS,
	which separates Classification & Flotation as its own row to highlight
	the pathway-specific beneficiation burden of low-grade lepidolite ore.

	Parameters
	----------
	sc           : SupplyChain  (facilities already built via evaluate_project)
	project_data : dict
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
	update_materials(sc, project_data, "conservative")
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
	update_materials(sc, project_data, "optimistic")
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
	update_materials(sc, project_data, "midpoint")
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
	# Colors — match existing dissertation figure convention
	# ------------------------------------------------------------------
	cost_colors = {
		"Material Costs":      "#4e79a7",
		"Labor Costs":         "#f28e2b",
		"Utility Costs":       "#59a14f",
		"Other":               "#e15759",
		"Tailings":            "#7b5ea7",
		"Wastewater Treatment":"#b09bc7",
	}
	imp_colors = {
		"Scope One":   "#f28e2b",
		"Scope Two":   "#4e79a7",
		"Scope Three": "#76b7b2",
	}

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






