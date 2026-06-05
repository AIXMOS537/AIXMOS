#!/usr/bin/env node
/**
 * iMessage relay — runs ON THE MAC (work iPhone's Apple ID), lets the Brain
 * send texts through Messages.app. The Windows sender (lib/sender.js, channel
 * "imessage") POSTs here over Tailscale.
 *
 *   POST /send   { "to": "+15551234567", "text": "hello" }   header: X-Relay-Secret
 *   GET  /health
 *
 * Env:
 *   RELAY_PORT     default 8787
 *   RELAY_SECRET   shared secret; must match IMESSAGE_RELAY_SECRET on the sender
 *   RELAY_BIND     default 0.0.0.0 (keep it behind Tailscale, not public internet)
 *
 * Run:  RELAY_SECRET=yourSecret node relay.js
 * macOS will prompt to allow Terminal/Node to control "Messages" — approve it
 * (System Settings → Privacy & Security → Automation). For SMS (green) to
 * non-iMessage numbers, the iPhone must have Text Message Forwarding ON.
 */

const http = require('http');
const { execFile } = require('child_process');

const PORT = parseInt(process.env.RELAY_PORT || '8787', 10);
const BIND = process.env.RELAY_BIND || '0.0.0.0';
const SECRET = process.env.RELAY_SECRET || '';

// AppleScript: try iMessage first, fall back to the SMS service if available.
const SCRIPT = `
on run {targetAddr, targetText}
  tell application "Messages"
    try
      set svc to 1st service whose service type = iMessage
      set theBuddy to buddy targetAddr of svc
      send targetText to theBuddy
      return "imessage"
    on error
      set smsService to 1st service whose service type = SMS
      set theBuddy to buddy targetAddr of smsService
      send targetText to theBuddy
      return "sms"
    end try
  end tell
end run
`;

function sendViaMessages(to, text) {
  return new Promise((resolve, reject) => {
    execFile('osascript', ['-e', SCRIPT, to, text], { timeout: 20000 }, (err, stdout, stderr) => {
      if (err) return reject(new Error((stderr || err.message || '').trim()));
      resolve((stdout || '').trim() || 'sent');
    });
  });
}

function readBody(req) {
  return new Promise(resolve => {
    let b = '';
    req.on('data', c => (b += c));
    req.on('end', () => { try { resolve(JSON.parse(b || '{}')); } catch { resolve({}); } });
  });
}

const server = http.createServer(async (req, res) => {
  const json = (code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); };

  if (req.method === 'GET' && req.url === '/health') return json(200, { ok: true, service: 'imessage-relay' });

  if (req.method === 'POST' && req.url === '/send') {
    if (SECRET && req.headers['x-relay-secret'] !== SECRET) return json(401, { ok: false, error: 'bad secret' });
    const body = await readBody(req);
    if (!body.to || !body.text) return json(400, { ok: false, error: 'to and text required' });
    try {
      const via = await sendViaMessages(String(body.to), String(body.text));
      return json(200, { ok: true, via, to: body.to });
    } catch (e) {
      return json(500, { ok: false, error: e.message });
    }
  }
  json(404, { ok: false, error: 'not found' });
});

server.listen(PORT, BIND, () => {
  console.log(`iMessage relay listening on ${BIND}:${PORT}  (secret ${SECRET ? 'ON' : 'OFF — set RELAY_SECRET!'})`);
});
