// Ranking page: Chispas / season votes, filter by faction, paginated table and my position.
import { apiFetch, requireAuthOrRedirect } from "./api.js";
import { esc } from "./map/noise.js";
import { mountNav } from "./ui/nav.js";
import { toastError } from "./ui/toast.js";
import { SCOPES, atHandle, myPositionText, pageInfo, rankingPath, rankingRows } from "./ranking/view.js";

const $ = (id) => document.getElementById(id);
const state = { scope: "chispas", faction: null, page: 0, me: null, factions: [], seq: 0 };

if (requireAuthOrRedirect()) init();

async function init() {
  try {
    state.me = await apiFetch("/api/users/me");
  } catch {
    window.location.href = "/index.html";
    return;
  }
  mountNav($("site-nav"), "ranking", state.me);
  $("who").textContent = atHandle(state.me.handle);
  try {
    state.factions = await apiFetch("/api/factions");
  } catch (err) {
    toastError(`No se pudieron cargar las facciones: ${err.message}`);
  }
  renderTabs();
  renderChips();
  $("scope-tabs").addEventListener("keydown", onTabKey);
  await load();
}

function renderTabs() {
  const box = $("scope-tabs");
  box.innerHTML = SCOPES.map((s) => `<button type="button" role="tab" class="tab" id="tab-${s.id}" aria-controls="rank-panel" data-scope="${s.id}" aria-selected="${s.id === state.scope}" tabindex="${s.id === state.scope ? 0 : -1}">${esc(s.label)}</button>`).join("");
  $("rank-panel").setAttribute("aria-labelledby", `tab-${state.scope}`);
  box.querySelectorAll("[data-scope]").forEach((b) => b.addEventListener("click", () => select({ scope: b.dataset.scope })));
}

/** Arrow keys move between tabs (WAI-ARIA tabs pattern). */
function onTabKey(e) {
  if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
  const i = SCOPES.findIndex((s) => s.id === state.scope);
  const next = SCOPES[(i + (e.key === "ArrowRight" ? 1 : SCOPES.length - 1)) % SCOPES.length];
  select({ scope: next.id });
  $(`tab-${next.id}`)?.focus();
}

function renderChips() {
  const all = [{ slug: null, name: "Todas", color: null }, ...state.factions];
  $("faction-chips").innerHTML = all.map((f) => `
    <button type="button" class="chip-btn" data-faction="${esc(f.slug ?? "")}" aria-pressed="${(f.slug ?? null) === state.faction}">
      ${f.color ? `<span class="dot" style="background:${esc(f.color)}" aria-hidden="true"></span>` : ""}${esc(f.name)}
    </button>`).join("");
  $("faction-chips").querySelectorAll("[data-faction]").forEach((b) => b.addEventListener("click", () => select({ faction: b.dataset.faction || null })));
}

function select(change) {
  Object.assign(state, change, { page: change.page ?? 0 });
  renderTabs();
  renderChips();
  load();
}

function skeleton() {
  return Array.from({ length: 6 }, () => '<span class="skeleton" style="height: 22px;"></span>').join("");
}

async function load() {
  const panel = $("rank-panel"), seq = ++state.seq;
  panel.setAttribute("aria-busy", "true");
  panel.innerHTML = skeleton();
  $("me-row").hidden = true;
  try {
    const data = await apiFetch(rankingPath(state));
    if (seq !== state.seq) return;
    renderTable(data);
  } catch (err) {
    if (seq !== state.seq) return;
    const msg = err.status === 404 && state.scope === "votos" ? "No hay temporada activa: todavía no hay votos que contar." : err.message;
    panel.innerHTML = `<p class="empty">${esc(msg)}</p>`;
    if (err.status !== 404) toastError(msg);
  } finally {
    if (seq === state.seq) panel.setAttribute("aria-busy", "false");
  }
}

function renderTable(data) {
  const panel = $("rank-panel");
  const rows = rankingRows(data, { meId: state.me.id, factions: state.factions });
  const info = pageInfo(data);
  const valueHead = state.scope === "votos" ? "Votos" : "Chispas";
  $("me-row").hidden = false;
  $("me-row").textContent = `Tu posición: ${myPositionText(data.me, state.scope)}`;
  if (!rows.length) {
    panel.innerHTML = '<p class="empty">Nadie en este ranking todavía.</p>';
    return;
  }
  panel.innerHTML = `
    <div class="table-wrap">
      <table class="data-table">
        <caption class="sr-only">${esc(valueHead)} · página ${info.page + 1} de ${info.pages}</caption>
        <thead><tr><th scope="col" class="num">#</th><th scope="col">Jugador</th><th scope="col">Facción</th><th scope="col">Rol</th><th scope="col" class="num">${valueHead}</th></tr></thead>
        <tbody>
          ${rows.map((r) => `
            <tr class="${r.isMe ? "is-me" : ""}"${r.isMe ? ' aria-current="true"' : ""}>
              <td class="num">${r.rank}</td>
              <td>${esc(r.handle)}${r.isMe ? ' <span class="muted">(tú)</span>' : ""}</td>
              <td><span style="display:inline-flex;align-items:center;gap:8px"><span class="dot" style="${r.factionColor ? `background:${esc(r.factionColor)}` : ""}" aria-hidden="true"></span>${esc(r.factionName)}</span></td>
              <td>${esc(r.role)}</td>
              <td class="num">${esc(r.value)}</td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>
    <div class="pager">
      <span class="muted">${info.from}–${info.to} de ${info.total}</span>
      <span style="display:flex;gap:8px">
        <button type="button" class="btn secondary" data-page="prev" ${info.hasPrev ? "" : "disabled"}>Anterior</button>
        <button type="button" class="btn secondary" data-page="next" ${info.hasNext ? "" : "disabled"}>Siguiente</button>
      </span>
    </div>`;
  panel.querySelector('[data-page="prev"]').addEventListener("click", () => go(info.page - 1));
  panel.querySelector('[data-page="next"]').addEventListener("click", () => go(info.page + 1));
}

function go(page) {
  state.page = Math.max(0, page);
  load();
}
