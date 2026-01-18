import { useState, useEffect } from 'react';
import { SearchBar, Button, Modal, SkeletonTable, ResizableTable, ResizableTableCell, ConfirmDialog } from '../components/common';
import type { Plugin, PluginInstallRequest } from '../types';
import { pluginsService } from '../services/plugins';

// Plugin table column configuration
const PLUGIN_COLUMNS = [
  { key: 'name', header: 'Plugin Name', initialWidth: 180, minWidth: 120 },
  { key: 'marketplace', header: 'Marketplace', initialWidth: 140, minWidth: 100 },
  { key: 'version', header: 'Version', initialWidth: 100, minWidth: 80 },
  { key: 'author', header: 'Author', initialWidth: 140, minWidth: 100 },
  { key: 'skills', header: 'Skills', initialWidth: 80, minWidth: 60 },
  { key: 'status', header: 'Status', initialWidth: 100, minWidth: 80 },
  { key: 'description', header: 'Description', initialWidth: 250, minWidth: 150 },
  { key: 'actions', header: 'Actions', initialWidth: 140, minWidth: 100, align: 'right' as const },
];

// Install Plugin Modal Component
function InstallPluginModal({
  isOpen,
  onClose,
  onInstall,
  isInstalling,
}: {
  isOpen: boolean;
  onClose: () => void;
  onInstall: (data: PluginInstallRequest) => Promise<void>;
  isInstalling: boolean;
}) {
  const [gitUrl, setGitUrl] = useState('');
  const [gitRef, setGitRef] = useState('main');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!gitUrl.trim()) {
      setError('Git URL is required');
      return;
    }

    try {
      await onInstall({ gitUrl: gitUrl.trim(), gitRef: gitRef.trim() || 'main' });
      setGitUrl('');
      setGitRef('main');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to install plugin');
    }
  };

  const handleClose = () => {
    setGitUrl('');
    setGitRef('main');
    setError('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Install Plugin from Git">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-white mb-2">
            Git Repository URL *
          </label>
          <input
            type="text"
            value={gitUrl}
            onChange={(e) => setGitUrl(e.target.value)}
            placeholder="https://github.com/org/plugin-repo"
            className="w-full px-4 py-2.5 bg-dark-bg border border-dark-border rounded-lg text-white placeholder-muted focus:border-primary focus:outline-none"
            disabled={isInstalling}
          />
          <p className="text-xs text-muted mt-1">
            Repository must contain a plugin.yaml file with skills in a skills/ directory.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-white mb-2">
            Branch / Tag / Commit
          </label>
          <input
            type="text"
            value={gitRef}
            onChange={(e) => setGitRef(e.target.value)}
            placeholder="main"
            className="w-full px-4 py-2.5 bg-dark-bg border border-dark-border rounded-lg text-white placeholder-muted focus:border-primary focus:outline-none"
            disabled={isInstalling}
          />
        </div>

        {error && (
          <div className="p-3 bg-status-error/10 border border-status-error/20 rounded-lg">
            <p className="text-sm text-status-error">{error}</p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4">
          <Button variant="secondary" onClick={handleClose} disabled={isInstalling}>
            Cancel
          </Button>
          <Button type="submit" disabled={isInstalling}>
            {isInstalling ? 'Installing...' : 'Install Plugin'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isInstallModalOpen, setIsInstallModalOpen] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isInstalling, setIsInstalling] = useState(false);

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState<Plugin | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Update state
  const [updatingPluginId, setUpdatingPluginId] = useState<string | null>(null);

  // Fetch plugins on mount
  useEffect(() => {
    const fetchPlugins = async () => {
      try {
        const data = await pluginsService.list();
        setPlugins(data);
      } catch (error) {
        console.error('Failed to fetch plugins:', error);
      } finally {
        setIsInitialLoading(false);
      }
    };
    fetchPlugins();
  }, []);

  const filteredPlugins = plugins.filter((plugin) =>
    plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    plugin.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleInstall = async (data: PluginInstallRequest) => {
    setIsInstalling(true);
    try {
      const installed = await pluginsService.install(data);
      setPlugins((prev) => [...prev, installed]);
      setIsInstallModalOpen(false);
    } finally {
      setIsInstalling(false);
    }
  };

  const handleUpdate = async (pluginId: string) => {
    setUpdatingPluginId(pluginId);
    try {
      const updated = await pluginsService.update(pluginId);
      setPlugins((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (error) {
      console.error('Failed to update plugin:', error);
    } finally {
      setUpdatingPluginId(null);
    }
  };

  const handleDeleteClick = (plugin: Plugin) => {
    setDeleteTarget(plugin);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await pluginsService.uninstall(deleteTarget.id);
      setPlugins((prev) => prev.filter((plugin) => plugin.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (error) {
      console.error('Failed to delete plugin:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  const getStatusBadge = (status: Plugin['status']) => {
    const statusConfig = {
      installed: { bg: 'bg-status-success/10', text: 'text-status-success', label: 'Installed' },
      updating: { bg: 'bg-status-warning/10', text: 'text-status-warning', label: 'Updating' },
      error: { bg: 'bg-status-error/10', text: 'text-status-error', label: 'Error' },
    };
    const config = statusConfig[status];
    return (
      <span className={`px-2 py-1 text-xs font-medium ${config.bg} ${config.text} rounded`}>
        {config.label}
      </span>
    );
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Plugin Management</h1>
          <p className="text-muted mt-1">Install and manage plugins from Git repositories.</p>
        </div>
        <Button icon="add" onClick={() => setIsInstallModalOpen(true)}>
          Install Plugin
        </Button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <SearchBar
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search plugins..."
          className="w-96"
        />
      </div>

      {/* Plugins Table */}
      <div className="bg-dark-card border border-dark-border rounded-xl overflow-hidden">
        {isInitialLoading ? (
          <SkeletonTable rows={5} columns={8} />
        ) : filteredPlugins.length === 0 ? (
          <div className="p-12 text-center">
            <span className="material-symbols-outlined text-5xl text-muted mb-4 block">
              extension
            </span>
            <p className="text-white font-medium mb-2">No plugins installed</p>
            <p className="text-muted text-sm mb-4">
              Install plugins from Git repositories to extend functionality.
            </p>
            <Button icon="add" onClick={() => setIsInstallModalOpen(true)}>
              Install Plugin
            </Button>
          </div>
        ) : (
          <ResizableTable columns={PLUGIN_COLUMNS}>
            {filteredPlugins.map((plugin) => (
              <tr
                key={plugin.id}
                className="border-b border-dark-border hover:bg-dark-hover transition-colors"
              >
                <ResizableTableCell>
                  <div>
                    <span className="text-white font-medium">{plugin.name}</span>
                    <p className="text-xs text-muted truncate" title={plugin.gitUrl}>
                      {plugin.gitUrl}
                    </p>
                  </div>
                </ResizableTableCell>
                <ResizableTableCell>
                  {plugin.marketplace ? (
                    <span className="px-2 py-1 text-xs font-medium bg-purple-500/10 text-purple-400 rounded">
                      {plugin.marketplace}
                    </span>
                  ) : (
                    <span className="text-muted">-</span>
                  )}
                </ResizableTableCell>
                <ResizableTableCell>
                  <span className="text-muted">v{plugin.version}</span>
                </ResizableTableCell>
                <ResizableTableCell>
                  <span className="text-muted">{plugin.author}</span>
                </ResizableTableCell>
                <ResizableTableCell>
                  <span className="px-2 py-1 text-xs font-medium bg-primary/10 text-primary rounded">
                    {plugin.skillIds.length}
                  </span>
                </ResizableTableCell>
                <ResizableTableCell>
                  {getStatusBadge(plugin.status)}
                </ResizableTableCell>
                <ResizableTableCell>
                  <span className="text-muted" title={plugin.description}>
                    {plugin.description}
                  </span>
                </ResizableTableCell>
                <ResizableTableCell align="right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => handleUpdate(plugin.id)}
                      disabled={updatingPluginId === plugin.id}
                      className="p-2 rounded-lg text-muted hover:text-white hover:bg-dark-hover transition-colors disabled:opacity-50"
                      title="Update plugin"
                    >
                      <span className="material-symbols-outlined text-xl">
                        {updatingPluginId === plugin.id ? 'sync' : 'refresh'}
                      </span>
                    </button>
                    <button
                      onClick={() => handleDeleteClick(plugin)}
                      className="p-2 rounded-lg text-muted hover:text-status-error hover:bg-status-error/10 transition-colors"
                      title="Uninstall plugin"
                    >
                      <span className="material-symbols-outlined text-xl">delete</span>
                    </button>
                  </div>
                </ResizableTableCell>
              </tr>
            ))}
          </ResizableTable>
        )}
      </div>

      {/* Install Modal */}
      <InstallPluginModal
        isOpen={isInstallModalOpen}
        onClose={() => setIsInstallModalOpen(false)}
        onInstall={handleInstall}
        isInstalling={isInstalling}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        title="Uninstall Plugin"
        message={`Are you sure you want to uninstall "${deleteTarget?.name}"? This will also remove all ${deleteTarget?.skillIds.length || 0} associated skill(s).`}
        confirmText="Uninstall"
        variant="danger"
        isLoading={isDeleting}
      />
    </div>
  );
}
