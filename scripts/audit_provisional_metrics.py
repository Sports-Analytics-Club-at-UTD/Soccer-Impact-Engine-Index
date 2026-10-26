"""Read-only bounded observed metrics using a caller-supplied provisional lookup.

Run with python -B -m scripts.audit_provisional_metrics. No per90, file outputs,
network requests, scoring policies or production evidence attestations.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq

from scripts.audit_provisional_identity import (
    EVENT_COLUMNS as IDENTITY_COLUMNS, MAPPING_COLUMNS, ProvisionalAudit, audit_provisional,
)
from src.identity import PLAYER_KEYS, IdentityError, _columns, _contexts, _ids
from src.recovery import _minutes, inspect_recovery
from src.press_resistance import inspect_press_resistance
from src.metrics.recovery_coverage import EVENT_TYPES, recovery_counts
from src.metrics.press_actions import COUNT_COLS, RATE_COLS, aggregate_actions, add_completion_rates

EVENT_COLUMNS = [*IDENTITY_COLUMNS, "location", "duel_type", "duel_outcome",
                 "interception_outcome", "ball_recovery_recovery_failure",
                 "under_pressure", "pass_outcome", "dribble_outcome"]
RECOVERY_KEYS = [*PLAYER_KEYS, "event_type"]


class MetricsPrerequisiteError(IdentityError):
    """Unresolved input prevents partial player metrics; accounting stays available."""
    def __init__(self, identity, recovery_accounting, press_accounting):
        self.identity = identity
        self.recovery_accounting = recovery_accounting
        self.press_accounting = press_accounting
        super().__init__(f"{identity.summary['unresolved']} unresolved input events; "
                         "no player metrics calculated; inspect unmatched keys and action accounting")


@dataclass
class MetricsAudit:
    identity: ProvisionalAudit
    recovery: pd.DataFrame
    by_zone: pd.DataFrame
    press: pd.DataFrame
    recovery_accounting: pd.DataFrame
    press_accounting: pd.DataFrame
    zones: pd.DataFrame
    summary: dict


def audit_metrics(events, crosswalk, minutes):
    """Use existing extraction/aggregation definitions without wider-scope exposure.

    Identity checks cover ALL input rows, including events neither metric uses.
    The inspect helpers preserve M2B's nullable recovery-flag storage adaptation
    and M3A's nullable pressure/outcome behavior. Only fully resolved input may
    produce selected-player metrics, still labeled provisional by this workflow.
    """
    _columns(events, EVENT_COLUMNS, "metric events")
    exposure = _minutes(minutes)
    identity = audit_provisional(events, crosswalk, exposure[PLAYER_KEYS])
    lookup = identity.lookup.lookup
    rec = inspect_recovery(events, lookup, exposure[PLAYER_KEYS])
    pressure = inspect_press_resistance(events, lookup, exposure[PLAYER_KEYS])
    if identity.summary["unresolved"]:
        raise MetricsPrerequisiteError(identity, rec.accounting, pressure.accounting)
    selected_rec = rec.identity.selected_events()
    selected_press = pressure.identity.selected_events()
    totals, by_zone = recovery_counts(selected_rec, group_cols=PLAYER_KEYS)
    press = add_completion_rates(aggregate_actions(selected_press))
    zone_rows = []
    for kind in EVENT_TYPES:
        selected = selected_rec.loc[selected_rec.event_type.eq(kind)]
        count = int(totals.loc[totals.event_type.eq(kind), "count"].sum())
        zoned = int(by_zone.loc[by_zone.event_type.eq(kind), "count"].sum())
        unknown = int(selected.zone.isna().sum())
        if count != len(selected) or zoned != len(selected) - unknown:
            raise IdentityError("recovery/zone count conservation failed")
        zone_rows.append(dict(event_type=kind, selected=count, zoned=zoned, unknown_zone=unknown))
    if totals.duplicated(RECOVERY_KEYS).any() or by_zone.duplicated([*RECOVERY_KEYS, "zone"]).any():
        raise IdentityError("recovery aggregation produced duplicate keys")
    if press.duplicated(PLAYER_KEYS).any():
        raise IdentityError("press aggregation produced duplicate keys")
    for column in COUNT_COLS:
        if int(press[column].sum()) != int(selected_press[column].sum()):
            raise IdentityError("press attempt/completion conservation failed")
    if int(press.pressured_actions.sum()) != len(selected_press):
        raise IdentityError("press actions not conserved")
    for column in RATE_COLS:
        if not press[column].dropna().between(0, 100).all():
            raise IdentityError("press percentages outside 0..100")
    global_press = add_completion_rates(pd.DataFrame([
        {column: int(press[column].sum()) for column in COUNT_COLS}])).to_dict(orient="records")[0]
    observed = identity.events.loc[identity.events.identity_status.eq("selected"), PLAYER_KEYS].drop_duplicates()
    attached = observed.merge(exposure, on=PLAYER_KEYS, how="left", validate="one_to_one")
    return MetricsAudit(identity, totals, by_zone, press, rec.accounting, pressure.accounting,
                        pd.DataFrame(zone_rows), {
        "label": "PROVISIONAL OBSERVED METRICS",
        "production_verified": False,
        "input_events": len(events),
        "observed_matches": int(events.match_id.nunique()),
        "selected_observed_contexts": len(observed),
        "recovery_player_contexts": len(totals[PLAYER_KEYS].drop_duplicates()),
        "press_player_contexts": len(press),
        "recovery_nonqualifying_events": len(events) - int(rec.accounting.extracted.sum()),
        "press_nonqualifying_events": len(events) - int(pressure.accounting.filtered.sum()),
        "neither_metric_events": len(events) - len(set(rec.identity.events.id) | set(pressure.identity.events.id)),
        "input_event_types": {str(k): int(v) for k, v in events.type.value_counts(dropna=False).items()},
        "selected_contexts_missing_minutes": int(attached.minutes.isna().sum()),
        "selected_contexts_zero_minutes": int(attached.minutes.eq(0).sum()),
        "selected_contexts_positive_minutes": int(attached.minutes.gt(0).sum()),
        "exposure_scope": "delivered player/team/competition/season; prefix alignment unestablished",
        "corresponding_match_level_exposure": "NOT ESTABLISHED; not reconstructed",
        "per90": "WITHHELD; prefix numerator and delivered minutes have different scopes",
        "aggregate_press": global_press,
        "counts_conserved": True,
    })


def compare_delivery(result, delivery):
    """Compare category/key coverage only; different numerator windows are not equalities."""
    _columns(delivery, [*RECOVERY_KEYS, "count"], "delivered recovery")
    source = _contexts(delivery[[*RECOVERY_KEYS, "count"]], "delivered recovery")
    source["player_id"] = _ids(source.player_id, "delivered recovery.player_id")
    if not source.event_type.isin(EVENT_TYPES).all() or source.duplicated(RECOVERY_KEYS).any():
        raise IdentityError("delivered recovery has unknown categories or duplicate normalized keys")
    joined = result.recovery.merge(source, on=RECOVERY_KEYS, how="outer",
                                   validate="one_to_one", indicator=True)
    return {
        "count_comparison": "NOT COMPARABLE: prefix and wider delivered numerator scopes differ",
        "formula_disagreement": "NOT ESTABLISHED by different-scope counts",
        "delivered_rows": len(source),
        "delivered_player_contexts": len(source[PLAYER_KEYS].drop_duplicates()),
        "shared_context_category_rows": int(joined._merge.eq("both").sum()),
        "observed_only_context_category_rows": int(joined._merge.eq("left_only").sum()),
        "delivered_only_context_category_rows": int(joined._merge.eq("right_only").sum()),
    }


def audit_files(*, events_path, crosswalk_path, minutes_path, limit=4096,
                delivered_recovery_path=None, comparison_minutes_path=None):
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    paths = [events_path, crosswalk_path, minutes_path]
    paths += [p for p in (delivered_recovery_path, comparison_minutes_path) if p is not None]
    for path in paths:
        if not Path(path).is_file():
            raise FileNotFoundError(f"Required input unavailable: {path}")
    crosswalk = pq.read_table(crosswalk_path, columns=MAPPING_COLUMNS).to_pandas()
    minutes = pq.read_table(minutes_path, columns=[*PLAYER_KEYS, "minutes"]).to_pandas()
    pieces, remaining = [], limit
    for batch in pq.ParquetFile(events_path).iter_batches(
            batch_size=min(limit, 65536), columns=EVENT_COLUMNS):
        piece = batch.slice(0, remaining).to_pandas()
        pieces.append(piece)
        remaining -= len(piece)
        if remaining == 0:
            break
    events = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=EVENT_COLUMNS)
    result = audit_metrics(events, crosswalk, minutes)
    if delivered_recovery_path is not None:
        delivery = pq.read_table(delivered_recovery_path, columns=[*RECOVERY_KEYS, "count"]).to_pandas()
        result.summary["delivery_comparison"] = compare_delivery(result, delivery)
    if comparison_minutes_path is not None:
        comparison = _minutes(pq.read_table(comparison_minutes_path,
                                           columns=[*PLAYER_KEYS, "minutes"]).to_pandas())
        original = _minutes(minutes)
        joined = original.merge(comparison, on=PLAYER_KEYS, how="outer",
                                 validate="one_to_one", indicator=True, suffixes=("", "_refresh"))
        common = joined._merge.eq("both")
        equal = joined.minutes.eq(joined.minutes_refresh) | (joined.minutes.isna() & joined.minutes_refresh.isna())
        result.summary["minutes_comparison"] = {
            "shared_contexts": int(common.sum()),
            "original_only": int(joined._merge.eq("left_only").sum()),
            "refresh_only": int(joined._merge.eq("right_only").sum()),
            "changed_minutes": int((common & ~equal).sum()),
            "scope_alignment": "NOT ESTABLISHED by agreement between delivered tables",
        }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--minutes", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=4096)
    parser.add_argument("--delivered-recovery", type=Path)
    parser.add_argument("--comparison-minutes", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit_files(events_path=args.events, crosswalk_path=args.crosswalk,
                             minutes_path=args.minutes, limit=args.limit,
                             delivered_recovery_path=args.delivered_recovery,
                             comparison_minutes_path=args.comparison_minutes)
    except MetricsPrerequisiteError as exc:
        print(f"Prerequisite failed: {exc}", file=sys.stderr)
        print(exc.identity.summary, file=sys.stderr)
        print(exc.identity.unmatched.to_string(index=False), file=sys.stderr)
        print(exc.recovery_accounting.to_string(index=False), file=sys.stderr)
        print(exc.press_accounting.to_string(index=False), file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        print(f"Diagnostic rejected: {exc}", file=sys.stderr)
        return 1
    print("PROVISIONAL OBSERVED METRICS - NOT PRODUCTION-VERIFIED")
    for name, summary in [("Identity", result.identity.summary), ("Lookup", result.identity.lookup.summary),
                          ("Metrics", result.summary)]:
        print(name, summary)
    for name, table in [("Recovery accounting", result.recovery_accounting),
                        ("Press accounting", result.press_accounting), ("Zone accounting", result.zones),
                        ("Recovery by zone", result.by_zone), ("Player recovery counts", result.recovery),
                        ("Player press counts/percentages", result.press)]:
        print(name)
        print(table.to_string(index=False))
    print("All player tables use canonical grouping order, not metric rankings. No output files written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
