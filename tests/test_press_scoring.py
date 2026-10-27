"""Synthetic candidate press policies; no real datasets or score writers."""
import ast
from dataclasses import replace
import inspect
import math
import unittest

import numpy as np
import pandas as pd

from src import press_scoring as module
from src.identity import PLAYER_KEYS
from src.identity_evidence import SYNTHETIC, VERIFIED, DELIVERED
from src.metrics.press_actions import COUNT_COLS, DERIVED_COLS, add_completion_rates
from src.press_resistance import integrate_press_resistance
from src.press_scoring import (ACTION_COLUMNS, FIFA, PERCENTILE, LEAGUES, NOTICE,
    CandidatePolicy, ComparisonPools, PressScope, PressScoringError, SyntheticEvidence,
    evaluate_press_candidates)


def fixture(counts=None,roles=None):
    """Invented actors, match IDs and full-season scope declarations for tests only."""
    counts=counts if counts is not None else [(40,n,0,0) for n in (10,20,30,40)]
    evidence=SyntheticEvidence(SYNTHETIC,"controlled-fixture-v1","invented ledger in test_press_scoring",True)
    policy=CandidatePolicy("synthetic-policy-v1","explicit test policy; not team approval",PERCENTILE,
        30,900.,"separate_mid_cb",2,"one_context_per_player")
    pop=[];actions=[];members=[]
    for i,values in enumerate(counts):
        key=dict(player_id=i+1,team=f"Invented Team {i+1}",competition_name=LEAGUES[i%4],season_name="2015/2016")
        scope=PressScope(key["competition_name"],key["season_name"],(100+i,),True)
        role=roles[i] if roles else ("DM" if i%2==0 else "CM")
        pop.append(dict(**key,position_group=role,minutes=900.,exposure_scope=scope,
            identity_evidence=evidence,context_evidence=evidence,exposure_evidence=evidence))
        actions.append(dict(**key,**dict(zip(COUNT_COLS,values)),numerator_scope=scope,coverage_evidence=evidence))
        members.append(dict(**key,pool_group="CB" if role=="CB" else "MID"))
    return pd.DataFrame(pop,columns=module.POPULATION_COLUMNS),pd.DataFrame(actions,columns=ACTION_COLUMNS),ComparisonPools(
        "invented-population-v1","2015/2016",LEAGUES,pd.DataFrame(members,columns=[*PLAYER_KEYS,"pool_group"]),evidence),evidence,policy


def run(pop,actions,pools,evidence,policy):
    return evaluate_press_candidates(pop,actions,pools=pools,evidence=evidence,policy=policy)


class PressScoringTests(unittest.TestCase):
    def test_worked_percentile_example_four_leagues_jointly(self):
        result=run(*fixture()); p=result.players
        self.assertEqual(p.press_resistance_rate.tolist(),[25,50,75,100])
        self.assertEqual(p.candidate_percentile.tolist(),[25,50,75,100])
        self.assertEqual(p.candidate_score.tolist(),[25,50,75,100])
        self.assertEqual(result.pools.iloc[0].eligible_count,4)
        self.assertEqual(result.metadata["competitions"],LEAGUES)
        self.assertTrue(p.candidate_zscore.isna().all())

    def test_worked_sample_z_fifa_example_no_rounding(self):
        f=list(fixture()); f[4]=replace(f[4],formula=FIFA)
        result=run(*f)
        mean,std=62.5,math.sqrt(3125/3)
        for i,value in enumerate((25,50,75,100)):
            z=(value-mean)/std
            self.assertAlmostEqual(result.players.iloc[i].candidate_zscore,z)
            self.assertAlmostEqual(result.players.iloc[i].candidate_score,65+10*z)
        self.assertAlmostEqual(result.pools.iloc[0].sample_std,std)
        self.assertNotEqual(result.players.iloc[0].candidate_score,round(result.players.iloc[0].candidate_score))

    def test_attempt_weighted_not_mean_of_pass_and_dribble_percentages(self):
        result=run(*fixture([(10,10,30,0),(40,20,0,0)])).players.iloc[0]
        self.assertEqual(result.pressured_pass_completion_rate,100)
        self.assertEqual(result.pressured_dribble_completion_rate,0)
        self.assertEqual(result.press_resistance_rate,25)
        self.assertEqual(result.pressured_actions,40)

    def test_actual_m3a_event_integration_parity(self):
        pop,actions,pools,evidence,policy=fixture([(2,1,2,1),(40,30,0,0)])
        key=pop.iloc[0][PLAYER_KEYS].to_dict()
        events=pd.DataFrame([dict(id=str(i),player="Invented Actor",**{k:key[k] for k in PLAYER_KEYS if k!="player_id"},
            type=kind,under_pressure=True,pass_outcome=outcome if kind=="Pass" else None,
            dribble_outcome=outcome if kind=="Dribble" else None) for i,(kind,outcome) in enumerate(
                [("Pass",None),("Pass","Incomplete"),("Dribble","Complete"),("Dribble",None)])])
        crosswalk=pd.DataFrame([dict(**key,player_name_raw="Invented Actor")])
        integrated=integrate_press_resistance(events,crosswalk,pop[PLAYER_KEYS]).totals
        for c in [*COUNT_COLS,*DERIVED_COLS]: actions.loc[0,c]=integrated.iloc[0][c]
        # Optional supplied totals on the other row must also be internally true.
        second=add_completion_rates(actions.loc[[1],COUNT_COLS]).iloc[0]
        for c in DERIVED_COLS: actions.loc[1,c]=second[c]
        result=run(pop,actions,pools,evidence,replace(policy,min_actions=0)).players
        for c in [*COUNT_COLS,*DERIVED_COLS]: self.assertEqual(result.iloc[0][c],integrated.iloc[0][c])

    def test_average_tie_percentiles(self):
        p=run(*fixture([(40,10,0,0),(40,10,0,0),(40,30,0,0),(40,40,0,0)])).players
        self.assertEqual(p.candidate_percentile.tolist(),[37.5,37.5,75,100])

    def test_mid_and_cb_are_separate_when_requested(self):
        p=run(*fixture([(40,10,0,0),(40,20,0,0),(40,30,0,0),(40,40,0,0)],["DM","CM","CB","CB"])).players
        self.assertEqual(p.candidate_score.tolist(),[50,100,50,100])

    def test_combined_pool_requires_explicit_alternative_policy(self):
        f=list(fixture(roles=["DM","CM","CB","CB"]))
        members=f[2].members.copy(); members["pool_group"]="COMBINED"; f[2]=replace(f[2],members=members)
        with self.assertRaises(PressScoringError): run(*f)
        f[4]=replace(f[4],pooling="combined_mid_cb")
        self.assertEqual(run(*f).players.candidate_score.tolist(),[25,50,75,100])

    def test_no_automatic_candidate_policy(self):
        f=list(fixture()); f[4]=None; result=run(*f)
        self.assertTrue(result.players.candidate_score.isna().all())
        self.assertTrue(result.players.reasons.map(lambda r:"candidate_policy_not_selected" in r).all())
        self.assertEqual(result.players.press_resistance_rate.tolist(),[25,50,75,100])
        with self.assertRaises(TypeError): evaluate_press_candidates(f[0],f[1],pools=f[2],evidence=f[3])
        with self.assertRaises(TypeError): CandidatePolicy("missing fields","source",PERCENTILE)

    def test_unknown_policy_and_invalid_explicit_thresholds_rejected(self):
        f=fixture()
        for changes in (dict(formula="unknown"),dict(min_actions=-1),dict(min_actions=30.),dict(min_actions=True),
                        dict(min_minutes=None),dict(min_minutes=float("inf")),dict(min_pool_size=1),dict(pooling="auto"),dict(reference_unit="guess")):
            with self.subTest(changes=changes),self.assertRaises(PressScoringError):
                run(*f[:4],replace(f[4],**changes))

    def test_action_30_and_50_boundaries(self):
        f=fixture([(29,20,0,0),(30,21,0,0),(49,30,0,0),(50,40,0,0)])
        p=run(*f).players
        self.assertEqual(p.eligible.tolist(),[False,True,True,True])
        p=run(*f[:4],replace(f[4],min_actions=50)).players
        self.assertEqual(p.eligible.tolist(),[False,False,False,True])
        self.assertIn("insufficient_candidate_pool",p.iloc[-1].reasons)
        self.assertIn("below_candidate_min_actions",p.iloc[1].reasons)

    def test_candidate_900_boundary_not_inherited_default(self):
        f=list(fixture()); f[0].loc[0,"minutes"]=899
        result=run(*f).players
        self.assertIn("below_candidate_min_minutes",result.iloc[0].reasons)
        self.assertTrue(result.iloc[1].eligible)
        f[4]=replace(f[4],min_minutes=450)
        self.assertTrue(run(*f).players.iloc[0].eligible)

    def test_observed_zero_completions_score_but_zero_attempts_do_not(self):
        p=run(*fixture([(40,0,0,0),(40,20,0,0),(0,0,0,0)])).players
        self.assertEqual(p.iloc[0].press_resistance_rate,0)
        self.assertEqual(p.iloc[0].candidate_score,50)
        self.assertTrue(pd.isna(p.iloc[2].press_resistance_rate))
        self.assertIn("zero_attempts",p.iloc[2].reasons)
        self.assertTrue(pd.isna(p.iloc[2].candidate_score))

    def test_missing_actions_not_invented_zero(self):
        f=list(fixture()); f[1]=f[1].iloc[1:]; result=run(*f).players
        self.assertIn("missing_actions",result.iloc[0].reasons)
        self.assertTrue(pd.isna(result.iloc[0].pressured_actions))
        self.assertEqual(len(result),4)

    def test_partial_counts_are_withheld(self):
        f=list(fixture()); f[1][COUNT_COLS[0]]=f[1][COUNT_COLS[0]].astype(object); f[1].at[0,COUNT_COLS[0]]=None
        p=run(*f).players.iloc[0]
        self.assertIn("incomplete_action_counts",p.reasons)
        self.assertTrue(pd.isna(p.press_resistance_rate))
        self.assertEqual(p.pressured_pass_completed,10)

    def test_completions_over_attempts_rejected_even_with_another_missing_count(self):
        f=list(fixture()); f[1].loc[0,COUNT_COLS[1]]=41
        for partial in (False,True):
            if partial:
                f[1][COUNT_COLS[2]]=f[1][COUNT_COLS[2]].astype(object); f[1].at[0,COUNT_COLS[2]]=None
            with self.assertRaises(PressScoringError): run(*f)

    def test_negative_noninteger_boolean_string_complex_infinite_counts_rejected(self):
        for value in (-1,.5,True,"40",1j,float("inf"),2**63,float(2**53),10**400):
            f=list(fixture()); f[1][COUNT_COLS[0]]=f[1][COUNT_COLS[0]].astype(object); f[1].at[0,COUNT_COLS[0]]=value
            with self.subTest(value=value),self.assertRaises(PressScoringError): run(*f)

    def test_exact_int64_counts_and_combined_overflow(self):
        f=fixture([(2**63-1,2**63-2,0,0),(40,20,0,0)])
        p=run(*f).players
        self.assertEqual(int(p.iloc[0].pressured_pass_attempts),2**63-1)
        self.assertEqual(int(p.iloc[0].successful_pressured_actions),2**63-2)
        f=list(f); f[1].loc[0,"pressured_dribble_attempts"]=1
        with self.assertRaisesRegex(PressScoringError,"overflows"): run(*f)

    def test_exact_fraction_ranking_not_float_shadow_rounding(self):
        result=run(*fixture([(2**63-1,2**63-2,0,0),(2**63-1,2**63-3,0,0)]))
        self.assertEqual(result.players.candidate_percentile.tolist(),[100,50])

    def test_contradictory_supplied_totals_or_percentages_rejected(self):
        for column,value in (("pressured_actions",41),("successful_pressured_actions",11),("press_resistance_rate",50),
                             ("pressured_pass_completion_rate",None),("pressured_dribble_completion_rate",0)):
            f=list(fixture()); expected=add_completion_rates(f[1][COUNT_COLS])
            for c in DERIVED_COLS: f[1][c]=expected[c]
            f[1][column]=f[1][column].astype(object); f[1].at[0,column]=value
            with self.subTest(column=column),self.assertRaises(PressScoringError): run(*f)

    def test_missing_zero_unreliable_and_invalid_exposure(self):
        for value,reason in ((None,"missing_exposure"),(0,"nonpositive_exposure")):
            f=list(fixture()); f[0]["minutes"]=f[0].minutes.astype(object); f[0].at[0,"minutes"]=value
            self.assertIn(reason,run(*f).players.iloc[0].reasons)
        for value in (-1,float("inf"),True,"900",1j):
            f=list(fixture()); f[0]["minutes"]=f[0].minutes.astype(object); f[0].at[0,"minutes"]=value
            with self.assertRaises(PressScoringError): run(*f)
        f=list(fixture()); f[0].at[0,"exposure_evidence"]=None
        self.assertIn("missing_or_incomplete_exposure_evidence",run(*f).players.iloc[0].reasons)

    def test_incomplete_evidence_withholds_without_changing_measurement(self):
        for field in ("identity_evidence","context_evidence","exposure_evidence"):
            f=list(fixture()); f[0].at[0,field]=replace(f[3],complete=False)
            p=run(*f).players.iloc[0]
            self.assertEqual(p.press_resistance_rate,25)
            self.assertTrue(pd.isna(p.candidate_score))
        f=list(fixture()); f[1].at[0,"coverage_evidence"]=None
        self.assertIn("incomplete_press_coverage",run(*f).players.iloc[0].reasons)
        f=list(fixture()); f[2]=replace(f[2],coverage_evidence=replace(f[3],complete=False))
        self.assertTrue(run(*f).players.candidate_score.isna().all())
        f=list(fixture()); f[3]=replace(f[3],complete=False)
        self.assertTrue(run(*f).players.candidate_score.isna().all())

    def test_real_verified_delivered_and_provisional_kinds_rejected_everywhere(self):
        for kind in (VERIFIED,DELIVERED,"PROVISIONAL"):
            for location in ("dataset","pool","identity","press"):
                f=list(fixture()); bad=replace(f[3],kind=kind)
                if location=="dataset": f[3]=bad
                elif location=="pool": f[2]=replace(f[2],coverage_evidence=bad)
                elif location=="identity": f[0].at[0,"identity_evidence"]=bad
                else: f[1].at[0,"coverage_evidence"]=bad
                with self.subTest(kind=kind,location=location),self.assertRaisesRegex(PressScoringError,"synthetic-only"):
                    run(*f)

    def test_mixed_synthetic_fixture_ids_and_truthy_completeness_rejected(self):
        for bad in (dict(fixture_id="different"),dict(complete="True"),dict(source="")):
            f=list(fixture()); f[1].at[0,"coverage_evidence"]=replace(f[3],**bad)
            with self.assertRaises(PressScoringError): run(*f)

    def test_scopes_must_match_and_be_full_season(self):
        for changes in (dict(match_ids=(999,)),dict(season_name="2023/2024"),dict(full_season=False),dict(match_ids=(1,1)),dict(match_ids=(True,))):
            f=list(fixture()); f[1].at[0,"numerator_scope"]=replace(f[1].at[0,"numerator_scope"],**changes)
            with self.subTest(changes=changes),self.assertRaises(PressScoringError): run(*f)
        for table,column,reason in ((0,"exposure_scope","missing_exposure_scope"),(1,"numerator_scope","missing_numerator_scope")):
            f=list(fixture()); f[table].at[0,column]=None
            self.assertIn(reason,run(*f).players.iloc[0].reasons)

    def test_wrong_season_competition_role_and_cross_position_membership_rejected(self):
        for table,column,value in ((0,"season_name","2023/2024"),(1,"competition_name","1. Bundesliga"),(0,"position_group","GK")):
            f=list(fixture()); f[table].loc[0,column]=value
            with self.assertRaises(PressScoringError): run(*f)
        f=list(fixture()); member=f[2].members.copy(); member.loc[0,"pool_group"]="CB"; f[2]=replace(f[2],members=member)
        with self.assertRaisesRegex(PressScoringError,"cross-position"): run(*f)

    def test_explicit_four_league_definition_required(self):
        f=fixture()
        for p in (replace(f[2],season_name="2023/2024"),replace(f[2],competitions=LEAGUES[:-1]),replace(f[2],competitions=LEAGUES[:-1]+("La Liga",))):
            with self.assertRaises(PressScoringError): run(f[0],f[1],p,f[3],f[4])

    def test_conflicting_match_contexts_across_players_rejected(self):
        f=list(fixture())
        for table,column in ((0,"exposure_scope"),(1,"numerator_scope")):
            f[table].at[1,column]=replace(f[table].at[1,column],match_ids=(100,))
        with self.assertRaisesRegex(PressScoringError,"contradictory competition"):
            run(*f)

    def test_normalized_team_alias_collision_rejected(self):
        f=list(fixture()); f[0].loc[0,"team"]="Marseille"
        duplicate=f[0].iloc[[0]].copy(); duplicate.loc[0,"team"]="Olympique de Marseille"
        f[0]=pd.concat([f[0],duplicate])
        with self.assertRaises(PressScoringError): run(*f)

    def test_missing_and_ambiguous_roles_retained_but_not_scored(self):
        for role,reason in ((None,"missing_role"),("AMBIGUOUS","ambiguous_role")):
            f=list(fixture()); f[0].loc[0,"position_group"]=role
            self.assertIn(reason,run(*f).players.iloc[0].reasons)

    def test_duplicate_canonical_actions_population_and_pool_members_rejected(self):
        f=fixture()
        for location in (0,1,2):
            values=list(f)
            if location<2: values[location]=pd.concat([values[location],values[location].iloc[[0]]])
            else: values[2]=replace(values[2],members=pd.concat([values[2].members,values[2].members.iloc[[0]]]))
            with self.assertRaises(PressScoringError): run(*values)

    def test_unknown_action_or_pool_context_rejected(self):
        for location in ("actions","members"):
            f=list(fixture())
            if location=="actions": f[1].loc[0,"player_id"]=999
            else:
                members=f[2].members.copy(); members.loc[0,"player_id"]=999; f[2]=replace(f[2],members=members)
            with self.assertRaises(PressScoringError): run(*f)

    def test_nonmember_is_retained_with_na(self):
        f=list(fixture()); f[2]=replace(f[2],members=f[2].members.iloc[1:])
        p=run(*f).players
        self.assertEqual(len(p),4)
        self.assertIn("not_pool_member",p.iloc[0].reasons)

    def test_transfer_reference_unit_is_explicit_and_contexts_never_collapsed(self):
        f=list(fixture()); f[0].loc[1,"player_id"]=1; f[1].loc[1,"player_id"]=1
        members=f[2].members.copy(); members.loc[1,"player_id"]=1; f[2]=replace(f[2],members=members)
        with self.assertRaisesRegex(PressScoringError,"reference contexts"): run(*f)
        f[4]=replace(f[4],reference_unit="canonical_context")
        result=run(*f)
        self.assertEqual(len(result.players),4)
        self.assertEqual(result.pools.iloc[0].eligible_count,4)

    def test_singleton_empty_constant_and_explicit_pool_minimum(self):
        for values in ([(40,20,0,0)],[(40,20,0,0)]*6):
            for formula in (PERCENTILE,FIFA):
                f=list(fixture(values)); f[4]=replace(f[4],formula=formula)
                self.assertTrue(run(*f).players.candidate_score.isna().all())
        f=list(fixture()); f[4]=replace(f[4],min_pool_size=5)
        self.assertTrue(run(*f).players.candidate_score.isna().all())
        f=list(fixture([])); self.assertTrue(run(*f).players.empty)

    def test_percentile_lower_bound_and_fifa_both_clips(self):
        f=list(fixture([(200,i,0,0) for i in range(1,201)])); f[4]=replace(f[4],min_actions=0)
        self.assertEqual(run(*f).players.iloc[0].candidate_score,1)
        for values,expected,index in (([(100,0,0,0)]+[(100,100,0,0)]*99,1,0),
                                      ([(100,0,0,0)]*99+[(100,100,0,0)],99,-1)):
            f=list(fixture(values)); f[4]=replace(f[4],formula=FIFA)
            self.assertEqual(run(*f).players.iloc[index].candidate_score,expected)

    def test_exact_id_and_unsafe_float_handling(self):
        f=list(fixture())
        for t in (f[0],f[1],f[2].members): t.loc[0,"player_id"]=2**63-1
        self.assertEqual(int(run(*f).players.iloc[-1].player_id),2**63-1)
        f[0]["player_id"]=f[0].player_id.astype(float)
        with self.assertRaises(PressScoringError): run(*f)

    def test_input_immutability_repeatability_and_row_order_invariance(self):
        f=fixture(); before=[t.copy(deep=True) for t in (f[0],f[1],f[2].members)]
        a=run(*f); b=run(f[0].iloc[::-1],f[1].iloc[::-1],replace(f[2],members=f[2].members.iloc[::-1]),f[3],f[4])
        pd.testing.assert_frame_equal(a.players,b.players,check_exact=True)
        pd.testing.assert_frame_equal(a.pools,b.pools,check_exact=True)
        pd.testing.assert_frame_equal(a.players,run(*f).players,check_exact=True)
        for old,actual in zip(before,(f[0],f[1],f[2].members)): pd.testing.assert_frame_equal(old,actual)

    def test_source_and_policy_provenance_preserved_without_approval(self):
        result=run(*fixture())
        self.assertEqual(result.metadata["policy"]["min_actions"],30)
        self.assertFalse(result.metadata["policy_finalized"])
        self.assertFalse(result.metadata["production_scoring_supported"])
        self.assertFalse(result.metadata["publication_authorized"])
        self.assertTrue(result.players.notice.eq(NOTICE).all())
        self.assertEqual(result.players.iloc[0].source_provenance["dataset"]["kind"],SYNTHETIC)
        self.assertEqual(result.players.iloc[0].policy_status,"NOT_FINALIZED")
        self.assertEqual(result.players.iloc[0].policy_provenance["min_actions"],30)
        self.assertEqual(result.players.iloc[0].exposure_scope,result.players.iloc[0].numerator_scope)
        self.assertEqual(result.pools.iloc[0].dataset_evidence["kind"],SYNTHETIC)

    def test_no_ovr_tiers_io_network_or_production_scoring_calls(self):
        result=run(*fixture()); self.assertFalse(set(result.players)&{"ovr","overall","tier"})
        tree=ast.parse(inspect.getsource(module))
        names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
        attrs={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        self.assertFalse(names & {"open","score_dri","classify_tier","requests","urlopen","__main__"})
        self.assertFalse(attrs & {"to_csv","to_parquet","to_json","read_parquet","read_csv","write_text"})


if __name__=="__main__": unittest.main()
