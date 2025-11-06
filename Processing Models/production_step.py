from typing import Dict, Any, List, Optional
import copy
import math

from helpers import safe_float, safe_bool, build_material_flows


# Define a class for each step of the PBCM
class ProductionStep:
		'''
		Current issues:
		step_pv = primary_input_pv, which would need to be disentangled later on.
		'''
		def __init__(self,
							facility,
							step_id: str,
							step_name: Optional[str] = None,
							# Step details
							key_chemical: Optional[str] = None,
							notes: Optional[str] = None,
							sources: Optional[Any] = None,
							# Process parameters grouped
							process_params: Optional[Dict[str, Any]] = None,  # e.g., {"process_type": "batch", "base_volume": 1000, ...}
							batch_params: Optional[Dict[str, Any]] = None,    # e.g., {"cycle_time": 1.0, "setup_time": 0.2, ...}
							utilities: Optional[Dict[str, Any]] = None,       # e.g., {"electricity": 1000, "natural_gas": 500, ...}
							equipment: Optional[Dict[str, Any]] = None,       # e.g., {"price": 10000, "life": 10, ...}
							labor: Optional[Dict[str, Any]] = None,           # e.g., {"dedicated": True, "base": 100, ...}
							downtime: Optional[Dict[str, float]] = None,      # {"unplanned": 0.05, "scheduled": 0.02}
							material_flows: Optional[Dict[str, Dict[str, Any]]] = None  # primary_inputs, primary_outputs, reagents, etc.
					):

				# Step-level details
				self.facility = facility
				self.step_id = step_id
				self.step_name = step_name or step_id
				self.key_chemical = key_chemical # The key chemical equation used in this production step
				self.notes = notes
				self.sources = sources

				self.step_pv = None

				# Default dictionaries if not provided
				# Maybe should probably raise errors instead of using empty dicts? we use default values
				# below but may want to inherit sometimes from facility or otherwise flag. Hard to say
				process_params = process_params or {}
				batch_params = batch_params or {}
				utilities = utilities or {}
				equipment = equipment or {}
				labor = labor or {}
				downtime = downtime or {}
				material_flows = material_flows or {}

				# Process parameters
				self.process_type: str = process_params.get("process_type", "batch")
				self.base_volume: Optional[float] = process_params.get("base_volume")
				self.base_volume_unit: Optional[str] = process_params.get("base_volume_unit")
				self.scaling_exponent: float = process_params.get("scaling_exponent", 1.0)
				self.dedicated_line: bool = process_params.get("dedicated_line", False)
				self.volume_defining_input: str = process_params.get("volume_defining_input") # Probably need to eventually clarify if this is a whole input or constituent
				self.volume_defining_output: str = process_params.get("volume_defining_output")

				# Batch
				self.batch_cycle_time: Optional[float] = batch_params.get("cycle_time")
				self.batch_cycle_time_unit: Optional[str] = batch_params.get("cycle_time_unit")
				self.batch_setup_time: Optional[float] = batch_params.get("setup_time")
				self.batch_setup_time_unit: Optional[str] = batch_params.get("setup_time_unit")
				self.scrap_rate: float = batch_params.get("scrap_rate", 0.0)

				# Utilities
				self.electricity_base_total: float = utilities.get("electricity_base_total", 0.0)
				self.electricity_base_total_unit: Optional[str] = utilities.get("electricity_base_total_unit")
				self.electricity_source: Optional[str] = utilities.get("electricity_source")

				self.natural_gas_base_total: float = utilities.get("natural_gas_base_total", 0.0)
				self.natural_gas_base_total_unit: Optional[str] = utilities.get("natural_gas_base_total_unit")
				self.natural_gas_source: Optional[str] = utilities.get("natural_gas_source")

				self.process_water_base_total: float = utilities.get("process_water_base_total", 0.0)
				self.process_water_base_total_unit: Optional[str] = utilities.get("process_water_base_total_unit")

				self.cooling_water_base_total: float = utilities.get("cooling_water_base_total", 0.0)
				self.cooling_water_base_total_unit: Optional[str] = utilities.get("cooling_water_base_total_unit")

				self.steam_base_total: float = utilities.get("steam_base_total", 0.0)
				self.steam_base_total_unit: Optional[str] = utilities.get("steam_base_total_unit")

				self.compressed_air_base_total: float = utilities.get("compressed_air_base_total", 0.0)
				self.compressed_air_base_total_unit: Optional[str] = utilities.get("compressed_air_base_total_unit")

				# Equipment
				self.prim_equip_price_base: float = equipment.get("price", 0.0)
				self.prim_equip_price_base_unit: Optional[str] = equipment.get("unit")
				self.prim_equip_scaling_exponent: float = equipment.get("scaling_exponent", 1.0)
				self.prim_equip_life: float = equipment.get("life")
				self.prim_equip_life_unit: Optional[str] = equipment.get("life_unit")
				self.tooling_cost_base: float = equipment.get("tooling_cost", 0.0)
				self.tooling_cost_base_unit: Optional[str] = equipment.get("tooling_unit")
				self.tooling_scaling_exponent: float = equipment.get("tooling_scaling_exponent", 1.0)
				self.footprint_base: float = equipment.get("footprint_base", 0.0)
				self.footprint_base_unit: Optional[str] = equipment.get("footprint_unit")
				self.footprint_scaling_exponent: float = equipment.get("footprint_scaling_exponent", 1.0)

				# Labor
				self.dedicated_labor: bool = labor.get("dedicated", False)
				self.labor_base: float = labor.get("base", 0.0)
				self.labor_base_unit: Optional[str] = labor.get("unit")
				self.labor_scaling_exponent: float = labor.get("scaling_exponent", 1.0)

				# Downtime
				self.unplanned_downtime: float = downtime.get("unplanned", self.facility.upd)
				self.scheduled_maintenance: float = downtime.get("scheduled", self.facility.scm)

				# Material flows
				self.primary_inputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("primary_inputs", {}))
				self.secondary_inputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("secondary_inputs", {}))
				self.primary_outputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("primary_outputs", {}))
				self.secondary_outputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("secondary_outputs", {}))

				# Steps linkage
				self.next_steps: Dict[str, "ProductionStep"] = {}
				self.previous_steps: Dict[str, "ProductionStep"] = {}

				# Add self to facility steps
				if step_id in self.facility.steps:
						raise KeyError(f"Step with ID '{step_id}' already exists in the facility.")
				self.facility.steps[step_id] = self

				###########################
				# LOAD INPUTS AND OUTPUTS #
				###########################

				# -------- Outputs --------

				# Connect primary outputs to next step, where it exists, and connect the two steps if it does. 
				for output_name, props in self.primary_outputs.items():
						# Check if next step id is in facility
						next_step_id = props["next_step"]
						if next_step_id in self.facility.steps:
								next_step = self.facility.steps[next_step_id]

								# Check to insure that the primary output is one of the next step's primary inputs
								if output_name in next_step.primary_inputs:
										self.next_steps[next_step_id] = next_step
										next_step.previous_steps[self.step_id] = self # Add this step to the next step's previous steps
										# NOTE FOR LATER: If multiple outputs feed the same next step, may want self.next_steps to map output names → next_step instead of step IDs → next_step.
								else:
										raise KeyError(f"Output product {output_name} is not recognized as an input to next step {next_step_id}.")
						elif next_step_id == "Final":
								self.next_steps = {} # Don't turn into none, an empty dict is symbolic of no next steps
						else:
								raise KeyError(f"Next step with id {next_step_id} is not defined in the facility.")

				# Check to make sure volume_defining_output (defined in production_step input data) is in fact listed 
				# in the primary outputs or is a constituent
				valid_outputs = set(self.primary_outputs.keys()) # Gather all valid outputs
				for output_data in self.primary_outputs.values():
						valid_outputs.update(output_data["constituents"].keys())

				if self.volume_defining_output not in valid_outputs:
						raise KeyError(
								f"Volume defining output '{self.volume_defining_output}' is not defined as a primary output or as a constituent in this step."
						)

				# Initialize connections from secondary outputs/coproducts to sinks
				for coproduct_name, props in self.secondary_outputs.items():
						sink = props["sink"]

						self.secondary_outputs[coproduct_name]["volume"] = 0.0 # will be computed later

						# Check if next step id is in facility
						if sink in self.facility.sinks:
								# Add coproduct to sink
								self.facility.sinks[sink][coproduct_name] = 0.0 # will be computed later
						else:
								raise KeyError(f"Co-product sink {sink} is not defined in the facility.")

				# --------- Inputs ---------

				# Check to make sure volume_defining_input (defined in production_step input data) is in the primary inputs or is a constituent
				valid_inputs = set(self.primary_inputs.keys()) # Gather all valid outputs
				for input_data in self.primary_inputs.values():
						valid_inputs.update(input_data["constituents"].keys())
				if self.volume_defining_input not in valid_inputs and self.volume_defining_input != "":
						raise KeyError(
								f"Volume defining input '{self.volume_defining_input}' is not defined as a primary input or as a constituent in this step."
						)

				for reagent_name, props in self.secondary_inputs.items():
						# Check to make sure reagent has a cost associated with it
						if reagent_name not in self.facility.material_costs:
								raise KeyError(f"Reagent '{reagent_name}' does not have a recorded cost at the facility level.")

						# Check if target constituents are in the primary input or the primary input
						valid_inputs = set(self.primary_inputs.keys())
						target_consts = props["targets"]  # dict: {constituent: {"ratio": r, "elim": e, "usage": 0, ...}}

						# Collect all constituents across primary inputs in a set
						all_primary_constituents = {
								const
								for input_data in self.primary_inputs.values()
								for const in input_data["constituents"].keys()
						}

						# Verify each reagent target constituent is present in the primary inputs
						for target in target_consts:
								if target not in valid_inputs and target not in all_primary_constituents:
										raise KeyError(f"Reagent '{reagent_name}' requires constituent '{target}', which is not present in any primary input.")

				# All other checks passed, add to facility
				self.facility.steps[self.step_id] = self

				# PROCESSING TIME
				self.plt = self.facility.plt # Paid labor time
				self.wlt = self.facility.wlt # Worked labor time
				self.lta = self.wlt*(1-self.unplanned_downtime-self.scheduled_maintenance) # Line time available

		##############################################
		# CLASS METHODS - DATA IMPORT (HERE FOR NOW) #
		##############################################

		@classmethod
		def from_table(cls, facility, step_vars: Dict[str, str]):
					"""Factory to build ProductionStep from a step_vars dictionary (one column)."""
					process_params = {
							"process_type": step_vars.get("process_type"),
							"base_volume": safe_float(step_vars.get("base_volume", 0.0)),
							"base_volume_unit": step_vars.get("base_volume_unit"),
							"scaling_exponent": safe_float(step_vars.get("scaling_exponent", 1.0)),
							"dedicated_line": safe_bool(step_vars.get("dedicated_line", False)),
							"volume_defining_input": step_vars.get("volume_defining_input"),
							"volume_defining_output": step_vars.get("volume_defining_output"),
					}

					batch_params = {
							"cycle_time": safe_float(step_vars.get("batch_cycle_time", 0.0)),
							"cycle_time_unit": step_vars.get("batch_cycle_time_unit"),
							"setup_time": safe_float(step_vars.get("batch_setup_time", 0.0)),
							"setup_time_unit": step_vars.get("batch_setup_time_unit"),
							"scrap_rate": safe_float(step_vars.get("scrap_rate", 0.0)),
					}

					utilities = {
							"electricity_base_total": safe_float(step_vars.get("electricity_base_total", 0.0)),
							"electricity_base_total_unit": step_vars.get("electricity_base_total_unit"),
							"electricity_source": step_vars.get("electricity_source"),
							"natural_gas_base_total": safe_float(step_vars.get("natural_gas_base_total", 0.0)),
							"natural_gas_base_total_unit": step_vars.get("natural_gas_base_total_unit"),
							"natural_gas_source": step_vars.get("natural_gas_source"),
							"process_water_base_total": safe_float(step_vars.get("process_water_base_total", 0.0)),
							"process_water_base_total_unit": step_vars.get("process_water_base_total_unit"),
							"cooling_water_base_total": safe_float(step_vars.get("cooling_water_base_total", 0.0)),
							"cooling_water_base_total_unit": step_vars.get("cooling_water_base_total_unit"),
							"steam_base_total": safe_float(step_vars.get("steam_base_total", 0.0)),
							"steam_base_total_unit": step_vars.get("steam_base_total_unit"),
							"compressed_air_base_total": safe_float(step_vars.get("compressed_air_base_total", 0.0)),
							"compressed_air_base_total_unit": step_vars.get("compressed_air_base_total_unit"),
					}

					equipment = {
							"price": safe_float(step_vars.get("prim_equip_price_base", 0.0)),
							"unit": step_vars.get("prim_equip_price_base_unit"),
							"scaling_exponent": safe_float(step_vars.get("prim_equip_scaling_exponent", 1.0)),
							"life": safe_float(step_vars.get("prim_equip_life", 0.0)),
							"life_unit": step_vars.get("prim_equip_life_unit"),
							"tooling_cost": safe_float(step_vars.get("tooling_cost_base", 0.0)),
							"tooling_unit": step_vars.get("tooling_cost_base_unit"),
							"tooling_scaling_exponent": safe_float(step_vars.get("tooling_scaling_exponent", 1.0)),
							"footprint_base": safe_float(step_vars.get("footprint_base", 0.0)),
							"footprint_unit": step_vars.get("footprint_base_unit"),
							"footprint_scaling_exponent": safe_float(step_vars.get("footprint_scaling_exponent", 1.0)),
					}

					labor = {
							"dedicated": safe_bool(step_vars.get("dedicated_labor", False)),
							"base": safe_float(step_vars.get("labor_base", 0.0)),
							"unit": step_vars.get("labor_base_unit"),
							"scaling_exponent": safe_float(step_vars.get("labor_scaling_exponent", 1.0)),
					}

					downtime = {
							"unplanned": safe_float(step_vars.get("unplanned_downtime", 0.0)),
							"scheduled": safe_float(step_vars.get("scheduled_maintenance", 0.0)),
					}

					material_flows = build_material_flows(step_vars)

					return cls(
							facility=facility,
							step_id=step_vars["step_id"],
							step_name=step_vars.get("step_name"),
							key_chemical=step_vars.get("key_chemical"),
							notes=step_vars.get("notes"),
							sources=step_vars.get("sources"),
							process_params=process_params,
							batch_params=batch_params,
							utilities=utilities,
							equipment=equipment,
							labor=labor,
							downtime=downtime,
							material_flows=material_flows
					)

		#######################
		# PROCESS DEFINITIONS #
		#######################

		def set_constituents(self, target_name: str, constituents: dict, propagate: bool = False):
				"""
				Set the chemical composition of an input, output, or coproduct.
				Optionally propagate downstream if chemistry dependent.
				"""
				if target_name in self.primary_inputs:
						self.primary_inputs[target_name]["constituents"] = constituents
						if propagate:
								self.apply_reagents() # Ensure output composition exists to propagate.
								self.propagate_chemistry()
				elif target_name in self.primary_outputs:
						self.primary_outputs[target_name]["constituents"] = constituents
						if propagate:
								self.propagate_chemistry()
				elif target_name in self.secondary_outputs:
						self.secondary_outputs[target_name]["constituents"] = constituents
				else:
						raise KeyError(f"Target {target_name} not found in step {self.step_id}.")

		def apply_reagents(self):
				"""
				Apply reagent effects to the current step.
				Updates constituent removal and records per-unit reagent usage.
				"""
				# Gather initial amounts of constituents across all primary inputs
				total_consts = {}
				for input_data in self.primary_inputs.values():
						for const, amount in input_data.get("constituents", {}).items():
								if amount in ("", None):
										continue
								try:
										numeric_amount = float(amount)
										total_consts[const] = total_consts.get(const, 0.0) + numeric_amount
								except (ValueError, TypeError):
										continue

				if not total_consts:
						raise ValueError(f"No primary input constituents found for step {self.step_id}.")

				# Apply reagents
				for reagent_name, props in self.secondary_inputs.items():
						reagent_usage = 0.0

						for target, tprops in props["targets"].items():
								ratio = tprops["ratio"]
								elim  = tprops["elim"]

								if target in total_consts:
										remove_amount = elim * total_consts[target]
										total_consts[target] = max(0.0, total_consts[target] - remove_amount)
								elif target in self.primary_inputs:
										# Reduce input conversion factor
										conv = self.primary_inputs[target]["conversion_factor"]
										self.primary_inputs[target]["conversion_factor"] = conv * (1 - elim)
										remove_amount = conv * elim
								else:
										raise KeyError(f"Reagent '{reagent_name}' targets '{target}' which is not present.")

								reagent_usage += ratio * remove_amount
								tprops["per_unit_usage"] = tprops.get("per_unit_usage", 0.0) + ratio * remove_amount

						props["usage"] = reagent_usage

				# Update primary output constituents if output chemistry is dependent on inputs
				if not self.primary_outputs:
						raise ValueError(f"No primary outputs defined for step {self.step_id}.")
				output_name = next(iter(self.primary_outputs))
				if self.primary_outputs[output_name]["chemistry_dependence"]: # Only overwrite if output explicitly depends on input chemistry.
						self.primary_outputs[output_name]["constituents"] = total_consts

		def propagate_chemistry(self, propagate: bool = True):
				"""
				Push updated constituent compositions into next steps' inputs.
				Only applies if next step has chemistry_dependence = True.
				"""
				if not self.primary_outputs:
						return

				output_name, output_data = next(iter(self.primary_outputs.items())) # Assume only one primary output for now
				total_consts = output_data.get("constituents", {})

				for next_step in self.next_steps.values():
						if output_name in next_step.primary_inputs:
								next_step.primary_inputs[output_name]["constituents"] = copy.deepcopy(total_consts)

								if next_step.primary_inputs[output_name].get("chemistry_dependence") and propagate:
										next_step.apply_reagents()
										next_step.propagate_chemistry(propagate=True)
						else:
								raise KeyError(f"Output {output_name} not found in next step {next_step.step_id} inputs.")

		def compute_step_pv(self, propagate: bool = False):
				"""
				Compute the production volume for this step.
				Propagates volumes backward to previous steps if requested.
				"""
				# --- Target volume ---
				if self.next_steps:
						next_step = next(iter(self.next_steps.values()))
						if next_step.step_pv is None:
								raise ValueError(f"Next step {next_step.step_id} volume not yet calculated.")

						if self.volume_defining_output in next_step.primary_inputs:
								target_volume = next_step.step_pv
						else:
								raise KeyError(f"Volume-defining output {self.volume_defining_output} not in next step inputs.")
				else:
						if self.facility.apv is None:
								raise ValueError("Facility APV must be set for terminal steps.")
						target_volume = self.facility.apv

				# --- Ratios ---
				output_props = next(iter(self.primary_outputs.values()))  # Assuming only one primary input for now
				yield_rate = output_props["yield_rate"]

				if self.volume_defining_output in self.primary_outputs:
						output_ratio = 1.0
				else: # not a primary output, check the constituents
						output_consts = output_props.get("constituents", {})
						if self.volume_defining_output in output_consts:
								output_ratio = output_consts[self.volume_defining_output]
						else:
								raise KeyError(f"Volume-defining output '{self.volume_defining_output}' not found in step {self.step_id}.")

				if self.volume_defining_input in self.primary_inputs:
						input_ratio = self.primary_inputs[self.volume_defining_input]["conversion_factor"]
				else: # not a primary input, check the constituents
						primary_input = next(iter(self.primary_inputs.values())) # Assuming only one primary input for now
						input_consts = primary_input.get("constituents", {})
						if self.volume_defining_input in input_consts:
								# Multiply here because pv is being divided by input ratio - check to ensure
								input_ratio = primary_input["conversion_factor"] * input_consts[self.volume_defining_input] 
						else:
								raise KeyError(f"Volume-defining input {self.volume_defining_input} not found in step {self.step_id}.")

				self.step_pv = (target_volume / yield_rate) * (output_ratio / input_ratio)

				# --- Scale reagents ---
				self.scale_reagents()

				# --- Co-product volumes ---
				for coproduct_name, props in self.secondary_outputs.items():
						conv = props["conversion_factor"]
						coproduct_volume = self.step_pv * conv * yield_rate
						self.secondary_outputs[coproduct_name]["volume"] = coproduct_volume

						sink_name = props["sink"]
						if sink_name in self.facility.sinks:
								self.facility.sinks[sink_name][coproduct_name] = (
										self.facility.sinks[sink_name].get(coproduct_name, 0.0) + coproduct_volume
								)
						else:
								raise KeyError(f"Sink {sink_name} not defined in facility.")

				# --- Propagate upstream volumes ---
				if propagate and self.previous_steps:
						for prev_step in self.previous_steps.values():
								prev_step.compute_step_pv(propagate=True)

		def scale_reagents(self):
				"""
				Convert per-unit reagent usage into absolute consumption.
				Requires step_pv to be set.
				"""
				if self.step_pv is None:
						raise ValueError(f"Step {self.step_id} step_pv must be set before scaling reagents.")

				for reagent_name, props in self.secondary_inputs.items():
						usage_fraction = props.get("usage")
						if usage_fraction is None:
								raise ValueError(f"Reagent {reagent_name} has no per-unit usage (run apply_reagents first).")

						abs_usage = usage_fraction * self.step_pv
						props["abs_usage"] = abs_usage
						props["total_cost"] = abs_usage * self.facility.material_costs.get(reagent_name, 0.0)

		from typing import Dict, Any

		def calculate_environmental_impacts(self, impact_factors: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
				"""
				Compute environmental impacts for THIS step by multiplying this step's
				utility use and sinked coproduct volumes by the provided impact_factors.

				Parameters
				----------
				impact_factors : dict
						Expected keys for utilities like:
								{"electricity": {...}, "natural_gas": {...}, ...}
						And (optionally) sink factors either as:
								impact_factors["sinks"][sink_name][coproduct_name] -> {category: factor}
						or flat:
								impact_factors[sink_name] -> {category: factor}

				Returns
				-------
				dict
						{
							"utility_impacts": { utility: {category: value, ...}, ... },
							"sink_impacts":    { sink: { coproduct: {category: value, ...}, ... }, ... },
							"total_step_impacts":   { category: total_value_across_utilities_and_sinks }
						}
				"""
				def _lookup_sink_factors(sink_name: str, coproduct_name: str) -> Dict[str, float]:
						sinks_block = (impact_factors or {}).get("sinks", {})
						# Prefer coproduct-specific factors if present
						if isinstance(sinks_block, dict) and sink_name in sinks_block:
								maybe = sinks_block.get(sink_name, {})
								if isinstance(maybe, dict) and coproduct_name in maybe:
										return maybe.get(coproduct_name, {}) or {}
								return maybe if isinstance(maybe, dict) else {}
						# Fallback to top-level sink block (no coproduct specificity)
						return (impact_factors or {}).get(sink_name, {}) or {}

				# Map this class's attributes -> impact_factors keys
				utility_map = [
						("electricity_consumed",    "electricity"),
						("natural_gas_consumed",    "natural_gas"),
						("process_water_consumed",  "process_water"),
						("cooling_water_consumed",  "cooling_water"),
						("steam_consumed",          "steam"),
						("compressed_air_consumed", "compressed_air"),
						# Add more if necessary
				]

				# ---------- Utilities ----------
				utility_impacts: Dict[str, Dict[str, float]] = {}
				for attr, key in utility_map:
						qty = getattr(self, attr, 0.0) or 0.0
						if not qty:
								continue
						factors = (impact_factors or {}).get(key, {}) or {}
						if factors:
								utility_impacts[key] = {cat: qty * fac for cat, fac in factors.items()}

				# ---------- Sinks (coproducts routed to landfill/wastewater/air/etc.) ----------
				sink_impacts: Dict[str, Dict[str, Dict[str, float]]] = {}
				secondary_outputs = getattr(self, "secondary_outputs", {}) or {}
				for coproduct_name, props in secondary_outputs.items():
						sink_name = (props or {}).get("sink")
						volume = (props or {}).get("volume", 0.0) or 0.0
						if not sink_name or not volume:
								continue
						factors = _lookup_sink_factors(sink_name, coproduct_name)
						if not factors:
								continue
						sink_impacts.setdefault(sink_name, {})
						sink_impacts[sink_name][coproduct_name] = {
								cat: volume * fac for cat, fac in factors.items()
						}

				# ---------- Totals ----------
				scope_one_impacts: Dict[str, float] = {}
				scope_two_impacts: Dict[str, float] = {}
				total_step_impacts: Dict[str, float] = {}
				for cats in utility_impacts.values():
						for cat, val in cats.items():
								scope_two_impacts[cat] = scope_two_impacts.get(cat, 0.0) + val
								total_step_impacts[cat] = total_step_impacts.get(cat, 0.0) + val
				for by_coproduct in sink_impacts.values():
						for cats in by_coproduct.values():
								for cat, val in cats.items():
										scope_one_impacts[cat] = scope_one_impacts.get(cat, 0.0) + val
										total_step_impacts[cat] = total_step_impacts.get(cat, 0.0) + val

				self.utility_impacts = utility_impacts
				self.sink_impacts = sink_impacts
				self.scope_one_impacts = scope_one_impacts
				self.scope_two_impacts = scope_two_impacts
				self.total_step_impacts = total_step_impacts

				return {
						"utility_impacts": utility_impacts,
						"sink_impacts": sink_impacts,
						"scope_one_impacts": scope_one_impacts,
						"scope_two_impacts": scope_two_impacts,
						"total_step_impacts": total_step_impacts,
				}

		#######################################
		# CALCULATE ALL COSTS & EXTERNALITIES #
		#######################################
		def calculate(self):
				# --- STEP 1: Process-type specific throughput & scaling ---
				if self.process_type == "batch":
						self._calc_batch_scaling()
				elif self.process_type == "continuous":
						self._calc_cont_scaling()
				else:
						raise ValueError(f"Unknown process type {self.process_type}")

				# --- STEP 2: Common operational costs ---
				self._calc_material_costs()
				self._calc_labor_costs()
				self._calc_utility_costs()

				# --- STEP 3: Capital and fixed costs ---
				self._calc_capital_costs()

				# --- STEP 4: Totals ---
				self.tot_var_cost = self.tot_mat_cost + self.labor_cost + self.utility_cost
				self.tot_fixed_cost = (self.machine_cost + self.tool_cost +
																self.building_cost + self.aux_equip_cost +
																self.maint_cost + self.fixed_over_cost)
				self.tot_cost = self.tot_var_cost + self.tot_fixed_cost

				# --- STEP 5: Externalites --- # Should this be here? 
				self.calculate_environmental_impacts(self.facility.impact_factors)

		##############################
		# INTERNAL COST CALC HELPERS #
		##############################

		def _calc_batch_scaling(self):
				"""Scale throughput, machine, and labor for batch process"""
				self.ltr = self.step_pv / (self.base_volume / (self.batch_cycle_time + self.batch_setup_time))  # line time required

				# Machines required
				if self.dedicated_line:
						self.machines_required = math.ceil(self.ltr / self.lta)
				else:
						self.machines_required = self.ltr / self.lta

				self.scaled_equip_price = self.machines_required * self.prim_equip_price_base

				# Labor required
				if self.dedicated_labor:
						self.labor_required = math.ceil(self.labor_base * self.ltr / self.lta)
				else:
						self.labor_required = self.labor_base * self.ltr / self.lta

				# Utility consumption (scale with line time)
				self.electricity_consumed = self.electricity_base_total * self.ltr
				self.natural_gas_consumed = self.natural_gas_base_total * self.ltr
				self.process_water_consumed = self.process_water_base_total * self.ltr
				self.cooling_water_consumed = self.cooling_water_base_total * self.ltr
				self.steam_consumed = self.steam_base_total * self.ltr
				self.compressed_air_consumed = self.compressed_air_base_total * self.ltr

		def _calc_cont_scaling(self):
				'''
				Scale throughput, labor, and utilities for continuous process
				'''
				volume_ratio = self.step_pv / self.base_volume if self.base_volume else 1.0

				# Equipment scaling
				self.machines_required = 1
				self.scaled_equip_price = (self.prim_equip_price_base *
																		(volume_ratio ** self.prim_equip_scaling_exponent))

				# Utility scaling
				self.electricity_consumed = self.electricity_base_total * (volume_ratio ** self.scaling_exponent)
				self.natural_gas_consumed = self.natural_gas_base_total * (volume_ratio ** self.scaling_exponent)
				self.process_water_consumed = self.process_water_base_total * (volume_ratio ** self.scaling_exponent)
				self.cooling_water_consumed = self.cooling_water_base_total * (volume_ratio ** self.scaling_exponent)
				self.steam_consumed = self.steam_base_total * (volume_ratio ** self.scaling_exponent)
				self.compressed_air_consumed = self.compressed_air_base_total * (volume_ratio ** self.scaling_exponent)

				# Labor scaling
				self.labor_required = self.labor_base * (volume_ratio ** self.labor_scaling_exponent)

		def _calc_material_costs(self):
				'''
				Aggregate material costs from reagents and materials
				'''
				self.tot_mat_cost = 0

				# New structure: reagents in secondary_inputs
				for reagent, props in self.secondary_inputs.items():
						self.tot_mat_cost += props.get("total_cost", 0)

				# Structure for primary_inputs - not currently used
				# for primary_input, props in self.primary_inputs.items():
				#     self.tot_mat_cost += props.get("total_cost", 0)

		def _calc_labor_costs(self):
				'''
				Calculate labor cost (batch vs continuous differences already in labor_required
				'''
				self.labor_cost = self.facility.wage * self.labor_required * self.plt # May want to adapt to allow for production step-specific wages. 

		def _calc_utility_costs(self):
				"""Calculate cost of utilities based on facility prices"""
				self.electricity_cost = self.electricity_consumed * self.facility.elec_price
				self.natural_gas_cost = self.natural_gas_consumed * self.facility.gas_price
				self.process_water_cost = self.process_water_consumed * self.facility.proc_water_price
				self.cooling_water_cost = self.cooling_water_consumed * self.facility.cool_water_price
				self.steam_cost = self.steam_consumed * self.facility.steam_price
				self.compressed_air_cost = self.compressed_air_consumed * self.facility.comp_air_price

				self.utility_cost = (self.electricity_cost + self.natural_gas_cost +
															self.process_water_cost + self.cooling_water_cost +
															self.steam_cost + self.compressed_air_cost)

		def _calc_capital_costs(self):
				"""Calculate machine, tooling, building, and overhead costs"""
				# --- Machine cost ---
				if self.prim_equip_life is not None:
						equip_crf = self.facility.calc_crf(self.facility.dr, self.prim_equip_life)
						self.machine_cost = equip_crf * self.scaled_equip_price
				else:
						self.machine_cost = self.facility.crf * self.scaled_equip_price # Assume machine life is life of facility

				# --- Tool cost ---
				if hasattr(self, "tool_price") and self.tool_price:
						if self.tool_life is not None:
								tool_crf = crf(self.facility.dr, self.tool_life)
								self.tool_cost = tool_crf * self.tool_price * getattr(self, "machines_required", 1) * getattr(self, "tool_use", 1)
						else:
								self.tool_cost = self.facility.crf * self.tool_price * getattr(self, "machines_required", 1) * getattr(self, "tool_use", 1)
				elif hasattr(self, "tooling_cost_base") and self.tooling_cost_base:
						if self.tool_life is not None:
								tool_crf = crf(self.facility.dr, self.tool_life)
								self.tool_cost = tool_crf * self.tooling_cost_base
						else:
								self.tool_cost = self.facility.crf * self.tooling_cost_base
				else:
						self.tool_cost = 0

				# --- Building, aux, maintenance, overhead ---
				if self.process_type == "batch":
						footprint = self.footprint_base
				else:
						volume_ratio = self.step_pv / self.base_volume if self.base_volume else 1.0
						footprint = self.footprint_base * (volume_ratio ** self.footprint_scaling_exponent)

				self.building_cost = self.facility.bcrf * self.facility.build_price * footprint
				self.aux_equip_cost = self.machine_cost * self.facility.aux_equip
				self.maint_cost = self.machine_cost * self.facility.maint
				self.fixed_over_cost = (self.machine_cost + self.tool_cost +
																self.building_cost + self.aux_equip_cost +
																self.maint_cost) * self.facility.fixed_over

		########################
		# CLASS HELPER METHODS #
		########################

		def get_next_step(self, output_name): # NOTE THIS ASSUMES ONLY ONE NEXT STEP
				step_id = self.primary_outputs[output_name]["step_id"]
				if step_id == "final":
						return None
				return self.facility.steps[step_id]

		def proc_inputs(self):
				for mat,props in self.new_mats.items():
						print("Input material", mat, "has demand", props["demand"], "at cost", props["total_cost"])

		def proc_outputs(self):
				print("Effective Step Production Volume:",self.step_pv)
				print("Line time available per line:",self.lta)
				print("Line time required per line:",self.ltr)
				print("Lines required:",self.machines_required)

		def op_outputs(self):
				print("Energy consumption:",self.energy_consumed)
				print("Laborers required:",self.labor_required)

		def return_costs(self):
				print("\n")
				self.return_var_costs()
				self.return_fixed_costs()
				print("TOTAL STEP COSTS:", self.tot_cost, "\n")

		def return_var_costs(self):
				print("VARIABLE COSTS:")
				print("Step Material Costs:", self.tot_mat_cost)
				print("Step Labor Costs:", self.labor_cost)
				print("Step Energy Costs:", self.energy_cost)
				print("Step Variable Costs:", self.tot_var_cost)

		def return_fixed_costs(self):
				print("FIXED COSTS:")
				print("Step Machine Costs:", self.machine_cost)
				print("Step Tool Costs:", self.tool_cost)
				print("Step Building Costs:", self.building_cost)
				print("Step Auxiliary Equipment Costs:", self.aux_equip_cost)
				print("Step Maintenance Costs:", self.maint_cost)
				print("Step Fixed Overhead Costs:", self.fixed_over_cost)
				print("Step Fixed Costs:", self.tot_fixed_cost)
