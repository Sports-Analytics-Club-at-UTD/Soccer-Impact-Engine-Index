"""V2 arithmetic, private boundary and preserved ranking contracts."""
import copy
from fractions import Fraction as F
import json
from pathlib import Path
import pytest
from src.provisional_ovr import formula_b
from src.ratings_v2 import independent_b, rank_profiles, reconstruct, VERSION


@pytest.mark.parametrize('values',[[90,80,70,60,50],[65]*5,[99,99,1,1,1],[80,80,70,70,50],[1]*5,[99]*5,[60.125,75.625,82.5,44.25,66.375]])
def test_exact_specialization_invariant(values):
    s=sorted(map(F,values),reverse=True)
    expected=sum(s)/5+(s[0]-s[4])/10+(s[1]-s[3])/20
    assert independent_b(values)==formula_b(values)==float(expected)
    assert formula_b(list(reversed(values)))==float(expected)


@pytest.mark.parametrize('values',[[None,65,65,65,65],[65]*4,[0,65,65,65,65],[100,65,65,65,65],[True,65,65,65,65]])
def test_missing_or_invalid_not_imputed(values):
    assert formula_b(values) is None and independent_b(values) is None


def test_stable_unrounded_separate_eligible_rankings():
    rows=[dict(player_id=pid,comparison_group=g,ovr=dict(value=v,eligible=e)) for pid,g,v,e in [(3,'MID',70,True),(2,'MID',70,True),(1,'CB',90,True),(4,'MID',99,False),(5,'MID',70.0000001,True),(6,'MID',None,False)]]
    assert rank_profiles(rows)=={5:1,2:2,3:3,1:1}
    assert rank_profiles(list(reversed(rows)))==rank_profiles(rows)
    assert rank_profiles(rows,eligible_only=False)[4]==1


def test_v2_version_separate():
    from scripts.reconstruct_ratings_v2 import build
    assert VERSION != 'soccer-public-ratings/v1'
    root=Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError,match='ignored audit-output'):
        build(root/'frontend/public/ratings-v2')


def test_repeat_artifact_refuses_different_evidence(tmp_path):
    from scripts.reconstruct_ratings_v2 import write_verified
    p=tmp_path/'candidate.private.json'
    write_verified(p,b'{"publication_authorized":false}')
    write_verified(p,b'{"publication_authorized":false}')
    with pytest.raises(ValueError,match='Preserve differing previous evidence'):
        write_verified(p,b'{"publication_authorized":true}')
    assert p.read_bytes()==b'{"publication_authorized":false}'


def test_real_weber_component_and_frozen_contract():
    from scripts.reconstruct_ratings_v2 import SOURCE,B3A,B3B
    import csv
    base=B3A/'audit-output/permanent-exit-support'
    facts={(f['player_id'],f['match_id']):f for f in json.loads((base/'baseline-diagnostic-facts.json').read_bytes())}
    for f in json.loads((base/'pending-corrected-facts.json').read_bytes()):facts[f['player_id'],f['match_id']]=f
    canonical=[json.loads(s) for s in (SOURCE/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl').read_text(encoding='utf8').splitlines()]
    canonical=[p for p in canonical if p['player_id']==7435]
    facts=[f for f in facts.values() if f['player_id']==7435]
    ref=json.loads((SOURCE/'data/derived/private-five-attribute-v2/frozen-reference.json').read_bytes());before=copy.deepcopy(ref)
    with (B3B/'audit-output/event-chronology/current-exception-inventory.csv').open(encoding='utf-8-sig') as f:exceptions=list(csv.DictReader(f))
    players,corrected,changed,proofs=reconstruct(canonical,facts,ref,exceptions)
    p=players[0];m=next(f for f in corrected if f['match_id']==3900512)['metrics']['press_resistance']
    assert m['supported'] is False and m['reasons']==['SOURCE_CHRONOLOGY_CONFLICT']
    assert len(changed)==4 and len(proofs['components'])==1
    assert p['attributes']['press_resistance']['numerator']==79
    assert p['attributes']['press_resistance']['attempts']==109
    assert p['ovr']['value']==69.48710292180395
    assert not p['ovr']['eligible'] and not p['publication_authorized']
    assert ref==before
    # An omitted fixture is missing evidence, never another nonappearance.
    with pytest.raises(ValueError,match='missing canonical appearance'):
        reconstruct(canonical,[f for f in facts if f['match_id']!=3900512],ref,exceptions)
