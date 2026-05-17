#!/usr/bin/env node
import { spawn } from "node:child_process";
import path from "node:path";
import { getRepoRoot, loadPaths, loadEnvFile } from "./lib/paths.mjs";

const root = getRepoRoot();
const paths = loadPaths();
if (!paths) {
  console.error("Run: npm run setup");
  process.exit(1);
}

const composeFile = path.join(root, "docker", "docker-compose.yml");
const env = { ...process.env, ...loadEnvFile(root), ROOT: root.replace(/\\/g, "/") };

const child = spawn(
  "docker",
  ["compose", "-f", composeFile, "down"],
  { cwd: root, env, stdio: "inherit", shell: process.platform === "win32" }
);

child.on("exit", (code) => process.exit(code ?? 1));
