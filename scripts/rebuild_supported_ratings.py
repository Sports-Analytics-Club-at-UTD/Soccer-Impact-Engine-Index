"""Rebuild all published identities from retained source bytes into a new snapshot.

Research evidence stays in ignored audit-output. Only the aggregate, versioned
player projection is suitable for the website. This command never deploys it.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import hashlib
import json
from pathlib import Path
import time

from src.reconciled_source import replay
from src.supported_sample_ratings import ATTRIBUTES, POLICY, VERSION, aggregate, digest, freeze_reference, score, unpack

ROOT = Path(__file__).resolve().parents[1]
OLD_SHA = '9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e'
PUBLIC_KEYS = {'progressive_passing':'line_breaking_passes'}


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def jsonl(path):
    with Path(path).open(encoding='utf8') as handle:
        for line in handle:
            if line.strip(): yield json.loads(line)


def write(path, value):
    with path.open('x', encoding='utf8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')


def project(old, players, appearances, nonappearances, reference):
    originals = {int(p['player_id']):p for p in old['players']}
    contexts = {}
    for row in appearances:
        contexts.setdefault(row['player_id'], set()).add((row['team'], row['competition']))
    rows = []
    for p in players:
        previous = originals[p['player_id']]
        coverage = dict(supported_minutes=float(unpack(p['known_supported_minutes'])),
            observed_fixtures=len(p['observed_match_ids']), supported_fixtures=len(p['supported_match_ids']),
            unresolved_fixtures=len(p['observed_match_ids'])-len(p['supported_match_ids']))
        attributes = {}
        bundes = '1. Bundesliga' in p['competitions']
        for a,m in p['attributes'].items():
            warnings = []
            if m['excluded_appearances']: warnings.append('EXCLUDED_UNSUPPORTED_OBSERVATIONS')
            if a == 'press_resistance' and m['attempts'] < 40: warnings.append('BELOW_40_PRESS_ACTIONS / LIMITED DATA')
            if bundes: warnings.extend(['LIMITED DATA','PARTIAL SEASON'])
            low = m['attempts'] < 40 if a == 'press_resistance' else unpack(m['supported_minutes']) < 900
            attributes[PUBLIC_KEYS.get(a,a)] = dict(rating=m['rating'], percentile=m['percentile'],
                limited_data=bundes or low, missingness=[] if m['rating'] is not None else [m['score_reason']], warnings=warnings,
                coverage=dict(supported_fixtures=len(m['numerator_match_ids']), excluded_fixtures=len(m['excluded_appearances']),
                    supported_minutes=float(unpack(m['supported_minutes'])), pressure_attempts=m['attempts']))
        ovr = dict(value=p['overall'], status='calculated' if p['overall'] is not None else 'unavailable',
            eligible=p['eligible'], exclusion_reasons=p['exclusion_reasons'], comparison_position=p['comparison_group'])
        rows.append({k:previous[k] for k in ('id','player_id','name','season_name','comparison_position','positions','primary_position','secondary_positions')} |
            dict(limited_data=bundes, partial_season=True,
                clubs=[dict(name=t,competition_name=c) for t,c in sorted(contexts.get(p['player_id'],set()))] or previous['clubs'],
                coverage=coverage, attributes=attributes, ovr=ovr, badge_eligible=p['eligible']))
    complete = [p for p in rows if p['ovr']['value'] is not None]
    return dict(schema_version='soccer-public-ratings/v2', release='2015-16-v2', season='2015/2016',
        formula_version=old['formula_version'], eligibility_version=VERSION, reference_version='supported-mid-cb-2015-16/v2',
        disclosures=[
            'Experimental project ratings, not official EA Sports FC/FIFA ratings or validated player quality.',
            'Available observations do not establish complete seasons. Unsupported observations are excluded, not counted as zero performances.',
            'MID and CB have separate rebuilt references using the same supported-sample eligibility rule. Ratings are not directly comparable with the earlier release.',
            'Rankings require 900 supported minutes for every per90 metric and 40 supported pressure attempts. These are retained project cutoffs, not validated certainty thresholds; Bundesliga coverage remains outside the ranking cohort.',
            'Progressive passing is a proxy and does not verify opponent defensive lines. Pressure ratios may use verified actions from fixtures without a confirmed final duration.'
        ], counts=dict(examined=len(rows), available=len(rows), complete=len(complete), partial=len(rows)-len(complete),
            bundesliga_complete=sum(p['limited_data'] for p in complete),
            bundesliga_partial=sum(p['limited_data'] and p['ovr']['value'] is None for p in rows)), players=rows)


def build(source, audit, output, workers=4):
    source, audit, output = source.resolve(), audit.resolve(), output.resolve()
    if not output.is_relative_to(ROOT/'audit-output') or output.exists():
        raise ValueError('a new directory inside this checkout audit-output is required')
    old_path = ROOT/'frontend/public/data/player-ratings-2015-16-v1.json'
    if sha(old_path) != OLD_SHA: raise ValueError('historical public release changed')
    old = json.loads(old_path.read_bytes()); identities = {int(p['player_id']):p['name'] for p in old['players']}
    summary = json.loads((audit/'summary.json').read_text())
    if not summary['complete_published_population'] or summary['player_count'] != 691 or summary['source_fixture_failures'] or summary['cross_fixture_duplicate_event_ids']:
        raise ValueError('complete original audit required')
    verified = json.loads((audit/'verification-final.json').read_text())
    if verified.get('status') != 'PASS': raise ValueError('completed independent audit verification required')
    receipt_path = audit/'input-hashes.json'; prior_receipts = json.loads(receipt_path.read_text())
    receipts = {str(old_path): OLD_SHA, str(receipt_path):sha(receipt_path)}
    bindings = {}
    for relative in ('data/derived/phase3-step2-source-reconstruction-2026-10-27/appearance-ledger.jsonl',
                     'data/derived/bundesliga-targeted-2026-10-29/appearances.jsonl'):
        ledger = source/relative
        if prior_receipts.get(str(ledger)) != sha(ledger): raise ValueError('audited source ledger changed')
        receipts[str(ledger)] = sha(ledger)
        for row in jsonl(ledger):
            binding = row.get('review_reference', row.get('report_reference'))
            if binding:
                if row['match_id'] in bindings and bindings[row['match_id']] != binding:
                    raise ValueError('conflicting fixture bindings')
                bindings[row['match_id']] = binding
    if len(bindings) != summary['source_fixture_count']: raise ValueError('incomplete fixture population')
    output.mkdir(parents=True)
    started = time.monotonic(); appearances = []; nonappearances = []; event_ids = set(); fixtures = []
    tasks = [(str(source),mid,b,identities) for mid,b in sorted(bindings.items())]
    with ProcessPoolExecutor(max_workers=workers) as executor, (output/'source-replay.jsonl').open('x',encoding='utf8') as handle:
        pending = {executor.submit(replay,task):task[1] for task in tasks}
        for index,future in enumerate(as_completed(pending),1):
            result = future.result()  # Source errors fail the entire rebuild.
            current = set(result.pop('event_ids'))
            if current & event_ids: raise ValueError('event UUID repeated across fixtures')
            event_ids.update(current); receipts.update(result.pop('receipts'))
            appearances.extend(result['appearances']); nonappearances.extend(result['nonappearances']); fixtures.append(result['match_id'])
            handle.write(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n')
            if index % 50 == 0 or index == len(tasks):
                print(f'Replayed {index}/{len(tasks)} fixtures; {len(event_ids):,} events; {time.monotonic()-started:.0f}s',flush=True)
    return finish(output, old, appearances, nonappearances, receipts, fixtures, len(event_ids))


def finish(output, old, appearances, nonappearances, receipts, fixtures, event_count):
    appearances.sort(key=lambda r:(r['player_id'],r['match_id']))
    nonappearances.sort(key=lambda r:(r['player_id'],r['match_id']))
    measured = aggregate(old['players'], appearances)
    if aggregate(list(reversed(old['players'])), list(reversed(appearances))) != measured:
        raise ValueError('nondeterministic measurement aggregation')
    bound = digest(receipts)
    reference = freeze_reference(measured,bound); players = score(measured,reference)
    if score(list(reversed(measured)), reference) != list(reversed(players)):
        raise ValueError('nondeterministic scoring')
    public = project(old,players,appearances,nonappearances,reference)
    old_players = {int(p['player_id']):p for p in old['players']}
    changes = []
    for p in players:
        previous = old_players[p['player_id']]
        changes.append(dict(player_id=p['player_id'],name=p['name'],position=p['comparison_group'],
            old_eligible=previous['ovr']['eligible'], eligible=p['eligible'],
            old_minutes=previous['coverage']['supported_minutes'], minutes=float(unpack(p['known_supported_minutes'])),
            old_matches=previous['coverage']['observed_fixtures'], matches=len(p['observed_match_ids']),
            supported_matches=len(p['supported_match_ids']), old_overall=previous['ovr']['value'], overall=p['overall'],
            exclusion_reasons=p['exclusion_reasons']))
    result = dict(player_count=len(players), fixture_count=len(fixtures), original_events=event_count,
        old_eligible=sum(p['ovr']['eligible'] for p in old['players']), eligible=sum(p['eligible'] for p in players),
        newly_eligible=sum(not p['old_eligible'] and p['eligible'] for p in changes),
        no_longer_eligible=sum(p['old_eligible'] and not p['eligible'] for p in changes),
        accepted_dismissals=sum(bool(r['dismissal'] and r['dismissal']['accepted']) for r in appearances),
        unresolved_appearances=sum(r['seconds'] is None for r in appearances),
        excluded_metric_appearances={a:sum(not r['metrics'][a]['included'] for r in appearances) for a in ATTRIBUTES},
        identity_conflicts=sum(bool(r['identity_reasons']) for r in appearances),
        reference_sha256=reference['sha256'], policy=POLICY,
        ranked_by_position={g:sum(p['eligible'] and p['comparison_group']==g for p in players) for g in ('MID','CB')},
        exclusion_counts=dict(Counter(reason for p in players for reason in p['exclusion_reasons'])))
    for name,value in [('measurements.json',measured),('players.json',players),('frozen-reference.json',reference),
                       ('input-hashes.json',receipts),('changes.json',changes),('summary.json',result),
                       ('nonappearances.json',nonappearances),('public-ratings.json',public)]:
        write(output/name,value)
    with (output/'changes.csv').open('x',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(changes[0])); writer.writeheader(); writer.writerows(changes)
    implementation = {str(path.relative_to(ROOT)):sha(path) for path in [ROOT/'src/supported_sample_ratings.py',ROOT/'src/reconciled_source.py',ROOT/'src/dismissal_reconciliation.py',Path(__file__)]}
    write(output/'manifest.json',dict(version=VERSION,input_binding=bound,implementation=implementation,
        artifacts={p.name:sha(p) for p in output.iterdir() if p.is_file()}, policy=POLICY))
    print(json.dumps(result,indent=2),flush=True)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    args=parser.parse_args();build(args.source_root,args.audit,args.output,args.workers)
