# Off-ball spatial dominance display

All three teams use the selected Plan A: the original flat interactive pitch. The shared component and stylesheet provide the same presentation for PSG, Barcelona and Leverkusen, with each team's own values and coverage.

The Teams view replaces the three image elements with a responsive pitch. Its nine native buttons overlay lightweight SVG markings. The existing team selectors remain in place. Hover, focus, click and touch reveal the same compact tooltip; arrow keys move between zones, and Escape dismisses it. Switching teams resets zone interaction state. No metric calculation or player feature changes.

## Source and precision limitation

The available numerical evidence is the whole-percent labels in the unchanged public images in `frontend/public/team/`. No underlying spatial-dominance table is present in this checkout or the research branch's tracked files. These values are transcribed chart labels, not newly calculated rates or unrounded numerical measurements. The interface states that limitation rather than implying extra precision. The original PNGs remain tracked for comparison.

| Team | Matches with 360 data | Top row | Center row | Bottom row |
| --- | ---: | --- | --- | --- |
| Paris Saint-Germain | 57 | 58, 44, 31 | 75, 56, 33 | 58, 44, 29 |
| Barcelona | 35 | 62, 44, 29 | 74, 55, 31 | 61, 46, 33 |
| Bayer Leverkusen | 31 | 59, 42, 25 | 71, 52, 30 | 58, 44, 30 |

All values are percentages. Coverage counts come from the PNG subtitles. The counts do not certify a specific season, fixture list or frame-selection scope; those are unavailable here.

The research source `origin/arpit-dev:src/metrics/zones.py` defines a 120 × 80 pitch, x edges 0/40/80/120, y edges 0/(80/3)/(160/3)/80, and zone ID `y_band * 3 + x_band + 1`. Its `src/viz/zone_heatmap.py` inverts y so zero is at the top. Accordingly the display uses row-major order, own goal at left, attack toward the right. Upper/lower channels deliberately avoid assigning camera-dependent left/right names.

The metric is the share of observed spatial cells nearest to the defending team's players during opponent possession in event-triggered 360 frames. It is not true pitch control, defensive effectiveness or the chance of winning possession. The absolute 0–100 color scale is shared across teams. Tooltips expose only original whole-percent labels, and coverage is displayed above the pitch.

## Verification

`frontend/tests/spatialDominance.test.js` checks the 27 transcribed labels, coverage, zone layout, label contrast across the color scale, team switching, selection reset, keyboard navigation, Escape, hover and click behavior. It is registered in the public test inventory. Browser verification covers responsive layout, boundary tooltips and touch interaction separately.

Verified results:

- Production build passes; this JavaScript project has no separate type-check script.
- All 224 public tests pass, including the production-preview HTTP test. Private suites require separately provisioned files and were not run.
- Browser checks at 320, 375, 768 and 1440 pixels confirm all three teams' nine labels, no horizontal overflow, and tooltip bounds within the viewport at the four corners and center.
- Hover, keyboard focus, arrow navigation and Escape were checked in the browser. A touch-enabled mobile context confirms distinct zone taps and outside-tap dismissal, with no page errors.
- Desktop and mobile screenshots were inspected. Narrow-screen tooltips sit above the pitch to leave every zone accessible. The only initial resource error was the pre-existing missing favicon; a temporary development-server connection change required reloading the page.
