// Model loading (Kenney kits) and GPU instancing of every placed matrix.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import { NO_SHADOW, baseKey, kitScale } from './kits.js';

const pad4 = (n) => (n + 3) & ~3;
const LOAD_CONCURRENCY = 10;

/**
 * Models are published as glTF JSON with the buffer embedded as a base64 data: URI.
 * GLTFLoader would fetch() that data: URI, which a strict CSP (connect-src) blocks — that is
 * what happened in the published artifact — so the buffer is decoded here and a GLB is
 * assembled in memory instead. Keep this loader even where no CSP applies today.
 */
export async function loadModel(loader, base, key) {
  const res = await fetch(`${base}kits/${key}.json`);
  if (!res.ok) throw new Error(`${key}: HTTP ${res.status}`);
  const json = await res.json(), uri = json.buffers[0].uri;
  const raw = atob(uri.slice(uri.indexOf(',') + 1)), bin = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bin[i] = raw.charCodeAt(i);
  delete json.buffers[0].uri;
  const jsonBytes = new TextEncoder().encode(JSON.stringify(json)), jl = pad4(jsonBytes.length), bl = pad4(bin.length);
  const glb = new Uint8Array(12 + 8 + jl + 8 + bl), dv = new DataView(glb.buffer);
  dv.setUint32(0, 0x46546c67, true); dv.setUint32(4, 2, true); dv.setUint32(8, glb.length, true);
  dv.setUint32(12, jl, true); dv.setUint32(16, 0x4e4f534a, true);
  glb.fill(0x20, 20, 20 + jl); glb.set(jsonBytes, 20);
  dv.setUint32(20 + jl, bl, true); dv.setUint32(24 + jl, 0x004e4942, true); glb.set(bin, 28 + jl);
  return loader.parseAsync(glb.buffer, `${base}kits/${key.split('/')[0]}/`);
}

/** Loads every key with a small worker pool. Returns the map of loaded glTFs and the failures. */
export async function loadAll(base, keys, onProgress = () => {}, isCancelled = () => false) {
  const loader = new GLTFLoader(), gltfs = new Map(), fails = [], queue = [...keys];
  let done = 0;
  async function worker() {
    while (queue.length && !isCancelled()) {
      const k = queue.shift();
      try { gltfs.set(k, await loadModel(loader, base, k)); } catch (e) { fails.push(`${k}: ${e.message}`); }
      done++; onProgress(done, keys.length);
    }
  }
  await Promise.all(Array.from({ length: LOAD_CONCURRENCY }, worker));
  return { gltfs, fails };
}

function partsOf(key, gltfs, glowMats) {
  if (key === 'proc/wheat') return [{ g: new THREE.ConeGeometry(0.16, 0.95, 5).translate(0, 0.47, 0), m: new THREE.MeshStandardMaterial({ color: 0xd8b350, roughness: 1, flatShading: true }) }];
  if (key === 'proc/veg') return [{ g: new THREE.IcosahedronGeometry(0.34, 0).translate(0, 0.22, 0), m: new THREE.MeshStandardMaterial({ color: 0x4f8f3a, roughness: 1, flatShading: true }) }];
  const g = gltfs.get(baseKey(key)); if (!g) return [];
  g.scene.updateMatrixWorld(true);
  const out = [];
  g.scene.traverse((o) => {
    if (!o.isMesh) return;
    let m = o.material;
    if (key.endsWith('#glow')) {
      if (!glowMats.has(m)) { const gm = m.clone(); gm.emissive = new THREE.Color(0x9b5cff); gm.emissiveIntensity = 0.6; glowMats.set(m, gm); }
      m = glowMats.get(m);
    }
    out.push({ g: o.geometry.clone().applyMatrix4(o.matrixWorld), m });
  });
  return out;
}

/** One InstancedMesh per (model key, mesh part). */
export function buildInstances(scene, batches, gltfs) {
  const glowMats = new Map();
  for (const [key, mats] of batches) {
    for (const { g, m } of partsOf(key, gltfs, glowMats)) {
      const im = new THREE.InstancedMesh(g, m, mats.length);
      mats.forEach((mm, i) => im.setMatrixAt(i, mm));
      im.castShadow = !NO_SHADOW.has(baseKey(key)); im.receiveShadow = true; im.frustumCulled = false;
      scene.add(im);
    }
  }
}

/** Standalone clone of a model (characters keep their skeleton) with an optional animation mixer. */
export function spawnModel(gltfs, mixers, key, o) {
  const g = gltfs.get(key); if (!g) return null;
  const obj = key.startsWith('chars/') ? SkeletonUtils.clone(g.scene) : g.scene.clone(true);
  obj.traverse((c) => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } });
  obj.scale.setScalar((o.s ?? 1) * kitScale(key));
  if (g.animations?.length && (o.anim || o.walkCircle)) {
    const mixer = new THREE.AnimationMixer(obj); mixers.push(mixer);
    const clip = THREE.AnimationClip.findByName(g.animations, o.walkCircle ? 'walk' : o.anim);
    if (clip) mixer.clipAction(clip).play();
  }
  return obj;
}

/** Every model key the layout needs (procedural keys excluded). */
export function neededKeys(batches, spawns, extra = []) {
  const needed = new Set(extra);
  for (const k of batches.keys()) if (!k.startsWith('proc/')) needed.add(baseKey(k));
  for (const s of spawns) needed.add(s.key);
  return [...needed];
}
