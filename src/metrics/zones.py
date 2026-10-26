"""Recovery dependency excerpt from origin/arpit-dev (0445f18fa1895320f0679ee84022888793fae6e7).

Original: src/metrics/zones.py. Selected function bodies/constants are unchanged.
Only imports, this provenance header, and omission of unrelated CLI/helpers differ.
The integrated caller supplies stable player-ID grouping and validates joins.
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
