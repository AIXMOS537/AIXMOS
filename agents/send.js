const fs = require('fs');
const path = require('path');

const OUTBOX = path.join(__dirname, 'outbox');

async function prompt(rl, text) {
  const ask = q => new Promise(resolve => rl.question(q, answer => resolve(answer.trim())));
  const choice = await ask('  Save this output to outbox? (y/n): ');
  if (choice.toLowerCase() !== 'y') return false;

  if (!fs.existsSync(OUTBOX)) fs.mkdirSync(OUTBOX, { recursive: true });
  const file = path.join(OUTBOX, `aixmos-${new Date().toISOString().replace(/[:.]/g, '-')}.txt`);
  fs.writeFileSync(file, text);
  console.log(`  Saved: ${file}`);
  return true;
}

module.exports = { prompt };
