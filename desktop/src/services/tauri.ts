import { invoke } from '@tauri-apps/api/core';
import { listen, UnlistenFn } from '@tauri-apps/api/event';

export interface BackendStatus {
  running: boolean;
  port: number;
}

export interface CLIStatus {
  installed: boolean;
  path: string | null;
  version: string | null;
  node_installed: boolean;
  npm_installed: boolean;
}

// Store the backend port globally
let _backendPort: number = 8000;

export function getBackendPort(): number {
  return _backendPort;
}

export function setBackendPort(port: number): void {
  _backendPort = port;
}

export const tauriService = {
  // Backend management
  async startBackend(): Promise<number> {
    const port = await invoke<number>('start_backend');
    setBackendPort(port);
    return port;
  },

  async stopBackend(): Promise<void> {
    return invoke('stop_backend');
  },

  async getBackendStatus(): Promise<BackendStatus> {
    return invoke<BackendStatus>('get_backend_status');
  },

  async getBackendPortFromTauri(): Promise<number> {
    const port = await invoke<number>('get_backend_port');
    setBackendPort(port);
    return port;
  },

  // CLI management
  async checkCLI(): Promise<CLIStatus> {
    return invoke<CLIStatus>('check_claude_cli');
  },

  async installCLI(): Promise<string> {
    return invoke<string>('install_claude_cli');
  },

  // Event listeners
  async onBackendLog(callback: (log: string) => void): Promise<UnlistenFn> {
    return listen<string>('backend-log', (event) => callback(event.payload));
  },

  async onBackendError(callback: (error: string) => void): Promise<UnlistenFn> {
    return listen<string>('backend-error', (event) => callback(event.payload));
  },

  async onBackendTerminated(callback: (code: number | null) => void): Promise<UnlistenFn> {
    return listen<number | null>('backend-terminated', (event) => callback(event.payload));
  },
};

// Initialize backend connection
export async function initializeBackend(): Promise<number> {
  try {
    // First check if backend is already running
    const status = await tauriService.getBackendStatus();
    if (status.running) {
      setBackendPort(status.port);
      return status.port;
    }

    // Start the backend
    const port = await tauriService.startBackend();
    return port;
  } catch (error) {
    console.error('Failed to initialize backend:', error);
    // Fallback to default port
    return 8000;
  }
}
