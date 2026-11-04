// HTML templates for the La Última Luz panels. Presentational only: data in, markup out.
import { esc } from "../map/noise.js";
import {
  EVENT_TIMING_TEXT, MAX_CHISPAS_PER_VOTE, TACTICS, TRIANGLE_TEXT, WOUND_RULE_TEXT,
  factionName, hearts, reasonText, sealLabel, tacticLabel, tacticShares,
} from "./view.js";

const fmtScore = (n) => (Number.isFinite(n) ? n.toLocaleString("es-ES", { maximumFractionDigits: 2 }) : "—");
const fmtPct = (n) => `${Math.round((n ?? 0) * 100)} %`;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" }) : "");

export function introHtml() {
  return `
    <h2>¿Cuándo llega La Última Luz?</h2>
    <p>${esc(EVENT_TIMING_TEXT)}</p>
    <p class="muted">Mientras tanto, en convergencia y colapso puedes patrocinar con Chispas a los miembros de tu facción: los más patrocinados tienen más opciones de ser elegidos campeones.</p>`;
}

function heartsHtml(c) {
  const hs = hearts(c.wounds, c.max_wounds);
  const label = `${c.max_wounds - Math.min(c.wounds, c.max_wounds)} de ${c.max_wounds} vidas`;
  return `<span class="hearts" role="img" aria-label="${label}">${hs.map((alive) => `<span class="heart${alive ? "" : " lost"}" aria-hidden="true">${alive ? "♥" : "♡"}</span>`).join("")}</span>`;
}

export function championsHtml(state, myFaction) {
  return `
    <h2>Campeones</h2>
    <div class="champions">
      ${state.champions.map((c) => `
        <article class="champion${c.alive ? "" : " is-out"}${c.faction_slug === myFaction ? " is-mine" : ""}" style="--fc:${esc(c.faction_color)}">
          <header>
            <span class="faction">${esc(c.faction_name)}${c.faction_slug === myFaction ? " · tu facción" : ""}</span>
            <span class="state">${c.alive ? "En pie" : `Eliminado en la ronda ${c.eliminated_round ?? "?"}`}</span>
          </header>
          <div class="handle">@${esc(c.handle)}</div>
          <div class="row">${heartsHtml(c)}<span class="score" title="Puntuación acumulada">${fmtScore(c.total_score)} pts</span></div>
        </article>`).join("")}
    </div>`;
}

function myTotalsHtml(duel) {
  const shares = tacticShares(duel.my_faction_totals);
  return `
    <div class="my-vote">
      <p>Tu voto: <strong>${esc(tacticLabel(duel.my_tactic))}</strong> con peso <strong>${duel.my_weight ?? 1}</strong>.</p>
      <p class="muted">Así va tu facción (${duel.my_faction_voters} ${duel.my_faction_voters === 1 ? "votante" : "votantes"}). Las tácticas rivales se revelan al resolver la ronda.</p>
      <ul class="totals">
        ${shares.map((s) => `
          <li><span>${s.label}</span><span class="bar-track"><span class="bar-fill" style="width:${s.pct}%"></span></span><span class="num">${s.weight}</span></li>`).join("")}
      </ul>
    </div>`;
}

function votingFormHtml(duel, chispas) {
  const max = Math.min(MAX_CHISPAS_PER_VOTE, Math.max(0, chispas | 0));
  return `
    <form class="vote-form" novalidate>
      <fieldset class="tactics">
        <legend>Elige la táctica de tu campeón</legend>
        ${TACTICS.map((t, i) => `
          <label class="tactic">
            <input type="radio" name="tactic" value="${t.id}" ${i === 0 ? "required" : ""} />
            <span class="t-name">${t.label}</span>
            <span class="t-beats">vence a ${tacticLabel(t.beats).toLowerCase()}</span>
          </label>`).join("")}
      </fieldset>
      <p class="muted small">${esc(TRIANGLE_TEXT)}</p>
      <label class="spend">
        <span>Chispas para reforzar tu voto: <output name="spendOut">0</output> <span class="muted">(peso <output name="weightOut">1</output>)</span></span>
        <input type="range" name="spend" min="0" max="${max}" step="1" value="0" ${max === 0 ? "disabled" : ""} aria-describedby="spend-help" />
        <span id="spend-help" class="muted small">Tienes ${chispas} Chispas. Cada Chispa suma 1 al peso (máximo ${MAX_CHISPAS_PER_VOTE}).</span>
      </label>
      <button type="submit" class="btn">Votar</button>
      <p class="error" role="alert" data-error></p>
    </form>`;
}

export function duelHtml(duel, chispas) {
  let body;
  if (duel.has_voted) body = myTotalsHtml(duel);
  else if (duel.can_vote) body = votingFormHtml(duel, chispas);
  else body = '<p class="muted">Tu facción ya no tiene campeón en pie, así que no puedes votar en este duelo. Puedes seguir la ronda desde aquí.</p>';
  return `
    <div class="duel-head">
      <h2>Duelo de hoy · ${esc(duel.zone_name)}</h2>
      <span class="countdown" data-countdown aria-live="off"></span>
    </div>
    <p class="muted small">Ronda ${duel.round_number}. Se cierra el ${esc(fmtDate(duel.closes_at))}. ${esc(WOUND_RULE_TEXT)}</p>
    ${body}`;
}

export function lastRoundHtml(state) {
  const r = state.last_round;
  return `
    <h2>Última ronda · ${esc(r.zone_name)}</h2>
    <p class="muted small">Ronda ${r.round_number} · resuelta el ${esc(fmtDate(r.resolved_at))}</p>
    <p class="reason">${esc(reasonText(state, r))}</p>
    <div class="table-wrap">
      <table class="results">
        <thead><tr><th scope="col">Facción</th><th scope="col">Táctica</th><th scope="col">Peso</th><th scope="col">Participación</th><th scope="col">Victorias</th><th scope="col">Puntos</th></tr></thead>
        <tbody>
          ${[...r.factions].sort((a, b) => b.score - a.score).map((f) => `
            <tr class="${f.wounded ? "is-wounded" : ""}">
              <th scope="row">${esc(factionName(state, f.faction_slug))}${f.wounded ? ' <span class="tag">herida</span>' : ""}</th>
              <td>${esc(tacticLabel(f.tactic))}</td><td>${f.total_weight}</td><td>${fmtPct(f.participation)}</td><td>${f.wins}</td><td>${fmtScore(f.score)}</td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

export function winnerHtml(state) {
  const w = state.winner;
  const champ = w.champion_handle ? ` con @${esc(w.champion_handle)} como campeón` : "";
  return `<h2>Vencedor</h2><p class="winner"><strong>${esc(w.faction_name)}</strong> sobrevive a La Última Luz${champ}.</p>`;
}

export function sealPickerHtml(seal) {
  return `
    <h2>Elige el sello de la próxima temporada</h2>
    <p class="muted small">Como campeón vencedor decides qué estadística del mundo arranca reforzada.${seal.deadline ? ` Plazo: ${esc(fmtDate(seal.deadline))}; si nadie elige, se aplica el Sello del Eco.` : ""}</p>
    <form class="seal-form" novalidate>
      <fieldset class="seals">
        <legend class="sr-only">Sellos disponibles</legend>
        ${seal.options.map((o, i) => `
          <label class="seal-opt">
            <input type="radio" name="seal" value="${esc(o.id)}" ${i === 0 ? "required" : ""} />
            <span class="t-name">${esc(sealLabel(o.id))}</span>
            <span class="t-beats">+${o.bonus} ${esc(o.stat)}</span>
          </label>`).join("")}
      </fieldset>
      <button type="submit" class="btn">Sellar la temporada</button>
      <p class="error" role="alert" data-error></p>
    </form>`;
}

export function sealWaitingHtml(seal) {
  return `<h2>Sello pendiente</h2><p class="muted">El campeón vencedor está eligiendo el sello${seal.deadline ? ` (plazo: ${esc(fmtDate(seal.deadline))})` : ""}. Si no lo hace a tiempo se aplicará el Sello del Eco.</p>`;
}

export function sealedHtml(state) {
  const opt = state.seal.options.find((o) => o.id === state.seal.selected);
  const bonus = opt ? ` (+${opt.bonus} ${esc(opt.stat)})` : "";
  const next = state.next_season_number ? `la temporada ${state.next_season_number}` : "la nueva temporada";
  return `
    <h2>Temporada sellada</h2>
    <p>Sello elegido: <strong>${esc(sealLabel(state.seal.selected))}</strong>${bonus}.</p>
    <p><a class="btn" href="/poblado.html">Ir al poblado de ${next}</a></p>`;
}
