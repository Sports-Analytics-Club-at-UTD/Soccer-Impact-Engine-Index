/* Autocomplete + "Did you mean?" — small, dependency-free, typo tolerant. */

const norm = (s) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9\s-]/g, "").trim();

export function levenshtein(a, b) {
  if (a === b) return 0;
  const m = a.length, n = b.length;
  if (!m) return n;
  if (!n) return m;
  let prev = Array.from({ length: n + 1 }, (_, j) => j);
  for (let i = 1; i <= m; i++) {
    const cur = [i];
    for (let j = 1; j <= n; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = cur;
  }
  return prev[n];
}

export function search(query, players, limit = 6) {
  const q = norm(query);
  if (q.length < 1) return { matches: [], didYouMean: null };

  const scored = [];
  for (const p of players) {
    const full = norm(p.name);
    const tokens = full.split(/[\s-]+/);
    let score = 0;
    if (full.startsWith(q)) score = 3;
    else if (tokens.some((t) => t.startsWith(q))) score = 2;
    else if (full.includes(q)) score = 1;
    if (score) scored.push({ p, score });
  }
  scored.sort((a, b) => b.score - a.score || b.p.ovr - a.p.ovr);
  const matches = scored.slice(0, limit).map((s) => s.p);

  let didYouMean = null;
  if (!matches.length && q.length >= 3) {
    const allowed = Math.max(2, Math.floor(q.length * 0.34));
    let best = null;
    for (const p of players) {
      const full = norm(p.name);
      const pieces = [full, ...full.split(/[\s-]+/)];
      const d = Math.min(...pieces.map((x) => levenshtein(q, x)));
      if (d <= allowed && (!best || d < best.d)) best = { p, d };
    }
    if (best) didYouMean = best.p;
  }
  return { matches, didYouMean };
}
