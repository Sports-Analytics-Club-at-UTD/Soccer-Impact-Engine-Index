"""Synthetic geometry/identity tests plus bounded audit fixtures; no real scores."""
import ast
import copy
import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src import line_breaking_candidates as module
from src.line_breaking_candidates import (EVIDENCE_COLUMNS,FRAME_COLUMNS,NOTICE,JosephCandidatePolicy,
    LineBreakingError,aggregate_candidates,assess_passes,normalize_point,frame_quality)
from src.identity import PLAYER_KEYS,UnresolvedIdentityError
from src.identity_evidence import SYNTHETIC
from src.metrics.progressive_passes import prepare_passes,flag_progressive
from src.recovery import _extract
from scripts.audit_line_breaking_feasibility import EVENT_COLUMNS,audit_files

AREA=[0.,0.,120.,0.,120.,80.,0.,80.]


def fixture(opponents=3):
    key=dict(id="p1",match_id=10,competition_name="La Liga",season_name="2015/2016")
    p=pd.DataFrame([dict(**key,team="Invented Team",player="Invented Actor",player_id=1,
        x0=30.,y0=40.,x1=70.,y1=40.,completed=True,open_play=True,
        attacking_orientation="positive_x",orientation_source="controlled synthetic orientation")])
    rows=[dict(**key,teammate=True,actor=True,keeper=False,location=[30.,40.],visible_area=AREA.copy())]
    rows += [dict(**key,teammate=False,actor=False,keeper=False,location=[40.+i*5,20.+i],visible_area=AREA.copy()) for i in range(opponents)]
    f=pd.DataFrame(rows,columns=FRAME_COLUMNS)
    e=pd.DataFrame([dict(**key,usable=True,observations_complete=True,one_row_per_visible_player=True,
        attacking_orientation="positive_x",orientation_source="controlled fixture orientation",
        source="invented frame ledger",evidence_kind=SYNTHETIC)],columns=EVIDENCE_COLUMNS)
    policy=JosephCandidatePolicy("joseph-x-strip-synthetic-v1","Joseph >=3 convention; synthetic test only",0.)
    return p,f,e,policy


def run(p,f,e,policy): return assess_passes(p,f,frame_evidence=e,policy=policy)


class LineBreakingCandidateTests(unittest.TestCase):
    def test_two_vs_three_defenders_exact_joseph_threshold(self):
        for count,flag in ((2,False),(3,True),(4,True)):
            row=run(*fixture(count)).iloc[0]
            self.assertEqual(row.assessment_status,"assessed")
            self.assertEqual(row.opponents_bypassed,count)
            self.assertEqual(row.candidate_line_break,flag)

    def test_strict_x_boundaries_and_no_corridor_filter(self):
        p,f,e,policy=fixture()
        f.at[1,"location"]=[30.,10.]; f.at[2,"location"]=[70.,70.]; f.at[3,"location"]=[50.,79.]
        self.assertEqual(run(p,f,e,policy).iloc[0].opponents_bypassed,1)

    def test_goalkeeper_and_teammates_not_counted(self):
        p,f,e,policy=fixture(4)
        f.loc[1,"keeper"]=True; f.loc[2,"teammate"]=True
        self.assertEqual(run(p,f,e,policy).iloc[0].opponents_bypassed,2)

    def test_true_observed_zero_not_missing(self):
        row=run(*fixture(0)).iloc[0]
        self.assertEqual(row.assessment_status,"assessed")
        self.assertEqual(row.opponents_bypassed,0)
        self.assertFalse(row.candidate_line_break)

    def test_no_frame_is_na_not_zero(self):
        p,f,e,policy=fixture()
        row=run(p,f.iloc[:0],e,policy).iloc[0]
        self.assertIn("missing_frame",row.reasons)
        self.assertTrue(pd.isna(row.opponents_bypassed))
        self.assertTrue(pd.isna(row.candidate_line_break))

    def test_duplicate_visible_observations_withheld_not_deduplicated(self):
        p,f,e,policy=fixture(2); f=pd.concat([f,f.iloc[[1]]],ignore_index=True)
        row=run(p,f,e,policy).iloc[0]
        self.assertEqual(row.assessment_status,"unassessed")
        self.assertIn("ambiguous_duplicate_observations",row.reasons)
        self.assertTrue(pd.isna(row.candidate_line_break))

    def test_colocated_conflicting_flags_are_ambiguous(self):
        p,f,e,policy=fixture(2); extra=f.iloc[[1]].copy(); extra["teammate"]=True
        row=run(p,pd.concat([f,extra]),e,policy).iloc[0]
        self.assertIn("ambiguous_colocated_observations",row.reasons)

    def test_unknown_keeper_or_teammate_is_not_inferred(self):
        for column in ("keeper","teammate","actor"):
            p,f,e,policy=fixture(); f[column]=f[column].astype(object); f.at[1,column]=None
            row=run(p,f,e,policy).iloc[0]
            self.assertIn("missing_frame_flags",row.reasons)
            self.assertTrue(pd.isna(row.opponents_bypassed))

    def test_false_string_flag_rejected(self):
        p,f,e,policy=fixture(); f["keeper"]=f.keeper.astype(object); f.at[1,"keeper"]="False"
        with self.assertRaises(LineBreakingError): run(p,f,e,policy)

    def test_orientation_not_inferred_from_actor_alignment(self):
        p,f,e,policy=fixture(); p.loc[0,"attacking_orientation"]=None
        row=run(p,f,e,policy).iloc[0]
        self.assertEqual(row.actor_start_distance,0)
        self.assertIn("unestablished_pass_orientation",row.reasons)
        self.assertTrue(pd.isna(row.opponents_bypassed))

    def test_pandas_missing_flags_and_orientation_stay_unassessed(self):
        p,f,e,policy=fixture(); p["completed"]=p.completed.astype(object); p.at[0,"completed"]=pd.NA
        p.at[0,"attacking_orientation"]=pd.NA
        row=run(p,f,e,policy).iloc[0]
        self.assertIn("unknown_pass_eligibility",row.reasons)
        self.assertIn("unestablished_pass_orientation",row.reasons)
        self.assertTrue(pd.isna(row.candidate_line_break))

    def test_explicit_negative_orientation_normalization(self):
        p,f,e,policy=fixture()
        self.assertEqual(normalize_point([90,40],direction="negative_x"),(30,40))
        p.loc[0,["x0","x1"]]=[90.,50.]; p.loc[0,"attacking_orientation"]="negative_x"
        self.assertTrue(pd.isna(run(p,f,e,policy).iloc[0].opponents_bypassed))
        p.loc[0,["x0","y0"]]=normalize_point([90,40],direction="negative_x")
        p.loc[0,["x1","y1"]]=normalize_point([50,40],direction="negative_x")
        p.loc[0,"attacking_orientation"]="positive_x"
        # The supplied normalized fixture frame remains in the same positive-x view.
        self.assertEqual(run(p,f,e,policy).iloc[0].opponents_bypassed,3)
        with self.assertRaises(LineBreakingError): normalize_point([90,40],direction="guess")

    def test_actor_alignment_tolerance_is_explicit(self):
        p,f,e,policy=fixture(); f.at[0,"location"]=[31.,40.]
        self.assertIn("actor_start_alignment_failed",run(p,f,e,policy).iloc[0].reasons)
        policy=JosephCandidatePolicy("tolerance-test","explicit synthetic choice",1.)
        self.assertEqual(run(p,f,e,policy).iloc[0].opponents_bypassed,3)

    def test_missing_frame_actor_multiple_actors_or_actor_opponent_withheld(self):
        for edit,reason in (("none","missing_or_multiple_actors"),("multiple","missing_or_multiple_actors"),("opponent","actor_team_conflict")):
            p,f,e,policy=fixture()
            if edit=="none": f.loc[0,"actor"]=False
            elif edit=="multiple": f.loc[1,"actor"]=True
            else: f.loc[0,"teammate"]=False
            self.assertIn(reason,run(p,f,e,policy).iloc[0].reasons)

    def test_missing_and_invalid_geometry(self):
        p,f,e,policy=fixture(); p.loc[0,"x0"]=np.nan
        self.assertIn("missing_pass_geometry",run(p,f,e,policy).iloc[0].reasons)
        for value in (float("inf"),-1.,121.,"30",True):
            p,f,e,policy=fixture(); p["x0"]=p.x0.astype(object); p.at[0,"x0"]=value
            with self.assertRaises(LineBreakingError): run(p,f,e,policy)
        p,f,e,policy=fixture(); f.at[1,"location"]=[float("inf"),40.]
        with self.assertRaises(LineBreakingError): run(p,f,e,policy)

    def test_unusable_frame_or_missing_source_attestations_withheld(self):
        for column in ("usable","observations_complete","one_row_per_visible_player"):
            p,f,e,policy=fixture(); e.loc[0,column]=False
            self.assertIn("unestablished_"+column,run(p,f,e,policy).iloc[0].reasons)
        p,f,e,policy=fixture()
        self.assertIn("missing_frame_evidence",run(p,f,e.iloc[:0],policy).iloc[0].reasons)

    def test_missing_or_conflicting_visible_area(self):
        p,f,e,policy=fixture(); f.at[1,"visible_area"]=None
        self.assertIn("missing_or_invalid_visible_area",run(p,f,e,policy).iloc[0].reasons)
        p,f,e,policy=fixture(); f.at[1,"visible_area"]=[0.,0.,110.,0.,110.,80.,0.,80.]
        self.assertIn("conflicting_visible_area",run(p,f,e,policy).iloc[0].reasons)

    def test_unsuccessful_and_non_open_play_are_excluded_not_zero(self):
        for column,reason in (("completed","unsuccessful_pass"),("open_play","non_open_play_pass")):
            p,f,e,policy=fixture(); p.loc[0,column]=False; row=run(p,f,e,policy).iloc[0]
            self.assertEqual(row.assessment_status,"ineligible")
            self.assertIn(reason,row.reasons)
            self.assertTrue(pd.isna(row.candidate_line_break))

    def test_duplicate_or_conflicting_event_and_match_keys_rejected(self):
        p,f,e,policy=fixture()
        with self.assertRaises(LineBreakingError): run(pd.concat([p,p]),f,e,policy)
        with self.assertRaises(LineBreakingError): run(p,f,pd.concat([e,e]),policy)
        f.loc[1,"match_id"]=99
        with self.assertRaises(LineBreakingError): run(p,f,e,policy)

    def test_level_a_progressive_does_not_establish_level_b_break(self):
        p,f,e,policy=fixture(2)
        raw=pd.DataFrame([dict(id="p1",match_id=10,type="Pass",team="Invented Team",player="Invented Actor",
            competition_name="La Liga",season_name="2015/2016",location=[30,40],pass_end_location=[70,40],
            pass_type=None,pass_outcome=None,pass_length=40)])
        a=flag_progressive(prepare_passes(raw).assign(difficulty=1.))
        self.assertTrue(a.iloc[0].progressive)
        self.assertFalse(run(p,f,e,policy).iloc[0].candidate_line_break)
        self.assertTrue(run(*fixture(3)).iloc[0].candidate_line_break)

    def test_failed_ball_recovery_separate_and_not_causal(self):
        raw=pd.DataFrame([dict(id="failed",match_id=10,team="T",player="P",competition_name="La Liga",season_name="2015/2016",type="Ball Recovery",location=[50,40],
            duel_type=None,duel_outcome=None,interception_outcome=None,ball_recovery_recovery_failure=True)])
        self.assertTrue(_extract(raw).empty)
        raw.loc[0,"ball_recovery_recovery_failure"]=False
        self.assertEqual(len(_extract(raw)),1)
        p,f,e,policy=fixture(); result=run(p,f.iloc[:0],e,policy)
        self.assertTrue(pd.isna(result.iloc[0].candidate_line_break))
        p["preceding_recovery_failed"]=True
        with self.assertRaises(LineBreakingError): run(p,f,e,policy)

    def test_row_order_invariance_and_input_immutability(self):
        p,f,e,policy=fixture(); originals=copy.deepcopy((p,f,e))
        a=run(p,f,e,policy); b=run(p,f.iloc[::-1],e,policy)
        pd.testing.assert_frame_equal(a,b,check_exact=True)
        for actual,original in zip((p,f,e),originals): pd.testing.assert_frame_equal(actual,original)

    def test_diagnostic_player_aggregation_conservation_and_transfer_contexts(self):
        p,f,e,policy=fixture(); first=run(p,f,e,policy)
        second=first.copy(); second["id"]="p2"; second["team"]="Transferred Team"; second["match_id"]=11
        second["assessment_status"]="unassessed"; second["reasons"]=[("missing_frame",)]
        second["candidate_line_break"]=pd.array([None],dtype="boolean"); second["opponents_bypassed"]=pd.array([None],dtype="Int64")
        ledger=pd.concat([first,second],ignore_index=True)
        population=ledger[PLAYER_KEYS].drop_duplicates()
        crosswalk=pd.DataFrame(columns=["player_name_raw","player_id","team","competition_name","season_name"])
        result=aggregate_candidates(ledger,crosswalk=crosswalk,population=population)
        self.assertEqual(len(result.players),2)
        self.assertEqual(result.players.observed_passes.sum(),2)
        self.assertEqual(result.players.assessed_eligible_passes.sum(),1)
        self.assertEqual(result.players.unassessed_passes.sum(),1)
        self.assertTrue(pd.isna(result.players.loc[result.players.team.eq("Transferred Team"),"candidate_line_breaks"].iloc[0]))
        self.assertFalse(result.metadata["scope_complete"])
        # Known outsiders remain in the event ledger and accounting.
        outside=aggregate_candidates(ledger,crosswalk=crosswalk,population=population.iloc[[0]])
        self.assertEqual(outside.metadata["outside_population"],1)
        self.assertEqual(len(outside.events),2)
        self.assertEqual(len(outside.players),1)
        self.assertEqual(outside.players.iloc[0].policy_ids,(policy.policy_id,))

    def test_unresolved_identity_and_fabricated_assessment_rejected(self):
        result=run(*fixture()); population=result[PLAYER_KEYS].copy()
        crosswalk=pd.DataFrame(columns=["player_name_raw","player_id","team","competition_name","season_name"])
        unknown=result.drop(columns="player_id")
        with self.assertRaises(UnresolvedIdentityError): aggregate_candidates(unknown,crosswalk=crosswalk,population=population)
        result.loc[0,"opponents_bypassed"]=99
        with self.assertRaises(LineBreakingError): aggregate_candidates(result,crosswalk=crosswalk,population=population)

    def test_aggregation_requires_complete_valid_assessment_schema(self):
        result=run(*fixture()); population=result[PLAYER_KEYS].copy()
        crosswalk=pd.DataFrame(columns=["player_name_raw","player_id","team","competition_name","season_name"])
        with self.assertRaises(LineBreakingError):
            aggregate_candidates(result.drop(columns="frame_rows"),crosswalk=crosswalk,population=population)
        result["candidate_line_break"]=result.candidate_line_break.astype(object); result.at[0,"candidate_line_break"]="True"
        with self.assertRaises(LineBreakingError):
            aggregate_candidates(result,crosswalk=crosswalk,population=population)

    def test_no_ratings_per90_writers_or_network(self):
        source=ast.parse(inspect.getsource(module))
        attrs={n.attr for n in ast.walk(source) if isinstance(n,ast.Attribute)}
        self.assertFalse(attrs&{"to_csv","to_parquet","to_json","read_parquet","read_csv","write_text"})
        self.assertNotIn("candidate_score",run(*fixture()).columns)


class Bounded360AuditTests(unittest.TestCase):
    def test_projected_bounded_join_and_absent_target_frames(self):
        p,f,_,_=fixture()
        event=dict(id="p1",match_id=10,competition_name="La Liga",season_name="2015/2016",type="Pass",
            location=[30.,40.],pass_end_location=[70.,40.],pass_type=None,pass_outcome=None,
            ball_recovery_recovery_failure=None)
        missing=event|dict(id="p2",match_id=11)
        with tempfile.TemporaryDirectory() as folder:
            event_path=Path(folder)/"events.parquet"; frame_path=Path(folder)/"frames.parquet"
            pq.write_table(pa.Table.from_pylist([event,missing]),event_path,row_group_size=1)
            pq.write_table(pa.Table.from_pandas(f,preserve_index=False),frame_path,row_group_size=1)
            before=(event_path.read_bytes(),frame_path.read_bytes())
            out=audit_files(events_path=event_path,frames_path=frame_path,actor_tolerance=0,batch_size=1,scratch_dir=folder)
            self.assertEqual(out["frame_rows"],4); self.assertEqual(out["distinct_frame_events"],1)
            row=out["coverage"][0]
            self.assertEqual(row["pass_events"],2); self.assertEqual(row["pass_events_with_frames"],1)
            self.assertEqual(row["missing_frame_completed_open_play"],1)
            self.assertEqual(row["native_actor_aligned"],1)
            self.assertEqual(row["fully_direction_attested_candidate_passes"],0)
            self.assertFalse(out["production_fifth_attribute_ready"])
            self.assertEqual(before,(event_path.read_bytes(),frame_path.read_bytes()))
            self.assertEqual(len(list(Path(folder).iterdir())),2)

    def test_noncontiguous_frame_blocks_are_not_silently_combined(self):
        _,f,_,_=fixture()
        another=f.copy(); another["id"]="p2"; frames=pd.concat([f,another,f],ignore_index=True)
        event=dict(id="p1",match_id=10,competition_name="La Liga",season_name="2015/2016",type="Pass",location=[30.,40.],
            pass_end_location=[70.,40.],pass_type=None,pass_outcome=None,ball_recovery_recovery_failure=None)
        with tempfile.TemporaryDirectory() as folder:
            ep=Path(folder)/"events.parquet"; fp=Path(folder)/"frames.parquet"
            pq.write_table(pa.Table.from_pylist([event]),ep); pq.write_table(pa.Table.from_pandas(frames,preserve_index=False),fp)
            out=audit_files(events_path=ep,frames_path=fp,actor_tolerance=0,batch_size=1,scratch_dir=folder)
            self.assertEqual(out["repeated_noncontiguous_frame_event_blocks"],1)
            self.assertEqual(out["coverage"][0]["structurally_usable_completed_pass_frames"],0)

    def test_conflicting_frame_context_is_quarantined_without_first_choice(self):
        _,f,_,_=fixture(); other=f.copy(); other["match_id"]=99
        event=dict(id="p1",match_id=10,competition_name="La Liga",season_name="2015/2016",type="Pass",location=[30.,40.],
            pass_end_location=[70.,40.],pass_type=None,pass_outcome=None,ball_recovery_recovery_failure=None)
        with tempfile.TemporaryDirectory() as folder:
            ep=Path(folder)/"events.parquet"; fp=Path(folder)/"frames.parquet"
            pq.write_table(pa.Table.from_pylist([event]),ep)
            pq.write_table(pa.Table.from_pandas(pd.concat([f,other]),preserve_index=False),fp)
            out=audit_files(events_path=ep,frames_path=fp,actor_tolerance=0,batch_size=1,scratch_dir=folder)
            self.assertEqual(out["conflicting_frame_event_contexts"],1)
            self.assertEqual(out["coverage"][0]["pass_events_with_frames"],0)
            self.assertEqual(out["frame_slots"],[])


if __name__=="__main__": unittest.main()
