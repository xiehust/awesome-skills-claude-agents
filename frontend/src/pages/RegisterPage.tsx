import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(email, password, name || undefined);
      navigate('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#101622] flex items-center justify-center">
      <div className="bg-[#1a1f2e] rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-white mb-6">Create Account</h1>
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded p-3 mb-4 text-red-400 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-[#9da6b9] mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-[#101622] border border-[#2a2f3e] rounded px-3 py-2 text-white focus:outline-none focus:border-[#2b6cee]"
            />
          </div>
          <div>
            <label className="block text-sm text-[#9da6b9] mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#101622] border border-[#2a2f3e] rounded px-3 py-2 text-white focus:outline-none focus:border-[#2b6cee]"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-[#9da6b9] mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#101622] border border-[#2a2f3e] rounded px-3 py-2 text-white focus:outline-none focus:border-[#2b6cee]"
              required
              minLength={8}
            />
            <p className="text-xs text-[#9da6b9] mt-1">Min 8 chars, with uppercase, lowercase, and digit</p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#2b6cee] hover:bg-[#2b6cee]/80 text-white rounded py-2 font-medium disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        <p className="text-[#9da6b9] text-sm mt-4 text-center">
          Already have an account?{' '}
          <Link to="/login" className="text-[#2b6cee] hover:underline">Sign In</Link>
        </p>
      </div>
    </div>
  );
}
