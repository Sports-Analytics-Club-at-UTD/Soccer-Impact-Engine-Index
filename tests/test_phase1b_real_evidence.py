"""Read-only REAL retained pilot regression; no synthetic record is called real.

These checks skip when the deliberately untracked evidence has not been supplied.
Synthetic schema/failure checks remain in the other test modules.
"""
from collections import Counter
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.source_verification_batch import bound_document,load_json,manifest_from_phase1
from src.statsbomb_participation import adapt_match

ROOT=Path(__file__).resolve().parents[1]
PILOT=ROOT/'data/source-evidence/phase1-2026-10-27'
ARPIT=ROOT/'data/source-evidence/arpit-fixtures-2026-10-27/statsbomb_fixtures_2015_16.parquet'


@unittest.skipUnless((PILOT/'artifact-inventory.json').is_file(),'Retained real source pilot not supplied')
class RetainedRealEvidenceTests(unittest.TestCase):
    def test_original_nine_preserved_and_additional_five_detected(self):
        manifest=manifest_from_phase1(PILOT);counts=Counter();conflicts=set()
        with patch('scripts.source_verification_batch.public_transport',side_effect=AssertionError('offline only')):
            for row in manifest['matches']:
                if not row['artifacts']:continue
                docs=[bound_document(b) for b in (manifest['fixture_documents'][row['fixture_document']],row['artifacts']['lineups'],row['artifacts']['events'])]
                a=adapt_match(row['match_id'],*docs,clock_document_reference='retained provider clock documentation and checked zero-origin boundaries')
                for player,r in zip(a.players,a.validate()):
                    if not player.observations:continue
                    counts[r.status]+=1
                    self.assertFalse(r.source_independently_verified);self.assertFalse(r.publication_authorized)
                    if r.status=='CONFLICTING_EVIDENCE':
                        conflicts.add((row['match_id'],r.context.player_id));self.assertIsNone(r.elapsed_seconds);self.assertIsNone(r.position_allocation)
        original={(3754217,p) for p in [3437,3496,3517,6746]}|{(3829416,p) for p in [3230,16462]}|{(3879549,p) for p in [6636,7026,7147]}
        additional={(3829416,p) for p in [3210,4443,7323,401474]}|{(3879549,7458)}
        self.assertEqual(conflicts,original|additional)
        self.assertEqual(dict(counts),{'STRUCTURALLY_VALID':210,'CONFLICTING_EVIDENCE':14})

    @unittest.skipUnless(ARPIT.is_file(),'Arpit real snapshot not supplied')
    def test_arpit_actual_snapshot_agrees_with_retained_provider_list(self):
        import pyarrow.parquet as pq
        rows=pq.read_table(ARPIT,columns=['match_id','competition_name','season_name','home_team','away_team']).to_pylist()
        old=load_json(PILOT/'fixtures-normalized.json')
        self.assertEqual(len(rows),1517);self.assertEqual(len({r['match_id'] for r in rows}),1517)
        self.assertEqual(sorted(rows,key=lambda r:r['match_id']),sorted(old,key=lambda r:r['match_id']))
        self.assertEqual(Counter(r['competition_name'] for r in rows),{'La Liga':380,'Premier League':380,'Serie A':380,'Ligue 1':377})
        self.assertEqual(next(r for r in rows if r['match_id']==3879594)['home_team'],'AC Milan')


if __name__=='__main__':unittest.main()
