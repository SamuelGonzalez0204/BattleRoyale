// Shared site navigation: pure link list + a tiny mount helper.
import { apiFetch, getToken } from '../api.js';

const SECTIONS = [
  { id: 'poblado', href: '/poblado.html', label: 'Poblado' },
  { id: 'mapa', href: '/mapa.html', label: 'Mapa' },
  { id: 'battle-royale', href: '/battle-royale.html', label: 'La Última Luz' },
  { id: 'ranking', href: '/ranking.html', label: 'Ranking' },
  { id: 'lore', href: '/lore.html', label: 'Lore' },
];

/**
 * @param {string} current  id of the page being shown
 * @param {{loggedIn?: boolean, isAdmin?: boolean}} [opts]
 * @returns {{id: string, href: string, label: string, current: boolean}[]}
 */
export function navLinks(current, { loggedIn = true, isAdmin = false } = {}) {
  const extra = !loggedIn
    ? [{ id: 'entrar', href: '/index.html', label: 'Entrar' }]
    : isAdmin ? [{ id: 'admin', href: '/admin.html', label: 'Admin' }] : [];
  return [...SECTIONS, ...extra].map((l) => ({ ...l, current: l.id === current }));
}

function render(el, links) {
  el.replaceChildren(...links.map((l) => {
    const a = document.createElement('a');
    a.href = l.href; a.textContent = l.label;
    if (l.current) a.setAttribute('aria-current', 'page');
    return a;
  }));
}

/**
 * Renders the nav into `el` (a <nav>). Pass `me` when the page already loaded /api/users/me;
 * otherwise the admin link is resolved in the background when there is a session.
 */
export function mountNav(el, current, me) {
  if (!el) return;
  el.classList.add('site-nav');
  if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', 'Secciones');
  const loggedIn = Boolean(getToken());
  render(el, navLinks(current, { loggedIn, isAdmin: Boolean(me?.is_admin) }));
  if (me || !loggedIn) return;
  apiFetch('/api/users/me')
    .then((u) => { if (u?.is_admin) render(el, navLinks(current, { loggedIn, isAdmin: true })); })
    .catch(() => {});
}
