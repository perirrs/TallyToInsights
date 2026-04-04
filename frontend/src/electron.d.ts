/**
 * Type declarations for the Electron context bridge API
 * exposed via electron/preload.js → window.electron
 */

interface ElectronActivateResult {
  success: boolean;
  serial?: number;
  error?: string;
}

interface ElectronBridge {
  /** Returns true when this machine has a valid, activated license. */
  isActivated: () => Promise<boolean>;

  /**
   * Attempt product-key activation.
   * On success the app relaunches; on failure returns error message.
   */
  activate: (key: string) => Promise<ElectronActivateResult>;

  /** Partially-masked machine ID for display in the activation screen. */
  getMachineId: () => Promise<string>;

  /** Application version string. */
  getVersion: () => Promise<string>;

  /** Returns a pre-fetched desktop auth token from the main process (production fast-path). */
  getDesktopToken: () => Promise<{ access_token: string; user_id: number; name: string; is_admin: boolean } | null>;
}

declare global {
  interface Window {
    /** Present only when running inside Electron (not plain browser). */
    electron?: ElectronBridge;
  }
}

export {};
