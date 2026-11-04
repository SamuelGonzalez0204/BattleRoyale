// Sponsorship section (before La Última Luz): leaderboard per faction and the sponsor form.
import { apiFetch } from "../api.js";
import { esc } from "../map/noise.js";
import { apiErrorText, isUuid } from "./view.js";
import { toastSuccess } from "../ui/toast.js";
import { atHandle } from "../ranking/view.js";

const LIMIT = 5;
const MAX_SPONSOR = 1000;
const MEMBER_LIMIT = 8;
const SEARCH_DEBOUNCE_MS = 250;

function boardHtml(board, me) {
  const mine = board.faction_slug === me.faction_slug;
  const rows = board.members.length
    ? board.members.map((m) => `<li><span>@${esc(m.handle)}</span><span class="num">${m.total_chispas} ✦ · ${m.sponsorships}</span></li>`).join("")
    : '<li class="muted">Nadie patrocinado todavía</li>';
  return `<div class="board${mine ? " is-mine" : ""}"><h3>${esc(board.faction_name)}</h3><ol>${rows}</ol></div>`;
}

function formHtml(me) {
  return `
    <form class="sponsor-form" novalidate>
      <h3>Patrocina a alguien de tu facción</h3>
      <label>Buscar miembro
        <input name="q" class="input" type="search" autocomplete="off" placeholder="Escribe su @" aria-controls="member-list" />
      </label>
      <fieldset class="member-pick">
        <legend>Destinatario</legend>
        <div id="member-list" class="member-list" aria-live="polite" aria-busy="true"><span class="spinner" aria-hidden="true"></span> Buscando…</div>
      </fieldset>
      <label>Chispas (1–${MAX_SPONSOR}, tienes ${me.chispas})
        <input name="chispas" class="input" type="number" min="1" max="${MAX_SPONSOR}" step="1" value="10" required />
      </label>
      <button type="submit" class="btn">Patrocinar</button>
      <p class="error" role="alert" data-error></p>
    </form>`;
}

function membersHtml(members, selected) {
  if (!members.length) return '<p class="muted small">Ningún miembro coincide.</p>';
  return members.map((m) => `
    <label class="member">
      <input type="radio" name="recipient" value="${esc(m.user_id)}"${m.user_id === selected ? " checked" : ""} />
      <span class="member-handle">${esc(atHandle(m.handle))}</span>
      <span class="num muted">${m.sponsored_total} ✦ recibidas</span>
    </label>`).join("");
}

/** Debounced search over GET /api/factions/me/members?q= (the API leaves me out). */
function wireMemberPicker(form) {
  const list = form.querySelector("#member-list"), input = form.elements.q;
  let timer = null, seq = 0;
  async function search() {
    const mine = ++seq, selected = form.querySelector('input[name="recipient"]:checked')?.value;
    list.setAttribute("aria-busy", "true");
    try {
      const q = input.value.trim().replace(/^@/, "");
      const params = new URLSearchParams({ limit: String(MEMBER_LIMIT) });
      if (q) params.set("q", q);
      const members = await apiFetch(`/api/factions/me/members?${params}`);
      if (mine === seq) list.innerHTML = membersHtml(members, selected);
    } catch (err) {
      if (mine === seq) list.innerHTML = `<p class="error">${esc(apiErrorText(err))}</p>`;
    } finally {
      if (mine === seq) list.setAttribute("aria-busy", "false");
    }
  }
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(search, SEARCH_DEBOUNCE_MS); });
  search();
}

function readForm(form, me) {
  const data = new FormData(form);
  const userId = String(data.get("recipient") ?? "").trim();
  const chispas = Number(data.get("chispas"));
  if (!isUuid(userId)) return { error: "Elige a un miembro de la lista." };
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
  el.innerHTML = `
    <h2>Patrocinio</h2>
    <p class="muted small">${board.open ? "El patrocinio está abierto en esta fase." : "El patrocinio solo abre en convergencia y colapso, antes de La Última Luz."}</p>
    <div class="boards">${board.factions.map((b) => boardHtml(b, me)).join("")}</div>
    ${board.open && me.faction_slug ? formHtml(me) : ""}`;
  const form = el.querySelector(".sponsor-form");
  if (!form) return;
  wireMemberPicker(form);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errBox = form.querySelector("[data-error]"), btn = form.querySelector('button[type="submit"]');
    errBox.textContent = "";
    const { error, body } = readForm(form, me);
    if (error) { errBox.textContent = error; return; }
    btn.disabled = true; btn.textContent = "Enviando…";
    try {
      const res = await apiFetch("/api/sponsor", { method: "POST", body: JSON.stringify(body) });
      me.chispas = res.my_chispas; onChispas(res.my_chispas);
      toastSuccess(`Has patrocinado a @${res.recipient_handle} con ${res.chispas} Chispas (total: ${res.recipient_total}).`);
      await renderSponsor(el, me, onChispas);
    } catch (err) {
      errBox.textContent = apiErrorText(err);
      btn.disabled = false; btn.textContent = "Patrocinar";
    }
  });
}
