# Unified local Soccer Impact Index

Start the declared Python environment, then run Vite from `frontend/` with
`npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`.
The development root supplies **Home, Players, Leaderboards, Compare, Teams and
About**. `?view=five-attribute-experimental` remains an explicit entry into the
same interface; `?view=demo` selects the separate fictional demonstration.
Production still serves the fictional demo, not the local experiment.

One validated read-only adapter load supplies the existing canonical models.
Navigation reuses the shared header, search, player card, radar, comparison,
OVR and badge components; it introduces no second dataset or scoring pipeline.
The local endpoint is fixed, same-origin, loopback-only and no-store. Missing
or invalid frozen data yields an explicit error with no synthetic/demo fallback.
Teams and About remain usable independently of successful player delivery.

Hash routes preserve selected player identity, comparison pair and leaderboard
group across browser history and full reload. Search filters, pagination and
team choice survive navigation in the mounted session; memory-only filters
reset on reload. Unknown keys show an unavailable state, never another player.
Modified link clicks retain browser-native behavior. Navigation focuses the view
heading; mobile-menu Escape closes the menu and restores its button focus.

Teams stays mounted for selection continuity and reuses Arpit's three original
team-level heatmaps. They describe defender-nearest observed space during
opponent possession, not player ratings or true pitch control. Image-specific
source/run provenance and redistribution rights remain separate contributor/team
handoff questions; no calculations or PNGs are recreated here.

[Setup](../README.md), [Formula B](provisional-formula-b-ovr.md),
[badges](local-attribute-badges.md), [Limited Data](limited-data-status-consistency.md),
[private provisioning](private-local-provisioning.md) and
[test prerequisites](test-suite-inventory.md) describe the supported scope.
No personal audit paths, player result tables or unpublished screenshots are
required to reproduce source-only tests and the guarded demo.
