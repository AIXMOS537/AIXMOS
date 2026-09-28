#!/usr/bin/env node
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { getRepoRoot, loadPaths, loadEnvFile } from "./lib/paths.mjs";

const root = getRepoRoot();
const env = { ...loadEnvFile(root), ...process.env };
let failed = 0;

function check(name, ok, detail = "") {
  const icon = ok ? "✅" : "❌";
  console.log(`${icon} ${name}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failed++;
}

console.log("\nAIXMOSXTMMT-OPS doctor\n");

const nodeMajor = parseInt(process.version.slice(1), 10);
check("Node >= 20", nodeMajor >= 20, process.version);

const paths = loadPaths();
check("config/paths.json exists", !!paths, "run: npm run setup");

check(".env exists", fs.existsSync(path.join(root, ".env")), "copy from .env.example");

const required = [
  "SUPABASE_URL",
  "SUPABASE_ANON_KEY",
  "SUPABASE_SERVICE_ROLE_KEY",
];
for (const key of required) {
  const val = env[key];
  check(`.env ${key}`, !!val && !val.includes("xxxx"), val ? "set" : "missing");
}

try {
  execSync("docker info", { stdio: "ignore" });
  check("Docker running", true);
} catch {
  check("Docker running", false, "start Docker Desktop");
}

const ollama = env.OLLAMA_BASE_URL || "http://127.0.0.1:11434";
try {
  const res = await fetch(`${ollama.replace(/\/$/, "")}/api/tags`, {
    signal: AbortSignal.timeout(3000),
  });
  check("Ollama reachable", res.ok, ollama);
} catch {
  check("Ollama reachable", false, `${ollama} — run: ollama serve`);
}

try {
  if (typeof fs.statfsSync === "function") {
    const free = fs.statfsSync(root);
    const gb = (free.bfree * free.bsize) / 1e9;
    check("USB/disk free > 2GB", gb > 2, `${gb.toFixed(1)} GB`);
  } else {
    check("Disk space", true, "skipped");
  }
} catch {
  check("Disk space", true, "could not measure");
}

console.log(failed ? `\n⚠️  ${failed} check(s) failed\n` : "\n✅ All checks passed\n");
process.exit(failed ? 1 : 0);
