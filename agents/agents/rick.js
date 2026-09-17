/**
 * RICK — X's right-hand agent on the M1 Max.
 * Rick Sorkin persona. Executes, reports, escalates only what needs X.
 *
 * Capabilities:
 *   rick blast       — blast magic links to all operators
 *   rick ops [msg]   — post a message to Slack #ops
 *   rick health      — hit all Vercel endpoints + Supabase
 *   rick brief       — fire the morning brief to Telegram
 *   rick status      — show operator training progress
 *   rick wake        — print Rick's prime brief (reload context)
 */

// ── OWNER TIER. NOT PART OF THE DISTRIBUTED PACK. ───────────────────────────────────
// RICK is the owner's own control surface: it hardcodes a specific Slack channel, three
// specific Vercel deployments and a `blast` that messages THAT owner's operators. It is
// the only file in this repo carrying those identifiers.
//
// The installers mirror the whole tree, so without this guard a copy of RICK lands on
// every machine the pack is installed on. On a stranger's laptop it cannot work (no
// credentials) and should not try (it would hit someone else's production from their
// machine). The installers now exclude this file as well; the guard is the backstop for
// a hand-copied tree.
//
// To run it on the owner's own machine: export AIXMOS_OWNER_TIER=1
if (process.env.AIXMOS_OWNER_TIER !== "1") {
  console.error(
    "RICK is owner-tier and is not part of the AIXMOS pack.\n" +
    "It targets one specific operation's Slack, Vercel projects and operator list.\n" +
    "If this is the owner's machine: export AIXMOS_OWNER_TIER=1"
  );
  process.exit(2);
}

const { execSync, execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const https = require("https");

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  for (const line of fs.readFileSync(filePath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 1) continue;
    const key = trimmed.slice(0, eq);
    let val = trimmed.slice(eq + 1);
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = val;
  }
}

loadEnvFile(path.join(process.env.HOME || "", ".config/tmmt/evals-supabase.env"));

const ANON_KEY =
  process.env.SUPABASE_ANON_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  process.env.SUPABASE_PUBLISHABLE_KEY ||
  "";
const SUPABASE_URL = (
  process.env.SUPABASE_URL ||
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  ""
).replace(/\/$/, "");
const SLACK_OPS = "C0B8ZD1D11N";
const PORTAL = "https://tmmt-command-center.vercel.app/operator/training";

function fetch(url, opts = {}) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, { method: opts.method || "GET", headers: opts.headers || {} }, (res) => {
      let body = "";
      res.on("data", (d) => (body += d));
      res.on("end", () => {
        try { resolve({ ok: res.statusCode < 400, status: res.statusCode, json: () => JSON.parse(body), text: () => body }); }
        catch (e) { resolve({ ok: res.statusCode < 400, status: res.statusCode, json: () => ({}), text: () => body }); }
      });
    });
    req.on("error", reject);
    if (opts.body) req.write(opts.body);
    req.end();
  });
}

const commands = {
  async blast() {
    console.log("Rick → blasting operators...");
    const res = await fetch(`${SUPABASE_URL}/functions/v1/blast-operators`, {
      method: "POST",
      headers: { Authorization: `Bearer ${ANON_KEY}`, "Content-Type": "application/json" },
    });
    const data = res.json();
    console.log(`Done. ${data.message}`);
    if (data.errors?.length) console.error("Errors:", data.errors);
    return data;
  },

  async health() {
    const endpoints = [
      "https://tmmt-ops.vercel.app",
      "https://tmmt-command-center.vercel.app",
      "https://aixmos-landing.vercel.app",
    ];
    console.log("Rick → health sweep...");
    for (const url of endpoints) {
      try {
        const res = await fetch(url);
        console.log(`  ${res.ok ? "✓" : "✗"} ${url} → ${res.status}`);
      } catch (e) {
        console.log(`  ✗ ${url} → ${e.message}`);
      }
    }
    // Supabase ping
    try {
      const res = await fetch(`${SUPABASE_URL}/rest/v1/`, {
        headers: { apikey: ANON_KEY },
      });
      console.log(`  ${res.ok ? "✓" : "✗"} Supabase → ${res.status}`);
    } catch (e) {
      console.log(`  ✗ Supabase → ${e.message}`);
    }
  },

  async ops(msg) {
    if (!msg) { console.error("Usage: rick ops <message>"); return; }
    // Requires SLACK_BOT_TOKEN in env
    const token = process.env.SLACK_BOT_TOKEN;
    if (!token) { console.error("SLACK_BOT_TOKEN not set. Post manually."); return; }
    const res = await fetch("https://slack.com/api/chat.postMessage", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ channel: SLACK_OPS, text: msg }),
    });
    const data = res.json();
    console.log(data.ok ? `Posted to #ops.` : `Slack error: ${data.error}`);
  },

  async status() {
    console.log("Rick → operator training status...");
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/operator_training_progress?select=profile_id,module_id,percent_complete,updated_at&order=updated_at.desc`,
      { headers: { apikey: ANON_KEY, Authorization: `Bearer ${ANON_KEY}` } }
    );
    const rows = res.json();
    if (!rows.length) {
      console.log("  0 rows — no operator has started yet.");
    } else {
      rows.forEach((r) => console.log(`  ${r.profile_id.slice(0, 8)}… module ${r.module_id} → ${r.percent_complete}%`));
    }
  },

  wake() {
    const brief = path.join(__dirname, "../../Documents/Business/knowledge-base/RICK_PRIME_BRIEF.md");
    if (fs.existsSync(brief)) {
      console.log(fs.readFileSync(brief, "utf8"));
    } else {
      console.log("RICK_PRIME_BRIEF.md not found. Run sync-knowledge-base.sh first.");
    }
  },
};

async function main() {
  const [, , cmd, ...args] = process.argv;
  if (!cmd || !commands[cmd]) {
    console.log("Rick — available commands: blast | health | ops <msg> | status | wake");
    return;
  }
  await commands[cmd](...args);
}

main().catch(console.error);
