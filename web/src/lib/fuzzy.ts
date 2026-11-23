/** Typo-tolerant matching for short lists (the glossary): exact > prefix > whole word > substring > close spelling.
 *  "debt to equty", "rocce" and "sharp ratio" still find their entries. */

export const normalise = (s: string) => s.toLowerCase().replace(/[’']/g, '').replace(/[^a-z0-9&/+ -]+/g, ' ').replace(/\s+/g, ' ').trim()

/** Damerau-Levenshtein (optimal string alignment) distance, stopping early once it exceeds `max`. */
export function editDistance(a: string, b: string, max = 3): number {
  if (a === b) return 0
  if (Math.abs(a.length - b.length) > max) return max + 1
  const prev2 = new Array(b.length + 1).fill(0)
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j)
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]
    let rowMin = i
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1
      let v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) v = Math.min(v, prev2[j - 2] + 1)
      cur.push(v)
      rowMin = Math.min(rowMin, v)
    }
    for (let j = 0; j <= b.length; j++) prev2[j] = prev[j]
    prev = cur
    if (rowMin > max) return max + 1
  }
  return prev[b.length]
}

const allowed = (len: number) => (len <= 3 ? 0 : len <= 6 ? 1 : 2)

/** Score how well `query` matches any of `keys` (0 = no match, 100 = exact). */
export function score(query: string, keys: string[]): number {
  const q = normalise(query)
  if (!q) return 0
  let best = 0
  for (const raw of keys) {
    const k = normalise(raw)
    if (!k) continue
    if (k === q) return 100
    if (k.startsWith(q)) best = Math.max(best, 90 - Math.min(20, k.length - q.length))
    else if (` ${k} `.includes(` ${q} `)) best = Math.max(best, 75)
    else if (q.length >= 3 && k.includes(q)) best = Math.max(best, 60)
    // word-by-word spelling tolerance: every query word must be close to some word of the key
    const qw = q.split(' '), kw = k.split(' ')
    if (qw.length <= kw.length + 1) {
      let total = 0, ok = true
      for (const w of qw) {
        let d = Infinity
        for (const x of kw) {
          d = Math.min(d, x.startsWith(w) && w.length >= 3 ? 0 : editDistance(w, x, 2))
        }
        if (d > allowed(w.length)) { ok = false; break }
        total += d
      }
      if (ok) best = Math.max(best, 55 - total * 8)
    }
    // whole phrase typo ("rocce", "sharpe ratoi")
    const d = editDistance(q, k, 3)
    if (d <= allowed(q.length)) best = Math.max(best, 70 - d * 10)
  }
  return best
}

/** Items ranked by match, best first; items that do not match are dropped. */
export function fuzzyFilter<T>(items: T[], query: string, keys: (t: T) => string[], min = 30): T[] {
  if (!normalise(query)) return items
  return items.map((t) => [t, score(query, keys(t))] as const).filter(([, s]) => s >= min).sort((a, b) => b[1] - a[1]).map(([t]) => t)
}
