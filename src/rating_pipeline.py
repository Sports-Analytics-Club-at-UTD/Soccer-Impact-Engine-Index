"""Controlled synthetic scoring and source-readiness delivery; no production path."""
from dataclasses import asdict

import pandas as pd

from src import press_scoring as press
from src.defensive_candidates import evaluate_defensive_candidates
from src.dri_scoring import ROLE_GROUPS, SeasonScope, MEASUREMENT_COLUMNS
from src.identity import PLAYER_KEYS
from src.identity_evidence import SYNTHETIC
from src.rating_assembly import (PlayerContext, RatingScope, RatingEvidence, EvidenceSource,
    AttributePolicy, AttributeSlot, assemble_ratings, ATTRIBUTES)
from src.rating_delivery import envelope, archetype, withheld_attribute, GATES
from src.season_verification import season_readiness
from src.transfer_aggregation import aggregate_transfer, require_unique_memberships


def _player(context, name, role, minutes, cohort, source, match_ids, *, synthetic=False, full_season=False):
    return dict(player_id=str(context.player_id), name=name, team=context.team,
        competition_name=context.competition_name, season_name=context.season_name,
        role_group=ROLE_GROUPS.get(role), minutes=minutes, cohort_id=cohort,
        provenance=[source], contexts=[dict(team=context.team,competition_name=context.competition_name,
            season_name=context.season_name,match_ids=[str(i) for i in match_ids],source=source,
            full_season=full_season,evidence_kind=SYNTHETIC if synthetic else "UNVERIFIED")],
        overall=dict(rating=None,status="withheld",reasons=["policy_not_finalized"]))


def synthetic_rating_delivery(population, measurements, actions, *, pool, defensive_policy,
                             press_policy, evidence, names, transfers=()):
    """Raw counts/rates -> existing gates -> candidate transforms -> D3E -> v1.

    Inputs use existing DRI and press contracts. No evidence label can select a
    production path. Explicit policy selection is mandatory (None withholds).
    Transfer rows may be projected with transfer_inputs; their full lineage is
    checked here against the nominated scoring context before delivery.
    """
    if pool.evidence_kind != SYNTHETIC or evidence.kind != SYNTHETIC:
        raise ValueError("numeric pipeline is synthetic-only")
    if pool.coverage_evidence is not None and evidence.source != pool.coverage_evidence.source:
        raise ValueError("synthetic dataset/pool source mismatch")
    if press_policy is not None and (press_policy.formula != press.FIFA or
            press_policy.pooling != "separate_mid_cb" or press_policy.reference_unit != "one_context_per_player"):
        raise ValueError("rating delivery requires explicit separate-role FIFA press policy")
    defenses, _ = evaluate_defensive_candidates(population,measurements,pool=pool,policy=defensive_policy)
    pp = population.drop(columns=["reference_member"]).copy(deep=True)
    pp["exposure_scope"] = pp.exposure_scope.map(lambda s: press.PressScope(
        s.competition_name,s.season_name,s.match_ids,s.full_season) if s else None)
    def convert(e):
        if e is None:
            return None
        if e.kind != SYNTHETIC or e.source != evidence.source:
            raise ValueError("synthetic evidence lineage mismatch")
        return press.SyntheticEvidence(e.kind,evidence.fixture_id,e.source,e.complete)
    for field in ("identity_evidence","context_evidence","exposure_evidence"):
        pp[field] = pp[field].map(convert)
    reference_mask = population.reference_member & population.position_group.isin(ROLE_GROUPS)
    members = pp.loc[reference_mask,PLAYER_KEYS].copy()
    members["pool_group"] = population.loc[reference_mask,"position_group"].map(ROLE_GROUPS)
    pools = press.ComparisonPools(pool.population_id,pool.season_name,pool.competitions,members,convert(pool.coverage_evidence))
    pressed = press.evaluate_press_candidates(pp,actions,pools=pools,evidence=evidence,policy=press_policy).players
    contexts = [PlayerContext(**{k:r[k] for k in PLAYER_KEYS}) for r in population.to_dict("records")]
    source_rows = {tuple(r[k] for k in PLAYER_KEYS):r for r in population.to_dict("records")}
    transfer_map = {}
    for result in require_unique_memberships(transfers):
        if result["status"] != "synthetic_combined":
            raise ValueError("withheld transfer cannot enter scoring")
        c = result["context"]
        if c in transfer_map or c not in contexts or result["policy"].pool_id != pool.population_id:
            raise ValueError("transfer identity/pool mismatch")
        source = source_rows[tuple(asdict(c).values())]
        if source["minutes"] != result["minutes"] or source["reference_member"] != result["reference_member"] or ROLE_GROUPS.get(source["position_group"]) != result["role"]:
            raise ValueError("transfer exposure/membership/role mismatch")
        tp,tm,ta = transfer_inputs(result,evidence=pool.coverage_evidence,press_evidence=evidence)
        actual_metrics = measurements.loc[(measurements[PLAYER_KEYS] == pd.Series(asdict(c))).all(axis=1)]
        actual_actions = actions.loc[(actions[PLAYER_KEYS] == pd.Series(asdict(c))).all(axis=1)]
        if not actual_metrics.sort_values("event_type").reset_index(drop=True).equals(tm.sort_values("event_type").reset_index(drop=True)) or not actual_actions.reset_index(drop=True).equals(ta):
            raise ValueError("transfer numerator lineage mismatch")
        if source["exposure_scope"] != tp.iloc[0].exposure_scope:
            raise ValueError("transfer scope mismatch")
        transfer_map[c] = result
    slots = []; ranks = {}; policies = {}
    for table, attrs in ((defenses,ATTRIBUTES[:3]),(pressed,("press_resistance",))):
        for row in table.to_dict("records"):
            c = PlayerContext(**{k:row[k] for k in PLAYER_KEYS})
            original = source_rows[tuple(asdict(c).values())]
            scope = original["exposure_scope"]
            for aid in attrs:
                is_press = aid == "press_resistance"
                score = row["candidate_score" if is_press else f"{aid}_rating"]
                rank = row["candidate_percentile" if is_press else f"{aid}_rank"]
                reasons = tuple(row["reasons" if is_press else f"{aid}_reasons"])
                selected = press_policy if is_press else defensive_policy
                available = pd.notna(score)
                if available and not evidence.complete:
                    available = False; reasons = ("incomplete_synthetic_dataset",)
                policy = AttributePolicy(aid,selected.policy_id,"1","rating_1_100",True) if selected else None
                rs = RatingScope(c.competition_name,c.season_name,scope.match_ids,scope.full_season,pool.population_id) if scope else None
                lineage = RatingEvidence(SYNTHETIC,(EvidenceSource(SYNTHETIC,evidence.source),),evidence.fixture_id,True)
                slots.append(AttributeSlot(aid,c,float(score) if available else None,"available" if available else "withheld",
                    () if available else reasons or ("candidate_unavailable",),policy,lineage,rs,
                    f'{pool.population_id}:{ROLE_GROUPS.get(original["position_group"])}' if ROLE_GROUPS.get(original["position_group"]) else None))
                ranks[c,aid] = float(rank) if available else None
                policies[c,aid] = dict(policy_id=selected.policy_id,source=selected.source,formula=selected.formula,
                    min_minutes=selected.min_minutes if is_press else 900,
                    min_actions=selected.min_actions if is_press else None,status="candidate") if selected else None
    assemblies = assemble_ratings(contexts,slots)  # Deliberately no synthetic OVR policy.
    players = []
    for assembly in assemblies:
        c = assembly.context; original = source_rows[tuple(asdict(c).values())]
        minutes = original["minutes"]
        scope = original["exposure_scope"]
        p = _player(c,names[c],original["position_group"],float(minutes) if pd.notna(minutes) else None,
                    pool.population_id,evidence.source,scope.match_ids if scope else (),
                    synthetic=True,full_season=scope.full_season if scope else False)
        p["classification"] = "synthetic"
        for table in (population,measurements,actions):
            matching = table.loc[(table[PLAYER_KEYS] == pd.Series(asdict(c))).all(axis=1)]
            for r in matching.to_dict("records"):
                refs = [r.get("reportability_source")]
                refs += [getattr(r.get(k),"source",None) for k in
                         ("identity_evidence","context_evidence","exposure_evidence","coverage_evidence")]
                for ref in refs:
                    if ref is not None and ref not in p["provenance"]:
                        p["provenance"].append(ref)
        p["eligibility"] = dict.fromkeys(GATES,False) | dict(delivered_table_eligible=False,
            synthetic_supported=True,valid_sample_appearance_ids=[],contradictory_sample_appearance_ids=[],reasons=[])
        p["attributes"] = {}
        for s in assembly.attributes:
            p["attributes"][s.attribute_id] = dict(rating=s.score,percentile=ranks.get((c,s.attribute_id)),
                status="synthetic_candidate" if s.status == "available" else "withheld",reasons=list(s.reasons),
                policy=policies.get((c,s.attribute_id)),comparison_pool=f'{pool.population_id}:{p["role_group"]}' if p["role_group"] else None)
        p["attributes"]["line_breaking_passes"] = withheld_attribute("line_breaking_policy_pending",f'{pool.population_id}:{p["role_group"]}' if p["role_group"] else None)
        if c in transfer_map:
            result = transfer_map[c]; grouped = {}
            for r in result["contributions"]:
                ctx = r["context"]
                group = grouped.setdefault(ctx,dict(team=ctx.team,competition_name=ctx.competition_name,
                    season_name=ctx.season_name,match_ids=[],source=result["policy"].source,
                    full_season=True,evidence_kind=SYNTHETIC))
                group["match_ids"].append(str(r["match_id"]))
                if r["source"] not in p["provenance"]:
                    p["provenance"].append(r["source"])
            p["contexts"] = list(grouped.values())
            p["provenance"].append(f'transfer-policy:{result["policy"].policy_id}')
        p["archetype"] = archetype(p["attributes"],p["role_group"])
        players.append(p)
    return envelope(players,pool.population_id)


def readiness_rating_delivery(readiness, *, names, roles, source, cohort_id):
    """Existing season-readiness reports -> withheld cards, never numeric ratings.

    Even edited certification flags cannot enable candidate or production scores.
    This reader deliberately accepts only the current noncertifying report type.
    """
    if readiness.get("schema_version") != "season-evidence-readiness/v1" or readiness.get("publication_authorized") is not False:
        raise ValueError("nonpublication season-readiness report required")
    players = []
    for row in readiness["contexts"]:
        c = PlayerContext(**{k:row[k] for k in PLAYER_KEYS})
        if any(row[k] is not False for k in ("season_exposure_verified","validated_exposure_eligible","production_certified")):
            raise ValueError("current readiness reports cannot certify season production")
        p = _player(c,names[c],roles.get(c),None,cohort_id,source,row["observed_active_match_ids"])
        p["classification"] = "diagnostic"
        reasons = ["unverified_season_exposure","unverified_metric_numerator_coverage","unverified_actor_identity","scoring_policy_not_approved","publication_not_authorized"]
        if row["source_coverage_incomplete"]:
            reasons.append("incomplete_fixture_coverage")
        if row["contradictory_sample_appearance_ids"]:
            reasons.append("contradictory_appearances")
        p["eligibility"] = dict.fromkeys(GATES,False) | dict(delivered_table_eligible=row["delivered_table_eligible"],
            independent_source_supported=False,synthetic_supported=False,
            valid_sample_appearance_ids=[str(i) for i in row["valid_sample_appearance_ids"]],
            contradictory_sample_appearance_ids=[str(i) for i in row["contradictory_sample_appearance_ids"]],reasons=reasons)
        pool = f'{cohort_id}:{p["role_group"]}' if p["role_group"] else None
        p["attributes"] = {aid:withheld_attribute("unverified_season_exposure",pool) for aid in ATTRIBUTES}
        p["attributes"]["line_breaking_passes"] = withheld_attribute("line_breaking_policy_pending",pool)
        p["archetype"] = archetype(p["attributes"],p["role_group"])
        players.append(p)
    return envelope(players,cohort_id)


def source_readiness_delivery(fixtures, delivered_metadata, lineups, qualified_contexts, match_reports, **kwargs):
    return readiness_rating_delivery(season_readiness(fixtures,delivered_metadata,lineups,qualified_contexts,match_reports),**kwargs)


def transfer_inputs(result, *, evidence, press_evidence):
    """Project one permitted aggregate into existing mathematical input contracts."""
    require_unique_memberships([result])
    if result != aggregate_transfer(result["contributions"],policy=result["policy"]):
        raise ValueError("transfer result contradicts original contribution ledger")
    if result["status"] != "synthetic_combined" or evidence.kind != SYNTHETIC or press_evidence.kind != SYNTHETIC:
        raise ValueError("only supported synthetic transfers can enter candidate inputs")
    c = result["context"]; key = asdict(c)
    scope = SeasonScope(c.competition_name,c.season_name,tuple(r["match_id"] for r in result["contributions"]),True)
    pop = pd.DataFrame([dict(**key,position_group=result["role"],reference_member=result["reference_member"],minutes=result["minutes"],
        exposure_scope=scope,identity_evidence=evidence,context_evidence=evidence,exposure_evidence=evidence)])
    metrics = pd.DataFrame([dict(**key,event_type=event,count=result["counts"][aid],minutes=result["minutes"],per90=result["per90"][aid],
        rate_status="ok",numerator_scope=scope,reportable=True,reportability_source="synthetic transfer ledger",coverage_evidence=evidence)
        for aid,event in zip(ATTRIBUTES[:3],("Tackle","Interception","Ball Recovery"))],columns=MEASUREMENT_COLUMNS)
    actions = pd.DataFrame([dict(**key,**{k:result["counts"][k] for k in press.COUNT_COLS},
        numerator_scope=press.PressScope(scope.competition_name,scope.season_name,scope.match_ids,True),coverage_evidence=press_evidence)])
    return pop,metrics,actions
