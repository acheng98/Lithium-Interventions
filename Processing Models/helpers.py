import csv
import os
import contextlib
import re

_WORKBOOK_CACHE = {}

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

class _Table:
	def __init__(self, fieldnames, rows):
		self.fieldnames = fieldnames
		self._rows = rows
	def __iter__(self):
		return iter(self._rows)

def _load_workbook(path):
	import openpyxl
	key = (os.path.abspath(path), os.path.getmtime(path))
	if key not in _WORKBOOK_CACHE:
		_WORKBOOK_CACHE.clear()
		_WORKBOOK_CACHE[key] = openpyxl.load_workbook(path, data_only=True)
	return _WORKBOOK_CACHE[key]

def _resolve_sheet(wb, name):
	if name in wb.sheetnames:
		return wb[name]
	for sheet in wb.sheetnames:
		if sheet == name[:31]:
			return wb[sheet]
	raise KeyError(f"Sheet '{name}' not found. Available: {wb.sheetnames}")

@contextlib.contextmanager
def _open_table(data_folder, file):
	if str(data_folder).lower().endswith((".xlsx", ".xlsm")):
		ws = _resolve_sheet(_load_workbook(data_folder), file)
		grid = [list(r) for r in ws.iter_rows(values_only=True)]
		if not grid:
			raise ValueError(f"Sheet '{file}' is empty.")
		width = max((i + 1 for i, v in enumerate(grid[0]) if v is not None and str(v).strip()), default=0)
		fieldnames = [str(v).strip() for v in grid[0][:width]]
		rows = []
		for raw in grid[1:]:
			cells = list(raw[:width]) + [None] * max(0, width - len(raw))
			rows.append({h: ("" if v is None else str(v)) for h, v in zip(fieldnames, cells)})
		yield _Table(fieldnames, rows)
	else:
		with open(data_folder + file + ".csv", newline="") as f:
			reader = csv.DictReader(f)
			yield _Table(reader.fieldnames, list(reader))

def check_workbook_formula_cache(path):
	import openpyxl
	formulas = openpyxl.load_workbook(path, data_only=False)
	values = openpyxl.load_workbook(path, data_only=True)
	missing = []
	for name in formulas.sheetnames:
		sf, sv = formulas[name], values[name]
		for row in sf.iter_rows():
			for cell in row:
				if isinstance(cell.value, str) and cell.value.startswith("=") and sv[cell.coordinate].value is None:
					missing.append((name, cell.coordinate, cell.value))
	return missing

def build_data_dict(data_folder,file,col=2,param_split=".",skip_rows=["notes", "sources", "key_equation"]):
	"""
	Returns:
		{ column : { row_name : typed_value, ... }, ... }
	When the row_name includes a rank (e.g. ghg_emissions.low) return a nested dict
		{ column : { row_name : {rank: typed_value, rank: typed_value}, ... }, ... }
	Also, when the value includes a key_split, also return a nested dict
		{ column : { row_name : {key: value, key: value}, ... }, ... }
	"""
	with _open_table(data_folder,file) as reader:
		inputs_dict = {name: {} for name in reader.fieldnames[col:]} # typically, col=2: 0: variable names, 1: descriptions

		var_col = reader.fieldnames[0]
		for row in reader:
			var = row[var_col]
			if var in skip_rows: # skip processing all of the rows in skip_rows
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
	with _open_table(data_folder,file) as reader:
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
					if var in skip_rows: # skip processing all of the rows in skip_rows
						locations_dict[loc][var] = row.get(loc)
					else:
						locations_dict[loc][var] = clean_input_str(row.get(loc))

		return locations_dict

def build_facility_dict(data_folder,file,skip_rows=["notes", "sources", "key_equation"]):
	"""
	Returns:
		{ location : { row_name : typed_value, ... }, ... }
	"""
	with _open_table(data_folder,file) as reader:

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

				entry = new.setdefault(name, {
					"name_long": block.get("name_long"),
					"targets": {},
					"units": block.get("units"),
				})
				for t, r, e in zip(targets, ratios, elims):
					if t in entry["targets"]:
						raise KeyError(f"Reagent '{name}' in step '{step}' declares target '{t}' more than once.")
					entry["targets"][t] = {"ratio": r, "elim": e, "usage": 0, "abs_usage": 0, "total_cost": 0}
					
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