import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function getRepoRoot() {
  return path.resolve(__dirname, "..", "..");
}

export function pathsConfigFile() {
  return path.join(getRepoRoot(), "config", "paths.json");
}

export function loadPaths() {
  const file = pathsConfigFile();
  if (!fs.existsSync(file)) {
    return null;
  }
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

export function savePaths(data) {
  const file = pathsConfigFile();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n");
}

export function ensureDataDirs(root) {
  for (const sub of ["data/n8n", "data/logs", "data/cache"]) {
    fs.mkdirSync(path.join(root, sub), { recursive: true });
  }
  for (const gitkeep of ["data/n8n/.gitkeep", "data/logs/.gitkeep"]) {
    const p = path.join(root, gitkeep);
    if (!fs.existsSync(p)) fs.writeFileSync(p, "");
  }
}

export function loadEnvFile(root) {
  const envPath = path.join(root, ".env");
  if (!fs.existsSync(envPath)) return {};
  const out = {};
  for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i === -1) continue;
    out[t.slice(0, i).trim()] = t.slice(i + 1).trim();
  }
  return out;
}
