"""Controlled synthetic DRI mathematics and evidence regressions; no real scores."""
import ast
from dataclasses import replace
import inspect
import math
import unittest

import numpy as np
import pandas as pd

from src import dri_scoring as module
from src.dri_scoring import (ComparisonPool, DRIError, Evidence, LEAGUES, MEASUREMENT_COLUMNS,
    SCORE_COLUMNS, SeasonScope, classify_tier, fifa_from_zscore, score_dri)
from src.identity import PLAYER_KEYS
from src.identity_evidence import DELIVERED, SYNTHETIC, VERIFIED
from src.metrics.recovery_coverage import EVENT_TYPES


def fixture(rates=None, roles=None):
    """Toy full-season attestations only; match IDs do not denote real fixtures."""
    rates = rates if rates is not None else [(i, i, i) for i in (1, 2, 3, 4)]
    evidence = Evidence(SYNTHETIC, "controlled synthetic fixture", True)
    pool = ComparisonPool("synthetic-four-league-dri-v1", SYNTHETIC, evidence)
    population, measurements = [], []
    for i, values in enumerate(rates):
        league = LEAGUES[i % 4]
        scope = SeasonScope(league, "2015/2016", (100 + i % 4,), True)
        key = dict(player_id=i + 1, team=f"Synthetic Team {i+1}", competition_name=league, season_name="2015/2016")
        population.append(dict(**key, position_group=roles[i] if roles else ["DM", "CM"][i % 2],
            reference_member=True, minutes=900., exposure_scope=scope,
            identity_evidence=evidence, context_evidence=evidence, exposure_evidence=evidence))
        for event, value in zip(EVENT_TYPES, values):
            measurements.append(dict(**key, event_type=event, count=value * 10, minutes=900.,
                per90=float(value), rate_status="ok", numerator_scope=scope, reportable=True,
                reportability_source="synthetic event-completeness check", coverage_evidence=evidence))
    return pd.DataFrame(population), pd.DataFrame(measurements, columns=MEASUREMENT_COLUMNS), pool


def run(pop, measurements, pool):
    return score_dri(pop, measurements, pool=pool)


class DRIScoringTests(unittest.TestCase):
    def test_worked_four_player_percentiles_dri_z_and_unrounded_rating(self):
        result = run(*fixture())
        p = result.players
        expected = [25., 50., 75., 100.]
        for column in ("tackle_percentile", "interception_percentile", "ball_recovery_percentile", "dri", "dri_percentile"):
            self.assertEqual(p[column].tolist(), expected)
        mean, std = 62.5, math.sqrt(3125 / 3)
        self.assertAlmostEqual(result.pools.iloc[0].dri_mean, mean)
        self.assertAlmostEqual(result.pools.iloc[0].dri_sample_std, std)
        for i, dri in enumerate(expected):
            z = (dri - mean) / std
            self.assertAlmostEqual(p.iloc[i].dri_zscore, z)
            self.assertAlmostEqual(p.iloc[i].dri_fifa, 65 + 10*z)
        self.assertNotEqual(p.iloc[0].dri_fifa, round(p.iloc[0].dri_fifa))
        self.assertFalse(result.metadata["publication_authorized"])
        self.assertTrue(result.metadata["synthetic_only"])

    def test_equal_weights_not_raw_count_weighting(self):
        p, m, pool = fixture([(1, 4, 100), (2, 3, 200), (3, 2, 300), (4, 1, 400)])
        result = run(p, m, pool).players
        self.assertAlmostEqual(result.iloc[0].dri, (25+100+25)/3)
        self.assertAlmostEqual(result.iloc[3].dri, (100+25+100)/3)

    def test_average_ties_and_second_dri_percentile(self):
        result = run(*fixture([(1, 1, 1), (1, 1, 1), (3, 3, 3), (4, 4, 4)])).players
        self.assertEqual(result.tackle_percentile.tolist(), [37.5, 37.5, 75., 100.])
        self.assertEqual(result.dri_percentile.tolist(), [37.5, 37.5, 75., 100.])
        self.assertEqual(result.iloc[0].dri_fifa, result.iloc[1].dri_fifa)

    def test_900_inclusive_and_below_threshold_retained(self):
        p, m, pool = fixture()
        p.loc[0, "minutes"] = 899
        m.loc[m.player_id.eq(1), "minutes"] = 899
        m.loc[m.player_id.eq(1), "per90"] = m.loc[m.player_id.eq(1), "count"] / 899 * 90
        result = run(p, m, pool).players
        self.assertIn("below_900_minutes", result.iloc[0].reasons)
        self.assertFalse(result.iloc[0].eligible)
        self.assertTrue(result.iloc[1].eligible)
        self.assertEqual(result.iloc[1].minutes, 900)
        self.assertEqual(len(result), 4)

    def test_mid_cb_distributions_never_shared(self):
        p, m, pool = fixture([(1,1,1), (2,2,2), (100,100,100), (200,200,200)], ["DM", "CM", "CB", "CB"])
        result = run(p, m, pool)
        self.assertEqual(result.players.dri.tolist(), [50.,100.,50.,100.])
        self.assertEqual(result.pools.eligible_count.tolist(), [2,2])
        self.assertEqual(result.players.score_group.tolist(), ["MID","MID","CB","CB"])
        self.assertAlmostEqual(result.players.iloc[0].dri_fifa, result.players.iloc[2].dri_fifa)

    def test_all_four_leagues_share_one_mid_pool(self):
        result = run(*fixture())
        self.assertEqual(result.players.dri.tolist(), [25.,50.,75.,100.])
        pool = result.pools.iloc[0]
        self.assertEqual(pool.competitions, LEAGUES)
        self.assertEqual(pool.league_member_counts, tuple((league,1) for league in LEAGUES))
        self.assertEqual(len(pool.eligible_members), 4)

    def test_wrong_pool_season_or_league_declaration_rejected(self):
        p, m, pool = fixture()
        for bad in (replace(pool, season_name="2023/2024"), replace(pool, competitions=("1. Bundesliga",)),
                    replace(pool, competitions=LEAGUES[:-1]+("La Liga",))):
            with self.subTest(pool=bad), self.assertRaises(DRIError):
                run(p,m,bad)

    def test_wrong_population_season_is_explicit_na(self):
        p, m, pool = fixture()
        p.loc[0,"season_name"] = "2023/2024"
        m.loc[m.player_id.eq(1),"season_name"] = "2023/2024"
        r = run(p,m,pool).players
        self.assertEqual(r.iloc[0].status,"N/A")
        self.assertIn("invalid_pool_membership",r.iloc[0].reasons)
        self.assertTrue(r.iloc[0][SCORE_COLUMNS].isna().all())

    def test_bundesliga_diagnostic_context_cannot_join_target_cohort(self):
        p,m,pool=fixture()
        p.loc[0,"competition_name"]="1. Bundesliga"
        m.loc[m.player_id.eq(1),"competition_name"]="1. Bundesliga"
        self.assertIn("invalid_pool_membership",run(p,m,pool).players.iloc[0].reasons)

    def test_sample_std_ddof_one_not_population_std(self):
        r=run(*fixture([(1,1,1),(2,2,2)])).players
        self.assertAlmostEqual(r.iloc[0].dri_zscore,-1/math.sqrt(2))
        self.assertAlmostEqual(r.iloc[1].dri_zscore,1/math.sqrt(2))

    def test_fifa_clips_both_ends_and_preserves_precision(self):
        self.assertEqual(fifa_from_zscore(-100),1)
        self.assertEqual(fifa_from_zscore(100),99)
        self.assertEqual(fifa_from_zscore(3.4),99)
        self.assertEqual(fifa_from_zscore(-6.4),1)
        self.assertAlmostEqual(fifa_from_zscore(.123456789),66.23456789)
        for v in (None,True,float("nan"),float("inf"),"1",1j):
            with self.subTest(value=v), self.assertRaises(DRIError):
                fifa_from_zscore(v)

    def test_rating_clips_in_real_synthetic_rank_distribution(self):
        rates=[(0,0,0)]*99+[(100,100,100)]
        r=run(*fixture(rates)).players
        self.assertEqual(r.iloc[-1].dri_fifa,99)
        rates=[(0,0,0)]+[(100,100,100)]*99
        self.assertEqual(run(*fixture(rates)).players.iloc[0].dri_fifa,1)

    def test_gold_silver_approved_boundaries_separate_from_scoring(self):
        for score,expected in ((1,None),(74.999,None),(75,"Silver"),(89.999,"Silver"),(90,"Gold"),(99,"Gold"),(100,"Gold"),(None,None),(float("nan"),None)):
            with self.subTest(score=score):
                self.assertEqual(classify_tier(score),expected)
        self.assertNotIn("tier",run(*fixture()).players.columns)

    def test_invalid_tier_values_rejected(self):
        for v in (0,-1,100.001,True,"90",float("inf"),1j):
            with self.subTest(value=v),self.assertRaises(DRIError):
                classify_tier(v)

    def test_missing_component_never_zero_filled(self):
        p,m,pool=fixture()
        m=m.loc[~(m.player_id.eq(1)&m.event_type.eq("Tackle"))]
        r=run(p,m,pool).players.iloc[0]
        self.assertIn("tackle:missing_component",r.reasons)
        self.assertTrue(pd.isna(r.tackle_per90))
        self.assertTrue(r[SCORE_COLUMNS].isna().all())

    def test_missing_and_zero_minutes_have_distinct_na_reasons(self):
        for value,status,reason in ((None,"missing_minutes","missing_minutes"),(0,"zero_minutes","zero_minutes")):
            with self.subTest(value=value):
                p,m,pool=fixture()
                p["minutes"]=p.minutes.astype(object)
                p.loc[0,"minutes"]=value
                m["minutes"]=m.minutes.astype(object)
                select=m.player_id.eq(1)
                m.loc[select,"minutes"]=value
                m.loc[select,"per90"]=np.nan
                m.loc[select,"rate_status"]=status
                r=run(p,m,pool).players.iloc[0]
                self.assertIn(reason,r.reasons)
                self.assertEqual(r.status,"N/A")

    def test_invalid_numeric_measurements_rejected_without_coercion(self):
        for field in ("count","per90","minutes"):
            for value in (-1,float("inf"),True,"12",1j,10**400):
                with self.subTest(field=field,value=value):
                    p,m,pool=fixture()
                    m[field]=m[field].astype(object)
                    m.at[0,field]=value
                    with self.assertRaises(DRIError):
                        run(p,m,pool)

    def test_fractional_and_inexact_counts_rejected(self):
        for value in (.5,2**63,float(2**53)):
            p,m,pool=fixture()
            m["count"]=m["count"].astype(object)
            m.at[0,"count"]=value
            with self.subTest(value=value),self.assertRaises(DRIError):
                run(p,m,pool)

    def test_invalid_population_minutes_rejected(self):
        for value in (-1,float("inf"),True,"900"):
            p,m,pool=fixture()
            p["minutes"]=p.minutes.astype(object)
            p.at[0,"minutes"]=value
            with self.subTest(value=value),self.assertRaises(DRIError):
                run(p,m,pool)

    def test_duplicate_population_and_recovery_keys_rejected(self):
        p,m,pool=fixture()
        with self.assertRaises(DRIError):
            run(pd.concat([p,p.iloc[[0]]]),m,pool)
        with self.assertRaises(DRIError):
            run(p,pd.concat([m,m.iloc[[0]]]),pool)

    def test_alias_collisions_rejected(self):
        p,m,pool=fixture()
        duplicate=p.iloc[[0]].copy()
        p.loc[0,"team"]="Marseille"
        duplicate.loc[0,"team"]="Olympique de Marseille"
        with self.assertRaises(DRIError):
            run(pd.concat([p,duplicate]),m,pool)

    def test_unknown_measurement_identity_rejected(self):
        p,m,pool=fixture()
        m.loc[0,"player_id"]=99
        with self.assertRaises(DRIError):
            run(p,m,pool)

    def test_exact_int64_identity_retained_and_unsafe_float_rejected(self):
        p,m,pool=fixture()
        p.loc[0,"player_id"]=2**63-1
        m.loc[m.player_id.eq(1),"player_id"]=2**63-1
        self.assertEqual(int(run(p,m,pool).players.iloc[-1].player_id),2**63-1)
        p["player_id"]=p.player_id.astype(float)
        with self.assertRaises(DRIError):
            run(p,m,pool)

    def test_unsupported_per90_keeps_na(self):
        p,m,pool=fixture()
        m.loc[0,"per90"]=np.nan
        m.loc[0,"rate_status"]="unsupported"
        self.assertIn("tackle:unsupported_per90",run(p,m,pool).players.iloc[0].reasons)

    def test_contradictory_rates_and_exposure_rejected(self):
        for field,value in (("per90",99.),("minutes",950.),("rate_status","zero_minutes")):
            p,m,pool=fixture()
            m.loc[0,field]=value
            with self.subTest(field=field),self.assertRaises(DRIError):
                run(p,m,pool)

    def test_scope_mismatch_and_partial_season_withheld(self):
        p,m,pool=fixture()
        old=m.at[0,"numerator_scope"]
        m.at[0,"numerator_scope"]=replace(old,match_ids=(999,))
        self.assertIn("tackle:numerator_exposure_scope_mismatch",run(p,m,pool).players.iloc[0].reasons)
        p.at[0,"exposure_scope"]=replace(old,full_season=False)
        self.assertIn("unsupported_full_season_exposure",run(p,m,pool).players.iloc[0].reasons)

    def test_scope_unknown_or_wrong_context_withheld(self):
        p,m,pool=fixture()
        p.at[0,"exposure_scope"]=None
        self.assertIn("unsupported_full_season_exposure",run(p,m,pool).players.iloc[0].reasons)
        p,m,pool=fixture()
        p.at[0,"exposure_scope"]=replace(p.at[0,"exposure_scope"],season_name="2023/2024")
        self.assertIn("exposure_context_mismatch",run(p,m,pool).players.iloc[0].reasons)

    def test_malformed_match_scopes_rejected(self):
        for ids in ((1,1),(2,1),(True,),(1.0,),(),[1]):
            p,m,pool=fixture()
            p.at[0,"exposure_scope"]=replace(p.at[0,"exposure_scope"],match_ids=ids)
            with self.subTest(ids=ids),self.assertRaises(DRIError):
                run(p,m,pool)

    def test_component_reportability_requires_explicit_evidence(self):
        for field,value in (("reportable",False),("reportable",None),("reportability_source",None)):
            p,m,pool=fixture()
            m[field]=m[field].astype(object)
            m.at[0,field]=value
            self.assertIn("tackle:unreportable_or_unverified",run(p,m,pool).players.iloc[0].reasons)

    def test_no_truthy_string_evidence_flags(self):
        p,m,pool=fixture()
        m["reportable"]=m.reportable.astype(object)
        m.at[0,"reportable"]="False"
        with self.assertRaises(DRIError):
            run(p,m,pool)
        with self.assertRaises(DRIError):
            run(p,m,replace(pool,coverage_evidence=Evidence(SYNTHETIC,"fixture","True")))

    def test_unverified_incomplete_or_provisional_coverage_withheld(self):
        for evidence in (None,Evidence(DELIVERED,"delivery",True),Evidence("PROVISIONAL","events",True),Evidence(SYNTHETIC,"fixture",False)):
            p,m,pool=fixture()
            m.at[0,"coverage_evidence"]=evidence
            with self.subTest(evidence=evidence):
                self.assertIn("tackle:unverified_or_incomplete_coverage",run(p,m,pool).players.iloc[0].reasons)
                r=run(p,m,replace(pool,coverage_evidence=evidence))
                self.assertTrue(r.players.status.eq("N/A").all())

    def test_identity_context_and_exposure_each_need_trust(self):
        for field in ("identity_evidence","context_evidence","exposure_evidence"):
            p,m,pool=fixture()
            p.at[0,field]=Evidence("PROVISIONAL","caller supplied mapping",True)
            self.assertIn("unverified_"+field,run(p,m,pool).players.iloc[0].reasons)

    def test_synthetic_evidence_cannot_enter_verified_pool(self):
        p,m,pool=fixture()
        r=run(p,m,replace(pool,evidence_kind=VERIFIED,coverage_evidence=Evidence(VERIFIED,"caller verified manifest reference",True)))
        self.assertTrue(r.players.status.eq("N/A").all())
        with self.assertRaises(DRIError):
            run(p,m,replace(pool,evidence_kind="PROVISIONAL"))

    def test_singleton_empty_and_constant_pools_withhold_all_scores(self):
        for rates,reason in (([(1,1,1)],"insufficient_reference_pool"),
                            ([(1,1,1)]*4,"constant_dri_reference_pool"),
                            ([(1,1,1)]*6,"constant_dri_reference_pool"),
                            ([(1,1,1)]*7,"constant_dri_reference_pool")):
            r=run(*fixture(rates))
            self.assertTrue(r.players[SCORE_COLUMNS].isna().all().all())
            self.assertEqual(r.players.iloc[0].reasons,(reason,))
        p,m,pool=fixture()
        r=run(p.iloc[:0],m.iloc[:0],pool)
        self.assertTrue(r.players.empty)
        self.assertEqual(r.pools.eligible_count.tolist(),[0,0])

    def test_missing_component_values_are_not_observed_zero(self):
        p,m,pool=fixture()
        m.loc[0,"count"]=np.nan
        m.loc[0,"per90"]=np.nan
        self.assertIn("tackle:missing_measurement",run(p,m,pool).players.iloc[0].reasons)
        zero=run(*fixture([(0,0,0),(1,1,1),(2,2,2),(3,3,3)])).players.iloc[0]
        self.assertTrue(zero.eligible)
        self.assertEqual(zero.tackle_per90,0)
        self.assertEqual(zero.tackle_percentile,25)

    def test_verified_gate_uses_only_explicit_caller_attestations(self):
        # Mock upstream verification in a controlled fixture, not verification
        # of real data. The module must never infer these attestations itself.
        p,m,pool=fixture()
        evidence=Evidence(VERIFIED,"mock upstream verifier in synthetic test",True)
        for name in ("identity_evidence","context_evidence","exposure_evidence"):
            p[name]=[evidence]*len(p)
        m["coverage_evidence"]=[evidence]*len(m)
        r=run(p,m,replace(pool,evidence_kind=VERIFIED,coverage_evidence=evidence))
        self.assertTrue(r.players.status.eq("scored").all())
        self.assertFalse(r.metadata["publication_authorized"])
        self.assertFalse(r.metadata["synthetic_only"])

    def test_opposing_ranks_do_not_create_float_noise_distinctions(self):
        r=run(*fixture([(1,2,3),(2,3,1),(3,1,2)]))
        self.assertEqual(r.pools.iloc[0].reason,"constant_dri_reference_pool")
        self.assertTrue(r.players.dri_fifa.isna().all())

    def test_missing_ambiguous_and_unsupported_roles(self):
        for role,reason in ((None,"missing_role"),(pd.NA,"missing_role"),("AMBIGUOUS","ambiguous_role"),("GK","unsupported_role")):
            p,m,pool=fixture()
            p.at[0,"position_group"]=role
            with self.subTest(role=role):
                self.assertIn(reason,run(p,m,pool).players.iloc[0].reasons)

    def test_transfers_require_explicit_single_reference_context(self):
        p,m,pool=fixture()
        p.loc[1,"player_id"]=1
        m.loc[m.player_id.eq(2),"player_id"]=1
        with self.assertRaisesRegex(DRIError,"multiple reference contexts"):
            run(p,m,pool)
        p.loc[1,"reference_member"]=False
        r=run(p,m,pool)
        self.assertEqual(len(r.players),4)
        self.assertEqual(r.pools.iloc[0].eligible_count,3)
        self.assertEqual(sum(key[0]==1 for key in r.pools.iloc[0].eligible_members),1)
        transferred=r.players.loc[r.players.team.eq("Synthetic Team 2")].iloc[0]
        self.assertEqual(transferred.reasons,("not_reference_member",))
        self.assertTrue(transferred[SCORE_COLUMNS].isna().all())

    def test_nonreference_context_does_not_change_percentiles(self):
        p,m,pool=fixture()
        p.loc[3,"reference_member"]=False
        r=run(p,m,pool).players
        self.assertAlmostEqual(r.iloc[0].dri,100/3)
        self.assertTrue(pd.isna(r.iloc[3].dri))

    def test_all_applicable_reasons_retained(self):
        p,m,pool=fixture()
        p.loc[0,"position_group"]="AMBIGUOUS"
        p.loc[0,"minutes"]=800
        m.loc[m.player_id.eq(1),"minutes"]=800
        m.loc[m.player_id.eq(1),"per90"]=m.loc[m.player_id.eq(1),"count"] / 800 * 90
        m.at[0,"reportable"]=False
        reasons=run(p,m,pool).players.iloc[0].reasons
        self.assertIn("ambiguous_role",reasons)
        self.assertIn("below_900_minutes",reasons)
        self.assertIn("tackle:unreportable_or_unverified",reasons)

    def test_input_immutability_row_order_invariance_and_repeatability(self):
        p,m,pool=fixture()
        old_p,old_m=p.copy(deep=True),m.copy(deep=True)
        first=run(p,m,pool)
        second=run(p.sample(frac=1,random_state=5),m.sample(frac=1,random_state=7),pool)
        pd.testing.assert_frame_equal(first.players,second.players,check_exact=True)
        pd.testing.assert_frame_equal(first.pools,second.pools,check_exact=True)
        pd.testing.assert_frame_equal(first.players,run(p,m,pool).players,check_exact=True)
        pd.testing.assert_frame_equal(p,old_p)
        pd.testing.assert_frame_equal(m,old_m)

    def test_malformed_schema_and_unresolved_identities_fail_closed(self):
        p,m,pool=fixture()
        for bad in (p.drop(columns="position_group"),p.assign(unexpected=1),p.rename(columns={"team":"player_name"})):
            with self.subTest(columns=bad.columns.tolist()),self.assertRaises(DRIError):
                run(bad,m,pool)
        p.loc[0,"player_id"]=pd.NA
        with self.assertRaises(DRIError):
            run(p,m,pool)

    def test_no_io_writers_or_final_ovr_generation(self):
        source=inspect.getsource(module)
        tree=ast.parse(source)
        names={node.attr for node in ast.walk(tree) if isinstance(node,ast.Attribute)}
        self.assertFalse(names & {"read_parquet","read_csv","to_parquet","to_csv","to_json","write_text","write_bytes"})
        self.assertNotIn("open",{node.id for node in ast.walk(tree) if isinstance(node,ast.Name)})
        self.assertNotIn("ovr",{c.lower() for c in run(*fixture()).players.columns})
        self.assertNotIn("__main__",source)


if __name__ == "__main__":
    unittest.main()
