from helpers import safe_float, load_csv, build_steps_dict, build_locations_dict, build_projects_dict, parse_transport_string
from supply_chain import SupplyChain
from facility import Facility
from production_step import ProductionStep
from transportation import Transportation, TransportRoute

import pandas as pd
from collections import defaultdict

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
	# Concentrated Brine facility 
	conc_brine = Facility(fac_id="Concentrated Brine", material_costs = material_costs,
						sinks = ["landfill","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"])

	import_steps(conc_brine,facility_steps[0])
	conc_brine.add_target_comp(target = "concentrated_lithium_brine", composition = chems[1], target_step_id = "1", propagate = True)
	conc_brine.update_location(locations[0],locations_dict[locations[0]]) 
	sc.add_facility(conc_brine)

	# Transportation
	brine_trucks = Transportation("Brine transport via truck",transp_data,"liquid_tanker_truck_diesel",distance=250)
	brine_truck_route = TransportRoute("Brine transport",[brine_trucks])

	# Evaporation ponds 'facility' 
	evap_ponds = Facility(fac_id="Evaporation Ponds", material_costs = material_costs,
						sinks = ["landfill","atmosphere"]) # Potassium?
	import_steps(evap_ponds,facility_steps[1])
	evap_ponds.update_location(locations[1],locations_dict[locations[1]])

	products = {"concentrated_lithium_brine": 1}
	sc.add_facility(evap_ponds, next_fac=conc_brine, products=products, transport_route=brine_truck_route)

	evap_ponds.add_target_comp(target = "concentrated_lithium_brine", composition = chems[1], target_step_id = "2", propagate = True)
	evap_ponds.add_target_comp(target = "raw_brine_from_ground", composition = chems[0], target_step_id = "1", propagate = True)

	evap = evap_ponds.fwd[1]
	evap.set_conversion_factor("concentrated_lithium_brine",brine_factors["Pond Recovery Efficiency"],change_yield=True)

	return sc 

def clay_lepidolite(sc,facility_steps,locations,transp_data,transports,chems,material_costs,densities,mining_factors):
	# Refining facility
	material_refining = Facility(fac_id="Material Refining", material_costs = material_costs,
						sinks = ["landfill","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"])

	import_steps(material_refining,facility_steps[1])
	material_refining.add_target_comp(target = "excavated_ore", composition = chems[1], target_step_id = "1", propagate = True)
	material_refining.update_location(locations[1],locations_dict[locations[1]]) 
	sc.add_facility(material_refining)

	# Transportation
	# ore_trucks = Transportation("Ore transport via truck",transp_data," ?? ",distance=250)
	# ore_truck = TransportRoute("Ore transport",[ore_trucks])

	# Mining 'facility' 
	material_extraction = Facility(fac_id="Mining", material_costs = material_costs,
						sinks = ["landfill","atmosphere","waste_pile"])
	import_steps(material_extraction,facility_steps[0])
	if mining_factors["Powder Factor"] in ["","-"]: # We do *not* have blasting
		pass
	else:
		# Get second/last step and add yield
		loading = material_extraction.fwd[1]
		
		# Get conversion factor from physical volume moved to tonnes diluted ore 
		cf = densities[0] / mining_factors["Swell Factor"] * (1+mining_factors["Dilution"])
		loading.set_conversion_factor("excavated_ore",1-mining_factors["Loss"],change_yield=True)
		loading.set_conversion_factor("excavated_ore",cf*(1+mining_factors["Strip Ratio"])) # load ore + waste
		loading.set_conversion_factor("waste",cf*mining_factors["Strip Ratio"]) # define waste

		# Get conversion factor from tonnes material blasted to physical volume moved 

	material_extraction.update_location(locations[0],locations_dict[locations[0]])

	products = {"excavated_ore": 1}
	sc.add_facility(material_extraction, next_fac=material_refining, products=products)#, transport_route=haul_truck)

	material_extraction.add_target_comp(target = "excavated_ore", composition = chems[1], target_step_id = "2", propagate = True)
	material_extraction.add_target_comp(target = "raw_material", composition = chems[0], target_step_id = "1", propagate = True)

	return sc 

def evaluate_project(project_data, material_costs, locations_dict, transp_data, data_folder):

	project_type = project_data["Type"]
	sc = SupplyChain()

	if project_type == "Brine-Evaporative":
		facility_steps = [
			build_steps_dict(load_csv(data_folder+project_data[k]))
			for k in ("Pathway 2", "Pathway 1")
		]
		locations = [project_data[k] for k in ("Location 2", "Location 1")]
		transports = [parse_transport_string(project_data[k]) for k in ["Transport 1"]]

		init_chem = {"Li": project_data["Initial Average Li Concentration"],
						"K": project_data["Initial Average K Concentration"],
						"Mg": project_data["Initial Average Mg Concentration"],
						"Ca": project_data["Initial Average Ca Concentration"],
						"Na": project_data["Initial Average Na Concentration"],
						"B": project_data["Initial Average B Concentration"],
						"SO4": project_data["Initial Average SO4 Concentration"],
					}
		interm_chem = {"Li": project_data["Intermediate Average Li Concentration"],
						"K": project_data["Intermediate Average K Concentration"],
						"Mg": project_data["Intermediate Average Mg Concentration"],
						"Ca": project_data["Intermediate Average Ca Concentration"],
						"Na": project_data["Intermediate Average Na Concentration"],
						"B": project_data["Intermediate Average B Concentration"],
						"SO4": project_data["Intermediate Average SO4 Concentration"],
					}
		chems = [init_chem,interm_chem]
		densities = [project_data["Initial Density"],project_data["Intermediate Density"]] # not needed for now - would affect conversion factors. 
		brine_factors = {"Pond Recovery Efficiency": project_data["Pond Recovery Efficiency"],
						}
		sc = lithium_evaporation(sc,facility_steps,locations,transp_data,transports,chems,material_costs,brine_factors)
	elif project_type == "Brine-DLE":
		pass 
	elif project_type == "Spodumene":
		pass
	elif project_type in ["Clays","Lepidolite"]:
		facility_steps = [
			build_steps_dict(load_csv(project_data[k]))
			for k in ("Pathway 2", "Pathway 1")
		]
		locations = [project_data[k] for k in ("Location 2", "Location 1")]
		transports = [parse_transport_string(project_data[k]) for k in ["Transport 1"]]
		init_chem = {"Li": project_data["Initial Average Li Concentration"],
						"K": project_data["Initial Average K Concentration"],
						"Mg": project_data["Initial Average Mg Concentration"],
						"Ca": project_data["Initial Average Ca Concentration"],
						"Na": project_data["Initial Average Na Concentration"],
						"Si": project_data["Initial Average Si Concentration"],
						"Rb": project_data["Initial Average Rb Concentration"],
						"F": project_data["Initial Average F Concentration"],
					}
		interm_chem = {"Li": project_data["Intermediate Average Li Concentration"],
						"K": project_data["Intermediate Average K Concentration"],
						"Mg": project_data["Intermediate Average Mg Concentration"],
						"Ca": project_data["Intermediate Average Ca Concentration"],
						"Na": project_data["Intermediate Average Na Concentration"],
						"Si": project_data["Intermediate Average Si Concentration"],
						"Rb": project_data["Intermediate Average Rb Concentration"],
						"F": project_data["Intermediate Average F Concentration"],
					}
		chems = [init_chem,interm_chem]
		densities = [project_data["Initial Density"],project_data["Intermediate Density"]] # not needed for now
		mining_factors = {"Strip Ratio": project_data["Strip Ratio"],
						"Dilution": project_data["Dilution"],
						"Loss": project_data["Loss"],
						"Swell Factor": project_data["Swell Factor"],
						"Powder Factor": project_data["Powder Factor"]
						}
		sc = clay_lepidolite(sc,facility_steps,locations,transp_data,transports,chems,material_costs,densities,mining_factors)
	else:
		raise ValueError(f"Project type '{project_type}' not defined.")

	# for target_pv in target_pvs:
	target_pv = project_data["Production Volume (Tonnes LCE / Year)"]
	sc.update_apv(target_pv)
	print(sc.get_detailed_pvs())
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


















