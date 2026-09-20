// In-memory stand-in for the Flask backend, for `npm run dev:mock`.
// Lets you work on the UI without Postgres, Chroma or an OpenAI key.
import { ApiError } from './http';
import { SEED_ADVERTISERS, SEED_USERS, seedMessages } from './mockSeed';
import { mockLoad, mockTopicsSeries, mockUsersSeries } from './mockAnalytics';
import { REVIEWED_FIELDS, approvalBlockers } from '../lib/advertisers';
import { session } from '../lib/storage';

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const db = {
  users: SEED_USERS.map((u) => ({ ...u })),
  chats: [{ id: 1, user_id: 1, title: null }],
  messages: [
    { id: 1, chat_id: 1, role: 'user', content: 'What documents do I need for a student visa in Cyprus?' },
    {
      id: 2,
      chat_id: 1,
      role: 'assistant',
      content:
        'For a student entry permit you usually submit the **MEDU2** application together with:\n\n' +
        '1. A valid passport (at least 6 months beyond your planned stay)\n' +
        '2. The letter of acceptance from your university\n' +
        '3. Proof of paid tuition fees for the first year\n' +
        '4. Bank statements showing you can support yourself\n' +
        '5. Medical insurance and a clean criminal record certificate\n\n' +
        'Check the current list with the Civil Registry and Migration Department before you apply.',
    },
  ],
  seq: 1000,
};
db.advertisers = SEED_ADVERTISERS.map((a) => ({ ...a, created_by: 'Kostia Admin', reviewed_by: a.reviewed_at ? 'Kostia Admin' : null }));
db.messages.forEach((m) => Object.assign(m, { user_id: 1, created_at: new Date().toISOString() }));
db.messages.push(...seedMessages(db.seq));
db.seq += db.messages.length;

function pickAdvertisement(topics) {
  const wanted = new Set((topics ?? []).filter(Boolean).map((t) => t.trim().toUpperCase()));
  if (!wanted.size) return null;

  const matching = db.advertisers.filter(
    (a) => a.status === 'approved' && (a.topics ?? []).some((t) => wanted.has(t.trim().toUpperCase())),
  );
  if (!matching.length) return null;

  const chosen = matching[Math.floor(Math.random() * matching.length)];
  return {
    label: 'Sponsored',
    id: chosen.id,
    company: chosen.company,
    website: chosen.website,
    category: chosen.category,
  };
}

const SUSPENDED = 'This account has been suspended. Contact support if you think this is a mistake.';

function assertActive(userId) {
  if (db.users.find((u) => u.id === userId)?.is_banned) throw new ApiError(SUSPENDED, 403);
}

// Mirrors what the real server must do: look up the caller and check the role on every admin call
function assertAdmin() {
  const me = db.users.find((u) => u.id === session.load()?.id);
  if (!me || me.role !== 'admin' || me.is_banned) throw new ApiError('Admin access required.', 403);
  return me;
}

function normalise(text) {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, '')
    .replace(/\s+/g, ' ')
    .trim();
}

const ANSWERS = [
  {
    match: /student|study|university|medu/i,
    topics: ['VISA'],
    text:
      'For a student entry permit you usually submit the **MEDU2** application together with:\n\n' +
      '1. A valid passport (at least 6 months beyond your planned stay)\n' +
      '2. The letter of acceptance from your university\n' +
      '3. Proof of paid tuition fees for the first year\n' +
      '4. Bank statements showing you can support yourself\n\n' +
      'Check the current list with the Civil Registry and Migration Department before you apply.',
  },
  {
    match: /employer|mdw|domestic/i,
    topics: ['VISA'],
    text:
      'When a domestic worker changes employer, the new employer files a **renewal due to change of employer** (form MDW3) with:\n\n' +
      '- the signed release agreement from the previous employer\n' +
      '- a new employment contract\n' +
      '- the declaration on salary payments\n\n' +
      '> Submit it before the current permit expires to avoid a gap in your legal stay.',
  },
  {
    match: /driv|licen|car|bus/i,
    topics: ['TRANSPORT'],
    text:
      'Visitors can drive with a licence from their home country for a limited period. If you become a resident, ' +
      'you may need to **exchange** it for a Cypriot licence at the Road Transport Department.\n\n' +
      '| Licence from | What to do |\n|---|---|\n| EU / EEA | Valid as is |\n| Other countries | Check exchange rules |',
  },
  {
    match: /rent|flat|apartment|lease|house/i,
    topics: ['REAL_ESTATE'],
    text:
      'Before signing a rental contract, check that:\n\n' +
      '1. The landlord is the registered owner (ask for the title deed)\n' +
      '2. The deposit amount and return conditions are written down\n' +
      '3. The contract is **stamped** at the tax department within 30 days\n\n' +
      'A stamped contract is also something the migration office asks for as proof of address.',
  },
];

function publicUser(u) {
  return { id: u.id, email: u.email, username: u.username, role: u.role ?? 'user' };
}

export function createMockApi() {
  return {
    async register({ email, password, username, consent }) {
      await wait(500);
      if (db.users.some((u) => u.email === email)) throw new ApiError('email already registered', 409);
      const user = { id: ++db.seq, email, password, username, consent, role: 'user', created_at: new Date().toISOString() };
      db.users.push(user);
      return publicUser(user);
    },

    async login({ email, password }) {
      await wait(500);
      const user = db.users.find((u) => u.email === email && u.password === password);
      if (!user) throw new ApiError('invalid email or password', 401);
      if (user.is_banned) throw new ApiError(SUSPENDED, 403);
      return publicUser(user);
    },

    async listChats(userId) {
      await wait(250);
      return db.chats.filter((c) => c.user_id === userId).map((c) => ({ ...c }));
    },

    async listMessages(chatId) {
      await wait(150);
      return db.messages.filter((m) => m.chat_id === chatId).map(({ id, role, content }) => ({ id, role, content }));
    },

    async createChat(userId) {
      await wait(200);
      assertActive(userId);
      const chat = { id: ++db.seq, user_id: userId, title: null };
      db.chats.push(chat);
      return { ...chat };
    },

    async ask({ question, chatId, model, userId }) {
      assertActive(userId);
      // Rough feel of each model's speed
      const base = { 'claude-opus-5': 2000, 'gpt-5': 1100 }[model] ?? 1000;
      await wait(base + Math.random() * 600);
      if (question.trim().length < 10) {
        return {
          answer:
            'Your request is too short for me to properly answer it. Please describe your immigration or study-in-Cyprus question in more detail.',
          topics: [],
          advertisement: null,
        };
      }
      const hit = ANSWERS.find((a) => a.match.test(question));
      const answer = hit?.text ?? 'This is a mock answer. Start the Flask backend and run `npm run dev` for real replies.';
      const now = new Date().toISOString();
      db.messages.push({ id: ++db.seq, chat_id: chatId, user_id: userId, role: 'user', content: question, created_at: now });
      db.messages.push({ id: ++db.seq, chat_id: chatId, user_id: userId, role: 'assistant', content: answer, created_at: now });
      const topics = hit?.topics ?? ['GENERAL'];
      return { answer, topics, advertisement: pickAdvertisement(topics) };
    },

    async renameChat(chatId, title) {
      await wait(150);
      const chat = db.chats.find((c) => c.id === chatId);
      if (chat) chat.title = title;
      return { persisted: true };
    },

    async adminStats() {
      await wait(300);
      assertAdmin();
      const weekAgo = Date.now() - 7 * 86_400_000;
      const userMessages = db.messages.filter((m) => m.role === 'user');
      const banned = db.users.filter((u) => u.is_banned).length;
      return {
        users: db.users.length,
        active_users: db.users.length - banned,
        banned_users: banned,
        messages_7d: userMessages.filter((m) => new Date(m.created_at) > weekAgo).length,
        messages_total: userMessages.length,
      };
    },

    async adminTopQuestions({ days = 7, limit = 10 } = {}) {
      await wait(350);
      assertAdmin();
      const since = days ? Date.now() - days * 86_400_000 : 0;
      const groups = new Map();
      for (const m of db.messages) {
        if (m.role !== 'user' || new Date(m.created_at) < since) continue;
        const key = normalise(m.content);
        if (key.length < 10) continue;
        const g = groups.get(key) ?? { question: m.content, count: 0 };
        g.count += 1;
        if (/^[A-Z]/.test(m.content) && m.content.endsWith('?')) g.question = m.content; // nicest spelling
        groups.set(key, g);
      }
      return [...groups.values()].sort((a, b) => b.count - a.count).slice(0, limit);
    },

    async adminUsers() {
      await wait(350);
      assertAdmin();
      return db.users.map((u) => {
        const mine = db.messages.filter((m) => m.user_id === u.id && m.role === 'user');
        const last = mine.reduce((max, m) => (m.created_at > max ? m.created_at : max), '') || null;
        return {
          ...publicUser(u),
          created_at: u.created_at,
          message_count: mine.length,
          last_active_at: last,
          is_banned: Boolean(u.is_banned),
          banned_reason: u.banned_reason ?? null,
          banned_at: u.banned_at ?? null,
        };
      });
    },

    async adminBanUser(userId, reason) {
      await wait(400);
      const me = assertAdmin();
      const user = db.users.find((u) => u.id === userId);
      if (!user) throw new ApiError('User not found.', 404);
      if (user.id === me.id) throw new ApiError("You can't ban your own account.", 400);
      if (user.role === 'admin') throw new ApiError('Admins can’t be banned. Remove the admin role first.', 400);
      Object.assign(user, { is_banned: true, banned_reason: reason || null, banned_at: new Date().toISOString() });
      return { ok: true };
    },

    async adminUnbanUser(userId) {
      await wait(300);
      assertAdmin();
      const user = db.users.find((u) => u.id === userId);
      if (!user) throw new ApiError('User not found.', 404);
      Object.assign(user, { is_banned: false, banned_reason: null, banned_at: null });
      return { ok: true };
    },

    async adminAnalyticsUsers(params) {
      await wait(350);
      assertAdmin();
      return mockUsersSeries(params);
    },

    async adminAnalyticsTopics(params) {
      await wait(350);
      assertAdmin();
      return mockTopicsSeries(params);
    },

    async adminAnalyticsLoad(params) {
      await wait(250);
      assertAdmin();
      return mockLoad(params);
    },

    async heartbeat() {
      return { ok: true };
    },

    async adminAdvertisers() {
      await wait(300);
      assertAdmin();
      return db.advertisers.map((a) => ({ ...a })).sort((a, b) => b.created_at.localeCompare(a.created_at));
    },

    async adminCreateAdvertiser(data) {
      await wait(400);
      const me = assertAdmin();
      const advertiser = {
        ...data,
        id: ++db.seq,
        status: 'pending',
        status_reason: null,
        checks: {},
        created_at: new Date().toISOString(),
        created_by: me.username,
        reviewed_at: null,
        reviewed_by: null,
      };
      db.advertisers.push(advertiser);
      return { ...advertiser };
    },

    async adminUpdateAdvertiser(id, data) {
      await wait(350);
      assertAdmin();
      const a = db.advertisers.find((x) => x.id === id);
      if (!a) throw new ApiError('Advertiser not found.', 404);
      const needsReview = a.status === 'approved' && REVIEWED_FIELDS.some((f) => f in data && data[f] !== a[f]);
      Object.assign(a, data);
      if (needsReview) Object.assign(a, { status: 'pending', checks: {}, status_reason: 'Details changed after approval' });
      return { ...a, sent_back_to_review: needsReview };
    },

    async adminSetAdvertiserStatus(id, { status, reason, checks }) {
      await wait(350);
      const me = assertAdmin();
      const a = db.advertisers.find((x) => x.id === id);
      if (!a) throw new ApiError('Advertiser not found.', 404);
      if (checks) a.checks = { ...checks };
      if (status === 'approved') {
        const blockers = approvalBlockers(a);
        if (blockers.length) throw new ApiError(blockers[0], 400);
      }
      if ((status === 'rejected' || status === 'suspended') && !reason?.trim()) {
        throw new ApiError('Give a reason.', 400);
      }
      Object.assign(a, {
        status,
        status_reason: reason?.trim() || null,
        reviewed_at: new Date().toISOString(),
        reviewed_by: me.username,
      });
      return { ...a };
    },

    async deleteChat(chatId) {
      await wait(200);
      db.chats = db.chats.filter((c) => c.id !== chatId);
      db.messages = db.messages.filter((m) => m.chat_id !== chatId);
      return { persisted: true };
    },
  };
}
