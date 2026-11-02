"""Synthetic reuse regressions; original-source checks are a separate audit."""
import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from src.identity import PLAYER_KEYS, IdentityError
from src.metrics import recovery_coverage as legacy
from src.metrics import safe_recovery as safe


def event(**kw):
    return dict(id="a", player_id=1, player="Same", team="Club", competition_name="League",
                season_name="2015/2016", event_type="Ball Recovery", zone="defensive", **kw) if not kw else event() | kw


def events(*rows):
    return pd.DataFrame(rows or [event()])


def exposure(value=90.):
    return events()[PLAYER_KEYS].assign(minutes=value)


class SafeRecoveryTests(unittest.TestCase):
    def test_old_defects_and_safe_outputs(self):
        rec=events(event(),event(id="b",player_id=2))
        self.assertEqual(legacy.recovery_counts(rec)[0]["count"].tolist(),[2])
        totals,_=safe.recovery_counts(rec)
        self.assertEqual(totals.player_id.tolist(),[1,2]);self.assertEqual(totals["count"].tolist(),[1,1])
        self.assertEqual({pid:set(g.id) for pid,g in rec.groupby("player_id")},{1:{"a"},2:{"b"}})
        count=totals.iloc[:1];dup=pd.concat([exposure(),exposure()])
        self.assertEqual(len(legacy.add_per90(count,dup,PLAYER_KEYS)),2)
        with self.assertRaisesRegex(safe.RecoveryInputError,"duplicate join keys"):safe.add_per90(count,dup,PLAYER_KEYS)

    def test_spelling_unicode_and_apostrophe_variants(self):
        for name in ["Fernando Luiz Roza","José 李","D''Angelo","D’Angelo"]:
            with self.subTest(name=name):
                rec=events(event(player="D'Angelo"),event(id="b",player=name))
                totals,zones=safe.recovery_counts(rec)
                self.assertEqual(totals["count"].tolist(),[2]);self.assertEqual(zones["count"].tolist(),[2])

    def test_contexts_separate_without_cross_attribution(self):
        for change in [dict(player_id=2,team="Other"),dict(team="Other"),dict(season_name="2016/2017"),dict(competition_name="Other")]:
            with self.subTest(change=change):
                rec=events(event(),event(id="b",**change));t,z=safe.recovery_counts(rec)
                self.assertEqual(len(t),2);self.assertEqual(t["count"].tolist(),[1,1]);self.assertEqual(z["count"].sum(),2)
                self.assertEqual(set(t[PLAYER_KEYS].itertuples(index=False,name=None)),set(rec[PLAYER_KEYS].itertuples(index=False,name=None)))

    def test_missing_identity_columns(self):
        for col in [*PLAYER_KEYS,"id","event_type","zone"]:
            with self.subTest(col=col),self.assertRaises((IdentityError,ValueError)):safe.recovery_counts(events().drop(columns=col))

    def test_missing_null_invalid_ids(self):
        for value in [None,np.nan,0,-1,True,"1",1.5]:
            with self.subTest(value=value),self.assertRaises(IdentityError):safe.recovery_counts(events(event(player_id=value)))

    def test_duplicate_uuid_and_conflicting_identity(self):
        for row in [event(),event(player_id=2),event(team="Other")]:
            with self.subTest(row=row),self.assertRaisesRegex(ValueError,"duplicate event UUIDs"):safe.recovery_counts(events(event(),row))

    def test_unsafe_grouping_explicitly_fails(self):
        for group in [legacy.DEFAULT_GROUP,["player_id"],[*PLAYER_KEYS,"player_id"],"player_id",[*PLAYER_KEYS,"event_type"]]:
            with self.subTest(group=group),self.assertRaises(ValueError):safe.recovery_counts(events(),group)

    def test_canonical_legacy_equivalence(self):
        rec=events(event(),event(id="b",zone=None),event(id="c",event_type="Tackle"))
        for a,b in zip(safe.recovery_counts(rec),legacy.recovery_counts(rec,PLAYER_KEYS)):assert_frame_equal(a,b)

    def test_event_type_and_zone_conservation(self):
        rec=events(*[event(id=str(i),event_type=kind,zone=zone) for i,(kind,zone) in enumerate((k,z) for k in legacy.EVENT_TYPES for z in ["defensive","defensive","attacking",None])])
        totals,zones=safe.recovery_counts(rec)
        for kind in legacy.EVENT_TYPES:
            self.assertEqual(totals.loc[totals.event_type.eq(kind),"count"].sum(),4)
            self.assertEqual(zones.loc[zones.event_type.eq(kind),"count"].sum(),3)
        self.assertEqual(zones.loc[zones.zone.eq("defensive"),"count"].sum(),6)

    def test_empty_events(self):
        t,z=safe.recovery_counts(events().iloc[:0]);self.assertTrue(t.empty and z.empty)
        self.assertEqual(t.columns.tolist(),[*PLAYER_KEYS,"event_type","count"])

    def test_null_contexts(self):
        for col in PLAYER_KEYS[1:]:
            with self.subTest(col=col),self.assertRaises((IdentityError,ValueError)):safe.recovery_counts(events(event(**{col:None})))

    def test_unknown_event_type(self):
        with self.assertRaisesRegex(ValueError,"event_type"):safe.recovery_counts(events(event(event_type="Pressure")))

    def test_one_to_one_and_precision(self):
        t,_=safe.recovery_counts(events());m=exposure(91.123456789)
        assert_frame_equal(safe.add_per90(t,m,PLAYER_KEYS),legacy.add_per90(t,m,PLAYER_KEYS))

    def test_many_to_one_repeated_types_and_zones(self):
        rec=events(event(),event(id="b",event_type="Tackle"),event(id="c",zone="attacking"))
        for table in safe.recovery_counts(rec):
            result=safe.add_per90(table,exposure(),PLAYER_KEYS)
            self.assertEqual(len(result),len(table));self.assertEqual(result.per90.tolist(),table["count"].tolist())
            assert_frame_equal(result[table.columns],table)

    def test_missing_zero_threshold_minutes(self):
        t,_=safe.recovery_counts(events())
        for value,threshold,expected in [(np.nan,None,None),(0.,None,None),(899.,900.,None),(900.,900.,.1)]:
            with self.subTest(value=value):
                result=safe.add_per90(t,exposure(value),PLAYER_KEYS,threshold)
                self.assertEqual(result["count"].tolist(),[1])
                if expected is None:self.assertTrue(result.per90.isna().all())
                else:self.assertEqual(result.per90.iloc[0],expected)

    def test_unmatched_and_empty_minute_tables(self):
        t,_=safe.recovery_counts(events())
        for m in [exposure().assign(player_id=2),exposure().iloc[:0]]:
            result=safe.add_per90(t,m,PLAYER_KEYS);self.assertEqual(len(result),1)
            self.assertTrue(result.minutes.isna().all() and result.per90.isna().all())

    def test_extra_unmatched_minutes_do_not_add_rows(self):
        t,_=safe.recovery_counts(events());m=pd.concat([exposure(),exposure().assign(player_id=2)])
        self.assertEqual(len(safe.add_per90(t,m,PLAYER_KEYS)),1)

    def test_empty_counts(self):
        t,_=safe.recovery_counts(events().iloc[:0]);self.assertTrue(safe.add_per90(t,exposure(),PLAYER_KEYS).empty)

    def test_negative_nonfinite_nonnumeric_minutes(self):
        t,_=safe.recovery_counts(events())
        for v in [-1.,np.inf,-np.inf,"90",True]:
            with self.subTest(value=v),self.assertRaises(ValueError):safe.add_per90(t,exposure(v),PLAYER_KEYS)

    def test_null_join_keys(self):
        t,_=safe.recovery_counts(events())
        for col in PLAYER_KEYS:
            for side in ["counts","minutes"]:
                a,b=t.copy(),exposure();(a if side=="counts" else b)[col]=None
                with self.subTest(col=col,side=side),self.assertRaises((ValueError,IdentityError)):safe.add_per90(a,b,PLAYER_KEYS)

    def test_missing_join_columns(self):
        t,_=safe.recovery_counts(events())
        for a,b in [(t.drop(columns="count"),exposure()),(t,exposure().drop(columns="minutes")),(t,exposure().drop(columns="team"))]:
            with self.assertRaises(IdentityError):safe.add_per90(a,b,PLAYER_KEYS)

    def test_unsafe_join_keys(self):
        t,_=safe.recovery_counts(events())
        with self.assertRaisesRegex(ValueError,"PLAYER_KEYS"):safe.add_per90(t,exposure(),["player_id"])

    def test_existing_rate_columns_rejected(self):
        t,_=safe.recovery_counts(events())
        for col in ["minutes","per90"]:
            with self.assertRaises(ValueError):safe.add_per90(t.assign(**{col:1}),exposure(),PLAYER_KEYS)

    def test_invalid_numerators_and_thresholds(self):
        t,_=safe.recovery_counts(events())
        for value in [-1.,np.nan,np.inf,"1",True]:
            with self.subTest(count=value),self.assertRaises(ValueError):safe.add_per90(t.assign(count=value),exposure(),PLAYER_KEYS)
        for threshold in [-1.,np.inf,np.nan,True,"900",[900]]:
            with self.subTest(threshold=threshold),self.assertRaises(ValueError):safe.add_per90(t,exposure(),PLAYER_KEYS,threshold)

    def test_no_input_mutation(self):
        r=events();m=exposure();before=r.copy(deep=True);mb=m.copy(deep=True)
        t,_=safe.recovery_counts(r);safe.add_per90(t,m,PLAYER_KEYS)
        assert_frame_equal(r,before);assert_frame_equal(m,mb)

    def test_fixture_specific_group_and_join(self):
        r=events(event(match_id=1),event(id="b",match_id=2));keys=[*PLAYER_KEYS,"match_id"]
        t,_=safe.recovery_counts(r,keys);m=r[keys].assign(minutes=[45.,90.])
        self.assertEqual(safe.add_per90(t,m,keys).per90.tolist(),[2.,1.])

    def test_duplicate_column_labels(self):
        r=events();r=pd.concat([r,r[["player_id"]]],axis=1)
        with self.assertRaises(IdentityError):safe.recovery_counts(r)

    def test_integrated_identity_contract_is_unchanged(self):
        from tests.test_recovery import setup
        from src.recovery import integrate_recovery
        e,x,m,p=setup()
        result=integrate_recovery(e,x,m,p)
        selected=result.identity.selected_events();t,z=safe.recovery_counts(selected)
        assert_frame_equal(z,result.by_zone)
        guarded=safe.add_per90(t,m,PLAYER_KEYS)
        assert_frame_equal(guarded,result.totals.drop(columns="rate_status"))
