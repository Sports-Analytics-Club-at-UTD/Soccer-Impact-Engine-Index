"""Pure evidence accounting; delivered eligibility never implies verified exposure."""
from collections import Counter, defaultdict

from src.identity import normalize_team_names
from src.participation_intervals import VALID, CONFLICT
from src.statsbomb_participation import _id
import pandas as pd


def _team(name):
    return str(normalize_team_names(pd.Series([name])).iloc[0])


def season_readiness(fixtures, delivered_metadata, lineups, qualified_contexts, match_reports):
    """Keep actor/team/league/season contexts distinct, including transfers.

    Supplied match reports cover a bounded collection, not an asserted complete
    appearance inventory. No complete-season or production attestation is inferred.
    """
    expected = {}
    for row in fixtures:
        mid = _id(row["match_id"])
        if mid in expected:
            raise ValueError("duplicate provider fixture ID")
        expected[mid] = dict(row)
    observed = {}
    for row in delivered_metadata:
        mid = _id(row["match_id"])
        if mid in observed and observed[mid] != row:
            raise ValueError("conflicting delivered fixture contexts")
        observed[mid] = dict(row)
    contexts = {}
    for row in qualified_contexts:
        key = (_id(row["player_id"]), _team(row["team"]), row["competition_name"], row["season_name"])
        if key in contexts:
            raise ValueError("duplicate actor/club/competition/season context")
        contexts[key] = dict(row)
    appearances = defaultdict(set)
    for row in lineups:
        f = expected.get(_id(row["match_id"]))
        if f is None or row.get("position") is None:
            continue
        key = (_id(row["player_id"]), _team(row["team"]), f["competition_name"], f["season_name"])
        if key in contexts:
            appearances[key].add(row["match_id"])
    reports = {}
    qualified_sample = defaultdict(list)
    all_statuses = Counter()
    source_actors = set()
    for report in match_reports:
        mid = _id(report["match_id"])
        if mid in reports or mid not in expected:
            raise ValueError("duplicate/out-of-scope source match report")
        f = expected[mid]
        if report.get("artifact_validation") != "BYTE_BOUND_SOURCE_SCHEMA_REVIEWED":
            continue
        if (report["competition_name"], report["season_name"]) != (f["competition_name"], f["season_name"]):
            raise ValueError("source report/fixture context disagreement")
        if report.get("production_certified") is not False:
            raise ValueError("pilot reports cannot assert production certification")
        reports[mid] = report
        seen = set()
        for row in report["players"]:
            p, validation = row["player"], row["validation"]
            c = p["context"]
            if c != validation["context"] or c["match_id"] != mid:
                raise ValueError("actor report context disagreement")
            key = (_id(c["player_id"]), _team(c["team_key"]), f["competition_name"], f["season_name"])
            if key in seen:
                raise ValueError("duplicate source appearance")
            seen.add(key)
            active = bool(p["observations"] or p.get("source_checks"))
            if not active:
                continue
            source_actors.add(key)
            all_statuses[validation["status"]] += 1
            if key in contexts:
                qualified_sample[key].append((mid,validation["status"]))
    leagues=[]
    for league, season in sorted({(r["competition_name"],r["season_name"]) for r in fixtures}):
        ids={mid for mid,f in expected.items() if (f["competition_name"],f["season_name"])==(league,season)}
        obs={mid for mid,f in observed.items() if (f["competition_name"],f["season_name"])==(league,season)}
        context_conflicts=sorted(mid for mid in ids & observed.keys() if
                                (observed[mid]["competition_name"],observed[mid]["season_name"])!=(league,season))
        leagues.append(dict(competition_name=league,season_name=season,provider_fixture_count=len(ids),
                            delivered_observed_count=len(obs),missing_from_delivered_ids=sorted(ids-obs),
                            unexpected_delivered_ids=sorted(obs-ids),context_conflict_ids=context_conflicts,
                            provider_ids_match_delivered=ids==obs and not context_conflicts,
                            source_match_pairs_obtained=len(ids & reports.keys()),
                            additional_match_pairs_required=len(ids-reports.keys()),
                            source_coverage_complete=not bool(ids-reports.keys()),season_exposure_verified=False,
                            full_historical_league_completeness="NOT_ESTABLISHED_BY_PROVIDER_LIST"))
    rows=[]
    for key,row in sorted(contexts.items()):
        observed_ids=appearances[key]
        sample=qualified_sample.get(key,[])
        valid_ids=sorted(mid for mid,status in sample if status==VALID)
        contradictory_ids=sorted(mid for mid,status in sample if status==CONFLICT)
        rows.append(dict(player_id=key[0],team=key[1],competition_name=key[2],season_name=key[3],
                         delivered_table_eligible=True,delivered_minutes=row.get("minutes"),
                         observed_active_match_ids=sorted(observed_ids),
                         source_pair_obtained_for_observed_matches=sorted(observed_ids & reports.keys()),
                         observed_matches_without_source_pair=sorted(observed_ids-reports.keys()),
                         valid_sample_appearance_ids=valid_ids,contradictory_sample_appearance_ids=contradictory_ids,
                         source_coverage_incomplete=True,season_exposure_verified=False,
                         validated_exposure_eligible=False,identity_gate="UNRESOLVED",
                         reportability_gate="UNRESOLVED",production_certified=False))
    by_actor=defaultdict(list)
    for row in rows:
        by_actor[row["player_id"]].append({k:row[k] for k in ("team","competition_name","season_name")})
    transfers=[dict(player_id=pid,contexts=values,contexts_kept_separate=True,scores_aggregated=False)
               for pid,values in sorted(by_actor.items()) if len(values)>1]
    return dict(schema_version="season-evidence-readiness/v1",leagues=leagues,contexts=rows,
                summary=dict(provider_fixture_count=len(expected),delivered_target_fixture_count=len(set(expected)&observed.keys()),
                             source_match_pairs_obtained=len(reports),observed_match_pairs_obtained=len(set(observed)&reports.keys()),
                             additional_provider_match_pairs_required=len(set(expected)-reports.keys()),
                             delivered_table_qualified_contexts=len(contexts),sample_active_player_contexts=len(source_actors),
                             qualified_contexts_touched=len(qualified_sample),
                             qualified_contexts_with_valid_sample=sum(any(s==VALID for _,s in sample) for sample in qualified_sample.values()),
                             qualified_contexts_with_contradictory_sample=sum(any(s==CONFLICT for _,s in sample) for sample in qualified_sample.values()),
                             active_appearance_status_counts=dict(all_statuses),
                             validated_season_exposure_eligible_contexts=0,production_certified_contexts=0),
                transferred_actors=transfers,missing_delivered_fixture_inclusion="PENDING_TEAM_APPROVAL",
                publication_authorized=False)
