"""Required retained-original regressions; missing private evidence is an error."""
import csv
from dataclasses import asdict
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import unittest

from scripts import decoder_fix_independent as raw
from scripts import off_field_card_independent as independent
from scripts.source_verification_batch import payload
from src import statsbomb_participation as production
from src.source_reconstruction import appearance_rows

ROOT=Path(__file__).resolve().parents[1]
PRIOR=ROOT.parent/'Soccer-Impact-Engine-Index-participation-decoder-fix/audit-output/decoder-fix'
RECON=ROOT.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation/audit-output/source-reconciliation'
RECEIPTS={};CACHE={}
production._timestamp=lru_cache(maxsize=8192)(production._timestamp)


def bound(path,expected):
    path=Path(path);b=path.read_bytes();h=hashlib.sha256(b).hexdigest();assert h==expected,path
    RECEIPTS[str(path.resolve())]=dict(sha256=h,bytes=len(b));return b


def load(pid,mid):
    if mid not in CACHE:
        with (PRIOR/'all-appearance-comparison.csv').open(encoding='utf-8-sig') as f:a=next(a for a in csv.DictReader(f) if int(a['match_id'])==mid)
        report=json.loads(bound(a['report_path'],a['report_sha256']))
        bs=(report['fixture_document'],report['artifacts']['lineups'],report['artifacts']['events'])
        docs=[production.SourceDocument(bound(b['path'],b['sha256']),b['source_reference'],'pinned-original') for b in bs]
        fixture=next(f for f in json.loads(docs[0].raw) if f['match_id']==mid)
        ls,es=json.loads(docs[1].raw),json.loads(docs[2].raw)
        adapted=production.adapt_match(mid,*docs,clock_document_reference='Pinned exact period-local source clocks; 0/45 offsets')
        CACHE[mid]=report,fixture,ls,es,adapted
    report,fixture,ls,es,adapted=CACHE[mid]
    p=next(p for p in adapted.players if p.context.player_id==pid);v=next(v for v in adapted.validate() if v.context.player_id==pid)
    player=next(p for t in ls for p in t['lineup'] if p['player_id']==pid)
    bounds,issues,_=raw.boundaries(es,{t['team_id'] for t in ls})
    oracle=independent.reconstruct(pid,p.team_id,player,es,bounds,issues)
    return report,fixture,ls,es,adapted,p,v,oracle,bounds


class OriginalSourceRegressions(unittest.TestCase):
    def unused(self,pid,mid,uid):
        report,fixture,ls,es,a,p,v,o,bounds=load(pid,mid)
        self.assertFalse(p.observations or p.source_checks);self.assertFalse(o['active']);self.assertEqual(o['issues'],[])
        self.assertIsNone(v.elapsed_seconds);self.assertEqual([d.state for d in p.off_field_discipline],['UNUSED_ROSTER'])
        self.assertTrue(p.off_field_discipline[0].event_ref.endswith(uid));self.assertIn(uid,o['event_ids'])
        self.assertEqual(sum(e['id']==uid for e in es),1)
        serialize=lambda v:json.loads(payload(asdict(v) if hasattr(v,'__dataclass_fields__') else [asdict(x) for x in v]))
        rebuilt=dict(report);rebuilt['players']=[dict(player=serialize(p),validation=serialize(v)) for p,v in zip(a.players,a.validate())];rebuilt['boundaries']=serialize(a.boundaries)
        row=next(r for r in appearance_rows(rebuilt,fixture,ls) if r['player_id']==pid)
        self.assertFalse(row['active_appearance']);self.assertEqual(row['participation_status'],'BENCH_NO_ASSERTED_APPEARANCE');self.assertIsNone(row['supported_minutes'])
        self.assertEqual(row['match_id'],mid);self.assertEqual(len(row['off_field_discipline']),1)

    def rejected(self,pid,mid):
        _,_,_,_,_,p,v,_,_=load(pid,mid)
        self.assertFalse(p.off_field_discipline);self.assertIsNone(v.elapsed_seconds)
        self.assertNotEqual(v.status,'STRUCTURALLY_VALID')

    def test_juanfran_unused_roster(self):self.unused(26023,3825670,'e8bbbe1d-37fb-4ffb-92dd-ee93a07c6481')
    def test_supplemental_6672(self):self.unused(6672,3825869,'64a577f6-1bd2-4ca5-bc3d-f6c8c61c157b')
    def test_supplemental_10612(self):self.unused(10612,3825885,'12abeefa-7d37-4b1d-b674-1487b0eebc9b')
    def test_supplemental_40458(self):self.unused(40458,3878555,'66115c24-7ba3-4208-a1d4-a4f92e2103c3')

    def test_pallois_exact_geometry_and_post_substitution_card(self):
        _,_,_,es,_,p,v,o,bounds=load(3256,3900519)
        self.assertEqual(v.elapsed_seconds,F('1573.137'));self.assertEqual(v.elapsed_seconds/60,F('26.21895'))
        self.assertEqual(o['issues'],[]);self.assertEqual(o['seconds'],v.elapsed_seconds)
        expected=[((1,F(0)),(1,F('389.128'))),((1,F('566.133')),(1,F('1750.142')))]
        self.assertEqual(o['intervals'],expected)
        self.assertEqual(independent.union(o['lineup_intervals'],bounds),independent.union(expected,bounds))
        self.assertEqual(F('566.133')-F('389.128'),F('177.005'))
        uid='7524424d-4b7b-482d-93eb-0611dde9d8b1';sub='97e31f4a-5b3f-42d1-904c-e50b384d219d'
        eventmap={e['id']:e for e in es};self.assertGreater(eventmap[uid]['index'],eventmap[sub]['index']);self.assertGreater(raw.clock(eventmap[uid]),raw.clock(eventmap[sub]))
        self.assertEqual([d.state for d in p.off_field_discipline],['AFTER_SUBSTITUTION']);self.assertIn(uid,o['event_ids'])

    def test_ramos_267533(self):self.rejected(5201,267533)
    def test_ramos_3825879(self):self.rejected(5201,3825879)
    def test_francis_3754058(self):self.rejected(3608,3754058)
    def test_mendy_3829490(self):self.rejected(4506,3829490)
    def test_batch1_sammarco(self):self.rejected(23349,3879602)
    def test_batch1_vives(self):self.rejected(40430,3879772)
    def test_batch1_wague(self):self.rejected(3577,3879863)
    def test_batch1_saunier(self):self.rejected(13730,3901259)

    def test_all_ten_batch2b_entry_proposals_are_source_backed(self):
        with (RECON/'recoverable-appearances.csv').open(encoding='utf-8-sig') as f:rows=[r for r in csv.DictReader(f) if r['classification']=='B']
        self.assertEqual(len(rows),10)
        for a in rows:
            with self.subTest(player_id=a['player_id'],match_id=a['match_id']):
                _,_,_,es,_,p,v,o,bounds=load(int(a['player_id']),int(a['match_id']))
                self.assertEqual(o['issues'],[])
                self.assertIsNotNone(v.elapsed_seconds)
                self.assertEqual(v.elapsed_seconds,o['seconds'])
                self.assertEqual(independent.union(o['intervals'],bounds),independent.union(o['lineup_intervals'],bounds))
                self.assertEqual(len(p.reconstructed_entries),1)
                proof=p.reconstructed_entries[0];ei={e['id']:e for e in es}
                entry=ei[proof.entry_ref.rsplit('/',1)[-1]];shift=ei[proof.shift_ref.rsplit('/',1)[-1]]
                self.assertEqual(raw.clock(entry),raw.clock(shift))
                self.assertEqual(shift['type']['name'],'Tactical Shift')

    def test_pajot_snapshot_conflict(self):self.rejected(3414,3829490)

    def test_permanent_exit_support_policy_is_unchanged(self):
        with (RECON/'disputed-appearances.csv').open(encoding='utf-8-sig') as f:rows=[r for r in csv.DictReader(f) if r['classification']=='E']
        self.assertEqual(len(rows),3)
        for a in rows:
            with self.subTest(player_id=a['player_id'],match_id=a['match_id']):self.rejected(int(a['player_id']),int(a['match_id']))


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalSourceRegressions))
    output=ROOT/'audit-output/off-field-source-test-input-hashes.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(RECEIPTS,indent=2)+'\n',encoding='utf8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
