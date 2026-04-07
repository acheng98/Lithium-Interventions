# compare_tornado.py
# Independent two-facet tornado comparison script.
# Input: tornado_data dicts from two projects (same structure as used by plot_tornado in helpers.py)
# Usage: run directly or import compare_tornado() into any notebook/script.

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


# ── colour palette (matches helpers.py) ─────────────────────────────────────
COL_CONSERVATIVE = "#f28e2b"
COL_OPTIMISTIC   = "#4e79a7"
MID_LABEL_BG     = "white"


def _get_entries(tornado_data: dict, metric: str) -> list[tuple[str, float, float]]:
	"""Return [(label, opt_val, con_val), ...] sorted by range descending."""
	entries = []
	for name, vals in tornado_data.get("machines", {}).items():
		entries.append((
			f"Machine:\n{name}",
			vals["optimistic"][metric],
			vals["conservative"][metric],
		))
	for name, vals in tornado_data.get("materials", {}).items():
		entries.append((
			f"Material:\n{name}",
			vals["optimistic"][metric],
			vals["conservative"][metric],
		))
	entries.sort(key=lambda x: abs(x[2] - x[1]), reverse=True)
	return entries


def compare_tornado(
	tornado_data_a: dict,
	tornado_data_b: dict,
	label_a: str = "Project A",
	label_b: str = "Project B",
	metric: str = "avg_opex",
	top_n: int = 3,
	xlab: str | None = None,
	suptitle: str | None = None,
	figsize: tuple = (9, 6),
	shared_x: bool = True,
	bar_height: float = 0.75,
	midpoint_label_fontsize: int = 7,
	show: bool = True,
) -> tuple:
	"""
	Plot a two-facet tornado comparison between two projects.

	Parameters
	----------
	tornado_data_a / _b : dict
		tornado_data dicts from each project's run_scenarios output.
		Expected keys: "baseline", "machines", "materials"
		Each machine/material entry must have "conservative" and "optimistic" sub-dicts
		with the chosen metric value.
	label_a / _b : str
		Display titles for each facet.
	metric : str
		Which metric to plot, e.g. "avg_opex", "avg_var_cost", "avg_co2".
	top_n : int
		Number of top drivers to show per facet (default 3).
	shared_x : bool
		If True, both axes share the same x-axis limits (default True).
	"""

	baseline_a = tornado_data_a["baseline"][metric]
	baseline_b = tornado_data_b["baseline"][metric]

	raw_a = _get_entries(tornado_data_a, metric)[:top_n]
	raw_b = _get_entries(tornado_data_b, metric)[:top_n]

	# Reverse so largest range is at top of the chart
	entries_a = raw_a[::-1]
	entries_b = raw_b[::-1]

	# ── compute global x limits if shared ────────────────────────────────────
	def _xlims(entries, baseline):
		all_vals = [v for _, o, c in entries for v in (o, c)] + [baseline]
		pad = (max(all_vals) - min(all_vals)) * 0.12
		return min(all_vals) - pad, max(all_vals) + pad

	xlim_a = _xlims(entries_a, baseline_a)
	xlim_b = _xlims(entries_b, baseline_b)

	if shared_x:
		global_xlim = (min(xlim_a[0], xlim_b[0]), max(xlim_a[1], xlim_b[1]))
		xlim_a = xlim_b = global_xlim

	# ── figure ────────────────────────────────────────────────────────────────
	fig, axes = plt.subplots(
		2, 1,
		figsize=figsize,
		sharex=shared_x,
		sharey=False,
		gridspec_kw={"hspace": 0.45},
	)

	def _draw_facet(ax, entries, baseline, title, xlim):
		labels   = [e[0] for e in entries]
		opt_vals = np.array([e[1] for e in entries])
		con_vals = np.array([e[2] for e in entries])

		y = np.arange(len(entries))

		# Conservative bars (extend right / worse)
		ax.barh(
			y, con_vals - baseline, left=baseline,
			height=bar_height,
			color=COL_CONSERVATIVE, label="Conservative", zorder=3,
		)
		# Optimistic bars (extend left / better)
		ax.barh(
			y, opt_vals - baseline, left=baseline,
			height=bar_height,
			color=COL_OPTIMISTIC, label="Optimistic", zorder=3,
		)

		ax.set_yticks(y)
		ax.set_yticklabels(labels, fontsize=9, linespacing=1.2)		

		# Midpoint line
		ax.axvline(baseline, color="black", linewidth=1.1, zorder=4)

		# # Midpoint label at top of plot
		# ax.text(
		# 	baseline, len(entries) - 0.5 + 0.45,
		# 	f"Midpoint:\n${baseline:,.0f}/t",
		# 	ha="center", va="bottom",
		# 	fontsize=midpoint_label_fontsize,
		# 	color="black",
		# 	bbox=dict(boxstyle="round,pad=0.2", fc=MID_LABEL_BG, ec="none", alpha=0.8),
		# 	zorder=5,
		# )

		# Value labels on each bar end
		# for i, (lbl, opt, con) in enumerate(entries):
		# 	# Optimistic (left end)
		# 	ax.text(
		# 		opt, i,
		# 		f"  ${opt:,.0f}" if opt > baseline else f"${opt:,.0f}  ",
		# 		ha="left" if opt > baseline else "right",
		# 		va="center", fontsize=7, color="black", zorder=5,
		# 	)
		# 	# Conservative (right end)
		# 	ax.text(
		# 		con, i,
		# 		f"  ${con:,.0f}" if con > baseline else f"${con:,.0f}  ",
		# 		ha="left" if con > baseline else "right",
		# 		va="center", fontsize=7, color="black", zorder=5,
		# 	)

		ax.set_title(title, fontsize=12, fontweight="bold", pad=8)
		ax.set_xlabel(xlab or f"Avg. Cost per tonne Li₂CO₃ ($/t)", fontsize=10)
		ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
		ax.tick_params(axis="x", labelsize=8)
		ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
		ax.spines[["top", "right"]].set_visible(False)

	_draw_facet(axes[0], entries_a, baseline_a, label_a, xlim_a)
	_draw_facet(axes[1], entries_b, baseline_b, label_b, xlim_b)

	# ── shared legend ─────────────────────────────────────────────────────────
	from matplotlib.patches import Patch
	legend_handles = [
		Patch(facecolor=COL_CONSERVATIVE, label="Conservative"),
		Patch(facecolor=COL_OPTIMISTIC,   label="Optimistic"),
	]
	fig.legend(
		handles=legend_handles,
		loc="lower center",
		ncol=2,
		frameon=True,
		facecolor="white",
		edgecolor="none",
		fontsize=10,
		bbox_to_anchor=(0.5, -0.04),
	)

	if suptitle:
		fig.suptitle(suptitle, fontsize=14, fontweight="bold", y=1.02)

	plt.tight_layout()
	if show:
		plt.show()
	return fig, axes


# ── Example usage ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

	tornado_data_lepidolite = {'baseline': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}, 'machines': {'acid_leach_circuit': {'conservative': {'avg_opex': 8553.559954010658, 'avg_var_cost': 8122.8477813644095, 'avg_co2': 16857.342932583884}, 'optimistic': {'avg_opex': 8500.499430128544, 'avg_var_cost': 8115.521300732347, 'avg_co2': 16828.43833838359}}, 'attrition_scrubber': {'conservative': {'avg_opex': 8561.835821472161, 'avg_var_cost': 8140.163625812013, 'avg_co2': 16925.65778689511}, 'optimistic': {'avg_opex': 8462.432263635785, 'avg_var_cost': 8072.261294836912, 'avg_co2': 16657.768001791464}}, 'blasting_generic': {'conservative': {'avg_opex': 8549.336851435562, 'avg_var_cost': 8139.7352242979605, 'avg_co2': 16854.27324276226}, 'optimistic': {'avg_opex': 8495.508374171952, 'avg_var_cost': 8097.587217708499, 'avg_co2': 16827.37880046232}}, 'classifier_generic': {'conservative': {'avg_opex': 8541.409714134972, 'avg_var_cost': 8121.22442089046, 'avg_co2': 16850.938414767388}, 'optimistic': {'avg_opex': 8510.292378166861, 'avg_var_cost': 8117.013449647154, 'avg_co2': 16834.325197441154}}, 'crushing_cycle': {'conservative': {'avg_opex': 8560.676495542146, 'avg_var_cost': 8124.5251988723485, 'avg_co2': 16863.960717412152}, 'optimistic': {'avg_opex': 8492.429946646675, 'avg_var_cost': 8114.100349327251, 'avg_co2': 16822.832369323507}}, 'drying_packaging_generic': {'conservative': {'avg_opex': 8530.818468171456, 'avg_var_cost': 8123.684379999308, 'avg_co2': 16865.232735898004}, 'optimistic': {'avg_opex': 8513.526783450354, 'avg_var_cost': 8115.342152422986, 'avg_co2': 16822.50622161229}}, 'excavation_loading_generic': {'conservative': {'avg_opex': 8835.428017465421, 'avg_var_cost': 8408.348125919105, 'avg_co2': 16979.22033925597}, 'optimistic': {'avg_opex': 8397.66265743846, 'avg_var_cost': 8005.069475908855, 'avg_co2': 16786.925076793912}}, 'mechanical_dewatering': {'conservative': {'avg_opex': 8529.150425087848, 'avg_var_cost': 8118.989904012218, 'avg_co2': 16842.122749123417}, 'optimistic': {'avg_opex': 8518.267262829098, 'avg_var_cost': 8118.513313649186, 'avg_co2': 16840.242494232283}}, 'multi_stage_ccd_thickening': {'conservative': {'avg_opex': 8582.859821603857, 'avg_var_cost': 8128.608488421392, 'avg_co2': 16880.070202080802}, 'optimistic': {'avg_opex': 8491.322245274709, 'avg_var_cost': 8112.858648342636, 'avg_co2': 16817.933583005655}}, 'precipitator': {'conservative': {'avg_opex': 8528.053727119952, 'avg_var_cost': 8121.766402553275, 'avg_co2': 16851.050246172133}, 'optimistic': {'avg_opex': 8514.77802265365, 'avg_var_cost': 8115.7204028542865, 'avg_co2': 16830.601797052448}}, 'staged_neutralization': {'conservative': {'avg_opex': 8558.79636727712, 'avg_var_cost': 8141.509099536002, 'avg_co2': 16930.96597973042}, 'optimistic': {'avg_opex': 8496.871487789866, 'avg_var_cost': 8104.381296920248, 'avg_co2': 16784.48854778846}}, 'thickener_generic': {'conservative': {'avg_opex': 8557.296289426193, 'avg_var_cost': 8130.626986743246, 'avg_co2': 16888.033626515702}, 'optimistic': {'avg_opex': 8496.859601283411, 'avg_var_cost': 8109.686896698219, 'avg_co2': 16805.42031793473}}, 'wash_purify_combo': {'conservative': {'avg_opex': 8521.04752343073, 'avg_var_cost': 8118.792076854718, 'avg_co2': 16841.214423271696}, 'optimistic': {'avg_opex': 8520.484772392816, 'avg_var_cost': 8118.591349422355, 'avg_co2': 16840.592980616646}}}, 'materials': {'collectors': {'conservative': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}, 'optimistic': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}}, 'depressants': {'conservative': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}, 'optimistic': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}}, 'explosives': {'conservative': {'avg_opex': 8528.798782102207, 'avg_var_cost': 8126.814853230358, 'avg_co2': 16840.82602161229}, 'optimistic': {'avg_opex': 8514.122244093378, 'avg_var_cost': 8112.1383152215285, 'avg_co2': 16840.82602161229}}, 'flocculant': {'conservative': {'avg_opex': 8599.145110057672, 'avg_var_cost': 8197.161181185824, 'avg_co2': 16908.52069315798}, 'optimistic': {'avg_opex': 8474.46870270885, 'avg_var_cost': 8072.484773837, 'avg_co2': 16791.69428182742}}, 'lime': {'conservative': {'avg_opex': 8911.694924286767, 'avg_var_cost': 8509.710995414916, 'avg_co2': 21185.823515075444}, 'optimistic': {'avg_opex': 8129.595375463395, 'avg_var_cost': 7727.611446591545, 'avg_co2': 13625.52787644955}}, 'limestone': {'conservative': {'avg_opex': 8536.118676969996, 'avg_var_cost': 8134.134748098147, 'avg_co2': 16845.98386397726}, 'optimistic': {'avg_opex': 8505.171622780163, 'avg_var_cost': 8103.187693908315, 'avg_co2': 16836.312909542936}}, 'neutralizing_agent': {'conservative': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}, 'optimistic': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}}, 'process_water': {'conservative': {'avg_opex': 9393.57847038639, 'avg_var_cost': 8991.594541514543, 'avg_co2': 16840.82602161229}, 'optimistic': {'avg_opex': 8271.235629728992, 'avg_var_cost': 7869.251700857139, 'avg_co2': 16840.82602161229}}, 'soda_ash': {'conservative': {'avg_opex': 9050.553960938587, 'avg_var_cost': 8648.570032066737, 'avg_co2': 17804.296587182303}, 'optimistic': {'avg_opex': 8135.256923647075, 'avg_var_cost': 7733.272994775225, 'avg_co2': 15877.355456042276}}, 'sodium_sulfate': {'conservative': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}, 'optimistic': {'avg_opex': 8520.645149875081, 'avg_var_cost': 8118.661221003231, 'avg_co2': 16840.82602161229}}, 'sulfuric_acid': {'conservative': {'avg_opex': 10673.583815611191, 'avg_var_cost': 10271.599886739345, 'avg_co2': 17778.11548113983}, 'optimistic': {'avg_opex': 7824.745783172497, 'avg_var_cost': 7422.7618543006465, 'avg_co2': 15840.470681977327}}}}
	tornado_data_clay = {'baseline': {'avg_opex': 10053.915166265126, 'avg_var_cost': 9223.249368763687, 'avg_co2': 22003.40886936426}, 'machines': {'blasting_generic': {'conservative': {'avg_opex': 10072.889485031292, 'avg_var_cost': 9231.21720074868, 'avg_co2': 22023.74581195453}, 'optimistic': {'avg_opex': 10040.077207996837, 'avg_var_cost': 9215.281536778693, 'avg_co2': 21983.071926773988}}, 'classifier_flotation': {'conservative': {'avg_opex': 10149.759316159309, 'avg_var_cost': 9243.18939609567, 'avg_co2': 22139.47225340607}, 'optimistic': {'avg_opex': 9996.224502458022, 'avg_var_cost': 9210.180981619958, 'avg_co2': 21913.177362052324}}, 'crushing_cycle': {'conservative': {'avg_opex': 10126.99652179411, 'avg_var_cost': 9232.765249961856, 'avg_co2': 22077.45511292761}, 'optimistic': {'avg_opex': 10002.507058488805, 'avg_var_cost': 9215.84812783178, 'avg_co2': 21945.817346592772}}, 'drying_packaging_generic': {'conservative': {'avg_opex': 10064.826114569594, 'avg_var_cost': 9228.424343741886, 'avg_co2': 22036.303840792832}, 'optimistic': {'avg_opex': 10045.949759436302, 'avg_var_cost': 9219.51541766736, 'avg_co2': 21980.51846936426}}, 'excavation_loading_generic': {'conservative': {'avg_opex': 10227.378579774128, 'avg_var_cost': 9360.301499162759, 'avg_co2': 22212.709903485007}, 'optimistic': {'avg_opex': 9986.332628564473, 'avg_var_cost': 9169.291698318684, 'avg_co2': 21921.891624417698}}, 'high_energy_grinding_mill': {'conservative': {'avg_opex': 10152.766765212817, 'avg_var_cost': 9310.859815002068, 'avg_co2': 22685.134955027163}, 'optimistic': {'avg_opex': 9992.833339348806, 'avg_var_cost': 9170.91066062128, 'avg_co2': 21596.143935072134}}, 'mechanical_dewatering': {'conservative': {'avg_opex': 10118.404695211753, 'avg_var_cost': 9225.425214413153, 'avg_co2': 22020.339849644628}, 'optimistic': {'avg_opex': 10035.94139482364, 'avg_var_cost': 9222.270238221428, 'avg_co2': 21995.789928238093}}, 'precipitator': {'conservative': {'avg_opex': 10056.197285205466, 'avg_var_cost': 9224.230328899577, 'avg_co2': 22009.99688099763}, 'optimistic': {'avg_opex': 10052.092399615985, 'avg_var_cost': 9222.311390101579, 'avg_co2': 21996.82085773089}}, 'solid_liquid_separation': {'conservative': {'avg_opex': 10060.29712024084, 'avg_var_cost': 9223.654414749837, 'avg_co2': 22006.56066719781}, 'optimistic': {'avg_opex': 10050.34789802628, 'avg_var_cost': 9223.097476518882, 'avg_co2': 22002.22694517668}}, 'staged_neutralization': {'conservative': {'avg_opex': 10058.934770736352, 'avg_var_cost': 9225.093150818158, 'avg_co2': 22017.755952124116}, 'optimistic': {'avg_opex': 10050.792616352168, 'avg_var_cost': 9222.097004979643, 'avg_co2': 21994.441942639347}}, 'sulfate_roasting_train_lepidolite': {'conservative': {'avg_opex': 10729.449286846851, 'avg_var_cost': 9661.500390712961, 'avg_co2': 24747.35632312391}, 'optimistic': {'avg_opex': 9673.055174639407, 'avg_var_cost': 9003.741884208039, 'avg_co2': 20628.462878726044}}, 'wash_purify_combo': {'conservative': {'avg_opex': 10054.284577661372, 'avg_var_cost': 9223.35829849383, 'avg_co2': 22004.047253931894}, 'optimistic': {'avg_opex': 10053.77015166328, 'avg_var_cost': 9223.19118138388, 'avg_co2': 22003.025838623682}}, 'water_leach': {'conservative': {'avg_opex': 10074.825987342596, 'avg_var_cost': 9229.260597270317, 'avg_co2': 22050.184242117186}, 'optimistic': {'avg_opex': 10042.243034128698, 'avg_var_cost': 9220.516992169767, 'avg_co2': 21982.147336294747}}}, 'materials': {'collectors': {'conservative': {'avg_opex': 10094.55262452193, 'avg_var_cost': 9263.886827020493, 'avg_co2': 22003.40886936426}, 'optimistic': {'avg_opex': 10013.27770800832, 'avg_var_cost': 9182.611910506883, 'avg_co2': 22003.40886936426}}, 'depressants': {'conservative': {'avg_opex': 10068.025394826516, 'avg_var_cost': 9237.35959732508, 'avg_co2': 22003.40886936426}, 'optimistic': {'avg_opex': 10042.626983416014, 'avg_var_cost': 9211.961185914575, 'avg_co2': 22003.40886936426}}, 'explosives': {'conservative': {'avg_opex': 10067.47945166815, 'avg_var_cost': 9236.813654166714, 'avg_co2': 22003.40886936426}, 'optimistic': {'avg_opex': 10040.350880862099, 'avg_var_cost': 9209.685083360662, 'avg_co2': 22003.40886936426}}, 'flocculant': {'conservative': {'avg_opex': 10054.17625768948, 'avg_var_cost': 9223.510460188041, 'avg_co2': 22004.17438942047}, 'optimistic': {'avg_opex': 10053.758511410513, 'avg_var_cost': 9223.092713909075, 'avg_co2': 22002.853266813236}}, 'lime': {'conservative': {'avg_opex': 10191.425655429917, 'avg_var_cost': 9360.75985792848, 'avg_co2': 24295.250355444125}, 'optimistic': {'avg_opex': 9893.486262239536, 'avg_var_cost': 9062.820464738099, 'avg_co2': 20307.446169665163}}, 'limestone': {'conservative': {'avg_opex': 10053.915166265126, 'avg_var_cost': 9223.249368763687, 'avg_co2': 22003.40886936426}, 'optimistic': {'avg_opex': 10053.915166265126, 'avg_var_cost': 9223.249368763687, 'avg_co2': 22003.40886936426}}, 'neutralizing_agent': {'conservative': {'avg_opex': 10076.450280264215, 'avg_var_cost': 9245.784482762778, 'avg_co2': 22003.40886936426}, 'optimistic': {'avg_opex': 10029.331405538847, 'avg_var_cost': 9198.665608037409, 'avg_co2': 22003.40886936426}}, 'process_water': {'conservative': {'avg_opex': 10229.166143963555, 'avg_var_cost': 9398.500346462117, 'avg_co2': 22003.40886936426}, 'optimistic': {'avg_opex': 9948.764579646066, 'avg_var_cost': 9118.098782144629, 'avg_co2': 22003.40886936426}}, 'soda_ash': {'conservative': {'avg_opex': 10645.854096723206, 'avg_var_cost': 9815.188299221767, 'avg_co2': 23944.192247915347}, 'optimistic': {'avg_opex': 9756.328381553958, 'avg_var_cost': 8925.662584052521, 'avg_co2': 20386.089387238357}}, 'sodium_sulfate': {'conservative': {'avg_opex': 10665.072895886422, 'avg_var_cost': 9834.407098384987, 'avg_co2': 27351.039003550606}, 'optimistic': {'avg_opex': 9748.336301454478, 'avg_var_cost': 8917.670503953039, 'avg_co2': 19711.5673832844}}, 'sulfuric_acid': {'conservative': {'avg_opex': 10059.0367830831, 'avg_var_cost': 9228.370985581661, 'avg_co2': 22005.61628621281}, 'optimistic': {'avg_opex': 10050.84219617434, 'avg_var_cost': 9220.176398672902, 'avg_co2': 22001.05292562799}}}}

	fig, axes = compare_tornado(
		tornado_data_a = tornado_data_lepidolite,
		tornado_data_b = tornado_data_clay,
		metric         = "avg_opex",
		top_n          = 3,
		shared_x       = True,       # set False to let each facet auto-scale
		suptitle       = "Top-3 Cost Sensitivity Drivers — Project Comparison",
	)