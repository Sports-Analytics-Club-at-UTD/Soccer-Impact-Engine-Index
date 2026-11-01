"""Invented observation contract fixture; no private inputs or scoring outputs."""
from src.provisional_delivery import ATTRIBUTES, DEFINITIONS, SCHEMA


def synthetic():
    """A supported 10-minute sample plus one explicitly excluded appearance."""
    attr={n:dict(rating=None,percentile=None,observation=None,reason='Unsupported') for n in ATTRIBUTES}
    for n in ATTRIBUTES[:3]:attr[n]['observation']=dict(value=0,unit='per90',count=0,minutes=dict(numerator=10,denominator=1),match_ids=['11'])
    attr['press_resistance']['observation']=dict(value=50,unit='percent',attempts=2,successes=1,pass_attempts=2,pass_successes=1,
        dribble_attempts=0,dribble_successes=0,match_ids=['11','12'],at_least_40=False)
    p=dict(id='101:2015/2016',player_id='101',name='Invented Player',season_name='2015/2016',
        contexts=[dict(team='Invented Club',competition_name='1. Bundesliga',match_ids=['11','12'])],
        comparison_group='CB',position_minutes={'CB':dict(numerator=10,denominator=1)},observed_positions=['Center Back'],
        bundesliga_candidate=True,observed_exposure_complete=False,supported_minutes=dict(numerator=10,denominator=1),
        excluded_match_ids=['12'],reference_member=False,limited_data=True,partial_season=True,provenance_ids=['synthetic'],attributes=attr,
        bundesliga_sample=dict(comparison_group='CB',position_minutes={'CB':dict(numerator=10,denominator=1)},supported_minutes=dict(numerator=10,denominator=1),match_ids=['11','12'],excluded_match_ids=['12'],press_attempts=2,press_successes=1))
    return dict(schema_version=SCHEMA,definitions_id=DEFINITIONS,numeric_ratings_enabled=False,publication_authorized=False,baseline=None,
        sources=[dict(id='synthetic',path='tests/invented.json',sha256='a'*64,label='Invented synthetic evidence')],players=[p])
