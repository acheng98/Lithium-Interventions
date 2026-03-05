from typing import Dict, Any, List, Optional
from collections import OrderedDict, defaultdict
import copy

from facility import Facility
from production_step import ProductionStep
from transportation import Transportation, TransportRoute
from helpers import plot_stacked_bars, plot_production_curve

# Define a class for the supply chain
class SupplyChain:
	"""
	Supply chain model composed of Facilities connected by optional TransportRoutes.

	Design principle:
	- Calculations happen in Facility / ProductionStep / TransportRoute.
	- SupplyChain getters and reports are read-only projections over *already computed* state.
	- A cached snapshot layer provides a stable schema for all projections.
	"""
	def __init__(self,transp_data,loc_data,machine_data,material_data):
		self.facilities: Dict[str, Facility] = {}  # facility_id : Facility
		self.links: Dict[Tuple[Facility, Facility], List[Any]] = {}  # (from_fac,to_fac): [products_dict, Optional(transport_route)]
		self.prod_map: Dict[float, List[float]] = {}  # apv: [tot_var_cost, tot_fixed_cost, tot_cost]
		self.fwd: List[Facility] = []
		self.rev: Iterable[Facility] = []
		self.fwd_transp: List[Union[Facility, TransportRoute]] = []
		self.rev_transp: List[Union[Facility, TransportRoute]] = []

		# Default values for facilities to inherit
		self.transp_data = transp_data
		self.loc_data = loc_data
		self.machine_data = machine_data
		self.material_data = material_data

		# Summary statistics
		self.apv: float = 0.0
		self.total_utilities: Dict[str, Any] = {}
		self.tot_var_cost: float = 0.0
		self.tot_fixed_cost: float = 0.0
		self.tot_opex: float = 0.0
		self.tot_capex: float = 0.0
		self.tot_cost: float = 0.0
		self.avg_var_cost: float = 0.0
		self.avg_fixed_cost: float = 0.0
		self.avg_opex: float = 0.0
		self.avg_capex: float = 0.0
		self.avg_cost: float = 0.0
		self.sink_costs: Dict[str, float] = {}
		self.env_impacts: Dict[str, float] = {}

		# Getter/report cache (invalidated on APV recalculation)
		self._getter_cache: Dict[Tuple[Any, ...], Any] = {}

	def _invalidate_getter_cache(self) -> None:
		self._getter_cache.clear()

	def add_facility(
		self,
		fac: Facility,
		next_fac: Optional[Facility] = None,
		products: Optional[Dict[str, float]] = None,
		transport_route: Optional[TransportRoute] = None,
		):
		self.facilities[fac.fac_id] = fac
		fac.supply_chain = self
		if next_fac is not None:
			if products == None:
				raise ValueError("Intermediate products being transferred between facilities are not defined.")
			else:
				self.link_facilities(fac,next_fac,products,transport_route)

	def link_facilities(
		self,
		from_fac: Facility,
		to_fac: Facility,
		products: Dict[str, float],
		transport_route: Optional[TransportRoute],
		):
		'''
		Create a directed link between facilities.

		from_fac (str): name of the source facility
		to_fac (str): name of the target facility
		products (dict): {product names: % of product to transfer to new facility}
		transport_route: optional TransportRoute for associated shipping between facilities.
		'''
		if from_fac.fac_id not in self.facilities:
			raise KeyError(f"Source facility '{from_fac.fac_id}' not found.")
		if to_fac.fac_id not in self.facilities:
			raise KeyError(f"Target facility '{to_fac.fac_id}' not found.")

		# Validate products exist
		from_outputs = self.facilities[from_fac.fac_id].collect_primary_outputs()
		to_inputs = self.facilities[to_fac.fac_id].collect_primary_inputs()

		for product in products.keys():
			if product not in from_outputs:
				raise KeyError(f"Product '{product}' not found in {from_fac.fac_id} outputs.")
			if product not in to_inputs:
				raise KeyError(f"Product '{product}' not found in {to_fac.fac_id} inputs.")

		# Validate transport_route is a TransportRoute class
		if transport_route is not None and not(isinstance(transport_route,TransportRoute)):
			raise ValueError(f"Input transport_route is not actually a TransportRoute object")

		key = (from_fac, to_fac)
		if key not in self.links:
			self.links[key] = {}
		self.links[key] = [products,transport_route]

	def register_sink_cost(self, sink_name: str, cost_per_unit: float) -> None:
		"""Register a unit handling cost for a sink (e.g. $/tonne to landfill)."""
		self.sink_costs[sink_name] = float(cost_per_unit)

	def topo_order(self):
		"""
		Return facility ids in forward topological order (upstream to downstream).
		"""
		# 1) Nodes set
		nodes = set(self.facilities.keys())
		# 2) Build adjacency & indegree
		adj = {n: set() for n in nodes}
		indeg = {n: 0 for n in nodes}

		# Validate link endpoints and build graph
		for (u, v), _ in self.links.items():
			if u.fac_id not in nodes or v.fac_id not in nodes:
				raise KeyError(f"Link refers to unknown facilities: {u.fac_id}->{v.fac_id}")
			if v.fac_id not in adj[u.fac_id]:
				adj[u.fac_id].add(v.fac_id)
				indeg[v.fac_id] += 1

		# 3) Initialize ready queue with zero-indegree nodes (sorted for determinism)
		ready = sorted([n for n in nodes if indeg[n] == 0])
		order: List[str] = []

		# 4) Kahn's algorithm
		while ready:
			u = ready.pop(0)        # pop smallest id for stable order
			order.append(u)
			for v in sorted(adj[u]): # iterate deterministically
				indeg[v] -= 1
				if indeg[v] == 0:
					# keep ready sorted; for large graphs use heapq
					insert_at = 0
					while insert_at < len(ready) and ready[insert_at] < v:
						insert_at += 1
					ready.insert(insert_at, v)

		# 5) Cycle check
		if len(order) != len(nodes):
			remaining = [n for n, d in indeg.items() if d > 0]
			raise ValueError(
				"Cycle detected in supply chain among facilities: "
				+ ", ".join(sorted(remaining))
			)

		self.fwd = [self.facilities[fid] for fid in order]
		self.rev = reversed(self.fwd)

		return self.fwd

	def topo_order_transp(self) -> List[Union[Facility, TransportRoute]]:
		"""Topo order including facility nodes and intermediate TransportRoutes."""
		self.topo_order()
		topo_order_transp: List[Union[Facility, TransportRoute]] = []
		for fac in self.fwd:
			topo_order_transp.append(fac)
			
			for (u, v),(products,transport_route) in self.links.items(): # This is O(n^2) which is technically inefficient, but n should be small
				if u == fac and transport_route is not None:
					topo_order_transp.append(transport_route)

		self.fwd_transp = topo_order_transp
		self.rev_transp = list(reversed(topo_order_transp))
		return topo_order_transp

	def update_apv(self, apv: float, recalc: bool = False) -> Dict[str, Any]:
		"""Evaluate the entire supply chain for a given annual production volume (APV)."""
		if type(apv) not in [float,int]: 
			raise ValueError("APV input must be a float or int")

		if (not recalc) and (apv in self.prod_map): # Don't need to re-run if already recorded and not explicitly recalculating
			self.apv = float(apv)
			cached = self.prod_map[self.apv]
			cached_var = cached[0] if len(cached) >= 1 else 0.0
			cached_fixed = cached[1] if len(cached) >= 2 else 0.0
			cached_total = cached[2] if len(cached) >= 3 else (cached_var + cached_fixed)
			cached_opex = cached[3] if len(cached) >= 4 else cached_var
			cached_capex = cached[4] if len(cached) >= 5 else cached_fixed

			return {
				"apv": self.apv,
				"tot_var_cost": cached_var,
				"tot_fixed_cost": cached_fixed,
				"tot_opex": cached_opex,
				"tot_capex": cached_capex,
				"tot_cost": cached_total,
				"avg_var_cost": cached_var / self.apv if self.apv else 0.0,
				"avg_fixed_cost": cached_fixed / self.apv if self.apv else 0.0,
				"avg_opex": cached_opex / self.apv if self.apv else 0.0,
				"avg_capex": cached_capex / self.apv if self.apv else 0.0,
				"avg_cost": cached_total / self.apv if self.apv else 0.0,
 				"total_co2": self.env_impacts.get("co2", 0.0),
 				"avg_co2": (self.env_impacts.get("co2", 0.0) / self.apv) if self.apv else 0.0,
			}

		self.apv = float(apv)
		self.topo_order()
		self._invalidate_getter_cache()

		# Reset rollups across runs
		self.total_utilities: Dict[str, Any] = {}
		self.tot_var_cost: float = 0.0
		self.tot_fixed_cost: float = 0.0
		self.tot_opex: float = 0.0
		self.tot_capex: float = 0.0
		self.tot_cost: float = 0.0
		self.avg_var_cost: float = 0.0
		self.avg_fixed_cost: float = 0.0
		self.avg_opex: float = 0.0
		self.avg_capex: float = 0.0
		self.avg_cost: float = 0.0
		self.sink_costs: Dict[str, float] = {}
		self.env_impacts: Dict[str, float] = {}

		cur_apv = float(apv)
		for fac in self.rev:
			updated_apv = False
			summary = fac.update_apv(cur_apv,recalc)
			self.tot_var_cost += summary["tot_var_cost"]
			self.tot_fixed_cost += summary["tot_fixed_cost"]
			self.tot_opex += summary["tot_opex"]
			self.tot_capex += summary["tot_capex"]
			self.tot_cost += summary["tot_cost"]

			for k, v in summary["emissions_totals"].items():
				self.env_impacts[k] = self.env_impacts.get(k, 0.0) + v

			for (u, v),(products,transport_route) in self.links.items(): # This is O(n^2) which is technically inefficient, but n should be small
				if v == fac:
					if transport_route is not None:
						res = transport_route.evaluate_total(total_volume=fac.get_initial_input_amount())
						self.tot_var_cost += res["variable_cost"]
						self.tot_fixed_cost += res["fixed_cost"]
						# Transport is treated as operating cost (no capex attribution)
						self.tot_opex += res["variable_cost"] + res["fixed_cost"]
						self.tot_cost += res["total_cost"]
				
						for k, v in res["emissions_totals"].items():
							self.env_impacts[k] = self.env_impacts.get(k, 0.0) + v

						# Assume only one link per facility at this time
						cur_apv = res["initial_volume"]
						updated_apv = True
						break

			
			if not updated_apv: # No transportation link identified, just get the input value to this current facility
				cur_apv = fac.get_initial_input_amount()

		for rec in self.get_sink_handling_costs():
			self.tot_var_cost	+= rec["total_cost"]
			self.tot_opex		+= rec["total_cost"]
			self.tot_cost		+= rec["total_cost"]
			
		self.avg_var_cost = self.tot_var_cost / self.apv if self.apv else 0.0
		self.avg_fixed_cost = self.tot_fixed_cost / self.apv if self.apv else 0.0
		self.avg_opex = self.tot_opex / self.apv if self.apv else 0.0
		self.avg_capex = self.tot_capex / self.apv if self.apv else 0.0
		self.avg_cost = self.tot_cost / self.apv if self.apv else 0.0
		self.prod_map[self.apv] = [self.tot_var_cost, self.tot_fixed_cost, self.tot_cost, self.tot_opex, self.tot_capex]

		return {
			"apv": self.apv,
			"tot_var_cost": self.tot_var_cost,
			"tot_fixed_cost": self.tot_fixed_cost,
			"tot_opex": self.tot_opex,
			"tot_capex": self.tot_capex,
			"tot_cost": self.tot_cost,
			"avg_var_cost": self.avg_var_cost,
			"avg_fixed_cost": self.avg_fixed_cost,
			"avg_opex": self.avg_opex,
			"avg_capex": self.avg_capex,
			"avg_cost": self.avg_cost,
			"total_co2": self.env_impacts.get("co2",0.0),
			"avg_co2": (self.env_impacts.get("co2", 0.0) / self.apv) if self.apv else 0.0,
		}

	# -------------------------
	# Step list utilities
	# -------------------------
	def get_steps(self, transp: bool = False) -> List[Union[ProductionStep, Transportation]]:
		"""Return ProductionSteps in topo order; optionally include Transportation legs."""
		steps: List[Union[ProductionStep, Transportation]] = []
		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				if not getattr(node, "fwd", None):
					node.topo_order()
				steps.extend(list(node.fwd))
			elif isinstance(node, TransportRoute) and transp:
				steps.extend(list(node.legs))
		return steps

	# -------------------------
	# Canonical snapshot layer
	# -------------------------
	def _get_step_snapshots(self, transp: bool = False, use_cache: bool = True) -> List[OrderedDict]:
		"""Return cached, topo-ordered step snapshots.

		Snapshots are read-only views over already-computed step attributes.
		They do *not* trigger recalculation.
		"""
		cache_key = ("step_snapshots", float(self.apv), transp)
		if use_cache and cache_key in self._getter_cache:
			return self._getter_cache[cache_key]

		def _safe_get(obj: Any, attr: str, default: Any = 0.0) -> Any:
			v = getattr(obj, attr, default)
			return default if v is None else v

		snaps: List[OrderedDict] = []
		for node in self.get_steps(transp=transp):
			if isinstance(node, ProductionStep):
				step_units = getattr(node, "step_basis_unit", None)

				# Reagents
				reagents = OrderedDict()
				for r_name, props in (getattr(node, "secondary_inputs", None) or {}).items():
					if props is None:
						continue
					reagents[r_name] = {
						"abs_usage": float(props.get("abs_usage", 0.0) or 0.0),
						"total_cost": float(props.get("total_cost", 0.0) or 0.0),
					}

				# Utilities
				fac = getattr(node, "facility", None)
				utility_candidates = [
					("electricity", "electricity_consumed", "electricity_cost", "elec_price"),
					("natural_gas", "natural_gas_consumed", "natural_gas_cost", "gas_price"),
					("diesel", "diesel_consumed", "diesel_cost", "diesel_price"),
					("propane", "propane_consumed", "propane_cost", "propane_price"),
					("cooling_water", "cooling_water_consumed", "cooling_water_cost", "cool_water_price"),
					("steam", "steam_consumed", "steam_cost", "steam_price"),
					("compressed_air", "compressed_air_consumed", "compressed_air_cost", "comp_air_price"),
				]
				utilities = OrderedDict()
				for uname, c_attr, cost_attr, price_attr in utility_candidates:
					consumed = float(_safe_get(node, c_attr, 0.0))
					cost = float(_safe_get(node, cost_attr, 0.0))
					unit_price = getattr(fac, price_attr, None) if fac is not None else None
					if consumed != 0.0 or cost != 0.0 or hasattr(node, c_attr) or hasattr(node, cost_attr):
						utilities[uname] = {"consumed": consumed, "cost": cost, "unit_price": unit_price}

				# Costs
				costs = OrderedDict([
					("tot_var_cost", float(_safe_get(node, "tot_var_cost", 0.0))),
					("tot_fixed_cost", float(_safe_get(node, "tot_fixed_cost", 0.0))),
					("tot_opex", float(_safe_get(node, "tot_opex", 0.0))),
					("tot_capex", float(_safe_get(node, "tot_capex", 0.0))),
					("tot_mat_cost", float(_safe_get(node, "tot_mat_cost", 0.0))),
					("labor_cost", float(_safe_get(node, "labor_cost", 0.0))),
					("utility_cost", float(_safe_get(node, "utility_cost", 0.0))),
					("machine_cost", float(_safe_get(node, "machine_cost", 0.0))),
					("tool_cost", float(_safe_get(node, "tool_cost", 0.0))),
					("building_cost", float(_safe_get(node, "building_cost", 0.0))),
					("aux_equip_cost", float(_safe_get(node, "aux_equip_cost", 0.0))),
					("maint_cost", float(_safe_get(node, "maint_cost", 0.0))),
					("fixed_over_cost", float(_safe_get(node, "fixed_over_cost", 0.0))),
				])

				# Coproducts
				coproducts = OrderedDict()
				for c_name, props in (getattr(node, "secondary_outputs", None) or {}).items():
					if props is None:
						continue
					coproducts[c_name] = {
						"volume": float(props.get("volume", 0.0) or 0.0),
						"sink": props.get("sink"),
					}

				# Impacts (if present)
				impacts = None
				if hasattr(node, "scope_one_impacts") or hasattr(node, "scope_two_impacts"):
					impacts = {
						"scope_one": dict(getattr(node, "scope_one_impacts", {}) or {}),
						"scope_two": dict(getattr(node, "scope_two_impacts", {}) or {}),
					}

				snaps.append(OrderedDict([
					("step_id", node.step_id),
					("step_name", node.step_name),
					("kind", "production"),
					("pv", float(_safe_get(node, "step_pv", 0.0))),
					("step_units",step_units),
					("constituents", dict(getattr(node, "constituents", {}) or {})),
					("primary_inputs", dict(getattr(node, "primary_inputs", {}) or {})),
					("reagents", reagents),
					("coproducts", coproducts),
					("utilities", utilities),
					("machines_required", float(_safe_get(node, "machines_required", 0.0))),
					("labor_required", float(_safe_get(node, "labor_required", 0.0))),
					("costs", costs),
					("impacts", impacts),
				]))

			elif isinstance(node, Transportation):
				snaps.append(OrderedDict([
					("step_id", node.name),
					("step_name", node.name),
					("kind", "transport"),
					("pv", float(_safe_get(node, "volume", 0.0))),
					("reagents", OrderedDict()),
					("utilities", OrderedDict()),
					("constituents", {}),
					("primary_inputs", {}),
					("labor_required", 0.0),
					("costs", OrderedDict([
						("variable_cost", float(_safe_get(node, "variable_cost", 0.0))),
						("fixed_cost", float(_safe_get(node, "fixed_cost", 0.0))),
						("total_cost", float(_safe_get(node, "total_cost", 0.0))),
					])),
					("impacts", {"emissions_totals": dict(getattr(node, "emissions_totals", {}) or {})}),
				]))
			else:
				raise ValueError("Unidentified node returned from sc.get_steps().")

		# Temporary adder for sinks
		sink_totals: Dict[str, float] = {}
		for snap in snaps:
			if snap.get("kind") != "production":
				continue
			for c_name, props in (snap.get("coproducts") or {}).items():
				sink = props.get("sink")
				volume = float(props.get("volume", 0.0) or 0.0)
				unit_cost = self.sink_costs.get(sink, 0.0)
				sink_totals[sink] = sink_totals.get(sink, 0.0) + volume * unit_cost

		for sink_name, total_cost in sink_totals.items():
			if total_cost == 0.0:
				continue
			snaps.append(OrderedDict([
				("step_name",	sink_name),
				("step_id", 	sink_name),
				("kind",		"sink"),
				("pv",			0.0),
				("costs",		OrderedDict([
					("tot_var_cost",	total_cost),
					("tot_fixed_cost",	0.0),
					("tot_opex",		total_cost),
					("tot_capex",		0.0),
				])),
			]))

		if use_cache:
			self._getter_cache[cache_key] = snaps
		return snaps

	# -------------------------
	# Overall summary getters
	# -------------------------
	def get_total_reagents(self) -> Dict[str, Dict[str, float]]:
		"""Aggregate total absolute usage and total cost for each reagent across all steps."""
		totals: Dict[str, Dict[str, float]] = {}
		for s in self._get_step_snapshots(transp=False):
			for reagent, props in (s.get("reagents") or {}).items():
				if reagent not in totals:
					totals[reagent] = {"abs_usage": 0.0, "total_cost": 0.0}
				totals[reagent]["abs_usage"] += float(props.get("abs_usage", 0.0) or 0.0)
				totals[reagent]["total_cost"] += float(props.get("total_cost", 0.0) or 0.0)

		for r, info in totals.items():
			info["output_avg_cost"] = (info["total_cost"] / self.apv) if self.apv else 0.0
		return totals

	def get_total_utilities(self) -> Dict[str, Dict[str, float]]:
		"""Aggregate total consumption and cost for each utility across all steps."""
		totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {"consumed": 0.0, "cost": 0.0})
		for s in self._get_step_snapshots(transp=False):
			for uname, rec in (s.get("utilities") or {}).items():
				totals[uname]["consumed"] += float(rec.get("consumed", 0.0) or 0.0)
				totals[uname]["cost"] += float(rec.get("cost", 0.0) or 0.0)

		out: Dict[str, Dict[str, float]] = {k: dict(v) for k, v in totals.items()}
		for uname, info in out.items():
			info["output_avg_cost"] = (info["cost"] / self.apv) if self.apv else 0.0
		return out

	def get_total_labor(self) -> Dict[str, float]:
		"""Aggregate labor demand and labor cost across all steps."""
		labor_required = 0.0
		labor_cost = 0.0
		for s in self._get_step_snapshots(transp=False):
			labor_required += float(s.get("labor_required", 0.0) or 0.0)
			labor_cost += float((s.get("costs") or {}).get("labor_cost", 0.0) or 0.0)
		return {
			"labor_required": labor_required,
			"labor_cost": labor_cost,
			"output_avg_labor_cost": (labor_cost / self.apv) if self.apv else 0.0,
		}

	def get_sink_handling_costs(self) -> List[Dict[str, Any]]:
		"""
		Compute handling costs for all coproducts using registered sink unit costs.
		Returns one record per coproduct per step: step_name, coproduct, sink, volume, unit_cost, total_cost, avg_cost.
		NOTE: reads from get_coproducts() (step.secondary_outputs) directly,
		not from facility.sinks, which is redundant aggregation / technical debt.
		"""
		out: List[Dict[str, Any]] = []
		for step_id, c_name, sink, volume in self.get_coproducts():
			unit_cost = self.sink_costs.get(sink, 0.0)
			out.append({
				"step_id":		step_id,
				"step_name": 	step_id,
				"coproduct":	c_name,
				"sink":			sink,
				"volume":		volume,
				"unit_cost":	unit_cost,
				"total_cost":	volume * unit_cost,
				"avg_cost":		(volume * unit_cost / self.apv) if self.apv else 0.0,
			})
		return out

	# -------------------------
	# Step-level projection getters
	# -------------------------
	def get_step_constituents(self) -> List[List[Any]]:
		return [[s["step_id"], s.get("constituents", {})] for s in self._get_step_snapshots(transp=False)]

	def get_constituent_amount_at_steps(self, constituent: str) -> List[List[Any]]:
		out = []
		for s in self._get_step_snapshots(transp=False):
			pv = float(s.get("pv", 0.0) or 0.0)
			val = float((s.get("constituents", {}) or {}).get(constituent, 0.0) or 0.0)
			out.append([s["step_id"], val * pv])
		return out

	def get_step_reagent_usage(self) -> List[List[Any]]:
		"""Backward-compatible shape: [step_id, reagent_name, {usage, cost}]."""
		out: List[List[Any]] = []
		for s in self._get_step_snapshots(transp=False):
			for reagent, props in (s.get("reagents") or {}).items():
				out.append([
					s["step_id"],
					reagent,
					{"usage": props.get("abs_usage", 0.0), "cost": props.get("total_cost", 0.0)},
				])
		return out

	def get_step_utility(self, utility_name: str) -> List[List[Any]]:
		"""Generic utility getter. Backward-compatible shape for old specific getters."""
		out: List[List[Any]] = []
		for s in self._get_step_snapshots(transp=False):
			rec = (s.get("utilities") or {}).get(utility_name, None)
			cons = float((rec or {}).get("consumed", 0.0) or 0.0)
			cost = float((rec or {}).get("cost", 0.0) or 0.0)
			out.append([s["step_id"], utility_name, cons, cost])
		return out

	def get_step_electric(self) -> List[List[Any]]:
		out = []
		for step_id, _, cons, cost in self.get_step_utility("electricity"):
			out.append([step_id, "Electricity", cons, cost])
		return out

	def get_step_natural_gas(self) -> List[List[Any]]:
		out = []
		for step_id, _, cons, cost in self.get_step_utility("natural_gas"):
			out.append([step_id, "Natural Gas", cons, cost])
		return out

	def get_step_diesel(self) -> List[List[Any]]:
		out = []
		for step_id, _, cons, cost in self.get_step_utility("diesel"):
			out.append([step_id, "Diesel", cons, cost])
		return out

	def get_step_propane(self) -> List[List[Any]]:
		out = []
		for step_id, _, cons, cost in self.get_step_utility("propane"):
			out.append([step_id, "Propane", cons, cost])
		return out

	def get_step_cooling_water(self) -> List[List[Any]]:
		out = []
		for step_id, _, cons, cost in self.get_step_utility("cooling_water"):
			out.append([step_id, "Cooling Water", cons, cost])
		return out

	def get_step_steam(self) -> List[List[Any]]:
		out = []
		for step_id, _, cons, cost in self.get_step_utility("steam"):
			out.append([step_id, "Steam", cons, cost])
		return out

	def get_step_compressed_air(self) -> List[List[Any]]:
		out = []
		for step_id, _, cons, cost in self.get_step_utility("compressed_air"):
			out.append([step_id, "Compressed Air", cons, cost])
		return out

	def get_step_utilities(self) -> List[List[Any]]:
		"""Legacy: [step_id, 'Total Utility Cost', utility_cost]."""
		out: List[List[Any]] = []
		for s in self._get_step_snapshots(transp=False):
			out.append([
				s["step_id"],
				"Total Utility Cost",
				float((s.get("costs") or {}).get("utility_cost", 0.0) or 0.0),
			])
		return out

	def get_step_utilities_detailed(self) -> List[OrderedDict]:
		"""Detailed utility breakdown, now sourced from snapshots."""
		results: List[OrderedDict] = []
		for s in self._get_step_snapshots(transp=False):
			utils = s.get("utilities") or OrderedDict()
			rec = OrderedDict([
				("step_id", s["step_id"]),
				("total_utility_cost", float((s.get("costs") or {}).get("utility_cost", 0.0) or 0.0)),
			])
			rec["utilities"] = utils
			results.append(rec)
		return results

	def get_step_labor(self) -> List[List[Any]]:
		out: List[List[Any]] = []
		for s in self._get_step_snapshots(transp=False):
			out.append([
				s["step_id"],
				float(s.get("labor_required", 0.0) or 0.0),
				float((s.get("costs") or {}).get("labor_cost", 0.0) or 0.0),
			])
		return out

	def get_step_machines(self) -> List[List[Any]]:
		out: List[List[Any]] = []
		for s in self._get_step_snapshots(transp=False):
			out.append([
				s["step_id"],
				float(s.get("machines_required", 0.0) or 0.0),
				float((s.get("costs") or {}).get("machine_cost", 0.0) or 0.0),
			])
		return out

	def get_coproducts(self) -> List[List[Any]]:
		"""Return [step_name, coproduct_name, sink, volume] for every coproduct at each step."""
		out: List[List[Any]] = []
		for s in self._get_step_snapshots(transp=False):
			for c_name, props in (s.get("coproducts") or {}).items():
				out.append([
					s["step_id"],
					c_name,
					props.get("sink"),
					float(props.get("volume", 0.0) or 0.0),
				])
		return out

	def get_detailed_pvs(self) -> List[List[Any]]:
		return [[s["step_id"], float(s.get("pv", 0.0) or 0.0), s.get("step_units")] for s in self._get_step_snapshots(transp=True)]

	def get_detailed_inputs(self) -> List[List[Any]]:
		inputs: List[List[Any]] = []
		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				for step in node.fwd:
					for primary_input, items in (step.primary_inputs or {}).items():
						inputs.append([step.step_name, primary_input, items.get("input_needed", 0.0)])
		return inputs

	# -------------------------
	# Cost reporting
	# -------------------------
	def get_step_cost_report(
		self,
		view: str = "total",
		transp: bool = False,
		detail: int = 2,
		capex_fields=("machine_cost", "tool_cost", "building_cost", "aux_equip_cost"),
		opex_variable_fields=("tot_mat_cost", "labor_cost", "utility_cost"),
		opex_fixed_fields=("maint_cost", "fixed_over_cost"),
	):
		"""
		view:
			  - "total": variable + fixed (full)
			  - "variable": variable only (materials + labor + utilities)
			  - "fixed": fixed only (machine + tool + building + aux + maint + overhead)
			  - "opex": materials + labor + utilities + maint + overhead
			  - "capex": machine + tool + building + aux
			  - "raw": canonical component dict

			detail:
			  1 -> [step_name, selected_total]
			  2 -> category breakdown for view
			  3 -> like 2 plus:
			       - material_cost_items (per-reagent from secondary_inputs)
			       - utility_cost_items (per-utility from *_consumed / *_cost)
			       Itemization is ALWAYS included where applicable.
		"""
		if view not in {"total", "opex", "capex", "variable", "fixed", "raw"}:
			raise ValueError("`view` must be one of: 'total', 'opex', 'capex', 'variable', 'fixed', 'raw'.")
		if detail not in {1, 2, 3}:
			raise ValueError("detail must be 1, 2, or 3")
		if view == "raw" and detail == 1:
			raise ValueError("view='raw' requires detail=2 or 3")

		out = []
		for s in self._get_step_snapshots(transp=transp):
			step_id = s["step_id"]
			step_name = s["step_name"]
			kind = s.get("kind")

			# Transportation
			if kind == "transport":
				c = s.get("costs") or {}
				var_cost = float(c.get("variable_cost", 0.0) or 0.0)
				fix_cost = float(c.get("fixed_cost", 0.0) or 0.0)
				total_cost = float(c.get("total_cost", var_cost + fix_cost) or 0.0)

				if view == "capex":
					selected_total = 0.0
					if detail == 1:
						out.append([step_id, selected_total])
					else:
						out.append(OrderedDict([
							("step_id", step_id),
							("step_name", step_name),
							("capex_total", 0.0),
							("capex_breakdown", {k: 0.0 for k in capex_fields}),
						]))
					continue

				# For transport legs, treat as operating (variable-ish) by default.
				if view in {"total", "variable", "fixed", "opex"}:
					selected_total = total_cost
					if detail == 1:
						out.append([step_id, selected_total])
					else:
						out.append(OrderedDict([
							("step_name", step_name),
							("step_id", step_id),
							("total_cost", total_cost),
							("variable_costs", var_cost),
							("fixed_costs", fix_cost),
						]))
					continue

				# raw
				if view == "raw":
					if detail == 1:
						raise ValueError("view='raw' requires detail=2 or 3")
					out.append(OrderedDict([
						("step_id", step_id),
						("step_name", step_name),
						("variable_costs", var_cost),
						("fixed_costs", fix_cost),
						("total_cost", total_cost),
					]))
					continue

				raise ValueError("Unhandled view for transport")

			# Handle sink - temporary as sinks probably should be converted to production_steps later on
			if kind == "sink":
				total_cost = float((s.get("costs") or {}).get("tot_var_cost", 0.0) or 0.0)
				if view == "capex":
					out.append([step_id, 0.0] if detail == 1 else OrderedDict([
						("step_id", step_id), ("step_name", step_name), ("capex_total", 0.0), ("capex_breakdown", {k: 0.0 for k in capex_fields}),
					]))
				elif view in {"total", "variable", "opex"}:
					out.append([step_id, total_cost] if detail == 1 else OrderedDict([
						("step_id", step_id), ("step_name", step_name), ("total_cost", total_cost), ("variable_costs", total_cost), ("fixed_costs", 0.0),
					]))
				elif view == "fixed":
					out.append([step_id, 0.0] if detail == 1 else OrderedDict([
						("step_id", step_id), ("step_name", step_name), ("fixed_costs", 0.0),
					]))
				elif view == "raw":
					out.append(OrderedDict([
						("step_id", step_id), ("step_name", step_name), ("variable_costs", total_cost), ("fixed_costs", 0.0), ("total_cost", total_cost),
					]))
				continue

			# Production
			c = s.get("costs") or {}
			comp = OrderedDict([
				("step_id", step_id),
				("step_name", step_name),
				("variable_costs", float(c.get("tot_var_cost", 0.0) or 0.0)),
				("fixed_costs", float(c.get("tot_fixed_cost", 0.0) or 0.0)),
				("tot_mat_cost", float(c.get("tot_mat_cost", 0.0) or 0.0)),
				("labor_cost", float(c.get("labor_cost", 0.0) or 0.0)),
				("utility_cost", float(c.get("utility_cost", 0.0) or 0.0)),
				("machine_cost", float(c.get("machine_cost", 0.0) or 0.0)),
				("tool_cost", float(c.get("tool_cost", 0.0) or 0.0)),
				("building_cost", float(c.get("building_cost", 0.0) or 0.0)),
				("aux_equip_cost", float(c.get("aux_equip_cost", 0.0) or 0.0)),
				("maint_cost", float(c.get("maint_cost", 0.0) or 0.0)),
				("fixed_over_cost", float(c.get("fixed_over_cost", 0.0) or 0.0)),
			])

			material_cost_items = None
			utility_cost_items = None
			if detail == 3:
				material_cost_items = s.get("reagents") or OrderedDict()
				utility_cost_items = s.get("utilities") or OrderedDict()

			if view == "raw":
				if detail == 2:
					out.append(comp)
				else:
					rec = OrderedDict(comp)
					rec["material_cost_items"] = material_cost_items
					rec["utility_cost_items"] = utility_cost_items
					out.append(rec)
				continue

			if view == "total":
				total_cost = comp["variable_costs"] + comp["fixed_costs"]
				if detail == 1:
					out.append([step_id, total_cost])
					continue

				rec = OrderedDict([
					("step_id", step_id),
					("step_name", step_name),
					("total_cost", total_cost),
					("variable_costs", comp["variable_costs"]),
					("fixed_costs", comp["fixed_costs"]),
					("material_costs", comp["tot_mat_cost"]),
					("labor_costs", comp["labor_cost"]),
					("utility_costs", comp["utility_cost"]),
					("machine_cost", comp["machine_cost"]),
					("tool_cost", comp["tool_cost"]),
					("building_cost", comp["building_cost"]),
					("aux_equip_cost", comp["aux_equip_cost"]),
					("maint_cost", comp["maint_cost"]),
					("fixed_over_cost", comp["fixed_over_cost"]),
				])

				if detail == 3:
					rec["material_cost_items"] = material_cost_items
					rec["utility_cost_items"] = utility_cost_items
				out.append(rec)
				continue

			if view == "capex":
				capex_total = sum(comp.get(k, 0.0) for k in capex_fields)
				if detail == 1:
					out.append([step_id, capex_total])
					continue
				out.append(OrderedDict([
					("step_id", step_id),
					("capex_total", capex_total),
					("capex_breakdown", {k: comp.get(k, 0.0) for k in capex_fields}),
				]))
				continue

			if view == "opex":
				opex_var = sum(comp.get(k, 0.0) for k in opex_variable_fields)
				opex_fix = sum(comp.get(k, 0.0) for k in opex_fixed_fields)
				opex_total = opex_var + opex_fix
				if detail == 1:
					out.append([step_id, opex_total])
					continue

				rec = OrderedDict([
					("step_id", step_id),
					("opex_total", opex_total),
					("opex_variable", opex_var),
					("opex_fixed_like", opex_fix),
					("opex_variable_breakdown", {k: comp.get(k, 0.0) for k in opex_variable_fields}),
					("opex_fixed_like_breakdown", {k: comp.get(k, 0.0) for k in opex_fixed_fields}),
					("material_costs", comp["tot_mat_cost"]),
					("labor_costs", comp["labor_cost"]),
					("utility_costs", comp["utility_cost"]),
				])
				if detail == 3:
					rec["material_cost_items"] = material_cost_items
					rec["utility_cost_items"] = utility_cost_items
				out.append(rec)
				continue

			if view == "variable":
				var_total = comp["variable_costs"]
				if detail == 1:
					out.append([step_id, var_total])
					continue

				rec = OrderedDict([
					("step_id", step_id),
					("variable_total", var_total),
					("material_costs", comp["tot_mat_cost"]),
					("labor_costs", comp["labor_cost"]),
					("utility_costs", comp["utility_cost"]),
				])
				if detail == 3:
					rec["material_cost_items"] = material_cost_items
					rec["utility_cost_items"] = utility_cost_items
				out.append(rec)
				continue

			if view == "fixed":
				fix_total = comp["fixed_costs"]
				if detail == 1:
					out.append([step_id, fix_total])
					continue

				rec = OrderedDict([
					("step_id", step_id),
					("fixed_total", fix_total),
					("machine_cost", comp["machine_cost"]),
					("tool_cost", comp["tool_cost"]),
					("building_cost", comp["building_cost"]),
					("aux_equip_cost", comp["aux_equip_cost"]),
					("maint_cost", comp["maint_cost"]),
					("fixed_over_cost", comp["fixed_over_cost"]),
				])
				out.append(rec)
				continue

			raise ValueError("Invalid view")

		return out

	def get_step_opex_costs(self, transp: bool = False, detail: int = 2, **kwargs):
		return self.get_step_cost_report(view="opex", transp=transp, detail=detail, **kwargs)

	def get_step_capex_costs(self, transp: bool = False, detail: int = 2, **kwargs):
		return self.get_step_cost_report(view="capex", transp=transp, detail=detail, **kwargs)

	def get_step_costs(self, transp: bool = False, detail: int = 1):
		return self.get_step_cost_report(view="total", transp=transp, detail=detail)

	# -------------------------
	# Plotting
	# -------------------------
	def plot_tot_fac_costs(self, apv=None, xscale=1, yscale=1, title='Cost of Steps', xlab='Step Names',
						   ylab='Total Cost', xlims=None, ylims=None):
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError("No APV values have been run; rerun with some target production volume.")

		labels = []
		costs = defaultdict(list)

		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				labels.append(node.fac_id)
				costs["Variable Costs"].append(node.tot_var_cost)
				costs["Fixed Costs"].append(node.tot_fixed_cost)
			elif isinstance(node, TransportRoute):
				labels.append(node.name)
				costs["Variable Costs"].append(node.variable_cost)
				costs["Fixed Costs"].append(node.fixed_cost)
			else:
				raise ValueError("Unidentified node in the supply chain's topographic order")

		plot_stacked_bars(labels, costs, stack_order=["Fixed Costs", "Variable Costs"], xscale=xscale, yscale=yscale,
						  title=title, xlab=xlab, ylab=ylab, xlims=xlims, ylims=ylims)

	def plot_tot_steps_costs(
		self,
		apv=None,
		xscale=1,
		yscale=1,
		title='Cost of Steps',
		xlab='Step Names',
		ylab='Total Cost',
		xlims=None,
		ylims=None,
		*,
		view: str = "total", # total|variable|fixed|opex|capex|combo
		detail: int = 2, # 1|2|3
		top_n = None, # int -> bucket to top_n + Other, None -> show all items; only used when detail=3
		transp: bool = True,
		wrap_width: int = 12,
		):
		"""
		Plot step costs using get_step_cost_report().

		view:
		  - "total": all costs
		  - "variable": variable-only (materials, labor, utilities)
		  - "fixed": fixed-only (machine, tool, building, aux, maint, overhead)
		  - "opex": materials, labor, utilities, maint, overhead (aux excluded)
		  - "capex": machine, tool, building, aux
		  - "combo": stacked CAPEX + OPEX totals (forces detail=1 behavior)

		detail:
		  1 -> single bar per step (total for the chosen view)
		  2 -> category-level stack for chosen view
		  3 -> category-level + automatic itemization of materials and utilities where applicable.
		       (to keep plots readable, top_n buckets per step if needed)
		"""
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError("No APV values have been run; rerun with some target production volume.")

		view = str(view).lower().strip()
		if view not in {"total", "variable", "fixed", "opex", "capex", "combo"}:
			raise ValueError("view must be one of: total|variable|fixed|opex|capex|combo")
		if detail not in {1, 2, 3}:
			raise ValueError("detail must be 1, 2, or 3")
		if top_n is not None and not isinstance(top_n, int):
			raise ValueError("top_n must be an int or None")

		labels: List[str] = []
		series: Dict[str, List[float]] = defaultdict(list)

		def _pad_all():
			for k in list(series.keys()):
				while len(series[k]) < len(labels):
					series[k].append(0.0)

		def _append(name: str, val: float):
			while len(series[name]) < len(labels) - 1:
				series[name].append(0.0)
			series[name].append(float(val or 0.0))

		def _topn_bucket(items_dict: Dict[str, Dict[str, Any]], key_name: str, topn: int) -> Dict[str, float]:
			"""
			Return top_n items + 'Other' bucket if remainder > 0.
			Assumes top_n is a positive integer.
			"""
			if not items_dict:
				return {}
			pairs = []
			for item, rec in items_dict.items():
				try:
					v = float(rec.get(key_name, 0.0) or 0.0)
				except Exception:
					v = 0.0
				pairs.append((item, v))
			pairs.sort(key=lambda x: x[1], reverse=True)
			top = pairs[:max(topn, 0)]
			rest = pairs[max(topn, 0):]
			out = {k: v for k, v in top}
			other = sum(v for _, v in rest)
			if other > 0:
				out["Other"] = other
			return out

		def _items_as_values(items_dict, key_name: str):
			"""Convert {item: {key_name: v}} -> {item: v} filtering zeros."""
			out = {}
			for k, rec in (items_dict or {}).items():
				try:
					v = float((rec or {}).get(key_name, 0.0) or 0.0)
				except Exception:
					v = 0.0
				if v != 0.0:
					out[k] = v
			return out

		def _get_itemized_maps(rec):
			"""
			Return (mat_items, util_items) as {name: value}.
			- If top_n is None: all items.
			- If top_n <= 0: empty dicts (meaning "don't itemize").
			- If top_n > 0: bucket to top_n + Other.
			"""
			raw_mat = rec.get("material_cost_items", {}) or {}
			raw_util = rec.get("utility_cost_items", {}) or {}

			if top_n is None:
				return _items_as_values(raw_mat, "total_cost"), _items_as_values(raw_util, "cost")
			if top_n <= 0:
				return {}, {}
			return _topn_bucket(raw_mat, "total_cost", top_n), _topn_bucket(raw_util, "cost", top_n)

		if view == "combo":
			cap = self.get_step_cost_report(view="capex", transp=transp, detail=1)
			opx = self.get_step_cost_report(view="opex", transp=transp, detail=1)
			for (nm1, capex_total), (nm2, opex_total) in zip(cap, opx):
				if nm1 != nm2:
					raise ValueError("Step ordering mismatch between CAPEX and OPEX reports.")
				labels.append(nm1)
				_append("CAPEX", capex_total)
				_append("OPEX", opex_total)
			_pad_all()
			plot_stacked_bars(labels, series, stack_order=["CAPEX","OPEX"], xscale=xscale, yscale=yscale,
							  title=title, xlab=xlab, ylab=ylab, xlims=xlims, ylims=ylims, wrap_width=wrap_width)
			return

		report = self.get_step_cost_report(view=view, transp=transp, detail=detail)

		for rec in report:
			if detail == 1:
				labels.append(rec[0])
				_append(view.upper(), rec[1])
				continue

			labels.append(rec.get("step_name"))

			if view == "total":
				if detail == 2:
					_append("Fixed Costs", rec.get("fixed_costs", 0.0))
					_append("Variable Costs", rec.get("variable_costs", 0.0))
				else: # detail == 3
					# fixed
					_append("Machine Cost", rec.get("machine_cost", 0.0))
					_append("Tool Cost", rec.get("tool_cost", 0.0))
					_append("Building Cost", rec.get("building_cost", 0.0))
					_append("Aux Equip Cost", rec.get("aux_equip_cost", 0.0))
					_append("Maintenance", rec.get("maint_cost", 0.0))
					_append("Fixed Overhead", rec.get("fixed_over_cost", 0.0))

					# Variable: labor aggregate; materials/utilities itemized if available
					_append("Labor Costs", rec.get("labor_costs", 0.0))

					mat_items, util_items = _get_itemized_maps(rec)

					if mat_items:
						for k, v in mat_items.items():
							_append(f"MAT: {k}", v)
					else:
						_append("Material Costs", rec.get("material_costs", 0.0))

					if util_items:
						for k, v in util_items.items():
							_append(f"UTIL: {k}", v)
					else:
						_append("Utility Costs", rec.get("utility_costs", 0.0))

			elif view == "variable":
				if detail == 2:
					_append("Material Costs", rec.get("material_costs", 0.0))
					_append("Labor Costs", rec.get("labor_costs", 0.0))
					_append("Utility Costs", rec.get("utility_costs", 0.0))
				else:  # detail == 3
					_append("Labor Costs", rec.get("labor_costs", 0.0))

					mat_items, util_items = _get_itemized_maps(rec)

					if mat_items:
						for k, v in mat_items.items():
							_append(f"MAT: {k}", v)
					else:
						_append("Material Costs", rec.get("material_costs", 0.0))

					if util_items:
						for k, v in util_items.items():
							_append(f"UTIL: {k}", v)
					else:
						_append("Utility Costs", rec.get("utility_costs", 0.0))

			elif view == "fixed":
				_append("Machine Cost", rec.get("machine_cost", 0.0))
				_append("Tool Cost", rec.get("tool_cost", 0.0))
				_append("Building Cost", rec.get("building_cost", 0.0))
				_append("Aux Equip Cost", rec.get("aux_equip_cost", 0.0))
				_append("Maintenance", rec.get("maint_cost", 0.0))
				_append("Fixed Overhead", rec.get("fixed_over_cost", 0.0))

			elif view == "capex":
				bd = rec.get("capex_breakdown", {}) or {}
				_append("Machine Cost", bd.get("machine_cost", 0.0))
				_append("Tool Cost", bd.get("tool_cost", 0.0))
				_append("Building Cost", bd.get("building_cost", 0.0))
				_append("Aux Equip Cost", bd.get("aux_equip_cost", 0.0))

			elif view == "opex":
				if detail == 2:
					_append("OPEX Fixed-like", rec.get("opex_fixed_like", 0.0))
					_append("OPEX Variable", rec.get("opex_variable", 0.0))
				else:  # detail == 3
					bd_fix = rec.get("opex_fixed_like_breakdown", {}) or {}
					_append("Maintenance", bd_fix.get("maint_cost", 0.0))
					_append("Fixed Overhead", bd_fix.get("fixed_over_cost", 0.0))

					_append("Labor Costs", rec.get("labor_costs", 0.0))
					mat_items, util_items = _get_itemized_maps(rec)

					if mat_items:
						for k, v in mat_items.items():
							_append(f"MAT: {k}", v)
					else:
						_append("Material Costs", rec.get("material_costs", 0.0))

					if util_items:
						for k, v in util_items.items():
							_append(f"UTIL: {k}", v)
					else:
						_append("Utility Costs", rec.get("utility_costs", 0.0))

			else:
				raise ValueError("Unhandled view")

		_pad_all()

		# Prefer “fixed first” when applicable
		if view == "total" and detail == 2:
			stack_order = ["Fixed Costs", "Variable Costs"]
		elif view == "opex" and detail == 2:
			stack_order = ["OPEX Fixed-like", "OPEX Variable"]
		else:
			stack_order = list(series.keys())

		plot_stacked_bars(labels, series, stack_order=stack_order, xscale=xscale, yscale=yscale,
						  title=title, xlab=xlab, ylab=ylab, xlims=xlims, ylims=ylims, wrap_width=wrap_width)

	def plot_tot_steps_impacts(self, apv=None, xscale=1, yscale=1, title='GHGs at each Step',
								xlab='Step Names', ylab='Total GHGs', xlims=None, ylims=None):
		# Left as existing behavior; consider refactoring analogous to costs.
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError("No APV values have been run; rerun with some target production volume.")

		labels = []
		scopes = defaultdict(list)

		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				for step in node.fwd:
					labels.append(step.step_name)
					scopes["Scope One"].append(step.scope_one_impacts.get('co2', 0))
					scopes["Scope Two"].append(step.scope_two_impacts.get('co2', 0))
					scopes["Scope Three"].append(getattr(step, "scope_three_impacts", {}).get('co2', 0))
			elif isinstance(node, TransportRoute):
				for leg in node.legs:
					labels.append(leg.name)
					scopes["Scope One"].append(leg.emissions_totals.get('ghg', 0))
					scopes["Scope Two"].append(0)
			else:
				raise ValueError("Unidentified node in the supply chain's topographic order")

		stack_order = ["Scope One", "Scope Two"]
		colors = {"Scope One": "#f28e2b", "Scope Two": "#4e79a7"}
		plot_stacked_bars(labels, scopes, stack_order=stack_order, colors=colors, xscale=xscale, yscale=yscale,
						  title=title, xlab=xlab, ylab=ylab, xlims=xlims, ylims=ylims)

	def plot_unit_cc(self, xscale=1, yscale=1, title='APV vs Average Cost',
					 xlab='Annual Production Volume (APV)', ylab='Unit Cost'):
		apvs = [apv * xscale for apv in self.prod_map.keys()]
		avg_costs = [cost[2] / apv * yscale for apv, cost in self.prod_map.items()]
		plot_production_curve(apvs, avg_costs, xscale, yscale, title, xlab, ylab)

	def plot_total_cc(self, xscale=1, yscale=1, title='APV vs Total Cost',
					  xlab='Annual Production Volume (APV)', ylab='Total Cost'):
		apvs = [apv * xscale for apv in self.prod_map.keys()]
		tot_costs = [cost[2] * yscale for cost in self.prod_map.values()]
		plot_production_curve(apvs, tot_costs, xscale, yscale, title, xlab, ylab)











