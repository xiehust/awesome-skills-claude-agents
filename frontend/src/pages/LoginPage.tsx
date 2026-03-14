import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#101622] flex items-center justify-center">
      <div className="bg-[#1a1f2e] rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-white mb-6">Sign In</h1>
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded p-3 mb-4 text-red-400 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
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
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#2b6cee] hover:bg-[#2b6cee]/80 text-white rounded py-2 font-medium disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <p className="text-[#9da6b9] text-sm mt-4 text-center">
          Don't have an account?{' '}
          <Link to="/register" className="text-[#2b6cee] hover:underline">Register</Link>
        </p>
      </div>
    </div>
  );
}
