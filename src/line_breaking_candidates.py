"""CANDIDATE / DIAGNOSTIC / NOT PRODUCTION APPROVED.

Joseph-style visible outfield-opponent x-strip counts, not defensive-line science.
Reference: Joseph-dev 013c8edd5196a15ac826558f4b0964cc6f3a3e58.
No orientation guessing, source trust promotion, season rates, ratings or I/O.
"""
from collections import Counter
from dataclasses import asdict, dataclass
import math
from numbers import Real

import numpy as np
import pandas as pd

from src.identity import PLAYER_KEYS, _contexts, _ids, resolve_events
from src.identity_evidence import STRENGTHS

NOTICE = "CANDIDATE / DIAGNOSTIC / NOT PRODUCTION APPROVED"
MIN_BYPASSED = 3
FRAME_KEYS = ["id", "match_id", "competition_name", "season_name"]
FRAME_COLUMNS = [*FRAME_KEYS, "teammate", "actor", "keeper", "location", "visible_area"]
PASS_COLUMNS = [*FRAME_KEYS, "team", "player", "x0", "y0", "x1", "y1", "completed", "open_play",
                "attacking_orientation", "orientation_source"]
EVIDENCE_COLUMNS = [*FRAME_KEYS, "usable", "observations_complete", "one_row_per_visible_player",
                    "attacking_orientation", "orientation_source", "source", "evidence_kind"]


class LineBreakingError(ValueError):
    """Unsafe event/context/geometry contracts; never repaired by guessing."""


@dataclass(frozen=True)
class JosephCandidatePolicy:
    policy_id: str
    source: str
    actor_alignment_tolerance: float


@dataclass(frozen=True)
class CandidateAggregation:
    events: pd.DataFrame
    players: pd.DataFrame
    metadata: dict


def _missing(value):
    return pd.api.types.is_scalar(value) and bool(pd.isna(value))


def _number(value):
    if _missing(value): return None
    try: valid=not isinstance(value,(bool,np.bool_)) and isinstance(value,Real) and math.isfinite(value)
    except OverflowError: valid=False
    if not valid:
        raise LineBreakingError("finite real coordinates required; no coercion")
    return float(value)


def _point(value):
    if _missing(value): return None
    if not isinstance(value,(list,tuple,np.ndarray)) or len(value)!=2:
        raise LineBreakingError("exactly two location coordinates required")
    point=tuple(_number(v) for v in value)
    if None in point: return None
    if not 0<=point[0]<=120 or not 0<=point[1]<=80:
        raise LineBreakingError("coordinate outside 120x80 pitch")
    return point


def normalize_point(point, *, direction):
    """Explicit 180-degree rotation only when the caller supplies negative_x."""
    value=_point(point)
    if direction not in ("positive_x","negative_x"):
        raise LineBreakingError("explicit known attacking direction required")
    return value if value is None or direction=="positive_x" else (120-value[0],80-value[1])


def polygon_valid(value):
    if _missing(value) or not isinstance(value,(list,tuple,np.ndarray)) or len(value)<6 or len(value)%2:
        return False
    try: points=[_point(value[i:i+2]) for i in range(0,len(value),2)]
    except LineBreakingError: return False
    if any(p is None for p in points) or len(set(points))<3: return False
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))>1e-9


def frame_quality(records):
    """Structural inspection of one complete supplied frame, not source verification.

    No stable visible-player ID exists in the delivered flat source. Repeated
    location/flag signatures are ambiguous, never silently deduplicated as people.
    """
    reasons=set(); signatures=Counter(); locations={}; actors=[]; opponents=[]; polygon=None; checked_areas={}
    for row in records:
        row=dict(row)
        for flag in ("teammate","actor","keeper"):
            if _missing(row[flag]): row[flag]=None
        for flag in ("teammate","actor","keeper"):
            if row[flag] is not None and type(row[flag]) is not bool:
                raise LineBreakingError("frame flags require bool or explicit None")
            if row[flag] is None: reasons.add("missing_frame_flags")
        p=_point(row["location"])
        if p is None: reasons.add("missing_frame_coordinates")
        area=row["visible_area"]
        area_key=tuple(area) if isinstance(area,(list,tuple,np.ndarray)) else None
        try:
            if area_key not in checked_areas: checked_areas[area_key]=polygon_valid(area)
            valid_area=checked_areas[area_key]
        except TypeError:
            valid_area=False
        if not valid_area: reasons.add("missing_or_invalid_visible_area")
        if polygon is None: polygon=area_key
        elif polygon!=area_key: reasons.add("conflicting_visible_area")
        signature=(row["teammate"],row["actor"],row["keeper"],p)
        signatures[signature]+=1
        if p is not None:
            if p in locations and locations[p]!=signature: reasons.add("ambiguous_colocated_observations")
            locations[p]=signature
        if row["actor"] is True:
            actors.append(p)
            if row["teammate"] is not True: reasons.add("actor_team_conflict")
        if row["teammate"] is False and row["keeper"] is False and p is not None: opponents.append(p)
    duplicates=sum(n-1 for n in signatures.values() if n>1)
    if duplicates: reasons.add("ambiguous_duplicate_observations")
    if len(actors)!=1: reasons.add("missing_or_multiple_actors")
    if not records: reasons.add("missing_frame")
    return {"rows":len(records),"duplicate_observation_rows":duplicates,"actor_count":len(actors),
            "actor_location":actors[0] if len(actors)==1 else None,"opponents":tuple(opponents),
            "reasons":tuple(sorted(reasons)),"structurally_usable":not reasons}


def _table(table,required,label,optional=()):
    if (not isinstance(table,pd.DataFrame) or not table.columns.is_unique
            or set(required)-set(table.columns) or set(table.columns)-set(required)-set(optional)):
        raise LineBreakingError(f"{label}: incompatible explicit columns")
    out=table.copy(deep=True).reset_index(drop=True)
    if not out.id.map(lambda v:isinstance(v,str) and bool(v.strip())).all():
        raise LineBreakingError("nonblank event IDs required")
    out["match_id"]=_ids(out.match_id,"match IDs")
    for c in ("competition_name","season_name"):
        if not out[c].map(lambda v:isinstance(v,str) and bool(v.strip())).all():
            raise LineBreakingError("explicit competition/season required")
    return out


def assess_passes(passes,frames,*,frame_evidence,policy):
    """Retain every pass: assessed, ineligible or unassessed, with nullable outputs.

    Caller supplies validated completion/open-play status, normalized positive-x
    geometry AND per-frame source/orientation/observation attestations. A small
    actor-to-start distance checks alignment, not the direction of attack.
    """
    if not isinstance(policy,JosephCandidatePolicy) or any(not isinstance(v,str) or not v.strip() for v in (policy.policy_id,policy.source)):
        raise LineBreakingError("explicit Joseph candidate policy/source required")
    tolerance=_number(policy.actor_alignment_tolerance)
    if tolerance is None or tolerance<0: raise LineBreakingError("nonnegative actor alignment tolerance required")
    p=_table(passes,PASS_COLUMNS,"passes",["player_id"])
    p=_contexts(p,"passes")
    if "player_id" in p: p["player_id"]=_ids(p.player_id,"pass player ID",allow_missing=True)
    f=_table(frames,FRAME_COLUMNS,"frames")
    e=_table(frame_evidence,EVIDENCE_COLUMNS,"frame evidence")
    if p.id.duplicated().any() or e.id.duplicated().any():
        raise LineBreakingError("duplicate/conflicting event identity")
    all_contexts=pd.concat([p[FRAME_KEYS],f[FRAME_KEYS],e[FRAME_KEYS]]).drop_duplicates()
    if all_contexts.id.duplicated().any() or all_contexts.drop(columns="id").drop_duplicates().match_id.duplicated().any():
        raise LineBreakingError("conflicting event or match contexts")
    if set(f.id)-set(p.id) or set(e.id)-set(p.id): raise LineBreakingError("frame/evidence event absent from explicit pass input")
    evidence=e.set_index("id").to_dict("index")
    quality={}
    for event_id,group in f.groupby("id",sort=True): quality[event_id]=frame_quality(group.to_dict("records"))
    for row in e.to_dict("records"):
        for flag in ("usable","observations_complete","one_row_per_visible_player"):
            if not _missing(row[flag]) and type(row[flag]) is not bool: raise LineBreakingError("frame evidence flags require bool or None")
        if not isinstance(row["source"],str) or not row["source"].strip() or row["evidence_kind"] not in STRENGTHS:
            raise LineBreakingError("explicit supported source provenance required")
    rows=[]
    for row in p.to_dict("records"):
        for flag in ("completed","open_play"):
            if _missing(row[flag]): row[flag]=None
        a=_point([row["x0"],row["y0"]]); b=_point([row["x1"],row["y1"]])
        for flag in ("completed","open_play"):
            if row[flag] is not None and type(row[flag]) is not bool: raise LineBreakingError("explicit pass status flags required")
        q=quality.get(row["id"]); source=evidence.get(row["id"])
        reasons=[]; status="unassessed"; count=None; line_break=None; distance=None
        if row["completed"] is False or row["open_play"] is False:
            status="ineligible"
            if row["completed"] is False: reasons.append("unsuccessful_pass")
            if row["open_play"] is False: reasons.append("non_open_play_pass")
        else:
            if row["completed"] is None or row["open_play"] is None: reasons.append("unknown_pass_eligibility")
            if a is None or b is None: reasons.append("missing_pass_geometry")
            if not isinstance(row["attacking_orientation"],str) or row["attacking_orientation"]!="positive_x" or not isinstance(row["orientation_source"],str) or not row["orientation_source"].strip():
                reasons.append("unestablished_pass_orientation")
            if q is None: reasons.append("missing_frame")
            else: reasons.extend(q["reasons"])
            if source is None: reasons.append("missing_frame_evidence")
            else:
                for flag in ("usable","observations_complete","one_row_per_visible_player"):
                    if source[flag] is not True: reasons.append("unestablished_"+flag)
                if not isinstance(source["attacking_orientation"],str) or source["attacking_orientation"]!="positive_x" or not isinstance(source["orientation_source"],str) or not source["orientation_source"].strip():
                    reasons.append("unestablished_frame_orientation")
            if q and q["actor_location"] is not None and a is not None:
                distance=math.dist(q["actor_location"],a)
                if distance>tolerance: reasons.append("actor_start_alignment_failed")
            if not reasons:
                count=sum(a[0]<opponent[0]<b[0] for opponent in q["opponents"])
                line_break=count>=MIN_BYPASSED; status="assessed"
        rows.append({**row,"assessment_status":status,"reasons":tuple(sorted(set(reasons))),
            "opponents_bypassed":count,"candidate_line_break":line_break,"actor_start_distance":distance,
            "frame_rows":q["rows"] if q else 0,"notice":NOTICE,"policy_provenance":asdict(policy),
            "frame_source_provenance":dict(source) if source else None,"production_verified":False})
    out=pd.DataFrame([{k:v for k,v in row.items() if k not in ("opponents_bypassed","candidate_line_break")} for row in rows],
                     columns=[*p.columns,"assessment_status","reasons","actor_start_distance","frame_rows","notice","policy_provenance","frame_source_provenance","production_verified"])
    out["opponents_bypassed"]=pd.array([row["opponents_bypassed"] for row in rows],dtype="Int64")
    out["candidate_line_break"]=pd.array([row["candidate_line_break"] for row in rows],dtype="boolean")
    return out


def aggregate_candidates(assessments,*,crosswalk,population):
    """M2A strict identity before diagnostic counts; no unobserved player rows/rates.

    Caller remains responsible for its trusted identity evidence. This pure
    resolver call does not attest any source or change D1 production gates.
    """
    required=[*FRAME_KEYS,"team","player","assessment_status","reasons","opponents_bypassed",
              "candidate_line_break","notice","production_verified","policy_provenance","frame_source_provenance","frame_rows"]
    if not isinstance(assessments,pd.DataFrame) or any(c not in assessments for c in required):
        raise LineBreakingError("complete diagnostic assessment ledger required")
    if not assessments.notice.eq(NOTICE).all() or not assessments.production_verified.eq(False).all():
        raise LineBreakingError("candidate provenance cannot be promoted")
    _ids(assessments.match_id,"assessment match IDs")
    contexts=assessments[FRAME_KEYS].drop_duplicates()
    if contexts.id.duplicated().any() or contexts.drop(columns="id").drop_duplicates().match_id.duplicated().any():
        raise LineBreakingError("conflicting assessment event/match contexts")
    for row in assessments.itertuples():
        if row.assessment_status not in ("assessed","ineligible","unassessed"): raise LineBreakingError("unknown assessment status")
        assessed=row.assessment_status=="assessed"
        if assessed:
            n=_number(row.opponents_bypassed)
            frame_rows=_number(row.frame_rows)
            if (n is None or n<0 or n!=int(n) or frame_rows is None or frame_rows<0 or frame_rows!=int(frame_rows)
                    or n>frame_rows or not isinstance(row.candidate_line_break,(bool,np.bool_))
                    or bool(row.candidate_line_break)!=(n>=MIN_BYPASSED) or row.reasons):
                raise LineBreakingError("contradictory candidate measurement")
        elif not _missing(row.opponents_bypassed) or not _missing(row.candidate_line_break):
            raise LineBreakingError("unassessed/ineligible values must remain N/A")
    resolved=resolve_events(assessments,crosswalk,population).events
    selected=resolved.loc[resolved.identity_status.eq("selected")]
    rows=[]
    for key,group in selected.groupby(PLAYER_KEYS,sort=True):
        assessed=group.assessment_status.eq("assessed"); n=int(assessed.sum())
        reasons=Counter(reason for values in group.reasons for reason in values)
        rows.append(dict(zip(PLAYER_KEYS,key))|{"observed_passes":len(group),"assessed_eligible_passes":n,
            "candidate_line_breaks":int(group.loc[assessed,"candidate_line_break"].sum()) if n else None,
            "opponents_bypassed_sum":int(group.loc[assessed,"opponents_bypassed"].sum()) if n else None,
            "unassessed_passes":int(group.assessment_status.eq("unassessed").sum()),
            "excluded_passes":int(group.assessment_status.eq("ineligible").sum()),
            "match_ids":tuple(sorted(map(int,group.match_id.unique()))),"event_ids":tuple(sorted(group.id)),
            "reason_counts":dict(sorted(reasons.items())),"notice":NOTICE,"scope_complete":False,
            "policy_ids":tuple(sorted({p["policy_id"] for p in group.policy_provenance})),
            "frame_sources":tuple(sorted({(p["source"],p["evidence_kind"]) for p in group.frame_source_provenance if p is not None})),
            "source_scope":"supplied observed pass events only; not a full-season numerator"})
    columns=[*PLAYER_KEYS,"observed_passes","assessed_eligible_passes","unassessed_passes","excluded_passes",
             "match_ids","event_ids","reason_counts","notice","scope_complete","policy_ids","frame_sources","source_scope"]
    players=pd.DataFrame([{k:v for k,v in row.items() if k not in ("candidate_line_breaks","opponents_bypassed_sum")} for row in rows],columns=columns)
    for c in ("candidate_line_breaks","opponents_bypassed_sum"): players[c]=pd.array([row[c] for row in rows],dtype="Int64")
    if rows and not players.observed_passes.eq(players.assessed_eligible_passes+players.unassessed_passes+players.excluded_passes).all():
        raise LineBreakingError("pass count conservation failed")
    return CandidateAggregation(resolved,players,{"notice":NOTICE,"production_verified":False,
        "input_events":len(resolved),"selected":len(selected),"outside_population":int(resolved.identity_status.eq("outside_population").sum()),
        "scope_complete":False,"per90":"WITHHELD; no aligned exposure input or season claim"})
