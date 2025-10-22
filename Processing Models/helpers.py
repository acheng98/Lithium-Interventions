from typing import Dict, Any, List, Optional

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
	if s in {"true", "t", "yes", "y", "1"}:
		return True
	if s in {"false", "f", "no", "n", "0"}:
		return False
	return default

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
		if not in_name:
			break
		constituents = parse_list_field(step_vars.get(f"primary_input_{i}_constituents", ""))
		chemistry_dependence = str(step_vars.get(f"primary_input_{i}_chemistry_dependence", "False")).strip().lower() in ("true", "yes", "1") # All strings always return as TRUE
		if not chemistry_dependence: # If not dependent on chemistry, we take the prescribed constituent fractions
			fractions = parse_list_field(step_vars.get(f"primary_input_{i}_constituent_fractions", ""), cast=float)
		else: # Else they must be calculated from an input chemistry
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
		material_flows["primary_outputs"][out_name] = {
			"next_step": step_vars.get(f"primary_output_{i}_step"),
			"yield_rate": float(step_vars.get(f"primary_output_{i}_yield_rate", 1.0)),
			"units": step_vars.get(f"primary_output_{i}_units"),
			"constituents": dict(zip(constituents, fractions)),
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
	# First row = header
	header = locational_data[0]

	# Extract location names (skip variable_name, Description, Unit)
	location_names = header[3:]

	locations_dict = {loc: {} for loc in location_names}

	# Process each row
	for row in locational_data[1:]:
		if not row or len(row) < 3:
			continue  # skip empty/malformed rows

		var_name = row[0]
		# values start from 4th column onward
		values = row[3:]

		for loc, val in zip(location_names, values):
			try:
				# Try to cast to float if numeric
				val = float(val)
			except (ValueError, TypeError):
				pass  # leave as string if not numeric

			locations_dict[loc][var_name] = val

	return locations_dict