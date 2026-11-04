// La Última Luz: the valley map as main view plus champions, duel, results, sponsorship and seal panels.
import { apiFetch, requireAuthOrRedirect } from "./api.js";
import { createMapViewer } from "./map/viewer.js";
import {
  championsHtml, duelHtml, introHtml, lastRoundHtml, sealPickerHtml, sealWaitingHtml, sealedHtml, winnerHtml,
} from "./br/panels.js";
import { renderSponsor } from "./br/sponsor.js";
import { apiErrorText, clampSpend, formatCountdown, sections, statusLine, viewerConfig, voteWeight } from "./br/view.js";

const $ = (id) => document.getElementById(id);
const COUNTDOWN_TICK_MS = 1000;
const REFRESH_AFTER_CLOSE_MS = 60_000;
const ctx = { me: null, state: null, viewer: null, timer: null, worldPhase: null };

if (requireAuthOrRedirect()) init();

function showPageError(message) {
  const box = $("page-error");
  box.textContent = message;
  box.hidden = !message;
}

async function init() {
  try {
    ctx.me = await apiFetch("/api/users/me");
  } catch {
    window.location.href = "/index.html";
    return;
  }
  if (!ctx.me.faction_slug) {
    window.location.href = "/augurio.html";
    return;
  }
  $("who").textContent = `@${ctx.me.handle} · ${ctx.me.faction_slug}`;
  setChispas(ctx.me.chispas);
  ctx.viewer = createMapViewer($("map"), {
    assetBase: "/mapa/",
    modes: ["aerial", "walk"],
    globalKeys: false,
    ui: { brand: false, phaseControl: false, places: false, help: false, credits: false },
  });
  ctx.viewer.ready.catch(() => showPageError("No se pudo cargar el mapa 3D. El resto de la página sigue funcionando."));
  try {
    const world = await apiFetch("/api/world");
    ctx.worldPhase = world.phase;
  } catch {
    ctx.worldPhase = null;
  }
  await loadState();
}

function setChispas(n) {
  $("chispas").textContent = `${n} ✦`;
}

async function loadState() {
  $("status-line").textContent = "Cargando…";
  $("panels").setAttribute("aria-busy", "true");
  try {
    ctx.state = await apiFetch("/api/br/state");
    showPageError("");
    render();
  } catch (err) {
    $("status-line").textContent = "";
    showPageError(apiErrorText(err));
  } finally {
    $("panels").setAttribute("aria-busy", "false");
  }
}

function setSection(id, visible, html) {
  const el = $(id);
  el.hidden = !visible;
  if (visible && html !== undefined) el.innerHTML = html;
  return el;
}

function render() {
  const { state, me } = ctx;
  const show = sections(state);
  $("status-line").textContent = statusLine(state);
  const view = viewerConfig(state, ctx.worldPhase);
  ctx.viewer.setPhase(view.phase);
  ctx.viewer.setFallenZones(view.fallen);
  if (view.focus) ctx.viewer.focusRegion(view.focus);

  setSection("intro", show.intro, introHtml());
  setSection("champions", show.champions, show.champions ? championsHtml(state, me.faction_slug) : "");
  setSection("winner", show.winner, show.winner ? winnerHtml(state) : "");
  setSection("seal", show.sealPicker || show.sealWaiting || show.sealed,
    show.sealPicker ? sealPickerHtml(state.seal) : show.sealed ? sealedHtml(state) : show.sealWaiting ? sealWaitingHtml(state.seal) : "");
  if (show.sealPicker) wireSeal();
  setSection("duel", show.duel, show.duel ? duelHtml(state.current_duel, me.chispas) : "");
  if (show.duel) { wireVote(state.current_duel); startCountdown(state.current_duel.closes_at); } else stopCountdown();
  setSection("last-round", show.lastRound, show.lastRound ? lastRoundHtml(state) : "");
  const sponsorEl = setSection("sponsor", show.sponsor);
  if (show.sponsor) renderSponsor(sponsorEl, me, setChispas);
}

function stopCountdown() {
  clearInterval(ctx.timer);
  ctx.timer = null;
}

function startCountdown(closesAt) {
  stopCountdown();
  const end = new Date(closesAt).getTime();
  const tick = () => {
    const el = document.querySelector("[data-countdown]");
    if (!el) return stopCountdown();
    const left = formatCountdown(end - Date.now());
    el.textContent = left ? `Cierra en ${left}` : "Votación cerrada · se resuelve en el cierre diario";
    if (!left) {
      stopCountdown();
      document.querySelectorAll(".vote-form input, .vote-form button").forEach((n) => { n.disabled = true; });
      setTimeout(loadState, REFRESH_AFTER_CLOSE_MS);
    }
  };
  tick();
  ctx.timer = setInterval(tick, COUNTDOWN_TICK_MS);
}

function wireVote(duel) {
  const form = document.querySelector(".vote-form");
  if (!form) return;
  const range = form.elements.spend;
  const sync = () => {
    const spend = clampSpend(range.value, ctx.me.chispas);
    form.elements.spendOut.value = spend;
    form.elements.weightOut.value = voteWeight(spend);
  };
  range.addEventListener("input", sync); sync();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errBox = form.querySelector("[data-error]"), btn = form.querySelector("button[type=submit]");
    const tactic = form.elements.tactic.value;
    errBox.textContent = "";
    if (!tactic) { errBox.textContent = "Elige una táctica antes de votar."; return; }
    btn.disabled = true; btn.textContent = "Enviando voto…";
    try {
      const res = await apiFetch(`/api/br/duels/${encodeURIComponent(duel.id)}/vote`, {
        method: "POST",
        body: JSON.stringify({ tactic, chispas_to_spend: clampSpend(range.value, ctx.me.chispas) }),
      });
      ctx.me.chispas = res.my_chispas; setChispas(res.my_chispas);
      await loadState();
    } catch (err) {
      errBox.textContent = apiErrorText(err);
      btn.disabled = false; btn.textContent = "Votar";
    }
  });
}

function wireSeal() {
  const form = document.querySelector(".seal-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errBox = form.querySelector("[data-error]"), btn = form.querySelector("button[type=submit]");
    const seal = form.elements.seal.value;
    errBox.textContent = "";
    if (!seal) { errBox.textContent = "Elige un sello."; return; }
    btn.disabled = true; btn.textContent = "Sellando…";
    try {
      const res = await apiFetch("/api/br/seal", { method: "POST", body: JSON.stringify({ seal }) });
      const notice = $("notice");
      notice.textContent = `Temporada ${res.previous_season_number} sellada. Empieza la temporada ${res.new_season.number}: ${res.new_season.name}.`;
      notice.hidden = false;
      await loadState();
    } catch (err) {
      errBox.textContent = apiErrorText(err);
      btn.disabled = false; btn.textContent = "Sellar la temporada";
    }
  });
}
