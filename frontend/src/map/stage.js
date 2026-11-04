// Renderer, camera, lights, sky dome, sea and the season-phase atmosphere blend.
import * as THREE from 'three';
import { lerp } from './noise.js';

const C = (hex) => new THREE.Color(hex);

export const PHASES = {
  construccion: { top: '#6fa6d6', hor: '#cfe3ee', fog: '#c4d8e2', near: 260, far: 900, sun: '#fff1d6', sunI: 2.8, dir: [0.5, 0.85, 0.35], hs: '#d6e9ff', hg: '#5d5236', hI: 1.1, rift: 0.6, beam: 0, ring: 0, water: '#3f88a8' },
  conflicto: { top: '#3f5d8c', hor: '#f0a46c', fog: '#dea07a', near: 200, far: 760, sun: '#ffb978', sunI: 2.4, dir: [-0.78, 0.36, 0.3], hs: '#ffcfa8', hg: '#4a3b2a', hI: 0.85, rift: 1.1, beam: 0.45, ring: 0, water: '#3b6f8e' },
  convergencia: { top: '#2e2550', hor: '#8d6fb8', fog: '#7a68a6', near: 110, far: 520, sun: '#d4c2ff', sunI: 1.4, dir: [0.2, 0.6, -0.6], hs: '#b7a3ef', hg: '#2f2840', hI: 0.85, rift: 2.2, beam: 0.8, ring: 0, water: '#3b4f7d' },
  colapso: { top: '#05070f', hor: '#1f2440', fog: '#171b30', near: 80, far: 440, sun: '#9fb2e8', sunI: 0.75, dir: [0.3, 0.7, 0.5], hs: '#5865a0', hg: '#14121c', hI: 0.6, rift: 3.2, beam: 1, ring: 1, water: '#1d2a48' },
};

export function createStage(canvas, { reducedMotion }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xc4d8e2, 260, 900);
  const camera = new THREE.PerspectiveCamera(50, 1, 0.3, 4000);
  camera.position.set(140, 330, 430);

  const hemi = new THREE.HemisphereLight(0xd6e9ff, 0x5d5236, 1.1); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff1d6, 2.8);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.near = 1; sun.shadow.camera.far = 700; sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.4;
  scene.add(sun, sun.target);

  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { top: { value: C('#6fa6d6') }, hor: { value: C('#cfe3ee') } },
    vertexShader: 'varying vec3 vW; void main(){ vW=(modelMatrix*vec4(position,1.)).xyz; gl_Position=projectionMatrix*viewMatrix*vec4(vW,1.); }',
    fragmentShader: 'uniform vec3 top; uniform vec3 hor; varying vec3 vW; void main(){ float h=normalize(vW-cameraPosition).y; gl_FragColor=vec4(mix(hor,top,smoothstep(-0.02,0.55,h)),1.); }',
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(3000, 32, 16), skyMat); scene.add(sky);

  const water = new THREE.Mesh(new THREE.PlaneGeometry(6000, 6000).rotateX(-Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x3f88a8, transparent: true, opacity: 0.9, roughness: 0.22, metalness: 0.05 }));
  water.receiveShadow = true; scene.add(water);

  const cur = { top: C('#6fa6d6'), hor: C('#cfe3ee'), fog: C('#c4d8e2'), sun: C('#fff1d6'), hs: C('#d6e9ff'), hg: C('#5d5236'), water: C('#3f88a8'),
    near: 260, far: 900, sunI: 2.8, hI: 1.1, rift: 0.6, beam: 0, ring: 0, dir: new THREE.Vector3(0.5, 0.85, 0.35).normalize() };
  const state = { phase: 'construccion' };
  const _tc = new THREE.Color(), _tv = new THREE.Vector3();

  /** Eases the atmosphere toward the current phase. `lift` pushes the fog out when the camera is high. */
  function updatePhase(dt, lift) {
    const p = PHASES[state.phase], k = reducedMotion ? 1 : 1 - Math.exp(-dt * 2.2);
    for (const n of ['top', 'hor', 'fog', 'sun', 'hs', 'hg', 'water']) cur[n].lerp(_tc.set(p[n]), k);
    for (const n of ['near', 'far', 'sunI', 'hI', 'rift', 'beam', 'ring']) cur[n] = lerp(cur[n], p[n], k);
    cur.dir.lerp(_tv.set(...p.dir).normalize(), k).normalize();
    skyMat.uniforms.top.value.copy(cur.top); skyMat.uniforms.hor.value.copy(cur.hor);
    scene.fog.color.copy(cur.fog); scene.fog.near = cur.near + lift * 0.9; scene.fog.far = cur.far + lift * 1.3;
    sun.color.copy(cur.sun); sun.intensity = cur.sunI; hemi.color.copy(cur.hs); hemi.groundColor.copy(cur.hg); hemi.intensity = cur.hI;
    water.material.color.copy(cur.water);
  }

  return { renderer, scene, camera, sun, sky, cur, state, updatePhase };
}
