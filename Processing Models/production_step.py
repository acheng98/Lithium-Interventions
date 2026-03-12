from typing import Dict, Any, List, Optional
import copy
import math
from collections import defaultdict

from helpers import safe_float, safe_bool


# Define a class for each step of the PBCM
class ProductionStep:
		def __init__(self,
							facility,
							step_params
					):

				# Step-level details
				self.facility = facility
				self.step_id = step_params.get("step_id")
				self.step_name = step_params.get("step_name",self.step_id)
				self.key_equation = step_params.get("key_equation") # The key equation, chemical or mechanical, used in this production step
				self.notes = step_params.get("notes")
				self.sources = step_params.get("sources")

				self.machine_block = step_params.get("machine_default") # Machine or machine block modeled in this step
				self.machine_blocks = step_params.get("machine_options",[self.machine_block])

				self.step_basis = step_params.get("step_basis") # The unit of measure of the intermediate volume in the step
				self.step_basis_unit = step_params.get("step_basis_unit") # Get the units
				self.volume_defining_basis = step_params.get("volume_defining_basis")
				self.vdb_unit = step_params.get("volume_defining_basis_unit") # Get the units
				self.volume_defining_output = step_params.get("volume_defining_output")
				self.vdo_unit = step_params.get("volume_defining_output_unit") # Get the units

				self.step_pv = None # Amount of production volume of step basis 
				self.constituents = None # Chemical constituents of the step basis, aggregated from inputs
				self.step_ccf = step_params.get("step_ccf")
				
				# ERROR CHECKING
				missing = [name for name, value in {"step_id": self.step_id,
																						"machine_default": self.machine_block,
																						"step_basis": self.step_basis,
																						"volume_defining_basis": self.volume_defining_basis,
																						"volume_defining_output": self.volume_defining_output,
																						"step_ccf": self.step_ccf
																						}.items()
									if value is None]

				if missing:
						raise ValueError(f"Missing required step parameters: {', '.join(missing)}")

				# Check if step is already in facility
				if self.step_id in self.facility.steps:
						raise KeyError(f"Step with ID '{step_id}' already exists in the facility.")

				# Process parameters
				self.load_machine_data(machine_block=self.machine_block)

				# Material flows
				material_flows = step_params.get("material_flows", {})
				if material_flows is {}:
						raise ValueError(f"Material flows for step {self.step_name} are not defined, check the inputs.")
				else:
						self.primary_inputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("primary_inputs", {}))
						self.secondary_inputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("secondary_inputs", {}))
						self.primary_outputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("primary_outputs", {}))
						self.secondary_outputs: Dict[str, Dict[str, float]] = copy.deepcopy(material_flows.get("secondary_outputs", {}))

				# Steps linkage
				self.next_steps: Dict[str, "ProductionStep"] = {}
				self.previous_steps: Dict[str, "ProductionStep"] = {}

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
								f"Volume defining output '{self.volume_defining_output}' is not defined as a primary output or as a constituent in this step {self.step_name}."
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
				self.aggregate_inputs()

				valid_bases = set([self.step_basis])
				for input_data in self.primary_inputs.values():
						valid_bases.update(self.constituents.keys())

				# Check to make sure volume_defining_basis is the basis or a constituent
				if self.volume_defining_basis not in valid_bases and self.volume_defining_basis != "":
						raise KeyError(
								f"Volume defining input '{self.volume_defining_basis}' is not defined as the step basis or as a constituent in this step {self.step_name}."
						)

				for reagent_name, props in self.secondary_inputs.items():
						# Check to make sure reagent has a cost associated with it
						if reagent_name not in self.facility.material_data:
								raise KeyError(f"Reagent '{reagent_name}' does not have associated data at the facility level.")

						# Check if target constituents are in the primary input or the primary input
						target_consts = props["targets"]  # dict: {constituent: {"ratio": r, "elim": e, "usage": 0, ...}}

						# Collect all constituents across primary inputs in a set
						all_primary_constituents = {
								const
								for input_data in self.primary_inputs.values()
								for const in input_data["constituents"].keys()
						}

						# Verify each reagent target constituent is present in the <<primary inputs>> process step constituents
						for target in target_consts:
								if target not in valid_bases and target not in all_primary_constituents:
										raise KeyError(f"Reagent '{reagent_name}' requires constituent '{target}', which is not present in any primary input or the step basis.")

				# All other checks passed, add to facility
				self.facility.steps[self.step_id] = self

				# PROCESSING TIME
				self.plt = self.facility.plt # Paid labor time
				self.wlt = self.facility.wlt # Worked labor time
				self.lta = self.wlt*(1-self.unplanned_downtime-self.scheduled_maintenance) # Line time available

		#######################
		# PROCESS DEFINITIONS #
		#######################

		def load_machine_data(self, machine_block: Optional[str] = None, machine_input: Optional[Dict[str, Any]] = None) -> None:
				"""
				Load machine parameters from a machine_data dict if inputted; set ProductionStep attributes.
				"""
				if machine_block is None:
						machine_block = self.machine_block
				else:
						self.machine_block = machine_block

				if machine_input is None:
						machine_data = self.facility.sc.machine_data.get(machine_block)
				else:
						machine_data = machine_input

				if machine_data is None:
						raise KeyError(f"Machine block with name {machine_block} is not found in input machine data. ({self.facility.fac_id}, {self.step_name})")

				# -------------------------
				# Identification / metadata
				# -------------------------
				self.machine_long_name: Optional[str] = machine_data.get("block_long_name")
				self.machine_block_type: Optional[str] = machine_data.get("machine_block_type")
				self.machine_notes = machine_data.get("notes")

				# -------------------------
				# Core sizing / throughput
				# -------------------------
				self.process_type: str = machine_data.get("process_type", "batch")
				self.base_volume: float = safe_float(machine_data.get("base_volume"), 0.0)
				self.base_volume_unit: Optional[str] = machine_data.get("base_volume_unit")
				self.scaling_exponent: float = safe_float(machine_data.get("scaling_exponent_throughput"), 1.0)
				self.oversizing_factor: float = safe_float(machine_data.get("oversizing_factor"), 1.0)
				self.dedicated_line = safe_bool(machine_data.get("dedicated_line"), True)

				# -------------------------
				# Batch parameters (if any)
				# -------------------------
				self.batch_cycle_time: Optional[float] = safe_float(machine_data.get("batch_cycle_time"), 0.0)
				self.batch_cycle_time_unit: Optional[str] = machine_data.get("batch_cycle_time_unit")
				self.batch_setup_time: Optional[float] = safe_float(machine_data.get("batch_setup_time"), 0.0)
				self.batch_setup_time_unit: Optional[str] = machine_data.get("batch_setup_time_unit")

				# -------------------------
				# Utilities (base totals)
				# -------------------------
				self.electricity_base_total: float = safe_float(machine_data.get("electricity_base_total"), 0.0)
				self.electricity_base_total_unit: Optional[str] = machine_data.get("electricity_base_total_unit")

				self.natural_gas_base_total: float = safe_float(machine_data.get("natural_gas_base_total"), 0.0)
				self.natural_gas_base_total_unit: Optional[str] = machine_data.get("natural_gas_base_total_unit")

				self.diesel_base_total: float = safe_float(machine_data.get("diesel_base_total"), 0.0)
				self.diesel_base_total_unit: Optional[str] = machine_data.get("diesel_base_total_unit")

				self.propane_base_total: float = safe_float(machine_data.get("propane_base_total"), 0.0)
				self.propane_base_total_unit: Optional[str] = machine_data.get("propane_base_total_unit")

				self.cooling_water_base_total: float = safe_float(machine_data.get("cooling_water_base_total"), 0.0)
				self.cooling_water_base_total_unit: Optional[str] = machine_data.get("cooling_water_base_total_unit")

				self.steam_base_total: float = safe_float(machine_data.get("steam_base_total"), 0.0)
				self.steam_base_total_unit: Optional[str] = machine_data.get("steam_base_total_unit")

				self.compressed_air_base_total: float = safe_float(machine_data.get("compressed_air_base_total"), 0.0)
				self.compressed_air_base_total_unit: Optional[str] = machine_data.get("compressed_air_base_total_unit")

				# -------------------------
				# Equipment / CAPEX
				# -------------------------
				self.prim_equip_price_base: float = safe_float(machine_data.get("prim_equip_price_base"), 0.0)
				self.prim_equip_price_base_unit: Optional[str] = machine_data.get("prim_equip_price_base_unit")

				self.prim_equip_scaling_exponent: float = safe_float(machine_data.get("prim_equip_scaling_exponent"), 1.0)
				self.prim_equip_life: float = safe_float(machine_data.get("prim_equip_life"), 0.0)
				self.prim_equip_life_unit: Optional[str] = machine_data.get("prim_equip_life_unit")

				self.tooling_cost_base: float = safe_float(machine_data.get("tooling_cost_base"), 0.0)
				self.tooling_cost_base_unit: Optional[str] = machine_data.get("tooling_cost_base_unit")
				self.tooling_scaling_exponent: float = safe_float(machine_data.get("tooling_scaling_exponent"), 1.0)

				self.footprint_base: float = safe_float(machine_data.get("footprint_base"), 0.0)
				self.footprint_base_unit: Optional[str] = machine_data.get("footprint_base_unit")
				self.footprint_scaling_exponent: float = safe_float(machine_data.get("footprint_scaling_exponent"), 1.0)

				# -------------------------
				# Labor
				# -------------------------
				self.dedicated_labor = safe_bool(machine_data.get("dedicated_labor"), False)
				self.labor_base: float = safe_float(machine_data.get("labor_base"), 0.0)
				self.labor_base_unit: Optional[str] = machine_data.get("labor_base_unit")
				self.labor_scaling_exponent: float = safe_float(machine_data.get("labor_scaling_exponent"), 1.0)

				# -------------------------
				# Opex / availability / downtime
				# -------------------------
				self.opex_fraction_of_capex: float = safe_float(machine_data.get("opex_fraction_of_capex"), 0.0)
				self.maint: float = safe_float(machine_data.get("maint_override"), self.facility.maint)
				self.unplanned_downtime: float = safe_float(machine_data.get("unplanned_downtime"), 0.0)
				self.proc_avail_factor: float = safe_float(machine_data.get("proc_avail_factor"), 1.0)
				self.scheduled_maintenance: float = safe_float(machine_data.get("scheduled_maintenance"), 0.0)

				# Keep facility time assumptions consistent and recompute availability
				self.plt = self.facility.plt
				self.wlt = self.facility.wlt
				self.lta = self.wlt * (1 - self.unplanned_downtime - self.scheduled_maintenance)

				# Invalidate any previously calculated results that depend on machine parameters 
				# to avoid stale references in tornado plots
				for name in [
						"ltr", "machines_required", "scaled_equip_cost",
						"labor_required",
						"electricity_consumed", "natural_gas_consumed", "diesel_consumed", "propane_consumed",
						"cooling_water_consumed", "steam_consumed", "compressed_air_consumed",
						"electricity_cost", "natural_gas_cost", "diesel_cost", "propane_cost"
						"cooling_water_cost", "steam_cost", "compressed_air_cost",
						"tot_var_cost", "tot_fixed_cost", "tot_cost", "tot_opex", "tot_capex",
						"machine_cost", "tool_cost", "building_cost", "aux_equip_cost",
						"maint_cost", "fixed_over_cost",
				]:
						if hasattr(self, name):
								setattr(self, name, None)

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
								self.apply_reagents() # Ensure output composition exists to propagate.
								self.propagate_chemistry()
				elif target_name in self.secondary_outputs:
						self.secondary_outputs[target_name]["constituents"] = constituents
				else:
						raise KeyError(f"Target {target_name} not found in step {self.step_id}.")

		def set_reagents(self, target_name: str, details: dict, propagate: bool = True):
				"""
				Set the 
				Default propagate downstream as reagents may remove constituents or step basis
				"""
				if target_name in self.secondary_inputs:
						if all(key in details.keys() for key in ["name_long","targets","units","usage"]):
								self.secondary_inputs[target_name] = details
						else:
								for key,value in details.items():
										if key in ["name_long","targets","units","usage"]:
												self.secondary_inputs[target_name][key] = value
						if propagate:
								self.apply_reagents()
								self.propagate_chemistry()
				else:
						raise KeyError(f"Target {target_name} not found in step {self.step_id}.")

		def set_conversion_factor(self,target_name,factor,field="conversion_factor"):
				"""
				Set the conversion factor or yield of an input, output, coproduct, or input/basis/output constituent
				target_name : str
						Name of the flow to update, or "step_basis" to update the step-level CCF.
				factor : float
						The new value to assign.
				field : str
						The property to update. One of:
						"conversion_factor"	— unit bridge between flow and step basis (default)
						"yield_rate"				— fractional yield on a primary output
						"ccf"								— kg constituent-bearing material per basis/output unit

				CCF on the step basis is stored as self.step_ccf and is updated directly.
				CCF on inputs and outputs is stored as flow_props["ccf"] and is used in
						compute_step_pv() and propagate_chemistry().
				"""
				valid_fields = {"conversion_factor", "yield_rate", "ccf"}
				if field not in valid_fields:
						raise ValueError(
								f"Invalid field '{field}' for step {self.step_id}. "
								f"Must be one of: {', '.join(sorted(valid_fields))}."
						)

				if target_name == "step_basis":
						if field != "ccf":
								raise ValueError(
										f"'step_basis' only supports field='ccf', got '{field}' in step {self.step_id}."
								)
						self.step_ccf = factor

				elif target_name in self.primary_inputs:
						if field == "yield_rate":
								raise ValueError(
										f"'yield_rate' is only valid for primary outputs, not primary inputs "
										f"(step {self.step_id}, target '{target_name}')."
								)
						self.primary_inputs[target_name][field] = factor

				elif target_name in self.primary_outputs:
						self.primary_outputs[target_name][field] = factor

				elif target_name in self.secondary_outputs:
						if field == "yield_rate":
								raise ValueError(
										f"'yield_rate' is only valid for primary outputs, not secondary outputs "
										f"(step {self.step_id}, target '{target_name}')."
								)
						self.secondary_outputs[target_name][field] = factor

				else:
						raise KeyError(
								f"Target '{target_name}' not found in step {self.step_id}. "
								f"Use 'step_basis' to update the step-level CCF."
						)

		def aggregate_inputs(self):
				# Gather initial amounts of constituents across all primary inputs
				# Massive issue here with conversion factors and units - sufficient for now (hopefully...)
				total_consts = {}
				for input_data in self.primary_inputs.values():
						for const, amount in input_data.get("constituents", {}).items():
								if amount in ("", None):
										total_consts[const] = total_consts.get(const, 0.0) # Still set to 0 if it doesn't exist
								try:
										numeric_amount = float(amount)
										total_consts[const] = total_consts.get(const, 0.0) + numeric_amount
								except (ValueError, TypeError):
										continue

				if total_consts == {}:
						raise ValueError(f"No primary input constituents found for step {self.step_id}.")
				# Constituents exist, assign to step 
				self.constituents = total_consts

				return total_consts

		def apply_reagents(self):
				"""
				Apply reagent effects to the current step.
				Updates constituent removal and records per-unit reagent usage.

				Reagent dosing uses step_ccf to conver constituents (in PPM) to an absolute mass (per basis unit)
				before multiplying by the reagent ratio (which should thus always be in kg reagent / kg constituent).
				"""
				total_consts = self.aggregate_inputs()

				# Apply reagents
				for reagent_name, props in self.secondary_inputs.items():
						reagent_usage = 0.0

						for target, tprops in props["targets"].items():
								ratio = tprops["ratio"]
								elim  = tprops["elim"]

								if target in total_consts:
										# Convert constituent amounts (always in PPM) to kg constituent per step basis unit (always kg)
										# to kg constituent per basis unit, via step_ccf, giving a dimensionally consistent base
										base_amount = (total_consts[target]) * self.step_ccf
										remove_amount = elim * total_consts[target]

										# Apply the removal to the running state (for downstream mass balance)
										total_consts[target] = max(0.0, total_consts[target] - remove_amount)
								elif target == self.step_basis:
										# Effectively reverse yield; more step production volume is needed to balance this elimination
										# This is still a ratio though, so effectively we are just multiplying by 1 (removing from the whole step production volume)
										base_amount = 1 
										remove_amount = elim
										for const in total_consts:
												total_consts[const] = max(0.0, total_consts[const] * (1-elim))
								else:
										raise KeyError(f"Reagent '{reagent_name}' targets '{target}' which is not present.")

								reagent_usage += ratio * base_amount
								tprops["per_unit_usage"] = tprops.get("per_unit_usage", 0.0) + ratio * base_amount

						props["usage"] = reagent_usage

				# Update primary output constituents if output chemistry is dependent on inputs
				if not self.primary_outputs:
						raise ValueError(f"No primary outputs defined for step {self.step_id}.")

				# For now, assuming only one primary output. Could install a filter later. 
				for output_name in self.primary_outputs:
						if self.primary_outputs[output_name]["chemistry_dependence"]: # Only overwrite if output explicitly depends on input chemistry.
								self.primary_outputs[output_name]["constituents"] = total_consts

		def propagate_chemistry(self, propagate: bool = True):
				"""
				Push updated constituent compositions (and accompanying CCF) into next steps' inputs.
				Only applies if next step has chemistry_dependence = True.
				"""
				if not self.primary_outputs:
						return

				# For now, assuming only one primary output. Could install a filter later. 
				for output_name, output_data in self.primary_outputs.items():
						if output_data["chemistry_dependence"]: # Only continue if output explicitly depends on input chemistry.
								total_consts = output_data.get("constituents", {})
								output_ccf = output_data.get("ccf")

								for next_step in self.next_steps.values():
										if output_name in next_step.primary_inputs:
												next_step.primary_inputs[output_name]["constituents"] = copy.deepcopy(total_consts)

												if output_ccf is not None:
														next_step.primary_inputs[output_name]["ccf"] = output_ccf

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
								# Get the amount from next step's input needed
								target_volume = next_step.primary_inputs[self.volume_defining_output]["input_needed"] 
						else: # Volume defining output not a primary output, check the constituents of the primary outputs to get the actual primary output
								volume_def_output = None 
								for output,props in self.primary_outputs.items():
										if self.volume_defining_output in props["constituents"]:
												volume_def_output = output
												break
								if volume_def_output in next_step.primary_inputs:
										target_volume = next_step.primary_inputs[volume_def_output]["input_needed"] 
								else:
										raise KeyError(f"Volume-defining output {self.volume_defining_output} not in next step inputs.")
				else:
						if self.facility.apv is None:
								raise ValueError("Facility APV must be set for terminal steps.")
						target_volume = self.facility.apv

				self.aggregate_inputs()

				# --- Ratios ---
				output_props = next(iter(self.primary_outputs.values()))  # Assuming only one primary output for now
				yield_rate = output_props["yield_rate"]

				vdb = self.volume_defining_basis
				vdo = self.volume_defining_output

				output_ratio = output_props["conversion_factor"]
				output_consts = output_props.get("constituents", {})

				if vdb == self.step_basis and vdo in self.primary_outputs:
						# Case 1: step basis --> primary output; no constituents involved. 
						conversion_ratio = 1
				elif vdb in self.constituents and vdo in output_consts:
						# Case 2: input constituent → output constituent. Constituent bearing material changes identity (e.g. brine to strong brine, 
						# strong brine to carbonate). Constituent units possibly reference different materials, so convert to absolute amounts with CCFs;
						# if they are the same, the CCFs should be the same and thus cancel. 
						# 
						# conc_in × basis_ccf → constituent / basis unit (input) (e.g. kg/L)
						# conc_out × output_ccf → constituent / basis unit (output) (should also equal kg/L)
						
						basis_constituent_amt = (self.constituents[self.volume_defining_basis] ) * self.step_ccf	# kg constituent / basis unit
						output_constituent_amt = (output_consts[vdo] ) * output_props["ccf"] 										# kg constituent / basis unit
						conversion_ratio = basis_constituent_amt / output_constituent_amt / output_ratio
						# print(self.step_id,basis_constituent_amt,output_constituent_amt,conversion_ratio)
				else:
						raise KeyError(
								f"Invalid combination of volume_defining_basis '{vdb}' and volume_defining_output '{vdo}' in step {self.step_id}. "
								f"Both must either be flows (step basis / primary output) or constituents — not mixed."
						)
						
				# Calculate production volume at step
				# print(self.step_id, target_volume, self.constituents)
				self.step_pv = (target_volume / yield_rate) / output_ratio / conversion_ratio 

				# CALCULATE USAGE / DEMAND FOR ALL INPUTS
				for primary_input,input_props in self.primary_inputs.items():
						needed = self.step_pv / input_props["conversion_factor"] # Conversion factor > 1 = 
						self.primary_inputs[primary_input]["input_needed"] = needed

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
						if reagent_name not in self.facility.material_data:
								raise KeyError (f"Reagent {reagent_name} not found in facility {self.facility.fac_id}'s listed materials with data.")

						# print(reagent_name,abs_usage,self.facility.material_data[reagent_name])
						props["total_cost"] = abs_usage * self.facility.material_data[reagent_name]["cost"]

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
						("diesel_consumed",					"diesel"),
						("propane_consumed",				"propane"),
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

				# ---------- Materials / reagents (Scope 3 upstream embodied emissions) ----------
				# Requires: (1) _calc_material_costs() already run so abs_usage is populated,
				#           (2) facility.material_data[reagent] contains impact category rows
				#               (e.g. "co2": kg CO2e/kg, "water": L/kg) sourced from Material Data CSV.
				material_impacts: Dict[str, Dict[str, float]] = {}
				secondary_inputs = getattr(self, "secondary_inputs", {}) or {}
				material_data = getattr(getattr(self, "facility", None), "material_data", {}) or {}
				for reagent_name, props in secondary_inputs.items():
						abs_usage = (props or {}).get("abs_usage")
						if not abs_usage:
								continue	# _calc_material_costs not yet run, or zero consumption
						mat = material_data.get(reagent_name, {}) or {}
						# Collect whichever impact categories are populated (co2, water, …)
						# Skip cost/price rows — only numeric rows that are recognised impact categories
						IMPACT_CATEGORIES = {"co2", "water"}	# extend as more columns are added to Material Data
						factors = {cat: val for cat, val in mat.items()
								if cat in IMPACT_CATEGORIES and isinstance(val, (int, float)) and val}
						if factors:
								material_impacts[reagent_name] = {cat: abs_usage * fac for cat, fac in factors.items()}

				# ---------- Totals ----------
				scope_one_impacts: Dict[str, float] = {}
				scope_two_impacts: Dict[str, float] = {}
				scope_three_impacts: Dict[str, float] = {}
				total_step_impacts: Dict[str, float] = {}
				SCOPE_ONE_UTILITIES = {"natural_gas", "diesel", "propane"}
				for utility_key, cats in utility_impacts.items():
						target = scope_one_impacts if utility_key in SCOPE_ONE_UTILITIES else scope_two_impacts
						for cat, val in cats.items():
								target[cat] = target.get(cat, 0.0) + val
								total_step_impacts[cat] = total_step_impacts.get(cat, 0.0) + val
				for by_coproduct in sink_impacts.values():
						for cats in by_coproduct.values():
								for cat, val in cats.items():
										scope_one_impacts[cat] = scope_one_impacts.get(cat, 0.0) + val
										total_step_impacts[cat] = total_step_impacts.get(cat, 0.0) + val
				for cats in material_impacts.values():
						for cat, val in cats.items():
								scope_three_impacts[cat] = scope_three_impacts.get(cat, 0.0) + val
								total_step_impacts[cat] = total_step_impacts.get(cat, 0.0) + val

				self.utility_impacts = utility_impacts
				self.sink_impacts = sink_impacts
				self.material_impacts = material_impacts
				self.scope_one_impacts = scope_one_impacts
				self.scope_two_impacts = scope_two_impacts
				self.scope_three_impacts = scope_three_impacts
				self.total_step_impacts = total_step_impacts

				return {
						"utility_impacts": utility_impacts,
						"sink_impacts": sink_impacts,
						"material_impacts": material_impacts,
						"scope_one_impacts": scope_one_impacts,
						"scope_two_impacts": scope_two_impacts,
						"scope_three_impacts": scope_three_impacts,
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
						raise ValueError(f"Unknown process type {self.process_type} for machine {self.machine_block}.")

				# --- STEP 2: Common operational costs ---
				self._calc_material_costs()
				self._calc_labor_costs()
				self._calc_utility_costs()

				# --- STEP 3: Capital and fixed costs ---
				self._calc_capital_costs()

				# --- STEP 4: Totals ---
				self.tot_var_cost = self.tot_mat_cost + self.labor_cost + self.utility_cost + self.opex_excess
				# "OPEX" here corresponds to annual operating expenditures (variable + fixed O&M).
				self.tot_opex = self.tot_var_cost + self.maint_cost + self.fixed_over_cost

				self.tot_capex = getattr(self, "tot_capex_annualized", (self.machine_cost + self.tool_cost + self.building_cost + self.aux_equip_cost))
				self.tot_fixed_cost = self.tot_capex + self.maint_cost + self.fixed_over_cost
				
				self.tot_cost = self.tot_var_cost + self.tot_fixed_cost

				# --- STEP 5: Externalites ---
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

				self.scaled_equip_cost = self.machines_required * self.prim_equip_price_base

				# Labor required
				if self.dedicated_labor:
						self.labor_required = math.ceil(self.labor_base * self.ltr / self.lta)
				else:
						self.labor_required = self.labor_base * self.ltr / self.lta

				# Utility consumption (scale with line time)
				self.electricity_consumed = self.electricity_base_total * self.ltr
				self.natural_gas_consumed = self.natural_gas_base_total * self.ltr
				self.diesel_consumed = self.diesel_base_total * self.ltr
				self.propane_consumed = self.propane_base_total * self.ltr
				self.cooling_water_consumed = self.cooling_water_base_total * self.ltr
				self.steam_consumed = self.steam_base_total * self.ltr
				self.compressed_air_consumed = self.compressed_air_base_total * self.ltr

		def _calc_cont_scaling(self):
				'''
				Scale throughput, labor, and utilities for continuous process
				'''
				# Hours of operation assumed by design
				self.ltr = self.lta

				volume_ratio = self.step_pv / (self.base_volume * self.lta) if self.base_volume else 1.0 # Assume base volumes are always units per hour

				# Equipment scaling
				self.machines_required = 1
				self.scaled_equip_cost = (self.prim_equip_price_base *
																		(volume_ratio ** self.prim_equip_scaling_exponent))

				# Utility scaling
				self.electricity_consumed = self.electricity_base_total * (volume_ratio ** self.scaling_exponent) * self.lta
				self.natural_gas_consumed = self.natural_gas_base_total * (volume_ratio ** self.scaling_exponent) * self.lta
				self.diesel_consumed = self.diesel_base_total * (volume_ratio ** self.scaling_exponent) * self.lta
				self.propane_consumed = self.propane_base_total * (volume_ratio ** self.scaling_exponent) * self.lta
				self.cooling_water_consumed = self.cooling_water_base_total * (volume_ratio ** self.scaling_exponent) * self.lta
				self.steam_consumed = self.steam_base_total * (volume_ratio ** self.scaling_exponent) * self.lta
				self.compressed_air_consumed = self.compressed_air_base_total * (volume_ratio ** self.scaling_exponent) * self.lta

				# Labor scaling
				if self.dedicated_labor:
						self.labor_required = math.ceil(self.labor_base * (volume_ratio ** self.labor_scaling_exponent))
				else:
						self.labor_required = self.labor_base * (volume_ratio ** self.labor_scaling_exponent)

		def _calc_material_costs(self):
				'''
				Aggregate material costs from reagents and materials
				'''
				self.tot_mat_cost = 0

				# Assume only secondary inputs (i.e. reagents) are new to system and thus have costs 
				for reagent, props in self.secondary_inputs.items():
						self.tot_mat_cost += props.get("total_cost", 0)

		def _calc_labor_costs(self):
				'''
				Calculate labor cost (batch vs continuous differences already in labor_required
				'''
				self.labor_cost = self.facility.wage * self.labor_required * self.plt # May want to adapt to allow for production step-specific wages. 

		def _calc_utility_costs(self):
				"""Calculate cost of utilities based on facility prices"""
				self.electricity_cost = self.electricity_consumed * self.facility.elec_price
				self.natural_gas_cost = self.natural_gas_consumed * self.facility.gas_price
				self.diesel_cost = self.diesel_consumed * self.facility.diesel_price
				self.propane_cost = self.propane_consumed * self.facility.propane_price
				self.cooling_water_cost = self.cooling_water_consumed * self.facility.cool_water_price
				self.steam_cost = self.steam_consumed * self.facility.steam_price
				self.compressed_air_cost = self.compressed_air_consumed * self.facility.comp_air_price

				self.utility_cost = (self.electricity_cost + self.natural_gas_cost + self.diesel_cost + self.propane_cost +
															self.cooling_water_cost + self.steam_cost + self.compressed_air_cost)

		def _calc_capital_costs(self):
				"""Calculate machine, tooling, building, and overhead costs"""
				# --- Machine cost ---
				if self.prim_equip_life is not None:
						equip_crf = self.facility.calc_crf(self.facility.dr, self.prim_equip_life)
						self.machine_cost = equip_crf * self.scaled_equip_cost * self.facility.machine_cost_factor
				else:
						# Assume machine life is life of facility
						self.machine_cost = self.facility.crf * self.scaled_equip_cost * self.facility.machine_cost_factor 

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
						footprint = self.footprint_base * self.machines_required
				else:
						volume_ratio = self.step_pv / (self.base_volume * self.lta) if self.base_volume else 1.0
						footprint = self.footprint_base * (volume_ratio ** self.footprint_scaling_exponent)

				self.building_cost = self.facility.bcrf * self.facility.build_price * footprint
				self.aux_equip_cost = self.machine_cost * self.facility.aux_equip
				self.maint_cost = self.scaled_equip_cost * self.maint
				self.fixed_over_cost = (self.machine_cost + self.tool_cost +
																self.building_cost + self.aux_equip_cost +
																self.maint_cost) * self.facility.fixed_over
				self.opex_excess = (self.machine_cost + self.tool_cost + self.building_cost +
															self.aux_equip_cost + self.maint_cost) * self.opex_fraction_of_capex

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
