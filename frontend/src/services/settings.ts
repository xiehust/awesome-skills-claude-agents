import api from './api';

// Settings response type (matches backend SettingsResponse)
export interface Settings {
  anthropicBaseUrl: string | null;
  anthropicApiKeySet: boolean;
  claudeCodeUseBedrock: boolean;
  bedrockAuthMethod: 'credentials' | 'bearer_token';
  awsRegion: string;
  awsAccessKeyId: string | null;
  awsSecretAccessKeySet: boolean;
  awsSessionTokenSet: boolean;
  awsBearerTokenSet: boolean;
  updatedAt: string | null;
}

// Settings update request type
export interface SettingsUpdateRequest {
  anthropicBaseUrl?: string | null;
  anthropicApiKey?: string | null;
  claudeCodeUseBedrock?: boolean;
  bedrockAuthMethod?: 'credentials' | 'bearer_token';
  awsRegion?: string;
  awsAccessKeyId?: string | null;
  awsSecretAccessKey?: string | null;
  awsSessionToken?: string | null;
  awsBearerToken?: string | null;
}

// Convert snake_case to camelCase for responses
const toCamelCase = (data: Record<string, unknown>): Settings => ({
  anthropicBaseUrl: (data.anthropic_base_url as string | null) ?? null,
  anthropicApiKeySet: (data.anthropic_api_key_set as boolean) ?? false,
  claudeCodeUseBedrock: (data.claude_code_use_bedrock as boolean) ?? false,
  bedrockAuthMethod: (data.bedrock_auth_method as 'credentials' | 'bearer_token') ?? 'credentials',
  awsRegion: (data.aws_region as string) ?? 'us-west-2',
  awsAccessKeyId: (data.aws_access_key_id as string | null) ?? null,
  awsSecretAccessKeySet: (data.aws_secret_access_key_set as boolean) ?? false,
  awsSessionTokenSet: (data.aws_session_token_set as boolean) ?? false,
  awsBearerTokenSet: (data.aws_bearer_token_set as boolean) ?? false,
  updatedAt: (data.updated_at as string | null) ?? null,
});

// Convert camelCase to snake_case for requests
const toSnakeCase = (data: SettingsUpdateRequest): Record<string, unknown> => {
  const result: Record<string, unknown> = {};
  if (data.anthropicBaseUrl !== undefined) result.anthropic_base_url = data.anthropicBaseUrl;
  if (data.anthropicApiKey !== undefined) result.anthropic_api_key = data.anthropicApiKey;
  if (data.claudeCodeUseBedrock !== undefined) result.claude_code_use_bedrock = data.claudeCodeUseBedrock;
  if (data.bedrockAuthMethod !== undefined) result.bedrock_auth_method = data.bedrockAuthMethod;
  if (data.awsRegion !== undefined) result.aws_region = data.awsRegion;
  if (data.awsAccessKeyId !== undefined) result.aws_access_key_id = data.awsAccessKeyId;
  if (data.awsSecretAccessKey !== undefined) result.aws_secret_access_key = data.awsSecretAccessKey;
  if (data.awsSessionToken !== undefined) result.aws_session_token = data.awsSessionToken;
  if (data.awsBearerToken !== undefined) result.aws_bearer_token = data.awsBearerToken;
  return result;
};

export const settingsService = {
  async get(): Promise<Settings> {
    const response = await api.get<Record<string, unknown>>('/settings');
    return toCamelCase(response.data);
  },

  async update(data: SettingsUpdateRequest): Promise<Settings> {
    const response = await api.put<Record<string, unknown>>('/settings', toSnakeCase(data));
    return toCamelCase(response.data);
  },
};
