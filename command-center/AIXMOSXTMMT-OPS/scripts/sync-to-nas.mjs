#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { getRepoRoot, loadEnvFile } from "./lib/paths.mjs";

const root = getRepoRoot();
const env = loadEnvFile(root);

const nasRoot =
  process.platform === "win32"
    ? env.NAS_AI_PATH_WIN
    : env.NAS_AI_PATH_MAC;

if (!nasRoot || nasRoot.includes("Volumes/nas")) {
  console.error("Mount NAS and set NAS_AI_PATH_MAC or NAS_AI_PATH_WIN in .env");
  process.exit(1);
}

const policySrc = path.join(root, "config", "autonomy.yaml");
const policyDst = path.join(nasRoot, "agents", "policy", "autonomy.yaml");

fs.mkdirSync(path.dirname(policyDst), { recursive: true });
fs.copyFileSync(policySrc, policyDst);
console.log(`✅ Copied autonomy.yaml → ${policyDst}`);

const auditDir = path.join(nasRoot, "agents", "audit");
fs.mkdirSync(auditDir, { recursive: true });
console.log(`✅ Ensured ${auditDir}`);
