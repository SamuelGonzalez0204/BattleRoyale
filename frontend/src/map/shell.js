// DOM skeleton of the viewer. Every widget can be switched off through `options.ui`.
import { esc } from './noise.js';

export const DEFAULT_UI = {
  brand: true, modeControl: true, phaseControl: true, places: true, card: true,
  minimap: true, labels: true, help: true, hint: true, joystick: true, loader: true, credits: true,
};

const MODE_BUTTONS = [['aerial', 'Aérea', '1'], ['walk', 'Paseo', '2'], ['fly', 'Vuelo', '3']];
const PHASE_BUTTONS = [['construccion', 'Construcción'], ['conflicto', 'Conflicto'], ['convergencia', 'Convergencia'], ['colapso', 'Colapso']];

/** Merges the page's widget switches over the defaults. */
export function resolveUi(ui = {}) {
  return { ...DEFAULT_UI, ...ui };
}

function controlsHtml(ui, modes) {
  if (!ui.modeControl && !ui.phaseControl) return '';
  const mode = ui.modeControl ? `
    <div class="seg panel" role="group" aria-label="Modo de cámara">
      <span class="seg-label">Vista</span>
      ${MODE_BUTTONS.filter(([m]) => modes.includes(m)).map(([m, label, key], i) => `<button type="button" data-mode="${m}" aria-pressed="${i === 0}" title="Tecla ${key}">${label}</button>`).join('')}
    </div>` : '';
  const phase = ui.phaseControl ? `
    <div class="seg phases panel" role="group" aria-label="Fase de la temporada">
      <span class="seg-label">Fase</span>
      ${PHASE_BUTTONS.map(([p, label], i) => `<button type="button" data-phase="${p}" aria-pressed="${i === 0}">${label}</button>`).join('')}
    </div>` : '';
  return `<div class="controls">${mode}${phase}</div>`;
}

export function renderShell(root, ui, { title, subtitle, modes }) {
  root.innerHTML = `
    <canvas class="mv-scene" tabindex="0" aria-label="Mapa 3D del Valle de la Grieta"></canvas>
    ${ui.labels ? '<div class="mv-labels"></div>' : ''}
    ${ui.brand ? `<header class="brand"><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></header>` : ''}
    ${controlsHtml(ui, modes)}
    ${ui.places ? `
      <aside class="mv-places panel" aria-label="Lugares del mapa">
        <header><h2>Lugares</h2><span class="mv-place-count"></span></header>
        <div class="mv-place-list"></div>
      </aside>
      <button type="button" class="mv-places-toggle panel" aria-expanded="false">Lugares</button>` : ''}
    ${ui.card ? '<article class="mv-card panel" hidden aria-live="polite"></article>' : ''}
    ${ui.hint ? '<div class="hint panel" hidden></div>' : ''}
    ${ui.help ? '<div class="help"></div>' : ''}
    ${ui.credits ? '<div class="credits">Modelos 3D: Kenney (CC0)</div>' : ''}
    ${ui.minimap ? `
      <div class="mini panel">
        <canvas class="mv-minimap" width="440" height="440" aria-label="Minimapa: haz clic para ir a ese punto"></canvas>
        <div class="mini-foot"><span class="mv-coords">x 0 · z 0</span><span>N ↑ · isla de 480 pasos</span></div>
      </div>` : ''}
    ${ui.joystick ? '<div class="mv-joy" hidden><div class="knob"></div></div>' : ''}
    ${ui.loader ? `
      <div class="mv-loader">
        <div class="box">
          <h2>${esc(title)}</h2>
          <p class="mv-load-msg">Desplegando el mapa…</p>
          <div class="bar"><i class="mv-load-bar"></i></div>
          <div class="mv-load-count"></div>
        </div>
      </div>` : ''}`;
  const q = (s) => root.querySelector(s);
  return {
    canvas: q('.mv-scene'), labels: q('.mv-labels'), places: q('.mv-places'), placeList: q('.mv-place-list'),
    placeCount: q('.mv-place-count'), placesToggle: q('.mv-places-toggle'), card: q('.mv-card'), hint: q('.hint'),
    help: q('.help'), minimap: q('.mv-minimap'), coords: q('.mv-coords'), joy: q('.mv-joy'),
    loader: q('.mv-loader'), loadMsg: q('.mv-load-msg'), loadBar: q('.mv-load-bar'), loadCount: q('.mv-load-count'),
  };
}
