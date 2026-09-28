#!/usr/bin/env node
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { getRepoRoot, loadPaths, loadEnvFile } from "./lib/paths.mjs";

const root = getRepoRoot();
const paths = loadPaths();
if (!paths) {
  console.error("Run: npm run setup");
  process.exit(1);
}

const envFile = path.join(root, ".env");
if (!fs.existsSync(envFile)) {
  console.error("Missing .env — copy .env.example");
  process.exit(1);
}

const composeFile = path.join(root, "docker", "docker-compose.yml");
const env = {
  ...process.env,
  ...loadEnvFile(root),
  ROOT: root.replace(/\\/g, "/"),
};

console.log(`Starting n8n (ROOT=${env.ROOT})...\n`);

const child = spawn(
  "docker",
  ["compose", "-f", composeFile, "up", "-d"],
  { cwd: root, env, stdio: "inherit", shell: process.platform === "win32" }
);

child.on("exit", (code) => {
  if (code === 0) {
    console.log("\n✅ n8n → http://localhost:5678\n");
  }
  process.exit(code ?? 1);
});
