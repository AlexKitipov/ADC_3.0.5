import { FormEvent, useState } from 'react';
import { notificationsAPI } from '../api/notifications';
import { EmptyState, ErrorState, StatusBanner } from '../components/PageState';
import type { NotificationDeliveryResponse } from '../types';

export async function sendNotificationTest(recipients: string, subject: string, body: string) {
  const response = await notificationsAPI.sendTest({
    recipients: recipients.split(',').map((recipient) => recipient.trim()).filter(Boolean),
    subject,
    body,
  });
  return response.data;
}

export function NotificationsPage() {
  const [recipients, setRecipients] = useState('');
  const [subject, setSubject] = useState('ADC notification test');
  const [body, setBody] = useState('This message verifies the configured backend notification delivery channel.');
  const [result, setResult] = useState<NotificationDeliveryResponse | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSending(true);
    setError(null);
    setResult(null);
    try {
      setResult(await sendNotificationTest(recipients, subject, body));
    } catch (sendError) {
      console.error('Failed to send notification test:', sendError);
      setError('Notification test could not be delivered. Check SMTP or backend notification settings.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Advanced/Lab Notifications</h2>
        <p className="mt-2 text-slate-400">Advanced/Lab delivery checks for backend notification tests and metadata outside the general settings form.</p>
      </div>

      {error && <ErrorState message={error} />}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.8fr)]">
        <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <label className="block text-sm font-medium text-slate-300">Recipients<input value={recipients} onChange={(event) => setRecipients(event.target.value)} placeholder="ops@example.com, trader@example.com" className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-brand-500" /></label>
          <label className="block text-sm font-medium text-slate-300">Subject<input value={subject} onChange={(event) => setSubject(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-brand-500" /></label>
          <label className="block text-sm font-medium text-slate-300">Body<textarea value={body} onChange={(event) => setBody(event.target.value)} rows={5} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-brand-500" /></label>
          <button type="submit" disabled={isSending} className="rounded-lg bg-brand-600 px-4 py-2 font-semibold text-white hover:bg-brand-500 disabled:opacity-60">{isSending ? 'Sending...' : 'Send test notification'}</button>
        </form>

        <aside className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h3 className="text-lg font-semibold text-white">Delivery result</h3>
          {result ? (
            <div className="mt-4 space-y-4">
              <StatusBanner tone={result.status === 'sent' ? 'success' : 'error'} message={result.error ?? `Notification ${result.status} to ${result.recipients.join(', ') || 'configured recipients'}.`} />
              <Metric label="Subject" value={result.subject} />
              <Metric label="Attached files" value={result.attached_files.length.toString()} />
              <Metric label="Skipped attachments" value={result.skipped_attachments.length.toString()} />
            </div>
          ) : <EmptyState title="No delivery attempt" message="Send a test to see backend recipients, attachment handling, and error metadata." />}
        </aside>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs uppercase tracking-wider text-slate-500">{label}</p><p className="mt-2 text-sm font-semibold text-white">{value || '—'}</p></div>;
}
