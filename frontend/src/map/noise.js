// Pure helpers: deterministic RNG, value noise and 2D polyline geometry. No THREE, no DOM.

export const TAU = Math.PI * 2;

export function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export const pick = (arr, r) => arr[Math.floor(r() * arr.length)];
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export function smooth(e0, e1, x) { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); }
export function hash2(i, j) {
  let h = Math.imul(i, 374761393) + Math.imul(j, 668265263);
  h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
}
export function vnoise(x, z) {
  const i = Math.floor(x), j = Math.floor(z), fx = x - i, fz = z - j;
  const u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
  const a = hash2(i, j), b = hash2(i + 1, j), c = hash2(i, j + 1), d = hash2(i + 1, j + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
export function fbm(x, z) { let s = 0, a = 0.5, f = 1; for (let o = 0; o < 4; o++) { s += a * vnoise(x * f, z * f); f *= 2.03; a *= 0.5; } return s / 0.9375; }

/** Distance from (x, z) to a polyline; `s` is the arc length at the closest point, `len` the total length. */
export function distPoly(pts, x, z) {
  let best = Infinity, along = 0, acc = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, az] = pts[i], [bx, bz] = pts[i + 1], dx = bx - ax, dz = bz - az, L2 = dx * dx + dz * dz, L = Math.sqrt(L2);
    const t = clamp(((x - ax) * dx + (z - az) * dz) / L2, 0, 1), px = ax + dx * t, pz = az + dz * t;
    const d = Math.hypot(x - px, z - pz); if (d < best) { best = d; along = acc + t * L; } acc += L;
  }
  return { d: best, s: along, len: acc };
}
export const faceTo = (x, z, tx, tz) => Math.atan2(tx - x, tz - z);

/** Intersection point of segments ab and cd, or null. */
export function segX(a, b, c, d) {
  const r = [b[0] - a[0], b[1] - a[1]], s = [d[0] - c[0], d[1] - c[1]], den = r[0] * s[1] - r[1] * s[0];
  if (Math.abs(den) < 1e-9) return null;
  const t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den, u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1 ? [a[0] + r[0] * t, a[1] + r[1] * t] : null;
}

export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
