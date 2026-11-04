// Plaza del Ciclo, Bahía del Gremio and Muralla del Norte.
import { TAU, faceTo, lerp, pick } from '../noise.js';

function plazaRoadAngles(DATA) {
  return DATA.roads.filter((r) => Math.hypot(...r[0]) < 24).map((r) => Math.atan2(r[1][1] - r[0][1], r[1][0] - r[0][0]));
}

export function buildPlaza(P, rng) {
  const { put, reserve, isFree, house, banner, spawn, extras } = P;
  const angles = plazaRoadAngles(P.DATA);
  const nearRoadAngle = (a, tol) => angles.some((ra) => Math.abs(Math.atan2(Math.sin(a - ra), Math.cos(a - ra))) < tol);
  put('town/fountain-round-detail', 0, 0); reserve(0, 0, 5);
  P.pavePlaza();
  for (let i = 0; i < 10; i++) { const a = (i / 10) * TAU + 0.3; put('town/lantern', Math.cos(a) * 11, Math.sin(a) * 11); }
  for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU + 0.2, x = Math.cos(a) * 6.8, z = Math.sin(a) * 6.8; put('grave/bench', x, z, { rot: faceTo(x, z, 0, 0) }); }
  extras.push({ type: 'board', x: 10, z: -9, rot: faceTo(10, -9, 0, 0) }); reserve(10, -9, 2.2);
  let k = 0;
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * TAU + 0.15; if (nearRoadAngle(a, 0.3)) continue;
    const x = Math.cos(a) * 14, z = Math.sin(a) * 14; if (!isFree(x, z, 1.4)) continue;
    put(k++ % 2 ? 'town/stall-green' : 'town/stall-red', x, z, { rot: faceTo(x, z, 0, 0) }); put('town/stall-bench', x * 0.9, z * 0.9, { rot: faceTo(x, z, 0, 0) + Math.PI / 2 }); reserve(x, z, 1.6);
  }
  put('town/cart', -15, 12, { rot: 0.6 }); put('town/cart-high', 13, 15, { rot: -0.9 }); put('pirate/barrel', -14, 14); put('pirate/crate', 15, 12, { rot: 0.4 }); put('pirate/crate-bottles', 16, 10.5, { rot: 1.2 });
  for (const [r0, r1, n] of [[22, 25, 26], [32, 37, 34]]) for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU + rng() * 0.05; if (nearRoadAngle(a, 0.2)) continue;
    const rr = lerp(r0, r1, rng()), x = Math.cos(a) * rr, z = Math.sin(a) * rr; if (!isFree(x, z, 2.2) || P.T.roadDist(x, z) < 3.6) continue;
    house(x, z, { w: 1 + Math.floor(rng() * 3), floors: 1 + (rng() < 0.5 ? 1 : 0), rot: faceTo(x, z, 0, 0),
      style: rng() < 0.4 ? 'stone' : 'wood', roof: rng() < 0.35 ? 'high' : 'gable', porch: true }, rng);
  }
  banner(-4, -18, 'gremio', 5); banner(0, -18.6, 'orden', 5); banner(4, -18, 'culto', 5);
  spawn('chars/character-female-b', -4, 10, { anim: 'idle', rot: 2.6 });
  spawn('chars/character-male-c', 7, 8, { anim: 'idle', rot: -2.2 });
  spawn('chars/character-female-d', 11, -5, { anim: 'idle', rot: -1.1 });
  spawn('chars/character-male-a', -12, -6, { anim: 'idle', rot: 1.2 });
  spawn('chars/character-male-e', 0, 8.6, { walkCircle: { cx: 0, cz: 0, r: 8.6, speed: 0.2 } });
  spawn('chars/character-female-b', 0, -12.5, { walkCircle: { cx: 0, cz: 0, r: 12.5, speed: -0.13 } });
}

function pier(P, x, z, ux, uz, maxN) {
  const rot = Math.atan2(ux, uz); let n = 0;
  for (let i = 0; i < 40 && n < maxN; i++) {
    const px = x + ux * 2.25 * i, pz = z + uz * 2.25 * i;
    if (P.H(px, pz) > 1.6) continue;
    P.put('pirate/structure-platform-dock', px, pz, { y: -0.75, rot }); n++;
  }
}

export function buildBahia(P, rng) {
  const { put, reserve, house, banner, spawn, scatter, extras, H } = P;
  put('pirate/tower-complete-large', -48, 176); reserve(-48, 176, 4);
  extras.push({ type: 'beam', x: -48, z: 176 });
  pier(P, -10, 122, 0, 1, 16); pier(P, 28, 120, 0.1, 1, 14); pier(P, -30, 134, -0.3, 1, 8);
  spawn('pirate/ship-large', -22, 168, { y: -0.7, rot: 0.25, bob: 1 });
  spawn('pirate/ship-pirate-medium', 46, 160, { y: -0.7, rot: -0.35, bob: 1 });
  spawn('pirate/ship-large', 14, 190, { y: -0.7, rot: 1.4, bob: 1 });
  spawn('pirate/boat-row-large', 6, 150, { y: -0.25, rot: 1.2, bob: 0.4 });
  spawn('pirate/boat-row-small', 36, 146, { y: -0.25, rot: -0.6, bob: 0.4 });
  spawn('pirate/boat-row-small', -18, 150, { y: -0.25, rot: 2.6, bob: 0.4 });
  spawn('pirate/ship-ghost', -144, 224, { y: -0.6, rot: 0.9, bob: 1.4, ghost: true });
  put('pirate/ship-wreck', 92, 216, { y: -1.6, rot: 1.1 });
  for (let i = 0; i < 12; i++) put(pick(['pirate/rocks-sand-a', 'pirate/rocks-a', 'pirate/rocks-b'], rng), 80 + rng() * 28, 202 + rng() * 26, { y: -1.2, rot: rng() * TAU, s: 0.8 + rng() });
  [[-18, 116], [-6, 122], [22, 114], [34, 118], [44, 108], [-28, 108]].forEach(([x, z], i) => {
    const y = H(x, z) - 0.1, rot = faceTo(x, z, 8, 140);
    put('pirate/structure', x, z, { y, rot }); put('pirate/structure-roof', x, z, { y: y + 2.2 * 0.9, rot }); reserve(x, z, 3.4);
    if (i % 2) put('pirate/flag-pennant', x + 2.6, z, { rot });
  });
  house(8, 116, { w: 3, floors: 2, style: 'stone', rot: Math.PI, roof: 'high', chimney: true }, rng);
  [[2, 104], [8, 100], [14, 104], [-4, 100], [20, 100]].forEach(([x, z], i) => { put(i % 2 ? 'town/stall-green' : 'town/stall-red', x, z, { rot: faceTo(x, z, 8, 108) }); reserve(x, z, 1.5); });
  scatter(rng, 50, 8, 122, 20, (x, z) => put(pick(['pirate/barrel', 'pirate/crate', 'pirate/crate-bottles', 'pirate/chest', 'pirate/bottle-large'], rng), x, z, { rot: rng() * TAU }), { minH: 0.6, road: 1.8, river: 8, r: 0.7 });
  put('pirate/cannon', -32, 146, { rot: 0.1 }); put('pirate/cannon', 52, 140, { rot: -0.3 }); put('pirate/cannon', -38, 140, { rot: 0.4 });
  put('pirate/mast', 58, 128, { rot: 1.2, y: H(58, 128) - 0.3 });
  scatter(rng, 22, 8, 92, 26, (x, z) => house(x, z, { w: 1 + Math.floor(rng() * 3), floors: 1 + (rng() < 0.35 ? 1 : 0), rot: faceTo(x, z, 8, 80), style: 'wood', porch: true }, rng), { r: 3.6, road: 3.8, reserve: false });
  scatter(rng, 320, 0, 120, 200, (x, z) => put(rng() < 0.5 ? 'pirate/palm-straight' : 'pirate/palm-bend', x, z, { rot: rng() * TAU, s: 0.8 + rng() * 0.5 }),
    { minH: 0.15, maxH: 1.6, river: 8, r: 1.8, where: (x, z) => z > 80 || Math.hypot(x, z) > 184 });
  banner(-10, 124, 'gremio'); banner(28, 122, 'gremio'); banner(-42, 174, 'gremio', 5); banner(8, 110, 'gremio', 7);
  spawn('chars/character-male-a', 4, 128, { anim: 'idle', rot: 3 });
  spawn('chars/character-female-d', 14, 108, { anim: 'idle', rot: -2.4 });
  spawn('chars/character-male-c', -12, 130, { anim: 'idle', rot: 1.6 });
}

export function buildMuralla(P, rng) {
  const { put, reserve, isFree, house, banner, spawn, scatter, lineOf, towerRound, towerSquare, H } = P;
  const riverDist = P.T.riverDist;
  const wz = (x) => -132 + Math.sin(x * 0.025) * 4;
  for (let x = -150; x <= 150; x += 1.44) {
    const z = wz(x); if (Math.abs(x) < 3.4) continue;
    if (riverDist(x, z) < 12 || H(x, z) < 1) continue;
    put('pirate/castle-wall', x, z, { rot: Math.atan2(-Math.cos(x * 0.025) * 0.1, 1), dy: -0.4 }); reserve(x, z, 1.4);
  }
  put('pirate/castle-gate', 0, wz(0), { dy: -0.3 });
  for (const x of [-124, -96, -40, -5.2, 5.2, 30, 62, 94, 124]) if (H(x, wz(x)) > 1 && riverDist(x, wz(x)) > 12) towerRound(x, wz(x), x === -96 ? 3 : 2);
  const bx = 48, bz = -100, e = 10;
  const corners = [[bx - e, bz - e], [bx + e, bz - e], [bx + e, bz + e], [bx - e, bz + e]];
  corners.forEach(([x, z]) => towerSquare(x, z, 2));
  for (let i = 0; i < 4; i++) {
    const a = corners[i], b = corners[(i + 1) % 4];
    lineOf('pirate/castle-wall', a, b, 1.44, { dy: -0.4, skip: (x, z) => Math.hypot(x - a[0], z - a[1]) < 2.2 || Math.hypot(x - b[0], z - b[1]) < 2.2 || (i === 2 && Math.abs(x - bx) < 2.4) });
  }
  reserve(bx, bz, 13);
  house(bx - 3, bz - 3, { w: 3, floors: 2, style: 'stone', rot: 0, roof: 'high' }, rng);
  house(bx + 5, bz - 4, { w: 1, floors: 3, style: 'stone', rot: 0 }, rng);
  put('td/weapon-ballista', bx + 4, bz + 4, { rot: Math.PI }); put('td/weapon-catapult', bx - 5, bz + 5, { rot: Math.PI }); put('td/weapon-cannon', bx, bz + 6, { rot: Math.PI });
  for (let x = -120; x <= 120; x += 22) { const z = wz(x) + 7; if (Math.abs(x) > 6 && H(x, z) > 1 && riverDist(x, z) > 12 && isFree(x, z, 1.2)) put(x % 44 ? 'td/weapon-catapult' : 'td/weapon-ballista', x, z, { rot: Math.PI }); }
  put('td/weapon-cannon', -9, -122, { rot: Math.PI }); put('td/weapon-cannon', 9, -122, { rot: Math.PI });
  scatter(rng, 14, -28, -100, 18, (x, z) => house(x, z, { w: 1 + Math.floor(rng() * 3), floors: 1 + (rng() < 0.5 ? 1 : 0), rot: faceTo(x, z, -28, -100), style: 'stone', porch: true }, rng), { r: 3.8, road: 3.4, reserve: false });
  for (let i = 0; i < 6; i++) put('survival/structure', -10 + i * 1.8, -110, { s: 1.2, rot: Math.PI }); // training stakes
  banner(-4.5, -126, 'orden', 7); banner(4.5, -126, 'orden', 7); banner(bx, bz + e + 2, 'orden', 7); banner(-96, -126, 'orden', 6); banner(-28, -88, 'orden', 6);
  spawn('chars/character-male-c', 0, -120, { anim: 'idle', rot: 0 });
  spawn('chars/character-male-a', 48, -88, { anim: 'idle', rot: 0.4 });
  spawn('chars/character-male-e', -6, -112, { anim: 'idle', rot: Math.PI });
}
