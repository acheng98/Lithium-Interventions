from typing import Dict, Any, List, Optional
import copy
import math
from collections import defaultdict

from helpers import safe_float, parse_numeric

# Define a class for the production environment
class Transportation:
	def __init__(
		self,
		name, 			# name for this transportation leg
		supply_chain,	# The supply chain object this transport route is associated with 
		mode,			# string label, e.g. "liquid_tanker_truck_diesel"
		distance,		# distance in km for this leg
		volume = 0,		# target volume transported - can be left out / initialized as 0 to be updated later
	):
		self.name = name
		self.mode = mode
		self.sc = supply_chain
		self.distance = distance # in KM
		self.volume = volume
		
		mode_data = self.sc.transp_data.get(mode)
		if mode_data is None:
			raise KeyError(f"Transportation mode '{mode}' not found in input tranportation data.")

		self.cost_pkm = mode_data["operating_cost"]
		self.ghg_emissions_pkm = mode_data["ghg_emissions"]
		self.so2_emissions_pkm = mode_data["so2_emissions"]
		self.nox_emissions_pkm = mode_data["nox_emissions"]
		self.pm_emissions_pkm = mode_data["pm_emissions"]
		# For now - only include losses within the transportation step. Assume that all calculations/costs based on initial volume.
		self.loss_fraction = mode_data["loss_fraction"]
		self.fixed_cost = mode_data["fixed_cost"]
		self.ref_volume = mode_data["base_volume"]

		self.input_volume = self.volume / (1.0 - self.loss_fraction)

	def evaluate_total(self, new_volume = None, rank="midpoint"):
		"""
		Evaluate this leg on a total volume.
		Returns totals: delivered_units, cost_total, emissions_total dict.
		"""
		if new_volume is not None:
			self.volume = new_volume

		self.input_volume = self.volume / (1.0 - self.loss_fraction)

		self.variable_cost = self.cost_pkm[rank] * self.distance * self.input_volume
		self.total_cost = self.fixed_cost + self.variable_cost

		self.trip_number = math.ceil(self.input_volume / self.ref_volume)

		dist_trips = self.distance * self.trip_number
		if self.mode not in ["dry_bulk_barges", "ocean_transport"]:
			dist_trips = dist_trips * 2 # Need to account for round trip

		self.emissions_totals = {
			"co2": self.ghg_emissions_pkm[rank] * dist_trips * self.ref_volume,
			"so2": self.so2_emissions_pkm[rank] * dist_trips * self.ref_volume,
			"nox": self.nox_emissions_pkm[rank] * dist_trips * self.ref_volume,
			"pm":  self.pm_emissions_pkm[rank]  * dist_trips * self.ref_volume,
		}

		return {
			"delivered_units": self.volume,
			"input_units": self.input_volume,
			"variable_cost": self.variable_cost,
			"fixed_cost": self.fixed_cost, 
			"total_cost": self.total_cost,
			"emissions_totals": self.emissions_totals,
		}

class TransportRoute:
	"""
	Ordered list of Transportation legs, evaluated on a *total* quantity.
	Can pass an override of the starting volume (total to send). If omitted,
	we use the volume already stored on the last leg.
	"""
	def __init__(self, name, legs, rank = "midpoint"):
		self.name = name 
		if type(legs) is not List and len(legs) == 0:
			raise ValueError("TransportRoute requires a list of at least one Transportation legs.")
		self.legs = legs
		self.rev = list(reversed(legs))

		self.fixed_cost = 0
		self.variable_cost = 0
		self.total_cost = 0
		self.route_emis = {"ghg": 0, "so2": 0, "nox": 0, "pm": 0}
		self.rank = rank

	def evaluate_total(self, total_volume=None, rank=None):
		if rank is None:
			rank = self.rank
		delivered_at_sink = float(self.legs[-1].volume if total_volume is None else total_volume)

		leg_results = []

		vol = delivered_at_sink
		for leg in self.rev:
			# Push current flow into leg, evaluate, then cascade delivered to next leg
			res = leg.evaluate_total(new_volume = vol, rank=rank)
			leg_results.append(res)

			self.fixed_cost += res["fixed_cost"]
			self.variable_cost += res["variable_cost"]
			self.total_cost += res["total_cost"]
			for k, v in res["emissions_totals"].items():
				self.route_emis[k] = self.route_emis.get(k, 0.0) + v

			vol = res["input_units"]
		required_at_source = vol

		return {
			"delivered_volume": delivered_at_sink,
			"initial_volume": required_at_source,
			"variable_cost": self.variable_cost,
			"fixed_cost": self.fixed_cost, 
			"total_cost": self.total_cost,
			"emissions_totals": self.route_emis,
			"legs": list(reversed(leg_results)),
		}













