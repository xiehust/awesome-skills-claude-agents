import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

export default function TenantOnboardingPage() {
  const { user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<'choice' | 'create'>('choice');
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/tenants', { name, slug });
      await refreshUser();
      navigate('/');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const resp = (err as { response: { data: { detail?: string } } }).response;
        setError(resp?.data?.detail || 'Failed to create organization');
      } else {
        setError('Failed to create organization');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleNameChange = (value: string) => {
    setName(value);
    // Auto-generate slug from name
    setSlug(value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''));
  };

  return (
    <div className="min-h-screen bg-[#101622] flex items-center justify-center">
      <div className="bg-[#1a1f2e] rounded-lg p-8 w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">&#127881;</div>
          <h1 className="text-2xl font-bold text-white">Welcome, {user?.name || user?.email}!</h1>
          <p className="text-[#9da6b9] mt-2">
            One more step — you need an organization to get started.
          </p>
        </div>

        {step === 'choice' && (
          <div className="space-y-4">
            <button
              onClick={() => setStep('create')}
              className="w-full bg-[#1e2536] hover:bg-[#252c3f] border border-[#2a2f3e] rounded-lg p-4 text-left transition-colors"
            >
              <div className="text-white font-medium">Create a new organization</div>
              <div className="text-sm text-[#9da6b9] mt-1">
                Set up your own workspace with agents, skills, and API key
              </div>
            </button>

            <div className="text-center text-[#9da6b9] text-sm py-2">
              or ask your team admin to invite you via your email ({user?.email})
            </div>

            <button
              onClick={logout}
              className="w-full text-[#9da6b9] hover:text-white text-sm py-2 transition-colors"
            >
              Sign out and use a different account
            </button>
          </div>
        )}

        {step === 'create' && (
          <form onSubmit={handleCreateTenant} className="space-y-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded p-3 text-red-400 text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm text-[#9da6b9] mb-1">Organization Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="My Team"
                className="w-full bg-[#101622] border border-[#2a2f3e] rounded px-3 py-2 text-white focus:outline-none focus:border-[#2b6cee]"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm text-[#9da6b9] mb-1">URL Slug</label>
              <div className="flex items-center">
                <span className="text-[#9da6b9] text-sm mr-1">org/</span>
                <input
                  type="text"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                  placeholder="my-team"
                  className="flex-1 bg-[#101622] border border-[#2a2f3e] rounded px-3 py-2 text-white focus:outline-none focus:border-[#2b6cee]"
                  required
                  pattern="[a-z0-9][a-z0-9-]*[a-z0-9]"
                  minLength={2}
                />
              </div>
              <p className="text-xs text-[#9da6b9] mt-1">Lowercase letters, numbers, and hyphens only</p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => { setStep('choice'); setError(''); }}
                className="flex-1 border border-[#2a2f3e] hover:bg-[#252c3f] text-white rounded py-2 text-sm transition-colors"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading || !name || !slug}
                className="flex-1 bg-[#2b6cee] hover:bg-[#2b6cee]/80 text-white rounded py-2 font-medium disabled:opacity-50 transition-colors"
              >
                {loading ? 'Creating...' : 'Create Organization'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
