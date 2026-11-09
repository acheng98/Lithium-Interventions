import os

FIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),"Raw Figures/Current")
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","Supplementary Data File.xlsx")

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
PATHWAY_COLORS = { 
	"Silver Peak": "#4292c6",
	"Thacker Pass": "#08519c",
	"Jianxiawo": "#d62728",
}
TORNADO_STYLES = {
	"conservative": {"edgecolor": "black", "linewidth": 0.8},
	"optimistic":   {"edgecolor": "white", "linewidth": 0.8},
}