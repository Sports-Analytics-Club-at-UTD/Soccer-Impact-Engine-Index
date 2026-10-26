"""Read-only checks for the existing minutes/recovery delivery; no scoring policy."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import sys

try:
    import numpy as np
    import pandas as pd
    from pandas.api.types import is_bool_dtype, is_numeric_dtype
except ImportError as exc:
    print(f"Dependency unavailable: {exc}. Use an environment with pandas, numpy "
          "and a pandas Parquet engine (pyarrow or fastparquet). Nothing installed.", file=sys.stderr)
    raise SystemExit(2) from exc

KEYS = ["player_id", "team", "competition_name", "season_name"]
GROUPS = ["GK", "CB", "DM", "CM", "FB", "WM", "AM", "ATT"]
IN_SCOPE = ["GK", "CB", "DM", "CM"]
POSITION_MINUTES = [f"min_{g}" for g in GROUPS]
RECOVERY_KEYS = KEYS + ["event_type"]
MINUTES_NUMERIC = ["player_id", "minutes", "matches", "tied_groups", *POSITION_MINUTES]
RECOVERY_NUMERIC = ["player_id", "minutes", "matches", "count", "per90", "pctl", "pool_n"]
MINUTES_TEXT = ["player_name", *KEYS[1:], "position_group"]
RECOVERY_TEXT = ["player", *KEYS[1:], "position_group", "event_type", "pctl_note"]
ATOL, RTOL = 1e-6, 1e-9


@dataclass
class Report:
    label: str
    checks: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self):
        return not any(c["severity"] == "ERROR" and c["count"] for c in self.checks)

    def check(self, name, data, bad, advice, severity="ERROR", columns=None):
        mask = pd.Series(bad, index=data.index).fillna(True).astype(bool)
        cols = list(dict.fromkeys(columns or [c for c in [*KEYS, "event_type"] if c in data]))
        self.checks.append(dict(name=name, count=int(mask.sum()), checked=len(data),
                                severity=severity, advice=advice,
                                examples=data.loc[mask, cols].head(3).to_dict("records")))

    def render(self):
        lines = [f"{'PASS' if self.ok else 'FAIL'}: {self.label}", *self.notes]
        for c in self.checks:
            status = c["severity"] if c["count"] else "PASS"
            lines.append(f"  {status} {c['name']}: {c['count']} / {c['checked']} rows")
            if c["count"]:
                lines.append(f"    {c['advice']}")
                if c["examples"]:
                    lines.append(f"    Examples: {c['examples']}")
        return "\n".join(lines)


def numbers(s):
    return pd.to_numeric(s, errors="coerce").astype(float)


def finite(s):
    return np.isfinite(numbers(s))


def schema(report, df, label, numeric, text, boolean):
    duplicate_columns = df.columns[df.columns.duplicated()].tolist()
    if duplicate_columns:
        report.check(f"{label}.duplicate_columns", pd.DataFrame({"column": duplicate_columns}),
                     [True] * len(duplicate_columns), "Supply unique column labels.", columns=["column"])
        return False
    missing = [c for c in numeric + text + boolean if c not in df]
    if missing:
        report.check(f"{label}.schema", pd.DataFrame({"missing": missing}), [True] * len(missing),
                     "Supply the existing delivered columns; do not rename them implicitly.",
                     columns=["missing"])
        return False
    bad = [c for c in numeric if not is_numeric_dtype(df[c]) or is_bool_dtype(df[c])]
    bad += [c for c in boolean if not is_bool_dtype(df[c])]
    bad += [c for c in text
            if not df[c].dropna().map(lambda v: isinstance(v, str)).all()]
    if bad:
        report.check(f"{label}.types", pd.DataFrame({"column": bad}), [True] * len(bad),
                     "Numeric fields must be numeric, flags boolean, and labels strings.",
                     columns=["column"])
        return False
    report.check(f"{label}.schema", df, [False] * len(df), "")
    report.check(f"{label}.nonempty", pd.DataFrame({"rows": [len(df)]}), [df.empty],
                 "Supply a nonempty delivery.", columns=["rows"])
    return True


def required_values(report, df, label, text):
    bad = df["player_id"].isna() | ~finite(df["player_id"])
    ids = numbers(df["player_id"])
    bad |= (ids <= 0) | (ids != np.floor(ids))
    for c in text:
        bad |= df[c].isna() | df[c].fillna("").str.strip().eq("")
    report.check(f"{label}.identifiers_and_labels", df, bad,
                 "Restore player IDs/context labels from source; names are not identity keys.")
    report.check(f"{label}.unique_keys", df, df.duplicated(
        RECOVERY_KEYS if label == "recovery" else KEYS, keep=False),
        "Resolve duplicate stable identity keys upstream; do not keep an arbitrary first row.")


def numeric_values(report, df, label, columns):
    for c in columns:
        report.check(f"{label}.{c}.finite_nonnegative", df,
                     ~finite(df[c]) | (numbers(df[c]) < 0),
                     f"Restore finite nonnegative {c} from source.",
                     columns=[*KEYS, c])


def validate(minutes, recovery, label="delivery"):
    report = Report(label)
    report.notes.append(f"Input rows: minutes={len(minutes)}, recovery={len(recovery)}")
    a = schema(report, minutes, "minutes", MINUTES_NUMERIC, MINUTES_TEXT, ["in_scope"])
    b = schema(report, recovery, "recovery", RECOVERY_NUMERIC, RECOVERY_TEXT,
               ["reportable", "meets_min", "full_coverage"])
    if not (a and b):
        return report
    required_values(report, minutes, "minutes", MINUTES_TEXT)
    required_values(report, recovery, "recovery", RECOVERY_TEXT)
    numeric_values(report, minutes, "minutes", ["minutes", *POSITION_MINUTES])
    numeric_values(report, recovery, "recovery", ["minutes", "count", "per90"])
    for label_, df in [("minutes", minutes), ("recovery", recovery)]:
        m = numbers(df["matches"])
        # Unused/zero-duration records in the delivered schema may have no match count.
        bad = ((numbers(df["minutes"]) > 0) & (~finite(m) | (m <= 0)))
        bad |= m.notna() & (~finite(m) | (m < 0) | (m != np.floor(m)))
        report.check(f"{label_}.matches", df, bad,
                     "Positive-minute players need a positive integral match count; "
                     "missing matches are permitted only for zero-minute records.")
        report.check(f"{label_}.position_group", df, ~df["position_group"].isin(GROUPS),
                     "Use a reported position-minute group from the existing delivery.")
    ties = numbers(minutes["tied_groups"])
    report.check("minutes.tied_groups", minutes,
                 ~finite(ties) | (ties < 1) | (ties > len(GROUPS)) | (ties != np.floor(ties)),
                 "Restore the reported integral tied-group count.")
    for df, flags, label_ in [(minutes, ["in_scope"], "minutes"),
                             (recovery, ["reportable", "meets_min", "full_coverage"], "recovery")]:
        report.check(f"{label_}.flags_present", df, df[flags].isna().any(axis=1),
                     "Supply explicit boolean flags; validator does not choose eligibility thresholds.")
    report.check("minutes.position_sum", minutes,
                 ~np.isclose(numbers(minutes["minutes"]),
                             minutes[POSITION_MINUTES].sum(axis=1, skipna=False),
                             atol=ATOL, rtol=RTOL),
                 "Total minutes must equal the sum of reported position minutes.",
                 columns=[*KEYS, "minutes", *POSITION_MINUTES])
    # Mirror the delivered producer's exact maximum/tie order, not a new role policy.
    position_minutes = minutes[POSITION_MINUTES].apply(numbers)
    valid_positions = (np.isfinite(position_minutes).all(axis=1)
                       & position_minutes.ge(0).all(axis=1))
    top = position_minutes.max(axis=1, skipna=False)
    has_exposure = valid_positions & top.gt(0)
    expected_role = position_minutes.fillna(0).idxmax(axis=1).str.removeprefix("min_")
    expected_ties = position_minutes.eq(top, axis=0).sum(axis=1)
    report.check("minutes.dominant_position", minutes,
                 has_exposure & minutes["position_group"].ne(expected_role),
                 "Use the group with most position minutes; exact ties follow "
                 "GK, CB, DM, CM, FB, WM, AM, ATT order.",
                 columns=[*KEYS, "position_group", *POSITION_MINUTES])
    report.check("minutes.position_ties", minutes,
                 has_exposure & ties.ne(expected_ties),
                 "tied_groups must count the groups sharing the maximum position minutes.",
                 columns=[*KEYS, "tied_groups", *POSITION_MINUTES])
    report.check("minutes.scope_agrees", minutes,
                 minutes["in_scope"].ne(minutes["position_group"].isin(IN_SCOPE)),
                 "The delivered in_scope flag must agree with GK/CB/DM/CM membership.",
                 columns=[*KEYS, "position_group", "in_scope"])
    report.check("minutes.zero_minute_classification", minutes,
                 numbers(minutes["minutes"]).eq(0),
                 "Zero-minute role classifications carry no observed exposure. Exclude them "
                 "from rate calculation; this is a warning, not a new eligibility policy.",
                 severity="WARNING", columns=[*KEYS, "minutes", "position_group", "tied_groups"])
    report.check("recovery.event_types", recovery,
                 ~recovery["event_type"].isin(["Tackle", "Interception", "Ball Recovery"]),
                 "Use the three event labels supported by the existing recovery delivery.")
    report.check("recovery.in_scope_position", recovery,
                 ~recovery["position_group"].isin(IN_SCOPE),
                 "Recovery rows are restricted to the delivered GK/CB/DM/CM scope.",
                 columns=[*KEYS, "event_type", "position_group"])
    expected_reportable = ~((recovery["position_group"] == "GK")
                            & (recovery["event_type"] != "Ball Recovery"))
    report.check("recovery.reportable_agrees", recovery,
                 recovery["reportable"].ne(expected_reportable),
                 "Apply the existing delivery rule: GK Ball Recovery only; "
                 "other in-scope groups report all three recovery event types.",
                 columns=[*KEYS, "event_type", "position_group", "reportable"])
    count = numbers(recovery["count"])
    report.check("recovery.integral_counts", recovery, count != np.floor(count),
                 "Recovery event counts must be integral.")
    denominator = numbers(recovery["minutes"])
    report.check("recovery.positive_denominator", recovery, denominator <= 0,
                 "A delivered recovery rate needs positive minutes; do not replace zero by an epsilon.")
    with np.errstate(divide="ignore", invalid="ignore"):
        expected = count / denominator * 90
    report.check("recovery.per90_arithmetic", recovery,
                 ~np.isclose(numbers(recovery["per90"]), expected, atol=ATOL, rtol=RTOL),
                 "Recompute per90 = count / minutes * 90 with the delivered denominator.",
                 columns=[*KEYS, "event_type", "count", "minutes", "per90"])
    eligible = recovery[["reportable", "meets_min", "full_coverage"]].fillna(False).all(axis=1)
    pctl, pool = numbers(recovery["pctl"]), numbers(recovery["pool_n"])
    report.check("recovery.percentile_availability", recovery, eligible != pctl.notna(),
                 "Reconcile percentile availability with the delivered flags; no threshold is inferred.")
    report.check("recovery.percentile_values", recovery,
                 pctl.notna() & (~finite(pctl) | (pctl < 0) | (pctl > 100)),
                 "Present percentiles must be finite and within 0..100.")
    report.check("recovery.pool_size", recovery,
                 (pctl.notna() & pool.isna()) |
                 (pool.notna() & (~finite(pool) | (pool <= 0) | (pool != np.floor(pool)))),
                 "Present pool sizes must be positive finite integers; scored rows require a pool.")
    if any(c["count"] and c["name"].endswith(".identifiers_and_labels") for c in report.checks):
        report.notes.append("Join checks skipped: repair invalid identifiers/labels first.")
        return report
    # Do not deduplicate: the actual left join must reveal multiplication and missing matches.
    joined = recovery.assign(_source_row=np.arange(len(recovery))).merge(
        minutes[KEYS + ["minutes", "position_group", "matches", "in_scope"]].rename(
            columns={c: f"_{c}_source" for c in
                     ["minutes", "position_group", "matches", "in_scope"]}),
        on=KEYS, how="left", indicator=True)
    multiplicity = joined.groupby("_source_row").size().reindex(range(len(recovery)), fill_value=0)
    missing = joined.loc[joined["_merge"] == "left_only", "_source_row"]
    report.check("join.exactly_one_minutes_record", recovery,
                 (multiplicity.to_numpy() != 1) | np.isin(np.arange(len(recovery)), missing),
                 "Resolve duplicate or missing minutes keys before joining.")
    report.check("join.missing_minutes", recovery,
                 np.isin(np.arange(len(recovery)), missing),
                 "Supply the missing player/team/competition/season minutes record.")
    report.notes.append(f"Left join rows: {len(recovery)} -> {len(joined)}; "
                        f"unmatched recovery rows={missing.nunique()}")
    matched_once = joined[(joined["_merge"] == "both") &
                          joined["_source_row"].map(multiplicity.eq(1))]
    report.check("join.minutes_agree", matched_once,
                 ~np.isclose(numbers(matched_once["minutes"]),
                             numbers(matched_once["_minutes_source"]), atol=ATOL, rtol=RTOL),
                 "Recovery denominators must match the unique minutes source.",
                 columns=[*KEYS, "event_type", "minutes", "_minutes_source"])
    report.check("join.position_group_agrees", matched_once,
                 matched_once["position_group"].ne(matched_once["_position_group_source"]),
                 "Recovery position groups must match the unique minutes source.",
                 columns=[*KEYS, "event_type", "position_group", "_position_group_source"])
    report.check("join.matches_agree", matched_once,
                 numbers(matched_once["matches"]).ne(numbers(matched_once["_matches_source"])),
                 "Recovery match counts must match the unique minutes source.",
                 columns=[*KEYS, "event_type", "matches", "_matches_source"])
    report.check("join.in_scope_minutes", matched_once,
                 ~matched_once["_in_scope_source"].fillna(False),
                 "Recovery rows require an in-scope minutes record under the existing rules.",
                 columns=[*KEYS, "event_type", "_position_group_source", "_in_scope_source"])
    return report


def compare(old_minutes, old_recovery, minutes, recovery):
    report = Report("old -> revised comparison")
    tables = [("old_minutes", old_minutes, False), ("old_recovery", old_recovery, True),
              ("revised_minutes", minutes, False), ("revised_recovery", recovery, True)]
    ready = True
    for name, df, rec in tables:
        ready &= schema(report, df, name, ["player_id", "count" if rec else "minutes"],
                        KEYS[1:] + (["event_type"] if rec else []), [])
        if ready:
            numeric_values(report, df, name, ["player_id", "count" if rec else "minutes"])
            bad = df[KEYS].isna().any(axis=1)
            for c in KEYS[1:] + (["event_type"] if rec else []):
                bad |= df[c].isna() | df[c].fillna("").str.strip().eq("")
            ids = numbers(df["player_id"])
            bad |= (ids <= 0) | (ids != np.floor(ids))
            report.check(f"{name}.identity", df, bad, "Comparison requires stable, complete keys.")
            if rec:
                values = numbers(df["count"])
                report.check(f"{name}.integral_counts", df, values != np.floor(values),
                             "Comparison event counts must be integral.")
    if not ready or not report.ok:
        return report
    for label, old, new, keys, value in [
        ("minutes", old_minutes, minutes, KEYS, "minutes"),
        ("recovery", old_recovery, recovery, RECOVERY_KEYS, "count"),
    ]:
        report.notes.append(f"{label}: rows {len(old)} -> {len(new)}; "
                            f"unique keys {len(old[keys].drop_duplicates())} -> "
                            f"{len(new[keys].drop_duplicates())}; "
                            f"duplicate-key excess {int(old.duplicated(keys).sum())} -> "
                            f"{int(new.duplicated(keys).sum())}")
        contexts = old[KEYS].drop_duplicates().merge(
            new[KEYS].drop_duplicates(), on=KEYS, how="outer", indicator=True)
        report.check(f"comparison.{label}.context_changes", contexts,
                     contexts["_merge"] != "both",
                     "New/missing stable player contexts need an explicit upstream explanation.",
                     columns=[*KEYS, "_merge"])
        # Aggregate old duplicate keys intentionally; preserve identity and event type.
        sums = old.groupby(keys, dropna=False)[value].sum().rename("old").reset_index().merge(
            new.groupby(keys, dropna=False)[value].sum().rename("revised").reset_index(),
            on=keys, how="outer")
        report.check(f"comparison.{label}.conservation", sums,
                     ~np.isclose(sums["old"].fillna(0), sums["revised"].fillna(0),
                                 atol=0 if value == "count" else ATOL,
                                 rtol=0 if value == "count" else RTOL),
                     f"Investigate changed {value} by stable context"
                     + (" and event type; equal grand totals alone are insufficient."
                        if value == "count" else "; do not discard duplicate-key minutes."),
                     columns=[*keys, "old", "revised"])
        report.notes.append(f"{label} total {value}: {old[value].sum():.6f} -> {new[value].sum():.6f}")
        if label == "recovery":
            report.notes.append("Recovery totals by event type: "
                                f"{old.groupby('event_type')['count'].sum().to_dict()} -> "
                                f"{new.groupby('event_type')['count'].sum().to_dict()}")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", required=True, type=Path)
    parser.add_argument("--recovery", required=True, type=Path)
    parser.add_argument("--compare-minutes", type=Path, help="Older delivery; comparison only")
    parser.add_argument("--compare-recovery", type=Path, help="Older delivery; comparison only")
    args = parser.parse_args(argv)
    if bool(args.compare_minutes) != bool(args.compare_recovery):
        parser.error("Supply both --compare-minutes and --compare-recovery.")
    try:
        minutes, recovery = pd.read_parquet(args.minutes), pd.read_parquet(args.recovery)
        reports = [validate(minutes, recovery)]
        reports[0].notes[:0] = [f"Minutes: {args.minutes.resolve()}",
                               f"Recovery: {args.recovery.resolve()}"]
        if args.compare_minutes:
            reports.append(compare(pd.read_parquet(args.compare_minutes),
                                   pd.read_parquet(args.compare_recovery), minutes, recovery))
            reports[-1].notes[:0] = [f"Old minutes: {args.compare_minutes.resolve()}",
                                    f"Old recovery: {args.compare_recovery.resolve()}"]
    except (OSError, ValueError, TypeError, ImportError) as exc:
        print(f"ERROR: Cannot read input datasets: {exc}. Check paths, Parquet files and "
              "installed pandas/Parquet dependencies. Nothing was installed.", file=sys.stderr)
        return 2
    print("\n\n".join(r.render() for r in reports))
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
