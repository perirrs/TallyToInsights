/**
 * Electron main process — TallyInsights Desktop
 *
 * Startup flow:
 *  1. Check if this machine is activated (offline, encrypted local store)
 *  2. If NOT activated → load React app (activation screen shown by React)
 *  3. On successful activation → app.relaunch() + app.exit()
 *  4. If activated → (production only) spawn Python backend, wait for health
 *  5. Open main BrowserWindow with the React app
 */

const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron');
const path = require('path');
const Store = require('electron-store');
const productKey = require('./product-key');
const backendLauncher = require('./backend-launcher');

// ── Environment detection ──────────────────────────────────────────────────
const isDev = !app.isPackaged;

// ── Encrypted activation store ─────────────────────────────────────────────
const store = new Store({
  name: 'activation',
  encryptionKey: 'ti-activation-store-key-v1-xk9m2n',
  clearInvalidConfig: true,
});

// ── Activation helpers ─────────────────────────────────────────────────────
function isActivated() {
  const activation = store.get('activation');
  if (!activation || !activation.key || !activation.machineId) return false;
  // Validate key is still cryptographically valid
  if (productKey.validateKey(activation.key) === null) return false;
  // Validate machine hasn't changed
  return activation.machineId === productKey.getMachineId();
}

function doActivate(key) {
  const serial = productKey.validateKey(key);
  if (serial === null) {
    return { success: false, error: 'Invalid product key. Please check the key and try again.' };
  }
  store.set('activation', {
    key: key.toUpperCase().trim(),
    serial,
    machineId: productKey.getMachineId(),
    activatedAt: new Date().toISOString(),
  });
  return { success: true, serial };
}

// ── IPC handlers ───────────────────────────────────────────────────────────
ipcMain.handle('is-activated', () => isActivated());

ipcMain.handle('activate', async (_, key) => {
  const result = doActivate(key);
  if (result.success) {
    // Relaunch so the main window opens with the backend running
    app.relaunch();
    app.exit(0);
  }
  return result;
});

ipcMain.handle('get-machine-id', () => {
  const id = productKey.getMachineId();
  return `${id.slice(0, 8)}-****-****-****-${id.slice(-12)}`;
});

ipcMain.handle('get-version', () => app.getVersion());

// ── Window factory ─────────────────────────────────────────────────────────
function createWindow({ width = 1280, height = 800, resizable = true, title = 'TallyInsights' } = {}) {
  const win = new BrowserWindow({
    width,
    height,
    minWidth: resizable ? 1024 : width,
    minHeight: resizable ? 600 : height,
    resizable,
    title,
    backgroundColor: '#0f172a',
    show: false, // revealed after ready-to-show to avoid white flash
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      devTools: isDev,
    },
  });

  win.once('ready-to-show', () => win.show());

  // Open external links in system browser, not Electron
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url);
    return { action: 'deny' };
  });

  return win;
}

function getAppUrl(path_ = '') {
  if (isDev) return `http://localhost:5173${path_}`;
  return `file://${path.join(__dirname, '..', 'frontend', 'dist', 'index.html')}${path_}`;
}

// ── Main entry ─────────────────────────────────────────────────────────────
async function main() {
  await app.whenReady();

  // Disable default menu in production
  if (!isDev) Menu.setApplicationMenu(null);

  // ── Step 1: Activation gate ────────────────────────────────────────────
  if (!isActivated()) {
    const activationWin = createWindow({
      width: 500,
      height: 520,
      resizable: false,
      title: 'TallyInsights — License Activation',
    });
    activationWin.loadURL(getAppUrl());

    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') app.quit();
    });

    // After ipcMain.handle('activate') above does app.relaunch(), this window
    // closes and a fresh process starts fully activated.
    return;
  }

  // ── Step 2: Start Python backend (production only) ─────────────────────
  if (!isDev) {
    const loadingWin = createWindow({ width: 420, height: 240, resizable: false, title: 'TallyInsights' });
    loadingWin.loadURL(
      `data:text/html,<html style="background:#0f172a;display:flex;align-items:center;justify-content:center;height:100vh;margin:0"><p style="color:#94a3b8;font-family:sans-serif;font-size:16px">Starting TallyInsights…</p></html>`,
    );

    const started = await backendLauncher.start();
    loadingWin.close();

    if (!started) {
      dialog.showErrorBox(
        'TallyInsights — Startup Error',
        'The backend service failed to start.\n\nPlease reinstall the application or contact support.',
      );
      app.quit();
      return;
    }
  }

  // ── Step 3: Open main window ───────────────────────────────────────────
  const win = createWindow();
  win.loadURL(getAppUrl());

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      backendLauncher.stop();
      app.quit();
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      const w = createWindow();
      w.loadURL(getAppUrl());
    }
  });
}

main().catch((err) => {
  dialog.showErrorBox('TallyInsights — Error', String(err));
  app.quit();
});
