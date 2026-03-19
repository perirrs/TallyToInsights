/**
 * Manages the Python FastAPI backend child process.
 * In development: no-op (developer starts it manually).
 * In production: spawns the bundled backend.exe from resources.
 */

const { spawn } = require('child_process');
const path = require('path');
const { app } = require('electron');

const BACKEND_PORT = 8000;
const MAX_WAIT_SECONDS = 45;

let backendProcess = null;

/**
 * Start the bundled Python backend.
 * Returns true when the health endpoint responds, false on timeout.
 */
async function start() {
  const exePath = path.join(process.resourcesPath, 'backend', 'backend.exe');

  backendProcess = spawn(exePath, [], {
    cwd: path.dirname(exePath),
    env: {
      ...process.env,
      TALLY_PORT: String(BACKEND_PORT),
    },
    windowsHide: true,
    stdio: 'ignore',
  });

  backendProcess.on('error', (err) => {
    console.error('Backend process error:', err);
  });

  app.on('before-quit', stop);
  return waitForHealth();
}

/**
 * Poll http://localhost:{BACKEND_PORT}/api/health until it responds.
 */
async function waitForHealth() {
  const url = `http://127.0.0.1:${BACKEND_PORT}/api/health`;
  for (let i = 0; i < MAX_WAIT_SECONDS; i++) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch (_) {}
    await sleep(1000);
  }
  return false;
}

function stop() {
  if (backendProcess) {
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

module.exports = { start, stop };
