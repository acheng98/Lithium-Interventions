from supply_chain import SupplyChain
from facility import Facility, ReagentFacility
from sinks import load_sink_params, tailings_handling, sink_s_out, sink_override_map, apply_sink_overrides
from production_step import ProductionStep
from transportation import Transportation, TransportRoute
import helpers, scenarios, plotting, li_figures
from config import (DATA_FILE, FIG_DIR, NORM_AXES, FAC_SLOTS, WASTE_GROUP, SINK_SLOTS, SLOT_KEYS, 
	COST_SERIES_COLORS, SCOPE_COLORS, TORNADO_COLORS, PATHWAY_COLORS, TORNADO_STYLES)

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
	scenarios.update_materials(sc,pathway_data,"midpoint")
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

		if detail > 3:
			print(sc.get_step_reagent_usage())
			pprint(sc.get_step_utilities_detailed())
	
	if plot == 1:
		# sc.plot_step_costs(mode="average",view="opex",detail=3,cost_colors=COST_SERIES_COLORS)
		sc.plot_step_costs(mode="average",view="opex",detail=2,cost_colors=COST_SERIES_COLORS)
		sc.plot_step_impacts(mode="average",imp_colors=SCOPE_COLORS)
		# sc.plot_step_costs(view="variable",detail=3,cost_colors=COST_SERIES_COLORS)
		# sc.plot_step_costs(view="variable",detail=2,cost_colors=COST_SERIES_COLORS)
		# sc.plot_tot_steps_impacts()
		# sc.plot_total_cc()

	scenarios.update_machines(sc,"conservative")
	scenarios.update_materials(sc,pathway_data,"conservative")
	summary_conservative = sc.update_apv(target_pv,recalc=True)
	summary["conservative"] = summary_conservative
	# pprint(summary_conservative)
	# print("\nConservative - Labor:")
	# pprint(sc.get_step_labor())
	# print("\nUtilities:")
	# pprint(sc.get_total_utilities())
	# print(sc.get_step_reagent_usage())
	# pprint(sc.get_step_utilities_detailed())

	scenarios.update_machines(sc,"optimistic")
	scenarios.update_materials(sc,pathway_data,"optimistic")
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
			plotting.plot_scenario_step_costs(sc, pathway_data, pathway_data["Production Volume"],
				view="opex",	# total|variable|fixed|opex|capex  (combo not supported)
				mode="average",	# "total" | "average"
				detail=2,		# 1|2|3 — applied to midpoint bars; conservative/optimistic always use detail=1
				transp=True,
				# title=None,
				ylims=ylims_cost,
				xticks=xticks_cost,
				colors=COST_SERIES_COLORS,
			)
			plotting.plot_scenario_step_impacts(sc, pathway_data, pathway_data["Production Volume"],
				mode="average",         # "total" | "average"
				impact="co2",           # impact category key (e.g. "co2", "ghg")
				# title=None,
				ylims=ylims_emissions,
				xticks=xticks_emissions,
				colors=SCOPE_COLORS,
			)
		if plot == 2.1 and pathway == "Thacker Pass": # Custom Thacker Pass Aggregation
			li_figures.thacker_pass_steps_aggregated(sc, pathway_data, pathway_data["Production Volume"],
				ylims_cost=ylims_cost,			 xticks_cost=xticks_cost,
				ylims_emissions=ylims_emissions, xticks_emissions=xticks_emissions,
				cost_colors=COST_SERIES_COLORS, imp_colors=SCOPE_COLORS,
			)

		if plot == 2.2 and pathway == "Jianxiawo":
			li_figures.jianxiawo_steps_aggregated(sc, pathway_data, pathway_data["Production Volume"],
				ylims_cost=ylims_cost,			 xticks_cost=xticks_cost,
				ylims_emissions=ylims_emissions, xticks_emissions=xticks_emissions,
				cost_colors=COST_SERIES_COLORS, imp_colors=SCOPE_COLORS,
			)
		if plot == 3:
			tornado = scenarios.run_tornado_data(sc, pathway_data, apv=pathway_data["Production Volume"])
			plotting.plot_tornado(tornado, metric="avg_opex", top_n=5, colors=TORNADO_COLORS)
			plotting.plot_tornado(tornado, metric="avg_co2",  top_n=5, colors=TORNADO_COLORS)

		pathway_summaries[pathway] = summary 
		
		# If write is an integer, run the top-N restricted scenarios now while sc is built
		if isinstance(write, int) and write > 0:
			topn_summaries[pathway] = scenarios.run_topn_scenarios(
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

	# scenarios.update_machines(sc, "midpoint")
	# scenarios.update_materials(sc, pathway_data, "midpoint")
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
		pathway_outputs_to_workbook(extracted_data, data_folder)
		if isinstance(write, int) and write > 0:
			pathway_outputs_to_workbook(topn_summaries, data_folder, col_suffix=f"-{write}")

	return extracted_data


DIMS = (("Cost","avg_opex"),("Emissions","avg_co2"))

def upsert_reported_rows(data_file,rows,sheet="Reported Values"):
	import xlwings as xw
	app = xw.App(visible=False, add_book=False)
	try:
		wb = app.books.open(os.path.abspath(data_file))
		ws = wb.sheets[sheet]
		grid = ws.used_range.value
		header = list(grid[0])
		while header and header[-1] is None:
			header.pop()
		ci = {h: i for i, h in enumerate(header) if h is not None}
		index = {(str(r[ci["Pathway"]]), str(r[ci["Dimension"]])): n for n, r in enumerate(grid[1:], start=2) if r[ci["Pathway"]]}
		next_row = len(grid) + 1
		for row in rows:
			for col in row:
				if col not in ci:
					header.append(col)
					ci[col] = len(header) - 1
					ws.range((1, len(header))).value = col
			key = (str(row["Pathway"]), str(row["Dimension"]))
			if key not in index:
				index[key] = next_row
				next_row += 1
			for col, val in row.items():
				ws.range((index[key], ci[col] + 1)).value = val
		wb.save()
		wb.close()
	finally:
		app.quit()
 
def pathway_outputs_to_workbook(extracted_data,data_file,col_suffix=""):
	scen_to_col = {
		"optimistic":   f"Our Study-Low{col_suffix}",
		"midpoint":     "Our Study-Midpoint",
		"conservative": f"Our Study-High{col_suffix}",
	}
	rows = []
	for pathway, scens in extracted_data.items():
		for dim, metric in DIMS:
			row = {"Pathway": pathway, "Dimension": dim}
			for scen, col in scen_to_col.items():
				val = (scens.get(scen) or {}).get(metric)
				if val is not None:
					row[col] = float(val)
			rows.append(row)
	upsert_reported_rows(data_file, rows)

def run_all(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,
	fig_dir,
	norm_axes,
	pathways=("Silver Peak","Thacker Pass","Jianxiawo"),
	detail=4,
	axes_mode="both",
	top_n_range=3,
	top_n_tornado=5,
	write=True,
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
				li_figures._step_summary_figures(pathway,sc,pathway_data,apv,axes,fig_dir,suffix)

			tornado = scenarios.run_tornado_data(sc,pathway_data,apv)
			plotting.plot_tornado(tornado,metric="avg_opex",top_n=top_n_tornado,colors=TORNADO_COLORS)
			plotting.plot_tornado(tornado,metric="avg_co2",top_n=top_n_tornado,colors=TORNADO_COLORS)
			li_figures._save_open_figures([
				os.path.join(fig_dir,f"04-{pathway}-Sensitivity-Cost.png"),
				os.path.join(fig_dir,f"04-{pathway}-Sensitivity-Emissions.png"),
			])
			print("\nTornado ranges:")
			for kind in ("machines","materials"):
				for name,vals in sorted(tornado.get(kind,{}).items()):
					for metric in ("avg_opex","avg_co2"):
						spread = abs(vals["conservative"][metric]-vals["optimistic"][metric])
						print(f"  {kind[:-1]}  {name}  {metric}  {spread:,.4f}")

			topn_cost = scenarios.run_topn_scenarios(sc,pathway_data,apv,top_n=top_n_range,metric="avg_opex")
			topn_co2  = scenarios.run_topn_scenarios(sc,pathway_data,apv,top_n=top_n_range,metric="avg_co2")
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
			scenarios.update_machines(sc_nc,"midpoint")
			scenarios.update_materials(sc_nc,jx_data,"midpoint")
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
			scenarios.update_machines(sc_sx,"midpoint")
			scenarios.update_materials(sc_sx,tp_data,"midpoint")
			sx_summary = sc_sx.update_apv(tp_apv,recalc=True)
			sx_labels,sx_series,_ = sc_sx._build_steps_cost_series(view="opex",detail=2,transp=True,top_n=None)
			base_opex = extracted_data["Thacker Pass"]["midpoint"]["avg_opex"]
			print(f"\n{'='*72}\nThacker Pass sulfur supply shock at ${tp_sulfur_shock:,.3f}/kg, midpoint basis\n{'='*72}")
			print(f"avg_opex {sx_summary['avg_opex']:,.6f}   avg_co2 {sx_summary['avg_co2']/1000:,.6f}")
			print(f"delta vs midpoint {sx_summary['avg_opex']-base_opex:,.6f} $/t")
			for i,label in enumerate(sx_labels):
				print(f"  {label}: ${sum(vals[i] for vals in sx_series.values())/tp_apv:,.4f}/t")

		if write:
			pathway_outputs_to_workbook(extracted_data, data_folder)
			pathway_outputs_to_workbook(topn_summaries, data_folder, col_suffix=f"-{top_n_range}")

		return extracted_data,topn_summaries
	finally:
		plt.switch_backend(prev_backend)

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
			fac[pathway] = li_figures.facility_panel_data(sc, pathway_data, apv, co2_scale=co2_scale, fold_transport=fold_transport)
			tornado = scenarios.run_tornado_data(sc, pathway_data, apv)
			torn[pathway] = {
				m: (tornado["baseline"][m], li_figures.tornado_entries(tornado, m, top_n))
				for m in ("avg_opex", "avg_co2")
			}
			if show_band:
				tc = scenarios.run_topn_scenarios(sc, pathway_data, apv, top_n=top_n, metric="avg_opex")
				te = scenarios.run_topn_scenarios(sc, pathway_data, apv, top_n=top_n, metric="avg_co2")
				bands[pathway] = {
					"avg_opex": (tc["optimistic"]["avg_opex"], tc["conservative"]["avg_opex"]),
					"avg_co2":  (te["optimistic"]["avg_co2"] * 1000, te["conservative"]["avg_co2"] * 1000),
				}
 
		limits = {}
		for kind, fixed in (("cost", cost_xlim), ("co2", co2_xlim)):
			if fixed is not None:
				limits[kind] = tuple(fixed)
				continue
			ext = [li_figures._bar_extent(fac[p][kind]) for p in pathways]
			limits[kind] = li_figures._pad(min(e[0] for e in ext), max(e[1] for e in ext), margin)
 
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
					torn_limits[metric] = {p: li_figures._pad(lo, hi, margin) for p in pathways}
				else:
					torn_limits[metric] = {p: li_figures._pad(min(vs + [b]), max(vs + [b]), margin) for p, (b, vs) in pts.items()}
 
		paths = []
		for pathway in pathways:
			for kind, clrs, xticks, tag in (
				("cost", COST_SERIES_COLORS, cost_xticks, "Facility-Cost"),
				("co2", SCOPE_COLORS, co2_xticks, "Facility-Emissions"),
			):
				d = fac[pathway][kind]
				fig, ax = plotting.plot_stacked_bars(d["labels"], d["series"],
					stack_order=d["stack"], colors=clrs,
					title="", xlab="", ylab="",
					ylims=limits[kind], xticks=xticks,
					err_low=d["err_low"], err_high=d["err_high"],
					wrap_width=wrap_width, label_fontsize=fontsize, show=False)
				path = os.path.join(fig_dir, f"{prefix}-{pathway}-{tag}.png")
				li_figures._finish_panel(fig, ax, bar_width, bar_row_height, bar_rect, len(d["labels"]), ticklabels, path, dpi, fontsize)
				paths.append(path)
			if tornado_layout == "per_pathway":
				for metric, scale, tag in (("avg_opex", 1.0, "Tornado-Cost"), ("avg_co2", co2_scale, "Tornado-Emissions")):
					b, entries = torn[pathway][metric]
					if tornado_axes == "delta":
						entries = [(n, o - b, c - b) for n, o, c in entries]
						b = 0.0
					path = os.path.join(fig_dir, f"{prefix}-{pathway}-{tag}.png")
					li_figures._plot_tornado_panel(entries, b, torn_limits[metric][pathway], tornado_width, tornado_row_height, tornado_rect,
						ticklabels, path, dpi, scale, fontsize)
					paths.append(path)
 
		if tornado_layout == "combined":
			for metric, scale, xlim, xticks, tag in (
				("avg_opex", 1.0, tornado_cost_xlim, tornado_cost_xticks, "Tornado-Cost"),
				("avg_co2", co2_scale, tornado_co2_xlim, tornado_co2_xticks, "Tornado-Emissions"),
			):
				path = os.path.join(fig_dir, f"{prefix}-Combined-{tag}.png")
				torn_limits[metric] = li_figures._plot_combined_tornado(torn, bands, pathways, metric, scale,
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
		topn_cost = scenarios.run_topn_scenarios(sc,pathway_data,apv,top_n=top_n,metric="avg_opex")
		topn_co2  = scenarios.run_topn_scenarios(sc,pathway_data,apv,top_n=top_n,metric="avg_co2")
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

def relocation_rows(results,pathways_data):
	top_n = results["top_n"]
	cols = {"optimistic": "Our Study-Low", "midpoint": "Our Study-Midpoint", "conservative": "Our Study-High"}
	cols_n = {"optimistic": f"Our Study-Low-{top_n}", "conservative": f"Our Study-High-{top_n}"} if top_n else {}
	def _row(label,vals,dim,metric,extra):
		row = {"Pathway": label, "Dimension": dim, **extra}
		for scen,col in cols.items():
			row[col] = float(vals[scen][metric])
		for scen,col in cols_n.items():
			row[col] = float(vals[f"top{top_n}"][scen][metric])
		return row
	rows, labels = [], []
	for pathway,vals in results["base"].items():
		for dim,metric in DIMS:
			rows.append(_row(pathway,vals,dim,metric,{"Scenario": "Both"}))
	for (guest,host),vals in results["relocated"].items():
		loc = pathways_data[host]["Location 2"]
		label = _reloc_label(guest,loc)
		labels.append(label)
		ptype = pathways_data[guest]["Type"]
		extra = {"Location": loc, "Material": MATERIAL_BY_TYPE.get(ptype,ptype), "Scenario": "Relocation"}
		for dim,metric in DIMS:
			rows.append(_row(label,vals,dim,metric,extra))
	return rows, labels
 
def plot_relocation(results,pathways_data,data_file,save_path=None,**plot_kwargs):
	from costs_emissions import plot_cost_vs_emissions
	rows,relocated_labels = relocation_rows(results,pathways_data)
	upsert_reported_rows(data_file,rows)
	return plot_cost_vs_emissions(data_file,
		scenarios=("Both","Relocation"),
		hide_literature=True,
		title=plot_kwargs.pop("title","Relocation of operating context"),
		save_path=save_path if save_path is not None else False,
		top_n=results["top_n"],
		pathway_hatches={label: RELOC_HATCH for label in relocated_labels},
		**plot_kwargs)

if __name__ == '__main__':
	data_folder = DATA_FILE

	missing = helpers.check_workbook_formula_cache(data_folder)
	if missing:
		raise RuntimeError(f"{len(missing)} formula cells have no cached value; open the workbook in Excel, recalculate, and save. First: {missing[:5]}")

	pathways_data = helpers.build_data_dict(data_folder,"Pathway-Specific Data")
	transp_data   = helpers.build_data_dict(data_folder,"Transportation Data", col=3)
	loc_data      = helpers.build_locations_dict(data_folder,"Locational Data")
	machine_data  = helpers.build_data_dict(data_folder,"Machine Blocks Data", skip_rows=["notes", "sources", "key_equation", "machine_block_type"])
	material_data = helpers.build_data_dict(data_folder,"Material Data")

	run_all(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,
			FIG_DIR,NORM_AXES)
	run_summary_panels(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,FIG_DIR)

	# reloc = run_relocation(pathways_data,transp_data,loc_data,machine_data,material_data,data_folder,top_n=3)
	# plot_relocation(reloc,pathways_data,data_folder,
	# 	save_path=os.path.join(FIG_DIR,"relocation_cost_emissions.png"),
	# 	show_pathway_labels=False)












