from typing import Dict, Any, List, Optional
import copy
from collections import defaultdict

from facility import Facility
from transportation import Transportation, TransportRoute
from helpers import plot_stacked_bars, plot_production_curve

# Define a class for the supply chain
class SupplyChain:
	def __init__(self):
		self.facilities = {}   # facility_id : Facility
		self.links = {}        # (from_fac,to_fac): {products: fraction_transferred}
		self.prod_map = {} #apv: [self.tot_var_cost,self.tot_fixed_cost,self.tot_cost]
		self.fwd = []
		self.rev = []
		self.fwd_transp = []
		self.rev_transp = []

		self.apv = 0
		self.total_utilities = {}
		self.tot_var_cost = 0
		self.tot_fixed_cost = 0
		self.tot_cost = 0
		self.avg_var_cost = 0
		self.avg_fixed_cost = 0
		self.avg_cost = 0

	def add_facility(self, fac, next_fac = None, products = None, transport_route = None):
		self.facilities[fac.fac_id] = fac
		if next_fac is not None and products is not None:
			self.link_facilities(fac,next_fac,products,transport_route)

	def link_facilities(self, from_fac, to_fac, products, transport_route):
		'''
		from_fac (str): name of the source facility
		to_fac (str): name of the target facility
		products (dict): {product names: % of product to transfer to new facility}
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
				raise KeyError(f"Product '{product}' not found in {from_fac} outputs.")
			if product not in to_inputs:
				raise KeyError(f"Product '{product}' not found in {to_fac} inputs.")

		# Validate transport_route is a TransportRoute class
		if transport_route is not None and not(isinstance(transport_route,TransportRoute)):
			raise ValueError(f"Input transport_route is not actually a TransportRoute object")

		key = (from_fac, to_fac)
		if key not in self.links:
			self.links[key] = {}
		self.links[key] = [products,transport_route]

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

	def topo_order_transp(self):
		self.topo_order()
		topo_order_transp = []
		for fac in self.fwd:
			topo_order_transp.append(fac)
			
			for (u, v),(products,transport_route) in self.links.items(): # This is O(n^2) which is technically inefficient, but n should be small
				if u == fac and transport_route is not None:
					topo_order_transp.append(transport_route)

		self.fwd_transp = topo_order_transp
		self.rev_transp = list(reversed(topo_order_transp))
		return topo_order_transp

	def update_apv(self,apv):
		if apv not in self.prod_map and apv is not None: # Don't need to re-run if already recorded
			self.apv = apv
			self.topo_order()

			# Reset these values across apv runs 
			self.tot_var_cost   = 0.0
			self.tot_fixed_cost = 0.0
			self.tot_cost       = 0.0
			self.avg_var_cost   = 0.0
			self.avg_fixed_cost = 0.0
			self.avg_cost       = 0.0
			self.env_impacts = {}

			cur_apv = apv
			for fac in self.rev:
				updated_apv = False
				summary = fac.update_apv(cur_apv)
				self.tot_var_cost += summary["tot_var_cost"]
				self.tot_fixed_cost += summary["tot_fixed_cost"]
				self.tot_cost += summary["tot_cost"]

				for k, v in summary["emissions_totals"].items():
					self.env_impacts[k] = self.env_impacts.get(k, 0.0) + v

				for (u, v),(products,transport_route) in self.links.items(): # This is O(n^2) which is technically inefficient, but n should be small
					if v == fac:
						if transport_route is not None:
							res = transport_route.evaluate_total(new_volume=fac.get_initial_pv())
							self.tot_var_cost += res["variable_cost"]
							self.tot_fixed_cost += res["fixed_cost"]
							self.tot_cost += res["total_cost"]
					
							for k, v in res["emissions_totals"].items():
								self.env_impacts[k] = self.env_impacts.get(k, 0.0) + v

							# Assume only one link per facility at this time
							cur_apv = res["input_units"]
							updated_apv = True
							break
				
				if updated_apv is False: # No transportation link identified, just get the apv of this current facility
					# TECHNICALLY SHOULD BE THE VALUE OF THE INPUT NEEDED FOR THE VOLUME-DEFINING INPUT
					cur_apv = fac.get_initial_pv()


			self.avg_var_cost = self.tot_var_cost / self.apv
			self.avg_fixed_cost = self.tot_fixed_cost / self.apv
			self.avg_cost = self.tot_cost / self.apv
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

	# OVERALL SUMMARY STASTISTICS
	def get_total_reagents(self):
		"""
		Aggregates total absolute usage and total cost for each reagent across all steps.

		Returns:
			dict[str, dict[str, float]]
			{
				"Reagent A": {"abs_usage": x, "total_cost": y},
				"Reagent B": {"abs_usage": x, "total_cost": y},
				...
			}
		"""
		totals = {}

		for step in self.get_steps():
			secondary_inputs = getattr(step, "secondary_inputs", {}) or {}

			for reagent_name, props in secondary_inputs.items():
				if reagent_name not in totals:
					totals[reagent_name] = {"abs_usage": 0.0, "total_cost": 0.0}

				totals[reagent_name]["abs_usage"] += props.get("abs_usage", 0.0)
				totals[reagent_name]["total_cost"] += props.get("total_cost", 0.0)

		return totals

	def get_total_utilities(self):
		"""
		Aggregates total consumption and cost for each utility across all steps.

		Returns:
			dict[str, dict[str, float]]
			{
				"electricity": {"consumed": x, "cost": y},
				"natural_gas": {"consumed": x, "cost": y},
				...
			}
		"""
		utilities = {
			"electricity": ("electricity_consumed", "electricity_cost"),
			"natural_gas": ("natural_gas_consumed", "natural_gas_cost"),
			"process_water": ("process_water_consumed", "process_water_cost"),
			"cooling_water": ("cooling_water_consumed", "cooling_water_cost"),
			"steam": ("steam_consumed", "steam_cost"),
			"compressed_air": ("compressed_air_consumed", "compressed_air_cost"),
		}

		totals = {
			name: {"consumed": 0.0, "cost": 0.0}
			for name in utilities
		}

		for step in self.get_steps():
			for utility, (consumed_attr, cost_attr) in utilities.items():
				totals[utility]["consumed"] += getattr(step, consumed_attr, 0.0)
				totals[utility]["cost"] += getattr(step, cost_attr, 0.0)

		return totals

	def get_total_labor(self):
		labor_demand = 0
		labor_cost = 0
		for step in self.get_steps():
			labor_demand += step.labor_required
			labor_cost += step.labor_cost
		return labor

	# STEP-LEVEL SUMMARY STATISTICS
	def get_steps(self,transp = False):
		steps = []
		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				for step in node.fwd:
					steps.append(step)
			elif isinstance(node, TransportRoute) and transp:
				for leg in node.legs:
					steps.append(leg)
		return steps

	def get_step_constituents(self):
		consts = []
		for step in self.get_steps():
			consts.append([step.step_name, step.constituents])
		return consts

	def get_step_reagent_usage(self):
		reagent_usages = []
		for step in self.get_steps():
			for reagent_name, props in step.secondary_inputs.items():
				reagent_usages.append([step.step_name, reagent_name, props["abs_usage"], props["total_cost"]])
		return reagent_usages

	def get_step_electric(self):
		electric_usage = []
		for step in self.get_steps():
			electric_usage.append([step.step_name, "Electricity", step.electricity_consumed, step.electricity_cost])
		return electric_usage

	def get_step_natural_gas(self):
		natural_gas_usage = []
		for step in self.get_steps():
			natural_gas_usage.append([step.step_name, "Natural Gas", step.natural_gas_consumed, step.natural_gas_cost])
		return natural_gas_usage

	def get_step_process_water(self):
		process_water_usage = []
		for step in self.get_steps():
			process_water_usage.append([step.step_name, "Process Water", step.process_water_consumed, step.process_water_cost])
		return process_water_usage

	def get_step_cooling_water(self):
		cooling_water_usage = []
		for step in self.get_steps():
			cooling_water_usage.append([step.step_name, "Cooling Water", step.cooling_water_consumed, step.cooling_water_cost])
		return cooling_water_usage

	def get_step_steam(self):
		steam_usage = []
		for step in self.get_steps():
			steam_usage.append([step.step_name, "Steam", step.steam_consumed, step.steam_cost])
		return steam_usage

	def get_step_compressed_air(self):
		compressed_air_usage = []
		for step in self.get_steps():
			compressed_air_usage.append([step.step_name, "Compressed Air", step.compressed_air_consumed, step.compressed_air_cost])
		return compressed_air_usage

	def get_step_utilities(self):
		utility_usage = []
		for step in self.get_steps():
			utility_usage.append([step.step_name, "Total Utility Cost", step.utility_cost])
		return utility_usage

	def get_step_utilities_detailed(self):
		results = []
		for step in self.get_steps():
			results.append({
				"step_name": step.step_name,
				"total_utility_cost": step.utility_cost,

				"electricity": {
					"consumed": step.electricity_consumed,
					"cost": step.electricity_cost,
				},
				"natural_gas": {
					"consumed": step.natural_gas_consumed,
					"cost": step.natural_gas_cost,
				},
				"process_water": {
					"consumed": step.process_water_consumed,
					"cost": step.process_water_cost,
				},
				"cooling_water": {
					"consumed": step.cooling_water_consumed,
					"cost": step.cooling_water_cost,
				},
				"steam": {
					"consumed": step.steam_consumed,
					"cost": step.steam_cost,
				},
				"compressed_air": {
					"consumed": step.compressed_air_consumed,
					"cost": step.compressed_air_cost,
				},
			})
		return results

	def get_step_labor(self):
		labor = []
		for step in self.get_steps():
			labor.append([step.step_name, step.labor_required, step.labor_cost])
		return labor

	def get_detailed_pvs(self):
		pvs = []
		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				for step in node.fwd:
					pvs.append([step.step_name, step.step_pv])
			elif isinstance(node, TransportRoute):
				for leg in node.legs:
					pvs.append([leg.name, leg.volume])
		return pvs

	def get_detailed_inputs(self):
		inputs = []
		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				for step in node.fwd:
					for primary_input,items in step.primary_inputs.items():
						inputs.append([step.step_name, primary_input, items["input_needed"]])
		return inputs

	def plot_tot_fac_costs(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None):
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError(f"No APV values have been run; rerun with some target production volume.")

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
				raise ValueError(f"Unidentified node in the supply chain's topographic order")

		stack_order = ["Fixed Costs","Variable Costs"]
		plot_stacked_bars(labels,costs,stack_order=stack_order,xscale=xscale,yscale=yscale,
			title=title,xlab=xlab,ylab=ylab,xlims=xlims,ylims=ylims)

	def plot_tot_steps_costs(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None):
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError(f"No APV values have been run; rerun with some target production volume.")

		labels = []
		costs = defaultdict(list)

		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				for step in node.fwd:
					labels.append(step.step_name)
					costs["Variable Costs"].append(step.tot_var_cost)
					costs["Fixed Costs"].append(step.tot_fixed_cost)
			elif isinstance(node, TransportRoute):
				for leg in node.legs:
					labels.append(leg.name)
					costs["Variable Costs"].append(leg.variable_cost)
					costs["Fixed Costs"].append(leg.fixed_cost)
			else:
				raise ValueError(f"Unidentified node in the supply chain's topographic order")
			

		stack_order = ["Fixed Costs","Variable Costs"]
		plot_stacked_bars(labels,costs,stack_order=stack_order,xscale=xscale,yscale=yscale,
			title=title,xlab=xlab,ylab=ylab,xlims=xlims,ylims=ylims)

	def plot_tot_steps_impacts(self,apv=None,xscale=1,yscale=1,title='GHGs at each Step',xlab='Step Names',ylab='Total GHGs',xlims=None,ylims=None):
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError(f"No APV values have been run; rerun with some target production volume.")

		labels = []
		scopes = defaultdict(list)

		for node in self.topo_order_transp():
			if isinstance(node, Facility):
				for step in node.fwd:
					labels.append(step.step_name)
					scopes["Scope One"].append(step.scope_one_impacts.get('co2',0))
					scopes["Scope Two"].append(step.scope_two_impacts.get('co2',0))
			elif isinstance(node, TransportRoute):
				for leg in node.legs:
					labels.append(leg.name)
					scopes["Scope One"].append(leg.emissions_totals.get('ghg',0))
					scopes["Scope Two"].append(0)
			else:
				raise ValueError(f"Unidentified node in the supply chain's topographic order")

		stack_order = ["Scope One", "Scope Two"]

		# Optional colors to keep your house palette
		colors = {"Scope One": "#f28e2b", "Scope Two": "#4e79a7"}

		plot_stacked_bars(labels,scopes,stack_order=stack_order,colors=colors,xscale=xscale,yscale=yscale,
			title=title,xlab=xlab,ylab=ylab,xlims=xlims,ylims=ylims)

	def plot_unit_cc(self,xscale=1,yscale=1,title='APV vs Average Cost',xlab='Annual Production Volume (APV)',ylab='Unit Cost'):
		# Extract APVs and costs from the prod_map
		apvs = [apv * xscale for apv in self.prod_map.keys()]
		avg_costs = [cost[2]/apv * yscale for apv,cost in self.prod_map.items()]
		plot_production_curve(apvs,avg_costs,xscale,yscale,title,xlab,ylab)

	def plot_total_cc(self,xscale=1,yscale=1,title='APV vs Total Cost',xlab='Annual Production Volume (APV)',ylab='Total Cost'):
		# Extract APVs and costs from the prod_map
		apvs = [apv * xscale for apv in self.prod_map.keys()]
		tot_costs = [cost[2] * yscale for cost in self.prod_map.values()]

		plot_production_curve(apvs,tot_costs,xscale,yscale,title,xlab,ylab)











