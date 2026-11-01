"""Read-only preparation of real engine inputs; never grants scoring privileges.

Receipt acceptance here means hash-pinned review metadata is internally consistent.
The caller must authenticate the reviewer/authority independently. No signature,
certification, publication permission or production engine is implemented here.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import pandas as pd

from src.real_candidate_analysis import analyze, COHORT
from src.source_reconstruction import key, exact
from src.identity import PLAYER_KEYS
from src import press_scoring as press

SOURCE_SEAL = '2376fe773b709cf620a5cbf29c9a150ad2b32acd88291ff2f696deef1f2b94de'
CHECK_SEAL = '9f697c626129ae88766721dce4fc54df62529b529e27ebb20fa7f1958c7049ff'
REQUEST_SEAL = '78fb45d0567375e07a95752d0b63642ddd14a439e3d4451c47170bb9f352514c'
DEFAULT_SOURCE = Path('data/derived/phase3-step2-source-reconstruction-2026-10-27')
DEFAULT_CHECKS = Path('data/derived/phase3-step3-independent-verified-2026-10-28')
DEFAULT_REQUEST = Path('data/derived/phase3-step3-independent-validation-2026-10-28/review-request.json')
CORE = ('tackles', 'interceptions', 'recoveries', *press.COUNT_COLS)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _artifact(root, manifest, name):
    entries = [a for a in manifest['artifacts'] if a['path'] == name]
    if len(entries) != 1:
        raise ValueError('missing/duplicate sealed artifact: ' + name)
    path = root / name
    if path.stat().st_size != entries[0]['size_bytes'] or digest(path) != entries[0]['sha256']:
        raise ValueError('sealed artifact fingerprint mismatch: ' + name)
    return path


def _rows(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _index(rows):
    result = {}
    for row in rows:
        k = key(row)
        if k in result:
            raise ValueError('duplicate player/context identity')
        result[k] = row
    return result


@dataclass
class PreparedInputs:
    population: pd.DataFrame
    measurements: pd.DataFrame
    actions: pd.DataFrame
    pool: object
    report: dict


def prepare(clubs, independent, *, provenance):
    """Reuse the existing withheld projection; retain exact rational facts.

    All contexts are mapped, including blocked rows. No technical candidate is
    nominated as a reference member. The returned evidence remains UNVERIFIED.
    """
    by_key, checks = _index(clubs), _index(independent)
    if by_key.keys() != checks.keys():
        raise ValueError('source/independent context identity mismatch')
    actor_clubs = {}
    for c in clubs:
        actor_clubs.setdefault((c['player_id'], c['season_name']), set()).add(c['team_id'])
    facts, result, population, measurements, pool = analyze(clubs, source=provenance)
    if result.players.eligible.any() or result.players.status.ne('N/A').any():
        raise ValueError('unauthorized numeric path')
    actions, contexts = [], []
    for fact in facts:
        c, verified = by_key[key(fact)], checks[key(fact)]
        if (type(c['player_id']) is not int or c['player_id'] <= 0 or
                type(c['team_id']) is not int or c['team_id'] <= 0 or
                c['team_id'] != verified['team_id']):
            raise ValueError('stable actor/team identity mismatch')
        if (exact(c['supported_minutes']) * 60 != exact(verified['independent_seconds']) or
                c['withheld_appearance_count'] != verified['unresolved_appearances'] or
                verified['actor_findings'] != 0):
            raise ValueError('independent exposure/actor mismatch')
        if any(verified[field] is not False for field in
               ('reference_member', 'fully_evidence_ready', 'production_certified', 'publication_authorized')):
            raise ValueError('unexpected evidence trust promotion')
        if verified['transfer_reference_ambiguous'] is not (len(actor_clubs[c['player_id'], c['season_name']]) > 1):
            raise ValueError('transfer identity ambiguity mismatch')
        technical = bool(verified['technical_candidate_checks_passed'] and
            fact['candidate_900_evidence_met'] and verified['source_dominant_group_agrees'] and
            verified['delivered_comparison_group'] == fact['comparison_group'] and
            not fact['unresolved_appearance_count'] and not fact['identity_reasons'] and
            all(fact['components'][n]['candidate_900_measurement_ready'] for n in CORE))
        p = population.loc[(population[PLAYER_KEYS] == pd.Series(dict(zip(PLAYER_KEYS, key(fact))))).all(axis=1)].iloc[0]
        scope = p.exposure_scope
        actions.append(dict(zip(PLAYER_KEYS, key(fact))) | {
            **{n: fact['components'][n]['delivered_scope_count'] for n in press.COUNT_COLS},
            'numerator_scope': press.PressScope(scope.competition_name, scope.season_name,
                scope.match_ids, False) if scope and all(fact['components'][n]['candidate_900_measurement_ready']
                for n in press.COUNT_COLS) else None,
            'coverage_evidence': pool.coverage_evidence})
        contexts.append(dict(player_id=c['player_id'], team_id=c['team_id'], team=c['team'],
            competition_name=c['competition_name'], season_name=c['season_name'],
            comparison_group=fact['comparison_group'], cohort_id=COHORT,
            comparison_pool_id=f'{COHORT}:{fact["comparison_group"]}' if fact['comparison_group'] else None,
            technically_mappable=technical, reference_member=False,
            exact_minutes=fact['components']['tackles']['denominator_minutes'],
            analysis_match_ids=fact['analysis_match_ids'], excluded_match_ids=fact['excluded_match_ids'],
            components={n: fact['components'][n] for n in CORE},
            transfer_reference_ambiguous=verified['transfer_reference_ambiguous'],
            blockers=verified['blockers'], provenance=provenance))
    contexts.sort(key=key)
    report = dict(schema_version='real-scoring-preflight/v1', contexts=contexts,
        mapping_sha256=canonical_hash(contexts), contexts_mapped=len(contexts),
        technical_candidates=sum(c['technically_mappable'] for c in contexts),
        technical_groups={g: sum(c['technically_mappable'] and c['comparison_group'] == g for c in contexts)
                          for g in ('MID', 'CB')}, approved_reference_members=0,
        receipt_status='ABSENT', numeric_ratings_generated=0, scoring_enabled=False,
        publication_authorized=False, line_breaking_rating=None, overall_rating=None)
    return PreparedInputs(population, measurements, pd.DataFrame(actions, columns=press.ACTION_COLUMNS, dtype=object), pool, report)


def validate_receipt(report, receipt, *, trusted_receipt_sha256):
    """Validate a future separately authenticated, exact club-unit nomination.

    This preflight does not aggregate transfers or enable any scoring function.
    Changing the selected scoring unit requires the existing aggregation checks
    and a reviewed adapter extension; it cannot be described as a club receipt.
    """
    if not trusted_receipt_sha256 or canonical_hash(receipt) != trusted_receipt_sha256:
        raise ValueError('explicit independently trusted receipt digest required')
    if receipt.get('schema_version') != 'real-scoring-review-receipt/v1':
        raise ValueError('unsigned request or unsupported approval receipt')
    if receipt.get('decision_scope') != 'evidence_and_club_membership_only':
        raise ValueError('receipt does not select supported review scope')
    for field in ('reviewer', 'authority', 'reviewed_at', 'independent_basis', 'decision_version'):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError('missing receipt attestation: ' + field)
    expected = dict(source_manifest_sha256=SOURCE_SEAL, verification_manifest_sha256=CHECK_SEAL,
                    review_request_sha256=REQUEST_SEAL, mapping_sha256=report['mapping_sha256'])
    if receipt.get('bindings') != expected:
        raise ValueError('approval/evidence identity mismatch')
    if receipt.get('fixture_policy') != 'delivered_scope_excluding_3879594':
        raise ValueError('fixture scope change requires separate integration')
    if receipt.get('source_scope') != 'four_provider_inventories_2015_16_ligue1_377':
        raise ValueError('unaccepted provider coverage limitation')
    for field in ('exposure_role_attested', 'successful_interceptions_retained', 'private_computation_approved'):
        if receipt.get(field) is not True:
            raise ValueError('required decision absent: ' + field)
    if receipt.get('publication_authorized') is not False:
        raise ValueError('preflight cannot authorize publication')
    members = receipt.get('memberships')
    if not isinstance(members, list) or not members:
        raise ValueError('explicit approved reference membership required')
    contexts = {key(c): c for c in report['contexts']}
    seen = set()
    for member in members:
        if type(member.get('player_id')) is not int or type(member.get('team_id')) is not int:
            raise ValueError('exact stable member IDs required')
        c = contexts.get(key(member))
        if c is None or not c['technically_mappable'] or c['comparison_group'] != member.get('comparison_group'):
            raise ValueError('incomplete/unapproved context or comparison group')
        actor = (c['player_id'], c['season_name'])
        if actor in seen:
            raise ValueError('duplicate player-season reference influence')
        seen.add(actor)
        if member.get('reference_unit') != 'club_context' or member.get('team_id') != c['team_id']:
            raise ValueError('unsupported reference unit/context identity')
        if c['transfer_reference_ambiguous'] and member.get('transfer_decision') != 'nominate_this_club_only':
            raise ValueError('unresolved transfer membership')
    return dict(receipt_status='STRUCTURALLY_VALID_REQUIRES_AUTHENTICATED_REVIEW',
                nominated_members=len(members), scoring_enabled=False, publication_authorized=False,
                remaining_gates=['individual_scoring_policy_approval', 'reviewed_real_engine_admission',
                                 'separate_delivery_and_publication_authorization'])


def load_preflight(source=DEFAULT_SOURCE, checks=DEFAULT_CHECKS, request=DEFAULT_REQUEST):
    source, checks, request = Path(source), Path(checks), Path(request)
    for path, expected in ((source/'run-manifest.json', SOURCE_SEAL),
                           (checks/'run-manifest.json', CHECK_SEAL), (request, REQUEST_SEAL)):
        if digest(path) != expected:
            raise ValueError('approved evidence seal mismatch: ' + str(path))
    sm, vm = _read(source/'run-manifest.json'), _read(checks/'run-manifest.json')
    if vm['inputs']['source_manifest_sha256'] != SOURCE_SEAL:
        raise ValueError('independent/source binding mismatch')
    clubs = _rows(_artifact(source, sm, 'player-club-summaries.jsonl'))
    independent = _rows(_artifact(checks, vm, 'reference-population-evidence.jsonl'))
    prepared = prepare(clubs, independent, provenance=f'sha256:{SOURCE_SEAL};independent:{CHECK_SEAL};request:{REQUEST_SEAL}')
    prepared.report['evidence_bindings'] = dict(source_manifest_sha256=SOURCE_SEAL,
        verification_manifest_sha256=CHECK_SEAL, review_request_sha256=REQUEST_SEAL)
    return prepared


def main():
    """Console-only read-only preflight; no output file or numeric scoring mode."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--trusted-receipt-sha256')
    args = parser.parse_args()
    if bool(args.receipt) != bool(args.trusted_receipt_sha256):
        parser.error('receipt and independently trusted canonical digest must be supplied together')
    prepared = load_preflight()
    report = {k:v for k,v in prepared.report.items() if k != 'contexts'}
    if args.receipt:
        report['receipt_validation'] = validate_receipt(prepared.report, _read(args.receipt),
            trusted_receipt_sha256=args.trusted_receipt_sha256)
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
