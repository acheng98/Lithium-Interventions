from typing import Dict, Any, List, Optional
import copy

from production_step import ProductionStep
from helpers import plot_breakdown, plot_production_curve

# Define a class for the production environment
class Facility:

		# Instance attribute
		def __init__(self, fac_id, material_costs, sinks, apv=0, location=None, locations_dict=None, impact_factors=None,
								dpy=330, upd=0.2, scm=0, spd=3, hps=8, ub=0.5, pb=0.5, dr=0.10,
								wage=18, enpt=0.03, elec=0.08, gas=3.46, proc_water=3, cool_water=4, steam=0.0265, comp_air=0.04,
								build=3000, crp=6, brp=20, aux_equip=0.10, maint=0.10, fixed_over = 0.35):
			
			self.fac_id = fac_id
			self.apv = apv
			self.location = location # Location name
			self.material_costs = material_costs # material: cost. Gotta be careful of units
			self.steps = {}
			self.primary_inputs = {}   # facility-level "imports"
			self.primary_outputs = {}  # facility-level "exports"
			# Note the sinks input is a list. Possibly put this back into 'steps' later.
			self.sinks = sinks_dict = {sink: {} for sink in sinks} # Landfill, air/environment, wastewater treatment, etc.
			self.impact_factors = impact_factors or { # Should I even set 0 defaults?? 
					"electricity": {"CO2": 0.0, "water": 0.0},   # defaults: no impact
					"natural_gas": {"CO2": 0.0},
					"cooling_water": {"CO2": 0.0},
					"steam": {"CO2": 0.0, "water": 0.0},
					"compressed_air": {"CO2": 0.0},
					"landfill": {"CO2": 0.0, "land_use": 0.0},
					"wastewater": {"water": 0.0, "eutrophication": 0.0},
					"air": {"CO2": 0.0, "NOx": 0.0, "SO2": 0.0} # probably more, to add later if needed
			}

			self.dpy = dpy # Working days/year
			self.upd = upd # Facility-wide average Unplanned Downtime, as a percentage
			self.scm = scm # Scheduled maintenance
			self.spd = spd # Number of shifts/day
			self.hps = hps # Hours per shift
			self.ub = ub # Hours of unpaid breaks/shift
			self.pb = pb # Hours of paid breaks/shift
			self.dr = dr # Discount Rate
			self.wage = wage # Direct Wage (w/benefits)
			self.enpt = enpt # Energy Cost, as % of material and labor costs
			self.elec_price = elec # Electricity cost, $/kwh
			self.gas_price = gas # Gas cost, $/MMBTU
			self.proc_water_price = proc_water # Cost of water used for processing, $/m^3
			self.cool_water_price = cool_water # Cost of cooled water, $/m^3. Assume an increase over the process water cost.
			self.steam_price = steam # Cost of steam, $/kg. Assume ~1.2 cents / pound, or 2.65 cents / kg
			self.comp_air_price = comp_air # Cost of compressed air, in $/Nm^3 (normal m^3). Assume 4 cents for now.
			self.build_price = build # Building space cost, $/m^2
			self.crp = crp # Capital Recovery Period
			self.brp = brp # Building Recovery Period
			self.aux_equip = aux_equip # Annualized auxiliary Equipment cost, as a percentage of main machine cost
			self.maint = maint # Annualized maintenance costs, as a percentage of main machine cost
			self.fixed_over = fixed_over # Annualized fixed overhead costs, as a percentage of the total of {main machine, building, auxiliary equipment, and maintenance} costs

			# Calculate default values from inputs
			self.crf = self.calc_crf(self.dr,self.crp) # Capital recovery factor
			self.bcrf = self.calc_crf(self.dr,self.brp) # Building capital recovery factor

			self.plt = self.dpy*self.spd*(self.hps-self.ub) # Paid line time
			self.wlt = self.dpy*self.spd*(self.hps-self.ub-self.pb) # Worked line time

			self.prod_map = {} #apv: [self.tot_var_cost,self.tot_fixed_cost,self.tot_cost]
			self.fwd = [] # Forward topographically ordered production steps (upstream → downstream)
			self.rev = [] # Backward topographically ordered production steps (downstream → upstream)

			self.total_utilities = {}
			self.tot_var_cost = 0
			self.tot_fixed_cost = 0
			self.tot_cost = 0
			self.avg_var_cost = 0
			self.avg_fixed_cost = 0
			self.avg_cost = 0

			# If location specified, override defaults
			if location and locations_dict:
					if location not in locations_dict:
							raise ValueError(f"Location '{location}' not found in provided locations_dict.")
					self.update_location(location, locations_dict[location])

		@staticmethod
		def calc_crf(dr: float, period: float) -> float:
				"""
				Return the capital recovery factor for a given rate and period.
				"""
				if period == 1:
						return 1.0
				if dr == 0:
						return 1 / period
				return dr * (1 + dr) ** period / ((1 + dr) ** period - 1)

		# ============================================================
		# STEP ACCESSORS / ORGANIZERS / REPORTING
		# ============================================================

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
				return order

		def step_names(self):
				for step in self.steps.values():
						yield step.step_id

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
				first_step = next(iter(self.fwd))
				return first_step.step_pv

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
						raise KeyError(f"Target step with id '{target_step_id}' not found in facility.")
				step = self.steps[target_step_id]
				if target not in step.primary_inputs and target not in step.primary_outputs:
						raise KeyError(f"Input '{target}' not found in step {target_step_id} as either an input or output.")
				step.set_constituents(target, composition, propagate=propagate)

		# ============================================================
		# SCENARIO & LOCATION MANAGEMENT
		# ============================================================

		def update_location(self, location_name: str, location_data: dict, recalculate: bool = False):
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
				self.location = location_name

				# --- Update all provided parameters (only if present in location_data) ---
				for key, value in location_data.items():
						if hasattr(self, key):
								setattr(self, key, value)

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

				print(f"Facility location updated to '{location_name}'. (Facility production details {notif}updated.)")

		def update_apv(self,apv: float):
				"""
				Update APV and trigger full production cost calculation.
				Wrapper around calculate_all.
				"""
				if apv not in self.prod_map: # Don't need to re-run if already recorded
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
														"total_step_impacts": step.total_step_impacts,
												}
						results[step.step_name] = summary
				return results

		def get_total_environmental_impacts(self, update = False) -> dict:
				"""
				Sums all step totals into facility-wide totals (same categories).
				"""
				by_step = self.calculate_step_environmental_impacts(update)
				totals = {}
				for step_dict in by_step.values():
						for cat, val in step_dict["total_impacts"].items():
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
				self.fwd = self.topo_order()
				self.rev = reversed(self.fwd)
				
				# 1) Forward - chemistry: inputs → outputs, once per step
				s = next(iter(self.fwd))
				s.apply_reagents()
				s.propagate_chemistry(True) # When propagating, it recursively calls apply_reagents at each following step

				# For steps that are not dependent on input chemistry, still need to apply reagents
				for s in self.fwd:
						s.apply_reagents()

				# 2) Backward - volumes: set targets at sinks, walk upstream
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
				self.tot_cost = self.tot_var_cost + self.tot_fixed_cost

				# --- Average costs per unit ---
				self.avg_var_cost = self.tot_var_cost / self.apv
				self.avg_fixed_cost = self.tot_fixed_cost / self.apv
				self.avg_cost = self.tot_cost / self.apv

				# --- Store results for scenario tracking ---
				self.prod_map[self.apv] = [self.tot_var_cost, self.tot_fixed_cost, self.tot_cost]

				return {
						"apv": self.apv,
						"tot_var_cost": self.tot_var_cost,
						"tot_fixed_cost": self.tot_fixed_cost,
						"tot_cost": self.tot_cost,
						"avg_var_cost": self.avg_var_cost,
						"avg_fixed_cost": self.avg_fixed_cost,
						"avg_cost": self.avg_cost
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














