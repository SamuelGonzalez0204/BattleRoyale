// Cementerio de la Grieta (with the Altar del Eco and the rift crystals) and Bosque de los Exploradores.
import { TAU, pick } from '../noise.js';

const STONES = ['grave/gravestone-cross', 'grave/gravestone-round', 'grave/gravestone-wide', 'grave/gravestone-decorative', 'grave/gravestone-broken'];
const FOREST = ['survival/tree-tall', 'survival/tree-autumn-tall', 'survival/tree-autumn', 'survival/tree', 'town/tree-high', 'survival/tree-autumn-tall'];
export { STONES };

export function camp(P, cx, cz, tents, rng, light = false) {
  const { put } = P;
  put('survival/campfire-pit', cx, cz, { s: 1.2 }); put('survival/campfire-stand', cx, cz, { s: 1.2 });
  if (light) P.extras.push({ type: 'fire', x: cx, z: cz });
  for (let i = 0; i < tents; i++) {
    const a = (i / tents) * TAU + 0.5, x = cx + Math.cos(a) * 5.8, z = cz + Math.sin(a) * 5.8;
    put(i % 2 ? 'survival/tent' : 'survival/tent-canvas', x, z, { rot: Math.atan2(cx - x, cz - z) });
  }
  for (let i = 0; i < 4; i++) { const a = (i / 4) * TAU, x = cx + Math.cos(a) * 2.5, z = cz + Math.sin(a) * 2.5; put('survival/tree-log', x, z, { rot: a, s: 0.7 }); }
  P.reserve(cx, cz, 8);
}

function riftCrystals(P, rng) {
  const pts = P.DATA.rift;
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, az] = pts[i], [bx, bz] = pts[i + 1], L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
    for (let d = 0; d < L; d += 1.6) {
      const x0 = ax + ((bx - ax) * d) / L, z0 = az + ((bz - az) * d) / L, w = P.T.riftInfo(x0, z0).w; if (w < 0.8) continue;
      for (const sgn of [-1, 1]) {
        if (rng() < 0.3) continue;
        const off = sgn * (w + 0.6 + rng() * 3), x = x0 + nx * off, z = z0 + nz * off;
        P.put(rng() < 0.6 ? 'td/detail-crystal-large#glow' : 'td/detail-crystal#glow', x, z, { rot: rng() * TAU, s: 0.6 + rng() * 1.1, dy: -0.2 });
      }
    }
  }
}

export function buildCementerio(P, rng) {
  const { put, putTilt, reserve, isFree, banner, spawn, scatter, lineOf } = P;
  const X0 = 108, X1 = 156, Z0 = -66, Z1 = -22, fence = () => (rng() < 0.18 ? 'grave/iron-fence-damaged' : 'grave/iron-fence');
  lineOf(fence, [X0, Z0], [X1, Z0], 1.4); lineOf(fence, [X0, Z1], [X1, Z1], 1.4);
  lineOf(fence, [X1, Z0], [X1, Z1], 1.4); lineOf(fence, [X0, Z0], [X0, Z1], 1.4, { skip: (x, z) => z > -48 && z < -40 });
  put('grave/crypt-large', 148, -32, { rot: -Math.PI / 2, s: 1.2 }); reserve(148, -32, 5.6);
  [114, 120, 126, 140, 146, 152].forEach((x, i) => { put(i % 3 === 1 ? 'grave/crypt' : 'grave/crypt-small', x, -63); reserve(x, -63, 2); });
  for (let z = -59; z <= -25; z += 2.6) for (let x = 111; x <= 153; x += 2.2) {
    if (Math.abs(x - 132) < 2 || Math.abs(z + 44) < 1.6 || !isFree(x, z, 0.9) || rng() < 0.16) continue;
    const jx = x + (rng() - 0.5) * 0.5, jz = z + (rng() - 0.5) * 0.4;
    put(pick(STONES, rng), jx, jz, { rot: Math.PI + (rng() - 0.5) * 0.4 });
    if (rng() < 0.55) put(rng() < 0.5 ? 'grave/grave' : 'grave/grave-border', jx, jz + 1.0, { rot: Math.PI });
    if (rng() < 0.12) put('grave/candle-multiple', jx + 0.5, jz + 0.4);
    if (rng() < 0.06) put('grave/pumpkin-carved', jx - 0.5, jz + 0.5, { rot: rng() * TAU });
    if (rng() < 0.04) put('grave/urn-round', jx + 0.6, jz - 0.2);
  }
  for (let z = -64; z <= -24; z += 1.3) putTilt('grave/road', 132, z, rng() * 0.3, { dy: 0.02, s: 1.3 });
  for (let x = X0; x <= 132; x += 1.3) putTilt('grave/road', x, -44, rng() * 0.3, { dy: 0.02, s: 1.3 });
  for (const z of [-60, -50, -38, -28]) put('grave/lightpost-double', 134, z);
  put('grave/fire-basket', X0 - 1, -49, { s: 2 }); put('grave/fire-basket', X0 - 1, -39, { s: 2 });
  put('grave/altar-wood', 126, -46, { rot: Math.PI / 2 }); put('grave/cross-wood', 124.5, -46, { s: 1.6 });
  reserve(132, -44, 30);
  scatter(rng, 160, 132, -44, 56, (x, z) => put(rng() < 0.6 ? 'grave/pine' : 'grave/pine-crooked', x, z, { rot: rng() * TAU, s: 1.2 + rng() * 0.7 }), { minR: 36, r: 1.5 });
  scatter(rng, 30, 132, -44, 50, (x, z) => put(pick(['grave/trunk', 'grave/trunk-long', 'grave/debris', 'grave/cross-wood'], rng), x, z, { rot: rng() * TAU }), { minR: 34, r: 1 });
  // Altar del Eco
  put('grave/altar-stone', 168, -18, { rot: 0.4 }); reserve(168, -18, 4);
  for (let i = 0; i < 6; i++) { const a = (i / 6) * TAU + 0.4; put('grave/pillar-obelisk', 168 + Math.cos(a) * 4, -18 + Math.sin(a) * 4); }
  put('grave/candle-multiple', 167, -16.5); put('grave/candle-multiple', 169.2, -19.2); put('grave/fire-basket', 171, -15, { s: 2 });
  riftCrystals(P, rng);
  for (let i = 0; i < 8; i++) spawn('grave/character-ghost', 112 + rng() * 40, -62 + rng() * 34, { ghost: true, anim: 'idle', drift: rng() * TAU });
  spawn('chars/character-female-d', 144, -32, { anim: 'idle', rot: Math.PI / 2 });
  banner(X0 - 3, -50, 'culto'); banner(X0 - 3, -38, 'culto'); banner(164, -14, 'culto', 7);
}

export function buildBosque(P, rng) {
  const { put, reserve, banner, spawn, scatter, H } = P;
  const cx = 124, cz = 104;
  camp(P, cx, cz, 6, rng, true);
  put('survival/workbench', cx + 3.4, cz - 3.4, { rot: 0.5 }); put('survival/workbench-anvil', cx + 4.6, cz - 2.2, { rot: 0.8 });
  put('survival/box-large', cx - 3.6, cz - 3.6, { rot: 0.3 }); put('survival/box', cx - 3, cz - 4.4); put('survival/barrel', cx - 4.4, cz - 2.8);
  put('survival/bedroll', cx + 1.6, cz + 3.6, { rot: 0.4 }); put('survival/resource-wood', cx + 1, cz - 2.4, { s: 1.4 });
  put('survival/campfire-fishing-stand', cx - 1.2, cz + 1.4, { s: 1.4 }); put('survival/fish-large', cx - 1.4, cz + 2.2, { s: 1.6 });
  for (let i = 0; i < 30; i++) { const a = (i / 30) * TAU; if (Math.abs(Math.sin(a * 2)) < 0.25) continue; put('survival/fence-fortified', cx + Math.cos(a) * 10.5, cz + Math.sin(a) * 10.5, { rot: -a + Math.PI / 2 }); }
  reserve(cx, cz, 12);
  let y = H(160, 140) - 0.1; for (let i = 0; i < 3; i++) { put('td/wood-structure-high', 160, 140, { y }); y += 3; }
  put('td/tower-square-roof-a', 160, 140, { y }); reserve(160, 140, 2.6);
  camp(P, 176, 90, 3, rng); camp(P, 96, 150, 2, rng);
  scatter(rng, 2200, 124, 100, 84, (x, z) => put(pick(FOREST, rng), x, z, { rot: rng() * TAU, s: 0.8 + rng() * 0.7 }), { r: 1.3 });
  scatter(rng, 160, 124, 100, 84, (x, z) => put(pick(['survival/tree-trunk', 'survival/tree-autumn-trunk', 'survival/tree-log', 'survival/rock-b', 'survival/rock-c'], rng), x, z, { rot: rng() * TAU, s: 1.2 }), { r: 0.8 });
  // Cala de los Contrabandistas
  spawn('pirate/boat-row-small', 214, 44, { y: -0.25, rot: 2.2, bob: 0.4 });
  spawn('pirate/boat-row-large', 218, 60, { y: -0.25, rot: 1.4, bob: 0.4 });
  [[198, 46, 'pirate/crate'], [196.6, 48.6, 'pirate/crate-bottles'], [200.4, 54.6, 'pirate/barrel'], [203, 52.4, 'pirate/chest'], [197, 52, 'pirate/barrel']].forEach(([x, z, k]) => put(k, x, z, { rot: rng() * TAU }));
  const hy = H(194, 56) - 0.1; put('pirate/structure', 194, 56, { y: hy, rot: 1.2 }); put('pirate/structure-roof', 194, 56, { y: hy + 1.98, rot: 1.2 });
  put('town/lantern', 195, 50); put('pirate/rocks-a', 208, 32, { y: -0.8, rot: 1 }); put('pirate/rocks-b', 206, 68, { y: -0.8, rot: 2 });
  reserve(200, 50, 9); banner(193, 47, 'gremio', 5);
  spawn('chars/character-male-e', 120, 95, { anim: 'idle', rot: 0.2 });
  spawn('chars/character-female-b', 132, 108, { anim: 'idle', rot: -2 });
  spawn('chars/character-male-c', 198, 50, { anim: 'idle', rot: 1.2 });
}
