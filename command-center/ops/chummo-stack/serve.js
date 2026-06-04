// ═══════════════════════════════════════════════════════
// AIXMOS LOCAL SERVER
// Serves the portal and landing page from the flash drive
// Run: node serve.js
// Then open: http://localhost:3000
// ═══════════════════════════════════════════════════════

const http  = require('http');
const fs    = require('fs');
const path  = require('path');
const url   = require('url');

const PORT = 3000;
const ROOT = path.resolve(__dirname);
const USB_ROOT = path.resolve(__dirname, '..');
const FILES_ROOT = path.join(USB_ROOT, 'files');
const ROOT_PREFIX = ROOT + path.sep;
const FILES_PREFIX = FILES_ROOT + path.sep;

const MIME = {
  '.html': 'text/html',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.pdf':  'application/pdf',
  '.mp4':  'video/mp4',
  '.woff2':'font/woff2',
};

/** @type {Record<string, { base: string, file: string }>} */
const ROUTES = {
  '/':           { base: ROOT, file: 'public/index.html' },
  '/apply':      { base: ROOT, file: 'public/apply.html' },
  '/apply.html': { base: ROOT, file: 'public/apply.html' },
  '/thankyou':   { base: ROOT, file: 'public/thankyou.html' },
  '/operator':   { base: ROOT, file: 'public/operator.html' },
  '/portal':     { base: ROOT, file: 'portal/index.html' },
  '/portal/':    { base: ROOT, file: 'portal/index.html' },
  '/training':   { base: FILES_ROOT, file: 'operator-training.html' },
  '/pipeline':   { base: FILES_ROOT, file: 'pipeline.html' },
};

function resolveRequestPath(pathname) {
  const route = ROUTES[pathname];
  if (route) {
    return path.join(route.base, route.file);
  }
  return path.join(ROOT, pathname.replace(/^\//, ''));
}

function isPathAllowed(absPath) {
  return absPath.startsWith(ROOT_PREFIX) || absPath.startsWith(FILES_PREFIX);
}

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url);
  const absPath = path.resolve(resolveRequestPath(parsed.pathname));

  if (!isPathAllowed(absPath)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.readFile(absPath, (err, data) => {
    if (err) {
      // Try adding .html
      fs.readFile(absPath + '.html', (err2, data2) => {
        if (err2) {
          res.writeHead(404, { 'Content-Type': 'text/html' });
          res.end(`<h2 style="font-family:sans-serif;padding:40px">404 — Not found: ${parsed.pathname}</h2>`);
          return;
        }
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(data2);
      });
      return;
    }

    const ext = path.extname(absPath).toLowerCase();
    const mime = MIME[ext] || 'application/octet-stream';
    res.writeHead(200, {
      'Content-Type': mime,
      'Cache-Control': 'no-cache',
    });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log('\n');
  console.log('  \x1b[34m\x1b[1m╔══════════════════════════════════════╗\x1b[0m');
  console.log('  \x1b[34m\x1b[1m║  AIXMOS LOCAL SERVER — RUNNING       ║\x1b[0m');
  console.log('  \x1b[34m\x1b[1m╚══════════════════════════════════════╝\x1b[0m');
  console.log('\n');
  console.log('  \x1b[36mLanding page:\x1b[0m  http://localhost:' + PORT);
  console.log('  \x1b[36mApply form:\x1b[0m    http://localhost:' + PORT + '/apply');
  console.log('  \x1b[36mPrivate portal:\x1b[0m http://localhost:' + PORT + '/portal');
  console.log('  \x1b[36mTraining:\x1b[0m      http://localhost:' + PORT + '/training');
  console.log('\n');
  console.log('  \x1b[2mPress Ctrl+C to stop\x1b[0m');
  console.log('\n');
});
