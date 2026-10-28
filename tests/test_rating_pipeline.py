"""Offline end-to-end candidate and nonpublication regressions."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest

import pandas as pd

from scripts.preview_rating_pipeline import fixture, demonstration
from src import press_scoring as press
from src.defensive_candidates import evaluate_defensive_candidates
from src.dri_scoring import Evidence, SEASON, LEAGUES
from src.identity_evidence import VERIFIED, SYNTHETIC
from src.rating_assembly import PlayerContext, ATTRIBUTES
from src.rating_delivery import serialize_delivery, parse_delivery, validate_delivery, archetype
from src.rating_pipeline import synthetic_rating_delivery, source_readiness_delivery, readiness_rating_delivery, transfer_inputs
from src.transfer_aggregation import aggregate_transfer, TransferPolicy, COUNTS, require_unique_memberships


def transfer_fixture(pid=3057, cross=False):
    a=PlayerContext(pid,"Newcastle United" if pid==3057 else "Lorient",LEAGUES[1] if not cross else LEAGUES[3],SEASON)
    b=PlayerContext(pid,"Swansea City" if pid==3057 else "Sunderland",LEAGUES[1],SEASON)
    rows=[dict(context=c,role="DM",match_id=700000001+i,minutes=m,
        counts=dict(zip(COUNTS,(n,n*2,n*3,40,20+i*10,0,0))),source=f"invented-transfer-match-{i}",synthetic=True)
        for i,(c,m,n) in enumerate(((a,300.,10),(b,600.,30)))]
    policy=TransferPolicy("synthetic-combine/v1",True,cross,b,"synthetic-four-league/v1",True,"explicit synthetic club-combination experiment")
    return rows,policy


class PipelineTests(unittest.TestCase):
    def run_fixture(self, f):
        return synthetic_rating_delivery(**f)

    def test_full_precision_raw_to_contract_fixture(self):
        p=demonstration();first=p["players"][0]
        self.assertEqual(tuple(first["attributes"]),ATTRIBUTES)
        self.assertAlmostEqual(first["attributes"]["tackles"]["rating"],53.38104996137775)
        self.assertEqual(first["attributes"]["tackles"]["percentile"],25)
        self.assertEqual(first["attributes"]["press_resistance"]["percentile"],25)
        self.assertNotEqual(first["attributes"]["tackles"]["rating"],round(first["attributes"]["tackles"]["rating"]))
        self.assertEqual(first["overall"]["rating"],None)
        self.assertEqual(first["attributes"]["line_breaking_passes"]["rating"],None)
        self.assertFalse(p["production_ready"])

    def test_serialization_roundtrip_and_committed_cross_language_fixture(self):
        p=demonstration();s=serialize_delivery(p)
        self.assertEqual(parse_delivery(s),p)
        self.assertEqual(s,(Path(__file__).resolve().parents[1]/"frontend/tests/fixtures/syntheticRatings.json").read_text(encoding="utf-8"))
        p["players"].reverse()
        self.assertEqual(s,serialize_delivery(p))

    def test_input_immutability_and_order(self):
        f=fixture();before=f["population"].copy(deep=True)
        original=serialize_delivery(self.run_fixture(f))
        pd.testing.assert_frame_equal(before,f["population"])
        for k in ("population","measurements","actions"):
            f[k]=f[k].sample(frac=1,random_state=4).reset_index(drop=True)
        self.assertEqual(original,serialize_delivery(self.run_fixture(f)))

    def test_explicit_policy_none_withholds(self):
        f=fixture();f["defensive_policy"]=None;f["press_policy"]=None
        p=self.run_fixture(f)
        self.assertTrue(all(a["rating"] is None for r in p["players"] for a in r["attributes"].values()))

    def test_real_evidence_cannot_score(self):
        for which in ("pool","evidence"):
            f=fixture();f[which]=replace(f[which],**({"evidence_kind":VERIFIED} if which=="pool" else {"kind":VERIFIED}))
            with self.subTest(which=which),self.assertRaises(ValueError): self.run_fixture(f)

    def test_press_percentile_formula_not_misrepresented_as_rating(self):
        f=fixture();f["press_policy"]=replace(f["press_policy"],formula=press.PERCENTILE)
        with self.assertRaises(ValueError):self.run_fixture(f)

    def test_component_transform_is_per90_not_aggregate_or_percentile(self):
        f=fixture()
        for i,v in enumerate((1,2,3,100)):
            mask=(f["measurements"].player_id==900000001+i)&f["measurements"].event_type.eq("Tackle")
            f["measurements"].loc[mask,"count"]=v*10
            f["measurements"].loc[mask,"per90"]=float(v)
        p=self.run_fixture(f)["players"]
        self.assertEqual(p[2]["attributes"]["tackles"]["percentile"],75)
        self.assertNotEqual(p[2]["attributes"]["tackles"]["rating"],p[2]["attributes"]["interceptions"]["rating"])

    def test_constant_component_does_not_manufacture_65(self):
        f=fixture();mask=f["measurements"].event_type.eq("Tackle")
        f["measurements"].loc[mask,"count"]=10;f["measurements"].loc[mask,"per90"]=1.
        p=self.run_fixture(f)["players"][0]
        self.assertEqual(p["attributes"]["tackles"]["reasons"],["constant_component_pool"])
        self.assertIsNotNone(p["attributes"]["interceptions"]["rating"])

    def test_missing_metric_stays_null(self):
        f=fixture();f["measurements"]=f["measurements"].iloc[1:]
        p=self.run_fixture(f)["players"][0]
        self.assertIsNone(p["attributes"]["tackles"]["rating"])

    def test_900_and_missing_minutes(self):
        for minutes, available in ((899.,False),(900.,True),(None,False)):
            f=fixture();f["population"].loc[0,"minutes"]=minutes
            mask=f["measurements"].player_id.eq(900000001)
            f["measurements"].loc[mask,"minutes"]=minutes
            f["measurements"].loc[mask,"per90"] = float("nan") if minutes is None else f["measurements"].loc[mask,"count"]/minutes*90
            f["measurements"].loc[mask,"rate_status"]="missing_minutes" if minutes is None else "ok"
            p=self.run_fixture(f)["players"][0]
            with self.subTest(minutes=minutes):
                self.assertEqual(p["attributes"]["tackles"]["rating"] is not None,available)
                self.assertEqual(p["attributes"]["press_resistance"]["rating"] is not None,available)

    def test_press_action_threshold_29_30(self):
        for attempts,available in ((29,False),(30,True)):
            f=fixture();f["actions"].loc[0,"pressured_pass_attempts"]=attempts
            p=self.run_fixture(f)["players"][0]
            self.assertEqual(p["attributes"]["press_resistance"]["rating"] is not None,available)

    def test_press_policy_threshold_change_is_explicit(self):
        f=fixture();f["press_policy"]=replace(f["press_policy"],min_actions=50)
        p=self.run_fixture(f)["players"][0]
        self.assertIsNone(p["attributes"]["press_resistance"]["rating"])
        self.assertEqual(p["attributes"]["press_resistance"]["policy"]["min_actions"],50)

    def test_unverified_actor_and_incomplete_fixture_evidence_withhold(self):
        for field in ("identity_evidence","exposure_evidence"):
            f=fixture();f["population"].at[0,field]=None
            p=self.run_fixture(f)["players"][0]
            self.assertTrue(all(p["attributes"][aid]["rating"] is None for aid in ATTRIBUTES))
        f=fixture();f["pool"]=replace(f["pool"],coverage_evidence=replace(f["pool"].coverage_evidence,complete=False))
        self.assertTrue(all(a["rating"] is None for p in self.run_fixture(f)["players"] for a in p["attributes"].values()))

    def test_partial_exposure_scope_withholds_defense_and_rejects_press(self):
        f=fixture();f["population"].at[0,"exposure_scope"]=replace(f["population"].at[0,"exposure_scope"],full_season=False)
        with self.assertRaises(ValueError):self.run_fixture(f)

    def test_missing_pool_evidence_withholds_instead_of_crashing(self):
        f=fixture();f["pool"]=replace(f["pool"],coverage_evidence=None)
        self.assertTrue(all(a["rating"] is None for p in self.run_fixture(f)["players"] for a in p["attributes"].values()))

    def test_wrong_season_and_role(self):
        for field,value in (("season_name","2023/2024"),("position_group","GK")):
            f=fixture();f["population"].loc[0,field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_fixture(f)
        f=fixture();f["population"].loc[0,"position_group"]=None
        p=self.run_fixture(f)["players"][0]
        self.assertIsNone(p["role_group"])
        self.assertTrue(all(a["rating"] is None for a in p["attributes"].values()))

    def test_duplicate_reference_membership(self):
        f=fixture();f["population"].loc[1,"player_id"]=900000001
        with self.assertRaises(ValueError):self.run_fixture(f)

    def test_exact_int64_id_survives_json(self):
        f=fixture();big=2**63-1
        for name in ("population","measurements","actions"):
            f[name].loc[f[name].player_id.eq(900000001),"player_id"]=big
        old=next(c for c in f["names"] if c.player_id==900000001)
        f["names"][replace(old,player_id=big)]=f["names"].pop(old)
        p=self.run_fixture(f)
        self.assertEqual(parse_delivery(serialize_delivery(p))["players"][-1]["player_id"],str(big))

    def test_archetype_boundaries_and_independent_numbers(self):
        for rating,pct,tier in ((95,40,None),(60,96,"Gold"),(60,90,"Gold"),(99,75,"Silver"),(99,74.999,None)):
            p=demonstration();r=p["players"][0]
            for a in r["attributes"].values():
                if a["rating"] is not None:a["percentile"]=0
            r["attributes"]["tackles"].update(rating=rating,percentile=pct)
            r["archetype"]=archetype(r["attributes"],r["role_group"])
            self.assertEqual(validate_delivery(p)["players"][0]["archetype"]["tier"],tier)

    def test_contract_rejects_promotions_and_malformed_records(self):
        changes=[lambda d:d.update(production_ready=True),lambda d:d.update(publication_authorized=True),
            lambda d:d["players"][0].update(classification="verified"),
            lambda d:d["players"][0]["eligibility"].update(scoring_approved=True),
            lambda d:d["players"][0]["attributes"]["tackles"].update(rating=True),
            lambda d:d["players"][0]["attributes"]["tackles"].update(rating=float("nan")),
            lambda d:d["players"][0]["attributes"]["tackles"].update(percentile=101),
            lambda d:d["players"][0]["attributes"]["tackles"].update(comparison_pool="wrong"),
            lambda d:d["players"][0]["overall"].update(rating=65),
            lambda d:d["players"].append(copy.deepcopy(d["players"][0])),
            lambda d:d["players"][0]["attributes"].pop("recoveries"),
            lambda d:d["players"][0].update(player_id=900000001),
            lambda d:d["players"][0]["eligibility"].update(contradictory_sample_appearance_ids=["1"])]
        for mutate in changes:
            p=demonstration();mutate(p)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):validate_delivery(p)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):parse_delivery('{"schema_version":"a","schema_version":"b"}')

    def test_source_accounting_to_withheld_delivery(self):
        fixtures=[dict(match_id=1,competition_name=LEAGUES[0],season_name=SEASON)]
        context=dict(player_id=12,team="Invented",competition_name=LEAGUES[0],season_name=SEASON)
        c=PlayerContext(**context)
        p=source_readiness_delivery(fixtures,fixtures,[],[dict(**context,minutes=900.)],[],
            names={c:"Invented accounting actor"},roles={c:"DM"},source="synthetic accounting test, not original source",cohort_id="not-a-certified-cohort")
        r=p["players"][0];self.assertTrue(r["eligibility"]["delivered_table_eligible"])
        self.assertFalse(r["eligibility"]["season_exposure_verified"])
        self.assertTrue(all(a["rating"] is None for a in r["attributes"].values()))
        self.assertIn("incomplete_fixture_coverage",r["eligibility"]["reasons"])
        r["classification"]="verified"
        with self.assertRaises(ValueError):validate_delivery(p)

    def test_structural_sample_and_conflict_never_certify_source_or_exposure(self):
        from test_season_verification import inputs
        data=list(inputs())
        for index in (0,1,3,4):
            for r in data[index]:r["competition_name"]=LEAGUES[0]
        contexts=[PlayerContext(**{k:r[k] for k in ("player_id","team","competition_name","season_name")}) for r in data[3]]
        kwargs=dict(names={c:"Synthetic accounting actor" for c in contexts},roles={c:"CB" for c in contexts},source="synthetic byte-bound schema report",cohort_id="accounting-fixture")
        for status in ("STRUCTURALLY_VALID","CONFLICTING_EVIDENCE"):
            data[4][0]["players"][0]["validation"]["status"]=status
            p=source_readiness_delivery(*data,**kwargs)["players"][0]
            self.assertFalse(p["eligibility"]["independent_source_supported"])
            self.assertFalse(p["eligibility"]["season_exposure_verified"])
            self.assertTrue(all(a["rating"] is None for a in p["attributes"].values()))


REAL_READINESS=Path(__file__).resolve().parents[1]/"data/source-evidence/phase1b-2026-10-27/analysis/season-readiness.json"
REAL_MINUTES=Path(__file__).resolve().parents[1]/"data/validation/arpit-2026-10-21/player_minutes.parquet"


@unittest.skipUnless(REAL_READINESS.is_file() and REAL_MINUTES.is_file(),"optional local readiness/minutes unavailable")
class RealReadinessDeliveryTests(unittest.TestCase):
    def test_all_549_real_contexts_remain_withheld_in_memory(self):
        from src.identity import normalize_team_names
        r=json.loads(REAL_READINESS.read_text(encoding="utf-8"))
        table=pd.read_parquet(REAL_MINUTES)
        table["team"]=normalize_team_names(table.team)
        names={};roles={}
        for row in table.to_dict("records"):
            c=PlayerContext(**{k:row[k] for k in ("player_id","team","competition_name","season_name")})
            names[c]=row["player_name"];roles[c]=row["position_group"]
        p=readiness_rating_delivery(r,names=names,roles=roles,source=str(REAL_READINESS),cohort_id="withheld-current-549/v1")
        self.assertEqual(len(p["players"]),549)
        self.assertTrue(all(a["rating"] is None and a["percentile"] is None for row in p["players"] for a in row["attributes"].values()))
        self.assertTrue(all(row["minutes"] is None for row in p["players"]))
        self.assertFalse(p["publication_authorized"])
        # This JSON remains in memory and is never written as a player export.
        self.assertEqual(len(parse_delivery(serialize_delivery(p))["players"]),549)


class TransferTests(unittest.TestCase):
    def test_shelvey_weighted_counts_and_minutes(self):
        rows,policy=transfer_fixture();before=copy.deepcopy(rows)
        r=aggregate_transfer(rows,policy=policy)
        self.assertEqual(r["minutes"],900);self.assertEqual(r["counts"]["tackles"],40)
        self.assertEqual(r["per90"]["tackles"],4);self.assertEqual(len(r["contributions"]),2)
        self.assertTrue(r["reference_member"]);self.assertEqual(rows,before)
        self.assertEqual(r,aggregate_transfer(list(reversed(rows)),policy=policy))

    def test_kone_cross_league_explicit(self):
        rows,policy=transfer_fixture(13286,True)
        self.assertEqual(aggregate_transfer(rows,policy=policy)["status"],"synthetic_combined")
        self.assertIn("cross_league_transfer_not_permitted",aggregate_transfer(rows,policy=replace(policy,allow_cross_league=False))["reasons"])

    def test_missing_inapplicable_policy_withholds(self):
        rows,p=transfer_fixture()
        for policy in (None,replace(p,combine_clubs=False),replace(p,reference_context=replace(p.reference_context,team="Other"))):
            r=aggregate_transfer(rows,policy=policy)
            self.assertIsNone(r["counts"]);self.assertIsNone(r["minutes"]);self.assertFalse(r["reference_member"])

    def test_duplicates_rejected_and_membership_unique(self):
        rows,p=transfer_fixture()
        with self.assertRaises(ValueError):aggregate_transfer(rows+[rows[0]],policy=p)
        r=aggregate_transfer(rows,policy=p)
        with self.assertRaises(ValueError):require_unique_memberships([r,r])

    def test_missing_exposure_and_real_lineage_withhold(self):
        for field,value in (("minutes",None),("synthetic",False)):
            rows,p=transfer_fixture();rows[0][field]=value
            r=aggregate_transfer(rows,policy=p)
            self.assertIsNone(r["minutes"]);self.assertIsNone(r["per90"])

    def test_season_role_and_identity_mismatch_withhold(self):
        for field,value in (("season_name","2023/2024"),("player_id",99)):
            rows,p=transfer_fixture();rows[0]["context"]=replace(rows[0]["context"],**{field:value})
            self.assertEqual(aggregate_transfer(rows,policy=p)["status"],"withheld")
        rows,p=transfer_fixture();rows[0]["role"]="CB"
        self.assertEqual(aggregate_transfer(rows,policy=p)["status"],"withheld")

    def test_reference_membership_not_automatic(self):
        rows,p=transfer_fixture();r=aggregate_transfer(rows,policy=replace(p,admit_reference=False))
        self.assertEqual(r["status"],"synthetic_combined");self.assertFalse(r["reference_member"])

    def test_modified_aggregate_cannot_override_original_ledger(self):
        f=fixture();rows,p=transfer_fixture();r=aggregate_transfer(rows,policy=p)
        r["counts"]["tackles"]+=1
        with self.assertRaises(ValueError):transfer_inputs(r,evidence=f["pool"].coverage_evidence,press_evidence=f["evidence"])

    def test_transfer_flows_into_scoring_and_retains_contexts(self):
        f=fixture();rows,policy=transfer_fixture(13286,True);r=aggregate_transfer(rows,policy=policy)
        pop,metrics,actions=transfer_inputs(r,evidence=f["pool"].coverage_evidence,press_evidence=f["evidence"])
        for key,frame in (("population",pop),("measurements",metrics),("actions",actions)):
            f[key]=pd.concat([f[key],frame],ignore_index=True)
        f["names"][r["context"]]="Synthetic transfer actor, modeled on 13286"
        f["transfers"]=[r]
        p=synthetic_rating_delivery(**f)["players"][0]
        self.assertEqual(p["player_id"],"13286");self.assertEqual(len(p["contexts"]),2)
        self.assertEqual(p["minutes"],900);self.assertIsNotNone(p["attributes"]["tackles"]["rating"])
        f["measurements"].loc[f["measurements"].player_id.eq(13286),"count"]+=1
        with self.assertRaises(ValueError):synthetic_rating_delivery(**f)


if __name__ == "__main__":unittest.main()
