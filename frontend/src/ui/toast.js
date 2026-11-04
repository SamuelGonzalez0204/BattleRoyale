// Toasts: a small pure queue plus a lazy DOM renderer (aria-live polite, auto-dismiss).

export const TOAST_MS = 4500;
const ERROR_MS = 7000;
const VARIANTS = ['info', 'success', 'error'];

/**
 * @param {{max?: number}} [opts]
 * @returns {{ push(message: string, variant?: string): ({id: number, message: string, variant: string, timeout: number} | null),
 *   dismiss(id: number): boolean, list(): ReadonlyArray<object> }}
 */
export function createToastQueue({ max = 3 } = {}) {
  let items = [];
  let seq = 0;
  return {
    push(message, variant = 'info') {
      const text = String(message ?? '').trim();
      if (!text) return null;
      const v = VARIANTS.includes(variant) ? variant : 'info';
      const item = Object.freeze({ id: ++seq, message: text, variant: v, timeout: v === 'error' ? ERROR_MS : TOAST_MS });
      items = [...items, item].slice(-max);
      return item;
    },
    dismiss(id) {
      const next = items.filter((t) => t.id !== id);
      const changed = next.length !== items.length;
      items = next;
      return changed;
    },
    list: () => items,
  };
}

const queue = createToastQueue();
let region = null;

function ensureRegion() {
  if (region && document.body.contains(region)) return region;
  region = document.createElement('div');
  region.className = 'toasts';
  region.setAttribute('role', 'status');
  region.setAttribute('aria-live', 'polite');
  document.body.appendChild(region);
  return region;
}

function render() {
  const box = ensureRegion();
  const ids = new Set(queue.list().map((t) => t.id));
  box.querySelectorAll('[data-toast]').forEach((el) => { if (!ids.has(Number(el.dataset.toast))) el.remove(); });
  for (const t of queue.list()) {
    if (box.querySelector(`[data-toast="${t.id}"]`)) continue;
    const el = document.createElement('div');
    el.className = `toast toast-${t.variant}`;
    el.dataset.toast = String(t.id);
    const text = document.createElement('span');
    text.textContent = t.message;
    const close = document.createElement('button');
    close.type = 'button'; close.className = 'toast-close'; close.setAttribute('aria-label', 'Cerrar aviso'); close.textContent = '×';
    close.addEventListener('click', () => dismissToast(t.id));
    el.append(text, close);
    box.appendChild(el);
    setTimeout(() => dismissToast(t.id), t.timeout);
  }
}

export function dismissToast(id) {
  if (queue.dismiss(id)) render();
}

/** Shows a toast. `variant`: 'info' | 'success' | 'error'. */
export function toast(message, variant = 'info') {
  const item = queue.push(message, variant);
  if (item) render();
  return item;
}

export const toastError = (message) => toast(message, 'error');
export const toastSuccess = (message) => toast(message, 'success');
