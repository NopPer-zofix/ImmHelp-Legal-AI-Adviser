// Everything the browser remembers between visits. All access is guarded:
// storage can be disabled (private mode, strict settings) and the app must still work.

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable — keep working in memory */
  }
}

const USER_KEY = 'immhelp:user';

export const session = {
  load: () => read(USER_KEY, null),
  save: (user) => write(USER_KEY, user),
  clear: () => write(USER_KEY, null),
};

// Chat names and deletions the backend can't store yet (no title column,
// no DELETE endpoint). Kept per user, per browser.
export function chatPrefs(userId) {
  const titlesKey = `immhelp:titles:${userId}`;
  const hiddenKey = `immhelp:hidden:${userId}`;

  return {
    title: (chatId) => read(titlesKey, {})[chatId] ?? null,
    setTitle(chatId, title) {
      const all = read(titlesKey, {});
      all[chatId] = title;
      write(titlesKey, all);
    },
    hidden: () => new Set(read(hiddenKey, [])),
    hide(chatId) {
      const all = read(hiddenKey, []);
      if (!all.includes(chatId)) write(hiddenKey, [...all, chatId]);
    },
  };
}

// Paid-access mock-up: the plan and today's message count live in the browser.
// Replace with a backend /subscription endpoint before taking real payments.
export function subscriptionStore(userId) {
  const planKey = `immhelp:plan:${userId}`;
  const usageKey = `immhelp:usage:${userId}`;

  return {
    plan: () => read(planKey, null),
    setPlan: (plan) => write(planKey, plan),
    usage: () => read(usageKey, { day: '', count: 0 }),
    setUsage: (usage) => write(usageKey, usage),
  };
}
