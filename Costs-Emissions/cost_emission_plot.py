import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

# Creating the DataFrame
df = pd.read_csv("./test_set.csv")

# Mapping materials to specific markers
marker_dict = {"Brine": "o", "Spodumene": "s"}

# Define a custom high-contrast palette
custom_palette = {
    "Chile": "#E69F00",
    "Australia": "#56B4E9",
    "Argentina": "#009E73",
    "Zimbabwe": "#D55E00",  # High-contrast orange
    "China": "#0072B2",  # High-contrast blue
    "USA": "#F0E442"
}

# Mapping materials to specific markers
marker_dict = {"Brine": "o", "Spodumene": "s"}

# Define a custom high-contrast palette
custom_palette = {
    "Chile": "#E69F00",
    "Australia": "#56B4E9",
    "Argentina": "#009E73",
    "Zimbabwe": "#D55E00",  # High-contrast orange
    "China": "#0072B2",  # High-contrast blue
    "USA": "#F0E442"
}

# Create scatter plot
plt.figure(figsize=(10, 6))
scatter = sns.scatterplot(
    data=df, 
    x="Cost ($/ton LCE)", 
    y="Carbon Footprint (kg_CO2/kg_LCE)", 
    size="Volume (tons LCE)", 
    hue="Location", 
    style="Material",
    markers=marker_dict, 
    sizes=(50, 500), 
    edgecolor='black',
    alpha=0.7,
    palette=custom_palette
)

# Manually create legend - legend broke
# 1. LOCATION LEGEND
location_labels = df['Location'].unique()
location_handles = [
    Line2D([], [], marker='o', linestyle='', color=custom_palette[loc], label=loc, markersize=8)
    for loc in location_labels
]
legend_location = plt.legend(
    handles=location_handles,
    title="Location",
    loc='upper left',
    bbox_to_anchor=(1.05, 1),
    frameon=True,
    fancybox=True,
    borderpad=1
)
plt.gca().add_artist(legend_location)  # keep this legend when adding the next

# 2. MATERIAL LEGEND
material_handles = [
    Line2D([], [], marker=marker_dict[mat], linestyle='', color='gray', label=mat, markersize=8)
    for mat in marker_dict
]
legend_material = plt.legend(
    handles=material_handles,
    title="Material",
    loc='upper left',
    bbox_to_anchor=(1.05, 0.65),
    frameon=True,
    fancybox=True,
    borderpad=1
)
plt.gca().add_artist(legend_material)

# 3. VOLUME LEGEND
volume_levels = [40, 120, 200]
volume_handles = [
    plt.scatter([], [], s=level*2, label=f'{level} tons', color='gray', alpha=0.4, edgecolors='black')
    for level in volume_levels
]
legend_volume = plt.legend(
    handles=volume_handles,
    title="Volume (tons LCE)",
    loc='upper left',
    bbox_to_anchor=(1.05, 0.46),
    frameon=True,
    fancybox=True,
    borderpad=1
)
plt.gca().add_artist(legend_volume)

# Add horizontal reference lines
reference_lines = {
    2.7: "Generic Brine-Low (Kelly et al. 2021)",
    3.1: "Generic Brine-High (Kelly et al. 2021)",
    20.4: "Generic Spodumene  (Kelly et al. 2021)",
    8.9: "US Clays-Low (Iyer and Kelly 2024)",
    16.6: "US Clays-High (Iyer and Kelly 2024)",
    12: "US Brines (Iyer and Kelly 2024)"
}
for y_val, label in reference_lines.items():
    plt.axhline(y=y_val, color='gray', linestyle='dashed', alpha=0.5)
    plt.text(df["Cost ($/ton LCE)"].max() * 0.995, y_val, label, verticalalignment='center',
        horizontalalignment='right', fontsize=9, color='gray')
# Labels and title
plt.xlabel("Cost ($/ton LCE)")
plt.ylabel("Carbon Footprint (kg CO2/kg LCE)")
plt.title("Lithium Extraction: Cost vs. Carbon Footprint")

# Set origin to (0, 0)
plt.xlim(left=0)
plt.ylim(bottom=0)

# plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, linestyle='--', linewidth=0.5, color='gray', alpha=0.3)
plt.tight_layout(rect=[0, 0, 0.8, 1])
plt.show()
