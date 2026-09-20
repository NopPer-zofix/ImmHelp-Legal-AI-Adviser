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

// Sponsored slots served with an answer. The backend returns them from /ask but
// deliberately keeps them out of the stored transcript (see select_advertisement in
// server.py), and /messages/<chat> therefore returns none - so without this the slot
// vanished from an answer as soon as the chat was reloaded or switched away from.
//
// Keyed by the answer's position in the chat rather than by message id, because a
// freshly answered message has no id until it comes back from the server.
export function adStore(userId) {
  const key = `immhelp:ads:${userId}`;

  return {
    // → { [answerIndex]: ad }
    forChat: (chatId) => read(key, {})[chatId] ?? {},
    remember(chatId, answerIndex, ad) {
      if (!ad) return;
      const all = read(key, {});
      all[chatId] = { ...(all[chatId] ?? {}), [answerIndex]: ad };
      write(key, all);
    },
    forget(chatId) {
      const all = read(key, {});
      if (!(chatId in all)) return;
      delete all[chatId];
      write(key, all);
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

// Record of the accepted registration notice. The backend has no column for it yet,
// so it is also sent with POST /users (ignored by the current server) for later use.
export const consentRecord = {
  save: (userId, record) => write(`immhelp:consent:${userId}`, record),
  load: (userId) => read(`immhelp:consent:${userId}`, null),
};

// Last model the user picked
export const modelPref = {
  load: (userId) => read(`immhelp:model:${userId}`, null),
  save: (userId, modelId) => write(`immhelp:model:${userId}`, modelId),
};
