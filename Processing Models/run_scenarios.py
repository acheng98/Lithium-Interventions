from helpers import build_steps_dict, build_locations_dict
from supply_chain import SupplyChain
from facility import Facility
from production_step import ProductionStep

import pandas as pd

def main (excel_path):
	# Material Costs
	material_costs_df = pd.read_excel(excel_path, sheet_name="Material Costs")
	material_costs_df = material_costs_df.fillna("") 

	# Assumes first column is material name and second column is cost
	material_costs = {
		str(row[0]): float(row[1])
		for row in material_costs_df.itertuples(index=False, name=None)
		if pd.notna(row[0]) and pd.notna(row[1])
	}

	print(material_costs)

	# Locational Data
	locational_data_df = pd.read_excel(excel_path, sheet_name="Locational Data", dtype=str)
	locational_data_df = locational_data_df.fillna("") 

	# Convert the DataFrame into list of lists, with header row first
	header_ld = list(locational_data_df.columns)
	rows_ld = locational_data_df.values.tolist()
	locational_data = [header_ld] + rows_ld # as lists

	# Build dictionary using your existing function
	locations_dict = build_locations_dict(locational_data)

	print(locations_dict)

	# Initialize facility
	fac = Facility(apv=10000, material_costs = material_costs,
					sinks = ["landfill","resin_regeneration","solvent_recovery","wastewater_treatment","atmosphere"],
					dpy=300, spd=3, hps=8, ub=2/3, pb=1/3, dr=0.10, wage=18, elec=0.15, build=3000,
					crp=6, brp=20, aux_equip=0.10, maint=0.10, fixed_over=0.35, enpt=0.03)

	# Step data
	input_data_df = pd.read_excel(excel_path, sheet_name="Concentrated Brine", dtype=str)
	input_data_df = input_data_df.fillna("") 

	# Convert the DataFrame into list of lists, with header row first
	header_id = list(locational_data_df.columns)
	rows_id = locational_data_df.values.tolist()
	input_data = [header_id] + rows_id

	# Input_data is the nested list loaded from CSV
	steps_dict = build_steps_dict(input_data)
	print(steps_dict.keys())

	# Build step objects into facility fac
	steps = []
	for step_name in reversed(list(steps_dict.keys())):
		step_vars = steps_dict[step_name]
		step = ProductionStep.from_table(facility=fac, step_vars=step_vars)
		steps.append(step.step_name)

	print("Ingested steps:", list(reversed(steps)))

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

	fac.add_input_comp(primary_input = "concentrated_lithium_brine", input_composition = concentrated_brine_6pct_li_mg_per_L, target_step_id = "1", propagate = True)

	for step in fac.steps.values():
		print(step.primary_inputs)
		print(step.secondary_inputs)

	print(fac.calculate_all(10000))

if __name__ == '__main__':
	main("Master Data File.xlsx")