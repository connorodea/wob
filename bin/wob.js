#!/usr/bin/env node
// wob CLI entry — delegates to the Python package in this install,
// running inside the shared venv ~/.wob-venv (created by postinstall).
const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");

const HOME = os.homedir();
const VENV_PY = path.join(HOME, ".wob-venv", "bin", "python");
const PKG = path.join(__dirname, "..");

if (!fs.existsSync(VENV_PY)) {
  console.error("wob: venv missing — run the postinstall: node " +
    path.join(PKG, "scripts", "install.js"));
  process.exit(1);
}

const r = spawnSync(
  VENV_PY,
  ["-m", "wob", ...process.argv.slice(2)],
  {
    stdio: "inherit",
    cwd: PKG,
    env: { ...process.env, PYTHONPATH: PKG },
  }
);
process.exit(r.status === null ? 1 : r.status);