// Pure mapping from world stats (0..100) to what is built in the valley. No THREE, no DOM.
//
// Design: at layout time every stat-driven piece gets a threshold t in 0..100 (deterministic,
// hashed from its position so growth is spread across the valley instead of region by region).
// A piece is built when stat >= t. Each InstancedMesh batch holds pieces of ONE stat, sorted by
// t ascending, so applying a stat is a binary search + `InstancedMesh.count = n` (no matrix rewrites).
import { clamp, hash2 } from './noise.js';

export const STAT_KEYS = ['poblacion', 'comida', 'moral', 'defensa', 'oro'];

/** Share of each stat's pieces that is always built (threshold 0), so a low stat never empties the valley. */
export const GROWTH_BASE = { poblacion: 0.2, comida: 0.1, moral: 0.1, defensa: 0.15, oro: 0.1 };

const SALT = { poblacion: 11, comida: 23, moral: 37, defensa: 41, oro: 53 };
const FULL = 100;

/**
 * Stats to a complete 0..100 object. Missing/invalid stats count as 100 (full world).
 * @param {Partial<Record<string, unknown>> | null | undefined} stats
 * @returns {Record<'poblacion'|'comida'|'moral'|'defensa'|'oro', number>}
 */
export function normalizeStats(stats) {
  const out = {};
  for (const k of STAT_KEYS) {
    const v = stats ? Number(stats[k]) : FULL;
    out[k] = stats && stats[k] !== null && stats[k] !== undefined && Number.isFinite(v) ? clamp(v, 0, FULL) : FULL;
  }
  return out;
}

/**
 * Uniform draw u in [0,1) to a threshold: below `base` it is always built (0), the rest spreads over 0..100.
 * @param {number} u @param {number} base
 */
export function growthThreshold(u, base) {
  if (u <= base) return 0;
  return clamp(((u - base) / (1 - base)) * FULL, 0, FULL);
}

/** Deterministic threshold for a piece of `stat` placed at (x, z). */
export function placeThreshold(stat, x, z) {
  const u = hash2(Math.round(x * 10) + (SALT[stat] ?? 0) * 7919, Math.round(z * 10) - (SALT[stat] ?? 0) * 104729);
  return growthThreshold(Math.min(u, 0.999999), GROWTH_BASE[stat] ?? 0);
}

/** Indices of `thresholds` in ascending order (stable). */
export function sortByThreshold(thresholds) {
  return thresholds.map((t, i) => i).sort((a, b) => thresholds[a] - thresholds[b] || a - b);
}

/**
 * How many pieces are built at `value`, given ascending thresholds (count of t <= value).
 * @param {ArrayLike<number>} sorted @param {number} value
 */
export function visibleCount(sorted, value) {
  let lo = 0, hi = sorted.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (sorted[mid] <= value) lo = mid + 1; else hi = mid; }
  return lo;
}

/** Moral to lantern glow (emissive intensity) and the warm fill light (hemisphere intensity). */
export function moralLight(moral) {
  const k = clamp(Number(moral) || 0, 0, FULL) / FULL;
  return { lantern: 0.02 + k * 0.6, warmth: k * 0.25 };
}
