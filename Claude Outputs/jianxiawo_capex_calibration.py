import sys,os,io,contextlib,copy
PM=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","Processing Models")); sys.path.insert(0,PM)
import run_scenarios as rs, helpers
from supply_chain import SupplyChain
df=os.path.join(PM,"data/Master Data File.xlsx"); rs.data_folder=df
P=helpers.build_data_dict(df,"Project-Specific Data"); T=helpers.build_data_dict(df,"Transportation Data",col=3)
L=helpers.build_locations_dict(df,"Locational Data")
M=helpers.build_data_dict(df,"Machine Blocks Data",skip_rows=["notes","sources","key_equation","machine_block_type"]); Mat=helpers.build_data_dict(df,"Material Data")
MINE={"blasting","excav_load"}; CRUSH={"crushing"}; ROAST={"sulfate_roasting"}
CRU=5500
for apv in (46000,75000,111000):
	pdj=copy.deepcopy(P["Jianxiawo"]); pdj["Production Volume"]=apv
	sc=SupplyChain(T,L,M,Mat)
	with contextlib.redirect_stdout(io.StringIO()): rs.evaluate_project(sc,pdj,df,detail=0,plot=0)
	for rank in ("optimistic","midpoint","conservative"):
		with contextlib.redirect_stdout(io.StringIO()):
			helpers.update_machines(sc,rank); helpers.update_materials(sc,pdj,rank); sc.update_apv(apv,recalc=True)
		e={st.step_id:(st.scaled_equip_cost or 0) for st in sc.get_steps(transp=False)}
		roast=e["sulfate_roasting"]
		for lab,excl in (("excl mining",MINE),("excl mining+crushing",MINE|CRUSH),("excl mining+crush+classify",MINE|CRUSH|{"classifying"})):
			other=sum(v for k,v in e.items() if k not in excl|ROAST)
			tgt=CRU*apv
			cf=(tgt-roast)/other
			print(f"APV {apv:>6} {rank:<12} {lab:<22} roast ${roast/1e6:6.1f}M other ${other/1e6:6.1f}M | intensity pre-cf ${(roast+other)/apv:,.0f}/t ; at 0.75 ${(roast+0.75*other)/apv:,.0f}/t ; CRU total ${tgt/1e6:,.0f}M -> implied cf {cf:.2f}")
