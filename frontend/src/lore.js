// Public lore wiki: built from map-data.json (regions, POIs, story seeds) plus GET /api/lore. No login needed.
import { apiFetch } from "./api.js";
import { esc } from "./map/noise.js";
import { mountNav } from "./ui/nav.js";
import { toastError } from "./ui/toast.js";
import { statChipsHtml } from "./ui/stats.js";
import { factionRows, phaseLabel, regionCards, timelineItems, winnerRows } from "./lore/view.js";

const $ = (id) => document.getElementById(id);
const MAP_DATA_URL = "/mapa/map-data.json";
const REGION_DOT = { neutral: "#c9c2b0", gremio: "var(--gremio)", orden: "var(--orden)", culto: "var(--culto)" };

mountNav($("site-nav"), "lore");
init();

async function init() {
  const [mapRes, loreRes] = await Promise.allSettled([loadMapData(), apiFetch("/api/lore")]);
  const lore = loreRes.status === "fulfilled" ? loreRes.value : null;
  if (mapRes.status === "fulfilled") renderRegions(mapRes.value);
  else fail("regions", "No se pudo leer el mapa del valle. Recarga la página.");
  if (lore) {
    renderSeason(lore);
    renderFactions(lore.factions);
    renderChronicle(lore.decisions);
    renderWinners(lore.battle_royales);
  } else {
    const msg = "No se pudo conectar con el valle. Prueba de nuevo en un rato.";
    toastError(msg);
    for (const id of ["season-body", "factions", "chronicle", "winners"]) fail(id, msg);
  }
}

async function loadMapData() {
  const res = await fetch(MAP_DATA_URL);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function done(id, html) {
  const el = $(id);
  el.innerHTML = html;
  el.removeAttribute("aria-busy");
  el.closest("[aria-busy]")?.removeAttribute("aria-busy");
}

const fail = (id, msg) => done(id, `<p class="empty">${esc(msg)}</p>`);

function renderSeason({ season, world }) {
  if (!season) {
    done("season-body", '<p class="muted">Ahora mismo no hay temporada en curso.</p>');
    return;
  }
  done("season-body", `
    <p style="margin: 0 0 12px;"><strong>Temporada ${season.number} · ${esc(season.name)}</strong>
      <span class="pill" style="border: 1px solid var(--accent); color: var(--accent); margin-left: 8px;">Fase: ${esc(phaseLabel(season.phase))}</span></p>
    ${world ? `<div class="stat-grid" aria-label="Estado del valle">${statChipsHtml(world)}</div>` : ""}`);
}

function renderFactions(factions) {
  const rows = factionRows(factions);
  if (!rows.length) { done("factions", '<p class="empty">Todavía no hay facciones.</p>'); return; }
  done("factions", rows.map((f) => `
    <article class="card lore-card">
      <h3 style="display:flex;align-items:center;gap:10px"><span class="dot" style="background:${esc(f.color)}" aria-hidden="true"></span>${esc(f.name)}</h3>
      <div class="lore-meta"><span>${f.influence_pct}% de influencia</span><span>${f.members} ${f.members === 1 ? "miembro" : "miembros"}</span></div>
      <div class="bar-track" role="img" aria-label="${f.influence_pct}% de influencia"><div class="bar-fill" style="width:${Number(f.influence_pct) || 0}%;background:${esc(f.color)}"></div></div>
    </article>`).join(""));
}

function renderRegions(DATA) {
  done("regions", regionCards(DATA).map((r) => `
    <article class="card lore-card" id="region-${esc(r.id)}">
      <div class="poi-head">
        <h3 style="display:flex;align-items:center;gap:10px"><span class="dot" style="background:${REGION_DOT[r.faction] ?? "linear-gradient(90deg, var(--gremio) 50%, var(--orden) 50%)"}" aria-hidden="true"></span>${esc(r.name)}</h3>
        <a class="map-link" href="${esc(r.href)}">Ver en el mapa<span class="sr-only">: ${esc(r.name)}</span></a>
      </div>
      <div class="lore-meta"><span>${esc(r.factionName)}</span><span>Stat: ${esc(r.statLabel)}</span></div>
      <p>${esc(r.summary)}</p>
      <p class="lore-seed"><b>Semilla de historia</b>${esc(r.story)}</p>
      ${r.pois.length ? `<ul class="poi-list" aria-label="Lugares de ${esc(r.name)}">${r.pois.map((p) => `
        <li>
          <div class="poi-head"><strong>${esc(p.name)}</strong><span class="poi-kind">${esc(p.kindLabel)}</span></div>
          <span class="muted" style="font-size: 14px; line-height: 1.5;">${esc(p.text)}</span>
          <a class="map-link" href="${esc(p.href)}">Ver en el mapa<span class="sr-only">: ${esc(p.name)}</span></a>
        </li>`).join("")}</ul>` : ""}
    </article>`).join(""));
}

function renderChronicle(decisions) {
  const items = timelineItems(decisions);
  if (!items.length) { done("chronicle", '<p class="empty">Aún no se ha cerrado ninguna decisión.</p>'); return; }
  done("chronicle", `<ol class="timeline">${items.map((d) => `
    <li>
      <time datetime="${esc(d.date)}">${esc(d.dateLabel)}<br><span style="font-size: 12px;">Temporada ${d.seasonNumber}</span></time>
      <div>
        <p class="q">${esc(d.question)}</p>
        <div class="lore-meta">
          ${d.mapHref ? `<a href="${esc(d.mapHref)}">${esc(d.regionName)}</a>` : `<span>${esc(d.regionName)}</span>`}
          <span>${esc(d.outcome)}</span>
          ${d.effects.map((e) => `<span class="fx ${e.positive ? "up" : "down"}">${esc(e.text)}</span>`).join("")}
        </div>
      </div>
    </li>`).join("")}</ol>`);
}

function renderWinners(brs) {
  const rows = winnerRows(brs);
  if (!rows.length) { done("winners", '<p class="empty">La Última Luz aún no ha coronado a nadie.</p>'); return; }
  done("winners", `
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th scope="col">Temporada</th><th scope="col">Facción</th><th scope="col">Campeón</th><th scope="col">Sello</th></tr></thead>
      <tbody>${rows.map((w) => `<tr><td>${esc(w.season)}</td><td>${esc(w.faction)}</td><td>${esc(w.champion)}</td><td>${esc(w.seal)}</td></tr>`).join("")}</tbody>
    </table></div>`);
}
