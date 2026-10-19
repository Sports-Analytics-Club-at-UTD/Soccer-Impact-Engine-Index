"""Shared pitch-zone definition and location parsing (StatsBomb coordinates, 120 x 80).

ORIENTATION CONVENTION used in every module of this project
-----------------------------------------------------------
x = 0   -> the acting / defending team's OWN goal line
x = 120 -> the goal that team attacks
StatsBomb already normalises event locations this way (each team attacks left -> right
in its own events). Recovery events therefore need no flipping.
360 frames need care: see spatial_dominance.py.

ZONES (ASSUMPTION - placeholder, needs a team decision)
-------------------------------------------------------
3 x 3 grid: 3 bands along the pitch (thirds) x 3 bands across it.
    zone_id = y_band * 3 + x_band + 1        (1..9)
    x_band 0 = own defensive third, 1 = middle third, 2 = attacking third
    y_band 0/1/2 = the three channels across the pitch (we do NOT label left/right,
                   because that depends on which way the pitch is drawn)
Locations that are missing or outside the pitch get zone = <NA>. Nothing is guessed.
"""
import numpy as np
import pandas as pd

PITCH_X = 120.0
PITCH_Y = 80.0
X_EDGES = np.array([0.0, 40.0, 80.0, 120.0])
Y_EDGES = np.array([0.0, 80.0 / 3, 160.0 / 3, 80.0])
N_ZONES = 9


def split_location(series):
    """Turn a column of [x, y] lists/arrays into two float arrays. Missing -> NaN."""
    n = len(series)
    x = np.full(n, np.nan)
    y = np.full(n, np.nan)
    for i, loc in enumerate(series.to_numpy()):
        if isinstance(loc, (list, tuple, np.ndarray)) and len(loc) >= 2:
            x[i] = loc[0]
            y[i] = loc[1]
    return x, y


def assign_zone(x, y):
    """Zone id 1..9 for each (x, y); <NA> if missing or off-pitch. Returns a pandas Int64 array."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = (
        np.isfinite(x) & np.isfinite(y)
        & (x >= 0) & (x <= PITCH_X) & (y >= 0) & (y <= PITCH_Y)
    )
    xb = np.clip(np.searchsorted(X_EDGES, x, side="right") - 1, 0, 2)
    yb = np.clip(np.searchsorted(Y_EDGES, y, side="right") - 1, 0, 2)
    zone = np.where(ok, yb * 3 + xb + 1, 0)
    arr = pd.array(zone, dtype="Int64")
    arr[~ok] = pd.NA
    return arr


def zone_xband(zone):
    return (np.asarray(zone) - 1) % 3


def zone_yband(zone):
    return (np.asarray(zone) - 1) // 3