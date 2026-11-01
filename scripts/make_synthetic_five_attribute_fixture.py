"""Invented UI fixtures only; no real inputs, imports or production exporter."""
import argparse
import copy
import json
from pathlib import Path

from src.five_attribute_presentation import (ATTRIBUTES,LABELS,UNITS,SCHEMA,NOTICE,digest,validate_delivery)


def fixture():
    positions={}
    for group in ('MID','CB'):
        positions[group]={}
        for a,mean,sd in zip(ATTRIBUTES,[2,1.2,4,65,2.5] if group=='MID' else [1.5,1,3,60,2],[.5,.4,1,10,1]):
            pool=dict(population_version='synthetic:population:v1',comparison_position=group,metric_id=a,n=4,
                mean=mean,sample_sd=sd,member_ids=[f'synthetic:reference:{group}:{i}' for i in range(1,5)])
            pool['fingerprint']=digest(pool);positions[group][a]=pool
    ref=dict(version='synthetic:frozen-five:v1',synthetic=True,positions=positions);ref['fingerprint']=digest(ref)
    players=[]
    for key,group,bundes,missing in [('mid-transfer','MID',False,False),('cb','CB',False,False),
                                     ('bundesliga','CB',True,False),('missing','MID',False,True)]:
        mids=[f'synthetic:fixture:{key}:{i}' for i in range(1,11 if not bundes else 3)]
        clubs=[dict(name='SYNTHETIC North Club',competition_name='1. Bundesliga' if bundes else 'La Liga',match_ids=mids)]
        if key=='mid-transfer':
            clubs[0]['match_ids']=mids[:5]
            clubs.append(dict(name='SYNTHETIC South Club',competition_name='Ligue 1',match_ids=mids[5:]))
        p=dict(id=f'synthetic:{key}:2015/2016',player_id='synthetic:'+key,name='SYNTHETIC '+key.replace('-',' ').title(),
            season_name='2015/2016',comparison_position=group,positions=['Center Midfield','Center Defensive Midfield'] if group=='MID' else ['Center Back'],
            clubs=clubs,limited_data=bundes,partial_season=bundes,attributes={},
            provenance=[dict(id='synthetic:evidence',label='Invented test events and exposure; no real player',source='synthetic:fixture-generator',fingerprint=digest({'fixture':key}))])
        duration=180 if bundes else 900
        for a,num in zip(ATTRIBUTES,[20,10,50,30,30]):
            press=a=='press_resistance';den=12 if bundes and press else 40 if press else duration
            numerator=5 if bundes and press else num if not bundes else max(1,num//5)
            value=numerator/den*(100 if press else 90)
            pool=ref['positions'][group][a]
            rating=max(1,min(99,65+10*(value-pool['mean'])/pool['sample_sd']))
            m=dict(label=LABELS[a],measurement_kind='progressive_passing_proxy' if a=='line_breaking_passes' else 'observed_metric',
                rating=rating,percentile=75,observation=dict(value=value,unit=UNITS[a],numerator=numerator,denominator=den,
                    denominator_unit='actions' if press else 'minutes',supported_minutes=dict(numerator=duration,denominator=1),
                    action_sample_size=den if press else None,match_ids=mids),
                normalization=dict(comparison_position=group,reference_version=ref['version'],reference_fingerprint=ref['fingerprint'],pool_fingerprint=pool['fingerprint']),
                missingness=[],exclusions=[],limited_data=bundes,partial_season=bundes,provenance_ids=['synthetic:evidence'])
            if missing and a=='line_breaking_passes':
                m.update(rating=None,percentile=None,observation=None,missingness=['SYNTHETIC missing geometry example'])
                m['exclusions']=[dict(match_id=mids[0],reasons=['SYNTHETIC unsupported geometry'])]
            p['attributes'][a]=m
        players.append(p)
    return validate_delivery(dict(schema_version=SCHEMA,classification='synthetic',notice=NOTICE,
        publication_authorized=False,numeric_real_delivery_enabled=False,reference=ref,players=players))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    output=parser.parse_args().output;data=fixture();output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
