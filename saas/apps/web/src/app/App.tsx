import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/AppShell';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AuthPage } from '../pages/AuthPage';
import { DashboardPage } from '../pages/DashboardPage';
import { SettingsPage } from '../pages/SettingsPage';
import { SignalsPage } from '../pages/SignalsPage';
import { TradesPage } from '../pages/TradesPage';
import { useAuthStore } from '../store/authStore';

export function App() {
  const { loadCurrentUser } = useAuthStore();

  useEffect(() => {
    loadCurrentUser().catch(() => undefined);
  }, [loadCurrentUser]);

  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="signals" element={<SignalsPage />} />
          <Route path="trades" element={<TradesPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
