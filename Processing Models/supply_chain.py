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

		# Validate transport_route is a TransportRoute class

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
				summary = fac.update_apv(cur_apv)
				self.tot_var_cost += summary["tot_var_cost"]
				self.tot_fixed_cost += summary["tot_fixed_cost"]
				self.tot_cost += summary["tot_cost"]

				for k, v in summary["emissions_totals"].items():
					self.env_impacts[k] = self.env_impacts.get(k, 0.0) + v

				for (u, v),(products,transport_route) in self.links.items(): # This is O(n^2) which is technically inefficient, but n should be small
					if v == fac:
						if transport_route is not None:
							res = transport_route.evaluate_total(total_volume=fac.get_initial_pv())
							self.tot_var_cost += res["variable_cost"]
							self.tot_fixed_cost += res["fixed_cost"]
							self.tot_cost += res["total_cost"]
					
							for k, v in res["emissions_totals"].items():
								self.env_impacts[k] = self.env_impacts.get(k, 0.0) + v

							# Assume only one link per facility at this time
							cur_apv = res["initial_volume"]
							break
						else:
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











