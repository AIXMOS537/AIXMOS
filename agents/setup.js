const fs = require('fs');
const path = require('path');
const readline = require('readline');

const CONFIG_FILE = path.join(__dirname, 'config.json');

function ask(rl, q) {
  return new Promise(resolve => rl.question(q, answer => resolve(answer.trim())));
}

async function main() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const config = fs.existsSync(CONFIG_FILE)
    ? JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'))
    : {};

  console.log('\n  AIXMOS setup\n');
  const telegram = await ask(rl, '  Enable Telegram sending later? (y/n): ');
  config.telegram = config.telegram || {};
  config.telegram.enabled = telegram.toLowerCase() === 'y';

  if (config.telegram.enabled) {
    config.telegram.bot_token = await ask(rl, '  Telegram bot token: ');
    const chatId = await ask(rl, '  Morning brief chat id: ');
    config.scheduler = config.scheduler || {};
    config.scheduler.morning_brief_recipients = chatId ? [chatId] : [];
  }

  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
  console.log(`\n  Saved: ${CONFIG_FILE}\n`);
  rl.close();
}

if (require.main === module) main().catch(console.error);
