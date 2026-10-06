"""Zone heatmaps on a pitch, for both metrics (9-zone grid from src/metrics/zones.py).

Run from the repo root (after src/metrics/build_metric_tables.py has created data/processed/):

    # where does a PLAYER recover the ball? (share of his events of that type, per zone)
    python -W ignore -m src.viz.zone_heatmap --kind recovery --player "Sergio Busquets Burgos" --event-type "Ball Recovery"
    python -W ignore -m src.viz.zone_heatmap --kind recovery --player "N''Golo Kanté" --event-type Tackle --season 2015/2016

    # where does a team recover the ball? (share of its events of that type, per zone)
    python -W ignore -m src.viz.zone_heatmap --kind recovery --team "Barcelona" --event-type Tackle
    python -W ignore -m src.viz.zone_heatmap --kind recovery --team "Barcelona" --event-type "Ball Recovery" --season 2020/2021 --counts

    # how much of the observed space did a team's defence own? (only reportable teams)
    python -W ignore -m src.viz.zone_heatmap --kind spatial --team "Paris Saint-Germain"

Pictures are saved to <repo>/figures/ .

READING THE PICTURE
  - The pitch is drawn so every team attacks LEFT -> RIGHT (x = 0 is the team's own goal), same
    convention as zones.py / the events data. The three rows are the three channels across the
    pitch; they are NOT labelled left/right because that depends on the camera side.
  - Colour = one-hue blue ramp, light -> dark = more. Zones that are N/A (no data, or too few
    matches) are grey with an "N/A" label; they are never filled with a guess.
  - recovery default: each zone shows its SHARE of the team's counted events of that type.
    Shares are comparable across teams of different size; raw counts (--counts) are not,
    because they depend on how many matches are in the data.

The pitch is drawn with plain matplotlib (no mplsoccer needed). draw_pitch() can be swapped for
mplsoccer's Pitch if the team prefers - keep the 120 x 80 coordinates and inverted y axis.
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

from src.metrics.zones import PITCH_X, PITCH_Y, X_EDGES, Y_EDGES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"

# design tokens (reference palette: sequential blue steps 100 -> 700, light surface)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#c9c8c2"
NA_FILL = "#e6e5e0"
NA_INK = "#6b6a66"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
CMAP = LinearSegmentedColormap.from_list("seq_blue", BLUE_RAMP)


def _lum(rgb):
    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _text_on(fill):
    """Ink or white, whichever has more contrast with the cell colour."""
    L = _lum(to_rgb(fill))
    return INK if (L + 0.05) / (_lum(to_rgb(INK)) + 0.05) >= 1.05 / (L + 0.05) else "#ffffff"


def zone_bounds(zone):
    """(x0, y0, width, height) of a zone id 1..9."""
    xb, yb = (zone - 1) % 3, (zone - 1) // 3
    return X_EDGES[xb], Y_EDGES[yb], X_EDGES[xb + 1] - X_EDGES[xb], Y_EDGES[yb + 1] - Y_EDGES[yb]


def draw_pitch(ax):
    """Recessive pitch markings over the zone fills. y axis inverted (StatsBomb: y = 0 at the top)."""
    kw = dict(fill=False, edgecolor=INK, linewidth=1.0, alpha=0.35, zorder=5)
    ax.add_patch(Rectangle((0, 0), PITCH_X, PITCH_Y, **kw))
    ax.plot([60, 60], [0, PITCH_Y], color=INK, lw=1.0, alpha=0.35, zorder=5)
    ax.add_patch(Circle((60, 40), 10, **kw))
    for x0, w in ((0, 18), (PITCH_X - 18, 18)):          # penalty areas
        ax.add_patch(Rectangle((x0, 18), w, 44, **kw))
    for x0, w in ((0, 6), (PITCH_X - 6, 6)):             # six-yard boxes
        ax.add_patch(Rectangle((x0, 30), w, 20, **kw))
    ax.set_xlim(-2, PITCH_X + 2)
    ax.set_ylim(PITCH_Y + 2, -2)
    ax.set_aspect("equal")
    ax.axis("off")


def plot_zone_heatmap(values, title, subtitle=None, value_fmt="{:.0%}", vmin=None, vmax=None,
                      legend_label="", footnote=None, na_text="N/A"):
    """values: dict / Series zone(1..9) -> number. Missing or NaN zones are drawn as N/A."""
    vals = {z: values.get(z, np.nan) for z in range(1, 10)}
    finite = [v for v in vals.values() if pd.notna(v)]
    lo = vmin if vmin is not None else (0.0 if finite else 0.0)
    hi = vmax if vmax is not None else (max(finite) if finite else 1.0)
    if hi <= lo:
        hi = lo + 1.0
    norm = Normalize(lo, hi)

    fig, ax = plt.subplots(figsize=(9.2, 6.6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for z in range(1, 10):
        x0, y0, w, h = zone_bounds(z)
        v = vals[z]
        if pd.isna(v):
            fill, label, ink, hatch = NA_FILL, na_text, NA_INK, "////"
        else:
            fill, label = CMAP(norm(v)), value_fmt.format(v)
            ink, hatch = _text_on(fill), None
        ax.add_patch(Rectangle((x0, y0), w, h, facecolor=fill, edgecolor=SURFACE, linewidth=2.5,
                               hatch=hatch, zorder=2))
        ax.text(x0 + w / 2, y0 + h / 2, label, ha="center", va="center", fontsize=15,
                fontweight="bold", color=ink, zorder=6)
    draw_pitch(ax)

    # attacking-direction arrow below the pitch
    ax.annotate("", xy=(PITCH_X - 8, PITCH_Y + 7), xytext=(8, PITCH_Y + 7),
                arrowprops=dict(arrowstyle="->", color=INK_2, lw=1.2), annotation_clip=False)
    ax.text(PITCH_X / 2, PITCH_Y + 10.5, "direction of attack", ha="center", va="top",
            fontsize=10, color=INK_2)

    fig.text(0.06, 0.95, title, ha="left", va="top", fontsize=16, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.06, 0.905, subtitle, ha="left", va="top", fontsize=10.5, color=INK_2)
    if footnote:
        fig.text(0.06, 0.03, footnote, ha="left", va="bottom", fontsize=9, color=INK_2)

    if finite:   # a colour scale only means something if at least one zone has a value
        sm = plt.cm.ScalarMappable(norm=norm, cmap=CMAP)
        cax = fig.add_axes([0.2, 0.125, 0.6, 0.02])
        cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
        cb.outline.set_visible(False)
        cb.ax.tick_params(colors=INK_2, labelsize=9, length=0)
        cb.ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: value_fmt.format(v)))
        cb.set_label(legend_label, color=INK_2, fontsize=9.5)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.86, bottom=0.3)
    return fig


# ---------- data -> values ----------
def recovery_values(by_zone, team=None, event_type=None, competition=None, season=None, share=True,
                    player=None):
    """Zone -> share (or count) for a team and/or a player, one event type. Zero is a real zero.

    Players are matched by the exact name in the events file (there is no player_id).
    """
    if team is None and player is None:
        raise SystemExit("Give --team and/or --player.")
    d = by_zone[by_zone["event_type"] == event_type]
    if team:
        d = d[d["team"] == team]
    if player:
        d = d[d["player"] == player]
    if competition:
        d = d[d["competition_name"] == competition]
    if season:
        d = d[d["season_name"] == season]
    if d.empty:
        raise SystemExit(f"No {event_type} rows for team={team!r} player={player!r} "
                         f"competition={competition!r} season={season!r}. Names must match the data exactly.")
    counts = d.groupby("zone")["count"].sum().reindex(range(1, 10), fill_value=0)
    total = int(counts.sum())
    return (counts / total if share else counts).to_dict(), total


def spatial_values(table, team):
    d = table[table["defending_team"] == team]
    if d.empty:
        raise SystemExit(f"Team {team!r} is not in the spatial table.")
    return d.set_index("zone")["control_rate"].to_dict(), d["n_matches"].max(), bool(d["reportable"].all())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kind", required=True, choices=["recovery", "spatial"])
    p.add_argument("--team", help="required for spatial; for recovery give --team and/or --player")
    p.add_argument("--player", help="recovery only: exact player name as in the events file")
    p.add_argument("--event-type", choices=["Tackle", "Interception", "Ball Recovery"])
    p.add_argument("--competition")
    p.add_argument("--season")
    p.add_argument("--counts", action="store_true", help="recovery: show raw counts instead of shares")
    a = p.parse_args()
    FIGURES.mkdir(exist_ok=True)
    if a.kind == "spatial" and not a.team:
        raise SystemExit("--team is required for --kind spatial (Spatial Dominance is team-level only).")

    if a.kind == "recovery":
        if not a.event_type:
            raise SystemExit("--event-type is required for --kind recovery")
        by_zone = pd.read_parquet(PROCESSED / "recovery_coverage_by_zone.parquet")
        vals, total = recovery_values(by_zone, a.team, a.event_type, a.competition, a.season,
                                      share=not a.counts, player=a.player)
        scope = " / ".join(x for x in (a.competition, a.season) if x) or "all seasons in the data"
        who = a.player or a.team
        teams = ""
        if a.player:
            tm = by_zone[(by_zone["player"] == a.player)]["team"].unique()
            teams = f"{', '.join(sorted(tm))}  |  " if a.team is None else ""
        fig = plot_zone_heatmap(
            vals, f"{who}: where {a.event_type.lower()} events happen",
            subtitle=f"{teams}{scope}  |  {total:,} events with a known location",
            value_fmt="{:,.0f}" if a.counts else "{:.0%}", legend_label=(
                "events per zone" if a.counts else "share of the team's events of this type"),
            footnote="Raw counted events, no possession adjustment. Zones: 3 x 3 placeholder grid.")
        name = f"recovery_{a.event_type.replace(' ', '_')}_{who.replace(' ', '_')}.png"
    else:
        table = pd.read_parquet(PROCESSED / "spatial_dominance_team_zone.parquet")
        vals, n_matches, ok = spatial_values(table, a.team)
        sub = (f"{n_matches} matches with 360 data" if ok else
               f"N/A: only {n_matches} matches with 360 data (a minimum is required)")
        fig = plot_zone_heatmap(
            vals, f"{a.team}: share of observed space nearest to its defenders",
            subtitle=f"When the opponent had possession  |  {sub}",
            value_fmt="{:.0%}", vmin=0.0, vmax=1.0, legend_label="defender-nearest share of observed cells",
            footnote="Observed Spatial Dominance from event-triggered 360 frames; not true pitch control.")
        name = f"spatial_{a.team.replace(' ', '_')}.png"

    out = FIGURES / name
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()