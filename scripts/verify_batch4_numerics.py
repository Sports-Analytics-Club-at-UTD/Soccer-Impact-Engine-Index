"""Reapply Batch 3B diagnostic admission and independently verify 691 profiles."""
from collections import defaultdict,Counter
from fractions import Fraction as F
from pathlib import Path
import csv,hashlib,json
from scripts.event_chronology_diagnostics import correct_diagnostic_facts
from scripts import decoder_fix_independent as raw
from src.private_five_attribute import aggregate,score_players,validate_reference
from src.private_ovr_formula_c import exclusion_reasons
from src.provisional_ovr import formula_b

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'Soccer-Impact-Engine-Index'
B3A=ROOT.parent/'Soccer-Impact-Engine-Index-permanent-exit-support/audit-output/permanent-exit-support'
B3B=ROOT.parent/'Soccer-Impact-Engine-Index-event-chronology-reconciliation/audit-output/event-chronology'

def run():
    out=ROOT/'audit-output/batch4-numerics';out.mkdir(exist_ok=False);receipts={}
    def js(p):
        b=p.read_bytes();receipts[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return json.loads(b)
    def table(p):
        b=p.read_bytes();receipts[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
        return list(csv.DictReader(b.decode('utf-8-sig').splitlines()))
    canonical=[json.loads(l) for l in (SOURCE/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl').read_text().splitlines()]
    for p in canonical:p['observed_match_ids']=[mid for mid in p['observed_match_ids'] if (p['player_id'],mid)!=(26023,3825670)]
    fs={(f['player_id'],f['match_id']):f for f in js(B3A/'baseline-diagnostic-facts.json')}
    for f in js(B3A/'pending-corrected-facts.json'):fs[f['player_id'],f['match_id']]=f
    current=table(B3B/'current-exception-inventory.csv');facts,changed,correction=correct_diagnostic_facts(list(fs.values()),current)
    assert len(changed)==4 and len(correction['components'])==1
    ref=validate_reference(js(SOURCE/'data/derived/private-five-attribute-v2/frozen-reference.json'))
    profiles={p['player_id']:p for p in score_players(aggregate(canonical,facts),ref)}
    prior={int(r['player_id']):json.loads(r['proposed_batch3b']) for r in table(B3B/'full-population-comparison.csv')}
    byid=defaultdict(list)
    for f in facts:byid[f['player_id']].append(f)
    results=[];checks=Counter()
    for pid in prior:
        p=profiles[pid]
        before=prior[pid];fs=sorted(byid[pid],key=lambda f:f['match_id']);known=sum((raw.rational(f['seconds']) for f in fs if f['seconds'] is not None),F())/60
        assert str(known)==before['exact_supported_minutes']
        assert [f['match_id'] for f in fs]==before['appearance_ids']
        ratings=[];eligible=True;positive=bool(fs) and all(f['seconds'] is not None and raw.rational(f['seconds'])>0 for f in fs)
        for attr in raw.ATTRS:
            good=[f for f in fs if f['metrics'][attr]['supported']]
            num=sum(len(f['metrics'][attr]['numerator_ids']) for f in good)
            secs=sum((raw.rational(f['metrics'][attr]['seconds']) for f in good if f['metrics'][attr]['seconds'] is not None),F())
            attempts=sum(len(f['metrics'][attr]['denominator_ids']) for f in good) if attr=='press_resistance' else None
            value=F(100*num,attempts) if attempts else F(num*5400)/secs if attr!='press_resistance' and secs else None
            pool=ref['pools'][p['comparison_group']][attr]
            rating,pct=raw.score(value,known if attr=='press_resistance' else secs/60,known,p['limited_data'],pool)
            obs=p['attributes'][attr];old=before['attributes'][attr]
            assert (raw.rational(obs['exact_value']),obs['experimental_rating'],obs['percentile'])==(value,rating,pct)
            assert (old['numerator'],old['attempts'],old['exact_value'],old['supported_seconds'],old['rating'],old['percentile'])==(num,attempts,str(value) if value is not None else None,str(secs),rating,pct)
            assert old['supported_match_ids']==[f['match_id'] for f in good]
            eligible &= bool(pid in pool['member_ids'] and rating is not None and positive and known>=900 and secs/60==known and secs>=54000 and len(good)==len(fs) and not p['limited_data'] and (attr!='press_resistance' or attempts>=40) and all(f['match_id']!=3879594 for f in fs))
            ratings.append(rating);checks['independent_attributes']+=1
        overall=raw.overall(ratings);assert overall==formula_b(ratings)==before['overall']
        reasons=exclusion_reasons(p,ref);assert eligible==(not reasons)==before['eligible'];assert reasons==before['exclusion_reasons']
        checks['independent_formula_b']+=1;checks['independent_eligibility']+=1
        results.append(dict(player_id=pid,batch3b=before,batch4=before,overall_delta=0,eligibility_changed=False))
    assert len(results)==691
    (out/'profiles.json').write_text(json.dumps(results,ensure_ascii=True)+'\n')
    (out/'summary.json').write_text(json.dumps(dict(checks=checks,players=691,changed_profiles=0,changed_eligibility=0,pressure_correction_actions=len(changed),frozen_fingerprint=ref['sha256']),indent=2)+'\n')
    (out/'input-hashes.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print(dict(checks))

if __name__=='__main__':run()
