// Campos y Molinos and Cumbres Heladas.
import * as THREE from 'three';
import { TAU } from '../noise.js';
import { KIT } from '../kits.js';
import { camp } from './este.js';

function windmill(P, x, z, rot, rng) {
  const s = KIT.town * 1.6, hs = P.house(x, z, { w: 1, floors: 3, rot, style: 'stone', s, roof: 'point', grow: false }, rng);
  const p = new THREE.Vector3(0.68, 2.45, 0).applyMatrix4(hs.M);
  P.grown('comida', x, z, () => P.spawn('town/windmill', p.x, p.z, { y: p.y, rot, s: 1.6, spinX: 0.7 }), 'spin'); // blades turn with the food
}

export function buildCampos(P, rng) {
  const { put, reserve, isFree, house, banner, spawn, scatter, lineOf, H } = P;
  const { riverDist, roadDist } = P.T;
  for (const f of P.DATA.fields) {
    const c = Math.cos(f.rot), s = Math.sin(f.rot), trigo = f.crop === 'trigo', key = trigo ? 'proc/wheat' : 'proc/veg';
    P.grown('comida', f.c[0], f.c[1], () => { // the whole field is sown or fallow
      for (let lz = -f.d / 2 + 0.6; lz < f.d / 2; lz += trigo ? 1.2 : 1.3) for (let lx = -f.w / 2 + 0.4; lx < f.w / 2; lx += trigo ? 0.6 : 1.1) {
        const x = f.c[0] + lx * c + lz * s, z = f.c[1] - lx * s + lz * c;
        if (H(x, z) < 1 || riverDist(x, z) < 10 || roadDist(x, z) < 2.2) continue;
        put(key, x, z, { rot: rng() * TAU, s: 0.75 + rng() * 0.5, dy: -0.05 });
      }
    });
    reserve(f.c[0], f.c[1], Math.min(f.w, f.d) / 2);
    const corner = (u, v) => [f.c[0] + u * c + v * s, f.c[1] - u * s + v * c], hw = f.w / 2 + 0.8, hd = f.d / 2 + 0.8;
    const cs = [corner(-hw, -hd), corner(hw, -hd), corner(hw, hd), corner(-hw, hd)];
    for (let i = 0; i < 4; i++) lineOf(i === 0 ? (j) => (j === 3 ? 'town/fence-gate' : 'town/fence') : 'town/fence', cs[i], cs[(i + 1) % 4], 1.5,
      { axis: 'z', skip: (x, z) => H(x, z) < 1 || riverDist(x, z) < 10 || roadDist(x, z) < 2 });
  }
  for (const [x, z, r] of [[-152, -26, 0.6], [-184, 24, 1.4], [-142, 54, 2.3], [-196, -14, 0.2]]) windmill(P, x, z, r, rng);
  // Water mill by the river
  house(-70, -60, { w: 2, floors: 1, rot: -Math.PI / 2, style: 'wood', grow: false }, rng);
  P.grown('comida', -70, -60, () => spawn('town/watermill-wide', -76.2, -60.6, { y: 0.7, rot: 0, spinX: -1.1 }), 'spin');
  // Orchards
  for (const [ox, oz] of [[-126, -50], [-118, 34]]) for (let i = 0; i < 4; i++) for (let j = 0; j < 5; j++) {
    const x = ox + i * 4.2, z = oz + j * 4.2;
    if (isFree(x, z, 1) && roadDist(x, z) > 3 && riverDist(x, z) > 12) { put('town/tree-high-round', x, z, { rot: rng() * TAU, s: 0.85 }); reserve(x, z, 1.2); }
  }
  scatter(rng, 16, -150, 8, 52, (x, z) => house(x, z, { w: 1 + Math.floor(rng() * 3), floors: 1 + (rng() < 0.2 ? 1 : 0), rot: rng() * TAU, style: 'wood', porch: true }, rng), { r: 3.8, road: 3.6, reserve: false });
  scatter(rng, 90, -152, 8, 60, (x, z) => { const k = rng() < 0.5 ? 'grave/hay-bale' : 'grave/hay-bale-bundled', rot = rng() * TAU; P.grown('comida', x, z, () => put(k, x, z, { rot, s: 1.2 })); }, { r: 0.8, road: 2 });
  scatter(rng, 10, -152, 8, 56, (x, z) => put(rng() < 0.5 ? 'town/cart-high' : 'town/cart', x, z, { rot: rng() * TAU }), { r: 1.4, road: 2.6 });
  scatter(rng, 14, -152, 8, 56, (x, z) => { put('pirate/tool-shovel', x, z, { rot: rng() * TAU, s: 1.4 }); put('survival/bucket', x + 0.8, z, { s: 1.4 }); }, { r: 1 });
  banner(-100, -30, 'orden'); banner(-74, -42, 'orden');
  spawn('chars/character-male-e', -158, -18, { anim: 'idle', rot: 0.3 });
  spawn('chars/character-female-b', -136, 20, { anim: 'idle', rot: 2 });
}

export function buildCumbres(P, rng) {
  const { put, reserve, scatter, H } = P;
  const ax = 0, az = -196;
  for (let i = 0; i < 16; i++) { const a = (i / 16) * TAU, x = ax + Math.cos(a) * 17, z = az + Math.sin(a) * 17; put('grave/column-large', x, z, { rot: a, s: 1.25 }); }
  put('grave/altar-stone', ax, az, { s: 1.6 }); put('grave/fire-basket', ax, az + 4, { s: 3 }); put('grave/fire-basket', ax, az - 4, { s: 3 });
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * TAU + 0.2, x = ax + Math.cos(a) * 24, z = az + Math.sin(a) * 24;
    put('td/snow-wood-structure-high', x, z, { rot: -a }); put('td/snow-wood-structure-high', x, z, { rot: -a, y: H(x, z) + 3 });
  }
  reserve(ax, az, 27);
  camp(P, -38, -170, 3, rng); put('grave/fire-basket', -33, -165, { s: 2 });
  scatter(rng, 1200, 0, -190, 140, (x, z) => put(rng() < 0.7 ? 'td/snow-detail-tree-large' : 'td/snow-detail-tree', x, z, { rot: rng() * TAU, s: 1.4 + rng() * 1.2 }),
    { r: 1.4, minH: 3, where: (x, z) => z < -140 && P.T.isSnow(x, z, H(x, z)) });
  scatter(rng, 160, 0, -190, 140, (x, z) => put('td/snow-detail-rocks-large', x, z, { rot: rng() * TAU, s: 1 + rng() * 1.6 }), { r: 1.6, minH: 3, where: (x, z) => z < -144 });
}
