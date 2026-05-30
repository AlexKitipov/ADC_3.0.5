import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/AppShell';
import { FeatureGuard } from '../components/FeatureGuard';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AIControlsPage } from '../pages/AIControlsPage';
import { AuthPage } from '../pages/AuthPage';
import { DashboardPage } from '../pages/DashboardPage';
import { MarketDataPage } from '../pages/MarketDataPage';
import { NotificationsPage } from '../pages/NotificationsPage';
import { SessionsPage } from '../pages/SessionsPage';
import { SettingsPage } from '../pages/SettingsPage';
import { SimulationPage } from '../pages/SimulationPage';
import { SignalsPage } from '../pages/SignalsPage';
import { TradeJournalPage } from '../pages/TradeJournalPage';
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
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route element={<FeatureGuard featureName="Signals" requireSymbols />}>
            <Route path="signals" element={<SignalsPage />} />
          </Route>
          <Route element={<FeatureGuard featureName="Market data" requireSymbols />}>
            <Route path="market-data" element={<MarketDataPage />} />
          </Route>
          <Route element={<FeatureGuard featureName="Trades" requireTradingEnabled />}>
            <Route path="trades" element={<TradesPage />} />
          </Route>
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="trade-journal" element={<TradeJournalPage />} />
          <Route element={<FeatureGuard featureName="Simulations" requireSymbols />}>
            <Route path="simulations" element={<SimulationPage />} />
          </Route>
          <Route element={<FeatureGuard featureName="RL / LSTM controls" requireSymbols />}>
            <Route path="ai-controls" element={<AIControlsPage />} />
          </Route>
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
