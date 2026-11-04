// Fallen zones of La Última Luz: a low dark-violet fog volume over each fallen region.
import * as THREE from 'three';
import { TAU, mulberry32 } from './noise.js';
import { regionOwnerAt } from './zones.js';

const PUFFS_PER_REGION = 420;
const FOG_HEIGHT = 14;

function puffTexture() {
  const cv = document.createElement('canvas'); cv.width = cv.height = 64;
  const c = cv.getContext('2d'), g = c.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.5, 'rgba(255,255,255,.45)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  c.fillStyle = g; c.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(cv);
}
const seedOf = (id) => [...id].reduce((h, ch) => (Math.imul(h, 31) + ch.charCodeAt(0)) | 0, 7);

export function createFallenFog(scene, T, regions) {
  const texture = puffTexture();
  const material = new THREE.PointsMaterial({
    map: texture, color: 0x3a1a5c, size: 22, sizeAttenuation: true, transparent: true, opacity: 0.55,
    depthWrite: false, fog: false,
  });
  const glowMat = new THREE.PointsMaterial({
    map: texture, color: 0x8a4ddb, size: 9, sizeAttenuation: true, transparent: true, opacity: 0.5,
    depthWrite: false, blending: THREE.AdditiveBlending, fog: false,
  });
  const group = new THREE.Group(); group.renderOrder = 5; scene.add(group);
  const volumes = [];

  function buildVolume(region) {
    const rng = mulberry32(seedOf(region.id)), pts = [], base = [];
    for (let t = 0; t < PUFFS_PER_REGION * 4 && pts.length / 3 < PUFFS_PER_REGION; t++) {
      const a = rng() * TAU, d = Math.sqrt(rng()) * region.radius, x = region.center[0] + Math.cos(a) * d, z = region.center[1] + Math.sin(a) * d;
      if (regionOwnerAt(regions, x, z) !== region.id) continue;
      const y = Math.max(T.H(x, z), 0) + 1 + rng() * rng() * FOG_HEIGHT;
      pts.push(x, y, z); base.push(rng() * TAU);
    }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const fog = new THREE.Points(geo, material), glow = new THREE.Points(geo, glowMat);
    fog.frustumCulled = false; glow.frustumCulled = false;
    return { id: region.id, fog, glow, geo, y0: Float32Array.from(pts.filter((_, i) => i % 3 === 1)), ph: base };
  }

  function setFallen(ids) {
    for (const v of volumes) { group.remove(v.fog, v.glow); v.geo.dispose(); }
    volumes.length = 0;
    for (const id of ids) {
      const r = regions.find((q) => q.id === id); if (!r) continue;
      const v = buildVolume(r); group.add(v.fog, v.glow); volumes.push(v);
    }
  }

  function animate(t) {
    for (const v of volumes) {
      const p = v.geo.attributes.position;
      for (let i = 0; i < p.count; i++) p.setY(i, v.y0[i] + Math.sin(t * 0.35 + v.ph[i]) * 1.2);
      p.needsUpdate = true;
    }
    glowMat.opacity = 0.38 + Math.sin(t * 0.8) * 0.12;
  }

  function dispose() { setFallen([]); material.dispose(); glowMat.dispose(); texture.dispose(); scene.remove(group); }
  return { setFallen, animate, dispose };
}
