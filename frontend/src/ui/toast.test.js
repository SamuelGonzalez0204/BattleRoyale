import { describe, expect, it } from 'vitest';
import { createToastQueue, TOAST_MS } from './toast.js';

describe('createToastQueue', () => {
  it('adds toasts with incremental ids and a variant', () => {
    const q = createToastQueue();
    const a = q.push('Hola');
    const b = q.push('Fallo', 'error');
    expect(a).toMatchObject({ id: 1, message: 'Hola', variant: 'info' });
    expect(b).toMatchObject({ id: 2, variant: 'error' });
    expect(q.list().map((t) => t.id)).toEqual([1, 2]);
  });

  it('falls back to info for unknown variants', () => {
    expect(createToastQueue().push('x', 'rare').variant).toBe('info');
  });

  it('gives errors more time than other toasts', () => {
    const q = createToastQueue();
    expect(q.push('e', 'error').timeout).toBeGreaterThan(q.push('s', 'success').timeout);
    expect(q.push('s', 'success').timeout).toBe(TOAST_MS);
  });

  it('drops the oldest when over the limit', () => {
    const q = createToastQueue({ max: 2 });
    q.push('1'); q.push('2'); q.push('3');
    expect(q.list().map((t) => t.message)).toEqual(['2', '3']);
  });

  it('dismisses by id without mutating previous lists', () => {
    const q = createToastQueue();
    const a = q.push('a'); q.push('b');
    const before = q.list();
    expect(q.dismiss(a.id)).toBe(true);
    expect(q.list().map((t) => t.message)).toEqual(['b']);
    expect(before).toHaveLength(2);
    expect(q.dismiss(99)).toBe(false);
  });

  it('ignores empty messages', () => {
    const q = createToastQueue();
    expect(q.push('  ')).toBeNull();
    expect(q.list()).toEqual([]);
  });
});
