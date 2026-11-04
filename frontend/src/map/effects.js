// Living objects: spawned models, banners, the plaza board, lighthouse beam, campfire, the rift glow and the closing ring.
import * as THREE from 'three';
import { TAU, clamp, lerp } from './noise.js';
import { kitScale } from './kits.js';
import { spawnModel } from './assets.js';

const ADDITIVE = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false };
const UV_VERT = 'varying vec2 vU; void main(){ vU=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }';

export function createEffects({ scene, T, DATA, gltfs, mixers, P, cur, reducedMotion }) {
  const { H } = T;
  const FCOL = Object.fromEntries(Object.entries(DATA.factions).map(([k, v]) => [k, v.color]));
  const animated = [], riftLights = [];
  const fx = { fireLight: null, beamPivot: null, ring: null, riftRibbon: null, riftParticles: null };

  const poleMat = new THREE.MeshStandardMaterial({ color: 0x5a4330, roughness: 0.9 });
  function makeBanner({ x, z, faction, h }) {
    const g = new THREE.Group(), y = H(x, z);
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, h, 6), poleMat); pole.position.y = h / 2; pole.castShadow = true;
    const cloth = new THREE.Mesh(new THREE.PlaneGeometry(1.3, 2.1, 6, 1).translate(0.65, 0, 0),
      new THREE.MeshStandardMaterial({ color: FCOL[faction], side: THREE.DoubleSide, roughness: 0.8 }));
    cloth.position.set(0.08, h - 1.25, 0); cloth.castShadow = true;
    g.add(pole, cloth); g.position.set(x, y - 0.1, z); scene.add(g);
    animated.push({ type: 'flag', obj: cloth, ph: Math.random() * TAU });
  }
  function makeBoard(x, z, rot) {
    const g = new THREE.Group(), cv = document.createElement('canvas'); cv.width = 256; cv.height = 160;
    const c = cv.getContext('2d'); c.fillStyle = '#e8d9b4'; c.fillRect(0, 0, 256, 160);
    c.fillStyle = '#3a2a18'; c.font = 'bold 22px Georgia'; c.textAlign = 'center'; c.fillText('DECISIÓN DEL DÍA', 128, 38);
    c.fillRect(30, 52, 196, 2); c.font = '15px Georgia';
    ['¿Abrir la Puerta del Norte', 'a los mercaderes del Gremio?', '', 'SÍ ▮▮▮▮▮▮▯   NO ▮▮▮▮▯▯▯'].forEach((t, i) => c.fillText(t, 128, 80 + i * 20));
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const wood = new THREE.MeshStandardMaterial({ color: 0x6b4b2e, roughness: 0.9 });
    const board = new THREE.Mesh(new THREE.BoxGeometry(3.2, 2, 0.16), [wood, wood, wood, wood, new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9 }), wood]);
    board.position.y = 2.3; board.castShadow = true;
    for (const px of [-1.4, 1.4]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.18, 3.3, 0.18), wood); p.position.set(px, 1.65, -0.1); p.castShadow = true; g.add(p); }
    g.add(board); g.position.set(x, H(x, z), z); g.rotation.y = rot; scene.add(g);
  }
  function makeBeam(x, z) {
    const top = H(x, z) + 10.22 * kitScale('pirate/tower-complete-large') - 1.6;
    const pivot = new THREE.Group(); pivot.position.set(x, top, z);
    const mat = new THREE.MeshBasicMaterial({ color: 0xffe7a0, opacity: 0, ...ADDITIVE });
    for (const dir of [0, Math.PI]) {
      const cone = new THREE.Mesh(new THREE.ConeGeometry(7, 70, 24, 1, true), mat);
      cone.rotation.z = Math.PI / 2; cone.position.x = 35; const arm = new THREE.Group(); arm.rotation.y = dir; arm.add(cone); pivot.add(arm);
    }
    pivot.userData.mat = mat;
    const lamp = new THREE.PointLight(0xffe2a0, 0, 60, 1.6); pivot.add(lamp); pivot.userData.lamp = lamp;
    scene.add(pivot); fx.beamPivot = pivot;
  }
  function makeFire(x, z) {
    fx.fireLight = new THREE.PointLight(0xffa046, 30, 24, 1.6); fx.fireLight.position.set(x, H(x, z) + 1.4, z); scene.add(fx.fireLight);
  }
  function riftSampler() {
    const segs = []; let total = 0;
    for (let i = 0; i < DATA.rift.length - 1; i++) { const L = Math.hypot(DATA.rift[i + 1][0] - DATA.rift[i][0], DATA.rift[i + 1][1] - DATA.rift[i][1]); segs.push(L); total += L; }
    const at = (s) => {
      let acc = 0;
      for (let i = 0; i < segs.length; i++) {
        if (s <= acc + segs[i] || i === segs.length - 1) { const t = (s - acc) / segs[i], a = DATA.rift[i], b = DATA.rift[i + 1]; return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), (b[1] - a[1]) / segs[i], -(b[0] - a[0]) / segs[i]]; }
        acc += segs[i];
      }
      return null;
    };
    return { at, total };
  }
  function makeRift() {
    const { at, total } = riftSampler(), N = 260, pos = [], uv = [], idx = [];
    for (let i = 0; i <= N; i++) {
      const [x, z, nx, nz] = at((i / N) * total), w = T.riftInfo(x, z).w * 0.9 + 0.05;
      pos.push(x + nx * w, -2.8, z + nz * w, x - nx * w, -2.8, z - nz * w); uv.push(i / N, 0, i / N, 1);
      if (i < N) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
    fx.riftRibbon = new THREE.Mesh(g, new THREE.ShaderMaterial({
      ...ADDITIVE, uniforms: { t: { value: 0 }, k: { value: 0.6 } }, vertexShader: UV_VERT,
      fragmentShader: 'uniform float t; uniform float k; varying vec2 vU; void main(){ float c=1.-abs(vU.y-.5)*2.; float p=.6+.4*sin(vU.x*90.-t*2.); gl_FragColor=vec4(vec3(.62,.36,1.), c*p*k); }',
    }));
    scene.add(fx.riftRibbon);
    const M = 1100, pp = new Float32Array(M * 3), seeds = new Float32Array(M);
    for (let i = 0; i < M; i++) { const [x, z] = at(Math.random() * total); pp[i * 3] = x + (Math.random() - 0.5) * 6; pp[i * 3 + 1] = -3 + Math.random() * 11; pp[i * 3 + 2] = z + (Math.random() - 0.5) * 6; seeds[i] = Math.random(); }
    const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pp, 3));
    fx.riftParticles = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0xc69bff, size: 0.36, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false }));
    fx.riftParticles.userData.seeds = seeds; scene.add(fx.riftParticles);
    for (const s of [0.15, 0.4, 0.65, 0.88]) { const [x, z] = at(s * total); const l = new THREE.PointLight(0xa06bdb, 30, 40, 1.4); l.position.set(x, 1.5, z); scene.add(l); riftLights.push(l); }
  }
  function makeRing() {
    fx.ring = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 200, 1, true), new THREE.ShaderMaterial({
      ...ADDITIVE, uniforms: { k: { value: 0 } }, vertexShader: UV_VERT,
      fragmentShader: 'uniform float k; varying vec2 vU; void main(){ float a=pow(1.-vU.y,1.6)*.9*k; gl_FragColor=vec4(vec3(1.,.88,.55), a); }',
    }));
    fx.ring.position.set(0, 40, -196); fx.ring.visible = false; scene.add(fx.ring);
  }

  function runSpawns() {
    for (const sp of P.spawns) {
      const obj = spawnModel(gltfs, mixers, sp.key, sp.o); if (!obj) continue;
      const y = sp.o.y ?? H(sp.x, sp.z);
      obj.position.set(sp.x, y, sp.z); obj.rotation.y = sp.o.rot ?? 0;
      if (sp.o.ghost) obj.traverse((c) => { if (c.isMesh) { c.material = c.material.clone(); c.material.transparent = true; c.material.opacity = 0.72; c.material.emissive = new THREE.Color(0x8fd6c8); c.material.emissiveIntensity = 0.35; c.castShadow = false; } });
      if (sp.o.spinX) {
        const pivot = new THREE.Group(); pivot.position.copy(obj.position); pivot.rotation.y = sp.o.rot ?? 0;
        obj.position.set(0, 0, 0); obj.rotation.set(0, 0, 0); pivot.add(obj); scene.add(pivot);
        animated.push({ type: 'spin', obj, speed: sp.o.spinX }); continue;
      }
      scene.add(obj);
      if (sp.o.bob) animated.push({ type: 'bob', obj, y, amp: sp.o.bob, ph: Math.random() * TAU });
      if (sp.o.drift !== undefined) animated.push({ type: 'drift', obj, cx: sp.x, cz: sp.z, ph: sp.o.drift });
      if (sp.o.walkCircle) animated.push({ type: 'circle', obj, ...sp.o.walkCircle, ph: Math.atan2(sp.z, sp.x) });
    }
    for (const b of P.banners) makeBanner(b);
    for (const e of P.extras) {
      if (e.type === 'board') makeBoard(e.x, e.z, e.rot);
      else if (e.type === 'beam') makeBeam(e.x, e.z);
      else if (e.type === 'fire') makeFire(e.x, e.z);
    }
    makeRift(); makeRing();
  }

  function animateObject(a, t, dt) {
    if (a.type === 'spin') a.obj.rotation.x += a.speed * dt * (reducedMotion ? 0.3 : 1);
    else if (a.type === 'bob') { a.obj.position.y = a.y + Math.sin(t * 0.8 + a.ph) * 0.12 * a.amp; a.obj.rotation.z = Math.sin(t * 0.6 + a.ph) * 0.025 * a.amp; }
    else if (a.type === 'flag') a.obj.rotation.y = Math.sin(t * 1.7 + a.ph) * 0.35;
    else if (a.type === 'drift') {
      const ang = t * 0.12 + a.ph, x = a.cx + Math.cos(ang) * 3, z = a.cz + Math.sin(ang) * 3;
      a.obj.position.set(x, H(x, z) + 1.2 + Math.sin(t * 1.3 + a.ph) * 0.35, z); a.obj.rotation.y = -ang;
    } else if (a.type === 'circle') {
      const ang = a.ph + t * a.speed, x = a.cx + Math.cos(ang) * a.r, z = a.cz + Math.sin(ang) * a.r, sg = Math.sign(a.speed);
      a.obj.position.set(x, H(x, z) + 0.05, z); a.obj.rotation.y = Math.atan2(-Math.sin(ang) * sg, Math.cos(ang) * sg);
    }
  }
  function animate(t, dt) {
    for (const a of animated) animateObject(a, t, dt);
    for (const m of mixers) m.update(dt);
    const { riftRibbon, riftParticles, fireLight, beamPivot, ring } = fx;
    if (riftRibbon) { riftRibbon.material.uniforms.t.value = t; riftRibbon.material.uniforms.k.value = cur.rift * 0.7; }
    riftLights.forEach((l, i) => { l.intensity = 26 * cur.rift * (0.8 + 0.2 * Math.sin(t * 2 + i)); });
    if (riftParticles) {
      const p = riftParticles.geometry.attributes.position, sd = riftParticles.userData.seeds, rise = dt * (0.8 + cur.rift);
      for (let i = 0; i < p.count; i++) { let y = p.getY(i) + rise * (0.5 + sd[i]); if (y > 4 + cur.rift * 3) y = -3; p.setY(i, y); }
      p.needsUpdate = true; riftParticles.material.opacity = clamp(0.25 + cur.rift * 0.3, 0, 1);
    }
    if (fireLight) fireLight.intensity = 26 + Math.sin(t * 9) * 4 + Math.sin(t * 23) * 3;
    if (beamPivot) { beamPivot.rotation.y = t * 0.45; beamPivot.userData.mat.opacity = 0.11 * cur.beam; beamPivot.userData.lamp.intensity = 80 * cur.beam; }
    if (ring) { ring.visible = cur.ring > 0.02; const cyc = (t % 30) / 30, R = lerp(340, 22, 1 - (1 - cyc) ** 2); ring.scale.set(R, 120, R); ring.material.uniforms.k.value = cur.ring; }
  }

  return { runSpawns, animate, fx };
}
