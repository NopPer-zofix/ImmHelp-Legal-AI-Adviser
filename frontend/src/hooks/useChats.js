import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import { chatPrefs } from '../lib/storage';

// The old Streamlit app saved this greeting as the first message of every chat.
// The new welcome screen replaces it, so it is hidden when old chats load.
const LEGACY_GREETING = 'How can I help you?';

function deriveTitle(messages) {
  const first = messages.find((m) => m.role === 'user');
  if (!first) return 'New chat';
  const text = first.content.replace(/\s+/g, ' ').trim();
  return text.length > 48 ? `${text.slice(0, 47).trimEnd()}…` : text;
}

export function titleOf(chat) {
  return chat.customTitle || deriveTitle(chat.messages);
}

function readHashChatId() {
  const match = window.location.hash.match(/^#chat-(\d+)$/);
  return match ? Number(match[1]) : null;
}

export function useChats(user, { onAnswer } = {}) {
  // Called after every successful answer (the free-message counter uses it)
  const onAnswerRef = useRef(onAnswer);
  onAnswerRef.current = onAnswer;

  const prefs = useMemo(() => chatPrefs(user.id), [user.id]);

  const [chats, setChats] = useState([]);
  const [status, setStatus] = useState('loading'); // loading | ready | error
  const [loadError, setLoadError] = useState('');
  const [activeId, setActiveId] = useState(readHashChatId);
  const [pendingId, setPendingId] = useState(null);
  const [notice, setNotice] = useState('');

  // Async handlers need the latest chats without re-creating on every change
  const chatsRef = useRef(chats);
  chatsRef.current = chats;

  const patchChat = useCallback((id, fn) => {
    setChats((list) => list.map((c) => (c.id === id ? fn(c) : c)));
  }, []);

  const moveToTop = useCallback((id) => {
    setChats((list) => {
      const chat = list.find((c) => c.id === id);
      return chat ? [chat, ...list.filter((c) => c.id !== id)] : list;
    });
  }, []);

  const load = useCallback(async () => {
    setStatus('loading');
    try {
      const hidden = prefs.hidden();
      const list = (await api.listChats(user.id))
        .filter((c) => !hidden.has(c.id))
        .sort((a, b) => b.id - a.id);

      // Messages are loaded up front so the sidebar can title chats by their first question
      const loaded = await Promise.all(
        list.map(async (c) => {
          let messages = [];
          try {
            messages = (await api.listMessages(c.id)).filter(
              (m) => !(m.role === 'assistant' && m.content === LEGACY_GREETING),
            );
          } catch {
            /* show the chat empty rather than failing the whole list */
          }
          return { id: c.id, customTitle: c.title || prefs.title(c.id), messages };
        }),
      );

      setChats(loaded);
      setActiveId((current) => (loaded.some((c) => c.id === current) ? current : null));
      setStatus('ready');
    } catch (err) {
      setLoadError(err.message);
      setStatus('error');
    }
  }, [user.id, prefs]);

  useEffect(() => {
    load();
  }, [load]);

  // Keep the open chat in the URL so a page refresh returns to it
  useEffect(() => {
    const target = activeId ? `#chat-${activeId}` : window.location.pathname + window.location.search;
    window.history.replaceState(null, '', target);
  }, [activeId]);

  const runAsk = useCallback(
    async (chatId, question, history, model) => {
      setPendingId(chatId);
      try {
        const { answer, topics } = await api.ask({ question, history, userId: user.id, chatId, model: model?.id });
        patchChat(chatId, (c) => ({
          ...c,
          messages: [...c.messages, { role: 'assistant', content: answer, topics, model: model?.name }],
        }));
        onAnswerRef.current?.();
      } catch (err) {
        patchChat(chatId, (c) => ({
          ...c,
          messages: [...c.messages, { role: 'assistant', content: err.message, error: true, retry: { question, history, model } }],
        }));
      } finally {
        setPendingId(null);
        moveToTop(chatId);
      }
    },
    [user.id, patchChat, moveToTop],
  );

  const send = useCallback(
    async (text, model) => {
      const question = text.trim();
      if (!question || pendingId) return false;

      let chatId = activeId;
      if (chatId == null) {
        try {
          const chat = await api.createChat(user.id);
          chatId = chat.id;
          setChats((list) => [{ id: chatId, customTitle: null, messages: [] }, ...list]);
          setActiveId(chatId);
        } catch (err) {
          setNotice(`Couldn't start a new chat. ${err.message}`);
          return false;
        }
      }

      const previous = chatsRef.current.find((c) => c.id === chatId)?.messages ?? [];
      const history = previous.filter((m) => !m.error).map(({ role, content }) => ({ role, content }));

      patchChat(chatId, (c) => ({ ...c, messages: [...c.messages, { role: 'user', content: question }] }));
      await runAsk(chatId, question, history, model);
      return true;
    },
    [activeId, pendingId, user.id, patchChat, runAsk],
  );

  const retry = useCallback(
    (chatId) => {
      if (pendingId) return;
      const chat = chatsRef.current.find((c) => c.id === chatId);
      const failed = chat?.messages.at(-1);
      if (!failed?.error) return;
      patchChat(chatId, (c) => ({ ...c, messages: c.messages.slice(0, -1) }));
      runAsk(chatId, failed.retry.question, failed.retry.history, failed.retry.model);
    },
    [pendingId, patchChat, runAsk],
  );

  const rename = useCallback(
    async (chatId, title) => {
      const clean = title.replace(/\s+/g, ' ').trim();
      if (!clean) return;
      patchChat(chatId, (c) => ({ ...c, customTitle: clean }));
      prefs.setTitle(chatId, clean);
      try {
        await api.renameChat(chatId, clean);
      } catch (err) {
        setNotice(`The new name is saved on this device only. ${err.message}`);
      }
    },
    [patchChat, prefs],
  );

  const remove = useCallback(
    async (chatId) => {
      try {
        const { persisted } = await api.deleteChat(chatId);
        if (!persisted) prefs.hide(chatId);
        setChats((list) => list.filter((c) => c.id !== chatId));
        setActiveId((current) => (current === chatId ? null : current));
      } catch (err) {
        setNotice(`Couldn't delete the chat. ${err.message}`);
      }
    },
    [prefs],
  );

  const clearNotice = useCallback(() => setNotice(''), []);
  const startNew = useCallback(() => setActiveId(null), []);

  return {
    chats,
    status,
    loadError,
    reload: load,
    activeChat: chats.find((c) => c.id === activeId) ?? null,
    activeId,
    select: setActiveId,
    startNew,
    pendingId,
    send,
    retry,
    rename,
    remove,
    notice,
    clearNotice,
  };
}
