from typing import Dict, Any, List, Optional
import copy

from facility import Facility
from helpers import plot_breakdown, plot_production_curve

# Define a class for the supply chain
class SupplyChain:
	def __init__(self):
		self.facilities = {}   # facility_id : Facility
		self.links = {}        # (from_fac,to_fac): {products: fraction_transferred}
		self.prod_map = {} #apv: [self.tot_var_cost,self.tot_fixed_cost,self.tot_cost]
		self.fwd = []
		self.rev = []

		self.apv = 0
		self.total_utilities = {}
		self.tot_var_cost = 0
		self.tot_fixed_cost = 0
		self.tot_cost = 0
		self.avg_var_cost = 0
		self.avg_fixed_cost = 0
		self.avg_cost = 0

	def add_facility(self, fac, next_fac = None, products = None):
		self.facilities[fac.fac_id] = fac
		if next_fac is not None and products is not None:
			self.link_facilities(fac,next_fac,products)

	def link_facilities(self, from_fac, to_fac, products):
		'''
		from_fac (str): name of the source facility
		to_fac (str): name of the target facility
		products (dict): {product names: % of product to transfer to new facility}
		'''
		if from_fac.fac_id not in self.facilities:
			raise KeyError(f"Source facility '{from_fac.fac_id}' not found.")
		if to_fac.fac_id not in self.facilities:
			raise KeyError(f"Target facility '{to_fac.fac_id}' not found.")

		key = (from_fac, to_fac)
		if key not in self.links:
			self.links[key] = {}

		# Validate products exist
		from_outputs = self.facilities[from_fac.fac_id].collect_primary_outputs()
		to_inputs = self.facilities[to_fac.fac_id].collect_primary_inputs()

		for product in products.keys():
			if product not in from_outputs:
				raise KeyError(f"Product '{product}' not found in {from_fac} outputs.")
			if product not in to_inputs:
				raise KeyError(f"Product '{product}' not found in {to_fac} inputs.")

		self.links[key].update(products)

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
			# self.total_utilities = {}

			cur_apv = apv
			for fac in self.rev:
				summary = fac.update_apv(cur_apv)
				self.tot_var_cost += summary["tot_var_cost"]
				self.tot_fixed_cost += summary["tot_fixed_cost"]
				self.tot_cost += summary["tot_cost"]
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

	def propagate_materials(self):
		"""Push coproduct outputs from one facility into another’s inputs."""
		for (from_id, to_id), products in self.links.items(): # Really this should be an ordered list, but not necessary for now
			from_fac = self.facilities[from_id]
			to_fac = self.facilities[to_id]

			outputs = from_fac.collect_primary_outputs()

			for product, frac in products.items():
				if product not in outputs:
					continue  # skip missing product - shouldn't be possible, but keep code here just in case

				composition = outputs[product]["constituents"]

				# Pass to target facility
				to_fac.add_input_comp(
					primary_input=product,
					input_composition=composition,
					propagate=True
				)

			# Re-calculate volume in to_fac based on new input composition
			to_fac.calculate_all(to_fac.apv)

			# Based on the volume defining output in the from_fac, calculate the volume in from_fac

			produced_volume = outputs[product]["volume"]
			transfer_amount = produced_volume * frac

	def plot_tot_fac_costs(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None):
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError(f"No APV values have been run; rerun with some target production volume.")

		labels = []
		variable_costs = []
		fixed_costs = []

		for fac in self.fwd:
			labels.append(fac.fac_id)
			variable_costs.append(fac.tot_var_cost)
			fixed_costs.append(fac.tot_fixed_cost)

		plot_breakdown(labels,variable_costs,fixed_costs,xscale,yscale,title,xlab,ylab,xlims,ylims)

	def plot_tot_steps_in_facs_costs(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None):
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError(f"No APV values have been run; rerun with some target production volume.")

		labels = []
		variable_costs = []
		fixed_costs = []

		for fac in self.fwd:
			for step in fac.fwd:
				labels.append(step.step_name)
				variable_costs.append(step.tot_var_cost)
				fixed_costs.append(step.tot_fixed_cost)

		plot_breakdown(labels,variable_costs,fixed_costs,xscale,yscale,title,xlab,ylab,xlims,ylims)

	def plot_tot_steps_in_facs_impacts(self,apv=None,xscale=1,yscale=1,title='Cost of Steps',xlab='Step Names',ylab='Total Cost',xlims=None,ylims=None):
		if apv is not None:
			self.update_apv(apv)
		elif len(self.prod_map.keys()) == 0:
			raise ValueError(f"No APV values have been run; rerun with some target production volume.")

		labels = []
		scope_one = []
		scope_two = []

		for fac in self.fwd:
			for step in fac.fwd:
				labels.append(step.step_name)
				scope_one.append(step.scope_one_impacts.get('co2',0))
				scope_two.append(step.scope_two_impacts.get('co2',0))

		plot_breakdown(labels,scope_one,scope_two,xscale,yscale,title,xlab,ylab,xlims,ylims)

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











