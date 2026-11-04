// Open countryside: the gravestone road, crossroad hamlets, scattered trees/rocks and the grass pass.
import { TAU, faceTo, pick } from '../noise.js';
import { STONES } from './este.js';

const TREES = ['town/tree', 'town/tree-high', 'town/tree-crooked', 'town/tree-high-round', 'survival/tree-tall'];
const GRASS = ['survival/grass-large', 'survival/grass-large', 'survival/grass', 'pirate/grass-plant', 'pirate/grass-patch', 'pirate/grass'];

export function buildCountry(P, rng) {
  const { put, reserve, isFree, house, banner, scatter } = P;
  // Camino de las Lápidas
  const road = P.DATA.roads[6];
  for (let i = 0; i < road.length - 1; i++) {
    const [ax, az] = road[i], [bx, bz] = road[i + 1], L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
    for (let d = 1.5; d < L; d += 3.4) for (const sgn of [-1, 1]) {
      const x = ax + ((bx - ax) * d) / L + nx * sgn * 3.8, z = az + ((bz - az) * d) / L + nz * sgn * 3.8;
      if (!isFree(x, z, 0.6)) continue;
      put(pick(STONES, rng), x, z, { rot: Math.atan2(nx * -sgn, nz * -sgn) }); reserve(x, z, 0.6);
    }
  }
  banner(60, -92, 'culto'); banner(100, -64, 'culto');
  // Crossroad hamlets
  for (const [x, z, n] of [[52, 52, 6], [10, 60, 5], [56, -24, 5], [-64, 8, 4]]) {
    scatter(rng, n, x, z, 16, (hx, hz) => house(hx, hz, { w: 1 + Math.floor(rng() * 3), floors: 1 + (rng() < 0.3 ? 1 : 0), rot: faceTo(hx, hz, x, z), style: rng() < 0.3 ? 'stone' : 'wood', porch: true }, rng), { r: 3.8, road: 3.6, reserve: false });
    scatter(rng, 4, x, z, 14, (hx, hz) => put(pick(['town/cart', 'pirate/barrel', 'grave/hay-bale', 'town/stall-red'], rng), hx, hz, { rot: rng() * TAU }), { r: 1 });
  }
  // Open field
  scatter(rng, 1700, 0, 0, 210, (x, z) => put(pick(TREES, rng), x, z, { rot: rng() * TAU, s: 0.9 + rng() * 0.6 }),
    { r: 1.7, where: (x, z) => z > -128 && Math.hypot(x, z) > 44 });
  scatter(rng, 320, 0, 0, 210, (x, z) => put(pick(['town/rock-large', 'town/rock-wide', 'town/rock-small', 'survival/rock-b', 'td/detail-rocks-large'], rng), x, z, { rot: rng() * TAU, s: 0.6 + rng() * 1.0, dy: -0.2 }), { r: 1.4 });
  scatter(rng, 110, 0, -40, 200, (x, z) => put('town/hedge-large', x, z, { rot: rng() * TAU, s: 0.8 + rng() * 0.4 }), { r: 0.9, where: (x, z) => Math.hypot(x, z) > 40 });
  scatter(rng, 70, 0, 0, 210, (x, z) => put('pirate/patch-sand-foliage', x, z, { rot: rng() * TAU, dy: -0.05 }), { minH: 0.1, maxH: 1.1, r: 3, reserve: false });
}

export function buildGrass(P, rng) {
  const { H, put, putTilt, isFree } = P;
  const { isSnow, roadDist, riverDist, inField, riftInfo } = P.T;
  let n = 0;
  for (let t = 0; t < 26000 && n < 9500; t++) {
    const a = rng() * TAU, d = Math.sqrt(rng()) * 215, x = Math.cos(a) * d, z = Math.sin(a) * d, h = H(x, z);
    if (h < 1.1 || isSnow(x, z, h) || Math.hypot(x, z) < 18) continue;
    if (roadDist(x, z) < 2.3 || riverDist(x, z) < 9 || inField(x, z)) continue;
    const rf = riftInfo(x, z); if (rf.w > 0.1 && rf.d < rf.w + 3) continue;
    if (!isFree(x, z, 0.35)) continue;
    put(pick(GRASS, rng), x, z, { rot: rng() * TAU, s: 0.7 + rng() * 0.7, dy: -0.04 }); n++;
  }
  for (let t = 0, m = 0; t < 4000 && m < 260; t++) {
    const x = (rng() - 0.5) * 420, z = (rng() - 0.5) * 420, h = H(x, z);
    if (h < 1.2 || isSnow(x, z, h) || roadDist(x, z) < 4 || riverDist(x, z) < 12 || inField(x, z) || !isFree(x, z, 2.5)) continue;
    putTilt('pirate/patch-grass-foliage', x, z, rng() * TAU, { dy: -0.08 }); m++;
  }
}
