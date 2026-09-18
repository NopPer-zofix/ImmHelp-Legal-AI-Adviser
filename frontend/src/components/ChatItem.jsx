import { useCallback, useRef, useState } from 'react';
import { Ellipsis, Pencil, Trash2 } from 'lucide-react';
import { useDismiss } from '../hooks/useDismiss';

export default function ChatItem({ title, active, busy, onSelect, onRename, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const committed = useRef(false);
  const wrapRef = useRef(null);

  const closeMenu = useCallback(() => setMenuOpen(false), []);
  useDismiss(menuOpen, closeMenu, wrapRef);

  const startEditing = () => {
    setMenuOpen(false);
    setDraft(title);
    committed.current = false;
    setEditing(true);
  };

  // Enter and blur both commit; the ref stops the second one from firing twice
  const commit = () => {
    if (committed.current) return;
    committed.current = true;
    setEditing(false);
    if (draft.trim() && draft.trim() !== title) onRename(draft);
  };

  if (editing) {
    return (
      <li className="chat-item is-editing">
        <input
          className="chat-rename"
          value={draft}
          autoFocus
          onFocus={(e) => e.target.select()}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') {
              committed.current = true;
              setEditing(false);
            }
          }}
          aria-label="Chat name"
          maxLength={80}
        />
      </li>
    );
  }

  return (
    <li ref={wrapRef} className={`chat-item${active ? ' is-active' : ''}${menuOpen ? ' has-menu' : ''}`}>
      <button className="chat-link" onClick={onSelect} aria-current={active ? 'page' : undefined} title={title}>
        {busy && <span className="chat-busy" aria-label="Waiting for an answer" />}
        <span className="chat-title">{title}</span>
      </button>
      <button
        className="chat-more"
        aria-label={`Options for ${title}`}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((v) => !v)}
      >
        <Ellipsis size={16} />
      </button>

      {menuOpen && (
        <div className="menu" role="menu">
          <button role="menuitem" onClick={startEditing}>
            <Pencil size={15} /> Rename
          </button>
          <button
            role="menuitem"
            className="is-danger"
            onClick={() => {
              setMenuOpen(false);
              onDelete();
            }}
          >
            <Trash2 size={15} /> Delete
          </button>
        </div>
      )}
    </li>
  );
}
