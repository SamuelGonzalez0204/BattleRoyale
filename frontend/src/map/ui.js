// Places list, POI markers and card, proximity hint, floating region labels and the help line.
import * as THREE from 'three';
import { TAU, esc } from './noise.js';

const KIND = { hito: 'hito', lugar: 'lugar', misterio: 'misterio', paso: 'paso disputado' };
const HELP = {
  aerial: 'Arrastra para girar · clic derecho para desplazar · rueda para acercar · WASD mueve la vista',
  walk: 'WASD o flechas para andar · Mayús para correr · arrastra para mirar · E lee el lugar cercano',
  fly: 'WASD para volar · Espacio sube, X baja · Mayús acelera · arrastra para mirar',
};
const NARROW = 760;

function markerTexture(color, kind) {
  const cv = document.createElement('canvas'); cv.width = cv.height = 64; const c = cv.getContext('2d');
  c.translate(32, 32); c.shadowColor = 'rgba(0,0,0,.6)'; c.shadowBlur = 6;
  c.fillStyle = color; c.strokeStyle = '#f4ead2'; c.lineWidth = 4; c.beginPath();
  if (kind === 'paso') { c.rotate(Math.PI / 4); c.rect(-15, -15, 30, 30); }
  else if (kind === 'misterio') { c.moveTo(0, -20); c.lineTo(18, 14); c.lineTo(-18, 14); c.closePath(); }
  else c.arc(0, 0, 17, 0, TAU);
  c.fill(); c.shadowBlur = 0; c.stroke();
  if (kind === 'hito') { c.fillStyle = '#f4ead2'; c.beginPath(); c.arc(0, 0, 5.5, 0, TAU); c.fill(); }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export function createUi({ dom, root, scene, camera, canvas, T, DATA, nav, touch, listen }) {
  const { H } = T;
  const REG = Object.fromEntries(DATA.regions.map((r) => [r.id, r]));
  const FCOL = Object.fromEntries(Object.entries(DATA.factions).map(([k, v]) => [k, v.color]));
  const markers = [], ray = new THREE.Raycaster();
  let openPoi = null, nearPoi = null, fallen = [];

  function buildMarkers() {
    for (const p of DATA.pois) {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: markerTexture(FCOL[p.faction], p.kind), sizeAttenuation: false, depthTest: false, transparent: true }));
      const [x, z] = p.pos; sp.position.set(x, Math.max(H(x, z), 0) + (p.kind === 'hito' ? 11 : 8), z);
      sp.scale.setScalar(0.036); sp.renderOrder = 10; sp.userData.poi = p; scene.add(sp); markers.push(sp);
    }
  }
  function pickAt(cx, cy) {
    if (!dom.card) return;
    const r = canvas.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1), camera);
    const hit = ray.intersectObjects(markers)[0];
    if (hit) openCard(hit.object.userData.poi);
  }
  function markCurrent(id) {
    root.querySelectorAll('.place').forEach((b) => b.setAttribute('aria-current', String(b.dataset.id === id)));
  }
  function openCard(p) {
    if (!dom.card) return;
    openPoi = p; const reg = REG[p.region], f = DATA.factions[p.faction];
    const contested = p.contested ? `<span class="chip"><span class="dot f-${p.contested[0]}"></span><span class="dot f-${p.contested[1]}"></span>Disputado</span>` : '';
    const fallenChip = fallen.includes(p.region) ? '<span class="chip fallen-chip">Zona caída</span>' : '';
    dom.card.innerHTML = `
      <div class="eyebrow">${esc(reg.name)} · ${esc(KIND[p.kind])}</div>
      <h3>${esc(p.name)}</h3>
      <div class="chips">
        <span class="chip"><span class="dot f-${p.faction}"></span>${esc(p.kind === 'paso' ? 'Bandera: ' + f.name : f.name)}</span>
        ${contested}${fallenChip}
        <span class="chip stat">stat · ${esc(reg.stat)}</span>
        <span class="chip stat">rol · ${esc(reg.role)}</span>
      </div>
      <p>${esc(p.text)}</p>
      <div class="seed"><b>Semilla de historia</b>${esc(reg.story)}</div>
      <div class="card-actions"><button type="button" class="btn primary" data-card="go">Ir aquí</button><button type="button" class="btn" data-card="close">Cerrar</button></div>`;
    dom.card.hidden = false;
    dom.card.querySelector('[data-card="go"]').onclick = () => nav.goTo(p.pos[0], p.pos[1]);
    dom.card.querySelector('[data-card="close"]').onclick = closeCard;
    markCurrent(p.id);
  }
  function closeCard() { if (!dom.card) return; dom.card.hidden = true; openPoi = null; markCurrent(null); }

  const togglePlaces = (open) => { dom.places.classList.toggle('open', open); dom.placesToggle.setAttribute('aria-expanded', String(open)); };
  function renderPlaceList() {
    if (!dom.placeList) return;
    const left = DATA.regions.length - fallen.length;
    dom.placeCount.textContent = fallen.length ? `${left} en pie · ${fallen.length} caídas` : `${DATA.regions.length} regiones · ${DATA.pois.length} lugares`;
    dom.placeList.innerHTML = DATA.regions.map((r) => {
      const isFallen = fallen.includes(r.id);
      return `
      <div class="region-group${isFallen ? ' is-fallen' : ''}">
        <button type="button" class="region-name" data-region="${r.id}"><span class="dot f-${r.faction}"></span>${esc(r.name)}${isFallen ? '<span class="badge-fallen">caída</span>' : ''}</button>
        ${DATA.pois.filter((p) => p.region === r.id).map((p) => `
          <button type="button" class="place" data-id="${p.id}"><span class="dot f-${p.faction} ${p.kind === 'paso' ? 'paso' : ''}"></span><span class="nm">${esc(p.name)}</span><span class="kd">${esc(KIND[p.kind])}</span></button>`).join('')}
      </div>`;
    }).join('');
    if (openPoi) markCurrent(openPoi.id);
  }
  function buildPlaceList() {
    if (!dom.placeList) return;
    renderPlaceList();
    listen(dom.placeList, 'click', (e) => {
      const pl = e.target.closest('.place'), rg = e.target.closest('.region-name');
      if (pl) { const p = DATA.pois.find((q) => q.id === pl.dataset.id); openCard(p); nav.goTo(p.pos[0], p.pos[1]); if (root.clientWidth < NARROW) togglePlaces(false); }
      else if (rg) { const r = REG[rg.dataset.region]; nav.goTo(r.center[0], r.center[1]); }
    });
    listen(dom.placesToggle, 'click', () => togglePlaces(!dom.places.classList.contains('open')));
  }

  function updateNear() {
    const mode = nav.getMode();
    let best = null, bd = mode === 'walk' ? 11 : 16;
    if (mode !== 'aerial') {
      const p = nav.focus();
      for (const q of DATA.pois) { const d = Math.hypot(q.pos[0] - p.x, q.pos[1] - p.z); if (d < bd) { bd = d; best = q; } }
    }
    const h = dom.hint; if (!h) { nearPoi = best; return; }
    if (best !== nearPoi) { nearPoi = best; if (best) h.innerHTML = `${esc(best.name)} · ${touch ? 'toca para leer' : 'pulsa <kbd>E</kbd> para leer'}`; }
    h.hidden = !nearPoi || openPoi === nearPoi || !dom.card;
  }
  if (dom.hint) listen(dom.hint, 'click', () => nearPoi && openCard(nearPoi));
  const openNear = () => { if (nearPoi) openCard(nearPoi); };

  /* Region labels */
  const labelEls = dom.labels ? DATA.regions.map((r) => {
    const el = document.createElement('div'); el.className = 'rlabel';
    dom.labels.appendChild(el); return { el, r };
  }) : [];
  function renderLabels() {
    for (const { el, r } of labelEls) {
      const isFallen = fallen.includes(r.id);
      const sub = isFallen ? 'caída' : r.faction === 'neutral' ? 'sin facción' : r.faction === 'disputada' ? 'tierra disputada' : DATA.factions[r.faction].name;
      el.classList.toggle('is-fallen', isFallen);
      el.innerHTML = `${esc(r.name)}<small>${esc(sub)}</small>`;
    }
  }
  renderLabels();
  const _lv = new THREE.Vector3();
  function updateLabels(distance) {
    if (!labelEls.length) return;
    const mode = nav.getMode(), w = root.clientWidth, hgt = root.clientHeight;
    const show = mode === 'aerial' ? distance > 110 : mode === 'fly' && camera.position.y > 70;
    for (const { el, r } of labelEls) {
      if (!show) { el.style.display = 'none'; continue; }
      _lv.set(r.center[0], Math.max(H(r.center[0], r.center[1]), 0) + 18, r.center[1]).project(camera);
      if (_lv.z > 1) { el.style.display = 'none'; continue; }
      el.style.display = ''; el.style.transform = `translate(${((_lv.x + 1) / 2) * w}px, ${((1 - _lv.y) / 2) * hgt}px) translate(-50%,-50%)`;
    }
  }

  function updateHelp() {
    if (!dom.help) return;
    const mode = nav.getMode();
    dom.help.textContent = touch ? (mode === 'aerial' ? 'Arrastra para girar · pellizca para acercar' : 'Joystick para moverte · arrastra para mirar') : HELP[mode];
  }

  function setFallen(ids) {
    fallen = ids;
    renderPlaceList(); renderLabels();
    if (openPoi) openCard(openPoi);
  }

  const openById = (id) => { const p = DATA.pois.find((q) => q.id === id); if (p) openCard(p); };

  return { buildMarkers, buildPlaceList, pickAt, openNear, openById, closeCard, updateNear, updateLabels, updateHelp, setFallen };
}
