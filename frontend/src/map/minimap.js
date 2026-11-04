// Shaded minimap with roads, rift, POIs, fallen zones, the closing ring and the camera wedge.
import * as THREE from 'three';
import { TAU, clamp } from './noise.js';
import { regionOwnerAt } from './zones.js';

const EXT = 260;

export function createMinimap({ canvas, coordsEl, T, DATA, listen, nav }) {
  const ctx = canvas.getContext('2d'), MW = canvas.width;
  const FCOL = Object.fromEntries(Object.entries(DATA.factions).map(([k, v]) => [k, v.color]));
  const toMini = (x, z) => [((x + EXT) / (2 * EXT)) * MW, ((z + EXT) / (2 * EXT)) * MW];
  const toWorld = (u, v) => [(u / MW) * 2 * EXT - EXT, (v / MW) * 2 * EXT - EXT];
  let base = null, fallenLayer = null;
  const _c = new THREE.Color();

  function stroke(o, pts) { o.beginPath(); pts.forEach(([x, z], i) => { const [u, v] = toMini(x, z); if (i) o.lineTo(u, v); else o.moveTo(u, v); }); o.stroke(); }

  function build() {
    const img = ctx.createImageData(MW, MW), { H } = T;
    for (let j = 0; j < MW; j++) for (let i = 0; i < MW; i++) {
      const [x, z] = toWorld(i, j), h = H(x, z), k = (j * MW + i) * 4;
      let c;
      if (h < 0) { const d = clamp(-h / 5, 0, 1); c = _c.setRGB(0.18 - d * 0.06, 0.38 - d * 0.1, 0.48 - d * 0.08); }
      else { const hx = H(x + 1.2, z) - h, hz = H(x, z + 1.2) - h, shade = clamp(1 - (hx + hz) * 0.25, 0.7, 1.2); c = T.groundColor(x, z, h, 1 / Math.sqrt(1 + hx * hx + hz * hz)).multiplyScalar(shade); }
      img.data[k] = c.r * 255; img.data[k + 1] = c.g * 255; img.data[k + 2] = c.b * 255; img.data[k + 3] = 255;
    }
    const off = document.createElement('canvas'); off.width = off.height = MW; const o = off.getContext('2d'); o.putImageData(img, 0, 0);
    o.strokeStyle = 'rgba(160,128,88,.95)'; o.lineWidth = 2.4;
    for (const r of DATA.roads) stroke(o, r);
    o.strokeStyle = 'rgba(192,140,255,.95)'; o.lineWidth = 5; stroke(o, DATA.rift);
    base = off;
  }

  /** Region names are drawn after the fallen layer so a fallen name stays readable (and dimmed). */
  function drawNames(o, fallen) {
    o.font = '700 21px "Alegreya Sans", sans-serif'; o.textAlign = 'center'; o.lineWidth = 5; o.strokeStyle = 'rgba(10,14,20,.85)';
    for (const r of DATA.regions) {
      const [u, v] = toMini(r.center[0], r.center[1] - (r.id === 'plaza' ? 20 : 0));
      o.fillStyle = fallen.includes(r.id) ? 'rgba(214,190,240,.7)' : '#f2e8d2';
      o.strokeText(r.name, u, v); o.fillText(r.name, u, v);
    }
  }

  function setFallen(fallen) {
    const off = document.createElement('canvas'); off.width = off.height = MW; const o = off.getContext('2d');
    if (fallen.length) {
      const img = o.createImageData(MW, MW);
      for (let j = 0; j < MW; j += 1) for (let i = 0; i < MW; i += 1) {
        const [x, z] = toWorld(i, j), owner = regionOwnerAt(DATA.regions, x, z);
        if (!owner || !fallen.includes(owner)) continue;
        const k = (j * MW + i) * 4, hatch = (i + j) % 14 < 3;
        img.data[k] = hatch ? 150 : 34; img.data[k + 1] = hatch ? 90 : 14; img.data[k + 2] = hatch ? 220 : 56; img.data[k + 3] = hatch ? 200 : 165;
      }
      o.putImageData(img, 0, 0);
    }
    drawNames(o, fallen);
    fallenLayer = off;
  }

  function draw(ringK, ringScale) {
    if (!base) return;
    ctx.drawImage(base, 0, 0);
    if (fallenLayer) ctx.drawImage(fallenLayer, 0, 0);
    for (const p of DATA.pois) {
      const [u, v] = toMini(...p.pos); ctx.fillStyle = FCOL[p.faction]; ctx.strokeStyle = '#111'; ctx.lineWidth = 2.5; ctx.beginPath();
      if (p.kind === 'paso') ctx.rect(u - 6, v - 6, 12, 12); else ctx.arc(u, v, 6, 0, TAU);
      ctx.fill(); ctx.stroke();
    }
    if (ringK > 0.02) { const [u, v] = toMini(0, -196); ctx.strokeStyle = `rgba(255,232,160,${ringK})`; ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(u, v, (ringScale / (2 * EXT)) * MW, 0, TAU); ctx.stroke(); }
    const p = nav.focus(), yaw = nav.yaw(), [u, v] = toMini(p.x, p.z);
    ctx.save(); ctx.translate(u, v); ctx.rotate(-yaw + Math.PI);
    ctx.fillStyle = 'rgba(210,173,102,.28)'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 60, -Math.PI / 2 - 0.5, -Math.PI / 2 + 0.5); ctx.closePath(); ctx.fill();
    ctx.scale(1.7, 1.7);
    ctx.fillStyle = '#d2ad66'; ctx.strokeStyle = '#111'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(0, -11); ctx.lineTo(8, 8); ctx.lineTo(0, 3); ctx.lineTo(-8, 8); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.restore();
    if (coordsEl) coordsEl.textContent = `x ${Math.round(p.x)} · z ${Math.round(p.z)}`;
  }

  listen(canvas, 'click', (e) => {
    const r = canvas.getBoundingClientRect();
    nav.goTo(((e.clientX - r.left) / r.width) * 2 * EXT - EXT, ((e.clientY - r.top) / r.height) * 2 * EXT - EXT);
  });

  return { build, setFallen, draw };
}
