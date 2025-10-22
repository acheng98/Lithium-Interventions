from typing import Dict, Any, List, Optional
import copy
import numpy as np
import matplotlib.pyplot as plt

from production_step import ProductionStep

# Define a class for the production environment
class Facility:

  # Instance attribute
	def __init__(self, apv, material_costs, sinks, location=None, locations_dict=None, impact_factors=None,
				dpy=330, upd=0.2, scm=0, spd=3, hps=8, ub=0.5, pb=0.5, dr=0.10,
				wage=18, enpt=0.03, elec=0.08, gas=3.46, proc_water=3, cool_water=4, steam=0.0265, comp_air=0.04,
				build=3000, crp=6, brp=20, aux_equip=0.10, maint=0.10, fixed_over = 0.35):
		if isinstance(apv, (int, float)):
			self.apv = apv # Annual Production Volume
		else:
			raise ValueError(f"Input 'next step' must be a number (int or float), got {type(apv).__name__} instead.")

		self.location = location # Location name
		self.material_costs = material_costs # material: cost. Gotta be careful of units
		self.steps = {}
		self.primary_inputs = {}   # facility-level "imports"
		self.primary_outputs = {}  # facility-level "exports"
		# Note the sinks input is a list. Possibly put this back into 'steps' later.
		self.sinks = sinks_dict = {sink: {} for sink in sinks} # Landfill, air/environment, wastewater treatment, etc.
		self.impact_factors = impact_factors or {
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


	##################################
	# CLASS METHODS - (HERE FOR NOW) #
	##################################
	@classmethod
	def calc_crf(dr = None,period = None):
		if dr == None:
			dr = self.dr
		if period == None:
			period = self.crp

		if period == 1:
			return 1
		else:
			return dr*(1+dr)**(period)/((1+dr)**(period)-1)

	# ============================================================
	# STEP ACCESSORS / REPORTING
	# ============================================================

	def step_names(self):
		for step in self.steps.values():
			yield step.step_id

	def step_costs(self, detail = 1):
		if detail == 3:
			pass # optionally more detail somehow - probably breakdown by reagent?
		elif detail == 2:
			for step in self.steps.values():
				yield step.step_name, step.tot_var_cost, step.tot_fixed_cost, step.tot_cost
		else: # detail == 1 or any other number - least detailed
			for step in self.steps.values():
				yield step.step_name, step.tot_cost

	def step_pvs(self):
		for step in self.steps.values():
				yield step.step_name, step.step_pv

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

	def add_input_comp(self, primary_input: str, input_composition: dict, target_step_id = None, propagate = True):
		# Get first step
		if target_step_id is not None:
			if target_step_id not in self.steps:
				raise KeyError(f"Target step with id '{target_step_id}' not found in facility.")
			step = self.steps[target_step_id]
			if primary_input not in step.primary_inputs:
				raise KeyError(f"Input '{primary_input}' not found in step {target_step_id}.")
			step.set_constituents(primary_input, input_composition, propagate=propagate)
		else:
			# Apply to all steps that use this primary input
			found = False
			for step in self.steps.values():
				if primary_input in step.primary_inputs:
					step.set_constituents(primary_input, input_composition, propagate=propagate)
					found = True
			if not found:
				raise KeyError(f"Primary input '{primary_input}' not found in any step of this facility.")

	# ============================================================
	# SCENARIO & LOCATION MANAGEMENT
	# ============================================================

	def update_location(self, location_name: str, location_data: dict):
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
		self.crf = crf(self.dr, self.crp)   # Capital recovery factor
		self.bcrf = crf(self.dr, self.brp) # Building recovery factor

		self.plt = self.dpy * self.spd * (self.hps - self.ub)           # Paid line time
		self.wlt = self.dpy * self.spd * (self.hps - self.ub - self.pb) # Worked line time

		# Update all process and cost info
		self.calculate_all()

		print(f"Facility updated to location '{location_name}'.")

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
		Returns a dictionary of sink -> coproduct -> total volume across all steps.
		"""
		totals = {}
		for sink_name, coproducts in self.sinks.items():
			totals[sink_name] = {}
			for coproduct_name, step_volumes in coproducts.items():
				# Sum volumes across all steps
				total_volume = sum(v for k, v in step_volumes.items() if isinstance(v, (int, float)))
				totals[sink_name][coproduct_name] = total_volume
		return totals

	def calculate_environmental_impacts(self):
		"""
		Calculate total environmental impacts of utility consumption
		based on location-specific impact factors.
		Requires self.total_utilities (from report_utilities).
		"""
		if not hasattr(self, "total_utilities") or not self.total_utilities:
			raise ValueError("No utility totals found. Run report_utilities() first.")

		impacts = {}

		# --- Utility impacts ---
		utility_impacts = {}
		for utility, factors in self.impact_factors.get("utilities", {}).items():
			usage = self.total_utilities.get(utility, 0.0)
			utility_impacts[utility] = {cat: usage * factor for cat, factor in factors.items()}

		# --- Sink impacts ---
		sink_totals = self._sum_coproducts_in_sinks()
		sink_impacts = {}
		for sink_name, coproducts in sink_totals.items():
			sink_impacts[sink_name] = {}
			for coproduct_name, total_volume in coproducts.items():
				factors = self.impact_factors.get("sinks", {}).get(sink_name, {}).get(coproduct_name, {})
				sink_impacts[sink_name][coproduct_name] = {cat: total_volume * factor for cat, factor in factors.items()}

		# --- Aggregate total impacts per category ---
		total_impacts = {}
		# Sum utility impacts
		for utility, impacts in utility_impacts.items():
			for cat, value in impacts.items():
				total_impacts[cat] = total_impacts.get(cat, 0.0) + value
		# Sum sink impacts
		for sink, coproducts in sink_impacts.items():
			for coproduct, impacts in coproducts.items():
				for cat, value in impacts.items():
					total_impacts[cat] = total_impacts.get(cat, 0.0) + value

		return {
			"utility_impacts": utility_impacts,
			"sink_impacts": sink_impacts,
			"total_impacts": total_impacts
		}

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

		# Apply reagents to all steps for safety. May be better bundled/separated based 
		for step in self.steps.values():
			step.apply_reagents()

		if apv is not None and apv != self.apv:
			self.apv = apv

		# --- First: compute and propagate production volumes (step_pv) ---
		# Find the end steps (those with no next steps)
		end_steps = [s for s in self.steps.values() if not s.next_steps]
		if not end_steps:
			raise ValueError("No end step(s) found — cannot compute production volumes.")

		for step in end_steps:
			step.compute_step_pv(propagate=True)

		# --- Next: calculate chemistry and reagent usage ---
		first_steps = [s for s in self.steps.values() if not s.previous_steps]
		for step in first_steps:
			if any(inp.get("chemistry_dependence", False) for inp in step.primary_inputs.values()):
				step.compute_output_chem_comp(propagate=True)

		# --- Run cost calculations for each step ---
		for step in self.steps.values():
			step.calculate()

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
	def plot_tot_step_costs(self,apv,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None):
		fig, ax = plt.subplots()
		self.update_apv(apv)

		labels = [step.step_id_short for step in self.steps]
		variable_costs = [step.tot_var_cost for step in self.steps]
		fixed_costs = [step.tot_fixed_cost for step in self.steps]

		# X positions for the bars
		x = np.arange(len(self.steps))

		# Plot stacked bar chart
		plt.bar(x, variable_costs, label="Variable Cost")
		plt.bar(x, fixed_costs, bottom=variable_costs, label="Fixed Cost")

		# Add labels and title
		plt.xticks(x, labels)
		plt.xlabel(xlab)
		plt.ylabel(ylab)
		plt.title(title)
		plt.legend()

		if xlims != None:
			plt.xlim(xlims[0],xlims[1])
		if ylims != None:
			plt.ylim(ylims[0],ylims[1])

		# Show plot
		plt.tight_layout()
		plt.show()
		return fig,ax

	def plot_avg_step_costs(self,apv,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Cost/Unit',xlims=None,ylims=None):
		fig, ax = plt.subplots()
		self.update_apv(apv)

		labels = [step.step_id_short for step in self.steps]
		variable_costs = [step.tot_var_cost/apv for step in self.steps]
		fixed_costs = [step.tot_fixed_cost/apv for step in self.steps]

		# X positions for the bars
		x = np.arange(len(self.steps))

		# Plot stacked bar chart
		plt.bar(x, variable_costs, label="Variable Cost")
		plt.bar(x, fixed_costs, bottom=variable_costs, label="Fixed Cost")

		# Add labels and title
		plt.xticks(x, labels)
		plt.xlabel(xlab)
		plt.ylabel(ylab)
		plt.title(title)
		plt.legend()

		if xlims != None:
			plt.xlim(xlims[0],xlims[1])
		if ylims != None:
			plt.ylim(ylims[0],ylims[1])

		# Show plot
		plt.tight_layout()
		plt.show()
		return fig,ax

	def plot_unit_cc(self,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Unit Cost'):
		# Extract APVs and costs from the prod_map
		apvs = [apv * xscale for apv in self.prod_map.keys()]
		avg_costs = [cost[2]/apv * yscale for apv,cost in self.prod_map.items()]

		# Create the scatter plot
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

	def plot_total_cc(self,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Total Cost'):
		# Extract APVs and costs from the prod_map
		apvs = [apv * xscale for apv in self.prod_map.keys()]
		tot_costs = [cost[2] * yscale for cost in self.prod_map.values()]

		# Create the scatter plot
		fig = plt.figure(figsize=(8, 6))
		plt.scatter(apvs, tot_costs, color='blue', label='Production Volume vs Cost')

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
