// Pure mapping for the public lore page: regions + POIs from map-data.json and GET /api/lore. No DOM.
import { placeHref } from '../map/hash.js';
import { STAT_KEYS } from '../map/growth.js';
import { sealLabel } from '../br/view.js';
import { STAT_NAMES as STAT_LABELS } from '../ui/stats.js';
import { atHandle } from '../ranking/view.js';

export { STAT_LABELS };
const PHASES = { construccion: 'Construcción', conflicto: 'Conflicto', convergencia: 'Convergencia', colapso: 'Colapso' };
const KINDS = { hito: 'Hito', lugar: 'Lugar', misterio: 'Misterio', paso: 'Paso disputado' };
const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

export const phaseLabel = (p) => PHASES[p] ?? p;

/** 'YYYY-MM-DD' to '3 nov 2026' (parsed by hand: no timezone shift). */
export function dateLabel(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso));
  if (!m) return String(iso);
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
}

/** Effects dict to signed chips in stat order; zero deltas are dropped. */
export function effectChips(effects) {
  if (!effects) return [];
  const keys = [...STAT_KEYS.filter((k) => k in effects), ...Object.keys(effects).filter((k) => !STAT_KEYS.includes(k))];
  return keys
    .filter((k) => Number(effects[k]))
    .map((k) => {
      const d = Number(effects[k]);
      return { stat: k, text: `${d > 0 ? '+' : '−'}${Math.abs(d)} ${STAT_LABELS[k] ?? k}`, positive: d > 0 };
    });
}

/** Closed decisions, newest first, ready for the "Crónica" timeline. */
export function timelineItems(decisions = []) {
  return [...decisions]
    .sort((a, b) => String(b.date).localeCompare(String(a.date)))
    .map((d, i) => ({
      key: `${d.date}-${i}`,
      date: d.date,
      dateLabel: dateLabel(d.date),
      seasonNumber: d.season_number,
      regionName: d.region_name ?? 'Sin lugar',
      mapHref: d.region ? placeHref(d.region) : null,
      question: d.question,
      outcome: d.winner_option ? `Ganó «${d.winner_option}»` : 'Sin votos: no cambió nada.',
      effects: effectChips(d.effects_applied),
    }));
}

function regionFactionName(DATA, faction) {
  if (faction === 'disputada') return 'Tierra disputada';
  return DATA.factions?.[faction]?.name ?? 'Sin dueño';
}

/** The seven regions with their summary, story seed and POIs. */
export function regionCards(DATA) {
  return (DATA?.regions ?? []).map((r) => ({
    id: r.id,
    name: r.name,
    faction: r.faction,
    factionName: regionFactionName(DATA, r.faction),
    statLabel: STAT_LABELS[r.stat] ?? r.stat,
    summary: r.summary,
    story: r.story,
    href: placeHref(r.id),
    pois: (DATA.pois ?? []).filter((p) => p.region === r.id).map((p) => ({
      id: p.id, name: p.name, kindLabel: KINDS[p.kind] ?? p.kind, text: p.text, href: placeHref(p.id),
    })),
  }));
}

export const factionRows = (factions = []) => [...factions].sort((a, b) => b.influence_pct - a.influence_pct);

export function winnerRows(brs = []) {
  return brs.map((b) => ({
    season: `Temporada ${b.season_number}`,
    faction: b.winner_faction_name ?? 'Sin ganador',
    factionSlug: b.winner_faction_slug ?? null,
    champion: b.champion_handle ? atHandle(b.champion_handle) : '—',
    seal: b.seal ? sealLabel(b.seal) : 'Sin sello',
  }));
}
