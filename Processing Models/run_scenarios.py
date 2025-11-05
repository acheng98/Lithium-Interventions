from helpers import build_steps_dict, build_locations_dict
from supply_chain import SupplyChain
from facility import Facility
from production_step import ProductionStep

import pandas as pd

# Incorporate this into 'from_table'
def import_steps(fac,steps_dict):
	steps = []
	for step_name in reversed(list(steps_dict.keys())):
		step_vars = steps_dict[step_name]
		step = ProductionStep.from_table(facility=fac, step_vars=step_vars)
		steps.append(step.step_name)

	# print("Ingested steps:", list(reversed(steps)))
	return fac

def lithium_evaporation(material_costs, locations_dict, steps_dicts, target_pvs, interm_chem, transportation = None):
	sc = SupplyChain()

	# Concentrated Brine facility 
	# UPDATE TO TAKE IN LOCATIONAL DATA
	conc_brine = Facility(fac_id="Concentrated Brine",apv=10000, material_costs = material_costs, #Does the APV need to be defined here
						sinks = ["landfill","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
						dpy=300, spd=3, hps=8, ub=2/3, pb=1/3, dr=0.10, wage=18, elec=0.15, build=3000,
						crp=6, brp=20, aux_equip=0.10, maint=0.10, fixed_over=0.35, enpt=0.03)

	import_steps(conc_brine,steps_dicts[1])
	conc_brine.add_target_comp(target = "concentrated_lithium_brine", composition = interm_chem, target_step_id = "1", propagate = True)
	sc.add_facility(conc_brine)

	# Transportation
	# transp = Facility(
						# )
	# sc.add_facility()

	# Evaporation ponds 'facility' 
	evap_ponds = Facility(fac_id="Evaporation Ponds",apv=10000, material_costs = material_costs, #Does the APV need to be defined here
						sinks = ["landfill","atmosphere"], # Potassium? 
						dpy=300, spd=3, hps=8, ub=2/3, pb=1/3, dr=0.10, wage=18, elec=0.15, build=3000,
						crp=6, brp=20, aux_equip=0.10, maint=0.10, fixed_over=0.35, enpt=0.03)
	import_steps(evap_ponds,steps_dicts[0])

	products = {"concentrated_lithium_brine": 1}
	sc.add_facility(evap_ponds, next_fac=conc_brine, products=products)

	evap_ponds.add_target_comp(target = "concentrated_lithium_brine", composition = interm_chem, target_step_id = "2", propagate = True)
	
	for target_pv in target_pvs:
		sc.update_apv(target_pv)
		# sc.plot_tot_steps_in_facs_costs(ylims=[0,4*10**6])

	print(evap_ponds.calculate_environmental_impacts())
	# sc.plot_unit_cc()
	# sc.plot_total_cc()

if __name__ == '__main__':
	folder = "./data/"
	material_costs_path = "Material Costs.csv"
	locational_data_path = "Locational Data.csv"
	input_data_paths = ["Brine Evaporation.csv","Concentrated Brine.csv"] # Put these in order of upstream --> downstream
	# input_data_paths = ["Brine Evaporation.csv"]
	# input_data_paths = ["Concentrated Brine.csv"]

	# Material Costs
	material_costs_df = pd.read_csv(folder+material_costs_path, dtype=str).fillna("") 

	# Assumes first column is material name and second column is cost
	material_costs = {
		str(row[0]): float(row[1])
		for row in material_costs_df.itertuples(index=False, name=None)
		if pd.notna(row[0]) and pd.notna(row[1])
	}

	# Locational Data
	locational_data_df = pd.read_csv(folder+locational_data_path, dtype=str).fillna("") 

	# Convert the DataFrame into list of lists, with header row first
	header_ld = list(locational_data_df.columns)
	rows_ld = locational_data_df.values.tolist()
	locational_data = [header_ld] + rows_ld # as lists

	# Build dictionary using your existing function
	locations_dict = build_locations_dict(locational_data)

	steps_dicts = []
	for path in input_data_paths:
		# Step data
		input_data_df = pd.read_csv(folder+path, dtype=str).fillna("") 

		# Convert the DataFrame into list of lists, with header row first
		header_id = list(input_data_df.columns)
		rows_id = input_data_df.values.tolist()
		input_data = [header_id] + rows_id

		# Input_data is the nested list loaded from CSV
		steps_dict = build_steps_dict(input_data)
		steps_dicts.append(steps_dict)

	# Add input composition to the facility.
	# Salar de Atacama rough composition
	concentrated_brine_6pct_li_mg_per_L = {
		"Li": 81200.0,				# mg/L  5.8-6 wt% reported by Albemarle and others
		# "Cl": 414800.0,			# mg/L  (major counter-ion from LiCl)
		"Na": 20000.0,				# mg/L  (residual Na after earlier halite precipitation)
		"Mg": 10000.0,				# mg/L  (some Mg may remain or be partially removed earlier)
		"K": 8000.0,				# mg/L
		"B": 5000.0,				# mg/L
		"SO4": 5000.0,				# mg/L
		"Ca": 1000.0,				# mg/L
		# "Sr": 500.0,				# mg/L
		# "Rb": 50.0,				# mg/L
		# "Other_ions": 10450.0,	# mg/L  (trace/other salts to bring total tos measured TDS)
		# "TDS": 556000.0			# mg/L  (total dissolved salts reported for concentrated ponds)
	}
	# pvs = [10500*i for i in range(1,31)]
	pvs = [210000]
	# pvs = [21000]
	# pvs = [21000,105000,210000]

	lithium_evaporation(material_costs,locations_dict,steps_dicts,pvs,concentrated_brine_6pct_li_mg_per_L)


















