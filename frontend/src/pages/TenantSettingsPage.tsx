import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

interface TenantInfo {
  id: string;
  name: string;
  slug: string;
  plan: string;
  apiKeySet: boolean;
  useBedrock: boolean;
  maxAgents: number;
  maxSkills: number;
  status: string;
}

export default function TenantSettingsPage() {
  const { user } = useAuth();
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.get('/tenants/current').then(({ data }) => {
      setTenant({
        id: data.id,
        name: data.name,
        slug: data.slug,
        plan: data.plan,
        apiKeySet: data.api_key_set,
        useBedrock: data.use_bedrock,
        maxAgents: data.max_agents,
        maxSkills: data.max_skills,
        status: data.status,
      });
    }).catch(() => setTenant(null));
  }, []);

  const handleSaveApiKey = async () => {
    if (!apiKey) return;
    setSaving(true);
    setMessage('');
    try {
      await api.put('/tenants/current/api-key', {
        anthropic_api_key: apiKey,
        use_bedrock: tenant?.useBedrock || false,
      });
      setMessage('API key updated successfully');
      setApiKey('');
      if (tenant) setTenant({ ...tenant, apiKeySet: true });
    } catch {
      setMessage('Failed to update API key');
    } finally {
      setSaving(false);
    }
  };

  if (!tenant) {
    return (
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold mb-4">Tenant Settings</h1>
        <p className="text-[#9da6b9]">No tenant configured. Create one to get started.</p>
      </div>
    );
  }

  return (
    <div className="p-6 text-white max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Tenant Settings</h1>

      <div className="bg-[#1a1f2e] rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Organization Info</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-[#9da6b9]">Name</span>
            <span>{tenant.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#9da6b9]">Slug</span>
            <span>{tenant.slug}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#9da6b9]">Plan</span>
            <span className="capitalize">{tenant.plan}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#9da6b9]">Status</span>
            <span className="capitalize">{tenant.status}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#9da6b9]">Your Role</span>
            <span className="capitalize">{user?.role}</span>
          </div>
        </div>
      </div>

      <div className="bg-[#1a1f2e] rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">API Key</h2>
        <p className="text-sm text-[#9da6b9] mb-3">
          {tenant.apiKeySet ? 'API key is configured.' : 'No API key set. Configure one to use Claude.'}
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-ant-..."
            className="flex-1 bg-[#101622] border border-[#2a2f3e] rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-[#2b6cee]"
          />
          <button
            onClick={handleSaveApiKey}
            disabled={saving || !apiKey}
            className="bg-[#2b6cee] hover:bg-[#2b6cee]/80 text-white rounded px-4 py-2 text-sm disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
        {message && <p className="text-sm mt-2 text-green-400">{message}</p>}
      </div>

      <div className="bg-[#1a1f2e] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Limits</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-[#9da6b9]">Max Agents</span>
            <span>{tenant.maxAgents}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#9da6b9]">Max Skills</span>
            <span>{tenant.maxSkills}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
