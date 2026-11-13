"""Write a review index and individual change reports for every rebuilt player."""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def run(directory):
    def read(name):return json.loads((directory/name).read_text(encoding='utf8'))
    summary=read('summary.json');verification=read('verification.json')
    players=read('players.json');changes={p['player_id']:p for p in read('changes.json')}
    appearances=defaultdict(list)
    with (directory/'source-replay.jsonl').open(encoding='utf8') as handle:
        for line in handle:
            for row in json.loads(line)['appearances']:appearances[row['player_id']].append(row)
    folder=directory/'player-reports';folder.mkdir(exist_ok=False)
    lines=['# Supported-sample reconciliation results','',
        f"All {summary['player_count']} public profiles rebuilt from {summary['fixture_count']} retained fixtures and {summary['original_events']:,} original events.",'',
        f"Ranked: {summary['old_eligible']} → {summary['eligible']}. Newly eligible: {summary['newly_eligible']}; no longer eligible: {summary['no_longer_eligible']}.",'',
        f"Verified dismissal recoveries: {summary['accepted_dismissals']}. Unresolved appearances retained as exclusions: {summary['unresolved_appearances']}.",'',
        f"Independent verification: {verification['status']} across {verification['checks']:,} checks.",'',
        'Reference cohorts were rebuilt; score changes include normalization effects. A source limitation does not mean that the player performed badly. Historical full-season coverage is not certified. No merge or deployment has been performed.','',
        '| Player | Previously ranked | Now ranked | Supported / recorded matches | Confirmed minutes | Previous → new overall |',
        '| --- | --- | --- | --- | ---: | ---: |']
    if summary.get('partial_supported_appearances'):
        lines[6:6]=[f"Additional appearance recovery: {summary['fully_recovered_appearances']} fully recovered; {summary['partial_supported_appearances']} retain verified portions only. Unknown remainders are excluded. The remaining entirely unsupported appearance is Bundesliga and was left unchanged.",'']
        lines=[line.replace('Unresolved appearances retained as exclusions:','Appearances with unresolved portions:') for line in lines]
    for p in sorted(players,key=lambda p:p['name']):
        pid=p['player_id'];change=changes[pid];rows=sorted(appearances[pid],key=lambda r:r['match_id'])
        def fmt(value):return 'N/A' if value is None else f'{value:.2f}'
        url=(folder/f'{pid}.md').resolve().as_posix()
        lines.append(f"| [{p['name']}]({url}) | {change['old_eligible']} | {p['eligible']} | {len(p['supported_match_ids'])} / {len(p['observed_match_ids'])} | {change['minutes']:.2f} | {fmt(change['old_overall'])} → {fmt(p['overall'])} |")
        detail=[f"# {p['name']}",'',f"Provider ID: {pid}; comparison position: {p['comparison_group']}",'',
            f"Ranked: {change['old_eligible']} → {p['eligible']}; overall: {fmt(change['old_overall'])} → {fmt(p['overall'])}.",'',
            f"Coverage: {change['old_matches']} → {change['matches']} recorded appearances; {change['supported_matches']} now back {change['minutes']:.6f} confirmed minutes (previously {change['old_minutes']:.6f}).",'',
            'Eligibility exclusions: '+('; '.join(p['exclusion_reasons']) or 'None; the supported sample satisfies the uniform rule.'),'',
            '| Metric | Included / excluded fixtures | Minutes | Numerator | Pressure attempts | Rating | Percentile |',
            '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
        for a,m in p['attributes'].items():
            minutes=m['supported_minutes']['numerator']/m['supported_minutes']['denominator']
            detail.append(f"| {a} | {len(m['numerator_match_ids'])} / {len(m['excluded_appearances'])} | {minutes:.6f} | {m['numerator']} | {m['attempts'] if m['attempts'] is not None else '—'} | {fmt(m['rating'])} | {fmt(m['percentile'])} |")
        detail+=['','## Source corrections and exclusions','']
        issues=0
        for r in rows:
            notes=[]
            recovery=r.get('exposure_recovery')
            if recovery and recovery['seconds'] is not None:
                minutes=recovery['seconds']['numerator']/recovery['seconds']['denominator']/60
                notes.append(('Full physical-transition recovery' if recovery['complete'] else 'Partial physical-transition recovery')+f': {minutes:.6f} verified minutes; retained source issues: '+', '.join(r['original_issues']))
                if not recovery['complete']:notes.append('Unverified remainder excluded: '+', '.join(recovery['reasons']))
            if r['dismissal'] and r['dismissal']['accepted']:notes.append('Accepted verified dismissal cutoff; original issues retained: '+', '.join(r['original_issues']))
            if r['seconds'] is None:notes.append('Elapsed minutes remain unresolved: '+', '.join(r['original_issues']))
            for a,m in r['metrics'].items():
                if not m['included']:notes.append(a+': '+', '.join(m['reasons']))
            if notes:
                issues+=1;detail.append(f"- Match {r['match_id']}: "+'; '.join(notes)+'.')
        if not issues:detail.append('No excluded observations or dismissal corrections in the retained sample.')
        detail+=['','All counts are supported available samples. Pressure uses actions, not elapsed minutes. Ratings use the rebuilt position cohort and cannot be directly compared with the previous reference version.','']
        (folder/f'{pid}.md').write_text('\n'.join(detail),encoding='utf8')
    (directory/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    recovery_rows=[r for rows in appearances.values() for r in rows if 'exposure_recovery' in r]
    if recovery_rows:
        names={p['player_id']:p['name'] for p in players}
        recovery_lines=['# Review of all 238 non-Bundesliga appearances','',
            'Full recovery establishes the whole appearance. Partial recovery establishes only the listed source-backed intervals; the remainder stays excluded.','',
            '| Player | Match | League | Outcome | Verified minutes recovered | Remaining limitation |',
            '| --- | --- | --- | --- | ---: | --- |']
        for row in sorted(recovery_rows,key=lambda r:(names[r['player_id']],r['match_id'])):
            r=row['exposure_recovery'];minutes=0 if r['seconds'] is None else r['seconds']['numerator']/r['seconds']['denominator']/60
            recovery_lines.append(f"| {names[row['player_id']]} | {row['match_id']} | {row['competition']} | {'Full' if r['complete'] else 'Partial' if r['seconds'] else 'Withheld'} | {minutes:.6f} | {', '.join(r['reasons']) or 'None for elapsed exposure; metric-specific exclusions still apply.'} |")
        (directory/'RECOVERY-238.md').write_text('\n'.join(recovery_lines)+'\n',encoding='utf8')
    print(str((directory/'REPORT.md').resolve()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    run(parser.parse_args().directory)
