// Pure mapping for the ranking page: query paths, rows and pagination. No DOM, no fetch.

export const PAGE_SIZE = 20;
export const SCOPES = [
  { id: 'chispas', label: 'Chispas' },
  { id: 'votos', label: 'Votos de la temporada' },
];
const ROLES = { mercader: 'Mercader', guardia: 'Guardia', cronista: 'Cronista', explorador: 'Explorador' };
/** Thousands with a dot, always (es-ES skips grouping for 4 digits). */
export const fmt = (n) => String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');

/** @param {{scope?: string, faction?: string|null, page?: number}} q */
export function rankingPath({ scope, faction, page } = {}) {
  const s = SCOPES.some((x) => x.id === scope) ? scope : 'chispas';
  const p = Number.isInteger(page) && page > 0 ? page : 0;
  const params = new URLSearchParams({ scope: s, limit: String(PAGE_SIZE), offset: String(p * PAGE_SIZE) });
  if (faction) params.set('faction', faction);
  return `/api/ranking?${params}`;
}

/** '@ana' or 'ana' -> '@ana' (some handles are stored with the @). */
export const atHandle = (h) => `@${String(h ?? '').replace(/^@+/, '')}`;

export const roleLabel = (role) => ROLES[role] ?? '—';

export function valueLabel(scope, value) {
  const n = Number(value || 0);
  if (scope === 'votos') return `${fmt(n)} ${n === 1 ? 'voto' : 'votos'}`;
  return `${fmt(n)} ${n === 1 ? 'Chispa' : 'Chispas'}`;
}

/**
 * @param {{items?: object[]} | null} data  GET /api/ranking response
 * @param {{scope?: string, meId?: string, factions?: {slug: string, name: string, color: string}[]}} ctx
 */
export function rankingRows(data, { meId, factions = [] } = {}) {
  const bySlug = new Map(factions.map((f) => [f.slug, f]));
  return (data?.items ?? []).map((it) => {
    const f = bySlug.get(it.faction_slug);
    return {
      rank: it.rank,
      handle: atHandle(it.handle),
      factionSlug: it.faction_slug ?? null,
      factionName: f?.name ?? (it.faction_slug ? it.faction_slug : 'Sin facción'),
      factionColor: f?.color ?? null,
      role: roleLabel(it.role),
      value: fmt(it.value),
      isMe: Boolean(meId) && it.user_id === meId,
    };
  });
}

export function pageInfo({ total = 0, limit = PAGE_SIZE, offset = 0, items = [] } = {}) {
  const size = limit || PAGE_SIZE;
  const pages = Math.max(1, Math.ceil(total / size));
  const page = Math.floor(offset / size);
  return {
    page, pages, hasPrev: page > 0, hasNext: offset + items.length < total,
    from: items.length ? offset + 1 : 0, to: offset + items.length, total,
  };
}

export function myPositionText(me, scope) {
  if (!me) return 'Aún no apareces en este ranking.';
  return `Puesto ${me.rank} · ${valueLabel(scope, me.value)}`;
}
