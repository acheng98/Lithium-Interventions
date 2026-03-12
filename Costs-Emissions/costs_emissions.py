import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_num(x):
    """Parse currency/numeric strings to float, returning NaN on failure or zero."""
    if x is None:
        return np.nan
    s = str(x).strip().replace(",", "").replace("$", "")
    if s.lower() in {"", "na", "n/a", "null", "-", "none"}:
        return np.nan
    try:
        v = float(s)
        return np.nan if v == 0 else v   # treat 0 as missing
    except ValueError:
        return np.nan


def nanrange(arr):
    """Return (min, max) of finite values, or (NaN, NaN) if none."""
    finite = arr[np.isfinite(arr)]
    if len(finite) == 0:
        return np.nan, np.nan
    return finite.min(), finite.max()


def nice_tick(data_range, n_ticks_target=6):
    """
    Return a 'nice' tick interval that divides data_range into roughly
    n_ticks_target intervals, choosing from a set of round multiples.
    """
    raw = data_range / n_ticks_target
    magnitude = 10 ** np.floor(np.log10(raw))
    residual = raw / magnitude
    if residual < 1.5:
        nice = 1
    elif residual < 3.5:
        nice = 2
    elif residual < 7.5:
        nice = 5
    else:
        nice = 10
    return nice * magnitude


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

# Metadata columns — never treated as numeric data
METADATA_COLS = {"Project", "Company", "Location", "Material", "Dimension"}

# Our Study columns — same names used for both Cost and Emissions rows.
# Edit here if you rename them in the CSV.
OUR_COLS = {
    "low":  "Our Study-Low",
    "mid":  "Our Study-Midpoint",
    "high": "Our Study-High",
}

# Literature columns are detected dynamically at load time:
# every column that isn't in METADATA_COLS or OUR_COLS is treated as a
# literature source. No manual updates needed when new studies are added.

# Colour palette by material type
MATERIAL_COLORS = {
    "Brine":      "#1f77b4",   # blue
    "Brine-DLE":  "#aec7e8",   # light blue
    "Clay":       "#d62728",   # red
    "Spodumene":  "#2ca02c",   # green
    "Lepidolite": "#9467bd",   # purple
}
DEFAULT_COLOR = "#7f7f7f"


# ---------------------------------------------------------------------------
# Main plotting function
# ---------------------------------------------------------------------------

def plot_cost_vs_emissions(
    csv_path: str,
    title: str = "Cost vs. Emissions by project",
    figsize: tuple = (8, 8),          # square keeps 45° property
    save_path: str | None = None,
    our_alpha: float = 0.55,           # opacity of Our Study box fill
    lit_alpha: float = 0.18,           # opacity of literature box fill
    our_edge_alpha: float = 0.90,
    lit_edge_alpha: float = 0.45,
):
    # ------------------------------------------------------------------
    # Load & parse
    # ------------------------------------------------------------------
    df = pd.read_csv(csv_path)

    numeric_cols = [c for c in df.columns if c not in METADATA_COLS]
    for c in numeric_cols:
        df[c] = df[c].map(parse_num)

    # Dynamically identify literature columns: numeric cols minus Our Study cols
    our_col_set = set(OUR_COLS.values())
    lit_cols = [c for c in numeric_cols if c not in our_col_set]

    cost_df  = df[df["Dimension"] == "Cost"].copy()
    emiss_df = df[df["Dimension"] == "Emissions"].copy()

    # ------------------------------------------------------------------
    # Build per-project records
    # ------------------------------------------------------------------
    records = []

    # Only plot projects that have Our Study data in BOTH dimensions
    our_vals = list(OUR_COLS.values())
    cost_our_mask  = cost_df[our_vals].notna().any(axis=1)
    emiss_our_mask = emiss_df[our_vals].notna().any(axis=1)

    cost_with_our  = set(cost_df.loc[cost_our_mask,  "Project"])
    emiss_with_our = set(emiss_df.loc[emiss_our_mask, "Project"])
    both_projects  = cost_with_our & emiss_with_our

    for project in sorted(both_projects):
        crow = cost_df[cost_df["Project"] == project].iloc[0]
        erow = emiss_df[emiss_df["Project"] == project].iloc[0]

        material = crow["Material"]

        # Our Study box corners (same column names for cost and emissions)
        c_lo  = crow[OUR_COLS["low"]]
        c_mid = crow[OUR_COLS["mid"]]
        c_hi  = crow[OUR_COLS["high"]]
        e_lo  = erow[OUR_COLS["low"]]
        e_mid = erow[OUR_COLS["mid"]]
        e_hi  = erow[OUR_COLS["high"]]

        # Literature ranges — all lit cols present in each row
        lit_cost_vals  = crow[[c for c in lit_cols if c in crow.index]].to_numpy(dtype=float)
        lit_emiss_vals = erow[[c for c in lit_cols if c in erow.index]].to_numpy(dtype=float)

        lit_c_lo, lit_c_hi = nanrange(lit_cost_vals)
        lit_e_lo, lit_e_hi = nanrange(lit_emiss_vals)

        records.append(dict(
            project=project,
            material=material,
            c_lo=c_lo, c_mid=c_mid, c_hi=c_hi,
            e_lo=e_lo, e_mid=e_mid, e_hi=e_hi,
            lit_c_lo=lit_c_lo, lit_c_hi=lit_c_hi,
            lit_e_lo=lit_e_lo, lit_e_hi=lit_e_hi,
        ))

    if not records:
        raise ValueError("No projects found with Our Study data in both cost and emissions.")

    # ------------------------------------------------------------------
    # Determine axis limits with equal-interval 45° scaling
    # ------------------------------------------------------------------
    all_c = [r[k] for r in records for k in
             ("c_lo", "c_mid", "c_hi", "lit_c_lo", "lit_c_hi") if np.isfinite(r[k])]
    all_e = [r[k] for r in records for k in
             ("e_lo", "e_mid", "e_hi", "lit_e_lo", "lit_e_hi") if np.isfinite(r[k])]

    c_max_data = max(all_c)
    e_max_data = max(all_e)

    # Choose nice tick intervals, then force both axes to the same interval
    # count so grid squares are visually square on a square figure (45° lines).
    tick_c = nice_tick(c_max_data)
    tick_e = nice_tick(e_max_data)

    n_c = int(np.ceil(c_max_data / tick_c))
    n_e = int(np.ceil(e_max_data / tick_e))
    n_intervals = max(n_c, n_e)   # pad the shorter axis to match

    c_max = tick_c * n_intervals
    e_max = tick_e * n_intervals

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=figsize)

    legend_handles = []
    seen_materials = set()

    for r in records:
        color = MATERIAL_COLORS.get(r["material"], DEFAULT_COLOR)
        rgb   = plt.matplotlib.colors.to_rgb(color)

        # ---- Literature bounding box (transparent) -------------------
        if (np.isfinite(r["lit_c_lo"]) and np.isfinite(r["lit_c_hi"]) and
                np.isfinite(r["lit_e_lo"]) and np.isfinite(r["lit_e_hi"])):

            rect_lit = mpatches.FancyBboxPatch(
                (r["lit_c_lo"], r["lit_e_lo"]),
                r["lit_c_hi"] - r["lit_c_lo"],
                r["lit_e_hi"] - r["lit_e_lo"],
                boxstyle="square,pad=0",
                linewidth=1.2,
                edgecolor=(*rgb, lit_edge_alpha),
                facecolor=(*rgb, lit_alpha),
                zorder=2,
            )
            ax.add_patch(rect_lit)

        # ---- Our Study bounding box (opaque) -------------------------
        if (np.isfinite(r["c_lo"]) and np.isfinite(r["c_hi"]) and
                np.isfinite(r["e_lo"]) and np.isfinite(r["e_hi"])):

            rect_our = mpatches.FancyBboxPatch(
                (r["c_lo"], r["e_lo"]),
                r["c_hi"] - r["c_lo"],
                r["e_hi"] - r["e_lo"],
                boxstyle="square,pad=0",
                linewidth=1.6,
                edgecolor=(*rgb, our_edge_alpha),
                facecolor=(*rgb, our_alpha),
                zorder=3,
            )
            ax.add_patch(rect_our)

        # ---- Central midpoint ----------------------------------------
        if np.isfinite(r["c_mid"]) and np.isfinite(r["e_mid"]):
            ax.scatter(
                r["c_mid"], r["e_mid"],
                color=color, s=70, zorder=5,
                edgecolors="white", linewidths=0.8,
            )

        # ---- Project label -------------------------------------------
        lx = r["c_mid"] if np.isfinite(r["c_mid"]) else (r["c_lo"] + r["c_hi"]) / 2
        ly = r["e_mid"] if np.isfinite(r["e_mid"]) else (r["e_lo"] + r["e_hi"]) / 2
        ax.annotate(
            r["project"],
            xy=(lx, ly), xytext=(-18, -15),
            textcoords="offset points",
            fontsize=8, color=color, zorder=6,
        )

        # ---- Legend entry (one per material type) --------------------
        if r["material"] not in seen_materials:
            seen_materials.add(r["material"])
            legend_handles.append(
                mpatches.Patch(facecolor=color, label=r["material"])
            )

    # ---- Shared legend proxies for box types -------------------------
    legend_handles += [
        mpatches.Patch(facecolor="gray", alpha=our_alpha,
                       edgecolor="gray", linewidth=1.6,
                       label="Our Study range \n(specific projects)"),
        mpatches.Patch(facecolor="gray", alpha=lit_alpha,
                       edgecolor="gray", linewidth=1.2,
                       label="Literature range"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",
               markersize=7, markeredgecolor="white", label="Our Study midpoint"),
    ]

    # ------------------------------------------------------------------
    # Axes formatting
    # ------------------------------------------------------------------
    ax.set_xlim(0, c_max)
    ax.set_ylim(0, e_max)

    ax.set_xticks(np.arange(0, c_max + tick_c * 0.01, tick_c))
    ax.set_yticks(np.arange(0, e_max + tick_e * 0.01, tick_e))

    ax.set_xlabel("Cost ($/t Li₂CO₃)", fontsize=11)
    ax.set_ylabel("Emissions (t CO₂e / t Li₂CO₃)", fontsize=11)
    ax.set_title(title, fontsize=12, pad=10)

    ax.grid(True, linestyle=":", alpha=0.4)
    # No set_aspect("equal") — 45° comes from equal interval count on a square figure.

    ax.legend(handles=legend_handles, loc="upper left", fontsize=8, framealpha=0.85)

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    plot_cost_vs_emissions(
        "reported_both.csv",
        save_path="cost_vs_emissions.png",
    )