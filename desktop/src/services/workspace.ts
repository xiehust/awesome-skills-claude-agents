import api from './api';
import type { WorkspaceListResponse, WorkspaceFile, WorkspaceFileContent } from '../types';

// Convert snake_case file to camelCase
const fileToCamelCase = (data: Record<string, unknown>): WorkspaceFile => {
  return {
    name: data.name as string,
    type: data.type as 'file' | 'directory',
    size: data.size as number,
    modified: data.modified as string,
  };
};

// Convert snake_case list response to camelCase
const listResponseToCamelCase = (data: Record<string, unknown>): WorkspaceListResponse => {
  const files = (data.files as Record<string, unknown>[]) || [];
  return {
    files: files.map(fileToCamelCase),
    currentPath: data.current_path as string,
    parentPath: (data.parent_path as string | null) ?? null,
  };
};

// Convert snake_case file content to camelCase
const fileContentToCamelCase = (data: Record<string, unknown>): WorkspaceFileContent => {
  return {
    content: data.content as string,
    encoding: data.encoding as 'utf-8' | 'base64',
    size: data.size as number,
    mimeType: data.mime_type as string,
  };
};

export const workspaceService = {
  /**
   * List files and directories in the specified path
   * @param agentId The agent ID
   * @param path Relative path to list (default: ".")
   */
  async listFiles(agentId: string, path: string = '.'): Promise<WorkspaceListResponse> {
    const response = await api.post<Record<string, unknown>>(`/workspace/${agentId}/list`, {
      path,
    });
    return listResponseToCamelCase(response.data);
  },

  /**
   * Read file content
   * @param agentId The agent ID
   * @param path Relative path to the file
   */
  async readFile(agentId: string, path: string): Promise<WorkspaceFileContent> {
    const response = await api.get<Record<string, unknown>>(`/workspace/${agentId}/read`, {
      params: { path },
    });
    return fileContentToCamelCase(response.data);
  },
};
