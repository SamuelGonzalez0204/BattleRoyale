import { describe, expect, it } from 'vitest';
import { atHandle, PAGE_SIZE, SCOPES, myPositionText, pageInfo, rankingPath, rankingRows, roleLabel, valueLabel } from './view.js';

const FACTIONS = [
  { slug: 'gremio', name: 'Gremio del Comercio', color: '#d9a94f' },
  { slug: 'orden', name: 'Orden de la Muralla', color: '#7c92ad' },
];

describe('rankingPath', () => {
  it('builds the query for a scope and page', () => {
    expect(rankingPath({ scope: 'chispas', page: 0 })).toBe(`/api/ranking?scope=chispas&limit=${PAGE_SIZE}&offset=0`);
    expect(rankingPath({ scope: 'votos', faction: 'orden', page: 2 })).toBe(`/api/ranking?scope=votos&limit=${PAGE_SIZE}&offset=${PAGE_SIZE * 2}&faction=orden`);
  });

  it('falls back to chispas for unknown scopes and ignores bad pages', () => {
    expect(rankingPath({ scope: 'oro', page: -3 })).toBe(`/api/ranking?scope=chispas&limit=${PAGE_SIZE}&offset=0`);
  });

  it('knows both scopes', () => {
    expect(SCOPES.map((s) => s.id)).toEqual(['chispas', 'votos']);
  });
});

describe('rankingRows', () => {
  it('maps items to display rows and marks me', () => {
    const rows = rankingRows({ items: [
      { rank: 1, user_id: 'u1', handle: 'ana', faction_slug: 'gremio', role: 'mercader', value: 1200 },
      { rank: 2, user_id: 'u2', handle: 'bo', faction_slug: null, role: null, value: 5 },
    ] }, { scope: 'chispas', meId: 'u2', factions: FACTIONS });
    expect(rows[0]).toEqual({ rank: 1, handle: '@ana', factionSlug: 'gremio', factionName: 'Gremio del Comercio', factionColor: '#d9a94f', role: 'Mercader', value: '1.200', isMe: false });
    expect(rows[1]).toMatchObject({ handle: '@bo', factionName: 'Sin facción', factionColor: null, role: '—', isMe: true });
  });

  it('returns an empty list without items', () => {
    expect(rankingRows(null, {})).toEqual([]);
  });
});

describe('pageInfo', () => {
  it('computes pages and ranges', () => {
    expect(pageInfo({ total: 45, limit: 20, offset: 20, items: new Array(20) })).toEqual({ page: 1, pages: 3, hasPrev: true, hasNext: true, from: 21, to: 40, total: 45 });
    expect(pageInfo({ total: 0, limit: 20, offset: 0, items: [] })).toEqual({ page: 0, pages: 1, hasPrev: false, hasNext: false, from: 0, to: 0, total: 0 });
  });
});

describe('labels', () => {
  it('prefixes handles with a single @', () => {
    expect(atHandle('ana')).toBe('@ana');
    expect(atHandle('@@ana')).toBe('@ana');
  });

  it('formats values per scope', () => {
    expect(valueLabel('chispas', 1)).toBe('1 Chispa');
    expect(valueLabel('chispas', 30)).toBe('30 Chispas');
    expect(valueLabel('votos', 1)).toBe('1 voto');
    expect(valueLabel('votos', 2500)).toBe('2.500 votos');
  });

  it('names roles', () => {
    expect(roleLabel('cronista')).toBe('Cronista');
    expect(roleLabel(null)).toBe('—');
  });

  it('describes my position', () => {
    expect(myPositionText({ rank: 7, value: 40 }, 'chispas')).toBe('Puesto 7 · 40 Chispas');
    expect(myPositionText(null, 'votos')).toBe('Aún no apareces en este ranking.');
  });
});
