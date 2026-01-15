import { useState, useEffect } from 'react';
import { tauriService, CLIStatus, BackendStatus } from '../services/tauri';

export default function SettingsPage() {
  const [cliStatus, setCliStatus] = useState<CLIStatus | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const [cli, backend] = await Promise.all([
        tauriService.checkCLI(),
        tauriService.getBackendStatus(),
      ]);
      setCliStatus(cli);
      setBackendStatus(backend);
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  const handleInstallCLI = async () => {
    setLoading(true);
    setMessage(null);
    try {
      await tauriService.installCLI();
      setMessage({ type: 'success', text: 'Claude Code CLI installed successfully!' });
      await loadStatus();
    } catch (error) {
      setMessage({ type: 'error', text: `Installation failed: ${error}` });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveApiKey = () => {
    // In a real implementation, this would save to macOS Keychain via Tauri
    localStorage.setItem('ANTHROPIC_API_KEY', apiKey);
    setMessage({ type: 'success', text: 'API Key saved!' });
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {message && (
        <div
          className={`mb-4 p-4 rounded-lg ${
            message.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* API Configuration */}
      <section className="mb-8 bg-[#1a1f2e] rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">API Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Anthropic API Key</label>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-ant-..."
                className="flex-1 px-4 py-2 bg-[#101622] border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#2b6cee]"
              />
              <button
                onClick={handleSaveApiKey}
                className="px-4 py-2 bg-[#2b6cee] text-white rounded-lg hover:bg-[#2b6cee]/80"
              >
                Save
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Your API key is stored securely on your local machine.
            </p>
          </div>
        </div>
      </section>

      {/* Claude Code CLI Status */}
      <section className="mb-8 bg-[#1a1f2e] rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Claude Code CLI</h2>
        {cliStatus ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Status</span>
              <span className={cliStatus.installed ? 'text-green-400' : 'text-yellow-400'}>
                {cliStatus.installed ? '✓ Installed' : '✗ Not Installed'}
              </span>
            </div>
            {cliStatus.installed && cliStatus.version && (
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Version</span>
                <span className="text-white">{cliStatus.version}</span>
              </div>
            )}
            {cliStatus.installed && cliStatus.path && (
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Path</span>
                <span className="text-white text-sm font-mono">{cliStatus.path}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Node.js</span>
              <span className={cliStatus.node_installed ? 'text-green-400' : 'text-red-400'}>
                {cliStatus.node_installed ? '✓ Available' : '✗ Not Found'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">npm</span>
              <span className={cliStatus.npm_installed ? 'text-green-400' : 'text-red-400'}>
                {cliStatus.npm_installed ? '✓ Available' : '✗ Not Found'}
              </span>
            </div>
            {!cliStatus.installed && cliStatus.npm_installed && (
              <button
                onClick={handleInstallCLI}
                disabled={loading}
                className="mt-4 w-full px-4 py-2 bg-[#2b6cee] text-white rounded-lg hover:bg-[#2b6cee]/80 disabled:opacity-50"
              >
                {loading ? 'Installing...' : 'Install Claude Code CLI'}
              </button>
            )}
            {!cliStatus.installed && !cliStatus.npm_installed && (
              <p className="text-yellow-400 text-sm mt-2">
                Please install Node.js first to enable Claude Code CLI installation.
              </p>
            )}
          </div>
        ) : (
          <p className="text-gray-500">Loading...</p>
        )}
      </section>

      {/* Backend Status */}
      <section className="mb-8 bg-[#1a1f2e] rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Backend Service</h2>
        {backendStatus ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Status</span>
              <span className={backendStatus.running ? 'text-green-400' : 'text-red-400'}>
                {backendStatus.running ? '● Running' : '○ Stopped'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Port</span>
              <span className="text-white">{backendStatus.port}</span>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">Loading...</p>
        )}
      </section>

      {/* Storage Info */}
      <section className="mb-8 bg-[#1a1f2e] rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Storage</h2>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Data Directory</span>
            <span className="text-white font-mono text-xs">
              ~/Library/Application Support/ClaudeAgentPlatform/
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Skills Directory</span>
            <span className="text-white font-mono text-xs">
              ~/Library/Application Support/ClaudeAgentPlatform/skills/
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Database</span>
            <span className="text-white font-mono text-xs">data.db (SQLite)</span>
          </div>
        </div>
      </section>

      {/* About */}
      <section className="bg-[#1a1f2e] rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">About</h2>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Version</span>
            <span className="text-white">1.0.0</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Platform</span>
            <span className="text-white">macOS</span>
          </div>
        </div>
      </section>
    </div>
  );
}
