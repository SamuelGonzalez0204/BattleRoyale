import { describe, expect, it } from 'vitest';
import {
  GROWTH_BASE, STAT_KEYS, growthThreshold, moralLight, normalizeStats, placeThreshold, sortByThreshold, visibleCount,
} from './growth.js';

describe('normalizeStats', () => {
  it('returns a full world when there are no stats', () => {
    expect(normalizeStats(null)).toEqual({ poblacion: 100, comida: 100, moral: 100, defensa: 100, oro: 100 });
  });

  it('clamps to 0..100 and fills missing or invalid values with 100', () => {
    expect(normalizeStats({ poblacion: -5, comida: 140, moral: 'x', defensa: 42.4 })).toEqual({
      poblacion: 0, comida: 100, moral: 100, defensa: 42.4, oro: 100,
    });
  });

  it('knows the five world stats', () => {
    expect(STAT_KEYS).toEqual(['poblacion', 'comida', 'moral', 'defensa', 'oro']);
  });
});

describe('growthThreshold', () => {
  it('keeps the base share always built (threshold 0)', () => {
    expect(growthThreshold(0, 0.2)).toBe(0);
    expect(growthThreshold(0.19, 0.2)).toBe(0);
  });

  it('spreads the rest linearly over 0..100', () => {
    expect(growthThreshold(0.6, 0.2)).toBeCloseTo(50);
    expect(growthThreshold(0.999999, 0.2)).toBeLessThan(100);
  });

  it('clamps out-of-range draws', () => {
    expect(growthThreshold(-1, 0.1)).toBe(0);
    expect(growthThreshold(2, 0.1)).toBe(100);
  });
});

describe('placeThreshold', () => {
  it('is deterministic for the same stat and place', () => {
    expect(placeThreshold('poblacion', 12.3, -40)).toBe(placeThreshold('poblacion', 12.3, -40));
  });

  it('differs between stats at the same place', () => {
    const ts = STAT_KEYS.map((s) => placeThreshold(s, 30, 30));
    expect(new Set(ts).size).toBeGreaterThan(1);
  });

  it('stays in 0..100 and roughly honours the base share', () => {
    let zeros = 0;
    for (let i = 0; i < 2000; i++) {
      const t = placeThreshold('poblacion', (i % 50) * 3.7, Math.floor(i / 50) * 4.1);
      expect(t).toBeGreaterThanOrEqual(0); expect(t).toBeLessThan(100);
      if (t === 0) zeros++;
    }
    expect(zeros / 2000).toBeGreaterThan(GROWTH_BASE.poblacion - 0.06);
    expect(zeros / 2000).toBeLessThan(GROWTH_BASE.poblacion + 0.06);
  });
});

describe('sortByThreshold + visibleCount', () => {
  it('orders indices by threshold (stable for ties)', () => {
    expect(sortByThreshold([50, 0, 20, 0])).toEqual([1, 3, 2, 0]);
  });

  it('counts the instances built at a value (t <= value)', () => {
    const sorted = [0, 0, 10, 50, 50, 99];
    expect(visibleCount(sorted, 0)).toBe(2);
    expect(visibleCount(sorted, 49)).toBe(3);
    expect(visibleCount(sorted, 50)).toBe(5);
    expect(visibleCount(sorted, 100)).toBe(6);
    expect(visibleCount([], 70)).toBe(0);
  });
});

describe('moralLight', () => {
  it('dims lanterns and the warm fill at low moral', () => {
    const low = moralLight(0), high = moralLight(100);
    expect(low.lantern).toBeLessThan(high.lantern);
    expect(low.warmth).toBe(0);
    expect(high.warmth).toBeGreaterThan(0);
  });

  it('is monotonic', () => {
    expect(moralLight(30).lantern).toBeLessThan(moralLight(60).lantern);
  });
});
