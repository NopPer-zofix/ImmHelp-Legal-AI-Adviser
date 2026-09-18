// Thin wrapper over the Flask backend (IMMHelpBackend/server.py).
// Every function mirrors one helper from the old Streamlit main.py.

export class ApiError extends Error {
  constructor(message, status = 0, code = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// Fired when the server says the session is no longer valid (expired token, or the
// account was banned). App.jsx listens and logs the user out with this message.
export const AUTH_LOST_EVENT = 'immhelp:auth-lost';

// Login and registration report their own errors in the form
const AUTH_ROUTES = ['/login', '/users'];

const ASSISTANT_PREFIX = '[assistant] ';

// getToken: returns the session token once the backend issues one (JWT). Admin routes must
// check it server-side: the role stored in the browser only decides what the UI shows.
export function createHttpApi(baseUrl, getToken = () => null) {
  async function request(path, { method = 'GET', body, timeout = 15000 } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    const headers = {};
    if (body) headers['Content-Type'] = 'application/json';
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      const res = await fetch(baseUrl + path, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      // Flask answers 404/405 with HTML, so the body is not always JSON
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const error = new ApiError(data?.error || `The server responded with status ${res.status}.`, res.status, data?.code);
        const sessionLost = res.status === 401 || data?.code === 'banned';
        if (sessionLost && !AUTH_ROUTES.includes(path)) {
          window.dispatchEvent(new CustomEvent(AUTH_LOST_EVENT, { detail: error.message }));
        }
        throw error;
      }
      return data;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      if (err.name === 'AbortError') {
        throw new ApiError('The server took too long to respond. Try again in a moment.');
      }
      throw new ApiError("Can't reach the server. Check that the backend is running on port 5000.");
    } finally {
      clearTimeout(timer);
    }
  }

  function toMessage(row) {
    const isAssistant = row.message.startsWith(ASSISTANT_PREFIX);
    return {
      id: row.id,
      role: isAssistant ? 'assistant' : 'user',
      content: isAssistant ? row.message.slice(ASSISTANT_PREFIX.length) : row.message,
    };
  }

  return {
    // Returns the user with `role` and `token`; the server stores the consent version
    register: ({ email, password, username, consent }) =>
      request('/users', { method: 'POST', body: { email, password, username, consent } }),

    login: ({ email, password }) =>
      request('/login', { method: 'POST', body: { email, password } }),

    listChats: (userId) => request(`/chats/${userId}`),

    listMessages: async (chatId) => (await request(`/messages/${chatId}`)).map(toMessage),

    createChat: (userId) => request('/chats', { method: 'POST', body: { user_id: userId } }),

    // The router, retrieval and compaction all run inside /ask, so give it room.
    // `model` is still ignored by the server, which always uses its own OpenAI model
    ask: async ({ question, history, userId, chatId, model }) => {
      const data = await request('/ask', {
        method: 'POST',
        body: { question, history, user_id: userId, chat_id: chatId, model },
        timeout: 90000,
      });
      return { answer: data?.answer ?? 'The server returned an empty answer.', topics: data?.topics ?? [] };
    },

    // The backend has no rename/delete endpoints yet. These try them and report
    // whether the change was stored server-side; if not, the caller keeps it locally.
    renameChat: async (chatId, title) => {
      try {
        await request(`/chats/${chatId}`, { method: 'PATCH', body: { title } });
        return { persisted: true };
      } catch (err) {
        if (err.status === 404 || err.status === 405) return { persisted: false };
        throw err;
      }
    },

    // ----- Admin (IMMHelpBackend/admin_api.py) -----

    // → { users, active_users, banned_users, messages_7d, messages_total }
    adminStats: () => request('/admin/stats'),

    // → [{ question, count }] — user messages grouped after lower-casing and trimming punctuation
    adminTopQuestions: ({ days = 7, limit = 10 } = {}) => request(`/admin/top-questions?days=${days}&limit=${limit}`),

    // → [{ id, email, username, role, created_at, message_count, last_active_at, is_banned, banned_reason, banned_at }]
    adminUsers: () => request('/admin/users'),

    adminBanUser: (userId, reason) => request(`/admin/users/${userId}/ban`, { method: 'POST', body: { reason } }),

    adminUnbanUser: (userId) => request(`/admin/users/${userId}/unban`, { method: 'POST', body: {} }),

    // → [{ id, company, reg_number, website, category, licence_number, contact_name, contact_email,
    //      contact_phone, topics, notes, status, status_reason, checks, created_at, created_by,
    //      reviewed_at, reviewed_by }]
    adminAdvertisers: () => request('/admin/advertisers'),

    adminCreateAdvertiser: (data) => request('/admin/advertisers', { method: 'POST', body: data }),

    // Changing company, registration, category, licence or website on an approved advertiser
    // must move it back to "pending" and clear the checks
    adminUpdateAdvertiser: (id, data) => request(`/admin/advertisers/${id}`, { method: 'PATCH', body: data }),

    // status: approved (requires all checks) | rejected | suspended (reason required) | pending
    adminSetAdvertiserStatus: (id, { status, reason, checks }) =>
      request(`/admin/advertisers/${id}/status`, { method: 'POST', body: { status, reason, checks } }),

    deleteChat: async (chatId) => {
      try {
        await request(`/chats/${chatId}`, { method: 'DELETE' });
        return { persisted: true };
      } catch (err) {
        if (err.status === 404 || err.status === 405) return { persisted: false };
        throw err;
      }
    },
  };
}
