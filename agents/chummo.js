const { spawnSync } = require('child_process');
const path = require('path');

spawnSync(process.execPath, [path.join(__dirname, 'orchestrator.js'), 'chummo'], { stdio: 'inherit' });
