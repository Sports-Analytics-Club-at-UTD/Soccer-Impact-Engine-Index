export const LOCAL_SECTIONS = [
  { id: 'home', label: 'Home' },
  { id: 'players', label: 'Players' },
  { id: 'leaderboards', label: 'Leaderboards' },
  { id: 'compare', label: 'Compare' },
  { id: 'teams', label: 'Teams' },
  { id: 'about', label: 'About' },
];

// Hash routes stay within the existing development entry point. Identity values
// are lookup keys only; the validated dataset remains the sole player source.
export function readLocalRoute(hash = '') {
  const [path, query = ''] = hash.replace(/^#/, '').split('?');
  const aliases = { 'experimental-discovery': 'players', 'experimental-selected-card': 'players', 'experimental-comparison': 'compare' };
  const view = aliases[path] ?? path;
  const params = new URLSearchParams(query);
  return {
    view: LOCAL_SECTIONS.some((s) => s.id === view) ? view : 'home',
    playerId: params.get('player') || null,
    firstId: params.get('first') || null,
    secondId: params.get('second') || null,
    group: params.get('group') === 'CB' ? 'CB' : 'MID',
  };
}

export function localHref(route) {
  const params = new URLSearchParams();
  for (const [key, value] of [['player', route.playerId], ['first', route.firstId], ['second', route.secondId]]) {
    if (value) params.set(key, value);
  }
  if (route.group === 'CB') params.set('group', 'CB');
  return `#${LOCAL_SECTIONS.some((s) => s.id === route.view) ? route.view : 'home'}${params.size ? `?${params}` : ''}`;
}

export function isPlainNavigation(event) {
  return !event.defaultPrevented && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}
