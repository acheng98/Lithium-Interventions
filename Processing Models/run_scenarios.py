import helpers
from supply_chain import SupplyChain
from facility import Facility
from production_step import ProductionStep
from transportation import Transportation, TransportRoute

import pandas as pd
from collections import defaultdict
from copy import deepcopy
from pprint import pprint

def lithium_evaporation(sc,project_data,data_folder):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", supply_chain=sc,
							sinks = ["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
							steps = helpers.build_facility_dict(data_folder,project_data["Pathway 3"]))
	lithium_extraction.update_location(project_data["Location 2"]) # Assume lithium extraction plant is adjacent to concentrated brine facility
	sc.add_facility(lithium_extraction)

	# Concentrated Brine facility 	
	conc_brine = Facility(fac_id="Concentrated Brine", supply_chain=sc,
						sinks = ["landfill","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
						steps = helpers.build_facility_dict(data_folder,project_data["Pathway 2"]))
	conc_brine.update_location(project_data["Location 2"]) 
	sc.add_facility(conc_brine, next_fac=lithium_extraction, products={"brine_post_polishing": 1})

	# Evaporation ponds 'facility' 
	evap_ponds = Facility(fac_id="Evaporation Ponds", supply_chain=sc,
						sinks = ["landfill","atmosphere"], # Potassium?
						steps = helpers.build_facility_dict(data_folder,project_data["Pathway 1"]))
	evap_ponds.update_location(project_data["Location 1"]) 
	# Set conversion factor for yield from ponds
	evap = evap_ponds.fwd[1]
	evap.set_conversion_factor("concentrated_lithium_brine",project_data["Pond Recovery Efficiency"],change_yield=True)

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
	lithium_extraction.add_target_comp(target = "brine_post_polishing", 
								composition = conc_brine.fwd[-1].primary_outputs["brine_post_polishing"]["constituents"], # Would be nice to make a get function for this
								target_step_id = "precipitation_step", propagate = True)
	return sc 

def clay_lepidolite(sc,project_data,data_folder):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", supply_chain=sc,
								sinks=["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
								steps=helpers.build_facility_dict(data_folder,project_data["Pathway 3"]))
	lithium_extraction.update_location(project_data["Location 2"]) # Assume lithium extraction is adjacent to leaching plant 
	sc.add_facility(lithium_extraction)

	# Communition and Leaching facility 
	material_refining = Facility(fac_id="Material Refining", supply_chain=sc,
								sinks = ["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
								steps=helpers.build_facility_dict(data_folder,project_data["Pathway 2"]))
	material_refining.update_location(project_data["Location 2"])
	sc.add_facility(material_refining, next_fac = lithium_extraction, products = {"brine_post_polishing": 1})

	# Transportation
	transps = []
	for leg,dist in project_data["Transport 1"].items(): 
		transps.append(Transportation("Ore transport via truck",sc,leg,dist))
	ore_truck_route = TransportRoute("Ore transport",transps)

	# Mining 'facility' 
	material_extraction = Facility(fac_id="Mining", supply_chain=sc,
									sinks = ["landfill","atmosphere","waste_pile"],
									steps=helpers.build_facility_dict(data_folder,project_data["Pathway 1"]))
	material_extraction.update_location(project_data["Location 1"])

	rho_bank  = project_data["Initial Density"]
	swell_factor = project_data["Swell Factor"]
	dilution = project_data["Dilution"] # Apply dilution directly to chemical composition instead
	strip_ratio = project_data["Strip Ratio"]
	rho_loose = rho_bank / swell_factor
	loss = project_data["Loss"]
	
	init_conc = project_data["Initial Concentration"]
	rom_comp = deepcopy(project_data["Initial Concentration"])
	if not project_data["ROM feed?"]: # If the reported grade is not the grade at ROM, need to dilute
		rom_comp["Li"] = rom_comp["Li"] * (1 - dilution) # Apply dilution to initial composition - may need to apply to other minerals as well, or increase their makeup
	else: # ROM is reported grade
		init_conc["Li"] = rom_comp["Li"] / (1 - dilution) # Back-calculate ore grade based on dilution 



	if project_data["Powder Factor"] in ["","-",None]: # We do *not* have blasting
		# Update initial and final chemical compositions for extraction facility
		material_extraction.add_target_comp(target = "raw_material", composition = init_conc, target_step_id = "excav_load", propagate = False)
		material_extraction.add_target_comp(target = "rom_ore_feed", composition = rom_comp, target_step_id = "excav_load", propagate = False)

		loading = material_extraction.fwd[0]
		loading.set_conversion_factor("raw_material",1/rho_loose)
	else:
		# Update initial and final chemical compositions for extraction facility
		material_extraction.add_target_comp(target = "raw_material", composition = init_conc, target_step_id = "blasting", propagate = True)
		material_extraction.add_target_comp(target = "rom_ore_feed", composition = rom_comp, target_step_id = "excav_load", propagate = False)

		# Get second/last step and add yield
		loading = material_extraction.fwd[1]
		loading.set_conversion_factor("blasted_rock",1/rho_loose)
		
		blasting = material_extraction.fwd[0]
		blasting.set_reagents("explosives",{'targets': {"rock_blast_throughput": {'ratio': project_data["Powder Factor"], 'elim': 0.0}}})
		
	# Get conversion factor from physical volume moved to tonnes diluted ore 
	loading.set_conversion_factor("rom_ore_feed",1-loss,change_yield=True)
	loading.set_conversion_factor("rom_ore_feed",rho_loose * 1/(1+strip_ratio)) # get from ore --> total moved (ore + waste)
	loading.set_conversion_factor("waste",rho_loose * (strip_ratio + loss)/(1+strip_ratio)) # (calculate waste = strip ratio + loss)

	# Update initial and final chemical compositions for each subsequent facility module
	if project_data["Type"] == "Clays":
		material_refining.add_target_comp(target = "rom_ore_feed", composition = rom_comp, 
											target_step_id = project_data["Initial Concentration Target Step"], propagate = True)
		material_refining.add_target_comp(target = "brine_post_polishing", composition = project_data["Intermediate Concentration"], 
											target_step_id = project_data["Intermediate Concentration Target Step-Before"], propagate = False) 
		lithium_extraction.add_target_comp(target = "brine_post_polishing", composition = project_data["Intermediate Concentration"],
											target_step_id = project_data["Intermediate Concentration Target Step-After"], propagate = True)
	elif project_data["Type"] == "Lepidolite":
		material_refining.add_target_comp(target = "rom_ore_feed", composition = rom_comp, 
											target_step_id = project_data["Initial Concentration Target Step"], propagate = True)
		material_refining.add_target_comp(target = "roaster_feed", composition = project_data["Intermediate Concentration"], 
											target_step_id = project_data["Intermediate Concentration Target Step-Before"], propagate = False) 
		material_refining.add_target_comp(target = "roaster_feed", composition = project_data["Intermediate Concentration"],
											target_step_id = project_data["Intermediate Concentration Target Step-After"], propagate = True)
		
		# TEMPORARY HOLD 
		lithium_extraction.add_target_comp(target = "brine_post_polishing", composition = project_data["Intermediate Concentration"],
											target_step_id = "precipitation_step", propagate = True)

	
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
	
	# print("\nReagents:")
	# pprint(sc.get_total_reagents())
	# print("\nUtilities:")
	# pprint(sc.get_total_utilities())
	# print("\nLabor:")
	# pprint(sc.get_step_labor())
	# print("\nStep Production volumes:", sc.get_detailed_pvs())
	# print("\nCosts at each step:")
	# pprint(sc.get_step_costs(transp=True,detail=2))
	
	# print(sc.get_detailed_inputs())
	# print(sc.get_step_constituents())
	# print("\nAmount of lithium in each step:", sc.get_constituent_amount_at_steps("Li"))
	# print("\nAmount of lithium carbonate in each step:",sc.get_constituent_amount_at_steps("Li2CO3"))
	# print(sc.get_step_reagent_usage())
	# pprint(sc.get_step_utilities_detailed())
	# sc.plot_tot_steps_costs(view="opex",detail=3)
	# sc.plot_tot_steps_costs(view="opex",detail=2)
	# sc.plot_tot_steps_costs(view="variable",detail=3)
	# sc.plot_tot_steps_costs(view="variable",detail=2)
	# sc.plot_tot_steps_impacts()


	# helpers.update_machines(sc,"conservative")
	# summary_conservative = sc.update_apv(target_pv,recalc=True)
	# summary["conservative"] = summary_conservative
	# pprint(summary_conservative)
	# helpers.update_machines(sc,"optimistic")
	# summary_optimistic = sc.update_apv(target_pv,recalc=True)
	# summary["optimistic"] = summary_optimistic
	# pprint(summary_optimistic)


	# sc.plot_total_cc()

	return summary 

def compare_projects(projects,projects_data,transp_data,loc_data,machine_data,material_data):
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
				'avg_var_cost': sub_value['avg_var_cost'],
				'avg_co2': sub_value['avg_co2']
			}
	pprint(extracted_data)

	# helpers.plot_project_summaries(project_summaries)

if __name__ == '__main__':
	data_folder = "./interm-data/"

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
	# projects = ["Jianxiawo"]
	# projects = ["Thacker Pass"]
	projects = ["Jianxiawo","Silver Peak","Thacker Pass"]

	compare_projects(projects,projects_data,transp_data,loc_data,machine_data,material_data)


















