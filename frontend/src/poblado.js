import { apiFetch, requireAuthOrRedirect } from "./api.js";

const STAT_LABELS = {
  poblacion: "Población",
  comida: "Comida",
  moral: "Moral",
  defensa: "Defensa",
  oro: "Oro",
};

if (requireAuthOrRedirect()) {
  init();
}

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

  document.getElementById("who").textContent = `@${me.handle} · ${me.faction_slug}`;
  document.getElementById("chispas").textContent = me.chispas;

  await Promise.all([loadWorld(), loadFactions(me.faction_slug), loadDecision()]);
}

async function loadWorld() {
  const world = await apiFetch("/api/world");
  document.getElementById("season-title").textContent = `Temporada ${world.season_number} · ${world.season_name}`;
  document.getElementById("phase-pill").textContent = `FASE: ${world.phase.toUpperCase()}`;

  const statsBox = document.getElementById("stats");
  statsBox.innerHTML = "";
  for (const key of Object.keys(STAT_LABELS)) {
    const pct = world[key];
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;gap:14px";
    row.innerHTML = `
      <div class="muted" style="width:90px;font-size:13px">${STAT_LABELS[key]}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
      <div style="width:36px;text-align:right;font-size:13px">${pct}%</div>
    `;
    statsBox.appendChild(row);
  }
}

async function loadFactions(myFactionSlug) {
  const factions = await apiFetch("/api/factions");
  const box = document.getElementById("factions");
  box.innerHTML = "";
  for (const f of factions) {
    const mine = f.slug === myFactionSlug;
    const row = document.createElement("div");
    row.style.cssText = "display:flex;flex-direction:column;gap:6px";
    row.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <span style="font-size:13px;font-weight:${mine ? 600 : 400};color:${mine ? "var(--ink)" : "var(--muted)"}">${f.name}</span>
        <span class="muted" style="font-size:12px">${f.influence_pct}% · ${f.members} miembros</span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="width:${f.influence_pct}%;background:${f.color}"></div></div>
    `;
    box.appendChild(row);
  }
}

async function loadDecision() {
  const body = document.getElementById("decision-body");
  const closesBox = document.getElementById("decision-closes");

  let decision;
  try {
    decision = await apiFetch("/api/decisions/today");
  } catch {
    body.innerHTML = `<p class="muted" style="margin:0">Todavía no hay decisión publicada para hoy. Vuelve más tarde.</p>`;
    return;
  }

  closesBox.textContent = `Se cierra ${new Date(decision.closes_at).toLocaleString()}`;
  renderDecision(decision);
}

function renderDecision(decision) {
  const body = document.getElementById("decision-body");
  const total = decision.votes_a + decision.votes_b || 1;
  const pctA = Math.round((100 * decision.votes_a) / total);
  const pctB = 100 - pctA;

  body.innerHTML = `
    <p style="margin:0 0 14px 0">${decision.question}</p>
    <div style="display:flex;gap:14px;flex-wrap:wrap">
      ${voteButton("a", decision.option_a, pctA, decision.my_vote === "a")}
      ${voteButton("b", decision.option_b, pctB, decision.my_vote === "b")}
    </div>
  `;

  body.querySelectorAll("[data-vote]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      body.querySelectorAll("[data-vote]").forEach((b) => (b.disabled = true));
      try {
        const updated = await apiFetch("/api/decisions/today/vote", {
          method: "POST",
          body: JSON.stringify({ option: btn.dataset.vote, chispas_to_spend: 0 }),
        });
        renderDecision(updated);
        const me = await apiFetch("/api/users/me");
        document.getElementById("chispas").textContent = me.chispas;
      } catch (err) {
        alert(err.message);
        body.querySelectorAll("[data-vote]").forEach((b) => (b.disabled = false));
      }
    });
  });
}

function voteButton(option, label, pct, isMine) {
  const border = isMine ? "var(--accent)" : "var(--border)";
  const bg = isMine ? "var(--accent-soft)" : "var(--card)";
  return `
    <button data-vote="${option}" class="btn secondary" style="flex:1 1 220px;text-align:left;display:flex;flex-direction:column;gap:10px;border-color:${border};background:${bg}">
      <span style="font-weight:600">${label}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
      <span class="muted" style="font-size:12px">${pct}% de los votos</span>
    </button>
  `;
}
