"""
Track D: interactive demo map. Real GPS trail + candidate sites + the
QUBO/QAOA-relevant chosen sensor placement, overlaid on one map.
"""
import sys
import ast

import folium
import pandas as pd

sys.path.insert(0, "scripts")
from build_qubo import load_sites, LAKE_BANZENA_SITE_ID

INDIVIDUAL_FILTER = "Salif Keita"
CHOSEN_SITES = [0, 2, 7]  # from build_qubo.py -- proxy QUBO and true max-coverage agree


def load_trail():
    df = pd.read_csv("data/elephant_gps_raw.csv")
    df = df[df["visible"].astype(str).str.lower() == "true"]
    df = df[df["individual-local-identifier"] == INDIVIDUAL_FILTER]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def main():
    trail = load_trail()
    sites = load_sites()
    dwell = pd.read_csv("data/dwell_sites_context.csv")

    center = [trail["location-lat"].mean(), trail["location-long"].mean()]
    m = folium.Map(location=center, zoom_start=8, tiles="OpenStreetMap")

    # Full GPS trail, downsampled for render weight (every 4th fix keeps the shape, cuts size ~4x)
    coords = list(zip(trail["location-lat"].iloc[::4], trail["location-long"].iloc[::4]))
    folium.PolyLine(coords, color="#4a7c59", weight=1.5, opacity=0.5,
                     tooltip=f"{INDIVIDUAL_FILTER} GPS trail, 2008-2014 ({len(trail)} fixes)").add_to(m)

    # Dwell/rest sites -- context layer, NOT sensor candidates
    for _, row in dwell.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]], radius=3, color="#999999", fill=True,
            fill_opacity=0.4, weight=0,
            tooltip=f"Dwell/rest site (context only) — {int(row['n_fixes'])} fixes",
        ).add_to(m)

    # Candidate transit sites -- chosen (gold) vs not chosen (blue)
    for _, row in sites.iterrows():
        is_chosen = int(row["site_id"]) in CHOSEN_SITES
        is_banzena = int(row["site_id"]) == LAKE_BANZENA_SITE_ID
        label = f"Site {int(row['site_id'])}"
        if is_banzena:
            label += " — Lake Banzena (known dry-season water source)"
        label += f" | {int(row['n_fixes'])} fixes | weight={row['weight_c_i']:.3f}"
        label += " | SELECTED" if is_chosen else " | not selected"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=14 if is_chosen else 8,
            color="#c9972c" if is_chosen else "#2c6fc9",
            fill=True, fill_opacity=0.85, weight=3 if is_chosen else 1.5,
            popup=label, tooltip=label,
        ).add_to(m)
        if is_chosen:
            folium.Marker(
                location=[row["lat"], row["lon"]],
                icon=folium.DivIcon(html='<div style="font-size:11pt;font-weight:bold;color:#7a5a1a;">&#128247;</div>'),
            ).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                background: white; padding: 12px 16px; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3); font-family: sans-serif; font-size: 13px;">
      <b>Signal in the Bush — Salif Keita, Gourma, Mali</b><br>
      <span style="color:#4a7c59;">&#9473;&#9473;</span> GPS trail (2008&ndash;2014)<br>
      <span style="color:#c9972c;">&#9679;</span> Selected sensor site (k=3; QUBO &amp; true max-coverage agree)<br>
      <span style="color:#2c6fc9;">&#9679;</span> Candidate site, not selected<br>
      <span style="color:#999999;">&#9679;</span> Dwell/rest site (context only)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    m.save("demo/map.html")
    print("Saved demo/map.html")
    print(f"Trail: {len(trail)} fixes rendered as {len(coords)} downsampled points")
    print(f"Candidate sites: {len(sites)}, dwell context sites: {len(dwell)}")
    print(f"Selected: {CHOSEN_SITES}")


if __name__ == "__main__":
    main()
