import { describe, it, expect } from 'vitest';
import { sanitizeId, escapeHtml, secretsMatch } from '../src/auth.js';

describe('sanitizeId', () => {
  it('strips the payload from a stored-XSS attempt', () => {
    expect(sanitizeId('<img src=x onerror=alert(1)>')).toBe('imgsrcxonerroralert1');
  });

  it('keeps ordinary identifiers usable', () => {
    expect(sanitizeId('dispatch-agent_02')).toBe('dispatch-agent_02');
  });

  it('bounds length so a key cannot be used to exhaust storage', () => {
    expect(sanitizeId('a'.repeat(500))).toHaveLength(64);
  });

  it('returns empty for non-strings rather than coercing', () => {
    expect(sanitizeId(null)).toBe('');
    expect(sanitizeId({ toString: () => '<script>' })).toBe('');
  });
});

describe('escapeHtml', () => {
  it('neutralizes markup', () => {
    expect(escapeHtml('<b>&"\'')).toBe('&lt;b&gt;&amp;&quot;&#39;');
  });
});

describe('secretsMatch', () => {
  it('accepts an exact match', async () => {
    expect(await secretsMatch('correct-horse', 'correct-horse')).toBe(true);
  });

  it('rejects a near match', async () => {
    expect(await secretsMatch('correct-horse', 'correct-horsf')).toBe(false);
  });

  it('rejects non-strings without throwing', async () => {
    expect(await secretsMatch(undefined, 'x')).toBe(false);
  });
});
