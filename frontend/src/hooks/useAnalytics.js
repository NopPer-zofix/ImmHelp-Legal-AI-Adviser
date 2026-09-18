import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

function explain(err) {
  if (err.status === 404 || err.status === 405) {
    return "This server doesn't have the analytics API yet. Update the backend, or preview with npm run dev:mock.";
  }
  return err.message;
}

const tz = () => new Date().getTimezoneOffset();

// Users and topics for the chosen number of days
export function useTrends(days) {
  const [users, setUsers] = useState(null);
  const [topics, setTopics] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setUsers(null);
    setTopics(null);
    try {
      const [u, t] = await Promise.all([
        api.adminAnalyticsUsers({ days, tz: tz() }),
        api.adminAnalyticsTopics({ days, tz: tz() }),
      ]);
      setUsers(u.days);
      setTopics(t);
      setError('');
    } catch (err) {
      setError(explain(err));
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  return { users, topics, error, reload: load };
}

const LIVE_EVERY_MS = 30_000;

// Live load, refreshed every 30 seconds while the page is visible
export function useLiveLoad(hours) {
  const [load, setLoad] = useState(null);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);

  const fetchLoad = useCallback(async () => {
    try {
      setLoad(await api.adminAnalyticsLoad({ hours }));
      setUpdatedAt(new Date());
      setError('');
    } catch (err) {
      setError(explain(err));
    }
  }, [hours]);

  useEffect(() => {
    fetchLoad();
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') fetchLoad();
    }, LIVE_EVERY_MS);
    return () => clearInterval(timer);
  }, [fetchLoad]);

  return { load, error, updatedAt, refresh: fetchLoad };
}
