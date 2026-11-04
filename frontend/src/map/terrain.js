// Relief (H), ground colours and the terrain mesh. Heights depend only on map-data, so they are deterministic.
import * as THREE from 'three';
import { distPoly, fbm, lerp, smooth, vnoise } from './noise.js';
import { fallenWeightAt } from './zones.js';

export const S = 2;      // horizontal world scale over the base relief
export const VS = 1.25;  // vertical relief scale
export const WORLD = 300; // usable world radius in steps

/* Base relief zones (relief units) */
const ZONES = [
  { x: 0, z: 0, r: 26, h: 3.0 }, { x: 4, z: 56, r: 18, h: 1.8 }, { x: 0, z: -64, r: 10, h: 3.6 },
  { x: 24, z: -50, r: 15, h: 3.4 }, { x: -14, z: -50, r: 10, h: 3.4 }, { x: 66, z: -22, r: 22, h: 3.2 },
  { x: -76, z: 4, r: 30, h: 2.6 }, { x: 62, z: 52, r: 12, h: 2.8 },
  { x: 26, z: 26, r: 7, h: 3.0 }, { x: 4, z: 30, r: 6, h: 2.8 }, { x: 28, z: -14, r: 6, h: 3.0 },
];
const ZONES_AFTER = [
  { x: -24, z: 88, r: 7, h: 2.4 }, { x: 100, z: 25, r: 7, h: 1.1 }, { x: 0, z: -98, r: 19, h: 14 }, { x: 84, z: -9, r: 6, h: 3.2 },
];
const flat = (h, x, z, zn) => h + (zn.h - h) * smooth(zn.r, zn.r * 0.45, Math.hypot(x - zn.x, z - zn.z));
function basin(h, x, z, cx, cz, r, depth) { const t = smooth(r, r * 0.5, Math.hypot(x - cx, z - cz)); return Math.min(h, lerp(h, depth, t)); }

const C = (hex) => new THREE.Color(hex);
export const PAL = {
  deep: C('#7f7a5c'), abyss: C('#1e4556'), sand: C('#dcc794'), grassA: C('#6c9a49'), grassB: C('#8ab457'), grassC: C('#5f8d43'), forest: C('#4a7637'),
  grave: C('#6c7759'), rift: C('#5c3f7e'), riftFloor: C('#2a1b3d'), soilA: C('#7a5833'), soilB: C('#97773c'),
  stone: C('#a39a86'), road: C('#9c8158'), rock: C('#857f74'), snow: C('#eef2f6'), snowRock: C('#8d919b'),
};
const FALLEN_TINT = C('#2b1640');

/** Builds every terrain query for one map-data document. */
export function createTerrain(DATA) {
  const down = (pts) => pts.map(([x, z]) => [x / S, z / S]);
  const RAW = { river: down(DATA.river), rift: down(DATA.rift) };

  function riftRaw(x, z) {
    const p = distPoly(RAW.rift, x, z);
    const w = (1.2 + vnoise(p.s * 0.12 + 7, 3) * 1.9) * smooth(0, 9, p.s) * smooth(p.len, p.len - 6, p.s);
    return { d: p.d, w, s: p.s };
  }
  function H0(x, z) {
    const r = Math.hypot(x, z);
    const edge = 104 + (fbm(x * 0.012 + 3.1, z * 0.012 - 1.7) - 0.5) * 26;
    const plateau = 2 + fbm(x * 0.028, z * 0.028) * 3.5;
    let h = Math.min((edge - r) * 0.35, plateau);
    h += smooth(-55, -108, z) * (6 + fbm(x * 0.045 + 9, z * 0.045 + 4) * 11);
    for (const zn of ZONES) h = flat(h, x, z, zn);
    h = basin(h, x, z, 4, 98, 30, -5);
    h = basin(h, x, z, 113, 24, 13, -4);
    h = Math.min(h, lerp(h, -1.4, smooth(6, 2.4, distPoly(RAW.river, x, z).d)));
    const rf = riftRaw(x, z);
    if (rf.w > 0.05) h = lerp(h, -7, smooth(rf.w + 1.6, rf.w * 0.35, rf.d));
    for (const zn of ZONES_AFTER) h = flat(h, x, z, zn);
    return h;
  }
  /* World-coordinate queries */
  const H = (x, z) => H0(x / S, z / S) * VS;
  function riftInfo(x, z) { const r = riftRaw(x / S, z / S); return { d: r.d * S, w: r.w * S }; }
  const riverDist = (x, z) => distPoly(DATA.river, x, z).d;
  const roadDist = (x, z) => { let d = Infinity; for (const r of DATA.roads) d = Math.min(d, distPoly(r, x, z).d); return d; };
  function inField(x, z) {
    for (const f of DATA.fields) {
      const dx = x - f.c[0], dz = z - f.c[1], c = Math.cos(f.rot), s = Math.sin(f.rot);
      const lx = dx * c - dz * s, lz = dx * s + dz * c;
      if (Math.abs(lx) < f.w / 2 && Math.abs(lz) < f.d / 2) return { f, lx, lz };
    }
    return null;
  }
  const isSnow = (x, z, h) => (h > 9.5 * VS && z < -120) || h > 15 * VS;

  const _c = new THREE.Color();
  function groundColor(x, z, h, ny) {
    if (h < -1.5 && riftInfo(x, z).d < 8) return _c.copy(PAL.riftFloor);
    if (h < -0.4) return _c.copy(PAL.deep).lerp(PAL.abyss, smooth(-0.4, -4, h));
    if (h < 1.0) return _c.copy(PAL.sand);
    if (isSnow(x, z, h)) return _c.copy(ny < 0.7 ? PAL.snowRock : PAL.snow);
    if (ny < 0.78) return _c.copy(PAL.rock);
    _c.copy(PAL.grassA).lerp(PAL.grassB, fbm(x * 0.04, z * 0.04)).lerp(PAL.grassC, fbm(x * 0.15 + 5, z * 0.15) * 0.5);
    const df = Math.hypot(x - 124, z - 100); if (df < 80) _c.lerp(PAL.forest, smooth(80, 50, df));
    const dg = Math.hypot(x - 132, z + 44); if (dg < 56) _c.lerp(PAL.grave, smooth(56, 32, dg));
    const rf = riftInfo(x, z); if (rf.w > 0.1 && rf.d < 26) _c.lerp(PAL.rift, smooth(26, 4, rf.d) * 0.85);
    const fi = inField(x, z); if (fi) _c.copy(Math.abs(Math.floor(fi.lz / 1.2)) % 2 ? PAL.soilA : PAL.soilB);
    if (Math.hypot(x, z) < 17) _c.lerp(PAL.stone, 0.8);
    const rd = roadDist(x, z); if (rd < 2.4) _c.lerp(PAL.road, smooth(2.4, 1.2, rd));
    return _c;
  }

  return { H, riftInfo, riverDist, roadDist, inField, isSnow, groundColor };
}

/** Terrain mesh with vertex colours; keeps the base colours so fallen zones can be re-tinted cheaply. */
export function buildTerrain(scene, T) {
  const SIZE = 620, SEG = 420, geo = new THREE.PlaneGeometry(SIZE, SIZE, SEG, SEG).rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) pos.setY(i, T.H(pos.getX(i), pos.getZ(i)));
  geo.computeVertexNormals();
  const nrm = geo.attributes.normal, col = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const c = T.groundColor(pos.getX(i), pos.getZ(i), pos.getY(i), nrm.getY(i));
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  const base = col.slice();
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }));
  mesh.receiveShadow = true; scene.add(mesh);

  /** Darkens and tints violet every vertex inside a fallen region. */
  function tintFallen(regions, fallen) {
    const attr = geo.attributes.color;
    for (let i = 0; i < pos.count; i++) {
      const w = fallen.length ? fallenWeightAt(regions, fallen, pos.getX(i), pos.getZ(i)) * 0.72 : 0, j = i * 3;
      col[j] = lerp(base[j], FALLEN_TINT.r, w); col[j + 1] = lerp(base[j + 1], FALLEN_TINT.g, w); col[j + 2] = lerp(base[j + 2], FALLEN_TINT.b, w);
    }
    attr.needsUpdate = true;
  }
  return { mesh, tintFallen };
}
