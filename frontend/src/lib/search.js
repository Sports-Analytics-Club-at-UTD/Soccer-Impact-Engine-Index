/* Autocomplete + "Did you mean?" — small, dependency-free, typo tolerant. */

const norm = (s) =>
  s.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "")
    .replace(/[øłđðþæœß]/g, (c) => ({ø:'o',ł:'l',đ:'d',ð:'d',þ:'th',æ:'ae',œ:'oe',ß:'ss'})[c])
    .replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, " ").trim();

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
    let score = 0;
    for (const name of [p.name, p.canonicalName, ...(p.aliases ?? [])].filter(Boolean)) {
      const full = norm(name), tokens = full.split(/[\s-]+/);
      const candidate = full === q ? 4 : full.startsWith(q) ? 3
        : tokens.some((t) => t.startsWith(q)) ? 2 : full.includes(q) ? 1 : 0;
      score = Math.max(score, candidate);
    }
    if (score) scored.push({ p, score });
  }
  scored.sort((a, b) => b.score - a.score || (b.p.ovr ?? -1) - (a.p.ovr ?? -1) || String(a.p.id).localeCompare(String(b.p.id)));
  const matches = scored.slice(0, limit).map((s) => s.p);

  let didYouMean = null;
  if (!matches.length && q.length >= 3) {
    const allowed = Math.max(2, Math.floor(q.length * 0.34));
    let best = null;
    for (const p of players) {
      const pieces = [p.name, p.canonicalName, ...(p.aliases ?? [])].filter(Boolean)
        .flatMap((name) => { const full = norm(name); return [full, ...full.split(/[\s-]+/)]; });
      const d = Math.min(...pieces.map((x) => levenshtein(q, x)));
      if (d <= allowed && (!best || d < best.d)) best = { p, d };
    }
    if (best) didYouMean = best.p;
  }
  return { matches, didYouMean };
}
