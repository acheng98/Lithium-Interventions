from helpers import safe_float, load_csv, build_steps_dict, build_locations_dict, build_projects_dict, parse_keys_string
from supply_chain import SupplyChain
from facility import Facility
from production_step import ProductionStep
from transportation import Transportation, TransportRoute

import pandas as pd
from collections import defaultdict
from copy import deepcopy

# Probably should incorporate this into 'from_table'
def import_steps(fac,steps_dict):
	steps = []
	for step_name in reversed(list(steps_dict.keys())):
		step_vars = steps_dict[step_name]
		step = ProductionStep.from_table(facility=fac, step_vars=step_vars)
		steps.append(step.step_name)

	fac.topo_order()
	# print("Ingested steps:", list(reversed(steps)))
	return fac

def lithium_evaporation(sc,facility_steps,locations,transp_data,transports,chems,material_costs,brine_factors):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", material_costs = material_costs,
							sinks=["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"])
	import_steps(lithium_extraction,facility_steps[2])
	lithium_extraction.update_location(locations[1],locations_dict[locations[1]]) # Assume lithium extraction plant is adjacent to concentrated brine facility
	sc.add_facility(lithium_extraction)

	# Concentrated Brine facility 	
	conc_brine = Facility(fac_id="Concentrated Brine", material_costs = material_costs,
						sinks = ["landfill","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"])

	import_steps(conc_brine,facility_steps[1])
	conc_brine.update_location(locations[1],locations_dict[locations[1]]) 
	sc.add_facility(conc_brine)

	# Evaporation ponds 'facility' 
	evap_ponds = Facility(fac_id="Evaporation Ponds", material_costs = material_costs,
						sinks = ["landfill","atmosphere"]) # Potassium?
	import_steps(evap_ponds,facility_steps[0])
	evap_ponds.update_location(locations[0],locations_dict[locations[0]])

	products = {"concentrated_lithium_brine": 1}

	# Transportation
	if transports[0] is None: 
		# In certain locations - namely Silver Peak - brine is processed on-site with the ponds
		sc.add_facility(evap_ponds, next_fac=conc_brine, products=products)
	elif len(transports[0]) > 0: 
		transps = []
		for transport in transports[0]: 
			brine_trucks = Transportation("Brine transport via truck",transp_data,transport[0],distance=transport[1])
		brine_truck_route = TransportRoute("Brine transport",[brine_trucks])
		sc.add_facility(evap_ponds, next_fac=conc_brine, products=products, transport_route=brine_truck_route)

	# Fix Chemistries
	evap_ponds.add_target_comp(target = "concentrated_lithium_brine", composition = chems[1], target_step_id = "2", propagate = True)
	evap_ponds.add_target_comp(target = "raw_brine_from_ground", composition = chems[0], target_step_id = "1", propagate = True)
	conc_brine.add_target_comp(target = "concentrated_lithium_brine", composition = chems[1], target_step_id = "1", propagate = True)
	lithium_extraction.add_target_comp(target = "brine_post_polishing", 
		composition = conc_brine.fwd[2].primary_outputs["brine_post_polishing"]["constituents"], # Would be nice to make a get function for this
		target_step_id = "1", propagate = True
		)

	# Set conversion factor for yield from ponds
	evap = evap_ponds.fwd[1]
	evap.set_conversion_factor("concentrated_lithium_brine",brine_factors["Pond Recovery Efficiency"],change_yield=True)

	return sc 

def clay_lepidolite(sc,facility_steps,locations,transp_data,transports,chems,material_costs,densities,mining_factors):
	# Pregnant Solution Processing facility
	lithium_extraction = Facility(fac_id="Lithium Extraction", material_costs = material_costs,
							sinks=["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"])
	import_steps(lithium_extraction,facility_steps[2])
	lithium_extraction.update_location(locations[1],locations_dict[locations[1]]) # Assume lithium extraction is adjacent to leaching plant 
	sc.add_facility(lithium_extraction)

	# Communition and Leaching facility 
	material_refining = Facility(fac_id="Material Refining", material_costs = material_costs,
						sinks = ["tailings","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"])
	import_steps(material_refining,facility_steps[1])
	material_refining.update_location(locations[1],locations_dict[locations[1]])
	sc.add_facility(material_refining, next_fac =lithium_extraction)

	# Transportation
	transps = []
	for transport in transports[0]: 
		transps.append(Transportation("Ore transport via truck",transp_data,transport[0],distance=transport[1]))
	ore_truck_route = TransportRoute("Ore transport",transps)

	# Mining 'facility' 
	material_extraction = Facility(fac_id="Mining", material_costs = material_costs,
						sinks = ["landfill","atmosphere","waste_pile"])
	import_steps(material_extraction,facility_steps[0])
	material_extraction.update_location(locations[0],locations_dict[locations[0]])

	rho_bank  = densities[0]
	swell_factor = mining_factors["Swell Factor"]
	dilution = mining_factors["Dilution"] # Apply dilution directly to chemical composition instead
	strip_ratio = mining_factors["Strip Ratio"]
	rho_loose = rho_bank / swell_factor
	loss = mining_factors["Loss"]
	
	composition = deepcopy(chems[0])
	if not mining_factors["Composition_ROM"]: # If the reported grade is not the grade at ROM, need to dilute
		composition["Li"] = composition["Li"] * (1 - dilution) # Apply dilution to composition - may need to apply to other minerals as well, or increase their makeup

	if mining_factors["Powder Factor"] in ["","-",None]: # We do *not* have blasting
		# Update initial and final chemical compositions for extraction facility
		material_extraction.add_target_comp(target = "raw_material", composition = chems[0], target_step_id = "1", propagate = False)
		material_extraction.add_target_comp(target = "rom_ore_feed", composition = composition, target_step_id = "1", propagate = False)

		loading = material_extraction.fwd[0]
		loading.set_conversion_factor("raw_material",1/rho_loose)	
	else:
		# Update initial and final chemical compositions for extraction facility
		material_extraction.add_target_comp(target = "raw_material", composition = chems[0], target_step_id = "1", propagate = True)
		material_extraction.add_target_comp(target = "rom_ore_feed", composition = composition, target_step_id = "2", propagate = False)

		# Get second/last step and add yield
		loading = material_extraction.fwd[1]
		loading.set_conversion_factor("blasted_rock",1/rho_loose)	
		
	# Get conversion factor from physical volume moved to tonnes diluted ore 
	loading.set_conversion_factor("rom_ore_feed",1-loss,change_yield=True)
	loading.set_conversion_factor("rom_ore_feed",rho_loose * 1/(1+strip_ratio)) # get from ore --> total moved (ore + waste)
	loading.set_conversion_factor("waste",rho_loose * (strip_ratio + loss)/(1+strip_ratio)) # (calculate waste = strip ratio + loss)

	# Update initial and final chemical compositions for each subsequent facility module
	material_refining.add_target_comp(target = "rom_ore_feed", composition = composition, target_step_id = "1", propagate = True)

	interm_chem = chems[1]["Li"]
	# material_refining.add_target_comp(target = "purified_Li_solution", composition = ) don't have this intermediate composition yet 
	lithium_extraction.add_target_comp()
	# material_extraction.add_target_comp(target = "excavated_ore", composition = chems[0], target_step_id = "2", propagate = True) <-- target acid leaching

	products = {"rom_ore_feed": 1}
	sc.add_facility(material_extraction, next_fac=material_refining, products=products, transport_route=ore_truck_route)	

	return sc 

def evaluate_project(project_data, material_costs, locations_dict, transp_data, data_folder):

	project_type = project_data["Type"]
	sc = SupplyChain()

	if project_type == "Brine-Evaporative":
		facility_steps = []
		for k in ("Pathway 1","Pathway 2"):
			facility_steps.append(build_steps_dict(load_csv(data_folder+project_data[k])))
		facility_steps.append(build_steps_dict(load_csv(data_folder+"Solution Processing")))

		locations = [project_data[k] for k in ("Location 1","Location 2")]

		if project_data["Transport 1"] is not None:
			transports = [parse_keys_string(project_data["Transport 1"])]
		else:
			transports = [None]

		chem_strings = ["Initial Concentration","Intermediate Concentration"]
		chems = [dict(parse_keys_string(project_data[string])) for string in chem_strings]
		
		densities = [project_data["Initial Density"],project_data["Intermediate Density"]] # not needed for now - would affect conversion factors. 
		brine_factors = {"Pond Recovery Efficiency": project_data["Pond Recovery Efficiency"],
						}
		sc = lithium_evaporation(sc,facility_steps,locations,transp_data,transports,chems,material_costs,brine_factors)
	elif project_type == "Brine-DLE":
		pass 
	elif project_type == "Spodumene":
		pass
	elif project_type in ["Clays","Lepidolite"]:
		facility_steps = []
		for k in ("Pathway 1","Pathway 2"):
			facility_steps.append(build_steps_dict(load_csv(data_folder+project_data[k])))
		facility_steps.append(build_steps_dict(load_csv(data_folder+"Solution Processing")))

		locations = [project_data[k] for k in ("Location 1","Location 2")]
		transports = [parse_keys_string(project_data[k]) for k in ["Transport 1"]]

		chem_strings = ["Initial Concentration","Intermediate Concentration"]
		chems = [dict(parse_keys_string(project_data[string])) for string in chem_strings]
		
		densities = [project_data["Initial Density"],project_data["Intermediate Density"]]
		mining_factors = {"Strip Ratio": project_data["Strip Ratio"],
						"Dilution": project_data["Dilution"],
						"Loss": project_data["Loss"],
						"Swell Factor": project_data["Swell Factor"],
						"Powder Factor": project_data["Powder Factor"],
						"Composition_ROM": project_data["ROM feed?"]
						}
		sc = clay_lepidolite(sc,facility_steps,locations,transp_data,transports,chems,material_costs,densities,mining_factors)
	else:
		raise ValueError(f"Project type '{project_type}' not defined.")

	# for target_pv in target_pvs:
	target_pv = project_data["Production Volume (Tonnes LCE / Year)"] # convert to kg
	print(sc.update_apv(target_pv))
	print(sc.get_detailed_pvs())
	print(sc.get_step_constituents())
	print(sc.get_step_reagent_usage())
	# print(sc.get_detailed_pvs())
	sc.plot_tot_steps_costs()
	# sc.plot_tot_steps_impacts()

	# sc.plot_unit_cc()
	# sc.plot_total_cc()

if __name__ == '__main__':
	data_folder = "./data/"

	# Material Costs #
	material_costs_df = pd.read_csv(data_folder+"Material Costs.csv", dtype=str).fillna("")
	# Assumes first column is material name; *fourth* column is converted unit cost
	material_costs = {
		str(row[0]): safe_float(row[3])
		for row in material_costs_df.itertuples(index=False, name=None)
		if pd.notna(row[0]) and pd.notna(row[3])
	}

	# Locational data
	locational_data_df = pd.read_csv(data_folder+"Locational Data.csv", dtype=str).fillna("") 
	header_ld = list(locational_data_df.columns)
	rows_ld = locational_data_df.values.tolist()
	locational_data = [header_ld] + rows_ld # as lists
	locations_dict = build_locations_dict(locational_data)

	# Transportation data
	transp_data_df = pd.read_csv(data_folder+"Transportation Data.csv", dtype=str).fillna("") 

	# Project-Specific Data
	projects_data_df = pd.read_csv(data_folder+"Project-Specific Data.csv", dtype=str).fillna("") 
	projects_data = build_projects_dict(projects_data_df)

	################
	# Pick project #
	################
	project_data = projects_data["Salar de Atacama-SQM"]

	evaluate_project(project_data,material_costs,locations_dict,transp_data_df,data_folder)


















