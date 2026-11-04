import { describe, expect, it } from 'vitest';
import { parsePlaceHash, placeHref } from './hash.js';

describe('parsePlaceHash', () => {
  it('reads a plain region or POI id', () => {
    expect(parsePlaceHash('#cementerio')).toBe('cementerio');
    expect(parsePlaceHash('#barco-fantasma')).toBe('barco-fantasma');
    expect(parsePlaceHash('torre-alba')).toBe('torre-alba');
  });

  it('decodes and lower-cases', () => {
    expect(parsePlaceHash('#Fuente')).toBe('fuente');
    expect(parsePlaceHash('#%66uente')).toBe('fuente');
  });

  it('rejects anything that is not ascii words joined by hyphens', () => {
    for (const h of ['', '#', '#-a', '#a-', '#a--b', '#a b', '#<img>', '#ñu', '#%E0%A4%A', '#a/b']) expect(parsePlaceHash(h)).toBeNull();
    expect(parsePlaceHash(undefined)).toBeNull();
    expect(parsePlaceHash('#' + 'a'.repeat(65))).toBeNull();
  });

  it('only accepts known ids when a list is given', () => {
    expect(parsePlaceHash('#plaza', ['plaza', 'fuente'])).toBe('plaza');
    expect(parsePlaceHash('#nada', ['plaza'])).toBeNull();
  });
});

describe('placeHref', () => {
  it('links to the map page', () => {
    expect(placeHref('fuente')).toBe('/mapa.html#fuente');
  });
});
