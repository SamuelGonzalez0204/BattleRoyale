// Pure helpers for regions and fallen zones (La Última Luz). No THREE, no DOM.

/**
 * Region that owns a world point. Regions are circles (center + radius) that may overlap;
 * the owner is the one where the point is relatively deepest (smallest d / radius).
 * @param {{id: string, center: [number, number], radius: number}[]} regions
 * @returns {string | null}
 */
export function regionOwnerAt(regions, x, z) {
  let best = null, bestK = 1;
  for (const r of regions) {
    const k = Math.hypot(x - r.center[0], z - r.center[1]) / r.radius;
    if (k < bestK) { bestK = k; best = r.id; }
  }
  return best;
}

/**
 * Keeps only known region ids, without duplicates, preserving fall order.
 * @param {unknown} ids
 * @param {{id: string}[]} regions
 * @returns {string[]}
 */
export function normalizeFallen(ids, regions) {
  if (!Array.isArray(ids)) return [];
  const known = new Set(regions.map((r) => r.id));
  const out = [];
  for (const id of ids) if (typeof id === 'string' && known.has(id) && !out.includes(id)) out.push(id);
  return out;
}

/** True when the point belongs to a fallen region. */
export function isPointFallen(regions, fallen, x, z) {
  const owner = regionOwnerAt(regions, x, z);
  return owner !== null && fallen.includes(owner);
}

/** 0..1 strength of the fallen tint at a point (fades in over the outer 20 % of the region). */
export function fallenWeightAt(regions, fallen, x, z) {
  const owner = regionOwnerAt(regions, x, z);
  if (owner === null || !fallen.includes(owner)) return 0;
  const r = regions.find((q) => q.id === owner);
  const k = Math.hypot(x - r.center[0], z - r.center[1]) / r.radius;
  if (k <= 0.8) return 1;
  const t = Math.min(1, (1 - k) / 0.2);
  return t * t * (3 - 2 * t);
}

/** Splits regions into fallen (in fall order) and still standing ones. */
export function partitionRegions(regions, fallen) {
  return {
    fallen: fallen.map((id) => regions.find((r) => r.id === id)).filter(Boolean),
    standing: regions.filter((r) => !fallen.includes(r.id)),
  };
}

export const VIEW_MODES = ['aerial', 'walk', 'fly'];
export const PHASE_IDS = ['construccion', 'conflicto', 'convergencia', 'colapso'];
