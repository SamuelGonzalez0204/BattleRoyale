import { describe, expect, it } from 'vitest';
import { navLinks } from './nav.js';

describe('navLinks', () => {
  it('lists the site sections and marks the current one', () => {
    const links = navLinks('ranking', { loggedIn: true });
    expect(links.map((l) => l.label)).toEqual(['Poblado', 'Mapa', 'La Última Luz', 'Ranking', 'Lore']);
    expect(links.filter((l) => l.current).map((l) => l.id)).toEqual(['ranking']);
  });

  it('adds the admin link only for admins', () => {
    expect(navLinks('poblado', { loggedIn: true, isAdmin: true }).at(-1)).toMatchObject({ id: 'admin', href: '/admin.html' });
    expect(navLinks('poblado', { loggedIn: true }).some((l) => l.id === 'admin')).toBe(false);
  });

  it('offers to sign in when there is no session', () => {
    const links = navLinks('lore', { loggedIn: false });
    expect(links.at(-1)).toMatchObject({ id: 'entrar', href: '/index.html' });
    expect(links.some((l) => l.id === 'admin')).toBe(false);
  });
});
