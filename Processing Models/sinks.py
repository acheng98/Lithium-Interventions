from helpers import build_data_dict
from facility import ReagentFacility

SINK_REQUIRED = {
	"tailings": ("route", "location", "storage", "s_in", "s_final", "rho_s", "x_hyd"),
	"wastewater": ("cost",),
	"waste_rock": ("cost",),
	"other": ("cost",),
}

def load_sink_params(sc, data_folder):
	table = build_data_dict(data_folder, "Sink Data", skip_rows=["notes", "sources", "cost_unit"])
	tail = build_data_dict(data_folder, "Tailings Model Inputs")
	sc.sink_names = list(table)
	sc.sink_params, sc.wastewater_params, sc.flat_sinks = {}, {}, {}
	for name, row in table.items():
		kind = row.get("kind")
		if kind not in SINK_REQUIRED:
			raise ValueError(f"Sink Data '{name}': kind '{kind}' not in {sorted(SINK_REQUIRED)}")
		missing = [k for k in SINK_REQUIRED[kind] if row.get(k) is None]
		if missing:
			raise ValueError(f"Sink Data '{name}' ({kind}) missing {missing}")
		if kind == "tailings":
			sc.sink_params[name] = dict(row, train=list((row.get("train") or {}).items()))
		elif kind == "wastewater":
			sc.wastewater_params[name] = row
		else:
			sc.flat_sinks[name] = row
	sc.s_ceil, sc.stage, sc.placement, sc.tsf_opex = {}, {}, {}, {}
	for col, row in tail.items():
		for ph in ("cry", "hyd"):
			if (row.get("s_ceil") or {}).get(ph) is not None:
				sc.s_ceil[(col, ph)] = row["s_ceil"][ph]
				sc.stage[(col, ph)] = tuple(row[k][ph] for k in ("C_m", "c_w", "E_m", "e_w"))
		if row.get("tsf_opex") is not None:
			sc.placement[col] = (row["placement_cost"], row["placement_elec"])
			sc.tsf_opex[col] = row["tsf_opex"]
	register_sink_labels(sc)

def sink_s_out(sc, name):
	p = sc.sink_params[name]
	return p["train"][-1][1] if p["train"] else p["s_in"]

def tailings_handling(sc):
	def mw(s):
		return (1.0 - s) / s

	def s_ceil(mech, x):
		w = x * mw(sc.s_ceil[(mech, "hyd")]) + (1.0 - x) * mw(sc.s_ceil[(mech, "cry")])
		return 1.0 / (1.0 + w)

	def stage_coef(mech, x):
		h = sc.stage[(mech, "hyd")]
		c = sc.stage[(mech, "cry")]
		return tuple(x * h[i] + (1.0 - x) * c[i] for i in range(4))

	def ds_per_m3(w_s, rho_s, rho_w=1.0):
		rho_mix = 1.0 / (w_s / rho_s + (1.0 - w_s) / rho_w)
		return w_s * rho_mix

	sc.topo_order()
	ep = next(f.elec_price for f in sc.rev if not isinstance(f, ReagentFacility))
	sc.sink_elec = {}

	for name, p in sc.sink_params.items():
		x = p["x_hyd"]
		s_k = p.get("s_feed") or p["s_in"]
		dew_c, dew_e = 0.0, 0.0
		for mech, s_out in p["train"]:
			cap = s_ceil(mech, x)
			if s_out > cap + 1e-9:
				raise ValueError(f"{name}: {mech} s_out {s_out:.3f} exceeds ceiling {cap:.3f} at x_hyd={x}")
			if s_out <= s_k + 1e-9:
				raise ValueError(f"{name}: {mech} s_out {s_out:.3f} not above inlet {s_k:.3f}")
			dW = 1.0 / s_k - 1.0 / s_out
			C_m, c_w, E_m, e_w = stage_coef(mech, x)
			dew_c += C_m + c_w * dW
			dew_e += E_m + e_w * dW
			s_k = s_out
		if p["s_final"] < s_k - 1e-9:
			raise ValueError(f"{name}: s_final {p['s_final']} below mechanical outlet {s_k:.3f}")

		if p.get("placement_cost") is not None:
			pl_c, pl_e = p["placement_cost"], p["placement_elec"]
		else:
			pl_c, pl_e = sc.placement[p["route"]]
		loc = sc.loc_data[p["location"]]
		cost_tds = dew_c + pl_c
		elec = dew_e + pl_e
		if p["route"] == "offsite_gate":
			cost_tds += loc[f"tailings_{p['gate_class']}_cost"] / s_k
		elif p["storage"]:
			cost_tds += sc.tsf_opex[p["route"]]
			rdf = p.get("rho_dry_final")
			cost_tds += loc["tailings_storage_cost"] / (rdf if rdf else ds_per_m3(s_k, p["rho_s"]))
		cost_tds += elec * ep
		sc.register_sink_cost(name, cost_tds * ds_per_m3(p["s_in"], p["rho_s"]))
		sc.sink_elec[name] = elec

	sc.sink_scope_two = set(sc.sink_params)
	for fac in sc.rev:
		efs = fac.impact_factors.get("electricity") or {}
		fac.scope_two_sinks = sc.sink_scope_two
		fac.impact_factors = dict(fac.impact_factors, **{
			name: {cat: sc.sink_elec[name] * ds_per_m3(p["s_in"], p["rho_s"]) * f
				for cat, f in efs.items()}
			for name, p in sc.sink_params.items()})

	for name, p in {**sc.wastewater_params, **sc.flat_sinks}.items():
		sc.register_sink_cost(name, p["cost"])

def sink_override_map(nested):
	return {(step_id, coproduct): sink
		for step_id, coproducts in (nested or {}).items()
		for coproduct, sink in (coproducts or {}).items() if sink}

def apply_sink_overrides(sc,sink_overrides):
	if not sink_overrides:
		return
	for (step_id,coproduct),sink in sink_overrides.items():
		found = False
		for fac in sc.rev:
			step = fac.steps.get(step_id)
			if step is None:
				continue
			if coproduct not in step.secondary_outputs:
				raise KeyError(f"{step_id}: no secondary output '{coproduct}'")
			step.secondary_outputs[coproduct]["sink"] = sink
			found = True
		if not found:
			raise KeyError(f"sink override target step '{step_id}' not found")

def register_sink_labels(sc):
	labels = {"waste_pile": "Waste Rock Pile"}
	labels.update({name: "Wastewater Treatment" for name in sc.wastewater_params})
	labels.update({name: "Tailings Management" for name in sc.sink_params})
	sc.sink_labels = labels
	sc.sink_stack_order = ["Waste Rock Pile", "Tailings Management", "Wastewater Treatment"]







