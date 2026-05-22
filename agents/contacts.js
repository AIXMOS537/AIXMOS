// ═══════════════════════════════════════════════════════
// AIXMOS CONTACTS MODULE
// Persistent memory. Agents remember people.
// No more re-entering names and situations every run.
//
// Used by: all agents via require('./contacts')
// Data stored in: aixmos-contacts.json
// ═══════════════════════════════════════════════════════

const fs   = require('fs');
const path = require('path');

const CONTACTS_FILE = path.join(__dirname, 'aixmos-contacts.json');

function load() {
  try {
    if (fs.existsSync(CONTACTS_FILE)) return JSON.parse(fs.readFileSync(CONTACTS_FILE,'utf8'));
  } catch {}
  return { contacts:[], last_updated:null };
}

function save(data) {
  data.last_updated = new Date().toISOString();
  fs.writeFileSync(CONTACTS_FILE, JSON.stringify(data,null,2));
}

// ── ADD OR UPDATE CONTACT ─────────────────────────────
function upsert(contact) {
  const data = load();
  const idx  = data.contacts.findIndex(c =>
    c.name.toLowerCase() === contact.name.toLowerCase() ||
    (contact.phone && c.phone === contact.phone)
  );
  const now  = new Date().toISOString();
  if (idx >= 0) {
    data.contacts[idx] = { ...data.contacts[idx], ...contact, updated: now };
  } else {
    data.contacts.push({ id: Date.now(), created: now, updated: now, history:[], ...contact });
  }
  save(data);
  return data.contacts[idx >= 0 ? idx : data.contacts.length - 1];
}

// ── LOOKUP BY NAME OR PHONE ───────────────────────────
function lookup(query) {
  if (!query) return null;
  const data = load();
  const q    = query.toLowerCase().trim();
  return data.contacts.find(c =>
    c.name?.toLowerCase().includes(q) ||
    c.phone?.includes(q) ||
    c.email?.toLowerCase().includes(q)
  ) || null;
}

// ── SEARCH ────────────────────────────────────────────
function search(query) {
  if (!query) return [];
  const data = load();
  const q    = query.toLowerCase().trim();
  return data.contacts.filter(c =>
    c.name?.toLowerCase().includes(q) ||
    c.business?.toLowerCase().includes(q) ||
    c.tier?.toLowerCase().includes(q) ||
    c.stage?.toLowerCase().includes(q) ||
    c.notes?.toLowerCase().includes(q)
  );
}

// ── LIST ALL ──────────────────────────────────────────
function list(filter) {
  const data = load();
  if (!filter) return data.contacts;
  return data.contacts.filter(c => {
    if (filter.business && c.business !== filter.business) return false;
    if (filter.stage    && c.stage    !== filter.stage)    return false;
    if (filter.tier     && c.tier     !== filter.tier)     return false;
    return true;
  });
}

// ── ADD HISTORY ENTRY ─────────────────────────────────
function addHistory(nameOrPhone, entry) {
  const data    = load();
  const contact = data.contacts.find(c =>
    c.name?.toLowerCase().includes(nameOrPhone.toLowerCase()) ||
    c.phone?.includes(nameOrPhone)
  );
  if (!contact) return false;
  if (!contact.history) contact.history = [];
  contact.history.push({ date: new Date().toISOString(), ...entry });
  contact.last_contact = new Date().toISOString();
  save(data);
  return true;
}

// ── GET CONTACT CONTEXT (for agent prompts) ───────────
function getContext(nameOrPhone) {
  const contact = lookup(nameOrPhone);
  if (!contact) return null;
  const recentHistory = (contact.history || []).slice(-5);
  return {
    name:         contact.name,
    phone:        contact.phone,
    email:        contact.email,
    business:     contact.business,
    tier:         contact.tier,
    stage:        contact.stage,
    situation:    contact.situation,
    notes:        contact.notes,
    last_contact: contact.last_contact,
    recent_history: recentHistory,
    days_since_contact: contact.last_contact
      ? Math.floor((Date.now() - new Date(contact.last_contact)) / 86400000)
      : null,
  };
}

// ── FORMAT CONTACT SUMMARY ────────────────────────────
function formatSummary(contact) {
  if (!contact) return 'Contact not found.';
  const daysSince = contact.last_contact
    ? Math.floor((Date.now()-new Date(contact.last_contact))/86400000)
    : null;
  return [
    `Name:         ${contact.name}`,
    `Phone:        ${contact.phone || '—'}`,
    `Email:        ${contact.email || '—'}`,
    `Business:     ${contact.business || '—'}`,
    `Tier:         ${contact.tier || '—'}`,
    `Stage:        ${contact.stage || '—'}`,
    `Situation:    ${contact.situation || '—'}`,
    `Last contact: ${contact.last_contact ? new Date(contact.last_contact).toLocaleDateString() : 'Never'
      }${daysSince !== null ? ` (${daysSince}d ago)` : ''}`,
    `Notes:        ${contact.notes || '—'}`,
  ].join('\n');
}

// ── DELETE ────────────────────────────────────────────
function remove(nameOrPhone) {
  const data = load();
  const before = data.contacts.length;
  data.contacts = data.contacts.filter(c =>
    !c.name?.toLowerCase().includes(nameOrPhone.toLowerCase()) &&
    !c.phone?.includes(nameOrPhone)
  );
  if (data.contacts.length < before) { save(data); return true; }
  return false;
}

// ── COUNT ─────────────────────────────────────────────
function count() { return load().contacts.length; }

// ── CONTACTS CLI (standalone) ─────────────────────────
async function cli() {
  const readline = require('readline');
  const c = {
    blue:'\x1b[34m',cyan:'\x1b[36m',green:'\x1b[32m',yellow:'\x1b[33m',
    bold:'\x1b[1m',dim:'\x1b[2m',reset:'\x1b[0m',red:'\x1b[31m',
  };
  const rl = readline.createInterface({input:process.stdin,output:process.stdout});
  const ask = (q) => new Promise(r=>rl.question(q,a=>r(a.trim())));
  const hr  = () => console.log(`${c.dim}${'─'.repeat(48)}${c.reset}`);

  console.log(`\n${c.blue}${c.bold}  AIXMOS CONTACTS — ${count()} saved${c.reset}\n`);

  let running = true;
  while(running) {
    hr();
    console.log(`  ${c.cyan}1.${c.reset} Lookup contact`);
    console.log(`  ${c.cyan}2.${c.reset} Add / update contact`);
    console.log(`  ${c.cyan}3.${c.reset} List all contacts`);
    console.log(`  ${c.cyan}4.${c.reset} Search contacts`);
    console.log(`  ${c.cyan}5.${c.reset} Add history entry`);
    console.log(`  ${c.cyan}6.${c.reset} Delete contact`);
    console.log(`  ${c.dim}Q.${c.reset} Quit`);
    console.log();

    const pick = await ask(`  ${c.cyan}Choose: ${c.reset}`);
    switch(pick.toLowerCase()) {
      case '1': {
        const q = await ask(`  Name or phone: `);
        const contact = lookup(q);
        if(contact) { console.log(`\n${formatSummary(contact)}\n`); }
        else { console.log(`  ${c.yellow}Not found.${c.reset}\n`); }
        break;
      }
      case '2': {
        const contact = {};
        contact.name     = await ask(`  Name: `);
        contact.phone    = await ask(`  Phone (+1...): `);
        contact.email    = await ask(`  Email: `);
        contact.business = await ask(`  Business (tmmt/aixmos/ecom): `);
        contact.tier     = await ask(`  Tier (e.g. Membership $97/mo): `);
        contact.stage    = await ask(`  Pipeline stage: `);
        contact.situation= await ask(`  Situation/notes: `);
        if(contact.name) { upsert(contact); console.log(`  ${c.green}✓ Saved${c.reset}\n`); }
        break;
      }
      case '3': {
        const all = list();
        console.log(`\n  ${c.bold}${all.length} contacts:${c.reset}`);
        all.forEach(contact => {
          const days = contact.last_contact
            ? Math.floor((Date.now()-new Date(contact.last_contact))/86400000)
            : null;
          console.log(`  ${c.cyan}${contact.name.padEnd(20)}${c.reset} ${(contact.tier||'').padEnd(25)} ${(contact.stage||'').padEnd(20)} ${days!==null?days+'d ago':'never contacted'}`);
        });
        console.log();
        break;
      }
      case '4': {
        const q = await ask(`  Search query: `);
        const results = search(q);
        console.log(`\n  ${results.length} results:`);
        results.forEach(contact => console.log(`  ${c.cyan}${contact.name}${c.reset} — ${contact.business||''} — ${contact.stage||''}`));
        console.log();
        break;
      }
      case '5': {
        const name = await ask(`  Contact name: `);
        const note = await ask(`  What happened: `);
        const agent= await ask(`  Which agent did this (chummo/moose/etc): `);
        if(addHistory(name,{note,agent})) console.log(`  ${c.green}✓ History added${c.reset}\n`);
        else console.log(`  ${c.yellow}Contact not found.${c.reset}\n`);
        break;
      }
      case '6': {
        const q = await ask(`  Name or phone to delete: `);
        if(remove(q)) console.log(`  ${c.green}✓ Deleted${c.reset}\n`);
        else console.log(`  ${c.yellow}Not found.${c.reset}\n`);
        break;
      }
      case 'q': running=false; break;
      default: break;
    }
  }
  rl.close();
}

module.exports = { upsert, lookup, search, list, addHistory, getContext, formatSummary, remove, count };

// Run standalone if called directly
if (require.main === module) cli().catch(console.error);
