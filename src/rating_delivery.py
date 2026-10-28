"""Strict nonpublication rating delivery. This version has no production mode."""
import copy
import json
import math

from src.dri_scoring import LEAGUES, SEASON
from src.rating_assembly import ATTRIBUTES, PlayerContext, _context
from src.identity_evidence import SYNTHETIC, VERIFIED

SCHEMA = "soccer-rating-delivery/v1"
NOTICE = "SYNTHETIC / NOT PRODUCTION RATINGS"
GATES = ("delivered_table_eligible", "independent_source_supported", "season_exposure_verified",
         "metric_numerator_verified", "scoring_approved", "publication_authorized")


def _keys(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(f"exact fields required: {fields}")


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("nonblank text required")


def _id(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or str(int(value)) != value or not 0 < int(value) <= 2**63-1:
        raise ValueError("exact positive signed-int64 decimal string required")


def _strings(value, *, nonempty=False, ids=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError("explicit array required")
    for v in value:
        (_id if ids else _text)(v)
    if len(set(value)) != len(value):
        raise ValueError("duplicate array values")
    if ids and value != sorted(value, key=int):
        raise ValueError("canonical match ID order required")


def archetype(attributes, role):
    order = ("tackles", "recoveries", "interceptions", "press_resistance", "line_breaking_passes") if role == "CB" else ATTRIBUTES
    best = None
    for key in order:
        value = attributes[key]["percentile"]
        if value is not None and (best is None or value > best[1]):
            best = (key, value)
    return dict(attribute_id=best[0] if best and best[1] >= 75 else None,
                tier="Gold" if best and best[1] >= 90 else "Silver" if best and best[1] >= 75 else None)


def validate_delivery(payload):
    _keys(payload, ("schema_version", "notice", "publication_authorized", "production_ready", "scope", "players"))
    if payload["schema_version"] != SCHEMA or payload["notice"] != NOTICE or payload["publication_authorized"] is not False or payload["production_ready"] is not False:
        raise ValueError("nonpublication v1 envelope required")
    scope = payload["scope"]
    _keys(scope, ("season_name", "competitions", "role_groups", "cohort_id"))
    if scope["season_name"] != SEASON or scope["competitions"] != list(LEAGUES) or scope["role_groups"] != ["MID", "CB"]:
        raise ValueError("explicit four-league 2015/2016 MID/CB scope required")
    _text(scope["cohort_id"])
    if not isinstance(payload["players"], list):
        raise ValueError("player array required")
    seen = set()
    for p in payload["players"]:
        _keys(p, ("player_id", "name", "team", "competition_name", "season_name", "role_group", "classification",
                  "minutes", "provenance", "contexts", "eligibility", "cohort_id", "attributes", "archetype", "overall"))
        _id(p["player_id"])
        _context(PlayerContext(int(p["player_id"]),p["team"],p["competition_name"],p["season_name"]))
        for k in ("name", "team", "competition_name", "season_name", "cohort_id"):
            _text(p[k])
        key = (p["player_id"],p["team"],p["competition_name"],p["season_name"])
        if key in seen:
            raise ValueError("duplicate canonical context")
        seen.add(key)
        if p["season_name"] != SEASON or p["competition_name"] not in LEAGUES or p["role_group"] not in ("MID", "CB", None):
            raise ValueError("player scope mismatch")
        if p["cohort_id"] != scope["cohort_id"]:
            raise ValueError("cohort mismatch")
        if p["classification"] not in ("synthetic", "diagnostic", "verified"):
            raise ValueError("unsupported record classification")
        if p["minutes"] is not None and (type(p["minutes"]) not in (int,float) or not math.isfinite(p["minutes"]) or p["minutes"] < 0):
            raise ValueError("invalid minutes")
        _strings(p["provenance"],nonempty=True)
        if not isinstance(p["contexts"],list) or not p["contexts"]:
            raise ValueError("source contexts required")
        context_seen = set(); match_seen = set()
        for c in p["contexts"]:
            _keys(c, ("team", "competition_name", "season_name", "match_ids", "source", "full_season", "evidence_kind"))
            _context(PlayerContext(int(p["player_id"]),c["team"],c["competition_name"],c["season_name"]))
            for k in ("team", "source"):
                _text(c[k])
            if c["season_name"] != SEASON or c["competition_name"] not in LEAGUES:
                raise ValueError("contribution season/competition mismatch")
            _strings(c["match_ids"],ids=True)
            expected_kind = {"synthetic":SYNTHETIC,"diagnostic":"UNVERIFIED","verified":VERIFIED}[p["classification"]]
            if type(c["full_season"]) is not bool or c["evidence_kind"] != expected_kind:
                raise ValueError("explicit context scope/evidence required")
            if match_seen.intersection(c["match_ids"]):
                raise ValueError("duplicate match across transfer contexts")
            match_seen.update(c["match_ids"])
            ck = (c["team"],c["competition_name"],c["season_name"])
            if ck in context_seen:
                raise ValueError("duplicate contribution context")
            context_seen.add(ck)
        if (p["team"],p["competition_name"],p["season_name"]) not in context_seen:
            raise ValueError("nominated context absent from lineage")
        e = p["eligibility"]
        _keys(e, (*GATES, "synthetic_supported", "valid_sample_appearance_ids", "contradictory_sample_appearance_ids", "reasons"))
        if any(type(e[g]) is not bool for g in (*GATES,"synthetic_supported")):
            raise ValueError("separate boolean evidence gates required")
        if e["scoring_approved"] or e["publication_authorized"]:
            raise ValueError("v1 cannot authorize production")
        _strings(e["valid_sample_appearance_ids"],ids=True)
        _strings(e["contradictory_sample_appearance_ids"],ids=True)
        _strings(e["reasons"])
        if set(e["valid_sample_appearance_ids"]) & set(e["contradictory_sample_appearance_ids"]):
            raise ValueError("appearance cannot be valid and contradictory")
        synthetic = p["classification"] == "synthetic"
        if synthetic and any(e[g] for g in GATES[1:]):
            raise ValueError("synthetic evidence cannot assert source verification")
        if not synthetic and e["synthetic_supported"]:
            raise ValueError("real record cannot acquire synthetic scoring privileges")
        if p["classification"] == "verified" and (not all(e[g] for g in GATES[1:4]) or e["reasons"] or
                e["contradictory_sample_appearance_ids"] or any(not c["full_season"] or not c["match_ids"] for c in p["contexts"])):
            raise ValueError("verified classification contradicts evidence gates")
        _keys(p["attributes"], ATTRIBUTES)
        for aid, a in p["attributes"].items():
            _keys(a, ("rating", "percentile", "status", "reasons", "policy", "comparison_pool"))
            _strings(a["reasons"])
            if a["policy"] is not None:
                _keys(a["policy"], ("policy_id", "source", "formula", "min_minutes", "min_actions", "status"))
                for k in ("policy_id", "source", "formula"):
                    _text(a["policy"][k])
                if a["policy"]["status"] != "candidate":
                    raise ValueError("candidate policy only")
                for k in ("min_minutes", "min_actions"):
                    n = a["policy"][k]
                    if n is not None and (type(n) not in (int,float) or not math.isfinite(n) or n < 0):
                        raise ValueError("invalid policy threshold")
            if a["status"] == "withheld":
                if a["rating"] is not None or a["percentile"] is not None or not a["reasons"]:
                    raise ValueError("withheld values need nulls and reasons")
            elif a["status"] == "synthetic_candidate":
                if not synthetic or not e["synthetic_supported"] or e["reasons"] or e["contradictory_sample_appearance_ids"] or a["reasons"] or a["policy"] is None or p["role_group"] is None or any(not c["match_ids"] or not c["full_season"] for c in p["contexts"]):
                    raise ValueError("numeric candidate requires synthetic eligibility and complete lineage")
                for k, low in (("rating",1),("percentile",0)):
                    v = a[k]
                    if type(v) not in (int,float) or not math.isfinite(v) or not low <= v <= 100:
                        raise ValueError("invalid rating/percentile")
                if aid == "line_breaking_passes":
                    raise ValueError("line-breaking policy pending")
            else:
                raise ValueError("unsupported attribute status")
            expected_pool = f'{p["cohort_id"]}:{p["role_group"]}' if p["role_group"] else None
            if a["comparison_pool"] != expected_pool:
                raise ValueError("attribute comparison pool mismatch")
        if p["archetype"] != archetype(p["attributes"],p["role_group"]):
            raise ValueError("archetype must follow percentiles")
        if p["overall"] != dict(rating=None,status="withheld",reasons=["policy_not_finalized"]):
            raise ValueError("OVR policy pending")
    return copy.deepcopy(payload)


def serialize_delivery(payload):
    checked = validate_delivery(payload)
    checked["players"].sort(key=lambda p:(int(p["player_id"]),p["team"],p["competition_name"],p["season_name"]))
    return json.dumps(checked,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(",", ":")) + "\n"


def parse_delivery(text):
    def unique(pairs):
        result = {}
        for k,v in pairs:
            if k in result:
                raise ValueError("duplicate JSON key")
            result[k] = v
        return result
    return validate_delivery(json.loads(text,object_pairs_hook=unique))


def envelope(players, cohort_id):
    return validate_delivery(dict(schema_version=SCHEMA,notice=NOTICE,publication_authorized=False,production_ready=False,
        scope=dict(season_name=SEASON,competitions=list(LEAGUES),role_groups=["MID","CB"],cohort_id=cohort_id),players=players))


def withheld_attribute(reason, pool):
    return dict(rating=None,percentile=None,status="withheld",reasons=[reason],policy=None,comparison_pool=pool)
