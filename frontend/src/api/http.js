// Thin wrapper over the Flask backend (IMMHelpBackend/server.py).
// Every function mirrors one helper from the old Streamlit main.py.

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

const ASSISTANT_PREFIX = '[assistant] ';

export function createHttpApi(baseUrl) {
  async function request(path, { method = 'GET', body, timeout = 15000 } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    try {
      const res = await fetch(baseUrl + path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      // Flask answers 404/405 with HTML, so the body is not always JSON
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new ApiError(data?.error || `The server responded with status ${res.status}.`, res.status);
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
    register: ({ email, password, username }) =>
      request('/users', { method: 'POST', body: { email, password, username } }),

    login: ({ email, password }) =>
      request('/login', { method: 'POST', body: { email, password } }),

    listChats: (userId) => request(`/chats/${userId}`),

    listMessages: async (chatId) => (await request(`/messages/${chatId}`)).map(toMessage),

    createChat: (userId) => request('/chats', { method: 'POST', body: { user_id: userId } }),

    // The router, retrieval and compaction all run inside /ask, so give it room.
    ask: async ({ question, history, userId, chatId }) => {
      const data = await request('/ask', {
        method: 'POST',
        body: { question, history, user_id: userId, chat_id: chatId },
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
