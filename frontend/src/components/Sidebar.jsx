import { useState } from 'react';
import { PanelLeftClose, Plus } from 'lucide-react';
import { titleOf } from '../hooks/useChats';
import ChatItem from './ChatItem';
import UserMenu from './UserMenu';
import ConfirmDialog from './ConfirmDialog';

export default function Sidebar({ user, chats, subscription, onUpgrade, onManage, onClose, onNavigate, onLogout }) {
  const [toDelete, setToDelete] = useState(null);

  const select = (id) => {
    chats.select(id);
    onNavigate();
  };

  return (
    <aside className="sidebar" aria-label="Chats">
      <div className="sidebar-head">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">👽</span>
          ImmHelp
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close sidebar">
          <PanelLeftClose size={18} />
        </button>
      </div>

      <button
        className="new-chat"
        onClick={() => {
          chats.startNew();
          onNavigate();
        }}
      >
        <span className="new-chat-icon">
          <Plus size={16} strokeWidth={2.25} />
        </span>
        New chat
      </button>

      <nav className="recents" aria-labelledby="recents-heading">
        <h2 id="recents-heading" className="recents-heading">
          Recents
        </h2>

        {chats.status === 'loading' && <p className="sidebar-note">Loading your chats…</p>}

        {chats.status === 'error' && (
          <div className="sidebar-note">
            <p>Couldn't load your chats. {chats.loadError}</p>
            <button className="link-btn" onClick={chats.reload}>
              Try again
            </button>
          </div>
        )}

        {chats.status === 'ready' && chats.chats.length === 0 && (
          <p className="sidebar-note">Your conversations will appear here.</p>
        )}

        <ul className="chat-list">
          {chats.chats.map((chat) => (
            <ChatItem
              key={chat.id}
              title={titleOf(chat)}
              active={chat.id === chats.activeId}
              busy={chat.id === chats.pendingId}
              onSelect={() => select(chat.id)}
              onRename={(title) => chats.rename(chat.id, title)}
              onDelete={() => setToDelete(chat)}
            />
          ))}
        </ul>
      </nav>

      <UserMenu user={user} subscription={subscription} onUpgrade={onUpgrade} onManage={onManage} onLogout={onLogout} />

      <ConfirmDialog
        open={toDelete != null}
        title="Delete chat?"
        body={toDelete ? `“${titleOf(toDelete)}” and its messages will be removed from your chats.` : ''}
        confirmLabel="Delete"
        onCancel={() => setToDelete(null)}
        onConfirm={() => {
          chats.remove(toDelete.id);
          setToDelete(null);
        }}
      />
    </aside>
  );
}
