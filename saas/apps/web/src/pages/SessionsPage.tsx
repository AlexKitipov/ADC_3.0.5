import { SessionControls } from '../components/SessionControls';
import { LiveMarketWidget } from '../components/LiveMarketWidget';

export function SessionsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Sessions</h2>
        <p className="mt-2 text-slate-400">
          Create, start, stop, and audit the live automated trading runtime that powers stream ticks and mock-broker activity.
        </p>
      </div>
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <SessionControls />
        <LiveMarketWidget symbol="EURUSD" />
      </section>
    </div>
  );
}
