/**
 * Electron preload script.
 * Exposes a safe subset of Electron APIs to the renderer (React app)
 * via contextBridge — Node.js is NOT available in the renderer directly.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  /** Returns true if this copy is activated on this machine. */
  isActivated: () => ipcRenderer.invoke('is-activated'),

  /**
   * Attempt to activate with the given product key.
   * Returns { success: boolean, serial?: number, error?: string }
   * On success, the app relaunches automatically.
   */
  activate: (key) => ipcRenderer.invoke('activate', key),

  /** Returns a display-safe version of the machine ID (first 20 chars). */
  getMachineId: () => ipcRenderer.invoke('get-machine-id'),

  /** Returns the app version string. */
  getVersion: () => ipcRenderer.invoke('get-version'),

  /**
   * Returns the desktop auto-login token fetched from the backend after startup.
   * Null in dev mode (use manual login instead).
   */
  getDesktopToken: () => ipcRenderer.invoke('get-desktop-token'),
});
