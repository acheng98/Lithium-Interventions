import helpers
from supply_chain import SupplyChain
from facility import Facility
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
							sinks = ["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
							location = project_data["Location 2"], # Assume lithium extraction plant is adjacent to concentrated brine facility
							steps = helpers.build_facility_dict(data_folder,project_data["Pathway 3"]))
	sc.add_facility(lithium_extraction)

	# Concentrated Brine facility 	
	conc_brine = Facility(fac_id="Concentrated Brine", supply_chain=sc,
						sinks = ["landfill","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
						location = project_data["Location 2"],
						steps = helpers.build_facility_dict(data_folder,project_data["Pathway 2"]))
	sc.add_facility(conc_brine, next_fac=lithium_extraction, products={"pls_post_polishing": 1})

	# Evaporation ponds 'facility' 
	evap_ponds = Facility(fac_id="Evaporation Ponds", supply_chain=sc,
						sinks = ["landfill","atmosphere"], # Potassium?
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
								sinks=["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
								location=project_data["Location 2"], # Assume lithium extraction is adjacent to leaching plant 
								steps=helpers.build_facility_dict(data_folder,project_data["Pathway 3"]))
	sc.add_facility(lithium_extraction)

	# Communition and Leaching facility 
	material_refining = Facility(fac_id="Material Refining", supply_chain=sc,
								sinks = ["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
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
									sinks = ["landfill","atmosphere","waste_pile"],
									location=project_data["Location 1"],
									steps=helpers.build_facility_dict(data_folder,project_data["Pathway 1"]))

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
	loading.set_conversion_factor("rom_ore_feed",rho_loose * 1/(1+strip_ratio)) # get from ore --> total moved (ore + waste)
	loading.set_conversion_factor("waste",rho_loose * (strip_ratio + loss)/(1+strip_ratio)) # (calculate waste = strip ratio + loss)

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
		print(pls_post_polishing)
		lithium_extraction.add_target_comp(target = "pls_post_polishing", composition = pls_post_polishing["constituents"],
											target_step_id = "precipitation_step", propagate = True)

		# Jank workaround to custom-set CCFs for solution processing because they are different between Clay & Lepidolite
		precip_step = lithium_extraction.fwd[0]
		ccf = 0.2/(0.2/2.7+0.8/1)/10**6 # Assume TDS is ~100 g/L
		precip_step.set_conversion_factor("pls_post_polishing",ccf,field="ccf")
		precip_step.set_conversion_factor("polish_pls_throughput",ccf,field="ccf")

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
		precip_step.set_conversion_factor("polish_pls_throughput",ccf,field="ccf")
	
	products = {"rom_ore_feed": 1}
	sc.add_facility(material_extraction, next_fac=material_refining, products=products, transport_route=ore_truck_route)	

	return sc 

def evaluate_project(sc,project_data,data_folder):
	summary = {}

	project_type = project_data["Type"]
	if project_type == "Brine-Evaporative":
		sc = lithium_evaporation(sc,project_data,data_folder)
	elif project_type == "Brine-DLE":
		pass 
	elif project_type == "Spodumene":
		pass
	elif project_type in ["Clays","Lepidolite"]:
		sc = clay_lepidolite(sc,project_data,data_folder)
	else:
		raise ValueError(f"Project type '{project_type}' not defined.")

	# for target_pv in target_pvs:
	target_pv = project_data["Production Volume"] # convert to kg
	# print("Summary statistics:")
	summary_midpoint = sc.update_apv(target_pv)
	summary["midpoint"] = summary_midpoint
	# pprint(summary_midpoint)
	
	print("\nProduction volume at each step:")
	print("\nStep Production volumes:", sc.get_detailed_pvs())
	print(sc.get_detailed_inputs())
	pprint(sc.get_step_constituents())
	# print("\nAmount of lithium in each step:", sc.get_constituent_amount_at_steps("Li"))
	# print("\nAmount of lithium carbonate in each step:",sc.get_constituent_amount_at_steps("Li2CO3"))
	
	# print(sc.get_step_reagent_usage())
	# pprint(sc.get_step_utilities_detailed())
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
	
	wk_compare(sc,project_type)

	# sc.plot_tot_steps_costs(view="opex",detail=3)
	# sc.plot_tot_steps_costs(view="opex",detail=2)
	# sc.plot_tot_steps_costs(view="variable",detail=3)
	# sc.plot_tot_steps_costs(view="variable",detail=2)
	# sc.plot_tot_steps_impacts()
	# sc.plot_total_cc()

	helpers.update_machines(sc,"conservative")
	summary_conservative = sc.update_apv(target_pv,recalc=True)
	summary["conservative"] = summary_conservative
	# pprint(summary_conservative)

	helpers.update_machines(sc,"optimistic")
	summary_optimistic = sc.update_apv(target_pv,recalc=True)
	summary["optimistic"] = summary_optimistic
	# pprint(summary_optimistic)

	return summary 

def wk_compare(sc,proj):
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
			if step["step_name"] in ["Brine pumping", "Evaporation Ponds", ]:
				mine_opex += (step["material_costs"] + step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"])
				mine_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			else:
				proc_reag += step["material_costs"]
				proc_pow += step["utility_cost_items"]["electricity"]["cost"]
				proc_other += (step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"] - step["utility_cost_items"]["electricity"]["cost"])
				proc_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
	if proj == "Clays":
		for step in step_costs:
			if step["step_name"] in ["Loading with excavator"]:
				mine_opex += (step["material_costs"] + step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"])
				mine_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			elif step["step_name"] in ["Ore transport via truck"]:
				mine_opex += (step["variable_costs"])
			else:
				proc_reag += step["material_costs"]
				proc_pow += step["utility_cost_items"]["electricity"]["cost"]
				proc_other += (step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"] - step["utility_cost_items"]["electricity"]["cost"])
				proc_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
	if proj == "Lepidolite":
		for step in step_costs:
			if step["step_name"] in ["Blasting with drilling and explosives","Loading with excavator"]:
				mine_opex += (step["material_costs"] + step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"])
				mine_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
			elif step["step_name"] in ["Ore transport via truck"]:
				mine_opex += (step["variable_costs"])
			else:
				proc_reag += step["material_costs"]
				proc_pow += step["utility_cost_items"]["electricity"]["cost"]
				proc_other += (step["labor_costs"] + step["utility_costs"] + step["maint_cost"] + step["fixed_over_cost"] - step["utility_cost_items"]["electricity"]["cost"])
				proc_capex += (step["machine_cost"] + step["tool_cost"] + step["building_cost"] + step["aux_equip_cost"])
	
	print("Annual Production Volume:",apv,
		"\nAvg. Mine Opex:", mine_opex/apv,
		"\nAvg. Mine Capex:", mine_capex/apv,
		"\nAvg. Process Reagent cost:", proc_reag/apv,
		"\nAvg. Process Power cost:", proc_pow/apv,
		"\nAvg. Other Process costs:", proc_other/apv,
		"\nAvg. Process Capex costs:", proc_capex/apv)


def compare_projects(projects,projects_data,transp_data,loc_data,machine_data,material_data,write):
	project_summaries = {}

	for project in projects:
		project_data = projects_data[project]
		sc = SupplyChain(transp_data,loc_data,machine_data,material_data)
		summary = evaluate_project(sc,project_data,data_folder)
		project_summaries[project] = summary 
		# pprint(summary)

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
	# pprint(extracted_data)

	# helpers.plot_project_summaries(project_summaries)

	if write:
		# Assumes:
		# Lithium Interventions/
		#	Processing Models/run_scenarios.py  (this file)
		#	Cost-Emissions/reported_costs.csv
		#	Cost-Emissions/reported_emissions.csv
		base_dir = os.path.dirname(os.path.abspath(__file__))
		cost_emissions_dir = os.path.normpath(os.path.join(base_dir,"..","Costs-Emissions"))

		cost_csv_path = os.path.join(cost_emissions_dir,"reported_costs.csv")
		emissions_csv_path = os.path.join(cost_emissions_dir,"reported_emissions.csv")

		write_project_outputs_to_csv(extracted_data,cost_csv_path,emissions_csv_path)

	return extracted_data

def write_project_outputs_to_csv(extracted_data,cost_csv_path,emissions_csv_path):
	# Map scenario names -> "Our Study" columns
	scen_to_col = {
		"optimistic": "Our Study-Low",
		"midpoint": "Our Study-Midpoint",
		"conservative": "Our Study-High",
	}

	# -------------------------
	# COSTS: write avg_opex
	# -------------------------
	df_cost = pd.read_csv(cost_csv_path)
	for project,scens in extracted_data.items():
		mask = df_cost["Project"].astype(str) == str(project)
		if not mask.any():
			continue
		for scen,col in scen_to_col.items():
			val = (scens.get(scen) or {}).get("avg_opex",None)
			df_cost.loc[mask,col] = helpers.format_currency(val)
	df_cost.to_csv(cost_csv_path,index=False)

	# -------------------------
	# EMISSIONS: write avg_co2
	# -------------------------
	df_em = pd.read_csv(emissions_csv_path)
	for project,scens in extracted_data.items():
		mask = df_em["Project"].astype(str) == str(project)
		if not mask.any():
			continue
		for scen,col in scen_to_col.items():
			val = (scens.get(scen) or {}).get("avg_co2",None)
			df_em.loc[mask,col] = val
	df_em.to_csv(emissions_csv_path,index=False)

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
	# projects = ["Thacker Pass"]
	projects = ["Jianxiawo"]
	# projects = ["Jianxiawo","Silver Peak","Thacker Pass"]

	compare_projects(projects,projects_data,transp_data,loc_data,machine_data,material_data,write=False)


















