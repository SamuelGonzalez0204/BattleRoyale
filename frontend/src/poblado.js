// El poblado: compact 3D village (world stats decide what is built), factions, Chispas and today's decision.
import { apiFetch, requireAuthOrRedirect } from "./api.js";
import { createMapViewer } from "./map/viewer.js";
import { esc } from "./map/noise.js";
import { placeHref } from "./map/hash.js";
import { phaseLabel } from "./lore/view.js";
import { atHandle } from "./ranking/view.js";
import { mountNav } from "./ui/nav.js";
import { statChipsHtml } from "./ui/stats.js";
import { toastError, toastSuccess } from "./ui/toast.js";

const $ = (id) => document.getElementById(id);
const DEFAULT_REGION = "plaza";
let viewer = null;

if (requireAuthOrRedirect()) init();

async function init() {
  let me;
  try {
    me = await apiFetch("/api/users/me");
  } catch {
    window.location.href = "/index.html";
    return;
  }
  if (!me.faction_slug) {
    window.location.href = "/augurio.html";
    return;
  }
  mountNav($("site-nav"), "poblado", me);
  $("who").textContent = `${atHandle(me.handle)} · ${me.faction_slug}`;
  $("chispas").textContent = me.chispas;
  showVerifyNotice(me);
  mountViewer();

  await Promise.all([loadWorld(), loadFactions(me.faction_slug), loadDecision()]);
  // Stats change at the daily close: refresh them when the player comes back to the tab.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loadWorld(); });
}

function mountViewer() {
  viewer = createMapViewer($("village"), {
    assetBase: "/mapa/",
    mode: "aerial",
    modes: ["aerial", "walk"],
    globalKeys: false,
    title: "El poblado",
    ui: { brand: false, phaseControl: false, places: false, help: false, credits: false, minimap: false },
  });
  viewer.focusRegion(DEFAULT_REGION);
  viewer.ready.catch(() => toastError("No se pudo cargar el poblado en 3D. El resto de la página funciona."));
}

function showVerifyNotice(me) {
  if (me.is_verified) return;
  const button = $("verify-resend");
  $("verify-notice").hidden = false;
  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Enviando…";
    try {
      const { message } = await apiFetch("/api/auth/verify/resend", { method: "POST" });
      toastSuccess(message);
      button.textContent = "Email enviado";
    } catch (err) {
      toastError(err.message);
      button.disabled = false;
      button.textContent = "Reenviar email de verificación";
    }
  });
}

async function loadWorld() {
  let world;
  try {
    world = await apiFetch("/api/world");
  } catch (err) {
    $("season-title").textContent = "El poblado";
    toastError(`No se pudo leer el estado del valle: ${err.message}`);
    return;
  }
  $("season-title").textContent = `Temporada ${world.season_number} · ${world.season_name}`;
  const pill = $("phase-pill");
  pill.textContent = `Fase: ${phaseLabel(world.phase)}`;
  pill.hidden = false;
  $("stats").innerHTML = statChipsHtml(world);
  viewer?.setPhase(world.phase);
  viewer?.setWorldStats(world);
}

async function loadFactions(myFactionSlug) {
  const box = $("factions");
  try {
    const factions = await apiFetch("/api/factions");
    box.innerHTML = factions.map((f) => {
      const mine = f.slug === myFactionSlug;
      const pct = Number(f.influence_pct) || 0;
      return `
        <div style="display:flex;flex-direction:column;gap:6px">
          <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">
            <span style="font-size:13px;font-weight:${mine ? 600 : 400};color:${mine ? "var(--ink)" : "var(--muted)"}">${esc(f.name)}${mine ? " · la tuya" : ""}</span>
            <span class="muted" style="font-size:12px">${pct}% · ${f.members} ${f.members === 1 ? "miembro" : "miembros"}</span>
          </div>
          <div class="bar-track" role="img" aria-label="${esc(f.name)}: ${pct}% de influencia"><div class="bar-fill" style="width:${pct}%;background:${esc(f.color)}"></div></div>
        </div>`;
    }).join("");
  } catch (err) {
    box.innerHTML = `<p class="empty">${esc(err.message)}</p>`;
  } finally {
    box.removeAttribute("aria-busy");
  }
}

async function loadDecision() {
  const body = $("decision-body");
  let decision;
  try {
    decision = await apiFetch("/api/decisions/today");
  } catch (err) {
    const text = err.status === 409 ? err.message : "Todavía no hay decisión publicada para hoy. Vuelve más tarde.";
    body.innerHTML = `<p class="muted" style="margin:0">${esc(text)}</p>`;
    body.removeAttribute("aria-busy");
    return;
  }
  $("decision-closes").textContent = `Se cierra ${new Date(decision.closes_at).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" })}`;
  if (decision.region) {
    viewer?.focusRegion(decision.region);
    $("village-caption").innerHTML = `Hoy se decide en <a href="${esc(placeHref(decision.region))}">${esc(decision.region_name ?? decision.region)}</a>. Lo construido depende del estado del valle.`;
  }
  renderDecision(decision);
  body.removeAttribute("aria-busy");
}

function renderDecision(decision) {
  const body = $("decision-body");
  const total = decision.votes_a + decision.votes_b;
  const pctA = total ? Math.round((100 * decision.votes_a) / total) : 0;
  const pctB = total ? 100 - pctA : 0;
  const where = decision.region_name ? `<p class="muted" style="margin:0 0 6px;font-size:12px;letter-spacing:.06em;text-transform:uppercase">${esc(decision.region_name)}</p>` : "";
  body.innerHTML = `
    ${where}
    <p style="margin:0 0 14px 0">${esc(decision.question)}</p>
    <div style="display:flex;gap:14px;flex-wrap:wrap" role="group" aria-label="Opciones de voto">
      ${voteButton("a", decision.option_a, pctA, decision.my_vote === "a")}
      ${voteButton("b", decision.option_b, pctB, decision.my_vote === "b")}
    </div>`;
  body.querySelectorAll("[data-vote]").forEach((btn) => btn.addEventListener("click", () => vote(btn.dataset.vote)));
}

async function vote(option) {
  const buttons = $("decision-body").querySelectorAll("[data-vote]");
  buttons.forEach((b) => { b.disabled = true; });
  try {
    const updated = await apiFetch("/api/decisions/today/vote", {
      method: "POST",
      body: JSON.stringify({ option, chispas_to_spend: 0 }),
    });
    renderDecision(updated);
    toastSuccess("Voto registrado.");
    const me = await apiFetch("/api/users/me");
    $("chispas").textContent = me.chispas;
  } catch (err) {
    toastError(err.message);
    buttons.forEach((b) => { b.disabled = false; });
  }
}

function voteButton(option, label, pct, isMine) {
  return `
    <button type="button" data-vote="${option}" class="btn secondary vote-btn" aria-pressed="${isMine}">
      <span style="font-weight:600">${esc(label)}</span>
      <span class="bar-track" style="display:block" aria-hidden="true"><span class="bar-fill" style="display:block;width:${pct}%"></span></span>
      <span class="muted" style="font-size:12px">${pct}% de los votos${isMine ? " · tu voto" : ""}</span>
    </button>`;
}
