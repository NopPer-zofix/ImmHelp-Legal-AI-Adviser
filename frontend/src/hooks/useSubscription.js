import { useCallback, useEffect, useMemo, useState } from 'react';
import { subscriptionStore } from '../lib/storage';
import { FREE_DAILY_LIMIT } from '../lib/plans';

function todayKey(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function addInterval(date, interval) {
  const next = new Date(date);
  if (interval === 'year') next.setFullYear(next.getFullYear() + 1);
  else next.setMonth(next.getMonth() + 1);
  return next.toISOString();
}

function untilMidnight() {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);
  const hours = Math.floor((midnight - now) / 3_600_000);
  if (hours >= 1) return `in ${hours} ${hours === 1 ? 'hour' : 'hours'}`;
  return 'in less than an hour';
}

// Free users get FREE_DAILY_LIMIT answered questions per calendar day.
// A question counts only once the backend answers it, so failed requests are free.
export function useSubscription(user) {
  const store = useMemo(() => subscriptionStore(user.id), [user.id]);
  const [plan, setPlanState] = useState(() => store.plan());
  const [usage, setUsage] = useState(() => store.usage());
  const [, setTick] = useState(0);

  // Re-render every minute so the counter resets at midnight without a reload
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 60_000);
    return () => clearInterval(t);
  }, []);

  const now = new Date();
  const isPro =
    plan?.status === 'active' || (plan?.status === 'cancelled' && new Date(plan.endsAt) > now);

  const used = usage.day === todayKey(now) ? usage.count : 0;
  const limit = FREE_DAILY_LIMIT;
  const remaining = isPro ? Infinity : Math.max(0, limit - used);

  const setPlan = useCallback(
    (next) => {
      store.setPlan(next);
      setPlanState(next);
    },
    [store],
  );

  const recordMessage = useCallback(() => {
    setUsage((current) => {
      const day = todayKey();
      const next = { day, count: (current.day === day ? current.count : 0) + 1 };
      store.setUsage(next);
      return next;
    });
  }, [store]);

  const subscribe = useCallback(
    ({ interval, cardLast4 }) => {
      const startedAt = new Date().toISOString();
      setPlan({ status: 'active', interval, cardLast4, startedAt, renewsAt: addInterval(startedAt, interval) });
    },
    [setPlan],
  );

  const cancel = useCallback(() => {
    setPlan({ ...plan, status: 'cancelled', endsAt: plan.renewsAt });
  }, [plan, setPlan]);

  const resume = useCallback(() => {
    const { endsAt, ...rest } = plan;
    setPlan({ ...rest, status: 'active' });
  }, [plan, setPlan]);

  return {
    plan: isPro ? plan : null,
    isPro,
    used,
    limit,
    remaining,
    canSend: isPro || remaining > 0,
    resetsIn: untilMidnight(),
    recordMessage,
    subscribe,
    cancel,
    resume,
  };
}
