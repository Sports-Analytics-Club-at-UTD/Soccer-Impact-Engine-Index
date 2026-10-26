# Soccer Defensive Control & Midfield Engine Index
### *(The Rodri & Cubarsí Model)*

An analytical scouting framework built exclusively for **Midfielders, Center-Backs, and Goalkeepers** — the players whose value is systematically underrated by traditional stat sheets.

---

## 📋 Project Description

Most public scouting models are built around attacking output — goals, assists, shot-creating actions. That leaves the players who *prevent* goals and *control* the game with almost no rigorous, publicly reproducible framework for evaluation.

This project shifts the focus entirely away from scoring output to build a spatial, event-driven model that quantifies the qualities that actually define elite defensive and midfield play:

- **Off-ball spatial dominance** — how much of the pitch a player effectively controls or denies, independent of the ball
- **Press resistance under high pressure** — a player's ability to retain and progress the ball when closed down
- **Progressive line-breaking pass value** — passes that meaningfully advance the ball past opposition defensive/midfield lines, weighted by risk and space created
- **Defensive recovery coverage** — the area and frequency of ball recoveries, interceptions, and defensive actions relative to a player's positional role

Named after two archetypes of the modern game — the deep-lying playmaker who dictates tempo (Rodri) and the ball-playing center-back who breaks lines from the back (Cubarsí) — the model aims to surface players with these profiles across Europe's top leagues, using spatial event data rather than box-score totals.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| **Language** | Python 3.10+ |
| **Data Sources & Libraries** | StatsBomb Open Data / Opta event data, `mplsoccer` |
| **Data Science & Graph Theory** | `pandas`, `numpy`, `scikit-learn`, `NetworkX` (passing network analysis) |
| **Visualization & Reporting** | `matplotlib`, `seaborn`, `plotly`, `Streamlit` |
| **Version Control** | Git / GitHub |

---

## 👥 Recommended Team Roles & Requirements

### Project Manager (PM)
- Strong organizational capabilities to manage deliverable timelines across data cleaning, metric calculation, and visualization phases
- Responsible for ensuring clear, documented definitions of non-standard soccer metrics (e.g., press resistance thresholds, what counts as a "line-breaking" pass) so the team works from a shared, unambiguous spec

### Lead Developer
- Intermediate-to-advanced Python skills
- Experience handling nested, spatial JSON datasets (StatsBomb/Opta event data is deeply nested and coordinate-heavy)
- Familiarity with graph theory algorithms (`NetworkX`) or spatial indexing techniques (e.g., via `scikit-learn`)

### Engineer / Researcher
- Foundational Python knowledge with hands-on `pandas` experience
- Interest in spatial data mapping and a willingness to learn `mplsoccer` for pitch visualizations
- Comfort constructing and iterating on custom metric algorithms from a written spec

---

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/<your-org>/soccer-defensive-control-index.git
cd soccer-defensive-control-index

# Create and activate a virtual environment
python3.10 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the app

```bash
streamlit run app/main.py
```

---

## 📁 Project Structure

```
soccer-defensive-control-index/
├── data/                # Raw and processed event data (StatsBomb / Opta)
├── src/
│   ├── ingestion/       # Data loading & parsing from JSON event data
│   ├── metrics/         # Core metric calculations (press resistance, line-breaking, etc.)
│   ├── networks/        # Passing network construction (NetworkX)
│   └── viz/             # mplsoccer pitch visualizations & plotting utilities
├── app/                 # Streamlit dashboard
├── notebooks/           # Exploratory analysis & metric prototyping
├── tests/                # Unit tests
├── requirements.txt
└── README.md
```

---

## 🧭 Roadmap

- [ ] Define and document metric specs (press resistance thresholds, line-breaking pass criteria, recovery coverage zones)
- [ ] Build data ingestion pipeline for StatsBomb Open Data
- [ ] Implement core metric calculations
- [ ] Build passing network analysis module
- [ ] Design pitch visualizations with `mplsoccer`
- [ ] Ship v1 Streamlit scouting dashboard
- [ ] Expand coverage across top 5 European leagues

---

## 🤝 Contributing

Contributions are welcome. Please open an issue to discuss proposed changes before submitting a pull request, and make sure any new metric includes a written definition in line with the PM's metric-spec documentation.

---

## 📄 License

*Add your chosen license here (e.g., MIT).*

## Spatial + Defensive Recovery metrics

Two metrics, documented in full in [docs/metric_documentation.md](docs/metric_documentation.md). Team V1 scope is 2015/16 only. Everything below is provisional until the team agrees the open decisions listed in that document.

- **Defensive Recovery Coverage** (per player): counts of successful Tackles, Interceptions and Ball Recoveries, kept as three separate event types and never blended, tagged by pitch zone (3x3 placeholder grid).
  - Per-90 rates use minutes played from StatsBomb lineups (every match capped at 90 minutes). Players are keyed on `player_id` and grouped GK / CB / DM / CM by most minutes played. Fullbacks, wide midfielders, attacking midfielders and forwards are out of scope.
  - Scores (`recovery_scores`): for each event type, a percentile, a display rating and a Gold / Silver tier. DM and CM are ranked together as Midfielders; CB and GK are separate. The pool is the four full 2015/16 leagues together (La Liga, Ligue 1, Premier League, Serie A). Eligible players have at least 900 minutes (provisional). Single-club seasons (for example Bundesliga) get per-90 rates but no score.
  - Goalkeepers: Ball Recovery only. No possession adjustment in V1.
  - `pctl` in `recovery_per90` is an older within-league helper and is separate from `recovery_scores`.
- **Observed Spatial Dominance** (team level only): share of each pitch zone closer to the defending team's visible players than to the attackers, from StatsBomb 360 frames. Not true pitch control. Free 360 data exists for four league-seasons covering one club each (127 matches). Only PSG, Barcelona and Bayer Leverkusen have enough matches to report; everything else is N/A (Premier League and Serie A have no free 360 data).

Run from the repo root, in this order:

```
python -W ignore -m src.metrics.build_metric_tables
python -W ignore -m src.ingestion.fetch_lineups
python -W ignore -m src.metrics.player_minutes
python -W ignore -m src.metrics.recovery_per90
python -W ignore -m src.metrics.recovery_scores
python -W ignore -m src.viz.zone_heatmap
python -m pytest -q
```

`zone_heatmap` needs `--kind` (recovery or spatial); see `--help` for options.

Processed tables (in `data/processed/`, not in git):
- `player_minutes.parquet`: one row per player_id + team + competition + season, with minutes and position group. Shared on the Drive (V1, provisional).
- `recovery_per90.parquet`: one row per player-season x event type, with count, minutes, per-90 rate and the within-league `pctl`. Shared on the Drive (V1, provisional).
- `recovery_scores.parquet`: one row per player-season x event type, with percentile, rating, tier and a note explaining any N/A. Not yet shared on the Drive.

Large data files are on the shared Drive, not in git.