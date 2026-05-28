import { FormEvent, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

interface AuthPageProps {
  mode: 'login' | 'register';
}

export function AuthPage({ mode }: AuthPageProps) {
  const navigate = useNavigate();
  const { token, login, register, isLoading, error } = useAuthStore();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  if (token) {
    return <Navigate to="/" replace />;
  }

  const isRegister = mode === 'register';

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (isRegister) {
      await register(email, username, password);
    } else {
      await login(username, password);
    }
    navigate('/dashboard');
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-12 text-slate-100">
      <section className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl shadow-blue-950/20">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-brand-500">ADC</p>
        <h1 className="mt-3 text-3xl font-bold">{isRegister ? 'Create your account' : 'Sign in'}</h1>
        <p className="mt-2 text-slate-400">
          {isRegister ? 'Start monitoring automated crypto trading performance.' : 'Access your trading dashboard.'}
        </p>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          {isRegister && (
            <label className="block">
              <span className="text-sm text-slate-300">Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
              />
            </label>
          )}
          <label className="block">
            <span className="text-sm text-slate-300">Username</span>
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
            />
          </label>
          <label className="block">
            <span className="text-sm text-slate-300">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
            />
          </label>

          {error && <p className="rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-xl bg-brand-600 px-4 py-3 font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          {isRegister ? 'Already have an account?' : 'Need an account?'}{' '}
          <Link className="font-semibold text-brand-500" to={isRegister ? '/login' : '/register'}>
            {isRegister ? 'Sign in' : 'Register'}
          </Link>
        </p>
      </section>
    </main>
  );
}
