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

def update_materials(sc, pathway_data, rank):
	"""Apply pathway-specific material cost and impact overrides at a given rank.

	Reads from two keys in pathway_data (populated by build_data_dict):
	  material_cost.<material>.<rank>              -> facility.material_data[material]["cost"]
	  material_impact.<material>.<category>.<rank> -> facility.material_data[material][category]

	Applies to all facilities in the supply chain.
	Silently skips entries where the ranked value is None, 0, or the material
	is not present in a facility's material_data.

	Parameters
	----------
	sc          : SupplyChain
	pathway_data: dict   -- single-pathway slice from build_data_dict
	rank        : str    -- "optimistic", "midpoint", or "conservative"
	"""
	cost_overrides = pathway_data.get("material_cost",   {}) or {}
	impact_overrides = pathway_data.get("material_impact", {}) or {}
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

def run_tornado_data(sc, pathway_data, apv):
	def _record(summary):
		return {
			"avg_opex":     summary.get("avg_opex",     0.0),
			"avg_var_cost": summary.get("avg_var_cost", 0.0),
			"avg_co2":      summary.get("avg_co2",      0.0),
		}

	def _reset_to_midpoint():
		update_machines(sc, "midpoint")
		update_materials(sc, pathway_data, "midpoint")

	results = {"baseline": {}, "machines": {}, "materials": {}}

	# Baseline
	_reset_to_midpoint()
	results["baseline"] = _record(sc.update_apv(apv, recalc=True))

	# Machines — vary one base at a time, hold all else at midpoint
	machine_bases = set()
	for step in sc.get_steps(transp=False):
		block = getattr(step, "machine_block", None)
		if block:
			machine_bases.add(block.split(".", 1)[0])

	for base in sorted(machine_bases):
		results["machines"][base] = {}
		for rank in ("conservative", "optimistic"):
			_reset_to_midpoint()
			update_machines(sc, {base: rank})
			results["machines"][base][rank] = _record(sc.update_apv(apv, recalc=True))

	# Materials — vary one material at a time, hold all else at midpoint
	mat_costs   = pathway_data.get("material_cost",   {}) or {}
	mat_impacts = pathway_data.get("material_impact", {}) or {}
	all_materials = set(mat_costs.keys()) | set(mat_impacts.keys())

	for material in sorted(all_materials):
		results["materials"][material] = {}
		single_pw = {
			"material_cost":   {material: mat_costs.get(material, {})},
			"material_impact": {material: mat_impacts.get(material, {})},
		}
		for rank in ("conservative", "optimistic"):
			_reset_to_midpoint()
			update_materials(sc, single_pw, rank)
			results["materials"][material][rank] = _record(sc.update_apv(apv, recalc=True))

	# Restore to midpoint
	_reset_to_midpoint()
	sc.update_apv(apv, recalc=True)

	return results

def run_topn_scenarios(sc, pathway_data, apv, top_n, metric="avg_opex"):
	"""
	Re-run conservative/midpoint/optimistic scenarios varying only the top_n most
	impactful machines and materials (ranked by |conservative - optimistic| range
	on `metric`).  Everything else is held at midpoint.
 
	Internally calls run_tornado_data to establish the ranking, then runs three
	targeted scenario passes.  sc is restored to midpoint after the call.
 
	Returns a dict with the same structure as evaluate_pathway:
	{
	    "conservative": {"apv": ..., "avg_opex": ..., "avg_var_cost": ..., "avg_co2": ...},
	    "midpoint":     {...},
	    "optimistic":   {...},
	}
	"""
	# Step 1: get tornado ranking
	tornado = run_tornado_data(sc, pathway_data, apv)
 
	# Step 2: build ranked list of (kind, name, opt_val, con_val)
	entries = []
	for name, vals in tornado.get("machines", {}).items():
		entries.append(("machine", name, vals["optimistic"][metric], vals["conservative"][metric]))
	for name, vals in tornado.get("materials", {}).items():
		entries.append(("material", name, vals["optimistic"][metric], vals["conservative"][metric]))
 
	entries.sort(key=lambda x: abs(x[3] - x[2]), reverse=True)
	top_entries = entries[:top_n]
 
	top_machines  = {e[1] for e in top_entries if e[0] == "machine"}
	top_materials = {e[1] for e in top_entries if e[0] == "material"}
 
	# Build a pathway_data slice covering only the top materials
	mat_costs   = pathway_data.get("material_cost",   {}) or {}
	mat_impacts = pathway_data.get("material_impact", {}) or {}
	top_pw = {
		"material_cost":   {m: mat_costs.get(m,   {}) for m in top_materials},
		"material_impact": {m: mat_impacts.get(m, {}) for m in top_materials},
	}
 
	# Step 3: run three scenario passes
	summary = {}
	for rank in ("conservative", "midpoint", "optimistic"):
		# Always start from a clean midpoint
		update_machines(sc, "midpoint")
		update_materials(sc, pathway_data, "midpoint")
		# Then apply only the top-N variables at the current rank
		if top_machines:
			update_machines(sc, {base: rank for base in top_machines})
		if top_materials:
			update_materials(sc, top_pw, rank)
		result = sc.update_apv(apv, recalc=True)
		summary[rank] = {
			"apv":          result["apv"],
			"avg_opex":     result["avg_opex"],
			"avg_var_cost": result["avg_var_cost"],
			"avg_co2":      result.get("avg_co2", 0.0) / 1000,  # kg -> t to match extracted_data convention
		}
 
	# Restore to midpoint
	update_machines(sc, "midpoint")
	update_materials(sc, pathway_data, "midpoint")
	sc.update_apv(apv, recalc=True)
 
	return summary