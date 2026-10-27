"""Synthetic read-only readiness regressions; never score real players."""
from contextlib import redirect_stdout
import ast
import inspect
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import audit_dri_readiness as module
from scripts.audit_dri_readiness import (EVENT_COLUMNS, LEAGUES, LINEUP_COLUMNS, MINUTE_COLUMNS,
    RECOVERY_COLUMNS, ROLE_MINUTES, ReadinessError, audit_files, candidate_population,
    canonical, compare_tables, lineup_exposure_compatibility, main, scan_events, table_integrity, target)
from src.identity import PLAYER_KEYS
from src.metrics.recovery_coverage import EVENT_TYPES


def fixture():
    minutes=[]; recovery=[]; lineups=[]; crosswalk=[]
    for pid,role,value,team in [(1,"CB",900.,"A"),(2,"DM",899.,"A"),(3,"FB",1000.,"B")]:
        key=dict(player_id=pid,team=team,competition_name="La Liga",season_name="2015/2016")
        minutes.append(dict(**key,player_name=f"Actor {pid}",position_group=role,minutes=value,matches=1.,tied_groups=1,
            **{c:value if c=="min_"+role else 0. for c in ROLE_MINUTES}))
        if role in ("CB","DM"):
            for event in EVENT_TYPES:
                recovery.append(dict(**key,position_group=role,minutes=value,matches=1.,event_type=event,
                    count=1,per90=90/value,reportable=True,full_coverage=True,meets_min=value>=900))
        lineups.append(dict(match_id=10,team=team,player_id=pid,player_name=f"Actor {pid}",position="Center Back",
            from_time="00:00",to_time="15:00",from_period=1.,to_period=1.,start_reason="Starting XI",end_reason="Substitution - Off (Tactical)"))
        crosswalk.append(dict(**key,player_name_raw=f"Actor {pid}"))
    base=dict(id="e1",match_id=10,player="Actor 1",team="A",competition_name="La Liga",season_name="2015/2016",
        type="Ball Recovery",location=[10.,10.],duel_type=None,duel_outcome=None,interception_outcome=None,
        ball_recovery_recovery_failure=None,position="Center Back",period=1,minute=1,second=0)
    events=pd.DataFrame([base,base|dict(id="e2",player="Actor 3",team="B"),base|dict(id="e3",player="Unknown")],columns=EVENT_COLUMNS)
    metadata=pd.DataFrame([dict(match_id=10,competition_name="La Liga",season_name="2015/2016")])
    return (pd.DataFrame(minutes,columns=MINUTE_COLUMNS),pd.DataFrame(recovery,columns=RECOVERY_COLUMNS),
            events,pd.DataFrame(crosswalk),pd.DataFrame(lineups,columns=LINEUP_COLUMNS),metadata)


def scan(f,**kwargs):
    m,r,e,c,l,meta=f
    candidates,_=candidate_population(m,r)
    return scan_events(kwargs.pop("path"),c,candidates,l,meta,**kwargs)


def write(path,table):
    pq.write_table(pa.Table.from_pandas(table,preserve_index=False),path,row_group_size=1)


class CandidateReadinessTests(unittest.TestCase):
    def test_exact_scope_isolation(self):
        m,r,*_=fixture()
        extra=m.copy(); extra["season_name"]="2023/2024"
        other=m.copy(); other["competition_name"]="1. Bundesliga"
        self.assertEqual(len(target(pd.concat([m,extra,other]))),3)

    def test_mid_cb_grouping_and_900_boundary(self):
        m,r,*_=fixture()
        c,summary=candidate_population(m,r)
        self.assertEqual(c.score_group.tolist(),["CB","MID"])
        self.assertEqual(c.under_900.tolist(),[False,True])
        self.assertEqual(c.delivered_rules_eligible.tolist(),[True,False])
        self.assertFalse(c.production_ready.any())
        self.assertEqual(summary["arithmetic_disagreements"],0)

    def test_cm_is_mid_and_unrelated_roles_not_scored(self):
        m,r,*_=fixture()
        m.loc[1,"position_group"]="CM"; r.loc[r.player_id.eq(2),"position_group"]="CM"
        c,_=candidate_population(m,r)
        self.assertEqual(c.player_id.tolist(),[1,2])
        self.assertEqual(c.iloc[1].score_group,"MID")

    def test_duplicate_canonical_minutes_and_components_fail(self):
        m,r,*_=fixture()
        for a,b in ((pd.concat([m,m.iloc[[0]]]),r),(m,pd.concat([r,r.iloc[[0]]]))):
            with self.assertRaises(ValueError): candidate_population(a,b)

    def test_missing_component_is_not_zero_filled(self):
        m,r,*_=fixture()
        c,_=candidate_population(m,r.iloc[1:])
        self.assertEqual(c.iloc[0].component_rows,2)
        self.assertFalse(c.iloc[0].complete_components)
        self.assertFalse(c.iloc[0].delivered_rules_eligible)

    def test_flags_do_not_establish_source_verification(self):
        m,r,*_=fixture(); c,_=candidate_population(m,r)
        self.assertTrue(c.iloc[0].delivered_rules_eligible)
        self.assertFalse(c.iloc[0].independently_verified_identity)
        self.assertFalse(c.iloc[0].independently_verified_coverage)
        self.assertFalse(c.iloc[0].independently_aligned_exposure)

    def test_false_coverage_reportability_and_bad_arithmetic_withhold(self):
        for column,value in (("full_coverage",False),("reportable",False),("per90",99.)):
            m,r,*_=fixture()
            if column=="full_coverage": r.loc[r.player_id.eq(1),column]=value
            else: r.loc[0,column]=value
            c,_=candidate_population(m,r)
            self.assertFalse(c.iloc[0].delivered_rules_eligible)

    def test_zero_and_missing_minutes_are_retained(self):
        for value in (0.,np.nan):
            m,r,*_=fixture(); m.loc[0,"minutes"]=value
            r.loc[r.player_id.eq(1),"minutes"]=value; r.loc[r.player_id.eq(1),"per90"]=np.nan
            c,_=candidate_population(m,r)
            self.assertFalse(c.iloc[0].delivered_rules_eligible)

    def test_invalid_counts_and_truthy_flags_rejected(self):
        for column,value in (("count",-1),("count",.5),("per90",float("inf")),("reportable","True")):
            m,r,*_=fixture(); r[column]=r[column].astype(object); r.at[0,column]=value
            with self.assertRaises(ValueError): candidate_population(m,r)

    def test_component_metadata_conflicts_not_selected_arbitrarily(self):
        m,r,*_=fixture(); r.loc[0,"position_group"]="CM"
        with self.assertRaisesRegex(ReadinessError,"conflicting metadata"):
            candidate_population(m,r)

    def test_original_duplicates_countable_without_becoming_replacements(self):
        m,r,*_=fixture()
        self.assertEqual(len(canonical(pd.concat([m,m.iloc[[0]]]),allow_duplicates=True)),4)
        self.assertEqual(len(canonical(pd.concat([r,r.iloc[[0]]]),recovery=True,allow_duplicates=True)),7)
        with self.assertRaises(ReadinessError): compare_tables(r,pd.concat([r,r.iloc[[0]]]),recovery=True)

    def test_input_immutability_and_deterministic_candidates(self):
        m,r,*_=fixture(); a,b=m.copy(deep=True),r.copy(deep=True)
        first,_=candidate_population(m,r)
        second,_=candidate_population(m.iloc[::-1],r.iloc[::-1])
        pd.testing.assert_frame_equal(first,second)
        pd.testing.assert_frame_equal(m,a); pd.testing.assert_frame_equal(r,b)

    def test_contributor_minute_compatibility_never_promotes_exposure(self):
        m,r,_,_,lineups,metadata=fixture()
        c,_=candidate_population(m,r)
        roster=lineups.merge(metadata,on="match_id",validate="many_to_one")
        result=lineup_exposure_compatibility(c,roster)
        self.assertEqual(result["positive_clipped_match_count_disagreements"],0)
        self.assertEqual(result["pooled_minutes_disagreements_under_assumptions"],2)
        self.assertFalse(result["independent_exposure_verified"])
        self.assertFalse(c.independently_aligned_exposure.any())


class EventReadinessTests(unittest.TestCase):
    def exercise(self,f=None,**kwargs):
        f=f or fixture()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"events.parquet"; write(path,f[2])
            return scan(f,path=path,scratch_dir=folder,**kwargs)

    def test_all_events_accounted_selected_outside_unknown(self):
        summary,observed,unknown,*_=self.exercise(batch_size=1)
        self.assertEqual(summary["events"]["selected"],1)
        self.assertEqual(summary["events"]["outside_population"],1)
        self.assertEqual(summary["events"]["unresolved"],1)
        self.assertEqual(summary["events"]["target_rows"],3)
        self.assertEqual(unknown.iloc[0].events,1)
        self.assertEqual(int(observed.observed_count.sum()),2)
        self.assertTrue(summary["row_count_conserved"])

    def test_missing_actor_remains_unresolved(self):
        f=list(fixture()); f[2].loc[2,"player"]=None
        s,_,u,*_=self.exercise(f)
        self.assertEqual(s["events"]["missing_actor_names"],1)
        self.assertEqual(u.iloc[0].reason,"missing_actor_name")

    def test_conflicting_name_key_quarantined(self):
        f=list(fixture()); conflicting=f[3].iloc[[0]].copy(); conflicting["player_id"]=999
        f[3]=pd.concat([f[3],conflicting])
        s,*_=self.exercise(f)
        self.assertEqual(s["lookup"]["conflicting_source_keys"],1)
        self.assertEqual(s["events"]["events_affected_by_conflicting_keys"],1)
        self.assertEqual(s["events"]["unresolved"],2)

    def test_duplicate_ids_across_batches_fail_without_deduplication(self):
        f=list(fixture()); f[2].loc[1,"id"]="e1"
        with self.assertRaisesRegex(ReadinessError,"duplicate global event IDs"):
            self.exercise(f,batch_size=1)

    def test_invalid_identity_rows_are_accounted_not_silently_dropped(self):
        f=list(fixture()); f[2].loc[0,"match_id"]=0
        s,*_=self.exercise(f)
        self.assertEqual(s["events"]["invalid_input"],1)
        self.assertEqual(s["events"]["target_rows"],sum(s["events"][k] for k in ("selected","outside_population","unresolved","invalid_input")))

    def test_out_of_scope_rows_do_not_change_target_population(self):
        f=list(fixture()); e=f[2].iloc[[0]].copy(); e["id"]="outside"; e["season_name"]="2023/2024"
        f[2]=pd.concat([f[2],e])
        s,*_=self.exercise(f)
        self.assertEqual(s["source_rows_scanned"],4)
        self.assertEqual(s["events"]["target_rows"],3)

    def test_metadata_and_lineup_scope_discrepancy_is_observable(self):
        f=list(fixture()); f[5].loc[0,"competition_name"]="Serie A"
        s,*_=self.exercise(f)
        self.assertEqual(s["event_metadata_disagreements"],1)
        # ID/team matching can agree even when competition context is wrong.
        self.assertEqual(s["actor_id_team_match_discrepancies"],0)
        self.assertFalse(s["source_coverage_independently_verified"])

    def test_missing_lineup_actor_and_spelling_are_not_inferred(self):
        f=list(fixture()); f[4]=f[4].iloc[1:]
        s,*_=self.exercise(f)
        self.assertEqual(s["actor_id_team_match_discrepancies"],1)
        self.assertEqual(s["actor_spelling_match_discrepancies"],1)

    def test_contradictory_metadata_rejected(self):
        f=list(fixture()); extra=f[5].copy(); extra["competition_name"]="Serie A"; f[5]=pd.concat([f[5],extra])
        with self.assertRaises(ValueError): self.exercise(f)

    def test_key_bounds_and_projection(self):
        with self.assertRaises(ReadinessError): self.exercise(batch_size=65537)
        with self.assertRaises(ReadinessError): self.exercise(max_summary_keys=1)
        self.assertNotIn("pass_end_location",EVENT_COLUMNS)
        self.assertNotIn("pass_length",EVENT_COLUMNS)


class FileReadinessTests(unittest.TestCase):
    def paths(self,folder):
        m,r,e,c,l,meta=fixture(); tables=dict(events=e,lineups=l,crosswalk=c,minutes=m,recovery=r,
            refresh_minutes=m,refresh_recovery=r,metadata=meta,original_minutes=m,original_recovery=pd.concat([r,r.iloc[[0]]]))
        result={}
        for key,table in tables.items():
            path=Path(folder)/(key+".parquet"); write(path,table); result[key+"_path"]=path
        return result

    def test_end_to_end_readiness_withholds_and_writes_no_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.paths(folder); before={p:p.read_bytes() for p in Path(folder).iterdir()}
            result=audit_files(**paths,batch_size=1,scratch_dir=folder)
            self.assertFalse(result.summary["production_scoring_ready"])
            self.assertEqual(result.summary["candidate_counts"]["total"],2)
            self.assertEqual(result.summary["original_comparison_only"]["duplicate_recovery_keys"],1)
            self.assertEqual(before,{p:p.read_bytes() for p in Path(folder).iterdir()})
            self.assertTrue(result.summary["local_count_reconciliation"]["candidate_delivered_only_rows"]>0)
            self.assertEqual(result.summary["corrected_recovery_integrity"]["arithmetic_disagreements"],0)

    def test_explicit_missing_file_rejected_before_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.paths(folder); paths["original_recovery_path"]=Path(folder)/"missing.parquet"
            with self.assertRaisesRegex(FileNotFoundError,"missing.parquet"):
                audit_files(**paths)

    def test_transfer_contexts_retained_without_auto_reference_choice(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.paths(folder)
            m=pq.read_table(paths["minutes_path"]).to_pandas(); r=pq.read_table(paths["recovery_path"]).to_pandas()
            m.loc[1,"player_id"]=1; m.loc[1,"team"]="C"; m.loc[1,"minutes"]=900
            r.loc[r.player_id.eq(2),["player_id","team","minutes","per90","meets_min"]]=[1,"C",900.,.1,True]
            for key in ("minutes_path","refresh_minutes_path"): write(paths[key],m)
            for key in ("recovery_path","refresh_recovery_path"): write(paths[key],r)
            result=audit_files(**paths,scratch_dir=folder)
            self.assertEqual(result.summary["candidate_counts"]["potential_transfer_contexts"],2)
            self.assertEqual(len(result.candidates),2)
            self.assertFalse(result.candidates.production_ready.any())

    def test_cli_is_terminal_only_and_lists_exact_candidate_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.paths(folder); args=[]
            for key,value in paths.items(): args += ["--"+key.removesuffix("_path").replace("_","-"),str(value)]
            output=io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(args+["--scratch-dir",folder,"--list-candidates"]),0)
            self.assertIn("Exact provisional candidate ledger",output.getvalue())
            self.assertIn('"production_scoring_ready": false',output.getvalue())

    def test_no_scoring_calls_network_or_dataset_output_writers(self):
        tree=ast.parse(inspect.getsource(module))
        calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        attrs={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        self.assertFalse(calls & {"score_dri","fifa_from_zscore","classify_tier","urlopen"})
        self.assertFalse(attrs & {"to_csv","to_parquet","to_json","write_text","write_bytes","rank","std","get_url"})

    def test_cli_exact_ledger_supports_unicode_names_on_windows(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.paths(folder)
            for key in ("minutes_path","refresh_minutes_path"):
                minutes=pq.read_table(paths[key]).to_pandas(); minutes.loc[0,"player_name"]="Actor Ć"
                write(paths[key],minutes)
            args=[]
            for key,value in paths.items(): args += ["--"+key.removesuffix("_path").replace("_","-"),str(value)]
            buffer=io.BytesIO(); stream=io.TextIOWrapper(buffer,encoding="cp1252")
            try:
                with redirect_stdout(stream): main(args+["--scratch-dir",folder,"--list-candidates"])
                stream.flush()
                self.assertIn("Actor Ć",buffer.getvalue().decode("utf-8"))
            finally:
                stream.detach()


if __name__=="__main__": unittest.main()
