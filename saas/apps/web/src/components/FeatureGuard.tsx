import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { settingsAPI } from '../api/settings';
import { LoadingState } from './LoadingState';
import { EmptyState, ErrorState } from './PageState';

const DEFAULT_MVP_SYMBOLS = ['EURUSD', 'GBPUSD'];

interface FeatureGuardProps {
  requireSymbols?: boolean;
  requireTradingEnabled?: boolean;
  featureName: string;
}

export function resolveConfiguredSymbols(symbols: string[] | null | undefined) {
  const configuredSymbols = (symbols ?? [])
    .map((symbol) => symbol.trim().toUpperCase())
    .filter(Boolean);

  return configuredSymbols.length > 0 ? configuredSymbols : DEFAULT_MVP_SYMBOLS;
}

export function FeatureGuard({ requireSymbols = false, requireTradingEnabled = false, featureName }: FeatureGuardProps) {
  const [status, setStatus] = useState<'loading' | 'ready' | 'blocked' | 'error'>(() => (
    requireSymbols || requireTradingEnabled ? 'loading' : 'ready'
  ));
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!requireSymbols && !requireTradingEnabled) {
      setStatus('ready');
      setMessage('');
      return undefined;
    }

    let isMounted = true;

    settingsAPI.getUserSettings()
      .then((response) => {
        if (!isMounted) {
          return;
        }
        const settings = response.data;
        const configuredSymbols = resolveConfiguredSymbols(settings.symbols);
        if (requireSymbols && configuredSymbols.length === 0) {
          setMessage(`${featureName} needs at least one trading symbol in settings before it can request backend data.`);
          setStatus('blocked');
          return;
        }
        if (requireTradingEnabled && !settings.enable_trading) {
          setMessage(`${featureName} uses automated trading controls, but automated trading is disabled in settings.`);
          setStatus('blocked');
          return;
        }
        setMessage('');
        setStatus('ready');
      })
      .catch((error) => {
        console.error('Failed to evaluate feature guard:', error);
        if (isMounted) {
          setMessage(`Configuration could not be loaded for ${featureName}.`);
          setStatus('error');
        }
      });

    return () => {
      isMounted = false;
    };
  }, [featureName, requireSymbols, requireTradingEnabled]);

  if (status === 'loading') {
    return <LoadingState label={`Checking ${featureName} configuration...`} />;
  }

  if (status === 'error') {
    return <ErrorState title="Configuration unavailable" message={message} />;
  }

  if (status === 'blocked') {
    return (
      <EmptyState
        title={`${featureName} is not configured`}
        message={message}
        actionLabel="Open settings"
        actionTo="/settings"
      />
    );
  }

  return <Outlet />;
}
