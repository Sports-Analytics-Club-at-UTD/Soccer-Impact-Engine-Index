"""Review bounded real-source participation evidence without production outputs.

Reads only the selected original matches and small delivered lineup/minutes
tables. Writes new review JSON exclusively inside the source-evidence directory.
Never reads delivered event payloads or modifies delivered minutes.
"""
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from fractions import Fraction
import argparse
import json
from pathlib import Path

import pandas as pd

from scripts.audit_dri_readiness import candidate_population
from scripts.audit_fixture_evidence import audit_files
from scripts.recover_source_sample import save_json
from src.identity import normalize_team_names, PLAYER_KEYS
from src.statsbomb_participation import SourceDocument, adapt_match


def serial(value):
    if isinstance(value, Fraction):
        return dict(numerator=value.numerator, denominator=value.denominator)
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


def normalized_team(name):
    return normalize_team_names(pd.Series([name])).iloc[0]


def nominal_seconds(stints):
    """Contributor's documented clipped-90 arithmetic, comparison only."""
    total = 0
    for row in stints:
        def clock(value, default):
            if value is None:
                return default
            minute, second = value.split(":")
            return min(5400, max(0, int(minute)*60+int(second)))
        total += max(0, clock(row.get("to"),5400)-clock(row.get("from"),0))
    return total


def review(root):
    ids = json.loads((root / "selection.json").read_text())
    if not 0 < len(ids) <= 8 or len(set(ids)) != len(ids):
        raise ValueError("bounded unique sample required")
    fixture_rows = json.loads((root / "fixtures-normalized.json").read_text())
    fixtures = {r["match_id"]:r for r in fixture_rows}
    revision = json.loads((root / "revision.json").read_text())["sha"]

    def doc(name):
        request = json.loads((root / (name + ".request.json")).read_text())
        d = SourceDocument((root / name).read_bytes(), request["url"], revision)
        if request["outcome"] != "success" or request["provider_revision"] != revision or request["sha256"] != d.fingerprint:
            raise ValueError("source document/request fingerprint or revision mismatch")
        return d

    local = pd.read_parquet("data/raw/statsbomb_lineups.parquet")
    local["team"] = normalize_team_names(local.team)
    minutes = pd.read_parquet("data/validation/arpit-refresh-review/player_minutes.parquet")
    recovery = pd.read_parquet("data/validation/arpit-refresh-review/recovery_per90.parquet")
    candidates, _ = candidate_population(minutes, recovery)
    qualified = candidates[candidates.delivered_rules_eligible]
    context_keys = set(qualified[PLAYER_KEYS].itertuples(index=False,name=None))
    per_match = []
    for mid in ids:
        context = fixtures[mid]
        competition = {"La Liga":11,"Premier League":2,"Serie A":12,"Ligue 1":7}[context["competition_name"]]
        adapted = adapt_match(mid, doc(f"matches-{competition}-27.json"), doc(f"lineups-{mid}.json"), doc(f"events-{mid}.json"),
                              clock_document_reference=f"https://github.com/statsbomb/open-data/blob/{revision}/doc/Open%20Data%20Events%20v4.0.0.pdf; timestamp/period/minute table; paired Half Start zero origins")
        results = adapted.validate()
        reviewed = []
        for player, result in zip(adapted.players,results):
            team = normalized_team(player.context.team_key)
            existing = local[(local.match_id == mid) & (local.player_id == player.context.player_id) & local.team.eq(team)]
            raw = [json.loads(s) for s in player.raw_positions]
            fields = {"position_id":"position_id","position":"position","from_time":"from","to_time":"to", "from_period":"from_period","to_period":"to_period","start_reason":"start_reason","end_reason":"end_reason"}
            # JSON int and delivered float period IDs compare numerically below.
            observed = [{k:None if pd.isna(r[k]) else r[k] for k in fields} for r in existing[existing.position.notna()].to_dict("records")]
            expected = [{k:r.get(v) for k,v in fields.items()} for r in raw]
            same = len(observed)==len(expected) and all(any(r==s for s in expected) for r in observed) and all(any(r==s for s in observed) for r in expected)
            season = minutes[(minutes.player_id==player.context.player_id)&minutes.team.eq(team)&minutes.competition_name.eq(adapted.competition_name)&minutes.season_name.eq(adapted.season_name)]
            nominal = nominal_seconds(raw) if raw else None
            key=(player.context.player_id,team,adapted.competition_name,adapted.season_name)
            codes = {i.code for i in result.issues}
            if not raw:
                classification="bench roster only; no participation asserted"
            elif result.status=="CONFLICTING_EVIDENCE":
                classification="other contradictory evidence"
            elif any("boundary" in c or "boundaries" in c for c in codes):
                classification="missing period boundaries"
            elif result.status=="INCOMPLETE_EVIDENCE":
                classification="missing entry/exit evidence"
            else:
                classification="source-supported and structurally valid; independent trust attestation pending"
            reviewed.append(dict(player=asdict(player),validation=asdict(result),classification=classification,
                                 table_qualified_context=key in context_keys,local_roster_rows=len(existing),
                                 local_position_stints_equal_source=same,local_player_name_equal=bool(len(existing)) and set(existing.player_name)=={player.player_name},
                                 contributor_nominal_seconds=nominal,
                                 supported_minus_nominal_seconds=result.elapsed_seconds-nominal if result.elapsed_seconds is not None and nominal is not None else None,
                                 delivered_season_minutes=season.minutes.tolist(),
                                 season_minutes_comparison="aggregate season total only; no delivered per-match minutes artifact"))
        active = [r for r in reviewed if r["player"]["observations"]]
        report=dict(match_id=mid,fixture=context,provenance=adapted.provenance,clock_policy=asdict(adapted.policy),
                    boundaries=[asdict(b) for b in adapted.boundaries],warnings=adapted.warnings,players=reviewed,
                    active_status_counts=dict(Counter(r["validation"]["status"] for r in active)),
                    issue_counts=dict(Counter(i["code"] for r in active for i in r["validation"]["issues"])),
                    finding_counts=dict(Counter(f["code"] for r in active for f in r["validation"]["findings"])),
                    local_active_stint_disagreements=[r["player"]["context"]["player_id"] for r in active if not r["local_position_stints_equal_source"]])
        save_json(root / f"participation-{mid}.json",json.loads(json.dumps(report,default=serial)))
        per_match.append({k:report[k] for k in ("match_id","active_status_counts","issue_counts","finding_counts","local_active_stint_disagreements")})

    # Estimate only from small existing roster/metadata tables, never events.
    needed=set()
    for row in local[local.position.notna()].itertuples(index=False):
        f=fixtures.get(row.match_id)
        if f and (row.player_id,row.team,f['competition_name'],f['season_name']) in context_keys:
            needed.add(int(row.match_id))
    fixture_report=audit_files(metadata_path="data/validation/arpit-match-context-review/match_metadata.parquet",lineups_path="data/raw/statsbomb_lineups.parquet",snapshot_path=root/"fixtures-normalized.json",snapshot_provenance_path=root/"fixtures-provenance.json")
    summary=dict(kind="real bounded source evidence; no production certification",provider_revision=revision,
                 sample=per_match,fixture_count=len(fixtures),sample_match_count=len(ids),
                 fixture_comparison_conflicts=fixture_report['comparison_has_conflicts'],
                 context_disagreements=fixture_report['context_disagreements'],team_disagreements=fixture_report['team_disagreements'],
                 table_qualified_context_count=len(context_keys),
                 qualified_observed_active_fixture_ids=sorted(needed),
                 additional_observed_active_match_pairs_required=sorted(needed-set(ids)),
                 additional_all_provider_match_pairs=len(set(fixtures)-set(ids)),
                 future_missing_delivered_match_ids=[3879594],
                 future_missing_match_relevance="3879594 may include qualifying actors absent from the local appearance inventory; pilot roster now available",
                 full_league_fixtures_absent_from_provider_count=3,
                 original_delivery_acquisition_history="unavailable; fresh requests cannot reconstruct history",
                 production_verified_contexts=0,publication_authorized=False)
    save_json(root/"participation-summary.json",summary)
    print(json.dumps({k:v for k,v in summary.items() if not k.endswith("fixture_ids") and k != "additional_observed_active_match_pairs_required"},indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    review(parser.parse_args().root)
