// World stat chips (icon + value + label). Pure: returns markup.
import { STAT_KEYS } from '../map/growth.js';

const ICONS = {
  poblacion: '<path d="M2 8L8 2L14 8V14H2Z" fill="none" stroke="currentColor" stroke-width="1.3"></path>',
  comida:
    '<line x1="8" y1="14" x2="8" y2="3" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="5" x2="4" y2="3" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="5" x2="12" y2="3" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="9" x2="4.5" y2="7" stroke="currentColor" stroke-width="1.2"></line>' +
    '<line x1="8" y1="9" x2="11.5" y2="7" stroke="currentColor" stroke-width="1.2"></line>',
  moral:
    '<path d="M8 13.5C3.5 10 1.8 7 3.3 4.8C4.4 3.2 6.6 3.4 8 5.2C9.4 3.4 11.6 3.2 12.7 4.8C14.2 7 12.5 10 8 13.5Z" fill="none" stroke="currentColor" stroke-width="1.2"></path>',
  defensa:
    '<path d="M8 1.5L13.5 3.5V8C13.5 11 11 13.3 8 14.3C5 13.3 2.5 11 2.5 8V3.5Z" fill="none" stroke="currentColor" stroke-width="1.2"></path>',
  oro: '<circle cx="8" cy="8" r="5.5" fill="none" stroke="#e0a73c" stroke-width="1.2"></circle><circle cx="8" cy="8" r="3" fill="none" stroke="#e0a73c" stroke-width="1"></circle>',
};

export const STAT_NAMES = { poblacion: 'Población', comida: 'Comida', moral: 'Moral', defensa: 'Defensa', oro: 'Oro' };

/** @param {Record<string, number>} stats */
export function statChipsHtml(stats) {
  return STAT_KEYS.map((key) => `
    <div class="stat-chip">
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">${ICONS[key]}</svg>
      <span style="font-size:13px;font-weight:600">${Number(stats?.[key]) || 0}%</span>
      <span class="muted" style="font-size:12px">${STAT_NAMES[key]}</span>
    </div>`).join('');
}
