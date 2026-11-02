"""Exact boundary contracts and hash-bound original recovery controls."""
import copy
from fractions import Fraction as F
import json
from pathlib import Path
import pytest
from src.source_reconstruction import event_within_exposure, flatten_events, measurements
from src.statsbomb_participation import SourceSchemaError
from test_source_reconstruction import data, review, project
from test_statsbomb_participation import run, transition
from test_off_field_cards import complete
from test_source_backed_entry import substitute
from test_permanent_exits import terminal


def appearance():
    return dict(participation_status='STRUCTURALLY_VALID',period_boundaries=[dict(period=1,start_seconds='0',end_seconds='2850.500'),dict(period=2,start_seconds='0',end_seconds='2850.500')],playing_intervals=[dict(start=dict(period=1,seconds='10.125'),end=dict(period=2,seconds='2800.125'))])


@pytest.mark.parametrize('period,stamp,expected',[(1,'00:00:10.125',True),(1,'00:00:10.124',False),(2,'00:46:40.125',True),(2,'00:46:40.126',False),(1,'00:47:30.500',True),(1,'00:47:30.501',False),(1,'00:47:30.499',True),(1,'00:48:00.000',False),(2,'00:00:00.000',True),(2,'01:30:00.000',False),(1,'00:46:00.000',True),(3,'00:00:00.000',False)])
def test_exact_boundaries(period,stamp,expected):
    a=appearance();before=copy.deepcopy(a)
    assert event_within_exposure(dict(period=period,timestamp=stamp),a)==expected
    assert a==before


@pytest.mark.parametrize('exit_kind',['substitution','terminal_exit','dismissal','temporary_exit'])
def test_after_explicit_exit_and_during_absence(exit_kind):
    a=appearance();a['playing_intervals']=[dict(start=dict(period=1,seconds='0'),end=dict(period=2,seconds='100.125'),exit_kind=exit_kind)]
    assert event_within_exposure(dict(period=2,timestamp='00:01:40.125'),a)
    assert not event_within_exposure(dict(period=2,timestamp='00:01:40.126'),a)
    if exit_kind=='temporary_exit':
        a['playing_intervals'].append(dict(start=dict(period=2,seconds='120.125'),end=dict(period=2,seconds='200')))
        assert not event_within_exposure(dict(period=2,timestamp='00:01:50.000'),a)
        assert event_within_exposure(dict(period=2,timestamp='00:02:00.125'),a)


@pytest.mark.parametrize('status',['CONFLICTING_EVIDENCE','INCOMPLETE_EVIDENCE','BENCH_NO_ASSERTED_APPEARANCE'])
def test_unresolved_never_admitted(status):
    a=appearance();a['participation_status']=status
    assert not event_within_exposure(dict(period=1,timestamp='00:01:00.000'),a)


def test_successful_unsuccessful_and_administrative():
    _,_,ms,_=project();m=next(r for r in ms if r['player_id']==101)
    assert m['components']['recoveries']['event_ids']==['recover']
    assert m['components']['pressured_pass_attempts']['count']==1
    assert m['components']['pressured_pass_completed']['count']==1
    assert all(not any('Half' in uid or 'xi-' in uid for uid in c['event_ids']) for c in m['components'].values())


@pytest.mark.parametrize('typ',['Pressure','Ball Receipt*','Tactical Shift'])
def test_nonmeasurement_rows(typ):
    d=data();e=copy.deepcopy(next(e for e in d[2] if e['id']=='recover'))
    e.update(id='nonmeasurement',type=dict(name=typ),under_pressure=True);d[2].append(e)
    _,_,ms,_=project(d)
    assert all('nonmeasurement' not in c['event_ids'] for m in ms for c in m['components'].values())


def test_missing_progressive_geometry():
    d=data();next(e for e in d[2] if e['id']=='pass')['pass'].pop('end_location')
    _,_,ms,_=project(d);m=next(r for r in ms if r['player_id']==101)
    assert 'MISSING_SOURCE_GEOMETRY' in m['components']['progressive_passes']['reasons']
    assert m['components']['progressive_passes']['per90'] is None


@pytest.mark.parametrize('conflict',['duplicate_uuid','stable_id'])
def test_invalid_reference_rejected(conflict):
    d=data()
    if conflict=='duplicate_uuid':d[2].append(copy.deepcopy(next(e for e in d[2] if e['id']=='recover')))
    else:next(e for e in d[2] if e['id']=='recover')['player']['id']=999
    with pytest.raises((ValueError,SourceSchemaError)):project(d)


def test_conflicting_lineup_withheld():
    d=data();d[1][0]['lineup'][0]['positions'].append(copy.deepcopy(d[1][0]['lineup'][0]['positions'][0]))
    a,_,ms,_=project(d)
    assert next(r for r in a if r['player_id']==101)['validated_elapsed_seconds'] is None
    assert all(c['per90'] is None for c in next(m for m in ms if m['player_id']==101)['components'].values())


def test_supported_measurements_preserved():
    _,_,ms,_=project();m=next(r for r in ms if r['player_id']==101)
    for name in ('tackles','interceptions','recoveries','progressive_passes'):
        assert m['components'][name]['count']==1
        assert m['components'][name]['per90']==float(F(5400,5701))


@pytest.mark.parametrize('fixture,delta',[(3754048,'0.034'),(3900579,'0.126'),(3825780,'0.073'),(3829454,'0.171')])
def test_original_recoveries_remain_withheld(fixture,delta):
    root=Path(__file__).resolve().parents[1]
    evidence=json.loads((root/'audit-output/chronology-priority/priority-evidence.json').read_text(encoding='utf8'))
    r=next(r for r in evidence if r['match_id']==fixture)
    import hashlib
    docs=[]
    for b in r['source_documents']:
        raw=Path(b['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==b['sha256'];docs.append(json.loads(raw))
    e=next(e for e in docs[2] if e['id']==r['event_id'])
    assert e['timestamp']==r['timestamp'] and e['index']==r['event_index']
    assert F(r['seconds_after_half_end'])==F(delta)
    assert r['outside_period'] and r['source_index_after_half_end']
    assert r['existing_decision']==r['proposed_decision']=='WITHHELD'
    assert r['production_metric_relevance']['recoveries']['reasons']==['NUMERATOR_DENOMINATOR_MISMATCH']
    oracle=r['independent_event_and_lineup_reconstruction']
    assert not oracle['issues'] and oracle['seconds']==oracle['lineup_seconds']


def pressure_fixture():
    import csv
    root=Path(__file__).resolve().parents[1]
    base=root.parent/'Soccer-Impact-Engine-Index-permanent-exit-support/audit-output/permanent-exit-support'
    f=next(f for f in json.loads((base/'baseline-diagnostic-facts.json').read_bytes()) if (f['player_id'],f['match_id'])==(7435,3900512))
    with (root/'audit-output/event-chronology/current-exception-inventory.csv').open(encoding='utf-8-sig') as stream:
        rows=[r for r in csv.DictReader(stream) if (r['player_id'],r['match_id'])==('7435','3900512')]
    return f,rows


def test_pressure_chronology_correction_keeps_raw_ratio_evidence():
    from scripts.event_chronology_diagnostics import correct_diagnostic_facts
    f,rows=pressure_fixture();before=copy.deepcopy(f)
    corrected,changed,proof=correct_diagnostic_facts([f],rows)
    m=corrected[0]['metrics']['press_resistance']
    assert f==before and f['metrics']['press_resistance']['supported']
    assert not m['supported'] and m['reasons']==['SOURCE_CHRONOLOGY_CONFLICT']
    assert len(changed)==4 and sum(r['trigger_conflict'] for r in changed)==3
    assert all(r['in_numerator'] and r['in_denominator'] and r['raw_uuid_retained'] for r in changed)
    assert m['counts']==before['metrics']['press_resistance']['counts']
    assert m['numerator_ids']==before['metrics']['press_resistance']['numerator_ids']
    assert m['denominator_ids']==before['metrics']['press_resistance']['denominator_ids']
    assert len(proof['source_proofs'])==3
    assert all('ENTRY_AFTER_PERMANENT_EXIT' in p['independent']['issues'] for p in proof['source_proofs'])
    assert all(p['separate_lineup'] is not None for p in proof['source_proofs'])
    assert corrected[0]['seconds']==f['seconds'] is None
    for attr in f['metrics']:
        if attr!='press_resistance':assert corrected[0]['metrics'][attr]==f['metrics'][attr]


def test_unknown_duration_alone_does_not_withhold_ratio():
    from scripts.event_chronology_diagnostics import correct_diagnostic_facts
    f,_=pressure_fixture();corrected,changed,proof=correct_diagnostic_facts([f],[])
    assert corrected==[f] and corrected[0]['metrics']['press_resistance']['supported']
    assert not changed and not proof['components']


@pytest.mark.parametrize('tamper',['timestamp','index','team','hash'])
def test_pressure_correction_rejects_unbound_evidence(tamper):
    from scripts.event_chronology_diagnostics import correct_diagnostic_facts
    f,rows=pressure_fixture();r=copy.deepcopy(next(r for r in rows if 'press_attempts' in json.loads(r['selected_metrics'])))
    if tamper=='timestamp':r['timestamp']='00:00:00.000'
    elif tamper=='index':r['event_index']='999999'
    elif tamper=='team':r['team_id']='999999'
    else:
        docs=json.loads(r['source_documents']);docs[2]['sha256']='0'*64;r['source_documents']=json.dumps(docs)
    before=copy.deepcopy(f)
    with pytest.raises((ValueError,KeyError)):correct_diagnostic_facts([f],[r])
    assert f==before


def test_supported_pre_exit_pressure_action_cannot_trigger_withholding():
    from scripts.event_chronology_diagnostics import correct_diagnostic_facts
    f,rows=pressure_fixture();r=copy.deepcopy(next(r for r in rows if 'press_attempts' in json.loads(r['selected_metrics'])))
    disputed={x['event_id'] for x in rows}
    uid=next(uid for uid in f['metrics']['press_resistance']['denominator_ids'] if uid not in disputed)
    events=json.loads(Path(json.loads(r['source_documents'])[2]['path']).read_bytes());e=next(e for e in events if e['id']==uid)
    r.update(event_id=uid,period=e['period'],timestamp=e['timestamp'],event_index=e['index'])
    with pytest.raises(ValueError,match='no independently established chronology conflict'):correct_diagnostic_facts([f],[r])


def test_already_withheld_component_is_not_changed_again():
    from scripts.event_chronology_diagnostics import correct_diagnostic_facts
    f,rows=pressure_fixture();f['metrics']['press_resistance'].update(supported=False,reasons=['SOURCE_CHRONOLOGY_CONFLICT'])
    corrected,changed,_=correct_diagnostic_facts([f],rows)
    assert corrected==[f] and not changed
