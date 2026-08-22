// One-time env setup: shared venv ~/.wob-venv with all Python deps.
// Idempotent — safe to re-run; skips work when the venv already exists.
const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");

const HOME = os.homedir();
const VENV = path.join(HOME, ".wob-venv");
const VENV_PY = path.join(VENV, "bin", "python");
const REQ = path.join(__dirname, "..", "requirements.txt");

function ok(res, quiet) {
  if (res.status !== 0 && !quiet) {
    console.error(`wob-install: ${res.error ? res.error.message : "command failed"}`);
  }
  return res.status === 0;
}

if (fs.existsSync(VENV_PY)) {
  console.log("wob: venv present, skipping install");
  process.exit(0);
}

const candidates = ["python3.13", "python3.12", "python3", "python"];
const py = candidates.find((p) => {
  const r = spawnSync(p, ["--version"], { stdio: "ignore" });
  return r.status === 0 && (p === "python3.12" || p === "python3.13" || p === "python3"
    ? true : false);
});

if (!py) {
  console.error("wob-install: python3.13 not found — install it first " +
    "(https://www.python.org/downloads/), then re-run:");
  console.error("  node " + path.join(__dirname, "install.js"));
  process.exit(0); // never break npm install
}

console.log(`wob-install: creating ${VENV} (python ${py})`);
ok(spawnSync(py, ["-m", "venv", VENV], { stdio: "inherit" }));
ok(spawnSync(VENV_PY, ["-m", "pip", "install", "--quiet", "--upgrade", "pip"], { stdio: "inherit" }));
ok(spawnSync(VENV_PY, ["-m", "pip", "install", "--quiet", "-r", REQ], { stdio: "inherit" }));
console.log("wob: installed — try: wob deals");