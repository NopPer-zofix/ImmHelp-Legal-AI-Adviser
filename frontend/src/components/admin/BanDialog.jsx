import { useEffect, useRef, useState } from 'react';

export default function BanDialog({ user, onBan, onCancel }) {
  const ref = useRef(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const dialog = ref.current;
    if (user) {
      setReason('');
      setError('');
      setBusy(false);
      if (!dialog.open) dialog.showModal();
    } else if (dialog.open) {
      dialog.close();
    }
  }, [user]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await onBan(user.id, reason.trim());
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-labelledby="ban-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onCancel();
      }}
    >
      {user && (
        <form className="dialog-body" onSubmit={submit}>
          <h2 id="ban-title">Ban {user.username}?</h2>
          <p>
            {user.email} won't be able to log in or ask questions. Their chat history is kept, and you can unban them
            at any time.
          </p>
          <label className="field">
            <span>Reason (only admins see this)</span>
            <textarea
              className="textarea"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Posting advertising links in questions"
              maxLength={300}
              disabled={busy}
              autoFocus
            />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="dialog-actions">
            <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>
              Cancel
            </button>
            <button className="btn btn-danger" disabled={busy}>
              {busy ? 'Banning…' : 'Ban user'}
            </button>
          </div>
        </form>
      )}
    </dialog>
  );
}
