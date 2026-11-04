// Placement primitives: matrices per model key (later instanced), occupancy grid, houses, towers, bridges and roads.
import * as THREE from 'three';
import { TAU, distPoly, pick, segX } from './noise.js';
import { KIT, kitScale } from './kits.js';
import { buildPlaza, buildBahia, buildMuralla } from './regions/centro.js';
import { buildCementerio, buildBosque } from './regions/este.js';
import { buildCampos, buildCumbres } from './regions/oeste.js';
import { buildCountry, buildGrass } from './regions/campo.js';

const UP = new THREE.Vector3(0, 1, 0);
const GRID = 10;
const WALLS = {
  wood: { plain: 'town/wall-wood', door: 'town/wall-wood-door', win: ['town/wall-wood-window-shutters', 'town/wall-wood-window-small'] },
  stone: { plain: 'town/wall', door: 'town/wall-door', win: ['town/wall-window-shutters', 'town/wall-window-small'] },
};

export function mat4(x, y, z, rot, s, sy = 1) {
  return new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromAxisAngle(UP, rot), new THREE.Vector3(s, s * sy, s));
}

/** Placement context bound to one terrain. Everything a region builder needs lives on the returned object. */
export function createPlacement(T, DATA) {
  const { H } = T;
  const batches = new Map(), spawns = [], banners = [], extras = [], bridges = [], occ = new Map();
  const addM = (key, m) => { if (!batches.has(key)) batches.set(key, []); batches.get(key).push(m); };
  const put = (key, x, z, o = {}) => {
    const y = (o.y ?? H(x, z)) + (o.dy ?? 0);
    addM(key, mat4(x, y, z, o.rot ?? 0, (o.s ?? 1) * kitScale(key), o.sy ?? 1));
  };
  const putLocal = (parent, key, lx, ly, lz, lrot = 0) => addM(key, parent.clone().multiply(mat4(lx, ly, lz, lrot, 1)));
  const _n = new THREE.Vector3(), _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion();
  const groundNormal = (x, z) => { const e = 0.6; return _n.set(-(H(x + e, z) - H(x - e, z)) / (2 * e), 1, -(H(x, z + e) - H(x, z - e)) / (2 * e)).normalize(); };
  function putTilt(key, x, z, rot, o = {}) { // flat piece resting on the slope
    _q1.setFromUnitVectors(UP, groundNormal(x, z)); _q2.setFromAxisAngle(UP, rot);
    const s = (o.s ?? 1) * kitScale(key);
    addM(key, new THREE.Matrix4().compose(new THREE.Vector3(x, H(x, z) + (o.dy ?? 0.05), z), _q1.clone().multiply(_q2), new THREE.Vector3(s, s, s)));
  }
  const spawn = (key, x, z, o = {}) => spawns.push({ key, x, z, o });

  const cellKey = (i, j) => i * 10007 + j;
  function reserve(x, z, r) {
    for (let i = Math.floor((x - r) / GRID); i <= Math.floor((x + r) / GRID); i++)
      for (let j = Math.floor((z - r) / GRID); j <= Math.floor((z + r) / GRID); j++) {
        const k = cellKey(i, j); if (!occ.has(k)) occ.set(k, []); occ.get(k).push({ x, z, r });
      }
  }
  function isFree(x, z, r) {
    const i = Math.floor(x / GRID), j = Math.floor(z / GRID);
    for (let a = i - 1; a <= i + 1; a++) for (let b = j - 1; b <= j + 1; b++)
      for (const o of occ.get(cellKey(a, b)) ?? []) if (Math.hypot(o.x - x, o.z - z) < o.r + r) return false;
    return true;
  }
  function valid(x, z, o = {}) {
    const h = H(x, z);
    if (h < (o.minH ?? 1.0) || h > (o.maxH ?? 99)) return false;
    if (T.roadDist(x, z) < (o.road ?? 2.8)) return false;
    if (T.riverDist(x, z) < (o.river ?? 13)) return false;
    const rf = T.riftInfo(x, z); if (rf.w > 0.1 && rf.d < rf.w + (o.rift ?? 6)) return false;
    if (T.inField(x, z)) return false;
    return isFree(x, z, o.r ?? 1);
  }
  function scatter(rng, n, cx, cz, rad, fn, o = {}) {
    let placed = 0;
    for (let t = 0; t < n * 6 && placed < n; t++) {
      const a = rng() * TAU, d = Math.sqrt(rng()) * rad, x = cx + Math.cos(a) * d, z = cz + Math.sin(a) * d;
      if (o.minR && Math.hypot(x - cx, z - cz) < o.minR) continue;
      if (o.where && !o.where(x, z)) continue;
      if (!valid(x, z, o)) continue;
      fn(x, z); if (o.reserve !== false) reserve(x, z, o.r ?? 1); placed++;
    }
  }
  function lineOf(key, a, b, step, o = {}) {
    const dx = b[0] - a[0], dz = b[1] - a[1], n = Math.max(1, Math.round(Math.hypot(dx, dz) / step));
    const rot = (o.axis ?? 'x') === 'x' ? Math.atan2(-dz, dx) : Math.atan2(dx, dz);
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n, x = a[0] + dx * t, z = a[1] + dz * t;
      if (o.skip?.(x, z, i)) continue;
      put(typeof key === 'function' ? key(i) : key, x, z, { rot, dy: o.dy ?? -0.05, s: o.s });
    }
  }

  /* Composite pieces */
  function house(x, z, o = {}, rng = Math.random) {
    const w = o.w ?? 2, floors = o.floors ?? 1, rot = o.rot ?? 0, s = o.s ?? KIT.town, W = WALLS[o.style ?? 'wood'];
    const hw = (w / 2) * s + 0.4;
    const y = Math.min(H(x, z), H(x + hw, z), H(x - hw, z), H(x, z + hw), H(x, z - hw)) - 0.05;
    const M = mat4(x, y, z, rot, s), mid = Math.floor((w - 1) / 2);
    const side = () => (rng() < 0.55 ? pick(W.win, rng) : W.plain);
    for (let f = 0; f < floors; f++) for (let i = 0; i < w; i++) {
      const lx = i - (w - 1) / 2;
      putLocal(M, f === 0 && i === mid ? W.door : side(), lx, f, 0, -Math.PI / 2);
      putLocal(M, side(), lx, f, 0, Math.PI / 2);
      if (i === 0) putLocal(M, side(), lx, f, 0, Math.PI);
      if (i === w - 1) putLocal(M, side(), lx, f, 0, 0);
    }
    const high = o.roof === 'high';
    if (w === 1) putLocal(M, high ? 'town/roof-high-point' : 'town/roof-point', 0, floors, 0);
    else {
      for (let i = 0; i < w; i++) putLocal(M, high ? 'town/roof-high-gable' : 'town/roof-gable', i - (w - 1) / 2, floors, 0, 0);
      if (o.chimney !== false && rng() < 0.5) putLocal(M, 'town/chimney', (w - 1) / 2, floors - 0.15, 0.1, 0);
    }
    if (o.porch && rng() < 0.6) putLocal(M, 'town/stairs-stone', mid - (w - 1) / 2, 0, 0.75, Math.PI);
    reserve(x, z, hw + 0.6);
    return { M, y, s };
  }
  function tower(kind, x, z, levels, stepB, stepT) {
    const s = KIT.td; let y = H(x, z) - 0.15;
    put(`td/tower-${kind}-bottom-a`, x, z, { y }); y += stepB * s;
    for (let l = 0; l < levels; l++) { put(`td/tower-${kind}-middle-a`, x, z, { y }); y += stepB * s; }
    put(`td/tower-${kind}-top-a`, x, z, { y }); y += stepT * s;
    put(`td/tower-${kind}-roof-a`, x, z, { y }); reserve(x, z, 2.2);
  }
  const towerRound = (x, z, levels = 2) => tower('round', x, z, levels, 0.6, 0.5);
  const towerSquare = (x, z, levels = 2) => tower('square', x, z, levels, 0.5, 0.5);

  /* Automatic bridges where a road crosses the river */
  function bridge(a, b, deckY) {
    const dx = b[0] - a[0], dz = b[1] - a[1], len = Math.hypot(dx, dz), n = Math.ceil(len / 1.45);
    const rot = Math.atan2(dx, dz), nx = Math.cos(rot), nz = -Math.sin(rot);
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n, x = a[0] + dx * t, z = a[1] + dz * t;
      for (const off of [-0.75, 0.75]) put('town/planks', x + nx * off, z + nz * off, { y: deckY, rot });
      for (const off of [-1.55, 1.55]) put('town/poles', x + nx * off, z + nz * off, { y: deckY, rot: rot + (off < 0 ? Math.PI : 0) });
      if (i % 2 === 0) for (const off of [-1.4, 1.4]) put('town/pillar-wood', x + nx * off, z + nz * off, { y: -1.8, rot, sy: (deckY + 1.8) / KIT.town });
    }
    put('town/lantern', a[0] + nx * 1.9, a[1] + nz * 1.9); put('town/lantern', b[0] - nx * 1.9, b[1] - nz * 1.9);
    bridges.push({ a, b, y: deckY + 0.1, w: 1.9 });
  }
  function autoBridges() {
    for (const road of DATA.roads) for (let i = 0; i < road.length - 1; i++) for (let j = 0; j < DATA.river.length - 1; j++) {
      const p = segX(road[i], road[i + 1], DATA.river[j], DATA.river[j + 1]); if (!p) continue;
      const dx = road[i + 1][0] - road[i][0], dz = road[i + 1][1] - road[i][1], L = Math.hypot(dx, dz), ux = dx / L, uz = dz / L;
      let t1 = 2, t2 = 2;
      while (t1 < 30 && H(p[0] - ux * t1, p[1] - uz * t1) < 1.2) t1 += 0.5;
      while (t2 < 30 && H(p[0] + ux * t2, p[1] + uz * t2) < 1.2) t2 += 0.5;
      const a = [p[0] - ux * (t1 + 1), p[1] - uz * (t1 + 1)], b = [p[0] + ux * (t2 + 1), p[1] + uz * (t2 + 1)];
      bridge(a, b, Math.max(H(...a), H(...b)) + 0.15);
    }
  }
  const onBridge = (x, z) => bridges.some((b) => distPoly([b.a, b.b], x, z).d < b.w + 0.6);

  /* Paved roads */
  function paveRoads(rng) {
    for (const road of DATA.roads) for (let i = 0; i < road.length - 1; i++) {
      const [ax, az] = road[i], [bx, bz] = road[i + 1], L = Math.hypot(bx - ax, bz - az), ux = (bx - ax) / L, uz = (bz - az) / L, rot = Math.atan2(ux, uz);
      for (let d = 0; d <= L; d += 1.42) {
        const x = ax + ux * d, z = az + uz * d;
        if (Math.hypot(x, z) < 16.5 || H(x, z) < 0.4 || onBridge(x, z)) continue;
        for (const off of [-0.72, 0.72]) putTilt('town/road', x + uz * off, z - ux * off, rot);
        if (rng() < 0.05) putTilt('grave/debris', x + uz * 2.2, z - ux * 2.2, rng() * TAU, { dy: 0 });
      }
    }
  }
  function pavePlaza() { for (let x = -16; x <= 16; x += 1.48) for (let z = -16; z <= 16; z += 1.48) if (Math.hypot(x, z) < 16.2) put('town/road', x, z, { dy: 0.04 }); }
  function roadLanterns(rng) {
    for (const road of DATA.roads) {
      const { len } = distPoly(road, road[0][0], road[0][1]); let acc = 0, side = 1;
      for (let i = 0; i < road.length - 1; i++) {
        const [ax, az] = road[i], [bx, bz] = road[i + 1], L = Math.hypot(bx - ax, bz - az), ux = (bx - ax) / L, uz = (bz - az) / L;
        for (let d = 8 - (acc % 18); d < L; d += 18) {
          side = -side; const x = ax + ux * d + uz * 2.6 * side, z = az + uz * d - ux * 2.6 * side;
          if (Math.hypot(x, z) < 20 || H(x, z) < 1 || onBridge(x, z) || !isFree(x, z, 0.4)) continue;
          put('town/lantern', x, z, { rot: rng() * TAU });
        }
        acc += L;
      }
      if (len > 30 && Math.hypot(...road[0]) > 20) { const [x, z] = road[0]; put('survival/signpost', x + 3, z + 2.5, { rot: rng() * TAU, s: 1.5 }); }
    }
  }
  const banner = (x, z, faction, h = 6) => { banners.push({ x, z, faction, h }); reserve(x, z, 0.6); };

  return {
    T, H, DATA, batches, spawns, banners, extras, bridges,
    put, putLocal, putTilt, spawn, reserve, isFree, valid, scatter, lineOf, house, towerRound, towerSquare,
    autoBridges, onBridge, paveRoads, pavePlaza, roadLanterns, banner,
  };
}

/** Builds the whole valley. The call order is fixed: every builder draws from the same seeded RNG. */
export function buildLayout(P, rng) {
  P.autoBridges();
  buildPlaza(P, rng); buildBahia(P, rng); buildMuralla(P, rng); buildCementerio(P, rng);
  buildCampos(P, rng); buildBosque(P, rng); buildCumbres(P, rng); buildCountry(P, rng);
  P.paveRoads(rng); P.roadLanterns(rng); buildGrass(P, rng);
}
