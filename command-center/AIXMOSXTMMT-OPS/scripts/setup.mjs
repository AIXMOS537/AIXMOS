#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { getRepoRoot, savePaths, ensureDataDirs } from "./lib/paths.mjs";

const root = getRepoRoot();

ensureDataDirs(root);

const envExample = path.join(root, ".env.example");
const envFile = path.join(root, ".env");
if (!fs.existsSync(envFile) && fs.existsSync(envExample)) {
  fs.copyFileSync(envExample, envFile);
  console.log("Created .env from .env.example — fill in your keys.");
}

// Mirror Supabase URL/anon into VITE_ for clock app if missing
if (fs.existsSync(envFile)) {
  let envText = fs.readFileSync(envFile, "utf8");
  const url = envText.match(/^SUPABASE_URL=(.+)$/m)?.[1];
  const anon = envText.match(/^SUPABASE_ANON_KEY=(.+)$/m)?.[1];
  if (url && !/^VITE_SUPABASE_URL=/m.test(envText)) {
    envText += `\nVITE_SUPABASE_URL=${url}\n`;
  }
  if (anon && !/^VITE_SUPABASE_ANON_KEY=/m.test(envText)) {
    envText += `VITE_SUPABASE_ANON_KEY=${anon}\n`;
  }
  fs.writeFileSync(envFile, envText);
}

savePaths({
  platform: process.platform,
  root,
  data: path.join(root, "data"),
  dockerCompose: path.join(root, "docker", "docker-compose.yml"),
  ollamaUrl: process.env.OLLAMA_BASE_URL || "http://127.0.0.1:11434",
  createdAt: new Date().toISOString(),
});

console.log("\n✅ AIXMOSXTMMT-OPS setup complete");
console.log(`   Root: ${root}`);
console.log(`   Platform: ${process.platform}`);
console.log("\nNext:");
console.log("  1. Edit .env with your Supabase + API keys");
console.log("  2. npm run doctor");
console.log("  3. npm run start   → n8n http://localhost:5678");
console.log("  4. npm run clock:install && npm run clock:dev\n");
