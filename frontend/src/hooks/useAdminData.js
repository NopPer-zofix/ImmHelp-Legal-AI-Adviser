import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

function explain(err) {
  if (err.status === 404 || err.status === 405) {
    return "This server doesn't have the admin API yet. Add the /admin routes to the backend, or preview with npm run dev:mock.";
  }
  if (err.status === 401 || err.status === 403) return 'The server refused access. Log in again with an admin account.';
  return err.message;
}

export function useAdminData() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState(null);
  const [top, setTop] = useState(null);
  const [days, setDays] = useState(7);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);

  const loadTop = useCallback(async (d) => {
    setTop(null);
    try {
      setTop(await api.adminTopQuestions({ days: d, limit: 10 }));
    } catch (err) {
      setError(explain(err));
    }
  }, []);

  const loadCore = useCallback(async () => {
    try {
      const [s, u] = await Promise.all([api.adminStats(), api.adminUsers()]);
      setStats(s);
      setUsers(u);
      setUpdatedAt(new Date());
      setError('');
    } catch (err) {
      setError(explain(err));
    }
  }, []);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    loadTop(days);
  }, [days, loadTop]);

  const refresh = () => {
    loadCore();
    loadTop(days);
  };

  const ban = async (userId, reason) => {
    await api.adminBanUser(userId, reason);
    await loadCore();
  };

  const unban = async (userId) => {
    await api.adminUnbanUser(userId);
    await loadCore();
  };

  return { stats, users, top, days, setDays, error, updatedAt, refresh, ban, unban };
}
