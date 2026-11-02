"""Synthetic Batch 4 guards: explicit IDs and provenance contexts remain binding."""
import pandas as pd
import pytest
from src.identity import IdentityError, PLAYER_KEYS, resolve_events
from src.source_reconstruction import reconcile_event, flatten_events


def source(**changes):
    return dict(id='uuid',match_id=11,team_id=7,team='Club',player_id=23,
                player='Raw Name',competition_name='League',season_name='Season',type='Pass',**changes)


@pytest.mark.parametrize(('field','value','reason'),[
    ('id','different','EVENT_UUID_MISMATCH'),('match_id',12,'MATCH_ID_MISMATCH'),
    ('team_id',8,'TEAM_ID_MISMATCH'),('player_id',24,'PLAYER_ID_MISMATCH'),
    ('team','Other Club','TEAM_ASSOCIATION_MISMATCH'),
    ('competition_name','Other','COMPETITION_NAME_MISMATCH'),
    ('season_name','Other','SEASON_NAME_MISMATCH'),('type','Duel','TYPE_MISMATCH'),
    ('player','Uncorroborated Name','PLAYER_NAME_MISMATCH_OR_MISSING'),
    ('player',None,'PLAYER_NAME_MISMATCH_OR_MISSING')])
def test_exact_delivered_rejection_reason(field,value,reason):
    raw=source();delivered={**raw,field:value};r=reconcile_event(raw,delivered)
    assert r['reasons']==[reason]
    assert r['status']=='UNRESOLVED_DELIVERED_ASSOCIATION'
    assert r['reconciled_player_id'] is None
    assert r['source_player_id']==23


def lookup(name='Raw Name',pid=23,team='Club',competition='League',season='Season'):
    return dict(player_name_raw=name,player_id=pid,team=team,competition_name=competition,season_name=season)


def event(name='Raw Name',uid='e1',pid=None,team='Club',competition='League',season='Season'):
    return dict(id=uid,player=name,player_id=pid,team=team,competition_name=competition,season_name=season)


def resolve(es,ls):
    x=pd.DataFrame(ls);return resolve_events(pd.DataFrame(es),x,x[PLAYER_KEYS].drop_duplicates(),strict=False)


def test_supplied_same_id_variant_needs_no_new_name_join():
    r=resolve([event('Spelling One',pid=23),event('Spelling Two','e2',23)],[lookup('Spelling One')])
    assert r.events.player_id.tolist()==[23,23]
    assert r.events.player.tolist()==['Spelling One','Spelling Two']
    assert r.events.id.tolist()==['e1','e2']
    assert r.counts['selected']==2


@pytest.mark.parametrize(('name1','name2'),[('Jos\u00e9','Jose\u0301'),("O'Name",'O\u2019Name'),('Same Surname','Other Surname')])
def test_unverified_unicode_apostrophe_or_surname_is_unresolved(name1,name2):
    r=resolve([event(name2)],[lookup(name1)])
    assert r.events.identity_status.tolist()==['unresolved']
    assert pd.isna(r.events.player_id.iloc[0])


@pytest.mark.parametrize(('field','other'),[('team','Club B'),('competition','League B'),('season','Season B')])
def test_trusted_alias_does_not_cross_context(field,other):
    r=resolve([event('Verified Variant',**{field:other})],[lookup('Verified Variant')])
    assert r.events.identity_status.tolist()==['unresolved']


def test_conflicting_supplied_id_exact_reason():
    with pytest.raises(IdentityError,match='^events: supplied player_id conflicts with trusted crosswalk$'):
        resolve([event(pid=24)],[lookup()])


def test_homonym_same_context_exact_reason():
    with pytest.raises(IdentityError,match='^crosswalk: ambiguous name-to-ID mappings in the same context$'):
        resolve([event()],[lookup(),lookup(pid=24)])


def test_duplicate_lookup_cannot_multiply_output():
    with pytest.raises(IdentityError,match='^crosswalk: duplicate normalized name/context keys; review repeated evidence explicitly before resolution$'):
        resolve([event()],[lookup(),lookup()])


def test_duplicate_uuid_cannot_split_across_players():
    with pytest.raises(IdentityError,match='^events: duplicate event IDs; do not deduplicate events implicitly$'):
        resolve([event(pid=23),event(pid=24)],[lookup()])


def test_many_events_one_trusted_actor_preserves_order():
    es=[event(uid=f'e{i}') for i in range(20)];r=resolve(es,[lookup()])
    assert r.events.id.tolist()==[e['id'] for e in es]
    assert r.events.player_id.tolist()==[23]*20


def test_same_surname_across_clubs_stays_separate():
    r=resolve([event('Surname',team='A'),event('Surname','e2',team='B')],[lookup('Surname',23,'A'),lookup('Surname',24,'B')])
    assert r.events.player_id.tolist()==[23,24]


def test_two_clubs_one_stable_id_preserves_context_and_counts():
    r=resolve([event('Name A',team='A'),event('Name B','e2',team='B')],[lookup('Name A',23,'A'),lookup('Name B',23,'B')])
    assert r.events.player_id.tolist()==[23,23]
    assert r.events.team.tolist()==['A','B']
    assert r.events.groupby('player_id').size().to_dict()=={23:2}


def test_unique_trusted_missing_id_bridge():
    r=resolve([event('Verified Variant')],[lookup('Verified Variant')])
    assert r.events.player_id.tolist()==[23]


def test_name_match_does_not_override_actor_id_in_source():
    fixture={'match_id':11,'home_team':{'home_team_id':7,'home_team_name':'Club'},'away_team':{'away_team_id':8,'away_team_name':'Other'}}
    raw=dict(id='u',team={'id':7,'name':'Club'},player={'id':24,'name':'Raw Name'})
    with pytest.raises(ValueError,match='^event actor conflict$'):
        flatten_events([raw],fixture,[dict(team_id=7,player_id=23,player_name_raw='Raw Name')])
