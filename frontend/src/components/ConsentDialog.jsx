import { useEffect, useRef, useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import { CONSENT_CHECKBOX, CONSENT_SECTIONS, CONSENT_TITLE } from '../lib/consent';

// Last step of registration: the account is created only after the user ticks the box and agrees.
export default function ConsentDialog({ open, busy, onAgree, onBack }) {
  const ref = useRef(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const dialog = ref.current;
    if (open) {
      setChecked(false);
      if (!dialog.open) dialog.showModal();
    } else if (dialog.open) {
      dialog.close();
    }
  }, [open]);

  const back = () => {
    if (!busy) onBack();
  };

  return (
    <dialog
      ref={ref}
      className="dialog dialog--consent"
      aria-labelledby="consent-title"
      aria-describedby="consent-body"
      onCancel={(e) => {
        e.preventDefault();
        back();
      }}
    >
      <div className="dialog-body">
        <span className="consent-icon" aria-hidden="true">
          <ShieldAlert size={22} />
        </span>
        <h2 id="consent-title" className="consent-title">
          {CONSENT_TITLE}
        </h2>

        <div id="consent-body" className="consent-text" tabIndex={0}>
          {CONSENT_SECTIONS.map((s) => (
            <section key={s.heading}>
              <h3>{s.heading}</h3>
              <p>{s.text}</p>
            </section>
          ))}
        </div>

        <label className="consent-check">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            disabled={busy}
          />
          <span>{CONSENT_CHECKBOX}</span>
        </label>

        <div className="dialog-actions">
          <button className="btn btn-ghost" onClick={back} disabled={busy}>
            Back
          </button>
          <button className="btn btn-primary" onClick={onAgree} disabled={!checked || busy}>
            {busy ? 'Creating account…' : 'Agree and create account'}
          </button>
        </div>
      </div>
    </dialog>
  );
}
