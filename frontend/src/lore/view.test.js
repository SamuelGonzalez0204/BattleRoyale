import { describe, expect, it } from 'vitest';
import { dateLabel, effectChips, factionRows, phaseLabel, regionCards, timelineItems, winnerRows } from './view.js';

const DATA = {
  factions: { gremio: { name: 'Gremio del Comercio', color: '#d9a94f' }, neutral: { name: 'Sin dueño', color: '#c9c2b0' } },
  regions: [
    { id: 'plaza', name: 'Plaza del Ciclo', faction: 'neutral', stat: 'moral', summary: 'S', story: 'H' },
    { id: 'campos', name: 'Campos y Molinos', faction: 'disputada', stat: 'comida', summary: 'S2', story: 'H2' },
  ],
  pois: [
    { id: 'fuente', name: 'Fuente del Ciclo', region: 'plaza', kind: 'hito', text: 'T' },
    { id: 'puente-molino', name: 'Puente del Molino', region: 'campos', kind: 'paso', text: 'T2' },
  ],
};

describe('effectChips', () => {
  it('orders by stat, drops zeros and signs the deltas', () => {
    expect(effectChips({ oro: -3, comida: 5, moral: 0 })).toEqual([
      { stat: 'comida', text: '+5 Comida', positive: true },
      { stat: 'oro', text: '−3 Oro', positive: false },
    ]);
  });

  it('handles empty effects', () => {
    expect(effectChips(null)).toEqual([]);
  });
});

describe('dateLabel', () => {
  it('formats ISO days without timezone drift', () => {
    expect(dateLabel('2026-11-03')).toBe('3 nov 2026');
    expect(dateLabel('bad')).toBe('bad');
  });
});

describe('timelineItems', () => {
  it('sorts newest first and describes the outcome', () => {
    const items = timelineItems([
      { date: '2026-11-01', season_number: 1, question: 'Q1', region: 'plaza', region_name: 'Plaza del Ciclo', winner: 'a', winner_option: 'Sí', effects_applied: { moral: 4 } },
      { date: '2026-11-02', season_number: 1, question: 'Q2', region: null, region_name: null, winner: null, winner_option: null, effects_applied: {} },
    ]);
    expect(items.map((i) => i.question)).toEqual(['Q2', 'Q1']);
    expect(items[0]).toMatchObject({ regionName: 'Sin lugar', mapHref: null, outcome: 'Sin votos: no cambió nada.', effects: [] });
    expect(items[1]).toMatchObject({ dateLabel: '1 nov 2026', regionName: 'Plaza del Ciclo', mapHref: '/mapa.html#plaza', outcome: 'Ganó «Sí»' });
    expect(items[1].effects[0].text).toBe('+4 Moral');
  });
});

describe('regionCards', () => {
  it('groups POIs under their region with map links', () => {
    const cards = regionCards(DATA);
    expect(cards[0]).toMatchObject({ id: 'plaza', factionName: 'Sin dueño', statLabel: 'Moral', href: '/mapa.html#plaza' });
    expect(cards[0].pois).toEqual([{ id: 'fuente', name: 'Fuente del Ciclo', kindLabel: 'Hito', text: 'T', href: '/mapa.html#fuente' }]);
    expect(cards[1]).toMatchObject({ factionName: 'Tierra disputada' });
    expect(cards[1].pois[0].kindLabel).toBe('Paso disputado');
  });
});

describe('factionRows + winnerRows + phaseLabel', () => {
  it('sorts factions by influence', () => {
    const rows = factionRows([{ slug: 'a', influence_pct: 10 }, { slug: 'b', influence_pct: 60 }]);
    expect(rows.map((r) => r.slug)).toEqual(['b', 'a']);
  });

  it('describes past winners', () => {
    expect(winnerRows([{ season_number: 2, winner_faction_slug: 'orden', winner_faction_name: 'Orden', champion_handle: 'kai', seal: 'muralla' }]))
      .toEqual([{ season: 'Temporada 2', faction: 'Orden', factionSlug: 'orden', champion: '@kai', seal: 'Sello de la Muralla' }]);
    expect(winnerRows([{ season_number: 1, winner_faction_slug: null, winner_faction_name: null, champion_handle: null, seal: null }])[0])
      .toMatchObject({ faction: 'Sin ganador', champion: '—', seal: 'Sin sello' });
  });

  it('names phases', () => {
    expect(phaseLabel('convergencia')).toBe('Convergencia');
    expect(phaseLabel('rara')).toBe('rara');
  });
});
