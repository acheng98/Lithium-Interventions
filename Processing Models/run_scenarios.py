import helpers
from supply_chain import SupplyChain
from facility import Facility, tailings_handling
from production_step import ProductionStep
from transportation import Transportation, TransportRoute

import os
import pandas as pd
from collections import defaultdict
from copy import deepcopy
from pprint import pprint

def lithium_evaporation(sc,project_data,data_folder):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", supply_chain=sc,
							sinks = ["tailings_35","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
							location = project_data["Location 2"], # Assume lithium extraction plant is adjacent to concentrated brine facility
							steps = helpers.build_facility_dict(data_folder,project_data["Pathway 3"]))
	sc.add_facility(lithium_extraction)

	# Concentrated Brine facility 	
	conc_brine = Facility(fac_id="Concentrated Brine", supply_chain=sc,
						sinks = ["tailings_35","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
						location = project_data["Location 2"],
						steps = helpers.build_facility_dict(data_folder,project_data["Pathway 2"]))
	sc.add_facility(conc_brine, next_fac=lithium_extraction, products={"pls_post_polishing": 1})

	# Evaporation ponds 'facility' 
	evap_ponds = Facility(fac_id="Evaporation Ponds", supply_chain=sc,
						sinks = ["tailings_35","atmosphere"], # Potassium?
						location = project_data["Location 1"],
						steps = helpers.build_facility_dict(data_folder,project_data["Pathway 1"]))
	# Set conversion factor for yield from ponds, and divide by evaporation rate to get size of ponds
	evap = evap_ponds.fwd[1]
	evap_rate = project_data["Evaporation Rate"]*365 # Convert from mm/day to mm/year. Divide L/year by mm/year = m^2
	evap.set_conversion_factor("concentrated_lithium_brine",project_data["Pond Recovery Efficiency"],field="yield_rate")
	evap.set_conversion_factor("concentrated_lithium_brine",evap_rate) # Convert to m^2 of area
	evap.set_conversion_factor("pumped_brine",1/evap_rate) # Convert from m^2 of area to brine to be pumped

	# Transportation
	products = {"concentrated_lithium_brine": 1}
	if project_data["Transport 1"] is None: 
		# In certain locations - namely Silver Peak - brine is processed on-site with the ponds
		sc.add_facility(evap_ponds, next_fac=conc_brine, products=products)
	else:
		brine_route = []
		for leg,dist in project_data["Transport 1"].items():
			brine_route.append(Transportation("Brine transport via truck",sc,leg,dist))
		sc.add_facility(evap_ponds, next_fac=conc_brine, products=products, transport_route=TransportRoute("Brine transport",brine_route))

	# Fix Chemistries
	evap_ponds.add_target_comp(target = "raw_brine_from_ground", 
								composition = project_data["Initial Concentration"], 
								target_step_id = project_data["Initial Concentration Target Step"], propagate = True)
	evap_ponds.add_target_comp(target = "concentrated_lithium_brine", 
								composition = project_data["Intermediate Concentration"], 
								target_step_id = project_data["Intermediate Concentration Target Step-Before"], propagate = True)
	conc_brine.add_target_comp(target = "concentrated_lithium_brine", 
								composition = project_data["Intermediate Concentration"], 
								target_step_id = project_data["Intermediate Concentration Target Step-After"], propagate = True) # Needs to be CSTR Generic for SQM
	lithium_extraction.add_target_comp(target = "pls_post_polishing", 
								composition = conc_brine.fwd[-1].primary_outputs["pls_post_polishing"]["constituents"], # Would be nice to make a get function for this
								target_step_id = "precipitation_step", propagate = True)
	return sc 

def clay_lepidolite(sc,project_data,data_folder):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", supply_chain=sc,
								sinks=["tailings_20","tailings_25","tailings_30","tailings_35","tailings_65","tailings_solid",
								"wastewater_treatment","atmosphere"],
								location=project_data["Location 2"], # Assume lithium extraction is adjacent to leaching plant 
								steps=helpers.build_facility_dict(data_folder,project_data["Pathway 3"]))
	sc.add_facility(lithium_extraction)

	# Communition and Leaching facility 
	material_refining = Facility(fac_id="Material Refining", supply_chain=sc,
								sinks = ["tailings_20","tailings_25","tailings_30","tailings_35","tailings_65","tailings_solid",
								"offgas_handling","wastewater_treatment","atmosphere"],
								location=project_data["Location 2"],
								steps=helpers.build_facility_dict(data_folder,project_data["Pathway 2"]))
	sc.add_facility(material_refining, next_fac = lithium_extraction, products = {"pls_post_polishing": 1})

	# Transportation
	transps = []
	for leg,dist in project_data["Transport 1"].items(): 
		transps.append(Transportation("Ore transport via truck",sc,leg,dist))
	ore_truck_route = TransportRoute("Ore transport",transps)

	# Mining 'facility' 
	material_extraction = Facility(fac_id="Mining", supply_chain=sc,
									sinks = ["waste_pile","atmosphere"],
									location=project_data["Location 1"],
									steps=helpers.build_facility_dict(data_folder,project_data["Pathway 1"]))

	# PULL PROJECT-SPECIFIC DATA
	rho_bank  = project_data["Initial Density"]
	swell_factor = project_data["Swell Factor"]
	dilution = project_data["Dilution"] # Apply dilution directly to chemical composition instead
	strip_ratio = project_data["Strip Ratio"]
	rho_loose = rho_bank / swell_factor
	loss = project_data["Loss"]
	
	init_conc = project_data["Initial Concentration"]
	rom_comp = deepcopy(project_data["Initial Concentration"])
	if not project_data["ROM feed"]: # If the reported grade is not the grade at ROM, need to dilute
		rom_comp["Li"] = rom_comp["Li"] * (1 - dilution) # Apply dilution to initial composition - may need to apply to other minerals as well, or increase their makeup
	else: # ROM is reported grade
		init_conc["Li"] = rom_comp["Li"] / (1 - dilution) # Back-calculate ore grade based on dilution 

	# No-blasting scenario
	if project_data["Powder Factor"] in ["","-",None]: 
		# Update initial and final chemical compositions for extraction facility
		material_extraction.add_target_comp(target = "raw_material", composition = init_conc, target_step_id = "excav_load", propagate = False)
		material_extraction.add_target_comp(target = "rom_ore_feed", composition = rom_comp, target_step_id = "excav_load", propagate = False)

		loading = material_extraction.fwd[0]
	# Blasting scenario
	else:
		# Update initial and final chemical compositions for extraction facility
		material_extraction.add_target_comp(target = "raw_material", composition = init_conc, target_step_id = "blasting", propagate = True)
		material_extraction.add_target_comp(target = "rom_ore_feed", composition = rom_comp, target_step_id = "excav_load", propagate = False)

		loading = material_extraction.fwd[1]

		# Get second/last step and add yield
		blasting = material_extraction.fwd[0]
		blasting.set_reagents("explosives",{'targets': {"rock_blast_throughput": {'ratio': project_data["Powder Factor"], 'elim': 0.0}}})
		
	# Get conversion factor from physical volume moved to tonnes diluted ore 
	loading.set_conversion_factor("rom_ore_feed",1-loss,field="yield_rate")
	loading.set_conversion_factor("rom_ore_feed",1/(1+strip_ratio)) # get from ore --> total moved (ore + waste)
	loading.set_conversion_factor("waste", (strip_ratio + loss)/(1+strip_ratio)) # (calculate waste = strip ratio + loss)

	# Update initial and final chemical compositions for each subsequent facility module
	if project_data["Type"] == "Clays":
		material_refining.add_target_comp(target = "rom_ore_feed", composition = rom_comp, 
											target_step_id = project_data["Initial Concentration Target Step"], propagate = True)
		material_refining.add_target_comp(target = "thick_leach_feed", composition = project_data["Intermediate Concentration"], 
											target_step_id = project_data["Intermediate Concentration Target Step-Before"], propagate = False) 
		material_refining.add_target_comp(target = "thick_leach_feed", composition = project_data["Intermediate Concentration"],
											target_step_id = project_data["Intermediate Concentration Target Step-After"], propagate = True)
		# Set input lithium extraction constituents based on final constituents in material refining
		pls_post_polishing = next(iter(material_refining.fwd[-1].primary_outputs.values()))
		lithium_extraction.add_target_comp(target = "pls_post_polishing", composition = pls_post_polishing["constituents"],
											target_step_id = "precipitation_step", propagate = True)

		# Jank workaround to custom-set CCFs for solution processing because they are different between Clay & Lepidolite
		precip_step = lithium_extraction.fwd[0]
		ccf = 0.2/(0.2/2.7+0.8/1)/10**6 # Assume TDS is ~100 g/L
		precip_step.set_conversion_factor("pls_post_polishing",ccf,field="ccf")
		precip_step.set_conversion_factor("step_basis",ccf,field="ccf")
		precip_step.set_conversion_factor("lithium_slurry",project_data["Carbonate Yield Rate"],field="yield_rate")

	elif project_data["Type"] == "Lepidolite":
		material_refining.add_target_comp(target = "rom_ore_feed", composition = rom_comp, 
											target_step_id = project_data["Initial Concentration Target Step"], propagate = True)
		material_refining.add_target_comp(target = "classified_slurry", composition = project_data["Intermediate Concentration"], 
											target_step_id = project_data["Intermediate Concentration Target Step-Before"], propagate = False) 
		material_refining.add_target_comp(target = "classified_slurry", composition = project_data["Intermediate Concentration"], 
											target_step_id = project_data["Intermediate Concentration Target Step-After"], propagate = True) 
		# Some bug is causing the water leach step to not be working for some reason, so fixing it here
		material_refining.add_target_comp(target = "roasted_mix", composition = project_data["Intermediate Concentration"], 
											target_step_id = "water_leach", propagate = True) 
		material_refining.add_target_comp(target = "pregnant_leach_solution", composition = project_data["Second Intermediate Concentration"],
											target_step_id = "water_leach", propagate = True)
		material_refining.add_target_comp(target = "pregnant_leach_solution", composition = project_data["Second Intermediate Concentration"],
											target_step_id = project_data["Second Intermediate Concentration Target Step-After"], propagate = True)
		# Temporary hold - need third constituent definition for some buggy reason
		lithium_extraction.add_target_comp(target = "pls_post_polishing", composition = project_data["Second Intermediate Concentration"],
											target_step_id = "precipitation_step", propagate = True)
		# Jank workaround to custom-set CCFs for solution processing because they are different between Clay & Lepidolite
		precip_step = lithium_extraction.fwd[0]
		ccf = 0.2/(0.2/2.7+0.8/1)/10**6
		precip_step.set_conversion_factor("pls_post_polishing",ccf,field="ccf")
		precip_step.set_conversion_factor("step_basis",ccf,field="ccf")
	
	products = {"rom_ore_feed": 1}
	sc.add_facility(material_extraction, next_fac=material_refining, products=products, transport_route=ore_truck_route)	

	return sc 

def evaluate_project(sc,project_data,data_folder,detail=1,plot=1):
	summary = {}

	project_type = project_data["Type"]
	if project_type == "Brine-Evaporative":
		sc = lithium_evaporation(sc,project_data,data_folder)
		tailings_handling(sc)
	elif project_type == "Brine-DLE":
		pass 
	elif project_type == "Spodumene":
		pass
	elif project_type in ["Clays","Lepidolite"]:
		sc = clay_lepidolite(sc,project_data,data_folder)
		tailings_handling(sc)
	else:
		raise ValueError(f"Project type '{project_type}' not defined.")

	# for target_pv in target_pvs:
	target_pv = project_data["Production Volume"] # convert to kg
	helpers.update_materials(sc,project_data,"midpoint")
	# print("Summary statistics:")
	summary_midpoint = sc.update_apv(target_pv)
	summary["midpoint"] = summary_midpoint
	# pprint(summary_midpoint)
	
	if type(detail) in (float,int):
		if detail > 1:
			print("\nProduction volume at each step:")
			print("\nStep Production volumes:", sc.get_detailed_pvs())
			# print("\nAmount of lithium in each step:", sc.get_constituent_amount_at_steps("Li"))
			# print("\nAmount of lithium carbonate in each step:",sc.get_constituent_amount_at_steps("Li2CO3"))
			pprint(sc.get_step_costs(transp=True,detail=1))

		if (detail > 1) and (detail <=2):
			print(sc.get_detailed_inputs())
			pprint(sc.get_step_constituents())

		if detail > 2:
			print("\nNumber of Machines at each step:")
			pprint(sc.get_step_machines())
			print("\nReagents:")
			pprint(sc.get_total_reagents())
			print("\nUtilities:")
			pprint(sc.get_total_utilities())
			print("\nLabor:")
			pprint(sc.get_step_labor())
			print("\nCosts at each step:")
			pprint(sc.get_step_costs(transp=True,detail=2))
			print("\nImpacts at each step:")
			pprint(sc.get_step_impacts(transp=True))

		if detail == 2.5:	
			wk_compare(sc,project_type) # Output comparison metrics vs Wesselkamper et al. 2025

		if detail > 3:
			print(sc.get_step_reagent_usage())
			pprint(sc.get_step_utilities_detailed())
	else:
		if detail == "tp_debug":
			tp_debug(sc,summary_midpoint)
	
	if plot == 1:
		# sc.plot_step_costs(mode="average",view="opex",detail=3)
		sc.plot_step_costs(mode="average",view="opex",detail=2)
		sc.plot_step_impacts(mode="average")
		# sc.plot_step_costs(view="variable",detail=3)
		# sc.plot_step_costs(view="variable",detail=2)
		# sc.plot_tot_steps_impacts()
		# sc.plot_total_cc()

	helpers.update_machines(sc,"conservative")
	helpers.update_materials(sc,project_data,"conservative")
	summary_conservative = sc.update_apv(target_pv,recalc=True)
	summary["conservative"] = summary_conservative
	# pprint(summary_conservative)
	# print("\nConservative - Labor:")
	# pprint(sc.get_step_labor())
	# print("\nUtilities:")
	# pprint(sc.get_total_utilities())
	# print(sc.get_step_reagent_usage())
	# pprint(sc.get_step_utilities_detailed())

	helpers.update_machines(sc,"optimistic")
	helpers.update_materials(sc,project_data,"optimistic")
	summary_optimistic = sc.update_apv(target_pv,recalc=True)
	summary["optimistic"] = summary_optimistic
	# pprint(summary_optimistic)
	# print("\nOptimistic - Labor:")
	# pprint(sc.get_step_labor())
	# print("\nUtilities:")
	# pprint(sc.get_total_utilities())
	# print(sc.get_step_reagent_usage())
	# pprint(sc.get_step_utilities_detailed())
		

	return summary 

def wk_compare(sc,proj): # Outputs metrics for comparison against Wesselkamper et al. 2025
	step_costs = sc.get_step_costs(transp=True,detail=3)
	apv = sc.apv
	mine_opex = 0
	mine_capex = 0
	proc_reag = 0
	proc_pow = 0
	proc_other = 0
	proc_capex = 0
	if proj == "Brine-Evaporative":
		for step in step_costs:
			if step["step_id"] in ["brine_pumping", "evap_ponds"]:
				mine_opex += (step["material_costs"] + step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"])
				mine_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			elif step["step_id"] in ["batch_treatment", "sls_step","precipitation_step","thicken_dewater","wash_purif_step","drying_packaging"]:
				proc_reag += step["material_costs"]
				proc_pow += step["utility_cost_items"]["electricity"]["cost"]
				proc_other += (step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"] - step["utility_cost_items"]["electricity"]["cost"])
				proc_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			else: # wastewater, reinjection, etc.
				proc_other += step["variable_costs"]
	if proj == "Clays":
		for step in step_costs:
			if step["step_id"] in ["excav_load"]:
				mine_opex += (step["material_costs"] + step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"])
				mine_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			elif step["step_id"] in ["Ore transport via truck"]:
				mine_opex += (step["variable_costs"])
			elif step["step_id"] in ["crushing","scrubbing","classifying","thickening","acid_leaching","neutralization","ccd","impurity_removal",
										"precipitation_step","thicken_dewater","wash_purif_step","drying_packaging"]:
				proc_reag += step["material_costs"]
				proc_pow += step["utility_cost_items"]["electricity"]["cost"]
				proc_other += (step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"] - step["utility_cost_items"]["electricity"]["cost"])
				proc_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			else: # Tailings, wastewater, etc. 
				proc_other += step["variable_costs"]
	if proj == "Lepidolite":
		for step in step_costs:
			if step["step_id"] in ["blasting","excav_load"]:
				mine_opex += (step["material_costs"] + step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"])
				mine_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			elif step["step_id"] in ["Ore transport via truck"]:
				mine_opex += (step["variable_costs"])
			elif step["step_id"] in ["crushing","classifying","grinding","dewatering","sulfate_roasting","water_leach","impurity_removal","stream_clarification",
										"precipitation_step","thicken_dewater","wash_purif_step","drying_packaging"]:
				proc_reag += step["material_costs"]
				proc_pow += step["utility_cost_items"]["electricity"]["cost"]
				proc_other += (step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"] - step["utility_cost_items"]["electricity"]["cost"])
				proc_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			else: # Tailings, wastewater, etc. 
				proc_other += step["variable_costs"]
	
	print("Annual Production Volume:",apv,
		"\nAvg. Mine Opex:", mine_opex/apv,
		"\nAvg. Mine Capex:", mine_capex/apv,
		"\nAvg. Process Reagent cost:", proc_reag/apv,
		"\nAvg. Process Power cost:", proc_pow/apv,
		"\nAvg. Other Process costs:", proc_other/apv,
		"\nAvg. Process Capex costs:", proc_capex/apv)

def tp_debug(sc, summary):
	"""
	Print a clean, tabular summary of Thacker Pass calibration metrics.
	Designed for step-by-step revision tracking against the DFS.
	Call with detail=5 in evaluate_project.
	"""
	apv = sc.apv
	if not apv:
		print("ERROR: APV is zero, cannot compute per-unit metrics.")
		return
 
	# --- Summary-level metrics ---
	avg_opex = summary.get("avg_opex", 0.0)
	avg_var_cost = summary.get("avg_var_cost", 0.0)
	avg_co2 = summary.get("avg_co2", 0.0)
	avg_cost = summary.get("avg_cost", 0.0)
	avg_capex = summary.get("avg_capex", 0.0)
 
	# --- Reagents ---
	reagents = sc.get_total_reagents()
	def _reagent(name):
		r = reagents.get(name, {})
		return r.get("abs_usage", 0.0), r.get("total_cost", 0.0)
 
	acid_kg, acid_cost = _reagent("sulfuric_acid")
	lime_kg, lime_cost = _reagent("lime")
	soda_kg, soda_cost = _reagent("soda_ash")
	lstone_kg, lstone_cost = _reagent("limestone")
	floc_kg, floc_cost = _reagent("flocculant")
	water_qty, water_cost = _reagent("process_water")
 
	# --- Utilities ---
	utilities = sc.get_total_utilities()
	def _util(name):
		u = utilities.get(name, {})
		return u.get("consumed", 0.0), u.get("cost", 0.0)
 
	elec_kwh, elec_cost = _util("electricity")
	diesel_l, diesel_cost = _util("diesel")
	gas_qty, gas_cost = _util("natural_gas")
	steam_qty, steam_cost = _util("steam")
 
	# --- Labor ---
	labor = sc.get_total_labor()
	labor_workers = labor.get("labor_required", 0.0)
	labor_cost = labor.get("labor_cost", 0.0)
 
	# --- Tailings / coproducts ---
	sinks = sc.get_sink_handling_costs()
	sink_summary = {}
	for rec in sinks:
		sname = rec["sink"]
		if sname not in sink_summary:
			sink_summary[sname] = {"volume": 0.0, "cost": 0.0}
		sink_summary[sname]["volume"] += rec["volume"]
		sink_summary[sname]["cost"] += rec["total_cost"]
 
	# --- Ore throughput (from leach step PV × solids concentration) ---
	pvs = sc.get_detailed_pvs()
	leach_pv = 0.0
	for row in pvs:
		if row[0] == "acid_leaching":
			leach_pv = row[1]
			break
	ore_throughput = leach_pv * 430 / 1000	# 430 kg solids/m³ at ρ_l=1.0, ÷1000 for tonnes
 
	# --- Print ---
	sep = "=" * 72
	div = "-" * 72
 
	print(f"\n{sep}")
	print(f"  THACKER PASS CALIBRATION SUMMARY  (detail=5)")
	print(f"{sep}")
 
	print(f"\n{'HEADLINE METRICS'}")
	print(div)
	print(f"  {'APV (t LCE/yr)':<40} {apv:>14,.0f}")
	print(f"  {'avg_opex ($/t LCE)':<40} {avg_opex:>14,.0f}")
	print(f"  {'avg_var_cost ($/t LCE)':<40} {avg_var_cost:>14,.0f}")
	print(f"  {'avg_capex ($/t LCE)':<40} {avg_capex:>14,.0f}")
	print(f"  {'avg_cost ($/t LCE)':<40} {avg_cost:>14,.0f}")
	print(f"  {'avg_co2 (t CO₂/t LCE)':<40} {avg_co2:>14,.2f}")
	print(f"  {'Ore throughput (t ore/yr)':<40} {ore_throughput:>14,.0f}")
	print(f"  {'Leach slurry volume (m³/yr)':<40} {leach_pv:>14,.0f}")
 
	print(f"\n{'REAGENT CONSUMPTION':<40} {'Total/yr':>14} {'kg/t LCE':>12} {'$/t LCE':>12} {'% of opex':>10}")
	print(div)
	reagent_rows = [
		("Sulfuric acid", acid_kg, acid_cost),
		("Lime (Ca(OH)₂)", lime_kg, lime_cost),
		("Soda ash (Na₂CO₃)", soda_kg, soda_cost),
		("Limestone (CaCO₃)", lstone_kg, lstone_cost),
		("Flocculant", floc_kg, floc_cost),
		("Process water (m³)", water_qty, water_cost),
	]
	tot_reagent_cost = sum(r[2] for r in reagent_rows)
	for name, qty, cost in reagent_rows:
		pct = (cost / (avg_opex * apv) * 100) if avg_opex else 0.0
		print(f"  {name:<38} {qty:>14,.0f} {qty/apv:>12,.0f} {cost/apv:>12,.0f} {pct:>9.1f}%")
	print(f"  {'TOTAL REAGENTS':<38} {'':>14} {'':>12} {tot_reagent_cost/apv:>12,.0f}")
 
	print(f"\n{'UTILITIES':<40} {'Total/yr':>14} {'per t LCE':>12} {'$/t LCE':>12}")
	print(div)
	util_rows = [
		("Electricity (kWh)", elec_kwh, elec_cost),
		("Diesel (L)", diesel_l, diesel_cost),
		("Natural gas", gas_qty, gas_cost),
		("Steam", steam_qty, steam_cost),
	]
	tot_util_cost = sum(r[2] for r in util_rows)
	for name, qty, cost in util_rows:
		print(f"  {name:<38} {qty:>14,.0f} {qty/apv:>12,.1f} {cost/apv:>12,.0f}")
	print(f"  {'TOTAL UTILITIES':<38} {'':>14} {'':>12} {tot_util_cost/apv:>12,.0f}")
 
	print(f"\n{'LABOR'}")
	print(div)
	print(f"  {'Workers per shift':<40} {labor_workers:>14,.1f}")
	print(f"  {'Total labor cost ($/t LCE)':<40} {labor_cost/apv:>14,.0f}")
 
	print(f"\n{'TAILINGS & WASTE STREAMS':<40} {'Volume/yr':>14} {'$/t LCE':>12}")
	print(div)
	tot_sink_cost = 0.0
	for sname in sorted(sink_summary.keys()):
		sv = sink_summary[sname]
		tot_sink_cost += sv["cost"]
		print(f"  {sname:<38} {sv['volume']:>14,.0f} {sv['cost']/apv:>12,.0f}")
	print(f"  {'TOTAL SINK COSTS':<38} {'':>14} {tot_sink_cost/apv:>12,.0f}")
 
	print(f"\n{'COST BUILDUP CHECK'}")
	print(div)
	print(f"  {'Reagents':<40} {tot_reagent_cost/apv:>14,.0f}")
	print(f"  {'Utilities':<40} {tot_util_cost/apv:>14,.0f}")
	print(f"  {'Labor':<40} {labor_cost/apv:>14,.0f}")
	print(f"  {'Sinks':<40} {tot_sink_cost/apv:>14,.0f}")
	subtotal = (tot_reagent_cost + tot_util_cost + labor_cost + tot_sink_cost) / apv
	print(f"  {'Subtotal (visible opex)':<40} {subtotal:>14,.0f}")
	print(f"  {'Reported avg_opex':<40} {avg_opex:>14,.0f}")
	print(f"  {'Residual (maint+overhead+opex_excess)':<40} {avg_opex - subtotal:>14,.0f}")
	print(f"{sep}\n")

def compare_projects(projects,projects_data,transp_data,loc_data,machine_data,material_data,write=False,detail=1,plot=1):
	"""
	write=False  -> do not write to CSV
	write=True   -> write full conservative/midpoint/optimistic to standard columns
	write=N (int)-> also write a top-N restricted scenario to columns suffixed '-N'
	               (e.g. 'Our Study-Low-3', 'Our Study-Midpoint-3', 'Our Study-High-3')
	"""
	project_summaries = {}
	topn_summaries    = {}  # populated only when write is an integer
	
	# CUSTOM RANGE DEFINITIONS
	ylims_cost=(0, 7000)
	xticks_cost=range(0, 7001, 1000)
	ylims_emissions=(0, 30000)
	xticks_emissions=range(0, 30001, 5000)

	for project in projects:
		project_data = projects_data[project]
		sc = SupplyChain(transp_data,loc_data,machine_data,material_data)
		summary = evaluate_project(sc,project_data,data_folder,detail,plot=plot)
		if plot == 2:
			plot_scenario_step_costs(sc, project_data, project_data["Production Volume"],
				view="opex",	# total|variable|fixed|opex|capex  (combo not supported)
				mode="average",	# "total" | "average"
				detail=2,		# 1|2|3 — applied to midpoint bars; conservative/optimistic always use detail=1
				transp=True,
				# title=None,
				ylims=ylims_cost,
				xticks=xticks_cost,
			)
			plot_scenario_step_impacts(sc, project_data, project_data["Production Volume"],
				mode="average",         # "total" | "average"
				impact="co2",           # impact category key (e.g. "co2", "ghg")
				# title=None,
				ylims=ylims_emissions,
				xticks=xticks_emissions,
			)
		if plot == 2.1 and project == "Thacker Pass": # Custom Thacker Pass Aggregation
			helpers.thacker_pass_steps_aggregated(sc, project_data, project_data["Production Volume"],
				ylims_cost=ylims_cost,			 xticks_cost=xticks_cost,
				ylims_emissions=ylims_emissions, xticks_emissions=xticks_emissions,
			)

		if plot == 2.2 and project == "Jianxiawo":
			helpers.jianxiawo_steps_aggregated(sc, project_data, project_data["Production Volume"],
				ylims_cost=ylims_cost,			 xticks_cost=xticks_cost,
				ylims_emissions=ylims_emissions, xticks_emissions=xticks_emissions,
			)
		if plot == 3:
			tornado = run_tornado_data(sc, project_data, apv=project_data["Production Volume"])
			helpers.plot_tornado(tornado, metric="avg_opex", top_n=5)
			helpers.plot_tornado(tornado, metric="avg_co2",  top_n=5)

		project_summaries[project] = summary 
		
		# If write is an integer, run the top-N restricted scenarios now while sc is built
		if isinstance(write, int) and write > 0:
			topn_summaries[project] = run_topn_scenarios(
				sc, project_data, project_data["Production Volume"], top_n=write
			)

	# pprint(project_summaries)
	extracted_data = {}
	for key, value in project_summaries.items():
		extracted_data[key] = {}
		for sub_key, sub_value in value.items():
			extracted_data[key][sub_key] = {
				'apv': sub_value['apv'],
				'avg_opex': sub_value['avg_opex'],
				'avg_var_cost': sub_value['avg_var_cost'],
				'avg_co2': sub_value['avg_co2']/1000 # Divide by 1000 to get tonnes
			}
	
	if detail in [1,3]:
		pprint(extracted_data)
	# helpers.plot_project_summaries(project_summaries)

	if write is not False and write is not None:
		# Assumes:
		# Lithium Interventions/
		#	Processing Models/run_scenarios.py  (this file)
		#	Cost-Emissions/reported_costs.csv
		#	Cost-Emissions/reported_emissions.csv
		base_dir = os.path.dirname(os.path.abspath(__file__))
		cost_emissions_dir = os.path.normpath(os.path.join(base_dir,"..","Costs-Emissions"))
		both_csv_path = os.path.join(cost_emissions_dir,"reported_both.csv")

		# Full outputs to standard columns
		write_project_outputs_to_csv(extracted_data, both_csv_path)
		# Write top-N outputs to suffixed columns
		if isinstance(write, int) and write > 0:
			write_project_outputs_to_csv(topn_summaries, both_csv_path, col_suffix=f"-{write}")

	return extracted_data

def write_project_outputs_to_csv(extracted_data, both_csv_path, col_suffix=""):
	"""
	Write extracted_data to the CSV at both_csv_path.
 
	col_suffix: appended to each column name.
	  ""   -> writes to "Our Study-Low", "Our Study-Midpoint", "Our Study-High"
	  "-3" -> writes to "Our Study-Low-3" and "Our Study-High-3" only
	         (midpoint is omitted when a suffix is present — it's always the same)
	"""
	scen_to_col = {
		"optimistic":   f"Our Study-Low{col_suffix}",
		"midpoint":		 "Our Study-Midpoint",
		"conservative": f"Our Study-High{col_suffix}",
	}
	
	df = pd.read_csv(both_csv_path)

	# Create any missing columns so loc assignment doesn't fail
	for col in scen_to_col.values():
		if col not in df.columns:
			df[col] = None
 
	for project, scens in extracted_data.items():
		project_mask = df["Project"].astype(str) == str(project)
		if not project_mask.any():
			continue
 
		cost_mask  = project_mask & (df["Dimension"] == "Cost")
		emiss_mask = project_mask & (df["Dimension"] == "Emissions")
 
		for scen, col in scen_to_col.items():
			# Write avg_opex into Cost row
			cost_val = (scens.get(scen) or {}).get("avg_opex", None)
			if cost_mask.any():
				df.loc[cost_mask, col] = helpers.format_currency(cost_val)
 
			# Write avg_co2 into Emissions row
			emiss_val = (scens.get(scen) or {}).get("avg_co2", None)
			if emiss_mask.any():
				df.loc[emiss_mask, col] = emiss_val
 
	df.to_csv(both_csv_path, index=False)

def plot_scenario_step_costs(sc, project_data, apv, *,
	view="opex",       # total|variable|fixed|opex|capex  (combo not supported)
	mode="average",       # "total" | "average"
	detail=2,           # 1|2|3 — applied to midpoint bars; conservative/optimistic always get aggregated to detail=1
	transp=True,
	wrap_width=12,
	xscale=1,
	yscale=1,
	title=None,
	xlab='Step Names',
	ylab=None,
	xticks=None,         # explicit tick positions on the value axis
	ylims=None,          # (min, max) for the value axis
	):
	"""
	Plot midpoint step costs as stacked bars (detail=detail) with asymmetric error bars
	showing the conservative (lower) and optimistic (upper) scenario extents.
 
	The sc object must already have its facilities built (e.g. after evaluate_project or
	the relevant lithium_evaporation / clay_lepidolite call).  All three scenarios are
	re-run internally; the sc is left in the optimistic state after the call.
 
	view='combo' is not supported here — use view='opex' or view='capex' separately.
	"""
	import numpy as np
 
	view = str(view).lower().strip()
	if view == "combo":
		raise ValueError("view='combo' is not supported in plot_scenario_step_costs; use 'opex' or 'capex' separately.")
 
	mode = str(mode).lower().strip()
	if mode not in {"total", "average"}:
		raise ValueError("mode must be 'total' or 'average'")
	if mode == "average" and not apv:
		raise ValueError("apv is zero; cannot compute average costs.")
 
	def _get_totals(labels, series):
		"""Sum across all series keys to get one total per step."""
		n = len(labels)
		totals = np.zeros(n)
		for vals in series.values():
			totals += np.asarray(vals, dtype=float)
		return totals
 
	# ---- Conservative ----
	helpers.update_machines(sc, "conservative")
	helpers.update_materials(sc, project_data, "conservative")
	sc.update_apv(apv, recalc=True)
	con_labels, con_series, _ = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	con_totals = _get_totals(con_labels, con_series)
 
	# ---- Optimistic ----
	helpers.update_machines(sc, "optimistic")
	helpers.update_materials(sc, project_data, "optimistic")
	sc.update_apv(apv, recalc=True)
	opt_labels, opt_series, _ = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	opt_totals = _get_totals(opt_labels, opt_series)

	# ---- Midpoint ----
	helpers.update_machines(sc, "midpoint")
	helpers.update_materials(sc, project_data, "midpoint")
	sc.update_apv(apv, recalc=True)
	mid_labels, mid_series, stack_order = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	mid_totals = _get_totals(mid_labels, mid_series)

	# print(con_labels, mid_labels, opt_labels)
	# print(con_totals, mid_totals, opt_totals)
	# Sanity check — all three runs should produce the same step ordering
	if con_labels != mid_labels or opt_labels != mid_labels:
		raise ValueError("Step label mismatch across scenarios; check that all three runs produce the same steps.")
 
	# ---- Compute asymmetric error extents ----
	err_low  = np.maximum(mid_totals - opt_totals, 0.0)  # downward: midpoint -> optimistic
	err_high = np.maximum(con_totals - mid_totals, 0.0)  # upward:   midpoint -> conservative
 
	# ---- Apply mode scaling ----
	divisor = apv if mode == "average" else 1.0
	mid_series = {k: [v / divisor for v in vals] for k, vals in mid_series.items()}
	err_low  = err_low  / divisor
	err_high = err_high / divisor
 
	# ---- Default labels ----
	if title is None:
		base = "Cost of Steps" if mode == "total" else "Average Cost per Unit at each Step"
		title = f"{base} (with scenario range)"
	if ylab is None:
		ylab = "Total Cost" if mode == "total" else "Average Cost ($/t)"
 
	helpers.plot_stacked_bars(
		mid_labels, mid_series,
		stack_order=stack_order,
		xscale=xscale, yscale=yscale,
		title=title, xlab=xlab, ylab=ylab,
		wrap_width=wrap_width,
		err_low=err_low,
		err_high=err_high,
		xticks=xticks,
		ylims=ylims
	)

def plot_scenario_step_impacts(sc, project_data, apv, *,
	mode="average",         # "total" | "average"
	impact="co2",           # impact category key (e.g. "co2", "ghg")
	transp=True,
	wrap_width=12,
	xscale=1,
	yscale=1,
	title=None,
	xlab='Step Names',
	ylab=None,
	ylims=None,          # (min, max) for the value axis
	xticks=None,         # explicit tick positions on the value axis
	):
	"""
	Plot midpoint step impacts as stacked scope bars with asymmetric error bars
	showing the conservative (higher emissions) and optimistic (lower emissions) extents.
 
	The sc object must already have its facilities built. All three scenarios are
	re-run internally; the sc is left in the optimistic state after the call.
	"""
	import numpy as np
 
	mode = str(mode).lower().strip()
	if mode not in {"total", "average"}:
		raise ValueError("mode must be 'total' or 'average'")
	if mode == "average" and not apv:
		raise ValueError("apv is zero; cannot compute average impacts.")
 
	def _get_totals(scopes):
		"""Sum across all scope keys to get one total per step."""
		totals = None
		for vals in scopes.values():
			arr = np.asarray(vals, dtype=float)
			totals = arr if totals is None else totals + arr
		return totals if totals is not None else np.zeros(0)
 
	# ---- Conservative ----
	helpers.update_machines(sc, "conservative")
	helpers.update_materials(sc, project_data, "conservative")
	sc.update_apv(apv, recalc=True)
	con_labels, con_scopes, _ = sc._build_steps_impact_series(impact=impact, transp=transp)
	con_totals = _get_totals(con_scopes)
 
	# ---- Optimistic ----
	helpers.update_machines(sc, "optimistic")
	helpers.update_materials(sc, project_data, "optimistic")
	sc.update_apv(apv, recalc=True)
	opt_labels, opt_scopes, _ = sc._build_steps_impact_series(impact=impact, transp=transp)
	opt_totals = _get_totals(opt_scopes)
 
	# ---- Midpoint ----
	helpers.update_machines(sc, "midpoint")
	helpers.update_materials(sc, project_data, "midpoint")
	sc.update_apv(apv, recalc=True)
	mid_labels, mid_scopes, stack_order = sc._build_steps_impact_series(impact=impact, transp=transp)
	mid_totals = _get_totals(mid_scopes)
 
	# Sanity check
	if con_labels != mid_labels or opt_labels != mid_labels:
		raise ValueError("Step label mismatch across scenarios.")
 
	# ---- Compute asymmetric error extents ----
	# Conservative = higher emissions (upward bar), optimistic = lower (downward bar)
	err_high = np.maximum(con_totals - mid_totals, 0.0)
	err_low  = np.maximum(mid_totals - opt_totals, 0.0)
 
	# ---- Apply mode scaling ----
	divisor = apv if mode == "average" else 1.0
	mid_scopes = {k: [v / divisor for v in vals] for k, vals in mid_scopes.items()}
	err_low  = err_low  / divisor
	err_high = err_high / divisor
 
	# ---- Default labels ----
	if title is None:
		base = f"{impact.upper()} Impacts at each Step" if mode == "total" else f"Average {impact.upper()} Impact per Unit at each Step"
		title = f"{base} (with scenario range)"
	if ylab is None:
		ylab = f"Total {impact.upper()} (kg)" if mode == "total" else f"Avg {impact.upper()} (kg/t)"
 
	colors = {"Scope One": "#f28e2b", "Scope Two": "#4e79a7", "Scope Three": "#76b7b2"}
	helpers.plot_stacked_bars(
		mid_labels, mid_scopes,
		stack_order=stack_order,
		colors=colors,
		xscale=xscale, yscale=yscale,
		title=title, xlab=xlab, ylab=ylab,
		wrap_width=wrap_width,
		err_low=err_low,
		err_high=err_high,
		xticks=xticks,
		ylims=ylims
	)

def run_tornado_data(sc, project_data, apv):
	def _record(summary):
		return {
			"avg_opex":     summary.get("avg_opex",     0.0),
			"avg_var_cost": summary.get("avg_var_cost", 0.0),
			"avg_co2":      summary.get("avg_co2",      0.0),
		}

	def _reset_to_midpoint():
		helpers.update_machines(sc, "midpoint")
		helpers.update_materials(sc, project_data, "midpoint")

	results = {"baseline": {}, "machines": {}, "materials": {}}

	# Baseline
	_reset_to_midpoint()
	results["baseline"] = _record(sc.update_apv(apv, recalc=True))

	# Machines — vary one base at a time, hold all else at midpoint
	machine_bases = set()
	for step in sc.get_steps(transp=False):
		block = getattr(step, "machine_block", None)
		if block:
			machine_bases.add(block.split(".", 1)[0])

	for base in sorted(machine_bases):
		results["machines"][base] = {}
		for rank in ("conservative", "optimistic"):
			_reset_to_midpoint()
			helpers.update_machines(sc, {base: rank})
			results["machines"][base][rank] = _record(sc.update_apv(apv, recalc=True))

	# Materials — vary one material at a time, hold all else at midpoint
	mat_costs   = project_data.get("material_cost",   {}) or {}
	mat_impacts = project_data.get("material_impact", {}) or {}
	all_materials = set(mat_costs.keys()) | set(mat_impacts.keys())

	for material in sorted(all_materials):
		results["materials"][material] = {}
		single_proj = {
			"material_cost":   {material: mat_costs.get(material, {})},
			"material_impact": {material: mat_impacts.get(material, {})},
		}
		for rank in ("conservative", "optimistic"):
			_reset_to_midpoint()
			helpers.update_materials(sc, single_proj, rank)
			results["materials"][material][rank] = _record(sc.update_apv(apv, recalc=True))

	# Restore to midpoint
	_reset_to_midpoint()
	sc.update_apv(apv, recalc=True)

	return results

def run_topn_scenarios(sc, project_data, apv, top_n, metric="avg_opex"):
	"""
	Re-run conservative/midpoint/optimistic scenarios varying only the top_n most
	impactful machines and materials (ranked by |conservative - optimistic| range
	on `metric`).  Everything else is held at midpoint.
 
	Internally calls run_tornado_data to establish the ranking, then runs three
	targeted scenario passes.  sc is restored to midpoint after the call.
 
	Returns a dict with the same structure as evaluate_project:
	{
	    "conservative": {"apv": ..., "avg_opex": ..., "avg_var_cost": ..., "avg_co2": ...},
	    "midpoint":     {...},
	    "optimistic":   {...},
	}
	"""
	# Step 1: get tornado ranking
	tornado = run_tornado_data(sc, project_data, apv)
 
	# Step 2: build ranked list of (kind, name, opt_val, con_val)
	entries = []
	for name, vals in tornado.get("machines", {}).items():
		entries.append(("machine", name, vals["optimistic"][metric], vals["conservative"][metric]))
	for name, vals in tornado.get("materials", {}).items():
		entries.append(("material", name, vals["optimistic"][metric], vals["conservative"][metric]))
 
	entries.sort(key=lambda x: abs(x[3] - x[2]), reverse=True)
	top_entries = entries[:top_n]
 
	top_machines  = {e[1] for e in top_entries if e[0] == "machine"}
	top_materials = {e[1] for e in top_entries if e[0] == "material"}
 
	# Build a project_data slice covering only the top materials
	mat_costs   = project_data.get("material_cost",   {}) or {}
	mat_impacts = project_data.get("material_impact", {}) or {}
	top_proj = {
		"material_cost":   {m: mat_costs.get(m,   {}) for m in top_materials},
		"material_impact": {m: mat_impacts.get(m, {}) for m in top_materials},
	}
 
	# Step 3: run three scenario passes
	summary = {}
	for rank in ("conservative", "midpoint", "optimistic"):
		# Always start from a clean midpoint
		helpers.update_machines(sc, "midpoint")
		helpers.update_materials(sc, project_data, "midpoint")
		# Then apply only the top-N variables at the current rank
		if top_machines:
			helpers.update_machines(sc, {base: rank for base in top_machines})
		if top_materials:
			helpers.update_materials(sc, top_proj, rank)
		result = sc.update_apv(apv, recalc=True)
		summary[rank] = {
			"apv":          result["apv"],
			"avg_opex":     result["avg_opex"],
			"avg_var_cost": result["avg_var_cost"],
			"avg_co2":      result.get("avg_co2", 0.0) / 1000,  # kg -> t to match extracted_data convention
		}
 
	# Restore to midpoint
	helpers.update_machines(sc, "midpoint")
	helpers.update_materials(sc, project_data, "midpoint")
	sc.update_apv(apv, recalc=True)
 
	return summary

if __name__ == '__main__':
	data_folder = "./data/"

	# Load in all data
	projects_data = helpers.build_data_dict(data_folder,"Project-Specific Data")
	transp_data = helpers.build_data_dict(data_folder,"Transportation Data", col=3)
	loc_data = helpers.build_locations_dict(data_folder,"Locational Data")
	machine_data = helpers.build_data_dict(data_folder,"Machine Blocks Data", skip_rows=["notes", "sources", "key_equation", "machine_block_type"])
	material_data = helpers.build_data_dict(data_folder,"Material Data")

	################
	# Pick project #
	################
	# projects = ["Silver Peak"]
	projects = ["Thacker Pass"]
	# projects = ["Jianxiawo"]
	# projects = ["Jianxiawo","Thacker Pass"]
	# projects = ["Silver Peak","Thacker Pass"]
	# projects = ["Jianxiawo","Silver Peak","Thacker Pass"]

	write=False
	# write=True
	# write=3
	# write=5
	# detail=1
	# detail=2
	# detail=2.5
	# detail=3
	# detail=4
	detail="tp_debug"
	plot=0
	# plot=1
	# plot=2 # step-by-step breakdown
	# plot=2.1 # step-by-step breakdown - Thacker Pass Aggregation
	# plot=2.2 # step-by-step breakdown - Jianxiawo Aggregation
	# plot=3 # Tornado

	# for write in [True,3,5]:
	# 	compare_projects(projects,projects_data,transp_data,loc_data,machine_data,material_data,write=write,detail=detail,plot=plot)
	compare_projects(projects,projects_data,transp_data,loc_data,machine_data,material_data,write=write,detail=detail,plot=plot)

















