
"""V1 press resistance: 2015/16, four complete leagues, DM+CM combined.

Run from anywhere: python src/metrics/press_resistance.py
Requires: pandas, pyarrow (or another parquet engine).
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] if Path(__file__).resolve().parent.name == 'metrics' else Path.cwd()
RAW = ROOT / 'data' / 'raw' / 'statsbomb_team_events.parquet'
MINUTES = ROOT / 'data' / 'processed' / 'player_minutes.parquet'
RECOVERY = ROOT / 'data' / 'processed' / 'recovery_per90.parquet'
OUT = ROOT / 'data' / 'processed'
SEASON = '2015/2016'
LEAGUES = {'La Liga', 'Premier League', 'Serie A', 'Ligue 1'}
KEY = ['player_id', 'team', 'competition_name', 'season_name']
MIN_MINUTES = 900
MIN_ACTIONS = 30


def require(df, cols, label):
    missing = sorted(set(cols) - set(df.columns))
    if missing:
        raise ValueError(f'{label} missing columns: {missing}. Available: {list(df.columns)}')


def main():
    for path in (RAW, MINUTES, RECOVERY):
        if not path.exists():
            raise FileNotFoundError(f'Missing {path}. Check the file location before running.')

    events = pd.read_parquet(RAW)
    minutes = pd.read_parquet(MINUTES)
    recovery = pd.read_parquet(RECOVERY)
    require(events, ['match_id', 'type', 'player', 'team', 'competition_name',
                     'season_name', 'under_pressure', 'pass_outcome', 'dribble_outcome'], 'events')
    require(minutes, KEY + ['minutes', 'position_group'], 'player_minutes')
    require(recovery, KEY + ['full_coverage'], 'recovery_per90')

    # The recovery file may have three event-type rows per player; reduce its coverage
    # information to exactly one flag per player-season key.
    recovery = recovery.loc[
        recovery['season_name'].eq(SEASON) & recovery['competition_name'].isin(LEAGUES),
        KEY + ['full_coverage']
    ].copy()
    recovery['full_coverage'] = recovery['full_coverage'].fillna(False).astype(bool)
    inconsistent = recovery.groupby(KEY, dropna=False)['full_coverage'].nunique()
    if (inconsistent > 1).any():
        raise ValueError('Conflicting full_coverage values for the same player-season.')
    coverage = recovery.drop_duplicates(KEY)

    minutes = minutes.loc[
        minutes['season_name'].eq(SEASON)
        & minutes['competition_name'].isin(LEAGUES)
        & minutes['position_group'].isin(['DM', 'CM'])
    ].copy()
    if minutes.duplicated(KEY).any():
        raise ValueError('player_minutes has duplicate player-season keys; resolve before joining.')

    # Keep only the complete-league reference population. Bundesliga is excluded.
    players = minutes.merge(coverage, on=KEY, how='left', validate='one_to_one')
    players = players.loc[players['full_coverage'].eq(True)].copy()
    if players.empty:
        raise ValueError('No full-coverage DM/CM players found. Inspect league labels and coverage flags.')

    # Resolve event names to IDs using the name column in player_minutes.
    # Name is ONLY a temporary crosswalk; final merge is strictly by KEY.
    possible_name_cols = ['player_name', 'player', 'name']
    name_col = next((c for c in possible_name_cols if c in players.columns), None)
    if name_col is None:
        raise ValueError(
            'player_minutes lacks a player-name field for mapping events to player_id. '
            'Provide a player_id column in events or a verified player-name crosswalk.'
        )
    if players[name_col].isna().any():
        raise ValueError('Missing player names in player_minutes; cannot safely map events.')

    crosswalk = players[KEY + [name_col]].rename(columns={name_col: 'player'}).copy()
    crosswalk['player'] = (
        crosswalk['player']
        .astype('string')
        .str.replace("''", "'", regex=False)
)
    name_key = ['player', 'team', 'competition_name', 'season_name']
    ambiguous = crosswalk.groupby(name_key, dropna=False)['player_id'].nunique()
    if (ambiguous > 1).any():
        raise ValueError('Ambiguous name-to-ID mappings found. Resolve them before proceeding.')
    crosswalk = crosswalk.drop_duplicates(name_key)

    events = events.loc[
        events['season_name'].eq(SEASON)
        & events['competition_name'].isin(LEAGUES)
        & events['under_pressure'].fillna(False).eq(True)
        & events['type'].isin(['Pass', 'Dribble'])
        & events['player'].notna()
    ].copy()
    events['player'] = (
        events['player']
        .astype('string')
        .str.replace("''", "'", regex=False)
)

    # This mapping is necessary because the supplied events schema has names but no IDs.
    mapped = events.merge(crosswalk, on=name_key, how='left', validate='many_to_one', indicator=True)
    unmatched = mapped['_merge'].ne('both').sum()
    print(f'Pressured pass/dribble events without an eligible DM/CM ID mapping: {unmatched:,}')
    mapped = mapped.loc[mapped['_merge'].eq('both')].copy()
    if mapped.empty:
        raise ValueError('No events mapped to eligible players; check naming and schema.')

    is_pass = mapped['type'].eq('Pass')
    mapped['successful'] = (
        (is_pass & mapped['pass_outcome'].isna())
        | (~is_pass & mapped['dribble_outcome'].eq('Complete'))
    )
    mapped['pressured_pass_attempts'] = is_pass.astype(int)
    mapped['pressured_pass_completed'] = (is_pass & mapped['successful']).astype(int)
    mapped['pressured_dribble_attempts'] = (~is_pass).astype(int)
    mapped['pressured_dribble_completed'] = (~is_pass & mapped['successful']).astype(int)

    stats = mapped.groupby(KEY, as_index=False).agg(
        pressured_pass_attempts=('pressured_pass_attempts', 'sum'),
        pressured_pass_completed=('pressured_pass_completed', 'sum'),
        pressured_dribble_attempts=('pressured_dribble_attempts', 'sum'),
        pressured_dribble_completed=('pressured_dribble_completed', 'sum'),
    )
    result = players.merge(stats, on=KEY, how='left', validate='one_to_one')
    count_cols = [
        'pressured_pass_attempts', 'pressured_pass_completed',
        'pressured_dribble_attempts', 'pressured_dribble_completed'
    ]
    result[count_cols] = result[count_cols].fillna(0).astype(int)
    result['pressured_actions'] = result['pressured_pass_attempts'] + result['pressured_dribble_attempts']
    result['successful_pressured_actions'] = (
        result['pressured_pass_completed'] + result['pressured_dribble_completed']
    )
    result['press_resistance_rate'] = (
        100 * result['successful_pressured_actions']
        / result['pressured_actions'].where(result['pressured_actions'].gt(0))
    )
    result['tier_eligible'] = (
        result['minutes'].ge(MIN_MINUTES) & result['pressured_actions'].ge(MIN_ACTIONS)
    )
    result['pooled_midfielder_percentile'] = float('nan')
    eligible = result['tier_eligible']
    result.loc[eligible, 'pooled_midfielder_percentile'] = (
        result.loc[eligible, 'press_resistance_rate'].rank(method='average', pct=True) * 100
    )
    p = result['pooled_midfielder_percentile']
    result['tier'] = 'Unranked'
    result.loc[eligible & p.ge(70), 'tier'] = 'Silver'
    result.loc[eligible & p.ge(90), 'tier'] = 'Gold'

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / 'press_resistance_v1.csv'
    parquet_path = OUT / 'press_resistance_v1.parquet'
    result.sort_values(['tier_eligible', 'pooled_midfielder_percentile'], ascending=False).to_csv(csv_path, index=False)
    result.to_parquet(parquet_path, index=False)

    print('\nLeagues:', sorted(result['competition_name'].unique().tolist()))
    print('DM/CM player-season rows:', len(result))
    print('Tier eligible:', int(eligible.sum()))
    print('Tier counts:\n' + result['tier'].value_counts().to_string())
    display = [c for c in ['player_name', 'player', 'name', 'team', 'competition_name',
                            'minutes', 'pressured_actions', 'press_resistance_rate',
                            'pooled_midfielder_percentile', 'tier'] if c in result.columns]
    print('\nTop 15 eligible players:\n' + result.loc[eligible].nlargest(
        15, 'pooled_midfielder_percentile')[display].to_string(index=False))
    print(f'\nSaved:\n{csv_path}\n{parquet_path}')


if __name__ == '__main__':
    main()
