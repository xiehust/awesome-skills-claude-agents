import api from './api';
import type { Plugin, PluginInstallRequest, PluginUpdateRequest } from '../types';

// Convert camelCase to snake_case for API requests
const toSnakeCaseInstall = (data: PluginInstallRequest) => {
  return {
    git_url: data.gitUrl,
    git_ref: data.gitRef,
  };
};

const toSnakeCaseUpdate = (data: PluginUpdateRequest) => {
  return {
    git_ref: data.gitRef,
  };
};

// Convert snake_case response to camelCase
const toCamelCase = (data: Record<string, unknown>): Plugin => {
  return {
    id: data.id as string,
    name: data.name as string,
    description: data.description as string,
    gitUrl: data.git_url as string,
    gitRef: data.git_ref as string,
    version: data.version as string,
    author: data.author as string,
    createdAt: data.created_at as string,
    updatedAt: data.updated_at as string,
    skillIds: (data.skill_ids as string[]) ?? [],
    status: data.status as 'installed' | 'updating' | 'error',
    errorMessage: data.error_message as string | undefined,
    marketplace: data.marketplace as string | undefined,
  };
};

interface PluginListResponse {
  plugins: Record<string, unknown>[];
  total: number;
}

export const pluginsService = {
  // List all installed plugins
  async list(): Promise<Plugin[]> {
    const response = await api.get<PluginListResponse>('/plugins');
    return response.data.plugins.map(toCamelCase);
  },

  // Get plugin by ID
  async get(id: string): Promise<Plugin> {
    const response = await api.get<Record<string, unknown>>(`/plugins/${id}`);
    return toCamelCase(response.data);
  },

  // Install plugin from git URL
  async install(data: PluginInstallRequest): Promise<Plugin> {
    const response = await api.post<Record<string, unknown>>('/plugins/install', toSnakeCaseInstall(data));
    return toCamelCase(response.data);
  },

  // Update installed plugin
  async update(id: string, data?: PluginUpdateRequest): Promise<Plugin> {
    const body = data ? toSnakeCaseUpdate(data) : {};
    const response = await api.post<Record<string, unknown>>(`/plugins/${id}/update`, body);
    return toCamelCase(response.data);
  },

  // Uninstall plugin
  async uninstall(id: string): Promise<void> {
    await api.delete(`/plugins/${id}`);
  },
};
