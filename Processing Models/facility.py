from typing import Dict, Any, List, Optional
import copy
from collections import defaultdict
from typing import NamedTuple

from production_step import ProductionStep
from helpers import plot_stacked_bars, plot_production_curve, build_data_dict

# Define a class for the production environment
class Facility:

		# Instance attribute
		def __init__(self, fac_id, supply_chain, location, sinks, apv=0, steps=None, impact_factors=None):
			
			self.fac_id = fac_id
			self.apv = apv
			self.sc = supply_chain # The supply chain object this facility is associated with 
			self.material_data = copy.deepcopy(self.sc.material_data) # to be updated with location-specific overrides as specified
			self.onsite_reagents = set()
			self.location = location # Location name
			self.steps = {}
			self.primary_inputs = {}   # facility-level "imports"
			self.primary_outputs = {}  # facility-level "exports"
			# Note the sinks input is a list. Possibly put this back into 'steps' later.
			self.sinks = sinks_dict = {sink: {} for sink in sinks} # Landfill, air/environment, wastewater treatment, etc.
			self.impact_factors = impact_factors or { # Should I even set 0 defaults?? 
					"electricity": {"co2": 0.0, "water": 0.0},   # defaults: no impact
					"natural_gas": {"co2": 0.0},
					"cooling_water": {"co2": 0.0},
					"steam": {"co2": 0.0, "water": 0.0},
					"compressed_air": {"co2": 0.0},
					"landfill": {"co2": 0.0, "land_use": 0.0},
					"wastewater": {"water": 0.0, "eutrophication": 0.0},
					"air": {"co2": 0.0, "nox": 0.0, "so2": 0.0} # probably more, to add later if needed
			}

			self.dpy = 0 # Working days/year
			self.upd = 0 # Facility-wide average Unplanned Downtime, as a percentage
			self.scm = 0 # Scheduled maintenance
			self.spd = 0 # Number of shifts/day
			self.hps = 0 # Hours per shift
			self.ub = 0 # Hours of unpaid breaks/shift
			self.pb = 0 # Hours of paid breaks/shift
			self.dr = 0 # Discount Rate
			self.wage = 0 # Direct Wage (w/benefits)
			self.elec_price = 0 # Electricity cost, $/kwh
			self.gas_price = 0 # Gas cost, $/MMBTU
			self.diesel_price = 0 # Diesel cost, $/L
			self.propane_price = 0 # Propane cost, $/L
			self.cool_water_price = 0 # Cost of cooled water, $/m^3. Assume an increase over the process water cost.
			self.steam_price = 0 # Cost of steam, $/kg. Assume ~1.2 cents / pound, or 2.65 cents / kg
			self.comp_air_price = 0 # Cost of compressed air, in $/Nm^3 (normal m^3). Assume 4 cents for now.
			self.build_price = 0 # Building space cost, $/m^2
			self.tailings_nonhazardous_cost = 0 # Cost of disposal for nonhazardous tailings for this facility
			self.tailings_hazardous_cost = 0 # Cost of disposal for hazardous tailings for this facility
			self.tailings_storage_cost = 0 # Cost of storage for tailings
			self.crp = 0 # Capital Recovery Period
			self.brp = 0 # Building Recovery Period
			self.aux_equip = 0 # Annualized auxiliary Equipment cost, as a percentage of main machine cost
			self.maint = 0 # Annualized maintenance costs, as a percentage of main machine cost
			self.fixed_over = 0 # Annualized fixed overhead costs, as a percentage of the total of {main machine, building, auxiliary equipment, and maintenance} costs
			self.machine_cost_factor = 0 # A cost factor to be applied due to the relative local price of machines vs. benchmarked price for machines

			self.prod_map = {} #apv: [self.tot_var_cost,self.tot_fixed_cost,self.tot_cost]
			self.fwd = [] # Forward topographically ordered production steps (upstream → downstream)
			self.rev = [] # Backward topographically ordered production steps (downstream → upstream)

			self.total_utilities = {}
			self.tot_var_cost = 0
			self.tot_fixed_cost = 0
			self.tot_opex = 0
			self.tot_capex = 0
			self.tot_cost = 0
			self.avg_var_cost = 0
			self.avg_fixed_cost = 0
			self.avg_cost = 0

			# Need to specify location
			if (location is None) or (location not in self.sc.loc_data):
					raise ValueError(f"Location '{location}' not found in supply chain locations.")
			else:
					self.update_location(location)
					
			# If steps are specified, import them
			if steps is not None and type(steps) == dict:
					self.import_steps(steps)

		@staticmethod
		def calc_crf(dr: float, period: float) -> float:
				"""
				Return the capital recovery factor for a given rate and period.
				Annualizing into year 0 payment
				"""
				if period == 1:
						return 1.0
				if dr == 0:
						return 1 / period
				return dr * (1 + dr) ** (period-1) / ((1 + dr) ** period - 1)

		# ============================================================
		# STEP ACCESSORS / ORGANIZERS / REPORTING
		# ============================================================
		def import_steps(self,steps_dict):
				steps = []
				for step_name in reversed(list(steps_dict.keys())):
						step = ProductionStep(facility=self, step_params=steps_dict[step_name])
						steps.append(step.step_name)
				self.topo_order()
				# print("Ingested steps:", list(reversed(steps)))

		def topo_order(self):
				"""
				Return steps in forward topological order (upstream to downstream).
				"""
				indeg = {sid: len(step.previous_steps) for sid, step in self.steps.items()}
				ready = [s for s in self.steps.values() if not s.previous_steps]
				order = []

				while ready:
						step = ready.pop(0)
						order.append(step)
						for nxt in step.next_steps.values():
								indeg[nxt.step_id] -= 1
								if indeg[nxt.step_id] == 0:
										ready.append(nxt)

				if len(order) != len(self.steps):
						raise ValueError("Cycle detected in facility flow graph.")

				self.fwd = order
				self.rev = list(reversed(self.fwd))

				return order

		def step_names(self):
				for step in self.fwd:
						yield step.step_name

		def step_costs(self, detail = 1):
				if detail == 3:
						pass # optionally more detail somehow - probably breakdown by reagent?
				elif detail == 2:
						for step in self.fwd:
								yield step.step_name, step.tot_var_cost, step.tot_fixed_cost, step.tot_cost
				else: # detail == 1 or any other number - least detailed
						for step in self.fwd:
								yield step.step_name, step.tot_cost

		def step_pvs(self):
				for step in self.steps.values():
						yield step.step_name, step.step_pv

		def get_initial_pv(self):
				'''
				Get the production volume at the first step
				'''
				first_step = self.fwd[0]
				return first_step.step_pv

		def get_initial_input_amount(self):
				'''Get the amount of primary input as calculated by conversion factors. Assumes only one primary input.'''
				first_step = self.fwd[0]
				return next(
						(items.get("input_needed", 0.0) for items in first_step.primary_inputs.values()),
						0.0
				)

		# ============================================================
		# INPUTS & OUTPUTS
		# ============================================================

		def collect_primary_outputs(self):
				"""
				Gather primary outputs from the last step(s) in the facility.
				These represent the products that can be exported or passed
				to another facility.
				"""
				outputs = {}
				for step in self.steps.values():
						# Only collect from terminal steps (those with no next steps)
						if not step.next_steps:
								for oname, odata in step.primary_outputs.items():
									outputs[oname] = {
											"volume": odata.get("volume", self.apv), # Output volume is facility production volume
											"constituents": copy.deepcopy(odata.get("constituents", {})),
											"units": odata.get("units", "")
									}
				self.primary_outputs = outputs
				return outputs

		def collect_primary_inputs(self):
				"""
				Gather primary inputs from the first step(s) in the facility.
				These represent the products that are imported from another facility.
				"""
				inputs = {}
				for step in self.steps.values():
						# Only collect from initial steps (those with no previous steps)
						if not step.previous_steps:
								step_pv = getattr(step, "step_pv", None)
								for iname, idata in step.primary_inputs.items():
										inputs[iname] = {
												"volume": idata.get("volume", step_pv), # Technically step_pv is not equal to volume required for input, but true for now.
												"constituents": copy.deepcopy(idata.get("constituents", {})),
												"units": idata.get("units", "")
										}
				self.primary_inputs = inputs
				return inputs

		def add_target_comp(self, target: str, composition: dict, target_step_id = None, propagate = True):
				# Get first step
				if target_step_id not in self.steps:
						raise KeyError(f"Target step with id '{target_step_id}' not found in facility {self.fac_id}.")
				elif target_step_id is None:
						# Flag if no steps exist
						self.topo_order()
						step = self.fwd[0]
				else:
						step = self.steps[target_step_id]

				if target not in step.primary_inputs and target not in step.primary_outputs:
						raise KeyError(f"Input '{target}' not found in step {target_step_id} of facility {self.fac_id} as either an input or output.")
				step.set_constituents(target, composition, propagate=propagate)

		# ============================================================
		# SCENARIO & LOCATION MANAGEMENT
		# ============================================================

		def update_location(self, location_name: str, recalculate: bool = False):
				"""
				Update facility-level parameters based on the specified location.
				Recalculates all dependent values automatically.
				Ideally, not directly needed, as a new facility should be generated for each location.
				However, probably helpful for developing sensitivity analysis.

				Parameters
				----------
				location_name : str
						Name of the location (e.g. "chile", "nevada").
				location_data : dict
						Dictionary of parameters for this location. Keys should match Facility attributes.
						Example keys: ["dpy", "spd", "hps", "ub", "pb", "dr", "wage", "elec_price", ...]
				"""
				loc_data = self.sc.loc_data.get(location_name)
				if loc_data is None:
						raise KeyError(f"Location {location_name} is not defined in the supply chain's input location data.")

				# --- Update all provided parameters (only if present in location_data) ---
				self.location = location_name
				for key, value in loc_data.items():
						if hasattr(self, key):
								setattr(self, key, value)
						elif key == "material_data":
								for material,cat_val in value.items():
										for category,val in cat_val.items():
												self.material_data[material][category] = val
						elif key == "material_data_overrides":
							for material, cat_val in (value or {}).items():
								if material not in self.material_data:
									print(f"Warning: material '{material}' in locational overrides not found in material_data; skipping.")
									continue
								for category, val in (cat_val or {}).items():
									if val is not None and val != 0:
										self.material_data[material][category] = val
						else:
								print(f"Attribute {key} in the location data is not defined as a facility attribute.")
 
				# --- Recalculate dependent values ---
				self.crf = self.calc_crf(self.dr, self.crp)   # Capital recovery factor
				self.bcrf = self.calc_crf(self.dr, self.brp) # Building recovery factor

				self.plt = self.dpy * self.spd * (self.hps - self.ub)           # Paid line time
				self.wlt = self.dpy * self.spd * (self.hps - self.ub - self.pb) # Worked line time

				# Update all process and cost info
				notif = ""
				if recalculate:
						self.calculate_all()
						notif = "not "

				# print(f"Location of facility '{self.fac_id}' updated to '{location_name}'. (Facility production details {notif}updated.)")

		def update_apv(self,apv,recalc=False):
				"""
				Update APV and trigger full production cost calculation.
				Wrapper around calculate_all.
				"""
				if not recalc and apv in self.prod_map: # Don't need to re-run if already recorded
						print("Input production volume has already been calculated.")
				return self.calculate_all(apv=apv)

		# ============================================================
		# UTILITIES & ENVIRONMENTAL IMPACTS
		# ============================================================

		def report_utilities(self, include_costs: bool = False) -> dict:
				"""
				Aggregate total utilities used across all steps in the facility.

				Parameters
				----------
				include_costs : bool
						If True, also report total costs for each utility.

				Returns
				-------
				dict
						Nested dictionary of utilities with quantities (and costs if requested).
				"""

				# Initialize totals
				totals = {
						"electricity": {"quantity": 0.0, "units": "kWh", "cost": 0.0},
						"natural_gas": {"quantity": 0.0, "units": "MMBTU", "cost": 0.0},
						"process_water": {"quantity": 0.0, "units": "m^3", "cost": 0.0},
						"cooling_water": {"quantity": 0.0, "units": "m^3", "cost": 0.0},
						"steam": {"quantity": 0.0, "units": "kg", "cost": 0.0},
						"compressed_air": {"quantity": 0.0, "units": "Nm^3", "cost": 0.0},
				}

				# Aggregate step-level consumption and costs
				for step in self.steps.values():
						totals["electricity"]["quantity"]    += getattr(step, "electricity_consumed", 0.0)
						totals["natural_gas"]["quantity"]    += getattr(step, "natural_gas_consumed", 0.0)
						totals["process_water"]["quantity"]  += getattr(step, "process_water_consumed", 0.0)
						totals["cooling_water"]["quantity"]  += getattr(step, "cooling_water_consumed", 0.0)
						totals["steam"]["quantity"]          += getattr(step, "steam_consumed", 0.0)
						totals["compressed_air"]["quantity"] += getattr(step, "compressed_air_consumed", 0.0)

						if include_costs:
								totals["electricity"]["cost"]    += getattr(step, "electricity_cost", 0.0)
								totals["natural_gas"]["cost"]    += getattr(step, "natural_gas_cost", 0.0)
								totals["process_water"]["cost"]  += getattr(step, "process_water_cost", 0.0)
								totals["cooling_water"]["cost"]  += getattr(step, "cooling_water_cost", 0.0)
								totals["steam"]["cost"]          += getattr(step, "steam_cost", 0.0)
								totals["compressed_air"]["cost"] += getattr(step, "compressed_air_cost", 0.0)

				self.total_utilities = totals
				# Drop unused utilities (quantity == 0)
				report = {
						util: {k: v for k, v in data.items() if k != "cost" or include_costs}
						for util, data in totals.items()
						if data["quantity"] > 0.0
				}

				return report

		def _sum_coproducts_in_sinks(self):
				"""
				Returns a dictionary of sink → coproduct → total volume across all steps.
				"""
				totals = {}
				for sink_name, coproducts in self.sinks.items():
						totals[sink_name] = {}
						for coproduct_name, step_volumes in coproducts.items():
								# Sum volumes across all steps
								total_volume = sum(v for k, v in step_volumes.items() if isinstance(v, (int, float)))
								totals[sink_name][coproduct_name] = total_volume
				return totals

		def get_step_environmental_impacts(self, update = False) -> dict:
				"""
				Returns a dict keyed by step_name with each step's impacts.
				"""
				results = {}
				for step_id, step in self.steps.items():
						if update:
								summary = step.calculate_environmental_impacts(self.impact_factors)
						else:
								summary = {
														"utility_impacts": step.utility_impacts,
														"sink_impacts": step.sink_impacts,
														"material_impacts":   getattr(step, "material_impacts",    {}),
														"scope_one_impacts":  getattr(step, "scope_one_impacts",   {}),
														"scope_two_impacts":  getattr(step, "scope_two_impacts",   {}),
														"scope_three_impacts":getattr(step, "scope_three_impacts", {}),
														"total_step_impacts": step.total_step_impacts,
												}
						results[step.step_name] = summary
				return results

		def get_total_environmental_impacts(self, update = False) -> dict:
				"""
				Sums all step totals into facility-wide totals (same categories).
				"""
				by_step = self.get_step_environmental_impacts(update)
				totals = {}
				for step_dict in by_step.values():
						for cat, val in step_dict["total_step_impacts"].items():
								totals[cat] = totals.get(cat, 0.0) + val
				return totals

		# ============================================================
		# COST CALCULATIONS
		# ============================================================

		def total_variable_cost(self):
				tot_var_cost = 0
				for step in self.steps.values():
						tot_var_cost += step.tot_var_cost
				self.tot_var_cost = tot_var_cost
				return self.tot_var_cost

		def total_fixed_cost(self):
				tot_fixed_cost = 0
				for step in self.steps.values():
						tot_fixed_cost += step.tot_fixed_cost
				self.tot_fixed_cost = tot_fixed_cost
				return self.tot_fixed_cost

		def total_cost(self):
				self.tot_cost = self.total_variable_cost() + self.total_fixed_cost()
				return self.tot_cost

		def total_opex(self):
				tot_opex = 0
				for step in self.steps.values():
						tot_opex += getattr(step, "tot_opex", 0.0) or 0.0
				self.tot_opex = tot_opex
				return self.tot_opex

		def total_capex(self):
				tot_capex = 0
				for step in self.steps.values():
						tot_capex += getattr(step, "tot_capex", 0.0) or 0.0
				self.tot_capex = tot_capex
				return self.tot_capex

		def average_variable_cost(self):
				self.avg_var_cost = self.total_variable_cost()/self.apv
				return self.avg_var_cost

		def average_fixed_cost(self):
				self.avg_fixed_cost = self.total_fixed_cost()/self.apv
				return self.avg_fixed_cost

		def average_cost(self):
				self.avg_cost = self.total_cost()/self.apv
				return self.avg_cost

		def calculate_all(self, apv: float = None):
				"""
				Master function to calculate all step- and facility-level costs.
				Optionally updates APV if a new value is passed.
				"""
				if apv is not None and apv != self.apv:
						self.apv = apv

				# Get steps in topoligical order
				self.topo_order()
				
				# 1) Forward - chemistry: inputs → outputs, once per step
				s = self.fwd[0]
				s.apply_reagents()
				s.propagate_chemistry(True) # When propagating, it recursively calls apply_reagents at each following step

				# For steps that are not dependent on input chemistry, still need to apply reagents
				for s in self.fwd:
						s.apply_reagents()

				# 2) Backward - volumes: set targets at sinks, walk upstream
				for sink_coproducts in self.sinks.values(): # Reset sink volumes so repeated calcs don't accumulate
						sink_coproducts.clear()
				for end in (step for step in self.steps.values() if not step.next_steps):
						end.output_volume = self.apv
				for s in self.rev:
						s.compute_step_pv()        # uses downstream demand to size upstream

				# 3) Scale reagents (per-unit × throughput) and run cost calculations for the step
				for s in self.fwd:
						s.scale_reagents()
						s.calculate()

				# --- Aggregate facility totals ---
				self.tot_var_cost = sum(step.tot_var_cost for step in self.steps.values())
				self.tot_fixed_cost = sum(step.tot_fixed_cost for step in self.steps.values())
				self.tot_opex = sum(step.tot_opex for step in self.steps.values())
				self.tot_capex = sum(step.tot_capex for step in self.steps.values())
				self.tot_cost = self.tot_var_cost + self.tot_fixed_cost

				# --- Average costs per unit ---
				self.avg_var_cost = self.tot_var_cost / self.apv
				self.avg_fixed_cost = self.tot_fixed_cost / self.apv
				self.avg_opex = self.tot_opex / self.apv
				self.avg_capex = self.tot_capex / self.apv
				self.avg_cost = self.tot_cost / self.apv

				# --- Store results for scenario tracking ---
				self.prod_map[self.apv] = [self.tot_var_cost, self.tot_fixed_cost, self.tot_cost, self.tot_opex, self.tot_capex]

				emissions_totals = self.get_total_environmental_impacts()

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
						"emissions_totals": emissions_totals
				}

		# ============================================================
		# PLOTTING FUNCTIONS
		# ============================================================
		def plot_tot_step_costs(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None):
				if apv is not None:
						self.update_apv(apv)
				elif len(self.prod_map.keys()) == 0:
						raise ValueError(f"No APV values have been run; rerun with some target production volume.")

				labels = [step.step_name for step in self.fwd]
				series = {
						"Fixed Costs": [step.tot_fixed_cost for step in self.fwd],
						"Variable Costs": [step.tot_var_cost for step in self.fwd],
				}
				return plot_stacked_bars(labels,series,stack_order=["Fixed Costs","Variable Costs"],xscale=xscale,yscale=yscale,
						title=title,xlab=xlab,ylab=ylab,xlims=xlims,ylims=ylims)

		def plot_avg_step_costs(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Cost/Unit',xlims=None,ylims=None):
				if apv is not None:
						self.update_apv(apv)
				elif len(self.prod_map.keys()) == 0:
						raise ValueError(f"No APV values have been run; rerun with some target production volume.")

				labels = [step.step_name for step in self.fwd]
				series = {
						"Fixed Costs": [step.tot_fixed_cost / self.apv for step in self.fwd],
						"Variable Costs": [step.tot_var_cost / self.apv for step in self.fwd],
				}
				return plot_stacked_bars(labels,series,stack_order=["Fixed Costs","Variable Costs"],xscale=xscale,yscale=yscale,
						title=title,xlab=xlab,ylab=ylab,xlims=xlims,ylims=ylims)

		def plot_unit_cc(self,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Unit Cost'):
				# Extract APVs and costs from the prod_map
				apvs = [apv * xscale for apv in self.prod_map.keys()]
				avg_costs = [cost[2]/apv * yscale for apv,cost in self.prod_map.items()]
				plot_production_curve(apvs,avg_costs,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Unit Cost')

		def plot_total_cc(self,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Total Cost'):
				# Extract APVs and costs from the prod_map
				apvs = [apv * xscale for apv in self.prod_map.keys()]
				tot_costs = [cost[2] * yscale for cost in self.prod_map.values()]

				plot_production_curve(apvs,tot_costs,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Unit Cost')

class ReagentFacility(Facility):

		def __init__(self, fac_id, supply_chain, location, sinks, target_reagent,
					target_facilities, apv=0, steps=None, impact_factors=None):
				super().__init__(fac_id, supply_chain, location, sinks, apv, steps, impact_factors)
				self.target_reagent = target_reagent
				self.target_facilities = list(target_facilities)
				for fac in self.target_facilities:
						if not any(target_reagent in step.secondary_inputs for step in fac.steps.values()):
								raise KeyError(f"{fac.fac_id} does not dose '{target_reagent}'.")
						fac.onsite_reagents.add(target_reagent)

		def demand(self):
				total = 0.0
				for fac in self.target_facilities:
						for step in fac.steps.values():
								props = step.secondary_inputs.get(self.target_reagent)
								if props is None:
										continue
								total += props.get("abs_usage") or 0.0
				return total

class DewateringResult(NamedTuple):
		cost: float   # $/t dry solids — OPEX excl. electricity cost
		elec: float   # kWh/t dry solids — for separate emissions calc
		# diesel: float # diesel usage/t dry solids - for separate emissions calc

SINK_REQUIRED = {
	"tailings": ("route", "location", "storage", "s_in", "s_final", "rho_s", "x_hyd"),
	"wastewater": ("cost",),
	"waste_rock": ("cost",),
	"other": ("cost",),
}

def load_sink_params(sc, data_folder):
	table = build_data_dict(data_folder, "Sink Data", skip_rows=["notes", "sources", "cost_unit"])
	tail = build_data_dict(data_folder, "Tailings Model Inputs")
	sc.sink_names = list(table)
	sc.sink_params, sc.wastewater_params, sc.flat_sinks = {}, {}, {}
	for name, row in table.items():
		kind = row.get("kind")
		if kind not in SINK_REQUIRED:
			raise ValueError(f"Sink Data '{name}': kind '{kind}' not in {sorted(SINK_REQUIRED)}")
		missing = [k for k in SINK_REQUIRED[kind] if row.get(k) is None]
		if missing:
			raise ValueError(f"Sink Data '{name}' ({kind}) missing {missing}")
		if kind == "tailings":
			sc.sink_params[name] = dict(row, train=list((row.get("train") or {}).items()))
		elif kind == "wastewater":
			sc.wastewater_params[name] = row
		else:
			sc.flat_sinks[name] = row
	sc.s_ceil, sc.stage, sc.placement, sc.tsf_opex = {}, {}, {}, {}
	for col, row in tail.items():
		for ph in ("cry", "hyd"):
			if (row.get("s_ceil") or {}).get(ph) is not None:
				sc.s_ceil[(col, ph)] = row["s_ceil"][ph]
				sc.stage[(col, ph)] = tuple(row[k][ph] for k in ("C_m", "c_w", "E_m", "e_w"))
		if row.get("tsf_opex") is not None:
			sc.placement[col] = (row["placement_cost"], row["placement_elec"])
			sc.tsf_opex[col] = row["tsf_opex"]

def sink_s_out(sc, name):
	p = sc.sink_params[name]
	return p["train"][-1][1] if p["train"] else p["s_in"]

def tailings_handling(sc):
	def mw(s):
		return (1.0 - s) / s

	def s_ceil(mech, x):
		w = x * mw(sc.s_ceil[(mech, "hyd")]) + (1.0 - x) * mw(sc.s_ceil[(mech, "cry")])
		return 1.0 / (1.0 + w)

	def stage_coef(mech, x):
		h = sc.stage[(mech, "hyd")]
		c = sc.stage[(mech, "cry")]
		return tuple(x * h[i] + (1.0 - x) * c[i] for i in range(4))

	def ds_per_m3(w_s, rho_s, rho_w=1.0):
		rho_mix = 1.0 / (w_s / rho_s + (1.0 - w_s) / rho_w)
		return w_s * rho_mix

	sc.topo_order()
	ep = next(f.elec_price for f in sc.rev if not isinstance(f, ReagentFacility))
	sc.sink_elec = {}

	for name, p in sc.sink_params.items():
		x = p["x_hyd"]
		s_k = p.get("s_feed") or p["s_in"]
		dew_c, dew_e = 0.0, 0.0
		for mech, s_out in p["train"]:
			cap = s_ceil(mech, x)
			if s_out > cap + 1e-9:
				raise ValueError(f"{name}: {mech} s_out {s_out:.3f} exceeds ceiling {cap:.3f} at x_hyd={x}")
			if s_out <= s_k + 1e-9:
				raise ValueError(f"{name}: {mech} s_out {s_out:.3f} not above inlet {s_k:.3f}")
			dW = 1.0 / s_k - 1.0 / s_out
			C_m, c_w, E_m, e_w = stage_coef(mech, x)
			dew_c += C_m + c_w * dW
			dew_e += E_m + e_w * dW
			s_k = s_out
		if p["s_final"] < s_k - 1e-9:
			raise ValueError(f"{name}: s_final {p['s_final']} below mechanical outlet {s_k:.3f}")

		if p.get("placement_cost") is not None:
			pl_c, pl_e = p["placement_cost"], p["placement_elec"]
		else:
			pl_c, pl_e = sc.placement[p["route"]]
		loc = sc.loc_data[p["location"]]
		cost_tds = dew_c + pl_c
		elec = dew_e + pl_e
		if p["route"] == "offsite_gate":
			cost_tds += loc[f"tailings_{p['gate_class']}_cost"] / s_k
		elif p["storage"]:
			cost_tds += sc.tsf_opex[p["route"]]
			rdf = p.get("rho_dry_final")
			cost_tds += loc["tailings_storage_cost"] / (rdf if rdf else ds_per_m3(s_k, p["rho_s"]))
		cost_tds += elec * ep
		sc.register_sink_cost(name, cost_tds * ds_per_m3(p["s_in"], p["rho_s"]))
		sc.sink_elec[name] = elec

	sc.sink_scope_two = set(sc.sink_params)
	for fac in sc.rev:
		efs = fac.impact_factors.get("electricity") or {}
		fac.scope_two_sinks = sc.sink_scope_two
		fac.impact_factors = dict(fac.impact_factors, **{
			name: {cat: sc.sink_elec[name] * ds_per_m3(p["s_in"], p["rho_s"]) * f
				for cat, f in efs.items()}
			for name, p in sc.sink_params.items()})

	for name, p in {**sc.wastewater_params, **sc.flat_sinks}.items():
		sc.register_sink_cost(name, p["cost"])











