import helpers
from supply_chain import SupplyChain
from facility import Facility, ReagentFacility
from sinks import load_sink_params, tailings_handling, sink_s_out, sink_override_map, apply_sink_overrides
from production_step import ProductionStep
from transportation import Transportation, TransportRoute
import matplotlib
import matplotlib.pyplot as plt

import os
import pandas as pd
import numpy as np
from collections import defaultdict
from copy import deepcopy
from pprint import pprint

def lithium_evaporation(sc,pathway_data,data_folder):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", supply_chain=sc,
							sinks = sc.sink_names,
							location = pathway_data["Location 2"], # Assume lithium extraction plant is adjacent to concentrated brine facility
							steps = helpers.build_facility_dict(data_folder,pathway_data["Facility 3"]))
	sc.add_facility(lithium_extraction)

	# Concentrated Brine facility 	
	conc_brine = Facility(fac_id="Concentrated Brine", supply_chain=sc,
						sinks = sc.sink_names,
						location = pathway_data["Location 2"],
						steps = helpers.build_facility_dict(data_folder,pathway_data["Facility 2"]))
	sc.add_facility(conc_brine, next_fac=lithium_extraction, products={"pls_post_polishing": 1})

	# Evaporation ponds 'facility' 
	evap_ponds = Facility(fac_id="Evaporation Ponds", supply_chain=sc,
						sinks = sc.sink_names, # Potassium?
						location = pathway_data["Location 1"],
						steps = helpers.build_facility_dict(data_folder,pathway_data["Facility 1"]))
	# Set conversion factor for yield from ponds, and divide by evaporation rate to get size of ponds
	evap = evap_ponds.fwd[1]
	evap_rate = pathway_data["Evaporation Rate"]*365 # Convert from mm/day to mm/year. Divide L/year by mm/year = m^2
	evap.set_conversion_factor("concentrated_lithium_brine",pathway_data["Pond Recovery Efficiency"],field="yield_rate")
	evap.set_conversion_factor("concentrated_lithium_brine",evap_rate) # Convert to m^2 of area
	evap.set_conversion_factor("evaporated_water",evap_rate) # Calculate evaporated water from rate times surface area
	evap.set_conversion_factor("pumped_brine",1/evap_rate) # Convert from m^2 of area to brine to be pumped

	# Transportation
	products = {"concentrated_lithium_brine": 1}
	if pathway_data["Transport 1"] is None: 
		# In certain locations - namely Silver Peak - brine is processed on-site with the ponds
		sc.add_facility(evap_ponds, next_fac=conc_brine, products=products)
	else:
		brine_route = []
		for leg,dist in pathway_data["Transport 1"].items():
			brine_route.append(Transportation("Brine transport via truck",sc,leg,dist))
		sc.add_facility(evap_ponds, next_fac=conc_brine, products=products, transport_route=TransportRoute("Brine transport",brine_route))

	# Fix Chemistries
	evap_ponds.add_target_comp(target = "raw_brine_from_ground", 
								composition = pathway_data["Initial Concentration"], 
								target_step_id = pathway_data["Initial Concentration Target Step"], propagate = True)
	evap_ponds.add_target_comp(target = "concentrated_lithium_brine", 
								composition = pathway_data["Intermediate Concentration"], 
								target_step_id = pathway_data["Intermediate Concentration Target Step-Before"], propagate = True)
	conc_brine.add_target_comp(target = "concentrated_lithium_brine", 
								composition = pathway_data["Intermediate Concentration"], 
								target_step_id = pathway_data["Intermediate Concentration Target Step-After"], propagate = True) # Needs to be CSTR Generic for SQM
	lithium_extraction.add_target_comp(target = "pls_post_polishing", 
								composition = conc_brine.fwd[-1].primary_outputs["pls_post_polishing"]["constituents"], # Would be nice to make a get function for this
								target_step_id = "precipitation_step", propagate = True)
	return sc 

def clay_lepidolite(sc,pathway_data,data_folder):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", supply_chain=sc,
								sinks = sc.sink_names,
								location=pathway_data["Location 2"], # Assume lithium extraction is adjacent to leaching plant 
								steps=helpers.build_facility_dict(data_folder,pathway_data["Facility 3"]))
	sc.add_facility(lithium_extraction)

	# Communition and Leaching facility 
	material_refining = Facility(fac_id="Material Refining", supply_chain=sc,
								sinks = sc.sink_names,
								location=pathway_data["Location 2"],
								steps=helpers.build_facility_dict(data_folder,pathway_data["Facility 2"]))
	sc.add_facility(material_refining, next_fac = lithium_extraction, products = {"pls_post_polishing": 1})

	# Transportation
	transps = []
	for leg,dist in pathway_data["Transport 1"].items(): 
		transps.append(Transportation("Ore transport via truck",sc,leg,dist))
	ore_truck_route = TransportRoute("Ore transport",transps)

	# Mining 'facility' 
	material_extraction = Facility(fac_id="Mining", supply_chain=sc,
									sinks = sc.sink_names,
									location=pathway_data["Location 1"],
									steps=helpers.build_facility_dict(data_folder,pathway_data["Facility 1"]))

	# PULL PATHWAY-SPECIFIC DATA
	rho_bank  = pathway_data["Initial Density"]
	swell_factor = pathway_data["Swell Factor"]
	dilution = pathway_data["Dilution"] # Apply dilution directly to chemical composition instead
	strip_ratio = pathway_data["Strip Ratio"]
	rho_loose = rho_bank / swell_factor
	loss = pathway_data["Loss"]
	
	init_conc = deepcopy(pathway_data["Initial Concentration"])
	rom_comp = deepcopy(pathway_data["Initial Concentration"])
	if not pathway_data["ROM feed"]: # If the reported grade is not the grade at ROM, need to dilute
		rom_comp["Li"] = rom_comp["Li"] * (1 - dilution) # Apply dilution to initial composition - may need to apply to other minerals as well, or increase their makeup
	else: # ROM is reported grade
		init_conc["Li"] = rom_comp["Li"] / (1 - dilution) # Back-calculate ore grade based on dilution 

	# No-blasting scenario
	if pathway_data["Powder Factor"] in ["","-",None]: 
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
		blasting.set_reagents("explosives",{'targets': {"rock_blast_throughput": {'ratio': pathway_data["Powder Factor"], 'elim': 0.0}}})
		
	# Get conversion factor from physical volume moved to tonnes diluted ore 
	loading.set_conversion_factor("rom_ore_feed",1-loss,field="yield_rate")
	loading.set_conversion_factor("rom_ore_feed",1/((1+strip_ratio)*rho_loose)) # get from ore --> total moved (ore + waste) in m^3
	loading.set_conversion_factor("rom_ore_feed",loading.step_ccf * rho_loose,field="ccf") # Adjust CCF as well as we need to go from tonnes to m^3 
	loading.set_conversion_factor("waste", (strip_ratio + loss)/(1+strip_ratio)) # (calculate waste = strip ratio + loss)

	# Adjust input conversion factors to crushing to account for loose ore density 
	crushing = material_refining.steps["crushing"]
	loop_factor = crushing.primary_inputs["rom_ore_feed"]["conversion_factor"]
	ipcf = rho_loose * loop_factor
	crushing.set_conversion_factor("rom_ore_feed", ipcf)
	crushing.set_conversion_factor("rom_ore_feed", ipcf * crushing.step_ccf, field="ccf")

	# Update initial and final chemical compositions for each subsequent facility module
	if pathway_data["Type"] == "Clays":
		# Set concentrations and grade-dependent calculations at seams 
		RHO_GRAIN = pathway_data["Grain Density"]

		# Circuit A: Attrition scrubbing, classifier, thickening
		classifier = material_refining.steps[pathway_data["Intermediate Concentration Target Step-Before"]]
		classified = classifier.volume_defining_output
		grade_ratio = rom_comp["Li"] / pathway_data["Intermediate Concentration"]["Li"]
		recycle_retention = classifier.primary_outputs[classified]["conversion_factor"] * classifier.primary_outputs[classified]["ccf"] / classifier.step_ccf
		classifier.set_conversion_factor(classified, classifier.primary_outputs[classified]["conversion_factor"] * grade_ratio) # Be careful here - a second call on the the sc object would do the same multiplication twice
		reject = next(iter(classifier.secondary_outputs))
		S_STACK = sink_s_out(sc, classifier.secondary_outputs[reject]["sink"])
		mass_yield = classifier.primary_outputs[classified]["yield_rate"] * grade_ratio
		classifier.set_conversion_factor(reject, (1 - mass_yield) * recycle_retention)
		classifier.set_constituents(reject, {"Li": rom_comp["Li"] * (1 - classifier.primary_outputs[classified]["yield_rate"]) / (1 - mass_yield)})
		thickener = material_refining.steps["thickening"]
		thickened = thickener.volume_defining_output
		fwd_vol = classifier.primary_outputs[classified]["yield_rate"] * classifier.primary_outputs[classified]["conversion_factor"]
		thick_vol = fwd_vol * thickener.primary_outputs[thickened]["yield_rate"] * thickener.primary_outputs[thickened]["conversion_factor"]
		reject_vol = classifier.secondary_outputs[reject]["conversion_factor"]
		reject_solids = reject_vol * classifier.step_ccf * 10**3
		makeup = thick_vol * (1 - thickener.primary_outputs[thickened]["ccf"] * 10**3 / RHO_GRAIN) \
			+ reject_solids * (1 - S_STACK) / S_STACK
		classifier.set_reagents("process_water", {"targets": {classifier.step_basis: {"ratio": makeup, "elim": 0.0}}})
		dilution = fwd_vol + reject_vol + (1 - recycle_retention) - 1.0
		classifier.set_reagents("recycled_process_water", {"targets": {classifier.step_basis: {"ratio": dilution - makeup, "elim": 0.0}}})

		# Circuit B: Acid leaching, Neutralization, CCD, Impurity Removal

		material_refining.add_target_comp(target = "rom_ore_feed", composition = rom_comp, 
											target_step_id = pathway_data["Initial Concentration Target Step"], propagate = True)
		material_refining.add_target_comp(target = "classified_slurry", composition = pathway_data["Intermediate Concentration"], 
											target_step_id = pathway_data["Intermediate Concentration Target Step-Before"], propagate = False) 
		material_refining.add_target_comp(target = "classified_slurry", composition = pathway_data["Intermediate Concentration"],
											target_step_id = pathway_data["Intermediate Concentration Target Step-After"], propagate = True)
		material_refining.add_target_comp(target = "washed_pregnant_leach_solution", composition = pathway_data["Second Intermediate Concentration"],
											target_step_id = pathway_data["Second Intermediate Concentration Target Step-Before"], propagate = False)
		material_refining.add_target_comp(target = "washed_pregnant_leach_solution", composition = pathway_data["Second Intermediate Concentration"],
											target_step_id = pathway_data["Second Intermediate Concentration Target Step-After"], propagate = True)

		# Set input lithium extraction constituents based on final constituents in material refining
		pls_post_polishing = next(iter(material_refining.fwd[-1].primary_outputs.values()))
		lithium_extraction.add_target_comp(target = "pls_post_polishing", composition = pls_post_polishing["constituents"],
											target_step_id = "precipitation_step", propagate = True)

		# Jank workaround to custom-set CCFs for solution processing because they are different between Clay & Lepidolite
		precip_step = lithium_extraction.fwd[0]
		ccf = material_refining.steps["impurity_removal"].primary_outputs["pls_post_polishing"]["ccf"] / 10**3 # Need to convert from per m^3
		precip_step.set_conversion_factor("pls_post_polishing",ccf,field="ccf")
		precip_step.set_conversion_factor("step_basis",ccf,field="ccf")
		if pathway_data.get("Carbonate Recovery Factor") not in (None, "-"):
			precip_step.set_conversion_factor("lithium_slurry", pathway_data["Carbonate Recovery Factor"], field="yield_rate")
		# Set conversion factor for mother liquor
		slurry = precip_step.primary_outputs["lithium_slurry"]
		ml_conv = 1/1000 - slurry["yield_rate"] * pls_post_polishing["constituents"]["Li"] * ccf / (slurry["constituents"]["Li"] * slurry["ccf"]) # 1/1000 is because the other units are in 1/PPM • m^3/L already
		precip_step.set_conversion_factor("mother_liquor", ml_conv, field="conversion_factor")

	elif pathway_data["Type"] == "Lepidolite":
		material_refining.add_target_comp(target = "rom_ore_feed", composition = rom_comp, 
											target_step_id = pathway_data["Initial Concentration Target Step"], propagate = True)
		material_refining.add_target_comp(target = "flotation_froth", composition = pathway_data["Intermediate Concentration"], 
											target_step_id = pathway_data["Intermediate Concentration Target Step-Before"], propagate = False) 
		material_refining.add_target_comp(target = "flotation_froth", composition = pathway_data["Intermediate Concentration"], 
											target_step_id = pathway_data["Intermediate Concentration Target Step-After"], propagate = True) 
		# Some bug is causing the water leach step to not be working for some reason, so fixing it here
		material_refining.add_target_comp(target = "roasted_mix", composition = pathway_data["Intermediate Concentration"], 
											target_step_id = "water_leach", propagate = True) 
		material_refining.add_target_comp(target = "pregnant_leach_solution", composition = pathway_data["Second Intermediate Concentration"],
											target_step_id = "water_leach", propagate = True)
		material_refining.add_target_comp(target = "pregnant_leach_solution", composition = pathway_data["Second Intermediate Concentration"],
											target_step_id = pathway_data["Second Intermediate Concentration Target Step-After"], propagate = True)
		# Temporary hold - need third constituent definition for some buggy reason
		lithium_extraction.add_target_comp(target = "pls_post_polishing", composition = pathway_data["Second Intermediate Concentration"],
											target_step_id = "precipitation_step", propagate = True)

		# Beneficiation circuit: classifying -> flotation -> thickening -> grinding -> dewatering
		RHO_GRAIN = pathway_data["Grain Density"]

		classifier = material_refining.steps["classifying"]
		flotation = material_refining.steps["flotation"]
		thickener = material_refining.steps["thickening"]
		mill = material_refining.steps["grinding"]
		press = material_refining.steps["dewatering"]

		cl_out = next(iter(classifier.primary_outputs.values()))
		th_out = next(iter(thickener.primary_outputs.values()))
		gr_out = next(iter(mill.primary_outputs.values()))
		pr_out = next(iter(press.primary_outputs.values()))
		slimes = classifier.secondary_outputs["classification_slimes"]
		tails = flotation.secondary_outputs["flotation_tailings"]
		filtrate = press.secondary_outputs["press_filtrate"]

		solids = classifier.step_ccf * 10**3
		fwd_vol = cl_out["yield_rate"] * cl_out["conversion_factor"]
		conc_vol = fwd_vol * (1 - tails["conversion_factor"])
		grind_fwd = gr_out["yield_rate"] * gr_out["conversion_factor"]
		press_vol = conc_vol * th_out["yield_rate"] * th_out["conversion_factor"] * grind_fwd
		w_cake = pr_out["ccf"] * 10**3

		s_slimes = sink_s_out(sc, slimes["sink"])
		s_tails = sink_s_out(sc, tails["sink"])
		impounded = solids * (slimes["conversion_factor"] * (1 - s_slimes) / s_slimes + tails["conversion_factor"] * fwd_vol * (1 - s_tails) / s_tails)
		cake_water = conc_vol * solids * grind_fwd * (1 - w_cake) / w_cake
		bleed = filtrate["conversion_factor"] * press_vol
		mill_loss = mill.secondary_outputs["mill_discharge"]["conversion_factor"] * conc_vol * th_out["yield_rate"] * th_out["conversion_factor"] * (1 - th_out["ccf"] * 10**3 / RHO_GRAIN)

		gross = classifier.secondary_inputs["process_water"]["targets"][classifier.step_basis]["ratio"]
		makeup = impounded + cake_water + bleed + mill_loss
		classifier.set_reagents("process_water", {"targets": {classifier.step_basis: {"ratio": makeup, "elim": 0.0}}})
		classifier.set_reagents("recycled_process_water", {"targets": {classifier.step_basis: {"ratio": gross - makeup, "elim": 0.0}}})

		# Jank workaround to custom-set CCFs for solution processing because they are different between Clay & Lepidolite
		precip_step = lithium_extraction.fwd[0]
		ccf = material_refining.steps["stream_clarification"].primary_outputs["pls_post_polishing"]["ccf"]
		precip_step.set_conversion_factor("pls_post_polishing",ccf,field="ccf")
		precip_step.set_conversion_factor("step_basis",ccf,field="ccf")

		if pathway_data.get("Carbonate Recovery Factor") not in (None, "-"):
			precip_step.set_conversion_factor("lithium_slurry", pathway_data["Carbonate Recovery Factor"], field="yield_rate")
		# Set conversion factor for mother liquor; liquor carries unrecovered Li and Na2SO4, so it is a discharge, not a recycle
		slurry = precip_step.primary_outputs["lithium_slurry"]
		ml_conv = 1/1000 - slurry["yield_rate"] * pathway_data["Second Intermediate Concentration"]["Li"] * ccf / (slurry["constituents"]["Li"] * slurry["ccf"])
		precip_step.set_conversion_factor("mother_liquor", ml_conv, field="conversion_factor")
		
	products = {"rom_ore_feed": 1}
	sc.add_facility(material_extraction, next_fac=material_refining, products=products, transport_route=ore_truck_route)	

	fac_by_sheet = {
		pathway_data["Facility 1"]: material_extraction,
		pathway_data["Facility 2"]: material_refining,
		pathway_data["Facility 3"]: lithium_extraction,
	}
	for reagent, spec in (pathway_data.get("reagent_plant") or {}).items():
		if not spec.get("sheet"):
			continue
		targets = [fac_by_sheet[s] for s in helpers.ensure_list(spec["facilities"])]
		plant = ReagentFacility(fac_id=spec['sheet'], supply_chain=sc,
								sinks = sc.sink_names,
								location=spec["location"], target_reagent=reagent,
								target_facilities=targets,
								steps=helpers.build_facility_dict(data_folder, spec["sheet"]))
		sc.add_facility(plant)

	return sc 

def evaluate_pathway(sc,pathway_data,data_folder,detail=1,plot=1,sink_overrides=None):
	summary = {}
	load_sink_params(sc, data_folder)

	pathway_type = pathway_data["Type"]
	if pathway_type == "Brine-Evaporative":
		sc = lithium_evaporation(sc,pathway_data,data_folder)
		tailings_handling(sc)
	elif pathway_type == "Brine-DLE":
		pass 
	elif pathway_type == "Spodumene":
		pass
	elif pathway_type in ["Clays","Lepidolite"]:
		sc = clay_lepidolite(sc,pathway_data,data_folder)
		tailings_handling(sc)
	else:
		raise ValueError(f"Pathway type '{pathway_type}' not defined.")

	overrides = sink_override_map(pathway_data.get("sink_override"))
	overrides.update(sink_overrides or {})
	apply_sink_overrides(sc,overrides)

	# for target_pv in target_pvs:
	target_pv = pathway_data["Production Volume"] # convert to kg
	helpers.update_materials(sc,pathway_data,"midpoint")
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

			print("\nStep-level OPEX & CO2 (per tonne):")
			_apv = sc.apv
			_imp_map = {r["step_name"]: r for r in sc.get_step_impacts(transp=True)}
			for _rec in sc.get_step_cost_report(view="opex", transp=True, detail=2):
				# detail=2 returns lists for transport and OrderedDicts for production/sinks
				if isinstance(_rec, list):
					_sname, _opex = _rec[0], _rec[1]
				else:
					_sname = _rec.get("step_name")
					_opex  = float(_rec.get("total_cost") or sum(
						_rec.get(k, 0.0) or 0.0 for k in
						("material_costs","labor_costs","utility_costs","opex_fixed_like")))
				_r = _imp_map.get(_sname, {})
				_co2 = sum(float((_r.get(sk) or {}).get("co2", 0.0) or 0.0) for sk in ("scope_one","scope_two","scope_three"))
				print(f"  {_sname}: opex=${_opex/_apv:,.1f}/t  co2={_co2/_apv:,.2f} kg/t")

		if detail == 2.5:	
			wk_compare(sc,pathway_type) # Output comparison metrics vs Wesselkamper et al. 2025

		if detail > 3:
			print(sc.get_step_reagent_usage())
			pprint(sc.get_step_utilities_detailed())
	else:
		if detail == "tp_debug":
			tp_debug(sc,summary_midpoint)
	
	if plot == 1:
		# sc.plot_step_costs(mode="average",view="opex",detail=3,cost_colors=COST_SERIES_COLORS)
		sc.plot_step_costs(mode="average",view="opex",detail=2,cost_colors=COST_SERIES_COLORS)
		sc.plot_step_impacts(mode="average",imp_colors=SCOPE_COLORS)
		# sc.plot_step_costs(view="variable",detail=3,cost_colors=COST_SERIES_COLORS)
		# sc.plot_step_costs(view="variable",detail=2,cost_colors=COST_SERIES_COLORS)
		# sc.plot_tot_steps_impacts()
		# sc.plot_total_cc()

	helpers.update_machines(sc,"conservative")
	helpers.update_materials(sc,pathway_data,"conservative")
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
	helpers.update_materials(sc,pathway_data,"optimistic")
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

def wk_compare(sc,pw): # Outputs metrics for comparison against Wesselkamper et al. 2025
	step_costs = sc.get_step_costs(transp=True,detail=3)
	apv = sc.apv
	mine_opex = 0
	mine_capex = 0
	proc_reag = 0
	proc_pow = 0
	proc_other = 0
	proc_capex = 0
	if pw == "Brine-Evaporative":
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
	if pw == "Clays":
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
	if pw == "Lepidolite":
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
	Call with detail=5 in evaluate_pathway.
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
		("Lime (CaO)", lime_kg, lime_cost),
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

def compare_pathways(pathways,pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,
	write=False,
	detail=1,
	plot=1,
	ylims_cost=None,
	xticks_cost=None,
	ylims_emissions=None,
	xticks_emissions=None,
	sink_overrides=None,):
	"""
	write=False  -> do not write to CSV
	write=True   -> write full conservative/midpoint/optimistic to standard columns
	write=N (int)-> also write a top-N restricted scenario to columns suffixed '-N'
	               (e.g. 'Our Study-Low-3', 'Our Study-Midpoint-3', 'Our Study-High-3')
	"""
	pathway_summaries = {}
	topn_summaries    = {}  # populated only when write is an integer

	for pathway in pathways:
		pathway_data = pathways_data[pathway]
		sc = SupplyChain(transp_data,loc_data,machine_data,material_data)
		summary = evaluate_pathway(sc,pathway_data,data_folder,detail,plot=plot,
			sink_overrides=(sink_overrides or {}).get(pathway))
		if plot == 2:
			plot_scenario_step_costs(sc, pathway_data, pathway_data["Production Volume"],
				view="opex",	# total|variable|fixed|opex|capex  (combo not supported)
				mode="average",	# "total" | "average"
				detail=2,		# 1|2|3 — applied to midpoint bars; conservative/optimistic always use detail=1
				transp=True,
				# title=None,
				ylims=ylims_cost,
				xticks=xticks_cost,
			)
			plot_scenario_step_impacts(sc, pathway_data, pathway_data["Production Volume"],
				mode="average",         # "total" | "average"
				impact="co2",           # impact category key (e.g. "co2", "ghg")
				# title=None,
				ylims=ylims_emissions,
				xticks=xticks_emissions,
			)
		if plot == 2.1 and pathway == "Thacker Pass": # Custom Thacker Pass Aggregation
			helpers.thacker_pass_steps_aggregated(sc, pathway_data, pathway_data["Production Volume"],
				ylims_cost=ylims_cost,			 xticks_cost=xticks_cost,
				ylims_emissions=ylims_emissions, xticks_emissions=xticks_emissions,
				cost_colors=COST_SERIES_COLORS, imp_colors=SCOPE_COLORS,
			)

		if plot == 2.2 and pathway == "Jianxiawo":
			helpers.jianxiawo_steps_aggregated(sc, pathway_data, pathway_data["Production Volume"],
				ylims_cost=ylims_cost,			 xticks_cost=xticks_cost,
				ylims_emissions=ylims_emissions, xticks_emissions=xticks_emissions,
				cost_colors=COST_SERIES_COLORS, imp_colors=SCOPE_COLORS,
			)
		if plot == 3:
			tornado = run_tornado_data(sc, pathway_data, apv=pathway_data["Production Volume"])
			helpers.plot_tornado(tornado, metric="avg_opex", top_n=5, colors=TORNADO_COLORS)
			helpers.plot_tornado(tornado, metric="avg_co2",  top_n=5, colors=TORNADO_COLORS)

		pathway_summaries[pathway] = summary 
		
		# If write is an integer, run the top-N restricted scenarios now while sc is built
		if isinstance(write, int) and write > 0:
			topn_summaries[pathway] = run_topn_scenarios(
				sc, pathway_data, pathway_data["Production Volume"], top_n=write
			)

	# pprint(pathway_summaries)
	extracted_data = {}
	for key, value in pathway_summaries.items():
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
	# helpers.pathway_summaries(pathway_summaries)

	# helpers.update_machines(sc, "midpoint")
	# helpers.update_materials(sc, pathway_data, "midpoint")
	# sc.update_apv(apv, recalc=True)
	# step = sc.facilities["Concentrated Brine"].steps["batch_treatment"]
	# step = sc.facilities["Material Refining"].steps["sulfate_roasting"]
	# step = sc.facilities["Material Refining"].steps["grinding"]
	# print("step_pv:              ", step.step_pv)
	# print("ltr:                  ", step.ltr)
	# print("lta:                  ", step.lta)
	# print("machines_required:    ", step.machines_required)
	# print("electricity_consumed: ", step.electricity_consumed)
	# print("electricity_base:     ", step.electricity_base_total)
	# print("batch_cycle+setup:    ", step.batch_cycle_time, "+", step.batch_setup_time)
	# print("base_volume:          ", step.base_volume)
	# print("dedicated_line:       ", step.dedicated_line)

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
		pathway_outputs_to_csv(extracted_data, both_csv_path)
		# Write top-N outputs to suffixed columns
		if isinstance(write, int) and write > 0:
			pathway_outputs_to_csv(topn_summaries, both_csv_path, col_suffix=f"-{write}")

	return extracted_data

def pathway_outputs_to_csv(extracted_data, both_csv_path, col_suffix=""):
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
	
	df = pd.read_csv(both_csv_path).astype(object)

	# Create any missing columns so loc assignment doesn't fail
	for col in scen_to_col.values():
		if col not in df.columns:
			df[col] = None
 
	for pathway, scens in extracted_data.items():
		pathway_mask = df["Pathway"].astype(str) == str(pathway)
		if not pathway_mask.any():
			continue
 
		cost_mask  = pathway_mask & (df["Dimension"] == "Cost")
		emiss_mask = pathway_mask & (df["Dimension"] == "Emissions")
 
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

def plot_scenario_step_costs(sc, pathway_data, apv, *,
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
 
	The sc object must already have its facilities built (e.g. after evaluate_pathway or
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
	helpers.update_materials(sc, pathway_data, "conservative")
	sc.update_apv(apv, recalc=True)
	con_labels, con_series, _ = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	con_totals = _get_totals(con_labels, con_series)
 
	# ---- Optimistic ----
	helpers.update_machines(sc, "optimistic")
	helpers.update_materials(sc, pathway_data, "optimistic")
	sc.update_apv(apv, recalc=True)
	opt_labels, opt_series, _ = sc._build_steps_cost_series(view=view, detail=detail, transp=transp, top_n=None)
	opt_totals = _get_totals(opt_labels, opt_series)

	# ---- Midpoint ----
	helpers.update_machines(sc, "midpoint")
	helpers.update_materials(sc, pathway_data, "midpoint")
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
		colors=helpers.cost_series_colors(mid_series, COST_SERIES_COLORS),
		xscale=xscale, yscale=yscale,
		title=title, xlab=xlab, ylab=ylab,
		wrap_width=wrap_width,
		err_low=err_low,
		err_high=err_high,
		xticks=xticks,
		ylims=ylims
	)

def plot_scenario_step_impacts(sc, pathway_data, apv, *,
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
	helpers.update_materials(sc, pathway_data, "conservative")
	sc.update_apv(apv, recalc=True)
	con_labels, con_scopes, _ = sc._build_steps_impact_series(impact=impact, transp=transp)
	con_totals = _get_totals(con_scopes)
 
	# ---- Optimistic ----
	helpers.update_machines(sc, "optimistic")
	helpers.update_materials(sc, pathway_data, "optimistic")
	sc.update_apv(apv, recalc=True)
	opt_labels, opt_scopes, _ = sc._build_steps_impact_series(impact=impact, transp=transp)
	opt_totals = _get_totals(opt_scopes)
 
	# ---- Midpoint ----
	helpers.update_machines(sc, "midpoint")
	helpers.update_materials(sc, pathway_data, "midpoint")
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
 
	colors = SCOPE_COLORS
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

def run_tornado_data(sc, pathway_data, apv):
	def _record(summary):
		return {
			"avg_opex":     summary.get("avg_opex",     0.0),
			"avg_var_cost": summary.get("avg_var_cost", 0.0),
			"avg_co2":      summary.get("avg_co2",      0.0),
		}

	def _reset_to_midpoint():
		helpers.update_machines(sc, "midpoint")
		helpers.update_materials(sc, pathway_data, "midpoint")

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
	mat_costs   = pathway_data.get("material_cost",   {}) or {}
	mat_impacts = pathway_data.get("material_impact", {}) or {}
	all_materials = set(mat_costs.keys()) | set(mat_impacts.keys())

	for material in sorted(all_materials):
		results["materials"][material] = {}
		single_pw = {
			"material_cost":   {material: mat_costs.get(material, {})},
			"material_impact": {material: mat_impacts.get(material, {})},
		}
		for rank in ("conservative", "optimistic"):
			_reset_to_midpoint()
			helpers.update_materials(sc, single_pw, rank)
			results["materials"][material][rank] = _record(sc.update_apv(apv, recalc=True))

	# Restore to midpoint
	_reset_to_midpoint()
	sc.update_apv(apv, recalc=True)

	return results

def run_topn_scenarios(sc, pathway_data, apv, top_n, metric="avg_opex"):
	"""
	Re-run conservative/midpoint/optimistic scenarios varying only the top_n most
	impactful machines and materials (ranked by |conservative - optimistic| range
	on `metric`).  Everything else is held at midpoint.
 
	Internally calls run_tornado_data to establish the ranking, then runs three
	targeted scenario passes.  sc is restored to midpoint after the call.
 
	Returns a dict with the same structure as evaluate_pathway:
	{
	    "conservative": {"apv": ..., "avg_opex": ..., "avg_var_cost": ..., "avg_co2": ...},
	    "midpoint":     {...},
	    "optimistic":   {...},
	}
	"""
	# Step 1: get tornado ranking
	tornado = run_tornado_data(sc, pathway_data, apv)
 
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
 
	# Build a pathway_data slice covering only the top materials
	mat_costs   = pathway_data.get("material_cost",   {}) or {}
	mat_impacts = pathway_data.get("material_impact", {}) or {}
	top_pw = {
		"material_cost":   {m: mat_costs.get(m,   {}) for m in top_materials},
		"material_impact": {m: mat_impacts.get(m, {}) for m in top_materials},
	}
 
	# Step 3: run three scenario passes
	summary = {}
	for rank in ("conservative", "midpoint", "optimistic"):
		# Always start from a clean midpoint
		helpers.update_machines(sc, "midpoint")
		helpers.update_materials(sc, pathway_data, "midpoint")
		# Then apply only the top-N variables at the current rank
		if top_machines:
			helpers.update_machines(sc, {base: rank for base in top_machines})
		if top_materials:
			helpers.update_materials(sc, top_pw, rank)
		result = sc.update_apv(apv, recalc=True)
		summary[rank] = {
			"apv":          result["apv"],
			"avg_opex":     result["avg_opex"],
			"avg_var_cost": result["avg_var_cost"],
			"avg_co2":      result.get("avg_co2", 0.0) / 1000,  # kg -> t to match extracted_data convention
		}
 
	# Restore to midpoint
	helpers.update_machines(sc, "midpoint")
	helpers.update_materials(sc, pathway_data, "midpoint")
	sc.update_apv(apv, recalc=True)
 
	return summary

def _value_axis_extent(ax):
	import numpy as np
	hi = float(ax.dataLim.intervalx[1])
	for coll in ax.collections:
		get_segs = getattr(coll,"get_segments",None)
		if get_segs is None:
			continue
		for seg in get_segs():
			seg = np.asarray(seg,dtype=float)
			if seg.size:
				hi = max(hi,float(np.max(seg[:,0])))
	return hi, float(ax.get_xlim()[1])

def _save_open_figures(paths):
	import matplotlib.pyplot as plt
	nums = plt.get_fignums()
	if len(nums) != len(paths):
		raise RuntimeError(f"open figures {len(nums)} != expected {len(paths)}: {[os.path.basename(p) for p in paths]}")
	for num,path in zip(nums,paths):
		fig = plt.figure(num)
		os.makedirs(os.path.dirname(path),exist_ok=True)
		for ax in fig.get_axes():
			data_hi,axis_hi = _value_axis_extent(ax)
			if data_hi > axis_hi*(1+1e-9):
				print(f"CLIP  {os.path.basename(path)}: data extent {data_hi:,.4f} exceeds axis limit {axis_hi:,.4f}")
		fig.savefig(path,dpi=300,bbox_inches="tight")
	plt.close("all")

def _step_summary_figures(pathway,sc,pathway_data,apv,axes,fig_dir,suffix):
	plot_scenario_step_costs(sc,pathway_data,apv,view="opex",mode="average",detail=2,transp=True,
		ylims=axes["ylims_cost"],xticks=axes["xticks_cost"])
	plot_scenario_step_impacts(sc,pathway_data,apv,mode="average",impact="co2",
		ylims=axes["ylims_emissions"],xticks=axes["xticks_emissions"])
	_save_open_figures([
		os.path.join(fig_dir,f"04-{pathway}-Steps-Cost{suffix}.png"),
		os.path.join(fig_dir,f"04-{pathway}-Steps-Emissions{suffix}.png"),
	])

def run_all(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,
	fig_dir,
	cost_emissions_dir,
	norm_axes,
	pathways=("Silver Peak","Thacker Pass","Jianxiawo"),
	detail=4,
	axes_mode="both",
	top_n_range=3,
	top_n_tornado=5,
	write_csv=True,
	):

	blank_axes = {k: None for k in norm_axes}
	if axes_mode == "normalized":
		axis_passes = [(norm_axes,"")]
	elif axes_mode == "auto":
		axis_passes = [(blank_axes,"")]
	elif axes_mode == "both":
		axis_passes = [(norm_axes,""),(blank_axes,"-Auto")]
	else:
		raise ValueError("axes_mode must be 'normalized', 'auto' or 'both'")

	prev_backend = matplotlib.get_backend()
	plt.switch_backend("Agg")
	try:
		extracted_data = {}
		topn_summaries = {}

		for pathway in pathways:
			pathway_data = pathways_data[pathway]
			apv = pathway_data["Production Volume"]
			print(f"\n{'='*72}\n{pathway}\n{'='*72}")

			sc = SupplyChain(transp_data,loc_data,machine_data,material_data)
			summary = evaluate_pathway(sc,pathway_data,data_folder,detail=detail,plot=0)
			extracted_data[pathway] = {
				scen: {
					"apv":          vals["apv"],
					"avg_opex":     vals["avg_opex"],
					"avg_var_cost": vals["avg_var_cost"],
					"avg_co2":      vals["avg_co2"]/1000,
				}
				for scen,vals in summary.items()
			}

			for axes,suffix in axis_passes:
				_step_summary_figures(pathway,sc,pathway_data,apv,axes,fig_dir,suffix)

			tornado = run_tornado_data(sc,pathway_data,apv)
			helpers.plot_tornado(tornado,metric="avg_opex",top_n=top_n_tornado,colors=TORNADO_COLORS)
			helpers.plot_tornado(tornado,metric="avg_co2",top_n=top_n_tornado,colors=TORNADO_COLORS)
			_save_open_figures([
				os.path.join(fig_dir,f"04-{pathway}-Sensitivity-Cost.png"),
				os.path.join(fig_dir,f"04-{pathway}-Sensitivity-Emissions.png"),
			])
			print("\nTornado ranges:")
			for kind in ("machines","materials"):
				for name,vals in sorted(tornado.get(kind,{}).items()):
					for metric in ("avg_opex","avg_co2"):
						spread = abs(vals["conservative"][metric]-vals["optimistic"][metric])
						print(f"  {kind[:-1]}  {name}  {metric}  {spread:,.4f}")

			topn_cost = run_topn_scenarios(sc,pathway_data,apv,top_n=top_n_range,metric="avg_opex")
			topn_co2  = run_topn_scenarios(sc,pathway_data,apv,top_n=top_n_range,metric="avg_co2")
			topn_summaries[pathway] = {
				scen: {
					"apv":          topn_cost[scen]["apv"],
					"avg_opex":     topn_cost[scen]["avg_opex"],
					"avg_var_cost": topn_cost[scen]["avg_var_cost"],
					"avg_co2":      topn_co2[scen]["avg_co2"],
				}
				for scen in topn_cost
			}

		print(f"\n{'='*72}\nHeadline metrics (avg_opex $/t, avg_co2 t/t)\n{'='*72}")
		pprint(extracted_data)
		print(f"\nTop-{top_n_range} restricted ranges")
		pprint(topn_summaries)

		if "Jianxiawo" in pathways:
			jx_data = pathways_data["Jianxiawo"]
			jx_apv = jx_data["Production Volume"]
			sc_nc = SupplyChain(transp_data,loc_data,machine_data,material_data)
			evaluate_pathway(sc_nc,jx_data,data_folder,detail=0,plot=0,
				sink_overrides=sink_override_map(jx_data.get("noncompliance_sink_override")))
			helpers.update_machines(sc_nc,"midpoint")
			helpers.update_materials(sc_nc,jx_data,"midpoint")
			nc_summary = sc_nc.update_apv(jx_apv,recalc=True)
			nc_labels,nc_series,_ = sc_nc._build_steps_cost_series(view="opex",detail=2,transp=True,top_n=None)
			base_opex = extracted_data["Jianxiawo"]["midpoint"]["avg_opex"]
			print(f"\n{'='*72}\nJianxiawo hazardous-waste non-compliance, midpoint\n{'='*72}")
			print(f"avg_opex {nc_summary['avg_opex']:,.6f}   avg_co2 {nc_summary['avg_co2']/1000:,.6f}")
			print(f"delta vs compliant {nc_summary['avg_opex']-base_opex:,.6f} $/t")
			for i,label in enumerate(nc_labels):
				print(f"  {label}: ${sum(vals[i] for vals in nc_series.values())/jx_apv:,.4f}/t")

		if "Thacker Pass" in pathways:
			tp_data = deepcopy(pathways_data["Thacker Pass"])
			tp_apv = tp_data["Production Volume"]
			tp_sulfur_shock = tp_data["material_cost"]["sulfur"]["shock"]
			tp_data["material_cost"]["sulfur"]["midpoint"] = tp_sulfur_shock
			sc_sx = SupplyChain(transp_data,loc_data,machine_data,material_data)
			evaluate_pathway(sc_sx,tp_data,data_folder,detail=0,plot=0)
			helpers.update_machines(sc_sx,"midpoint")
			helpers.update_materials(sc_sx,tp_data,"midpoint")
			sx_summary = sc_sx.update_apv(tp_apv,recalc=True)
			sx_labels,sx_series,_ = sc_sx._build_steps_cost_series(view="opex",detail=2,transp=True,top_n=None)
			base_opex = extracted_data["Thacker Pass"]["midpoint"]["avg_opex"]
			print(f"\n{'='*72}\nThacker Pass sulfur supply shock at ${tp_sulfur_shock:,.3f}/kg, midpoint basis\n{'='*72}")
			print(f"avg_opex {sx_summary['avg_opex']:,.6f}   avg_co2 {sx_summary['avg_co2']/1000:,.6f}")
			print(f"delta vs midpoint {sx_summary['avg_opex']-base_opex:,.6f} $/t")
			for i,label in enumerate(sx_labels):
				print(f"  {label}: ${sum(vals[i] for vals in sx_series.values())/tp_apv:,.4f}/t")

		if write_csv:
			both_csv_path = os.path.join(cost_emissions_dir,"reported_both.csv")
			pathway_outputs_to_csv(extracted_data,both_csv_path)
			pathway_outputs_to_csv(topn_summaries,both_csv_path,col_suffix=f"-{top_n_range}")

		return extracted_data,topn_summaries
	finally:
		plt.switch_backend(prev_backend)

def _slot_name(pathway_data, slot):
	return pathway_data[slot] if slot in SLOT_KEYS else slot

def _facility_index(sc, pathway_data, labels):
	nodes = sc.get_steps(transp=True)
	groups = []
	for i, node in enumerate(nodes):
		if isinstance(node, Transportation):
			name, grp = node.name, pathway_data["Facility 1"]
		else:
			fac_id = node.facility.fac_id
			name, grp = node.step_name, _slot_name(pathway_data, FAC_SLOTS.get(fac_id, fac_id))
		got = labels[i] if i < len(labels) else None
		if got != name:
			raise ValueError(f"Label {i}: expected '{name}', got '{got}'")
		groups.append(grp)
	for lbl in labels[len(nodes):]:
		if lbl not in SINK_SLOTS:
			raise ValueError(f"Unmapped sink label '{lbl}'")
		groups.append(_slot_name(pathway_data, SINK_SLOTS[lbl]))
	head = [pathway_data[k] for k in SLOT_KEYS if pathway_data.get(k)]
	tail = [g for g in dict.fromkeys(groups) if g not in head and g != WASTE_GROUP]
	order = [g for g in head + tail + [WASTE_GROUP] if g in groups]
	return groups, order

def _aggregate_by_facility(groups, order, series):
	import numpy as np
	pos = {g: i for i, g in enumerate(order)}
	out = {k: np.zeros(len(order)) for k in series}
	for k, vals in series.items():
		for g, v in zip(groups, vals):
			out[k][pos[g]] += float(v)
	return out

def facility_panel_data(sc, pathway_data, apv, *, view="opex", impact="co2", co2_scale=1.0, fold_transport=False):
	import numpy as np
	runs = {}
	for rank in ("conservative", "optimistic", "midpoint"):
		helpers.update_machines(sc, rank)
		helpers.update_materials(sc, pathway_data, rank)
		sc.update_apv(apv, recalc=True)
		runs[rank] = {
			"cost": sc._build_steps_cost_series(view=view, detail=2, transp=True, top_n=None),
			"co2":  sc._build_steps_impact_series(impact=impact, transp=True),
		}
	out = {}
	for kind, scale in (("cost", 1.0), ("co2", co2_scale)):
		mid_labels, _, mid_stack = runs["midpoint"][kind]
		for rank in ("conservative", "optimistic"):
			if runs[rank][kind][0] != mid_labels:
				raise ValueError(f"{kind}: step label mismatch between {rank} and midpoint")
		groups, order = _facility_index(sc, pathway_data, mid_labels)
		agg = {rank: _aggregate_by_facility(groups, order, runs[rank][kind][1]) for rank in runs}
		if kind == "cost" and fold_transport:
			for rank in agg:
				if "Transport" in agg[rank]:
					agg[rank]["Other"] = agg[rank].get("Other", 0.0) + agg[rank].pop("Transport")
		tot = {rank: sum(agg[rank].values()) for rank in agg}
		div = float(apv) / scale
		series = {k: v / div for k, v in agg["midpoint"].items()}
		out[kind] = {
			"labels":   order,
			"series":   series,
			"stack":    [k for k in mid_stack if k in series and np.any(series[k] != 0.0)],
			"err_low":  np.maximum(tot["midpoint"] - tot["optimistic"], 0.0) / div,
			"err_high": np.maximum(tot["conservative"] - tot["midpoint"], 0.0) / div,
		}
	return out

def tornado_entries(tornado, metric, top_n):
	entries = []
	for kind, prefix in (("machines", "Machine"), ("materials", "Material")):
		for name, vals in tornado.get(kind, {}).items():
			entries.append((f"{prefix}: {name}", vals["optimistic"][metric], vals["conservative"][metric]))
	entries.sort(key=lambda e: abs(e[2] - e[1]), reverse=True)
	return entries[:top_n]

def _bar_extent(d):
	import numpy as np
	vals = np.array(list(d["series"].values()))
	net = vals.sum(axis=0)
	hi = max(np.maximum(vals, 0.0).sum(axis=0).max(), (net + d["err_high"]).max())
	lo = min(0.0, (net - d["err_low"]).min())
	return lo, hi

def _pad(lo, hi, margin):
	span = hi - lo
	return (float(lo - span * margin if lo != 0 else lo), float(hi + span * margin))

def _finish_panel(fig, ax, width, row_height, rect, n_rows, ticklabels, path, dpi, fontsize):
	l, b, r, t = rect
	h = b + t + n_rows * row_height
	fig.set_size_inches(width, h)
	ax.set_position([l / width, b / h, 1 - (l + r) / width, 1 - (b + t) / h])
	ax.set_ylim(n_rows - 0.5, -0.5)
	ax.set_title("")
	ax.set_xlabel("")
	ax.set_ylabel("")
	ax.tick_params(axis="x", labelsize=fontsize)
	if not ticklabels:
		ax.set_yticklabels([])
	os.makedirs(os.path.dirname(path), exist_ok=True)
	fig.savefig(path, dpi=dpi, transparent=True)
	plt.close(fig)

def _plot_tornado_panel(entries, baseline, xlim, width, row_height, rect, ticklabels, path, dpi, scale, fontsize):
	fig, ax = plt.subplots(figsize=(width, 1.0))
	fig.patch.set_facecolor("none")
	ax.set_facecolor("none")
	y = np.arange(len(entries))
	b = baseline * scale
	opt = np.array([e[1] for e in entries]) * scale
	con = np.array([e[2] for e in entries]) * scale
	ax.barh(y, con - b, left=b, color=TORNADO_COLORS["conservative"], zorder=3)
	ax.barh(y, opt - b, left=b, color=TORNADO_COLORS["optimistic"], zorder=3)
	ax.axvline(b, color="black", linewidth=1.0, zorder=4)
	ax.set_yticks(y)
	ax.set_yticklabels([e[0] for e in entries], fontsize=fontsize)
	ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
	ax.set_xlim(xlim)
	_finish_panel(fig, ax, width, row_height, rect, len(entries), ticklabels, path, dpi, fontsize)

# def _check_row_overlap(rows, pathways, metric):
# 	for k, row in enumerate(rows):
# 		spans = sorted((min(b, o, c), max(b, o, c), p) for p, (b, o, c, _) in row.items())
# 		for (lo1, hi1, p1), (lo2, hi2, p2) in zip(spans, spans[1:]):
# 			if lo2 <= hi1:
# 				raise ValueError(f"{metric} rank {k + 1}: {p1} bar ({lo1:,.1f}-{hi1:,.1f}) overlaps {p2} bar ({lo2:,.1f}-{hi2:,.1f})")
 
# def _plot_combined_tornado(torn, bands, pathways, metric, scale, *, colors, styles, show_band, band_alpha,
# 	check_overlap, xlim, xticks, margin, width, row_height, rect, path, dpi, fontsize):
# 	n_rows = max(len(torn[p][metric][1]) for p in pathways)
# 	rows = [{} for _ in range(n_rows)]
# 	for p in pathways:
# 		b, entries = torn[p][metric]
# 		for k, (name, opt, con) in enumerate(entries):
# 			rows[k][p] = (b * scale, opt * scale, con * scale, name)
# 	if check_overlap:
# 		_check_row_overlap(rows, pathways, metric)
 
# 	pts = [v for row in rows for (b, o, c, _) in row.values() for v in (b, o, c)]
# 	if show_band:
# 		pts += [v * scale for p in pathways for v in bands[p][metric]]
# 	lim = tuple(xlim) if xlim is not None else _pad(min(pts), max(pts), margin)
 
# 	fig, ax = plt.subplots(figsize=(width, 1.0))
# 	fig.patch.set_facecolor("none")
# 	ax.set_facecolor("none")
# 	for p in pathways:
# 		clr = colors.get(p, "gray")
# 		b = torn[p][metric][0] * scale
# 		if show_band:
# 			lo, hi = (v * scale for v in bands[p][metric])
# 			ax.axvspan(min(lo, hi), max(lo, hi), color=clr, alpha=band_alpha, linewidth=0, zorder=1)
# 		for k, row in enumerate(rows):
# 			if p not in row:
# 				continue
# 			_, opt, con, _ = row[p]
# 			ax.barh(k, con - b, left=b, height=0.8, color=clr, zorder=3, **styles["conservative"])
# 			ax.barh(k, opt - b, left=b, height=0.8, color=clr, zorder=3, **styles["optimistic"])
# 		ax.vlines(b, -0.5, n_rows - 0.5, color="black", linewidth=1.0, zorder=4)
# 	ax.set_yticks([])
# 	ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
# 	ax.set_xlim(lim)
# 	if xticks is not None:
# 		ax.set_xticks(list(xticks))
# 	_finish_panel(fig, ax, width, row_height, rect, n_rows, False, path, dpi, fontsize)
 
# 	print(f"\nCombined tornado {metric} (scale={scale}), x-limits {lim}")
# 	for k, row in enumerate(rows):
# 		for p in pathways:
# 			if p in row:
# 				b, o, c, name = row[p]
# 				print(f"  rank {k + 1}  {p:<13} {name:<45} opt {o:,.1f}  mid {b:,.1f}  con {c:,.1f}")
# 	if show_band:
# 		for p in pathways:
# 			lo, hi = (v * scale for v in bands[p][metric])
# 			print(f"  joint top-{len(torn[p][metric][1])} band  {p:<13} {min(lo, hi):,.1f} - {max(lo, hi):,.1f}")
# 	return lim

def _plot_combined_tornado(torn, bands, pathways, metric, scale, *, colors, styles, show_band, band_alpha,
	group_gap, xlim, xticks, margin, width, row_height, rect, path, dpi, fontsize):
	pos, y = {}, 0.0
	for p in pathways:
		n = len(torn[p][metric][1])
		pos[p] = [y + k for k in range(n)]
		y += n + group_gap
	extent = y - group_gap
 
	pts = [v * scale for p in pathways for v in [torn[p][metric][0]] + [x for e in torn[p][metric][1] for x in (e[1], e[2])]]
	if show_band:
		pts += [v * scale for p in pathways for v in bands[p][metric]]
	lim = tuple(xlim) if xlim is not None else _pad(min(pts), max(pts), margin)
 
	fig, ax = plt.subplots(figsize=(width, 1.0))
	fig.patch.set_facecolor("none")
	ax.set_facecolor("none")
	for p in pathways:
		clr = colors.get(p, "gray")
		b = torn[p][metric][0] * scale
		top, bot = pos[p][0] - 0.5, pos[p][-1] + 0.5
		if show_band:
			lo, hi = sorted(v * scale for v in bands[p][metric])
			ax.fill_betweenx([top, bot], lo, hi, color=clr, alpha=band_alpha, linewidth=0, zorder=1)
		for yk, (name, opt, con) in zip(pos[p], torn[p][metric][1]):
			ax.barh(yk, con * scale - b, left=b, height=0.8, color=clr, zorder=3, **styles["conservative"])
			ax.barh(yk, opt * scale - b, left=b, height=0.8, color=clr, zorder=3, **styles["optimistic"])
		ax.vlines(b, top, bot, color="black", linewidth=1.0, zorder=4)
	ax.set_yticks([])
	ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
	ax.set_xlim(lim)
	if xticks is not None:
		ax.set_xticks(list(xticks))
	_finish_panel(fig, ax, width, row_height, rect, extent, False, path, dpi, fontsize)
 
	print(f"\nCombined tornado {metric} (scale={scale}), x-limits {lim}")
	for p in pathways:
		b = torn[p][metric][0] * scale
		for k, (name, opt, con) in enumerate(torn[p][metric][1]):
			print(f"  {p:<13} rank {k + 1}  {name:<45} opt {opt * scale:,.1f}  mid {b:,.1f}  con {con * scale:,.1f}")
		if show_band:
			lo, hi = sorted(v * scale for v in bands[p][metric])
			print(f"  {p:<13} joint top-{len(torn[p][metric][1])} band  {lo:,.1f} - {hi:,.1f}")
	return lim
 
def run_summary_panels(pathways_data, transp_data, loc_data, machine_data, material_data, data_folder, fig_dir,
	pathways=("Silver Peak", "Thacker Pass", "Jianxiawo"),
	top_n=3,
	tornado_layout="combined",	# "combined": one panel per metric, rows = rank, bars colored by pathway, absolute axis
								# "per_pathway": one tornado per pathway and metric, axes set by tornado_axes
	tornado_axes="common", 	# per_pathway only. "common": identical limits for all three rows
							# "span": a common span centered on each pathway own baseline
							# "auto": scales each pathway separately.
							# "delta": plots change from the midpoint of each pathway, on the same axis.
	joint_band=True,		# combined only: shade each pathway's joint top-n range (same ranking as Fig. 3)
	band_alpha=0.15,
	pathway_colors=None,
	tornado_styles=None,
	group_gap=0.2,			# combined only: blank space between pathway groups, in bar rows,
	co2_scale=1.0,
	fold_transport=False,	# summary panels: report Transport inside Other
	cost_xlim=None,
	co2_xlim=None,
	cost_xticks=None,
	co2_xticks=None,
	tornado_cost_xlim=None,
	tornado_co2_xlim=None,
	tornado_cost_xticks=None,
	tornado_co2_xticks=None,
	bar_width=5.0,
	bar_row_height=0.7,
	tornado_width=3.5,
	tornado_row_height=0.5,
	combined_width=7.0,
	combined_row_height=0.35,
	bar_rect=(1.25, 0.35, 0.15, 0.10),
	tornado_rect=(1.25, 0.35, 0.15, 0.10),
	combined_rect=(0.25, 0.35, 0.25, 0.10),
	ticklabels=True,
	wrap_width=18,
	fontsize=8,
	margin=0.05,
	dpi=300,
	prefix="04s",
	):
	if tornado_layout not in ("combined", "per_pathway"):
		raise ValueError("tornado_layout must be 'combined' or 'per_pathway'")
	if tornado_axes not in ("span", "common", "auto", "delta"):
		raise ValueError("tornado_axes must be 'span', 'common', 'auto' or 'delta'")
	colors = dict(PATHWAY_COLORS, **(pathway_colors or {}))
	styles = {k: dict(v, **((tornado_styles or {}).get(k) or {})) for k, v in TORNADO_STYLES.items()}
	show_band = joint_band and tornado_layout == "combined"
	prev_backend = matplotlib.get_backend()
	plt.switch_backend("Agg")
	try:
		fac, torn, bands = {}, {}, {}
		for pathway in pathways:
			pathway_data = pathways_data[pathway]
			apv = pathway_data["Production Volume"]
			sc = SupplyChain(transp_data, loc_data, machine_data, material_data)
			evaluate_pathway(sc, pathway_data, data_folder, detail=0, plot=0)
			fac[pathway] = facility_panel_data(sc, pathway_data, apv, co2_scale=co2_scale, fold_transport=fold_transport)
			tornado = run_tornado_data(sc, pathway_data, apv)
			torn[pathway] = {
				m: (tornado["baseline"][m], tornado_entries(tornado, m, top_n))
				for m in ("avg_opex", "avg_co2")
			}
			if show_band:
				tc = run_topn_scenarios(sc, pathway_data, apv, top_n=top_n, metric="avg_opex")
				te = run_topn_scenarios(sc, pathway_data, apv, top_n=top_n, metric="avg_co2")
				bands[pathway] = {
					"avg_opex": (tc["optimistic"]["avg_opex"], tc["conservative"]["avg_opex"]),
					"avg_co2":  (te["optimistic"]["avg_co2"] * 1000, te["conservative"]["avg_co2"] * 1000),
				}
 
		limits = {}
		for kind, fixed in (("cost", cost_xlim), ("co2", co2_xlim)):
			if fixed is not None:
				limits[kind] = tuple(fixed)
				continue
			ext = [_bar_extent(fac[p][kind]) for p in pathways]
			limits[kind] = _pad(min(e[0] for e in ext), max(e[1] for e in ext), margin)
 
		torn_limits = {}
		if tornado_layout == "per_pathway":
			for metric, scale in (("avg_opex", 1.0), ("avg_co2", co2_scale)):
				pts = {}
				for p in pathways:
					b, entries = torn[p][metric]
					pts[p] = (b * scale, [v * scale for e in entries for v in (e[1], e[2])])
				if tornado_axes == "delta":
					half = max(abs(v - b) for b, vs in pts.values() for v in vs) * (1 + margin)
					torn_limits[metric] = {p: (-half, half) for p in pts}
				elif tornado_axes == "span":
					half = max(abs(v - b) for b, vs in pts.values() for v in vs) * (1 + margin)
					torn_limits[metric] = {p: (b - half, b + half) for p, (b, _) in pts.items()}
				elif tornado_axes == "common":
					lo = min(min(vs + [b]) for b, vs in pts.values())
					hi = max(max(vs + [b]) for b, vs in pts.values())
					torn_limits[metric] = {p: _pad(lo, hi, margin) for p in pathways}
				else:
					torn_limits[metric] = {p: _pad(min(vs + [b]), max(vs + [b]), margin) for p, (b, vs) in pts.items()}
 
		paths = []
		for pathway in pathways:
			for kind, clrs, xticks, tag in (
				("cost", COST_SERIES_COLORS, cost_xticks, "Facility-Cost"),
				("co2", SCOPE_COLORS, co2_xticks, "Facility-Emissions"),
			):
				d = fac[pathway][kind]
				fig, ax = helpers.plot_stacked_bars(d["labels"], d["series"],
					stack_order=d["stack"], colors=clrs,
					title="", xlab="", ylab="",
					ylims=limits[kind], xticks=xticks,
					err_low=d["err_low"], err_high=d["err_high"],
					wrap_width=wrap_width, label_fontsize=fontsize, show=False)
				path = os.path.join(fig_dir, f"{prefix}-{pathway}-{tag}.png")
				_finish_panel(fig, ax, bar_width, bar_row_height, bar_rect, len(d["labels"]), ticklabels, path, dpi, fontsize)
				paths.append(path)
			if tornado_layout == "per_pathway":
				for metric, scale, tag in (("avg_opex", 1.0, "Tornado-Cost"), ("avg_co2", co2_scale, "Tornado-Emissions")):
					b, entries = torn[pathway][metric]
					if tornado_axes == "delta":
						entries = [(n, o - b, c - b) for n, o, c in entries]
						b = 0.0
					path = os.path.join(fig_dir, f"{prefix}-{pathway}-{tag}.png")
					_plot_tornado_panel(entries, b, torn_limits[metric][pathway], tornado_width, tornado_row_height, tornado_rect,
						ticklabels, path, dpi, scale, fontsize)
					paths.append(path)
 
		if tornado_layout == "combined":
			for metric, scale, xlim, xticks, tag in (
				("avg_opex", 1.0, tornado_cost_xlim, tornado_cost_xticks, "Tornado-Cost"),
				("avg_co2", co2_scale, tornado_co2_xlim, tornado_co2_xticks, "Tornado-Emissions"),
			):
				path = os.path.join(fig_dir, f"{prefix}-Combined-{tag}.png")
				torn_limits[metric] = _plot_combined_tornado(torn, bands, pathways, metric, scale,
					colors=colors, styles=styles, show_band=show_band, band_alpha=band_alpha,
					group_gap=group_gap, xlim=xlim, xticks=xticks, margin=margin,
					width=combined_width, row_height=combined_row_height, rect=combined_rect,
					path=path, dpi=dpi, fontsize=fontsize)
				paths.append(path)
 
		print(f"\nSummary panel axes (co2_scale={co2_scale})")
		print(f"  Facility cost x-limits:      {limits['cost']}")
		print(f"  Facility emissions x-limits: {limits['co2']}")
		if tornado_layout == "per_pathway":
			for metric in ("avg_opex", "avg_co2"):
				for p in pathways:
					print(f"  Tornado {metric} {p}: {torn_limits[metric][p]}")
		for path in paths:
			print(f"  wrote {path}")
		return {"facility_limits": limits, "tornado_limits": torn_limits, "paths": paths}
	finally:
		plt.switch_backend(prev_backend)

LOC_SLOTS = ("Location 1","Location 2","Location 3","Location 4")
MATERIAL_BLOCKS = ("material_cost","material_impact")
SCENS = ("optimistic","midpoint","conservative")
RELOC_HATCH = "///"
MATERIAL_BY_TYPE = {"Clays": "Clay", "Lepidolite": "Lepidolite", "Brine-Evaporative": "Brine", "Spodumene": "Spodumene"}

def _has_values(entry):
	if not isinstance(entry,dict):
		return entry not in (None,0)
	return any(_has_values(v) for v in entry.values())

def reloc_pathway_data(guest_data,host_data):
	reloc = deepcopy(guest_data)
	for slot in LOC_SLOTS:
		if reloc.get(slot):
			reloc[slot] = host_data.get(slot) or host_data["Location 2"]
	for spec in (reloc.get("reagent_plant") or {}).values():
		if spec.get("location"):
			spec["location"] = host_data["Location 2"]
	missing = []
	for blk in MATERIAL_BLOCKS:
		guest_blk = reloc.get(blk) or {}
		host_blk = host_data.get(blk) or {}
		for material in guest_blk:
			if _has_values(host_blk.get(material)):
				guest_blk[material] = deepcopy(host_blk[material])
			elif _has_values(guest_blk[material]):
				missing.append(f"{blk}.{material}")
	return reloc, missing

def _evaluate(pathway_data,transp_data,loc_data,machine_data,material_data,data_folder,top_n=None):
	sc = SupplyChain(transp_data,loc_data,machine_data,material_data)
	summary = evaluate_pathway(sc,pathway_data,data_folder,detail=0,plot=0)
	out = {scen: {"avg_opex": v["avg_opex"], "avg_co2": v["avg_co2"]/1000} for scen,v in summary.items()}
	if top_n:
		apv = pathway_data["Production Volume"]
		topn_cost = run_topn_scenarios(sc,pathway_data,apv,top_n=top_n,metric="avg_opex")
		topn_co2  = run_topn_scenarios(sc,pathway_data,apv,top_n=top_n,metric="avg_co2")
		out[f"top{top_n}"] = {scen: {"avg_opex": topn_cost[scen]["avg_opex"], "avg_co2": topn_co2[scen]["avg_co2"]} for scen in SCENS}
	return out

def run_relocation(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,
	pairs=(("Jianxiawo","Thacker Pass"),("Thacker Pass","Jianxiawo")),
	top_n=3,
	verbose=True,
	):
	results = {"base": {}, "relocated": {}, "missing": {}, "top_n": top_n}
	for pathway in {p for pair in pairs for p in pair}:
		results["base"][pathway] = _evaluate(pathways_data[pathway],transp_data,loc_data,machine_data,material_data,data_folder,top_n)
	for guest,host in pairs:
		reloc,missing = reloc_pathway_data(pathways_data[guest],pathways_data[host])
		results["missing"][(guest,host)] = missing
		results["relocated"][(guest,host)] = _evaluate(reloc,transp_data,loc_data,machine_data,material_data,data_folder,top_n)

	gaps = {}
	for a,b in pairs:
		if (b,a) not in results["relocated"] or (b,a) in gaps:
			continue
		loc_a = pathways_data[a]["Location 2"]
		loc_b = pathways_data[b]["Location 2"]
		gaps[(a,b)] = {}
		for metric in ("avg_opex","avg_co2"):
			for scen in SCENS:
				base_a = results["base"][a][scen][metric]
				base_b = results["base"][b][scen][metric]
				a_at_b = results["relocated"][(a,b)][scen][metric]
				b_at_a = results["relocated"][(b,a)][scen][metric]
				gaps[(a,b)][(metric,scen)] = {
					"observed": base_a - base_b,
					f"at {loc_a}": base_a - b_at_a,
					f"at {loc_b}": a_at_b - base_b,
					f"location effect {a}": a_at_b - base_a,
					f"location effect {b}": b_at_a - base_b,
				}
	results["gaps"] = gaps

	if verbose:
		print(f"\n{'='*72}\nRelocation of operating context (waste regime held at origin)\n{'='*72}")
		for (guest,host),vals in results["relocated"].items():
			loc = pathways_data[host]["Location 2"]
			for scen in SCENS:
				b = results["base"][guest][scen]
				r = vals[scen]
				print(f"  {guest:<13} -> {loc:<22} {scen:<12} opex {b['avg_opex']:>9,.0f} -> {r['avg_opex']:>9,.0f}   co2 {b['avg_co2']:>6.2f} -> {r['avg_co2']:>6.2f}")
			if results["missing"][(guest,host)]:
				print(f"  host has no value, guest value kept: {results['missing'][(guest,host)]}")
		for pair,table in gaps.items():
			print(f"\nGap {pair[0]} minus {pair[1]}")
			for (metric,scen),row in table.items():
				print(f"  {metric:<8} {scen:<12} " + "  ".join(f"{k}: {v:,.2f}" for k,v in row.items()))
	return results

def _reloc_label(pathway,location):
	return f"{pathway} ({location.split('_')[-1]})"

def write_relocation_csv(results,pathways_data,csv_path):
	top_n = results["top_n"]
	cols = {"optimistic": "Our Study-Low", "midpoint": "Our Study-Midpoint", "conservative": "Our Study-High"}
	cols_n = {"optimistic": f"Our Study-Low-{top_n}", "conservative": f"Our Study-High-{top_n}"} if top_n else {}
	entries = [(_reloc_label(p,pathways_data[p]["Location 2"]),p,pathways_data[p]["Location 2"],vals) for p,vals in results["base"].items()]
	entries += [(_reloc_label(g,pathways_data[h]["Location 2"]),g,pathways_data[h]["Location 2"],vals) for (g,h),vals in results["relocated"].items()]
	header = ["Pathway","Company","Location","Material","Dimension"] + list(cols.values()) + list(cols_n.values())
	rows = [{**{c: "-" for c in header[:4]}, "Dimension": "source_type"}]
	for label,pathway,loc,vals in entries:
		for dim,metric in (("Cost","avg_opex"),("Emissions","avg_co2")):
			row = {"Pathway": label, "Company": "", "Location": loc, "Material": MATERIAL_BY_TYPE.get(pathways_data[pathway]["Type"],pathways_data[pathway]["Type"]), "Dimension": dim}
			for scen,col in cols.items():
				row[col] = vals[scen][metric]
			for scen,col in cols_n.items():
				row[col] = vals[f"top{top_n}"][scen][metric]
			rows.append(row)
	pd.DataFrame(rows,columns=header).to_csv(csv_path,index=False)
	return [e[0] for e in entries[len(results["base"]):]]

def plot_relocation(results,pathways_data,csv_path,save_path=None,costs_emissions_dir=None,**plot_kwargs):
	import sys
	sys.path.insert(0,costs_emissions_dir or COST_EMISSIONS_DIR)
	from costs_emissions import plot_cost_vs_emissions
	relocated_labels = write_relocation_csv(results,pathways_data,csv_path)
	return plot_cost_vs_emissions(csv_path,
		title=plot_kwargs.pop("title","Relocation of operating context"),
		save_path=save_path if save_path is not None else False,
		top_n=results["top_n"],
		pathway_hatches={label: RELOC_HATCH for label in relocated_labels},
		**plot_kwargs)

# GLOBAL VARIABLES
FIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),"Raw Figures/Current")
COST_EMISSIONS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","Costs-Emissions"))

NORM_AXES = { # This is just for the cost and emissions step-by-step plots
	"ylims_cost":       (0,7000),
	"xticks_cost":      range(0,7001,1000),
	"ylims_emissions":  (-500,30000),
	"xticks_emissions": range(0,30001,5000),
}
FAC_SLOTS = {
	"Evaporation Ponds": "Facility 1",
	"Mining": "Facility 1",
	"Concentrated Brine": "Facility 2",
	"Material Refining": "Facility 2",
	"Lithium Extraction": "Facility 3",
}
WASTE_GROUP = "Tailings & Wastewater"
SINK_SLOTS = {
	"Tailings Management": WASTE_GROUP,
	"Wastewater Treatment": WASTE_GROUP,
	"Waste Rock Pile": WASTE_GROUP,
}
SLOT_KEYS = ("Facility 1", "Facility 2", "Facility 3")

# COLORS
COST_SERIES_COLORS = {
	"Material Costs":       "#4f79a7", # purple-ish
	"Labor Costs":          "#E69F00", # orange (okabe-ito)
	"Utility Costs":        "#F0E442", # yellow
	"Other":                "#a6a6a6", # light gray
	"Transport":            "#D55E00", # vermillion (okabe-ito)
	"Waste Rock Pile":      "#6f4038", # dark brown
	"Tailings Management":  "#8c564b", # medium brown
	"Wastewater Treatment": "#b98d84", # light brown
}
SCOPE_COLORS = {
	"Scope One":   "#7a3b63", # deep rose
	"Scope Two":   "#ebc3d9", # pale rose
	"Scope Three": "#cc79a7", # reddish purple (Okabe-Ito)
}
TORNADO_COLORS = {"conservative": "#f28e2b", "optimistic": "#4e79a7"} # If doing color for bars; uses pathway colors
PATHWAY_COLORS = { # Should be same as costs_emissions.py
	"Silver Peak": "#4292c6",
	"Thacker Pass": "#08519c",
	"Jianxiawo": "#d62728",
}
TORNADO_STYLES = {
	"conservative": {"edgecolor": "black", "linewidth": 0.8},
	"optimistic":   {"edgecolor": "white", "linewidth": 0.8},
}

if __name__ == '__main__':
	data_folder = "./data/Supplementary Data File.xlsx"

	missing = helpers.check_workbook_formula_cache(data_folder)
	if missing:
		raise RuntimeError(f"{len(missing)} formula cells have no cached value; open the workbook in Excel, recalculate, and save. First: {missing[:5]}")

	pathways_data = helpers.build_data_dict(data_folder,"Pathway-Specific Data")
	transp_data   = helpers.build_data_dict(data_folder,"Transportation Data", col=3)
	loc_data      = helpers.build_locations_dict(data_folder,"Locational Data")
	machine_data  = helpers.build_data_dict(data_folder,"Machine Blocks Data", skip_rows=["notes", "sources", "key_equation", "machine_block_type"])
	material_data = helpers.build_data_dict(data_folder,"Material Data")

	run_all(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,
			FIG_DIR,COST_EMISSIONS_DIR,NORM_AXES)
	run_summary_panels(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,FIG_DIR)

	# reloc = run_relocation(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,top_n=3)
	# plot_relocation(reloc,pathways_data,
	# 	os.path.join(COST_EMISSIONS_DIR,"relocation_both.csv"),
	# 	save_path=os.path.join(COST_EMISSIONS_DIR,"Current","relocation_cost_emissions.png"),
	# 	show_pathway_labels=False)












