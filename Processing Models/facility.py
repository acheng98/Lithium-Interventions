from typing import Dict, Any, List, Optional
import copy
from collections import defaultdict
from typing import NamedTuple

from production_step import ProductionStep
from helpers import plot_stacked_bars, plot_production_curve

# Define a class for the production environment
class Facility:

		# Instance attribute
		def __init__(self, fac_id, supply_chain, location, sinks, apv=0, steps=None, impact_factors=None):
			
			self.fac_id = fac_id
			self.apv = apv
			self.sc = supply_chain # The supply chain object this facility is associated with 
			self.material_data = copy.deepcopy(self.sc.material_data) # to be updated with location-specific overrides as specified
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
						return
				else:
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

				labels = []
				variable_costs = []
				fixed_costs = []

				for step in self.fwd:
						labels.append(step.step_id)
						variable_costs.append(step.tot_var_cost)
						fixed_costs.append(step.tot_fixed_cost)

				plot_breakdown(labels,variable_costs,fixed_costs,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None)

		def plot_avg_step_costs(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Cost/Unit',xlims=None,ylims=None):
				if apv is not None:
						self.update_apv(apv)
				elif len(self.prod_map.keys()) == 0:
						raise ValueError(f"No APV values have been run; rerun with some target production volume.")

				labels = [step.step_id_short for step in self.steps]
				variable_costs = [step.tot_var_cost/apv for step in self.steps]
				fixed_costs = [step.tot_fixed_cost/apv for step in self.steps]

				plot_breakdown(labels,variable_costs,fixed_costs,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None)

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

class DewateringResult(NamedTuple):
		cost: float   # $/t dry solids — OPEX excl. electricity cost
		elec: float   # kWh/t dry solids — for separate emissions calc
		# diesel: float # diesel usage/t dry solids - for separate emissions calc

def tailings_handling(sc):
		# ------------------------------------------------------------------
		# Disposal gate fees — applied to off-site streams only
		# Units: $/tonne wet as-received at gate
		# To convert to $/t DS: divide by s (cake solids fraction)
		# ------------------------------------------------------------------
		EREF_NONHAZ_NV	= 67.0		# $/t wet; non-hazardous landfill, Nevada (EREF 2024). Change to loading in from locational data later
		NDRC_HAZ_JX			= 280.0		# $/t wet; hazardous secure landfill, Jiangxi (NDRC 2024) - ~$2000 yuan/ton. Change to loading in from locational data later

		# On-site CTFS operating cost — Thacker Pass lined tailings facility
		# Covers liner amortization, leachate collection, monitoring, stormwater mgmt
		# Applied on top of dewatering cost for streams entering the CTFS
		# $/t DS; placeholder pending permit operational data
		ONSITE_CTFS_OPEX = 5.0		# $/t DS

		# ------------------------------------------------------------------
		# Dewatering / stacking cost tables (unchanged from prior definition)
		# ------------------------------------------------------------------
		DEWATERING_COST_BREAKPOINTS = {
				# (s_low, s_high): (c_at_s_low, c_at_s_high)  $/t dry solids
				# Estimated costs based on thickener and mechanical dewatering block models
				(0.08, 0.15): (8,  17),		# gravity thickening
				(0.15, 0.25): (17, 30),		# belt filter press
				(0.25, 0.50): (30, 48),		# plate-and-frame filter press
		}
		DEWATERING_ELECTRICITY_BREAKPOINTS = {
				# kWh/t dry solids
				(0.08, 0.15): (3,   8),		# gravity thickening: essentially pumping only
				(0.15, 0.25): (20, 35),		# belt filter press: belts + wash water pumps
				(0.25, 0.50): (35, 60),		# plate-and-frame: hydraulic press + feed pump
		}
		TAILINGS_STACKING_COST = {
				# (s_low, s_high): (c_at_s_low, c_at_s_high)  $/t dry solids
				(0.55, 0.75): (3.0, 8.0),	# paste pumping + conveyor stacking; wear rises with stiffness
				(0.75, 1.00): (4.0, 1.5),	# dry stack / conveyor only; cost falls with dryness
		}
		TAILINGS_STACKING_ELECTRICITY = {
				# kWh/t dry solids; decreases monotonically as s increases
				(0.55, 0.75): (20.0, 8.0),	# paste pump dominates; eases toward dry handoff
				(0.75, 1.00): (4.0,  2.0),	# conveyor + compaction only
		}

		def dewatering_stacking(s: float, elec_cost: float = 0.0) -> DewateringResult:
				"""
				Returns dewatering OPEX (s < 0.55) or stacking OPEX (s >= 0.55), in $/t DS.
				Does NOT include disposal gate fee or on-site CTFS opex — add those separately.
				"""
				if s < 0.55:
						breakpoints      = DEWATERING_COST_BREAKPOINTS
						elec_breakpoints = DEWATERING_ELECTRICITY_BREAKPOINTS
				else:
						breakpoints      = TAILINGS_STACKING_COST
						elec_breakpoints = TAILINGS_STACKING_ELECTRICITY
				for (s_lo, s_hi), (c_lo, c_hi) in breakpoints.items():
						if s_lo <= s <= s_hi:
								frac        = (s - s_lo) / (s_hi - s_lo)
								base_cost   = c_lo + frac * (c_hi - c_lo)
								e_lo, e_hi  = elec_breakpoints[(s_lo, s_hi)]
								electricity = e_lo + frac * (e_hi - e_lo)
								cost        = base_cost + electricity * elec_cost
								return DewateringResult(cost=cost, elec=electricity)
				raise ValueError(
						f"s={s:.3f} outside modeled range. "
						f"Sludge dewatering: [0.08, 0.55). Coarse stacking: [0.55, 1.00]."
				)

		# ------------------------------------------------------------------
		# Helper — dry solids mass (t) per m³ of slurry at weight fraction w_s
		# Used to convert $/t DS → $/m³ slurry for sink cost registration
		# Basis: mixture density  rho_mix = 1 / (w_s/rho_s + (1-w_s)/rho_w)
		# ------------------------------------------------------------------
		def ds_per_m3(w_s: float, rho_s: float = 2.7, rho_w: float = 1.0) -> float:
				rho_mix = 1.0 / (w_s / rho_s + (1.0 - w_s) / rho_w)
				return w_s * rho_mix

		sc.topo_order()
		fac = sc.rev[0]
		ep = fac.elec_price

		# ------------------------------------------------------------------
		# Sink cost registrations
		# Formula: $/m³ slurry = (c_handling_per_t_ds + c_disposal_per_t_ds) * ds_per_m3(w_s)
		#
		# Off-site:  c_disposal = gate_fee / s   (gate fee is $/t wet as-received)
		# On-site:   c_disposal = ONSITE_CTFS_OPEX (flat $/t DS, no gate fee) 
		# Stacking:  c_disposal = 0 (stacking cost already in dewatering_stacking for s >= 0.55)
		# ------------------------------------------------------------------

		# --- Silver Peak: brine chemical treatment residue (Mg(OH)2 / CaCO3 filter cake) ---
		# Route: off-site non-hazardous landfill (Nevada).  Disposal cost: EREF 2024.
		s_brine = 0.35
		c_brine = dewatering_stacking(s_brine, ep).cost + EREF_NONHAZ_NV / s_brine
		sc.register_sink_cost("tailings_35", c_brine * ds_per_m3(s_brine))

		# --- Thacker Pass: impurity sludge (Mg/Ca precipitates, thickener underflow) ---
		# Route: on-site CTFS (lined).  No gate fee; CTFS opex added explicitly.
		# CHANGED: was dewatering_stacking(0.25).cost only; now adds ONSITE_CTFS_OPEX
		s_tp_sludge = 0.25
		c_tp_sludge = dewatering_stacking(s_tp_sludge, ep).cost + ONSITE_CTFS_OPEX
		sc.register_sink_cost("tailings_25", c_tp_sludge * ds_per_m3(s_tp_sludge))

		# --- Thacker Pass + Jianxiawo: on-site stackable material (s ~ 0.62-0.68, use 0.65) ---
		# Streams: Thacker Pass CCD filter cake; Jianxiawo coarse reject; Jianxiawo leach residue
		# Route: on-site stacking.  Stacking cost is returned directly by dewatering_stacking.
		s_stack = 0.65
		c_stack = dewatering_stacking(s_stack, ep).cost		# stacking cost only; no gate fee
		sc.register_sink_cost("tailings_65", c_stack * ds_per_m3(s_stack))

		# --- Jianxiawo: impurity sludge (metal hydroxide precipitates, hazardous) ---
		# Route: off-site hazardous secure landfill (Jiangxi).  Disposal cost: NDRC 2024.
		# CHANGED: was dewatering_stacking(0.20).cost only; now adds NDRC hazardous gate fee / s
		s_haz = 0.20
		c_haz = dewatering_stacking(s_haz, ep).cost + NDRC_HAZ_JX / s_haz
		sc.register_sink_cost("tailings_20", c_haz * ds_per_m3(s_haz))

		# --- All pathways: crushed reject / waste rock (dry, on-site pile) ---
		# Route: on-site waste rock stack; no dewatering, no gate fee.
		# s ~ 0.95 (residual handling moisture); cost is conveyor + dozer only.
		# CHANGED: was dewatering_stacking(1, ...) * 2.7; now uses s=0.95 and ds_per_m3
		s_rock = 1
		c_rock = dewatering_stacking(s_rock, ep).cost
		sc.register_sink_cost("tailings_solid", c_rock * ds_per_m3(s_rock))

		sc.register_sink_cost("wastewater_treatment", 1)   # $/m3, placeholder


def brine_reinjection(sc):
		sc.register_sink_cost("wastewater_treatment", 1)   # $/m3, placeholder












