import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Button, Spinner, Dropdown } from '../components/common';
import type { DropdownOption } from '../components/common';
import { settingsService, type Settings, type SettingsUpdateRequest } from '../services/settings';

// AWS Regions for dropdown
const AWS_REGIONS: DropdownOption[] = [
  { id: 'us-east-1', name: 'US East (N. Virginia)', description: 'us-east-1' },
  { id: 'us-east-2', name: 'US East (Ohio)', description: 'us-east-2' },
  { id: 'us-west-1', name: 'US West (N. California)', description: 'us-west-1' },
  { id: 'us-west-2', name: 'US West (Oregon)', description: 'us-west-2' },
  { id: 'eu-west-1', name: 'EU (Ireland)', description: 'eu-west-1' },
  { id: 'eu-west-2', name: 'EU (London)', description: 'eu-west-2' },
  { id: 'eu-central-1', name: 'EU (Frankfurt)', description: 'eu-central-1' },
  { id: 'ap-northeast-1', name: 'Asia Pacific (Tokyo)', description: 'ap-northeast-1' },
  { id: 'ap-southeast-1', name: 'Asia Pacific (Singapore)', description: 'ap-southeast-1' },
  { id: 'ap-southeast-2', name: 'Asia Pacific (Sydney)', description: 'ap-southeast-2' },
];

// Auth method options
type BedrockAuthMethod = 'credentials' | 'bearer_token';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form state
  const [anthropicBaseUrl, setAnthropicBaseUrl] = useState('');
  const [anthropicApiKey, setAnthropicApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [claudeCodeUseBedrock, setClaudeCodeUseBedrock] = useState(false);
  const [bedrockAuthMethod, setBedrockAuthMethod] = useState<BedrockAuthMethod>('credentials');
  const [awsRegion, setAwsRegion] = useState('us-west-2');
  // Credentials auth
  const [awsAccessKeyId, setAwsAccessKeyId] = useState('');
  const [awsSecretAccessKey, setAwsSecretAccessKey] = useState('');
  const [showSecretKey, setShowSecretKey] = useState(false);
  const [awsSessionToken, setAwsSessionToken] = useState('');
  const [showSessionToken, setShowSessionToken] = useState(false);
  // Bearer token auth
  const [awsBearerToken, setAwsBearerToken] = useState('');
  const [showBearerToken, setShowBearerToken] = useState(false);

  // Load settings on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await settingsService.get();
        setSettings(data);
        setAnthropicBaseUrl(data.anthropicBaseUrl || '');
        setClaudeCodeUseBedrock(data.claudeCodeUseBedrock);
        setBedrockAuthMethod(data.bedrockAuthMethod);
        setAwsRegion(data.awsRegion);
        setAwsAccessKeyId(data.awsAccessKeyId || '');
      } catch (err) {
        setError('Failed to load settings');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  // Clear success message after 3 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);

    const updates: SettingsUpdateRequest = {
      anthropicBaseUrl: anthropicBaseUrl || null,
      claudeCodeUseBedrock,
      bedrockAuthMethod,
      awsRegion,
    };

    // Only include API key if changed
    if (anthropicApiKey) {
      updates.anthropicApiKey = anthropicApiKey;
    }

    if (claudeCodeUseBedrock) {
      if (bedrockAuthMethod === 'credentials') {
        updates.awsAccessKeyId = awsAccessKeyId || null;
        if (awsSecretAccessKey) {
          updates.awsSecretAccessKey = awsSecretAccessKey;
        }
        if (awsSessionToken) {
          updates.awsSessionToken = awsSessionToken;
        }
        // Clear bearer token when using credentials
        updates.awsBearerToken = null;
      } else {
        // bearer_token
        if (awsBearerToken) {
          updates.awsBearerToken = awsBearerToken;
        }
        // Clear credentials when using bearer token
        updates.awsAccessKeyId = null;
        updates.awsSecretAccessKey = null;
        updates.awsSessionToken = null;
      }
    }

    try {
      const updated = await settingsService.update(updates);
      setSettings(updated);
      setSuccessMessage('Settings saved successfully');
      // Clear password fields after save
      setAnthropicApiKey('');
      setAwsSecretAccessKey('');
      setAwsSessionToken('');
      setAwsBearerToken('');
    } catch (err) {
      setError('Failed to save settings');
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-muted mt-1">Configure API credentials and runtime settings.</p>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-green-500">check_circle</span>
            <span className="text-green-500">{successMessage}</span>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-red-500">error</span>
            <span className="text-red-500">{error}</span>
          </div>
        </div>
      )}

      {/* API Provider Toggle */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">API Provider</h2>

        <div className="flex items-center justify-between p-4 bg-dark-bg rounded-lg">
          <div>
            <label className="block text-sm font-medium text-white">Use AWS Bedrock</label>
            <p className="text-xs text-muted mt-0.5">
              Switch between Anthropic API and AWS Bedrock for Claude models
            </p>
          </div>
          <button
            type="button"
            onClick={() => setClaudeCodeUseBedrock(!claudeCodeUseBedrock)}
            className={clsx(
              'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
              claudeCodeUseBedrock ? 'bg-primary' : 'bg-dark-border'
            )}
          >
            <span
              className={clsx(
                'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                claudeCodeUseBedrock ? 'translate-x-5' : 'translate-x-0'
              )}
            />
          </button>
        </div>
      </div>

      {/* Anthropic API Settings */}
      {!claudeCodeUseBedrock && (
        <div className="bg-dark-card border border-dark-border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4">Anthropic API</h2>

          <div className="space-y-4">
            {/* Base URL */}
            <div>
              <label className="block text-sm font-medium text-muted mb-2">
                Base URL (Optional)
              </label>
              <input
                type="text"
                value={anthropicBaseUrl}
                onChange={(e) => setAnthropicBaseUrl(e.target.value)}
                placeholder="https://api.anthropic.com"
                className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-white placeholder:text-muted focus:outline-none focus:border-primary"
              />
              <p className="text-xs text-muted mt-1">
                Leave empty to use default Anthropic API endpoint
              </p>
            </div>

            {/* API Key */}
            <div>
              <label className="block text-sm font-medium text-muted mb-2">
                API Key
                {settings?.anthropicApiKeySet && (
                  <span className="ml-2 text-xs text-green-500">(configured)</span>
                )}
              </label>
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={anthropicApiKey}
                  onChange={(e) => setAnthropicApiKey(e.target.value)}
                  placeholder={settings?.anthropicApiKeySet ? '********' : 'sk-ant-...'}
                  className="w-full px-4 py-2 pr-12 bg-dark-bg border border-dark-border rounded-lg text-white placeholder:text-muted focus:outline-none focus:border-primary"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-white"
                >
                  <span className="material-symbols-outlined text-xl">
                    {showApiKey ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>
              <p className="text-xs text-muted mt-1">
                Enter a new key to update, leave empty to keep existing
              </p>
            </div>
          </div>
        </div>
      )}

      {/* AWS Bedrock Settings */}
      {claudeCodeUseBedrock && (
        <div className="bg-dark-card border border-dark-border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4">AWS Bedrock</h2>

          <div className="space-y-4">
            {/* Region */}
            <Dropdown
              label="AWS Region"
              options={AWS_REGIONS}
              selectedId={awsRegion}
              onChange={setAwsRegion}
              placeholder="Select a region..."
            />

            {/* Auth Method Selection */}
            <div>
              <label className="block text-sm font-medium text-muted mb-3">
                Authentication Method
              </label>
              <div className="flex gap-4">
                <label
                  className={clsx(
                    'flex-1 flex items-center gap-3 p-4 rounded-lg border cursor-pointer transition-colors',
                    bedrockAuthMethod === 'credentials'
                      ? 'bg-primary/10 border-primary'
                      : 'bg-dark-bg border-dark-border hover:border-dark-hover'
                  )}
                >
                  <input
                    type="radio"
                    name="authMethod"
                    value="credentials"
                    checked={bedrockAuthMethod === 'credentials'}
                    onChange={() => setBedrockAuthMethod('credentials')}
                    className="sr-only"
                  />
                  <div
                    className={clsx(
                      'w-5 h-5 rounded-full border-2 flex items-center justify-center',
                      bedrockAuthMethod === 'credentials'
                        ? 'border-primary bg-primary'
                        : 'border-dark-border bg-dark-bg'
                    )}
                  >
                    {bedrockAuthMethod === 'credentials' && (
                      <div className="w-2 h-2 rounded-full bg-white" />
                    )}
                  </div>
                  <div>
                    <div className="text-white font-medium">AWS Credentials</div>
                    <div className="text-xs text-muted">Access Key ID & Secret</div>
                  </div>
                </label>

                <label
                  className={clsx(
                    'flex-1 flex items-center gap-3 p-4 rounded-lg border cursor-pointer transition-colors',
                    bedrockAuthMethod === 'bearer_token'
                      ? 'bg-primary/10 border-primary'
                      : 'bg-dark-bg border-dark-border hover:border-dark-hover'
                  )}
                >
                  <input
                    type="radio"
                    name="authMethod"
                    value="bearer_token"
                    checked={bedrockAuthMethod === 'bearer_token'}
                    onChange={() => setBedrockAuthMethod('bearer_token')}
                    className="sr-only"
                  />
                  <div
                    className={clsx(
                      'w-5 h-5 rounded-full border-2 flex items-center justify-center',
                      bedrockAuthMethod === 'bearer_token'
                        ? 'border-primary bg-primary'
                        : 'border-dark-border bg-dark-bg'
                    )}
                  >
                    {bedrockAuthMethod === 'bearer_token' && (
                      <div className="w-2 h-2 rounded-full bg-white" />
                    )}
                  </div>
                  <div>
                    <div className="text-white font-medium">Bearer Token</div>
                    <div className="text-xs text-muted">JWT/OIDC Token</div>
                  </div>
                </label>
              </div>
            </div>

            {/* Credentials Auth Fields */}
            {bedrockAuthMethod === 'credentials' && (
              <div className="space-y-4 pt-2">
                {/* Access Key ID */}
                <div>
                  <label className="block text-sm font-medium text-muted mb-2">
                    Access Key ID
                  </label>
                  <input
                    type="text"
                    value={awsAccessKeyId}
                    onChange={(e) => setAwsAccessKeyId(e.target.value)}
                    placeholder="AKIAIOSFODNN7EXAMPLE"
                    className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-white placeholder:text-muted focus:outline-none focus:border-primary"
                  />
                </div>

                {/* Secret Access Key */}
                <div>
                  <label className="block text-sm font-medium text-muted mb-2">
                    Secret Access Key
                    {settings?.awsSecretAccessKeySet && (
                      <span className="ml-2 text-xs text-green-500">(configured)</span>
                    )}
                  </label>
                  <div className="relative">
                    <input
                      type={showSecretKey ? 'text' : 'password'}
                      value={awsSecretAccessKey}
                      onChange={(e) => setAwsSecretAccessKey(e.target.value)}
                      placeholder={settings?.awsSecretAccessKeySet ? '********' : 'wJalrXUtnFEMI/K7MDENG/...'}
                      className="w-full px-4 py-2 pr-12 bg-dark-bg border border-dark-border rounded-lg text-white placeholder:text-muted focus:outline-none focus:border-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecretKey(!showSecretKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-white"
                    >
                      <span className="material-symbols-outlined text-xl">
                        {showSecretKey ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                {/* Session Token (Optional) */}
                <div>
                  <label className="block text-sm font-medium text-muted mb-2">
                    Session Token (Optional)
                    {settings?.awsSessionTokenSet && (
                      <span className="ml-2 text-xs text-green-500">(configured)</span>
                    )}
                  </label>
                  <div className="relative">
                    <input
                      type={showSessionToken ? 'text' : 'password'}
                      value={awsSessionToken}
                      onChange={(e) => setAwsSessionToken(e.target.value)}
                      placeholder="For temporary credentials"
                      className="w-full px-4 py-2 pr-12 bg-dark-bg border border-dark-border rounded-lg text-white placeholder:text-muted focus:outline-none focus:border-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSessionToken(!showSessionToken)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-white"
                    >
                      <span className="material-symbols-outlined text-xl">
                        {showSessionToken ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                  <p className="text-xs text-muted mt-1">
                    Only required for temporary/federated credentials
                  </p>
                </div>
              </div>
            )}

            {/* Bearer Token Auth Fields */}
            {bedrockAuthMethod === 'bearer_token' && (
              <div className="space-y-4 pt-2">
                <div>
                  <label className="block text-sm font-medium text-muted mb-2">
                    Bearer Token
                    {settings?.awsBearerTokenSet && (
                      <span className="ml-2 text-xs text-green-500">(configured)</span>
                    )}
                  </label>
                  <div className="relative">
                    <input
                      type={showBearerToken ? 'text' : 'password'}
                      value={awsBearerToken}
                      onChange={(e) => setAwsBearerToken(e.target.value)}
                      placeholder={settings?.awsBearerTokenSet ? '********' : 'eyJhbGciOiJSUzI1NiIs...'}
                      className="w-full px-4 py-2 pr-12 bg-dark-bg border border-dark-border rounded-lg text-white placeholder:text-muted focus:outline-none focus:border-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowBearerToken(!showBearerToken)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-white"
                    >
                      <span className="material-symbols-outlined text-xl">
                        {showBearerToken ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                  <p className="text-xs text-muted mt-1">
                    JWT token for AWS Bedrock authentication
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} isLoading={isSaving} disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </div>
  );
}
