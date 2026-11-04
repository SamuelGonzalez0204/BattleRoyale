// Pure state -> view mapping for La Última Luz. No DOM, no fetch: unit-tested.

export const TACTICS = [
  { id: "ataque", label: "Ataque", beats: "astucia" },
  { id: "defensa", label: "Defensa", beats: "ataque" },
  { id: "astucia", label: "Astucia", beats: "defensa" },
];
export const TRIANGLE_TEXT = "Ataque vence a astucia, astucia a defensa y defensa a ataque.";
export const WOUND_RULE_TEXT =
  "Cada ronda, la facción con menor puntuación solo recibe una herida si queda por debajo del 85 % de la mejor; si no, nadie sale herido.";
export const EVENT_TIMING_TEXT =
  "La Última Luz llega cuando la temporada lleva 7 días en fase de colapso: en el cierre diario de las 23:59 (UTC) se elige un campeón por facción y se abre el primer duelo. Cada día cae una región del valle y la final se libra en las Cumbres Heladas.";
export const MAX_CHISPAS_PER_VOTE = 50;

const REASON_TEXT = {
  below_gap: (w) => `${w} quedó por debajo del 85 % de la mejor puntuación y recibe una herida.`,
  within_gap: () => "La peor puntuación quedó dentro del margen del 85 %: nadie resulta herido.",
  final_round: () => "Duelo final en la Arena: no hay heridas, la puntuación acumulada decide al vencedor.",
  no_contenders: () => "Ninguna facción con campeón vivo votó: la ronda se cerró sin heridas.",
};

const SEAL_NAMES = {
  abundancia: "Sello de la Abundancia",
  muralla: "Sello de la Muralla",
  oro: "Sello del Oro",
  eco: "Sello del Eco",
  cuna: "Sello de la Cuna",
};

export const tacticLabel = (id) => TACTICS.find((t) => t.id === id)?.label ?? "Sin táctica";
export const sealLabel = (id) => SEAL_NAMES[id] ?? id;

/** Name of a faction slug using the champions list (falls back to the slug). */
export function factionName(state, slug) {
  if (!slug) return "";
  return state?.champions?.find((c) => c.faction_slug === slug)?.faction_name ?? slug;
}

/** Spanish sentence explaining the last round's outcome. */
export function reasonText(state, lastRound) {
  if (!lastRound) return "";
  const make = REASON_TEXT[lastRound.reason];
  if (!make) return "Ronda resuelta.";
  let text = make(factionName(state, lastRound.wounded_faction_slug) || "La facción peor puntuada");
  if (lastRound.eliminated_faction_slug) {
    text += ` Su campeón suma su tercera herida y cae: ${factionName(state, lastRound.eliminated_faction_slug)} queda fuera.`;
  }
  return text;
}

/** One boolean per heart: true = life left. */
export function hearts(wounds, maxWounds = 3) {
  const max = Math.max(0, maxWounds | 0), w = Math.min(max, Math.max(0, wounds | 0));
  return Array.from({ length: max }, (_, i) => i < max - w);
}

/** "2 h 05 min", "4 min 09 s", "12 s" or null once closed. */
export function formatCountdown(ms) {
  if (!Number.isFinite(ms) || ms <= 0) return null;
  const s = Math.floor(ms / 1000), d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const pad = (n) => String(n).padStart(2, "0");
  if (d > 0) return `${d} d ${h} h`;
  if (h > 0) return `${h} h ${pad(m)} min`;
  if (m > 0) return `${m} min ${pad(sec)} s`;
  return `${sec} s`;
}

/** Vote weight for a given Chispas spend (1 + spend, spend clamped to 0..50). */
export function voteWeight(chispas) {
  return 1 + clampSpend(chispas, MAX_CHISPAS_PER_VOTE);
}
export function clampSpend(value, available) {
  const n = Math.floor(Number(value));
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.min(n, MAX_CHISPAS_PER_VOTE, Math.max(0, available | 0));
}

/** Percent shares of my faction's tactic totals. */
export function tacticShares(totals) {
  const t = { ataque: totals?.ataque ?? 0, defensa: totals?.defensa ?? 0, astucia: totals?.astucia ?? 0 };
  const sum = t.ataque + t.defensa + t.astucia;
  return TACTICS.map(({ id, label }) => ({ id, label, weight: t[id], pct: sum ? Math.round((100 * t[id]) / sum) : 0 }));
}

/** How the map should look for a given state. */
export function viewerConfig(state, worldPhase) {
  const status = state?.status ?? "none";
  const inEvent = status !== "none";
  return {
    phase: inEvent ? "colapso" : worldPhase || "construccion",
    fallen: inEvent ? [...(state.fallen_zones ?? [])] : [],
    focus: status === "active" ? state.current_zone ?? null : inEvent ? "cumbres" : null,
  };
}

/** Which page sections are visible. */
export function sections(state) {
  const status = state?.status ?? "none";
  return {
    intro: status === "none",
    sponsor: status === "none",
    champions: status !== "none" && (state.champions?.length ?? 0) > 0,
    duel: status === "active" && !!state.current_duel,
    lastRound: status !== "none" && !!state.last_round,
    winner: (status === "finished" || status === "sealed") && !!state.winner,
    sealPicker: status === "finished" && !!state.seal?.can_choose,
    sealWaiting: status === "finished" && !state.seal?.can_choose,
    sealed: status === "sealed",
  };
}

/** Short status line for the header. */
export function statusLine(state) {
  switch (state?.status) {
    case "active": return `Ronda ${state.round_number} de ${state.total_rounds} · ${zoneName(state, state.current_zone)}`;
    case "finished": return "La Última Luz se ha apagado: falta elegir el sello";
    case "sealed": return "Temporada sellada";
    default: return "Aún no ha comenzado";
  }
}
export function zoneName(state, id) {
  return state?.zones?.find((z) => z.id === id)?.name ?? id ?? "";
}

/** Friendly prefix for API errors by HTTP status. */
export function apiErrorText(err) {
  const msg = err?.message || "Error inesperado";
  switch (err?.status) {
    case 401: return "Tu sesión ha caducado. Vuelve a entrar.";
    case 409: return `No se pudo: ${msg}`;
    case 429: return "Demasiadas peticiones seguidas. Espera un momento y vuelve a intentarlo.";
    default: return msg;
  }
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const isUuid = (s) => UUID_RE.test(String(s ?? "").trim());
