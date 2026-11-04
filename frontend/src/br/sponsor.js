// Sponsorship section (before La Última Luz): leaderboard per faction and the sponsor form.
import { apiFetch } from "../api.js";
import { esc } from "../map/noise.js";
import { apiErrorText, isUuid } from "./view.js";

const LIMIT = 5;
const MAX_SPONSOR = 1000;

function boardHtml(board, me) {
  const mine = board.faction_slug === me.faction_slug;
  const rows = board.members.length
    ? board.members.map((m) => `<li><span>@${esc(m.handle)}</span><span class="num">${m.total_chispas} ✦ · ${m.sponsorships}</span></li>`).join("")
    : '<li class="muted">Nadie patrocinado todavía</li>';
  return `<div class="board${mine ? " is-mine" : ""}"><h3>${esc(board.faction_name)}</h3><ol>${rows}</ol></div>`;
}

function formHtml(myBoard, me) {
  const options = (myBoard?.members ?? []).filter((m) => m.user_id !== me.id)
    .map((m) => `<option value="${esc(m.user_id)}">@${esc(m.handle)}</option>`).join("");
  return `
    <form class="sponsor-form" novalidate>
      <h3>Patrocina a alguien de tu facción</h3>
      <label>Destinatario
        <select name="recipient" class="input">${options}<option value="__id">Otro miembro (por ID)…</option></select>
      </label>
      <label class="recipient-id" hidden>ID del miembro
        <input name="recipientId" class="input" inputmode="text" autocomplete="off" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
      </label>
      <label>Chispas (1–${MAX_SPONSOR}, tienes ${me.chispas})
        <input name="chispas" class="input" type="number" min="1" max="${MAX_SPONSOR}" step="1" value="10" required />
      </label>
      <button type="submit" class="btn">Patrocinar</button>
      <p class="error" role="alert" data-error></p>
      <p class="ok" role="status" data-ok></p>
    </form>`;
}

function readForm(form, me) {
  const data = new FormData(form);
  const pick = data.get("recipient");
  const userId = String(pick === "__id" ? data.get("recipientId") : pick).trim();
  const chispas = Number(data.get("chispas"));
  if (!isUuid(userId)) return { error: "Indica un miembro válido (su ID tiene formato UUID)." };
  if (userId === me.id) return { error: "No puedes patrocinarte a ti mismo." };
  if (!Number.isInteger(chispas) || chispas < 1 || chispas > MAX_SPONSOR) return { error: `Las Chispas deben ser un entero entre 1 y ${MAX_SPONSOR}.` };
  if (chispas > me.chispas) return { error: `Solo tienes ${me.chispas} Chispas.` };
  return { body: { user_id: userId, chispas } };
}

/** Renders the section into `el`. `onChispas(n)` reports the new balance after a sponsorship. */
export async function renderSponsor(el, me, onChispas) {
  el.innerHTML = '<h2>Patrocinio</h2><p class="muted" aria-busy="true">Cargando patrocinios…</p>';
  let board;
  try {
    board = await apiFetch(`/api/sponsor/leaderboard?limit=${LIMIT}`);
  } catch (err) {
    el.innerHTML = `<h2>Patrocinio</h2><p class="error" role="alert">${esc(apiErrorText(err))}</p>`;
    return;
  }
  const myBoard = board.factions.find((f) => f.faction_slug === me.faction_slug);
  el.innerHTML = `
    <h2>Patrocinio</h2>
    <p class="muted small">${board.open ? "El patrocinio está abierto en esta fase." : "El patrocinio solo abre en convergencia y colapso, antes de La Última Luz."}</p>
    <div class="boards">${board.factions.map((b) => boardHtml(b, me)).join("")}</div>
    ${board.open && me.faction_slug ? formHtml(myBoard, me) : ""}`;
  const form = el.querySelector(".sponsor-form");
  if (!form) return;
  const idRow = form.querySelector(".recipient-id"), select = form.elements.recipient;
  const syncId = () => { idRow.hidden = select.value !== "__id"; };
  select.addEventListener("change", syncId); syncId();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errBox = form.querySelector("[data-error]"), okBox = form.querySelector("[data-ok]"), btn = form.querySelector("button");
    errBox.textContent = ""; okBox.textContent = "";
    const { error, body } = readForm(form, me);
    if (error) { errBox.textContent = error; return; }
    btn.disabled = true; btn.textContent = "Enviando…";
    try {
      const res = await apiFetch("/api/sponsor", { method: "POST", body: JSON.stringify(body) });
      me.chispas = res.my_chispas; onChispas(res.my_chispas);
      await renderSponsor(el, me, onChispas);
      const ok = el.querySelector("[data-ok]");
      if (ok) ok.textContent = `Has patrocinado a @${res.recipient_handle} con ${res.chispas} Chispas (total: ${res.recipient_total}).`;
    } catch (err) {
      errBox.textContent = apiErrorText(err);
      btn.disabled = false; btn.textContent = "Patrocinar";
    }
  });
}
