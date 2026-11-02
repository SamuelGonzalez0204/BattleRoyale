// Escena ilustrada del poblado: traduce las 5 stats del mundo en una
// composición de sprites CC0 (Kenney) en vez de barras de progreso.
// Las posiciones son porcentajes fijos (mismo criterio que el mockup
// de diseño); lo único que cambia con los datos reales es CUÁNTAS
// piezas de cada tipo aparecen "construidas" frente a "vacías".

const SPRITES = {
  wallDoor: "/sprites/house-wall-door.png",
  wallPlain: "/sprites/house-wall-plain.png",
  roofGable: "/sprites/house-roof-gable.png",
  roofPlain: "/sprites/house-roof-plain.png",
  treeA: "/sprites/tree.png",
  treeHigh: "/sprites/tree-high.png",
  treeCrooked: "/sprites/tree-crooked.png",
  water: "/sprites/water-tile.png",
  dirt: "/sprites/dirt-tile.png",
  crystal: "/sprites/crystal.png",
  plant: "/sprites/plant.png",
  villagerA: "/sprites/villager-a.png",
  villagerB: "/sprites/villager-b.png",
};

const HOUSE_SLOTS = [
  { left: 44, top: 16 }, { left: 58, top: 28 }, { left: 48, top: 44 }, { left: 66, top: 14 }, { left: 38, top: 60 },
];
const TREE_SLOTS = [
  { left: 12, top: 8 }, { left: 28, top: 6 }, { left: 82, top: 12 }, { left: 90, top: 34 }, { left: 16, top: 82 },
];
const FIELD_SLOTS = [
  { left: 56, top: 58, w: 18, h: 30 }, { left: 78, top: 52, w: 18, h: 38 },
];
const COIN_SLOTS = [
  { left: 30, top: 18 }, { left: 22, top: 34 }, { left: 34, top: 46 },
];
const CROP_SPOTS = [
  { left: 60, top: 64 }, { left: 66, top: 70 }, { left: 82, top: 58 }, { left: 88, top: 64 },
];
const VILLAGERS = [
  { left: 52, top: 36, src: SPRITES.villagerA },
  { left: 62, top: 20, src: SPRITES.villagerB },
];

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

export function renderVillage(container, stats) {
  const builtHouses = clamp(Math.round(stats.poblacion / 20), 1, HOUSE_SLOTS.length);
  const builtTrees = clamp(Math.round(stats.defensa / 20), 1, TREE_SLOTS.length);
  const builtFields = clamp(Math.round(stats.comida / 50), 1, FIELD_SLOTS.length);
  const builtCoins = clamp(Math.round(stats.oro / 33), 1, COIN_SLOTS.length);
  const treeImgs = [SPRITES.treeA, SPRITES.treeHigh, SPRITES.treeCrooked];

  let html = `
    <div style="position:absolute;left:6%;top:10%;width:30%;height:46%;border-radius:50%;background-image:url(${SPRITES.water});background-size:44px 44px;background-repeat:repeat;opacity:0.9"></div>
    <div style="position:absolute;left:10%;top:14%;width:10%;height:14%;border-radius:50%;background:rgba(255,255,255,0.14)"></div>
  `;

  FIELD_SLOTS.forEach((p, i) => {
    const look =
      i < builtFields
        ? `background-image:url(${SPRITES.dirt});background-size:28px 28px;background-repeat:repeat`
        : `background:#2a2620;opacity:0.5;border:2px dashed #4a4538`;
    html += `<div style="position:absolute;left:${p.left}%;top:${p.top}%;width:${p.w}%;height:${p.h}%;border-radius:8px;${look}"></div>`;
  });

  CROP_SPOTS.slice(0, builtFields * 2).forEach((p) => {
    html += `<img src="${SPRITES.plant}" alt="" style="position:absolute;left:${p.left}%;top:${p.top}%;width:10px;height:10px;object-fit:contain">`;
  });

  COIN_SLOTS.forEach((p, i) => {
    html +=
      i < builtCoins
        ? `<img src="${SPRITES.crystal}" alt="" style="position:absolute;left:${p.left}%;top:${p.top}%;width:12px;height:12px;object-fit:contain">`
        : `<div style="position:absolute;left:${p.left}%;top:${p.top}%;width:10px;height:10px;border-radius:50%;border:1px dashed #8a6214;opacity:0.4"></div>`;
  });

  TREE_SLOTS.forEach((p, i) => {
    html += `<div style="position:absolute;left:${p.left}%;top:${p.top}%;width:22px;height:26px">`;
    html +=
      i < builtTrees
        ? `<img src="${treeImgs[i % treeImgs.length]}" alt="" style="width:100%;height:100%;object-fit:contain">`
        : `<div style="position:absolute;top:2px;left:3px;width:16px;height:16px;border-radius:50%;border:2px dashed #4a4538;opacity:0.6"></div>`;
    html += `</div>`;
  });

  VILLAGERS.forEach((v) => {
    html += `<img src="${v.src}" alt="" style="position:absolute;left:${v.left}%;top:${v.top}%;width:16px;height:16px;object-fit:contain">`;
  });

  HOUSE_SLOTS.forEach((p, i) => {
    html += `<div style="position:absolute;left:${p.left}%;top:${p.top}%;width:28px;height:26px">`;
    if (i < builtHouses) {
      const variantA = i % 2 === 0;
      const wall = variantA ? SPRITES.wallDoor : SPRITES.wallPlain;
      const roof = variantA ? SPRITES.roofGable : SPRITES.roofPlain;
      html += `<img src="${roof}" alt="" style="position:absolute;top:-6px;left:0;width:28px;height:18px;object-fit:contain">`;
      html += `<img src="${wall}" alt="" style="position:absolute;bottom:0;left:3px;width:22px;height:22px;object-fit:contain">`;
    } else {
      html += `<div style="position:absolute;bottom:0;left:2px;width:24px;height:18px;border-radius:4px;background:rgba(255,255,255,0.06);border:2px dashed #4a4538"></div>`;
    }
    html += `</div>`;
  });

  container.innerHTML = html;
}

const STAT_ICON_PATHS = {
  poblacion: '<path d="M2 8L8 2L14 8V14H2Z" fill="none" stroke="currentColor" stroke-width="1.3"></path>',
  comida:
    '<line x1="8" y1="14" x2="8" y2="3" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="5" x2="4" y2="3" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="5" x2="12" y2="3" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="9" x2="4.5" y2="7" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="9" x2="11.5" y2="7" stroke="currentColor" stroke-width="1.2"></line>',
  moral:
    '<path d="M8 13.5C3.5 10 1.8 7 3.3 4.8C4.4 3.2 6.6 3.4 8 5.2C9.4 3.4 11.6 3.2 12.7 4.8C14.2 7 12.5 10 8 13.5Z" fill="none" stroke="currentColor" stroke-width="1.2"></path>',
  defensa:
    '<path d="M8 1.5L13.5 3.5V8C13.5 11 11 13.3 8 14.3C5 13.3 2.5 11 2.5 8V3.5Z" fill="none" stroke="currentColor" stroke-width="1.2"></path>',
  oro: '<circle cx="8" cy="8" r="5.5" fill="none" stroke="#e0a73c" stroke-width="1.2"></circle><circle cx="8" cy="8" r="3" fill="none" stroke="#e0a73c" stroke-width="1"></circle>',
};

const STAT_LABELS = {
  poblacion: "Población",
  comida: "Comida",
  moral: "Moral",
  defensa: "Defensa",
  oro: "Oro",
};

export function renderStatChips(container, stats) {
  container.innerHTML = Object.keys(STAT_LABELS)
    .map(
      (key) => `
      <div style="display:flex;align-items:center;gap:8px;background:var(--card-soft);border:1px solid var(--border);border-radius:999px;padding:6px 14px;color:var(--ink)">
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">${STAT_ICON_PATHS[key]}</svg>
        <span style="font-size:13px;font-weight:600">${stats[key]}%</span>
        <span class="muted" style="font-size:12px">${STAT_LABELS[key]}</span>
      </div>`
    )
    .join("");
}
