#!/usr/bin/env node
/**
 * Convert AIXMOS-GUIDE.md to AIXMOS-GUIDE.html with print-ready CSS.
 * Tiny ad-hoc Markdown parser — handles the subset the guide uses.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const MD = path.join(ROOT, 'AIXMOS-GUIDE.md');
const HTML = path.join(ROOT, 'AIXMOS-GUIDE.html');

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function inline(s) {
  s = s.replace(/`([^`]+)`/g, (_, c) => `<code>${esc(c)}</code>`);
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  return s;
}

function render(md) {
  const lines = md.split(/\r?\n/);
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    if (/^```/.test(line)) {
      const lang = line.slice(3).trim();
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
      i++;
      out.push(`<pre class="code${lang ? ' lang-' + lang : ''}"><code>${esc(buf.join('\n'))}</code></pre>`);
      continue;
    }

    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { out.push(`<h${h[1].length}>${inline(esc(h[2]))}</h${h[1].length}>`); i++; continue; }

    if (/^---\s*$/.test(line)) { out.push('<hr/>'); i++; continue; }

    // Tables: header | --- | rows
    if (/^\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
      const headers = line.split('|').slice(1, -1).map(s => s.trim());
      i += 2;
      const rows = [];
      while (i < lines.length && /^\|.*\|\s*$/.test(lines[i])) {
        rows.push(lines[i].split('|').slice(1, -1).map(s => s.trim()));
        i++;
      }
      const head = headers.map(h => `<th>${inline(esc(h))}</th>`).join('');
      const body = rows.map(r => `<tr>${r.map(c => `<td>${inline(esc(c))}</td>`).join('')}</tr>`).join('');
      out.push(`<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`);
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(`<li>${inline(esc(lines[i].replace(/^[-*]\s+/, '')))}</li>`);
        i++;
      }
      out.push(`<ul>${items.join('')}</ul>`);
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(`<li>${inline(esc(lines[i].replace(/^\d+\.\s+/, '')))}</li>`);
        i++;
      }
      out.push(`<ol>${items.join('')}</ol>`);
      continue;
    }

    if (/^>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^>\s?/, ''));
        i++;
      }
      out.push(`<blockquote>${inline(esc(buf.join(' ')))}</blockquote>`);
      continue;
    }

    if (line.trim() === '') { i++; continue; }

    const buf = [line];
    i++;
    while (i < lines.length && lines[i].trim() !== '' && !/^(#|```|---|\||[-*]\s|>|\d+\.\s)/.test(lines[i])) {
      buf.push(lines[i]); i++;
    }
    out.push(`<p>${inline(esc(buf.join(' ')))}</p>`);
  }
  return out.join('\n');
}

const CSS = `
  @page { size: Letter; margin: 0.75in 0.85in; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body {
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
    font-size: 10.5pt; line-height: 1.45; color: #1a1a1a;
    max-width: 7in; margin: 0 auto;
  }
  h1 { font-size: 22pt; color: #0a2540; margin: 1.5em 0 0.4em; border-bottom: 2px solid #0a2540; padding-bottom: 0.2em; page-break-before: auto; }
  h1:first-of-type { page-break-before: avoid; margin-top: 0; }
  h2 { font-size: 15pt; color: #0a4d7a; margin: 1.6em 0 0.4em; border-bottom: 1px solid #cdd5e0; padding-bottom: 0.15em; page-break-after: avoid; }
  h3 { font-size: 12pt; color: #0a4d7a; margin: 1.3em 0 0.3em; page-break-after: avoid; }
  h4 { font-size: 11pt; color: #333; margin: 1.0em 0 0.2em; }
  p  { margin: 0.5em 0; }
  ul, ol { margin: 0.4em 0 0.6em 1.2em; padding: 0; }
  li { margin: 0.15em 0; }
  code { font-family: "Cascadia Code", Consolas, monospace; font-size: 9.5pt; background: #f1f3f7; padding: 1px 4px; border-radius: 3px; }
  pre.code { background: #0a2540; color: #e6edf3; padding: 0.7em 0.9em; border-radius: 4px; overflow-x: auto; font-size: 9pt; line-height: 1.4; page-break-inside: avoid; }
  pre.code code { background: transparent; color: inherit; padding: 0; }
  table { width: 100%; border-collapse: collapse; margin: 0.6em 0; font-size: 9.5pt; page-break-inside: avoid; }
  th { background: #0a2540; color: white; text-align: left; padding: 0.4em 0.6em; }
  td { border-bottom: 1px solid #e0e4ec; padding: 0.35em 0.6em; vertical-align: top; }
  tr:nth-child(even) td { background: #f7f9fc; }
  blockquote { border-left: 3px solid #0a4d7a; padding: 0.3em 0.9em; margin: 0.6em 0; background: #f5f7fb; color: #333; font-style: italic; }
  hr { border: none; border-top: 1px solid #cdd5e0; margin: 1.2em 0; }
  a { color: #0a4d7a; text-decoration: none; }
`;

const md = fs.readFileSync(MD, 'utf8');
const body = render(md);
const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>AIXMOS Agent Network — User Guide</title>
<style>${CSS}</style>
</head><body>
${body}
</body></html>`;

fs.writeFileSync(HTML, html, 'utf8');
console.log(`wrote ${HTML} (${(html.length / 1024).toFixed(1)} KB)`);
