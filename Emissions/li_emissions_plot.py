import pandas as pd
import plotly.express as px
import numpy as np
from io import StringIO
import random

# Set the seed value
random.seed(40)


def main(plot_type):
	df = pd.read_csv("./li_emissions.csv")

	# Filter out non-allowed pathways
	all_pathways = ["Argentina", "Australia-China", "Brazil-China", "Canada", "Chile", 
		"China", "Finland", "Germany", "Mexico", "Peru", "US", "Zimbabwe-China"]
	focus_pathways = ["Argentina", "Australia-China", "Canada", "Chile", "China", "US"]
	allowed_pathways = focus_pathways
	df = df[df['Pathway'].isin(allowed_pathways)]

	# Combine geothermal brines into regular brines
	df['Source'] = df['Source'].replace('Geothermal Brines-DLE', 'Brine-DLE')

	# Calculate the number of rows per Source
	source_counts = df['Source'].value_counts().to_dict()
	df['Source_labeled'] = df['Source'].map(lambda s: f"{s} (n={source_counts[s]})")
	
	# REPLACE WITH VIOLIN PLOT? 

	# Add jitter to Source for visual separation (numerically encoded)
	source_to_num = {s: i for i, s in enumerate(df['Source_labeled'].unique())}
	df['Source_jitter'] = df['Source_labeled'].map(source_to_num) + np.random.uniform(-0.20, 0.20, size=len(df))

	# Plot
	if plot_type == "violin":
		fig = px.violin(
			df,
			x="Source",
			y="Emissions Factor",
			color="Source",
			box=True,
    		points="all",
			hover_data=["Source", "Pathway", "Emissions Factor"]
		)

		fig.update_layout(
			title="Lithium Emissions Factors by Mineral Source and Production Pathway"
			)
	else:
		fig = px.scatter(
			df,
			x="Source_jitter",
			y="Emissions Factor",
			symbol="Pathway",
			color="Citation",
			hover_data=["Source", "Pathway", "Emissions Factor"],
			color_discrete_sequence=px.colors.qualitative.Light24
		)

		fig.update_traces(marker=dict(size=15))
		fig.update_layout(
			title="Lithium Emissions Factors by Mineral Source and Production Pathway (Jittered)"
			)

	# Update x-axis with category names
	fig.update_layout(
		xaxis=dict(
			tickmode="array",
			tickvals=list(source_to_num.values()),
			ticktext=list(source_to_num.keys()),
			title="Source"
		),
		yaxis_title="Emissions Factor (kg CO₂-eq/kg Li)",
	)

	fig.show()

if __name__ == '__main__':
	main("")