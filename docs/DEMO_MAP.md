# Generated results map (stage 8)

Run `.venv/Scripts/python.exe scripts/build_demo_map.py` from the repository root, then open `demo/map.html`. Internet access is needed for the Leaflet libraries and OpenStreetMap tiles. The normal pipeline also rebuilds this map.

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

Verification: generated successfully; Chrome rendered tiles, trail, rings, table, and named controls. Toggling the p=3 raw layer changed its checked state and removed its rings. The accessibility tree exposed all seven result rows and named layer checkboxes. Stage 8 audit/debug complete: all 37 unit tests passed. Regression checks cover saved-selection linkage, stale and missing provenance, corrupted coverage counts, and missing feasible samples. The audit also fixed hardcoded backend captions, distinguished valid empty selections from missing samples, validated budget and coverage counts against the saved matrix, and added the JSON manifest to pipeline freshness checks. Chrome confirmed named marker buttons and keyboard Enter collapsing the results disclosure. Basic accessibility was checked; full WCAG certification was not performed.
