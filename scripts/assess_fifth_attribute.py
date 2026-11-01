"""Read-only assessment of the private integration; exclusive diagnostic output."""
import argparse
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path

import pandas as pd

from scripts.prepare_fifth_attribute import records, sha
from src.fifth_attribute import combine_observations
from src.source_reconstruction import exact


def assess(root):
    root=Path(root)
    manifest=json.loads((root/'manifest.json').read_text())
    for name,expected in manifest['artifacts'].items():
        if sha(root/name)!=expected:raise ValueError('private artifact changed')
    players=list(records(root/'player-measurements.jsonl'))
    by_player=defaultdict(list)
    observations=list(records(root/'match-observations.jsonl'))
    bundesliga=combine_observations([r for r in observations if r['competition_name']=='1. Bundesliga'])
    four_league=combine_observations([r for r in observations if r['competition_name']!='1. Bundesliga'])
    for r in observations:
        if not r['reasons']:by_player[r['player_id']].append(r)
    refs=[p for p in players if p['experimental_reference_candidate']]
    splits=[]
    for p in refs:
        matches=sorted(by_player[p['player_id']],key=lambda r:r['match_id'])
        halves=[]
        for rows in (matches[::2],matches[1::2]):
            seconds=sum((exact(r['seconds']) for r in rows),Fraction(0))
            halves.append(dict(minutes=float(seconds/60),prog_passes_p90=sum(r['prog_passes'] for r in rows)*5400/float(seconds) if seconds else None,
                pass_value_p90=sum(r['value_sum'] for r in rows)*5400/float(seconds) if seconds and all(r['value_sum'] is not None for r in rows) else None))
        splits.append(dict(player_id=p['player_id'],group=p['comparison_group'],halves=halves))
    groups={}
    for group in ('MID','CB'):
        members=[p for p in refs if p['comparison_group']==group]
        frame=pd.DataFrame(members)
        paired=[r for r in splits if r['group']==group and all(h['minutes']>=450 for h in r['halves'])]
        def correlation(metric):
            df=pd.DataFrame([{str(i):r['halves'][i][metric] for i in (0,1)} for r in paired])
            value=df.rank(method='average').corr().iloc[0,1] if len(df)>1 else float('nan')
            return None if pd.isna(value) else float(value)
        def summary(rows):
            return dict(n=len(rows),mean_prog_passes_p90=sum(p['prog_passes_p90'] for p in rows)/len(rows) if rows else None,
                mean_pass_value_p90=sum(p['pass_value_p90'] for p in rows)/len(rows) if rows and all(p['pass_value_p90'] is not None for p in rows) else None)
        rho=frame[['prog_passes_p90','pass_value_p90']].rank(method='average').corr().iloc[0,1] if len(frame)>1 else None
        groups[group]=dict(reference_n=len(members),headline_vs_value_spearman=None if pd.isna(rho) else float(rho),
            alternating_fixture_split_players=len(paired),split_half_spearman={m:correlation(m) for m in ('prog_passes_p90','pass_value_p90')},
            exposure_sensitivity={'at_least_900':summary(members),'at_least_1800':summary([p for p in members if p['minutes']>=1800])},
            leagues={league:summary([p for p in members if p['competitions']==[league]]) for league in ('Premier League','La Liga','Serie A','Ligue 1')})
    def coverage(rows):
        return dict(observed=len(rows),supported=sum(p['prog_passes_p90'] is not None for p in rows),
            groups={g:dict(observed=sum(p['comparison_group']==g for p in rows),
                supported=sum(p['comparison_group']==g and p['prog_passes_p90'] is not None for p in rows)) for g in ('MID','CB')})
    result=dict(notice='PRIVATE / EXPERIMENTAL / DESCRIPTIVE ASSESSMENT',groups=groups,
        coverage=dict(four_league_scope_only=coverage(four_league),bundesliga_scope_only=coverage(bundesliga),
            note='Scope-specific diagnostic projections only. Transfers can occur in both scope summaries; the delivered measurement candidate remains one combined player-season.'),
        split_policy='Alternating sorted fixture IDs within player; both halves >=450 supported minutes. Descriptive, not chronological out-of-sample validation.',
        limitations=['Same-provider observations only; no possession or team-style adjustment.',
            'League summaries exclude cross-league transfers to avoid double counting.',
            '900 vs 1800 minutes changes the population and is a sensitivity description, not a coverage-bias correction.',
            'Statistical approval of pool composition, positional fairness, and cross-league comparability remains pending.'],
        input_manifest_sha256=sha(root/'manifest.json'),implementation_sha256=sha(__file__))
    path=root/'descriptive-assessment.json'
    with path.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    assess(parser.parse_args().input)
