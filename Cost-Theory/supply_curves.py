import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Data ──────────────────────────────────────────────────────────────────────
# (name, cost, capacity, type)  type: 'i'=incumbent, 'n'=new entrant
BASE = [
	('A', 25, 20, 'i'),
	('B', 35, 20, 'i'),
	('C', 50, 20, 'i'),
	('D', 65, 20, 'i'),
	('E', 75, 20, 'i'),
]
WITH_NEW = [
	('A',   25, 20, 'i'),
	('B',   35, 20, 'i'),
	('C',   50, 20, 'i'),
	('New', 55, 20, 'n'),
	('D',   65, 20, 'i'),
	('E',   75, 20, 'i'),
]

SCENARIOS = [
	{'producers': BASE,     'demand': 70,  'title': 'Status quo — low demand'},
	{'producers': WITH_NEW, 'demand': 70,  'title': 'New entrant — low demand'},
	{'producers': BASE,     'demand': 90, 'title': 'Status quo — high demand'},
	{'producers': WITH_NEW, 'demand': 90, 'title': 'New entrant — high demand'},
]

# ── Colors ────────────────────────────────────────────────────────────────────
C_INCUMBENT_COST = '#0F6E56'   # dark teal  — producer cost block
C_INCUMBENT_MG   = '#5DCAA5'   # bright teal — producer surplus band
C_NEW_COST       = '#854F0B'   # dark amber — new entrant cost block
C_NEW_MG         = '#EF9F27'   # bright amber — new entrant surplus band
C_DISPLACED      = '#B4B2A9'   # gray
C_PRICE          = '#E24B4A'   # red
C_DEMAND         = '#378ADD'   # blue
C_GRID           = '#EBEBEB'

def market_price(producers, demand):
	cum = 0
	for _, cost, cap, _ in producers:
		if cum + cap >= demand:
			return cost
		cum += cap
	return producers[-1][1]

def draw_panel(ax, producers, demand, price_annotation=None):
	price = market_price(producers, demand)
	ax.set_facecolor('white')

	# Grid
	for g in [25, 50, 75]:
		ax.axhline(g, color=C_GRID, linewidth=0.6, zorder=0)

	cum = 0
	for name, cost, cap, ptype in producers:
		x0, x1 = cum, cum + cap
		displaced = cum >= demand
		is_new = ptype == 'n'

		cost_color = C_DISPLACED if displaced else (C_NEW_COST if is_new else C_INCUMBENT_COST)

		# Cost block — solid, opaque fill from 0 to cost
		rect = mpatches.Rectangle(
			(x0, 0), cap, cost,
			facecolor=cost_color,
			edgecolor='white',
			linewidth=0.8,
			alpha=0.15 if displaced else 0.30,
			zorder=1,
		)
		ax.add_patch(rect)

		# Surplus band — vivid fill from cost up to market price
		if not displaced and cost < price:
			mg_color = C_NEW_MG if is_new else C_INCUMBENT_MG
			vol_in = min(cap, demand - cum)
			margin_rect = mpatches.Rectangle(
				(x0, cost), vol_in, price - cost,
				facecolor=mg_color,
				edgecolor='none',
				alpha=0.82,
				zorder=2,
			)
			ax.add_patch(margin_rect)

		# Top step line
		ax.plot([x0, x1], [cost, cost], color=cost_color,
			linewidth=2.4, alpha=1.0 if not displaced else 0.45, zorder=3)

		cum += cap

	# Vertical risers
	cum = 0
	for i, (name, cost, cap, ptype) in enumerate(producers[:-1]):
		x = cum + cap
		next_cost = producers[i + 1][1]
		cur_disp = cum >= demand
		nxt_disp = cum + cap >= demand
		rc = C_DISPLACED if (cur_disp or nxt_disp) else (
			C_NEW_COST if ptype == 'n' else C_INCUMBENT_COST)
		alpha = 0.45 if (cur_disp or nxt_disp) else 1.0
		ax.plot([x, x], [cost, next_cost], color=rc, linewidth=2.4, alpha=alpha, zorder=3)
		cum += cap

	# Demand line
	ax.axvline(demand, color=C_DEMAND, linewidth=1.5, linestyle=(0, (5, 4)), zorder=4)

	# Price line
	ax.axhline(price, color=C_PRICE, linewidth=1.8, linestyle=(0, (5, 4)), zorder=4)

	# Intersection dot
	ax.plot(demand, price, 'o', color=C_PRICE, markersize=5.5, zorder=5)

	# Price label on y-axis
	# ax.text(-1.5, price, f'${price}', color=C_PRICE,
	# 	fontsize=9, fontweight='bold', ha='right', va='center', zorder=6)

	# Price delta annotation (shown on right-column panels)
	if price_annotation is not None:
		delta, ref_price = price_annotation
		sign = '+' if delta > 0 else ''
		ax.annotate(
			f'{sign}{delta}/t vs\nno new entrant',
			xy=(demand + 1, price),
			xytext=(demand + 12, price + (8 if delta > 0 else -8)),
			fontsize=7.5,
			color=C_PRICE,
			ha='left', va='center',
			arrowprops=dict(arrowstyle='->', color=C_PRICE, lw=1.0),
			zorder=6,
		)

	# Axes
	total_supply = sum(c for _, _, c, _ in producers)
	ax.set_xlim(0, total_supply + 2)
	ax.set_ylim(0, 90)
	ax.set_xticks([])
	ax.set_yticks([])
	# ax.set_yticks([25, 50, 75])
	ax.tick_params(axis='y', labelsize=8, colors='#AAAAAA', length=0, pad=4)
	for spine in ax.spines.values():
		spine.set_visible(False)
	ax.spines['left'].set_visible(True)
	ax.spines['left'].set_color(C_GRID)
	ax.spines['left'].set_linewidth(0.6)

# ── Figure ────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(
	2, 2,
	figsize=(11, 7.5),
	facecolor='white',
)
fig.subplots_adjust(hspace=0.28, wspace=0.22, left=0.08, right=0.97, top=0.97, bottom=0.04)

# Compute price deltas: right panels show change vs left (status quo)
for row in range(2):
	scen_sq  = SCENARIOS[row * 2]       # left: status quo
	scen_ne  = SCENARIOS[row * 2 + 1]   # right: new entrant
	p_sq  = market_price(scen_sq['producers'],  scen_sq['demand'])
	p_ne  = market_price(scen_ne['producers'],  scen_ne['demand'])
	delta = p_ne - p_sq

	draw_panel(axes[row, 0], scen_sq['producers'],  scen_sq['demand'])
	draw_panel(axes[row, 1], scen_ne['producers'],  scen_ne['demand'])
		# price_annotation=(delta, p_sq))

out = './supply_curves_2x2.png'
fig.savefig(out, dpi=180, bbox_inches='tight', facecolor='white')
print('saved', out)









