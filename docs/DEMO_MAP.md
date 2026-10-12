# Interactive results map

Run `.venv/Scripts/python.exe scripts/build_demo_map.py` from the repository root, then open `demo/map.html`. The map is self-contained: Leaflet/jQuery and approximate Natural Earth country boundaries are embedded; no online tiles or CDN downloads are needed. The normal pipeline also rebuilds this map.

## Judge walkthrough

1. Drag to pan and use the plus/minus controls or scroll wheel to zoom. Hover over candidate dots and click selected markers for labels.
2. Leave the observed trail and candidate layers enabled to inspect the data and shortlist. Toggle the trail off when it obscures sites.
3. Enable only the classical placement layer: sites 0, 1, and 4 cover 1,075 observations.
4. Switch to raw and repaired QAOA layers at depths 1, 2, and 3. All currently select sites 0, 1, and 2, covering 883 observations; selected placements already meet the budget, so repair leaves them unchanged. Depth is the number of QAOA circuit layers, not the number of sensors.
5. Compare classical with repaired depth 3. Both select sites 0 and 1; their third choices differ. Zoom closely to see the 400 m circles. Screen-sized nested marker outlines identify methods and do not represent range.
6. Enable the optional approximate Banzena reference and zoom out to find it. It is context, not a candidate. Scroll the results panel for the complete table and caveats; its disclosure can be expanded/collapsed with the keyboard.

The generator reads the exact GPS baseline and all three generated QAOA repair reports. It checks their recorded input hashes and matching budget/radius before rendering; stale inputs fail explicitly. `demo/map_data.json` records the displayed selections, coverage, coordinates, date range, and monitoring radius.

Classical, selected raw QAOA, and repaired QAOA have separate layers. Depth 3 is initially enabled; depths 1 and 2 are optional. Blue outer, brown middle, and purple inner outlines distinguish coincident locations without displacing coordinates. Their monitoring circles use solid, dashed, and dotted strokes. Zoom in to inspect the 400 m zones. Raw refers to the selected feasible measured sample, not every shot or an averaged placement.

The accessible text table exposes all selections and covered observation counts independently of map colors. Layer checkboxes have text labels, markers have titles, the comparison disclosure is keyboard operable, focus outlines are visible, and the results panel scrolls on small screens. This is a basic accessibility check, not a full conformance certification.

The trail uses observed dates and is downsampled within segments; gaps over three hours are not connected. Banzena is an optional approximate gazetteer reference, never a selected candidate. The 400 m radius is an assumed monitoring zone, not a camera hardware specification. Coverage counts observations of one elephant; no quantum advantage is claimed.

Regression checks verify saved-selection linkage, input provenance, coverage counts, feasible-sample handling, and the absence of external map resources. Chrome checks confirmed named controls and keyboard operation of the comparison disclosure.

## Embedded-runtime fix

Qollab's embedded map received HTTP 403 images from the public OpenStreetMap tile server. The map now embeds Leaflet 1.9.4, jQuery 3.7.1, and approximate public-domain Natural Earth country boundaries instead of requesting tiles or CDN resources. The initial view fits the observed trail; grid lines, candidates, placement/range layers, popups, and live result markers remain interactive. This is a simplified geographic background with no road/satellite detail. Libraries and licenses are retained in demo/assets/. A sandboxed iframe with all external resource loading blocked rendered the corrected map successfully.
