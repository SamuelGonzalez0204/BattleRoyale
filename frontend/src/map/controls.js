// Camera modes (aerial orbit, third-person walk, free fly), keyboard/pointer input and the touch joystick.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { clamp, distPoly, lerp } from './noise.js';
import { WORLD } from './terrain.js';
import { spawnModel } from './assets.js';

const FORM_FIELD = 'input, textarea, select, [contenteditable="true"]';

/**
 * @param {object} c
 * @param {(target: EventTarget, type: string, fn: Function, opts?: object) => void} c.listen  registers a listener removed on dispose
 */
export function createControls(c) {
  const { camera, canvas, scene, T, bridges, listen, touch, reducedMotion, keyTarget, joyEl, hooks } = c;
  const { H } = T;
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true; controls.screenSpacePanning = false; controls.maxPolarAngle = 1.32;
  controls.minDistance = 10; controls.maxDistance = 700; controls.target.set(0, 4, 10);
  const st = { mode: 'aerial', tween: null };
  const keys = new Set(), joy = { x: 0, y: 0 };
  const walker = { obj: null, pos: new THREE.Vector3(0, 4, 26), heading: Math.PI, yaw: 0, pitch: 0.32, dist: 7.5, anim: 'idle', actions: {} };
  const flyer = { yaw: 0, pitch: 0.35 };

  function groundY(x, z) {
    let y = H(x, z);
    for (const b of bridges) { if (distPoly([b.a, b.b], x, z).d < b.w) y = Math.max(y, b.y); }
    return y;
  }
  function setupWalker(gltfs, mixers) {
    const g = gltfs.get('chars/character-male-a'); const obj = spawnModel(gltfs, [], 'chars/character-male-a', {}); if (!obj) return;
    scene.add(obj); walker.obj = obj;
    const mixer = new THREE.AnimationMixer(obj); mixers.push(mixer);
    for (const n of ['idle', 'walk', 'sprint']) { const clip = THREE.AnimationClip.findByName(g.animations, n); if (clip) walker.actions[n] = mixer.clipAction(clip); }
    walker.actions.idle?.play();
    obj.visible = st.mode === 'walk';
  }
  function setAnim(name) {
    if (walker.anim === name || !walker.actions[name]) return;
    const prev = walker.actions[walker.anim], next = walker.actions[name];
    next.reset().play(); prev?.crossFadeTo(next, 0.2, false); walker.anim = name;
  }
  function placeWalker(x, z) {
    let px = x, pz = z;
    const a = Math.atan2(-z, -x);
    for (let r = 0; r < 120 && H(px, pz) < 0.5; r += 2) { px = x + Math.cos(a) * r; pz = z + Math.sin(a) * r; }
    if (H(px, pz) < 0.5) { px = 0; pz = 26; }
    walker.pos.set(px, groundY(px, pz), pz);
  }
  function setMode(m) {
    if (m === st.mode) return;
    const prev = st.mode; st.mode = m; st.tween = null;
    controls.enabled = m === 'aerial';
    if (walker.obj) walker.obj.visible = m === 'walk';
    if (m === 'walk') {
      const src = prev === 'aerial' ? controls.target : camera.position;
      placeWalker(src.x, src.z);
      walker.yaw = Math.atan2(camera.position.x - walker.pos.x, camera.position.z - walker.pos.z);
    } else if (m === 'fly') {
      const d = new THREE.Vector3(); camera.getWorldDirection(d);
      flyer.yaw = Math.atan2(-d.x, -d.z); flyer.pitch = clamp(-Math.asin(d.y), -1.4, 1.4);
      if (prev === 'walk') camera.position.y += 6;
    } else {
      const t = prev === 'walk' ? walker.pos : camera.position.clone().add(new THREE.Vector3(-Math.sin(flyer.yaw) * 40, 0, -Math.cos(flyer.yaw) * 40));
      controls.target.set(clamp(t.x, -WORLD, WORLD), Math.max(groundY(t.x, t.z), 0), clamp(t.z, -WORLD, WORLD));
      camera.position.copy(controls.target).add(new THREE.Vector3(0, 60, 72));
    }
    if (joyEl) joyEl.hidden = !(touch && m !== 'aerial');
    hooks.onModeChange(m);
  }
  function moveInput() {
    let ix = joy.x, iy = joy.y;
    if (keys.has('KeyW') || keys.has('ArrowUp')) iy += 1;
    if (keys.has('KeyS') || keys.has('ArrowDown')) iy -= 1;
    if (keys.has('KeyD') || keys.has('ArrowRight')) ix += 1;
    if (keys.has('KeyA') || keys.has('ArrowLeft')) ix -= 1;
    const l = Math.hypot(ix, iy); if (l > 1) { ix /= l; iy /= l; }
    return { ix, iy, run: keys.has('ShiftLeft') || keys.has('ShiftRight') || Math.hypot(joy.x, joy.y) > 0.92 };
  }
  function updateWalk(dt) {
    if (!walker.obj) return;
    const { ix, iy, run } = moveInput(), fx = -Math.sin(walker.yaw), fz = -Math.cos(walker.yaw), rx = Math.cos(walker.yaw), rz = -Math.sin(walker.yaw);
    const mx = fx * iy + rx * ix, mz = fz * iy + rz * ix, moving = Math.hypot(mx, mz) > 0.05;
    if (moving) {
      const sp = (run ? 13 : 5.5) * dt, nx = walker.pos.x + mx * sp, nz = walker.pos.z + mz * sp;
      if (groundY(nx, nz) > -0.6 && Math.hypot(nx, nz) < 270) { walker.pos.x = nx; walker.pos.z = nz; }
      const target = Math.atan2(mx, mz), diff = Math.atan2(Math.sin(target - walker.heading), Math.cos(target - walker.heading));
      walker.heading += diff * Math.min(1, dt * 12);
    }
    setAnim(moving ? (run ? 'sprint' : 'walk') : 'idle');
    walker.pos.y = lerp(walker.pos.y, Math.max(groundY(walker.pos.x, walker.pos.z), -0.35), Math.min(1, dt * 14));
    walker.obj.position.copy(walker.pos); walker.obj.rotation.y = walker.heading;
    const cp = Math.cos(walker.pitch), off = new THREE.Vector3(Math.sin(walker.yaw) * cp, Math.sin(walker.pitch), Math.cos(walker.yaw) * cp).multiplyScalar(walker.dist);
    const want = walker.pos.clone().add(off).add(new THREE.Vector3(0, 1.1, 0));
    want.y = Math.max(want.y, H(want.x, want.z) + 0.7, 0.5);
    camera.position.lerp(want, Math.min(1, dt * 10));
    camera.lookAt(walker.pos.x, walker.pos.y + 1.0, walker.pos.z);
  }
  function updateFly(dt) {
    const { ix, iy, run } = moveInput(), sp = (run ? 80 : 26) * dt, cp = Math.cos(flyer.pitch);
    const dir = new THREE.Vector3(-Math.sin(flyer.yaw) * cp, -Math.sin(flyer.pitch), -Math.cos(flyer.yaw) * cp);
    const right = new THREE.Vector3(Math.cos(flyer.yaw), 0, -Math.sin(flyer.yaw));
    camera.position.addScaledVector(dir, iy * sp).addScaledVector(right, ix * sp);
    if (keys.has('Space')) camera.position.y += sp;
    if (keys.has('KeyX') || keys.has('KeyC')) camera.position.y -= sp;
    camera.position.x = clamp(camera.position.x, -WORLD - 20, WORLD + 20); camera.position.z = clamp(camera.position.z, -WORLD - 20, WORLD + 20);
    camera.position.y = clamp(camera.position.y, Math.max(H(camera.position.x, camera.position.z), 0) + 1.5, 450);
    camera.lookAt(camera.position.clone().add(dir));
  }
  function updateAerial(dt) {
    const { ix, iy, run } = moveInput();
    if (ix || iy) {
      const d = new THREE.Vector3(); camera.getWorldDirection(d); d.y = 0; d.normalize();
      const r = new THREE.Vector3(-d.z, 0, d.x), sp = (run ? 120 : 55) * dt * (controls.getDistance() / 120 + 0.3);
      const delta = d.multiplyScalar(iy * sp).add(r.multiplyScalar(ix * sp));
      controls.target.add(delta); camera.position.add(delta);
    }
    controls.target.x = clamp(controls.target.x, -WORLD, WORLD); controls.target.z = clamp(controls.target.z, -WORLD, WORLD);
    if (!st.tween) controls.target.y = lerp(controls.target.y, Math.max(groundY(controls.target.x, controls.target.z), 0), Math.min(1, dt * 4));
    controls.update();
  }
  /** Moves the view to a world point. In aerial mode `dist` overrides the default 34..80 framing; `instant` skips the glide. */
  function goTo(x, z, dist, instant = false) {
    if (st.mode === 'walk') { placeWalker(x, z + 6); walker.yaw = Math.atan2(walker.pos.x - x, walker.pos.z - z); return; }
    if (st.mode === 'fly') { camera.position.set(x, Math.max(H(x, z), 0) + 24, z + 34); flyer.yaw = 0; flyer.pitch = 0.6; return; }
    const t1 = new THREE.Vector3(x, Math.max(groundY(x, z), 0), z), d = dist ?? clamp(controls.getDistance(), 34, 80);
    const off = camera.position.clone().sub(controls.target).normalize().multiplyScalar(d);
    st.tween = { t: 0, dur: reducedMotion || instant ? 0.001 : 1.2, t0: controls.target.clone(), t1, c0: camera.position.clone(), c1: t1.clone().add(off) };
  }
  function updateTween(dt) {
    const tw = st.tween; if (!tw) return;
    tw.t = Math.min(1, tw.t + dt / tw.dur); const e = tw.t < 0.5 ? 4 * tw.t ** 3 : 1 - (-2 * tw.t + 2) ** 3 / 2;
    controls.target.lerpVectors(tw.t0, tw.t1, e); camera.position.lerpVectors(tw.c0, tw.c1, e);
    if (tw.t >= 1) st.tween = null;
  }
  function update(dt) {
    updateTween(dt);
    if (st.mode === 'aerial') updateAerial(dt); else if (st.mode === 'walk') updateWalk(dt); else updateFly(dt);
  }

  /* Input */
  let drag = null;
  listen(canvas, 'pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, id: e.pointerId }; st.tween = null; if (st.mode !== 'aerial') canvas.setPointerCapture(e.pointerId); });
  listen(canvas, 'pointermove', (e) => {
    if (!drag || drag.id !== e.pointerId || st.mode === 'aerial') return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
    if (st.mode === 'walk') { walker.yaw -= dx * 0.006; walker.pitch = clamp(walker.pitch + dy * 0.004, -0.05, 1.25); }
    else { flyer.yaw -= dx * 0.005; flyer.pitch = clamp(flyer.pitch + dy * 0.004, -1.4, 1.4); }
  });
  listen(canvas, 'pointerup', (e) => {
    if (drag && Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) < 6) hooks.onPick(e.clientX, e.clientY);
    drag = null;
  });
  listen(canvas, 'wheel', (e) => { if (st.mode === 'walk') { walker.dist = clamp(walker.dist + e.deltaY * 0.01, 3, 18); e.preventDefault(); } }, { passive: false });
  listen(keyTarget, 'keydown', (e) => {
    if (e.target instanceof Element && e.target.closest(FORM_FIELD)) return;
    if (e.target instanceof Element && e.target.closest('button') && (e.code === 'Space' || e.code === 'Enter')) return;
    keys.add(e.code);
    if (e.code === 'Digit1') setMode('aerial');
    if (e.code === 'Digit2') setMode('walk');
    if (e.code === 'Digit3') setMode('fly');
    if (e.code === 'KeyE') hooks.onInteract();
    if (e.code === 'Escape') hooks.onEscape();
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
  });
  listen(keyTarget, 'keyup', (e) => keys.delete(e.code));
  listen(window, 'blur', () => keys.clear());
  if (keyTarget !== window) listen(keyTarget, 'focusout', (e) => { if (!keyTarget.contains(e.relatedTarget)) keys.clear(); });

  if (joyEl) {
    const knob = joyEl.querySelector('.knob'); let id = null;
    const set = (e) => {
      const r = joyEl.getBoundingClientRect(), dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2), R = r.width / 2, l = Math.min(1, Math.hypot(dx, dy) / R), a = Math.atan2(dy, dx);
      joy.x = Math.cos(a) * l; joy.y = -Math.sin(a) * l; knob.style.transform = `translate(${joy.x * R * 0.6}px, ${-joy.y * R * 0.6}px)`;
    };
    listen(joyEl, 'pointerdown', (e) => { id = e.pointerId; joyEl.setPointerCapture(id); set(e); });
    listen(joyEl, 'pointermove', (e) => { if (e.pointerId === id) set(e); });
    const end = () => { id = null; joy.x = 0; joy.y = 0; knob.style.transform = ''; };
    listen(joyEl, 'pointerup', end); listen(joyEl, 'pointercancel', end);
  }

  /** Point the camera is about (for shadows, minimap, labels). */
  const focus = () => (st.mode === 'walk' ? walker.pos : st.mode === 'fly' ? camera.position : controls.target);
  const yaw = () => (st.mode === 'walk' ? walker.yaw : st.mode === 'fly' ? flyer.yaw : Math.atan2(camera.position.x - controls.target.x, camera.position.z - controls.target.z));

  return { controls, st, walker, setupWalker, setMode, goTo, update, focus, yaw, getMode: () => st.mode };
}
