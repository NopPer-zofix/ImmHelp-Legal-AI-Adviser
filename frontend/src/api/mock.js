// In-memory stand-in for the Flask backend, for `npm run dev:mock`.
// Lets you work on the UI without Postgres, Chroma or an OpenAI key.
import { ApiError } from './http';

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const db = {
  users: [{ id: 1, email: 'demo@immhelp.cy', password: 'demo1234', username: 'Demo User' }],
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
  seq: 10,
};

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
  return { id: u.id, email: u.email, username: u.username };
}

export function createMockApi() {
  return {
    async register({ email, password, username }) {
      await wait(500);
      if (db.users.some((u) => u.email === email)) throw new ApiError('email already registered', 409);
      const user = { id: ++db.seq, email, password, username };
      db.users.push(user);
      return publicUser(user);
    },

    async login({ email, password }) {
      await wait(500);
      const user = db.users.find((u) => u.email === email && u.password === password);
      if (!user) throw new ApiError('invalid email or password', 401);
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
      const chat = { id: ++db.seq, user_id: userId, title: null };
      db.chats.push(chat);
      return { ...chat };
    },

    async ask({ question, chatId }) {
      await wait(900 + Math.random() * 900);
      if (question.trim().length < 10) {
        return {
          answer:
            'Your request is too short for me to properly answer it. Please describe your immigration or study-in-Cyprus question in more detail.',
          topics: [],
        };
      }
      const hit = ANSWERS.find((a) => a.match.test(question));
      const answer = hit?.text ?? 'This is a mock answer. Start the Flask backend and run `npm run dev` for real replies.';
      db.messages.push({ id: ++db.seq, chat_id: chatId, role: 'user', content: question });
      db.messages.push({ id: ++db.seq, chat_id: chatId, role: 'assistant', content: answer });
      return { answer, topics: hit?.topics ?? ['GENERAL'] };
    },

    async renameChat(chatId, title) {
      await wait(150);
      const chat = db.chats.find((c) => c.id === chatId);
      if (chat) chat.title = title;
      return { persisted: true };
    },

    async deleteChat(chatId) {
      await wait(200);
      db.chats = db.chats.filter((c) => c.id !== chatId);
      db.messages = db.messages.filter((m) => m.chat_id !== chatId);
      return { persisted: true };
    },
  };
}
