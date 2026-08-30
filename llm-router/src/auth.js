/**
 * Request authentication and identifier hygiene.
 */

/**
 * Constant-time string comparison.
 *
 * `a === b` on a secret returns as soon as it finds a differing byte, so the
 * time it takes leaks how many leading bytes were correct. That is enough to
 * recover a secret byte-by-byte across enough requests. Comparing digests of
 * equal length in constant time removes the signal.
 */
export async function secretsMatch(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  const encode = (s) => new TextEncoder().encode(s);
  const [da, db] = await Promise.all([
    crypto.subtle.digest('SHA-256', encode(a)),
    crypto.subtle.digest('SHA-256', encode(b)),
  ]);
  const x = new Uint8Array(da);
  const y = new Uint8Array(db);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

/**
 * Sanitize any caller-supplied identifier before it is used as a storage key
 * or rendered anywhere.
 *
 * The chain this closes: a caller POSTs `{ agent: "<img src=x onerror=...>" }`.
 * That string is concatenated into a metrics key. An admin dashboard later
 * lists those keys. If the key reached the page as markup, the caller has
 * stored XSS in an operator's browser — a low-privilege input reaching a
 * high-privilege viewer.
 *
 * Escaping at render time is the usual answer, but it depends on every future
 * render site remembering. Constraining the value at the boundary means there
 * is nothing dangerous stored to begin with.
 */
export function sanitizeId(input, maxLength = 64) {
  if (typeof input !== 'string') return '';
  return input.toLowerCase().replace(/[^a-z0-9_-]/g, '').slice(0, maxLength);
}

/** Escape text for safe interpolation into HTML. */
export function escapeHtml(input) {
  return String(input).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}
