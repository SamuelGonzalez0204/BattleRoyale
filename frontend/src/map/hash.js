// Pure helpers for deep links into the map page (mapa.html#<region-or-poi-id>). No DOM.

const ID_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const MAX_ID = 64;

/**
 * Reads a place id from a location hash. Ids are plain ASCII words joined by hyphens.
 * @param {string | undefined | null} hash  e.g. '#barco-fantasma'
 * @param {string[]} [known]  when given, only these ids are accepted
 * @returns {string | null}
 */
export function parsePlaceHash(hash, known) {
  if (typeof hash !== 'string') return null;
  let raw = hash.startsWith('#') ? hash.slice(1) : hash;
  try { raw = decodeURIComponent(raw); } catch { return null; }
  const id = raw.trim().toLowerCase();
  if (!id || id.length > MAX_ID || !ID_RE.test(id)) return null;
  if (known && !known.includes(id)) return null;
  return id;
}

/** Link to a region or POI on the full map. */
export const placeHref = (id) => `/mapa.html#${encodeURIComponent(id)}`;
