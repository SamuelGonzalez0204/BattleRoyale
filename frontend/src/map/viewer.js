// Public entry point: mounts the 3D map of El Valle de la Grieta into a container.
import * as THREE from 'three';
import { clamp, mulberry32 } from './noise.js';
import { PHASE_IDS, VIEW_MODES, normalizeFallen } from './zones.js';
import { buildTerrain, createTerrain } from './terrain.js';
import { buildLayout, createPlacement } from './layout.js';
import { buildInstances, loadAll, neededKeys } from './assets.js';
import { createStage } from './stage.js';
import { createEffects } from './effects.js';
import { createFallenFog } from './fallen.js';
import { createControls } from './controls.js';
import { createUi } from './ui.js';
import { createMinimap } from './minimap.js';
import { renderShell, resolveUi } from './shell.js';

const LAYOUT_SEED = 20261103;
const nextFrame = () => new Promise((r) => setTimeout(r, 20));

/**
 * @typedef {object} MapViewerOptions
 * @property {string} [assetBase='/mapa/']   where map-data.json and kits/ are served
 * @property {Partial<typeof import('./shell.js').DEFAULT_UI>} [ui]  widget switches
 * @property {string} [title] @property {string} [subtitle]
 * @property {'aerial'|'walk'|'fly'} [mode='aerial'] @property {string[]} [modes]  modes offered in the control
 * @property {string} [phase='construccion'] @property {string[]} [fallenZones]
 * @property {boolean} [globalKeys=true]  listen to the keyboard on window (false: only while focus is inside the viewer)
 * @property {(mode: string) => void} [onModeChange] @property {(phase: string) => void} [onPhaseChange]
 */

/**
 * @param {HTMLElement} container
 * @param {MapViewerOptions} [options]
 * @returns {{ ready: Promise<{failedModels: string[]}>, setPhase(p: string): void, setFallenZones(ids: string[]): void,
 *   focusRegion(id: string): void, setMode(m: string): void, dispose(): void }}
 */
export function createMapViewer(container, options = {}) {
  const base = options.assetBase ?? '/mapa/';
  const ui = resolveUi(options.ui);
  const modes = (options.modes ?? VIEW_MODES).filter((m) => VIEW_MODES.includes(m));
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const touch = matchMedia('(pointer: coarse)').matches;
  const root = document.createElement('div'); root.className = 'mv';
  container.appendChild(root);
  const dom = renderShell(root, ui, { title: options.title ?? 'El Valle de la Grieta', subtitle: options.subtitle ?? 'Temporada 1 · La Grieta Despierta', modes });

  const offs = [];
  const listen = (target, type, fn, opts) => { target.addEventListener(type, fn, opts); offs.push(() => target.removeEventListener(type, fn, opts)); };
  const want = { phase: PHASE_IDS.includes(options.phase) ? options.phase : 'construccion', mode: modes.includes(options.mode) ? options.mode : modes[0], fallen: options.fallenZones ?? [], focus: null };
  let disposed = false, live = null;

  const stage = createStage(dom.canvas, { reducedMotion });
  const { renderer, scene, camera, sun, cur } = stage;
  stage.state.phase = want.phase;
  const resize = () => {
    const w = root.clientWidth || 1, h = root.clientHeight || 1;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  };
  const ro = new ResizeObserver(resize); ro.observe(root); resize();

  const pressed = (attr, value) => root.querySelectorAll(`[data-${attr}]`).forEach((b) => b.setAttribute('aria-pressed', String(b.dataset[attr] === value)));
  pressed('phase', want.phase);
  const msg = (t) => { if (dom.loadMsg) dom.loadMsg.textContent = t; };

  async function init() {
    let DATA;
    try {
      const res = await fetch(`${base}map-data.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      DATA = await res.json();
    } catch (e) { msg('No se pudo leer el mapa. Recarga la página.'); throw e; }
    const T = createTerrain(DATA), P = createPlacement(T, DATA);
    msg('Trazando caminos y aldeas…'); await nextFrame();
    buildLayout(P, mulberry32(LAYOUT_SEED));
    msg('Cargando modelos del valle…');
    const keys = neededKeys(P.batches, P.spawns, ['chars/character-male-a']);
    const { gltfs, fails } = await loadAll(base, keys, (done, total) => {
      if (dom.loadBar) dom.loadBar.style.width = `${(done / total) * 100}%`;
      if (dom.loadCount) dom.loadCount.textContent = `${done} / ${total} modelos`;
    }, () => disposed);
    if (disposed) return { failedModels: fails };
    msg('Levantando el terreno…'); await nextFrame();
    if (disposed) return { failedModels: fails };
    live = assemble(DATA, T, P, gltfs);
    if (dom.loader) dom.loader.hidden = true;
    return { failedModels: fails };
  }

  function assemble(DATA, T, P, gltfs) {
    const mixers = [];
    const terrain = buildTerrain(scene, T);
    buildInstances(scene, P.batches, gltfs);
    const effects = createEffects({ scene, T, DATA, gltfs, mixers, P, cur, reducedMotion });
    effects.runSpawns();
    const fog = createFallenFog(scene, T, DATA.regions);
    let uiApi = null;
    const nav = createControls({
      camera, canvas: dom.canvas, scene, T, bridges: P.bridges, listen, touch, reducedMotion,
      keyTarget: options.globalKeys === false ? root : window, joyEl: ui.joystick ? dom.joy : null,
      hooks: {
        onModeChange: (m) => { pressed('mode', m); uiApi?.updateHelp(); options.onModeChange?.(m); },
        onPick: (x, y) => uiApi?.pickAt(x, y), onInteract: () => uiApi?.openNear(), onEscape: () => uiApi?.closeCard(),
      },
    });
    nav.setupWalker(gltfs, mixers);
    uiApi = createUi({ dom, root, scene, camera, canvas: dom.canvas, T, DATA, nav, touch, listen });
    uiApi.buildMarkers(); uiApi.buildPlaceList(); uiApi.updateHelp();
    const minimap = dom.minimap ? createMinimap({ canvas: dom.minimap, coordsEl: dom.coords, T, DATA, listen, nav }) : null;
    minimap?.build();
    const L = { DATA, T, terrain, effects, fog, nav, ui: uiApi, minimap };
    applyFallen(L); nav.setMode(want.mode);
    if (want.focus) focusOn(L, want.focus, true);
    startLoop(L);
    return L;
  }

  function applyFallen(L) {
    const ids = normalizeFallen(want.fallen, L.DATA.regions);
    L.terrain.tintFallen(L.DATA.regions, ids); L.fog.setFallen(ids); L.ui.setFallen(ids); L.minimap?.setFallen(ids);
  }
  function focusOn(L, id, instant = false) {
    const r = L.DATA.regions.find((q) => q.id === id); if (!r) return;
    L.nav.goTo(r.center[0], r.center[1], clamp(r.radius * 2.4, 90, 260), instant);
  }

  const _focus = new THREE.Vector3();
  function updateShadow(nav) {
    const mode = nav.getMode();
    if (mode === 'fly') _focus.copy(camera.position).setY(Math.max(live.T.H(camera.position.x, camera.position.z), 0));
    else _focus.copy(nav.focus());
    const ext = mode === 'aerial' ? clamp(nav.controls.getDistance() * 0.75, 45, 240) : 60;
    const sc = sun.shadow.camera;
    if (Math.abs(sc.right - ext) > 2) { sc.left = -ext; sc.right = ext; sc.top = ext; sc.bottom = -ext; sc.updateProjectionMatrix(); }
    sun.target.position.copy(_focus); sun.position.copy(_focus).addScaledVector(cur.dir, 300);
  }
  function startLoop(L) {
    const clock = new THREE.Clock();
    renderer.setAnimationLoop(() => {
      const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime, mode = L.nav.getMode();
      const dist = L.nav.controls.getDistance();
      stage.updatePhase(dt, mode === 'aerial' ? dist : mode === 'fly' ? Math.max(0, camera.position.y - 20) : 0);
      L.nav.update(dt);
      L.effects.animate(t, dt); L.fog.animate(t); updateShadow(L.nav);
      L.ui.updateNear(); L.ui.updateLabels(dist);
      L.minimap?.draw(cur.ring, L.effects.fx.ring ? L.effects.fx.ring.scale.x : 0);
      stage.sky.position.copy(camera.position);
      renderer.render(scene, camera);
    });
  }

  /* Widget buttons */
  root.querySelectorAll('[data-mode]').forEach((b) => listen(b, 'click', () => api.setMode(b.dataset.mode)));
  root.querySelectorAll('[data-phase]').forEach((b) => listen(b, 'click', () => api.setPhase(b.dataset.phase)));

  const api = {
    ready: init(),
    setPhase(phase) {
      if (!PHASE_IDS.includes(phase)) return;
      want.phase = phase; stage.state.phase = phase; pressed('phase', phase); options.onPhaseChange?.(phase);
    },
    setFallenZones(ids) { want.fallen = Array.isArray(ids) ? [...ids] : []; if (live) applyFallen(live); },
    focusRegion(id) { want.focus = id; if (live) focusOn(live, id); },
    setMode(mode) { if (!modes.includes(mode)) return; want.mode = mode; if (live) live.nav.setMode(mode); else pressed('mode', mode); },
    dispose() {
      if (disposed) return;
      disposed = true;
      renderer.setAnimationLoop(null);
      offs.forEach((off) => off()); ro.disconnect();
      if (live) { live.nav.controls.dispose(); live.fog.dispose(); }
      scene.traverse((o) => {
        o.geometry?.dispose?.();
        const mats = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
        mats.forEach((m) => { m.map?.dispose?.(); m.dispose?.(); });
      });
      renderer.dispose(); root.remove();
    },
  };
  api.ready.catch(() => {});
  return api;
}
