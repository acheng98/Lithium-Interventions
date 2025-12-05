from typing import Dict, Any, List, Optional
import copy
from collections import defaultdict

from helpers import safe_float, parse_numeric

# Define a class for the production environment
class Transportation:
	def __init__(
		self,
		name, 			# name for this transportation leg
		transp_data,	# dataframe with transportation option data
		mode,			# string label, e.g. "liquid_tanker_truck_diesel"
		distance,		# distance in km for this leg
		volume = 0,		# target volume transported - can be left out / initialized as 0 to be updated later
	):
		self.name = name
		self.mode = mode
		self.distance = distance # in KM
		self.volume = volume
		if mode not in transp_data:
			raise KeyError(f"Transportation mode '{mode}' not found in input tranportation data.")
		mode_data = transp_data[mode]
		self.cost_pkm = parse_numeric(mode_data[3])
		self.ghg_emissions_pkm = safe_float(mode_data[10])
		self.so2_emissions_pkm = safe_float(mode_data[13])
		self.nox_emissions_pkm = safe_float(mode_data[16])
		self.pm_emissions_pkm = safe_float(mode_data[19])
		# For now - only include losses within the transportation step. Assume that all calculations/costs based on initial volume.
		self.loss_fraction = safe_float(mode_data[22]) 
		self.fixed_cost = safe_float(mode_data[2]) 
		self.ref_volume = safe_float(mode_data[0])

		self.input_volume = self.volume / (1.0 - self.loss_fraction)

	def evaluate_total(self, new_volume = None):
		"""
		Evaluate this leg on a total volume.
		Returns totals: delivered_units, cost_total, emissions_total dict.
		"""
		if new_volume is not None:
			self.volume = new_volume

		self.input_volume = self.volume / (1.0 - self.loss_fraction)

		self.variable_cost = self.cost_pkm * self.distance * self.input_volume
		self.total_cost = self.fixed_cost + self.variable_cost

		dist_trips = self.distance * self.input_volume # / self.ref_volume 

		self.emissions_totals = {
			"ghg": self.ghg_emissions_pkm * dist_trips,
			"so2": self.so2_emissions_pkm * dist_trips,
			"nox": self.nox_emissions_pkm * dist_trips,
			"pm":  self.pm_emissions_pkm  * dist_trips,
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
	def __init__(self, name, legs):
		self.name = name 
		if type(legs) is not List and len(legs) == 0:
			raise ValueError("TransportRoute requires a list of at least one Transportation legs.")
		self.legs = legs
		self.rev = list(reversed(legs))

		self.fixed_cost = 0
		self.variable_cost = 0
		self.total_cost = 0
		self.route_emis = {"ghg": 0, "so2": 0, "nox": 0, "pm": 0}

	def evaluate_total(self, total_volume=None):
		delivered_at_sink = float(self.legs[-1].volume if total_volume is None else total_volume)

		leg_results = []

		vol = delivered_at_sink
		for leg in self.rev:
			# Push current flow into leg, evaluate, then cascade delivered to next leg
			res = leg.evaluate_total(new_volume = vol)
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













