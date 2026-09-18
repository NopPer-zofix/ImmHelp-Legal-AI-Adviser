import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { api } from '../../api';
import {
  AD_CATEGORIES,
  AD_TOPICS,
  REVIEWED_FIELDS,
  approvalBlockers,
  findCategory,
  reviewChecks,
  statusLabel,
} from '../../lib/advertisers';
import { shortDate } from '../../lib/format';

const EMPTY = {
  company: '',
  reg_number: '',
  website: '',
  category: '',
  licence_number: '',
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  topics: [],
  notes: '',
};

const pick = (a) => Object.fromEntries(Object.keys(EMPTY).map((k) => [k, a?.[k] ?? EMPTY[k]]));

function validate(form) {
  const e = {};
  if (!form.company.trim()) e.company = 'Enter the company name.';
  if (!form.reg_number.trim()) e.reg_number = 'Enter the registration number.';
  if (!/^https?:\/\/[^\s.]+\.[^\s]+$/i.test(form.website.trim())) e.website = 'Enter a full address, e.g. https://example.com';
  if (!form.category) e.category = 'Choose a category.';
  if (!form.contact_name.trim()) e.contact_name = 'Enter a contact person.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.contact_email.trim())) e.contact_email = 'Enter a valid email.';
  if (!form.topics.length) e.topics = 'Choose at least one topic.';
  return e;
}

export default function AdvertiserDrawer({ open, advertiser, onClose, onCreated, onSaved }) {
  const ref = useRef(null);

  useEffect(() => {
    const d = ref.current;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="drawer"
      aria-labelledby="adv-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => e.target === ref.current && onClose()}
    >
      {open && (
        <DrawerContent
          key={advertiser?.id ?? 'new'}
          advertiser={advertiser}
          onClose={onClose}
          onCreated={onCreated}
          onSaved={onSaved}
        />
      )}
    </dialog>
  );
}

function DrawerContent({ advertiser, onClose, onCreated, onSaved }) {
  const isNew = !advertiser;
  const [form, setForm] = useState(() => pick(advertiser));
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [apiError, setApiError] = useState('');

  const category = form.category ? findCategory(form.category) : null;
  const dirty = JSON.stringify(form) !== JSON.stringify(pick(advertiser));
  const reReview =
    advertiser?.status === 'approved' && REVIEWED_FIELDS.some((f) => form[f] !== (advertiser[f] ?? ''));

  const set = (field) => (e) => {
    const value = e.target.value;
    setForm((f) => {
      const next = { ...f, [field]: value };
      // New advertiser: pre-fill topics from the category until the admin picks their own
      if (field === 'category' && isNew && f.topics.length === 0) next.topics = findCategory(value).topics;
      return next;
    });
    if (errors[field]) setErrors((x) => ({ ...x, [field]: undefined }));
  };

  const toggleTopic = (id) => {
    setForm((f) => ({ ...f, topics: f.topics.includes(id) ? f.topics.filter((t) => t !== id) : [...f.topics, id] }));
    if (errors.topics) setErrors((x) => ({ ...x, topics: undefined }));
  };

  async function save(e) {
    e.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length) return;

    const data = { ...form, website: form.website.trim(), company: form.company.trim() };
    setSaving(true);
    setApiError('');
    try {
      if (isNew) {
        onCreated(await api.adminCreateAdvertiser(data));
      } else {
        const updated = await api.adminUpdateAdvertiser(advertiser.id, data);
        await onSaved(
          updated.sent_back_to_review
            ? `${updated.company}: key details changed, so it's back in review.`
            : `${updated.company} is saved.`,
        );
      }
    } catch (err) {
      setApiError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const field = (name, label, props = {}) => (
    <label className="field">
      <span>{label}</span>
      <input value={form[name]} onChange={set(name)} aria-invalid={Boolean(errors[name])} {...props} />
      {errors[name] && <em className="field-error">{errors[name]}</em>}
    </label>
  );

  return (
    <div className="drawer-inner">
      <header className="drawer-head">
        <div>
          <h2 id="adv-title">{isNew ? 'New advertiser' : advertiser.company}</h2>
          {!isNew && <span className={`pill pill--${advertiser.status}`}>{statusLabel(advertiser.status)}</span>}
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>
      </header>

      <div className="drawer-body">
        {!isNew && <Review key={advertiser.status} advertiser={advertiser} onSaved={onSaved} disabled={dirty} />}

        <form id="adv-form" className="adv-form" onSubmit={save} noValidate>
          <fieldset>
            <legend>Company</legend>
            {field('company', 'Company name', { placeholder: 'Andreou & Partners LLC' })}
            <div className="field-row">
              {field('reg_number', 'Registration number', { placeholder: 'HE 123456' })}
              <label className="field">
                <span>Category</span>
                <select value={form.category} onChange={set('category')} aria-invalid={Boolean(errors.category)}>
                  <option value="" disabled>
                    Choose…
                  </option>
                  {AD_CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
                {errors.category && <em className="field-error">{errors.category}</em>}
              </label>
            </div>
            {field('website', 'Website', { placeholder: 'https://example.com', inputMode: 'url' })}
            {category?.licence &&
              field('licence_number', `Licence number (${category.licence})`, {
                placeholder: 'Needed before approval',
              })}
          </fieldset>

          <fieldset>
            <legend>Contact</legend>
            {field('contact_name', 'Contact person')}
            <div className="field-row">
              {field('contact_email', 'Email', { type: 'email' })}
              {field('contact_phone', 'Phone (optional)', { type: 'tel', placeholder: '+357' })}
            </div>
          </fieldset>

          <fieldset>
            <legend>Show their ads in answers about</legend>
            <div className="checks-inline">
              {AD_TOPICS.map((t) => (
                <label key={t.id} className="check">
                  <input type="checkbox" checked={form.topics.includes(t.id)} onChange={() => toggleTopic(t.id)} />
                  {t.label}
                </label>
              ))}
            </div>
            {errors.topics && <em className="field-error">{errors.topics}</em>}
          </fieldset>

          <fieldset>
            <legend>Internal notes</legend>
            <textarea
              className="textarea"
              rows={3}
              value={form.notes}
              onChange={set('notes')}
              placeholder="Only admins see this"
              aria-label="Internal notes"
            />
          </fieldset>
        </form>
      </div>

      <footer className="drawer-foot">
        {reReview && (
          <p className="warn">
            <AlertTriangle size={15} aria-hidden="true" /> Saving sends this advertiser back to review.
          </p>
        )}
        {apiError && (
          <p className="form-error" role="alert">
            {apiError}
          </p>
        )}
        <div className="drawer-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            {isNew || !dirty ? 'Close' : 'Discard changes'}
          </button>
          <button className="btn btn-primary" form="adv-form" disabled={saving || (!isNew && !dirty)}>
            {saving ? 'Saving…' : isNew ? 'Add advertiser' : 'Save changes'}
          </button>
        </div>
      </footer>
    </div>
  );
}

// Review checklist and status decisions for an existing advertiser
function Review({ advertiser, onSaved, disabled }) {
  const [checks, setChecks] = useState(advertiser.checks ?? {});
  const [action, setAction] = useState(null); // 'rejected' | 'suspended' while asking for a reason
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const list = reviewChecks(advertiser.category);
  const blockers = approvalBlockers({ ...advertiser, checks });
  const complete = blockers.length === 0;
  const { status } = advertiser;

  const toggle = async (id) => {
    const next = { ...checks, [id]: !checks[id] };
    setChecks(next);
    try {
      await api.adminUpdateAdvertiser(advertiser.id, { checks: next });
    } catch (err) {
      setError(`Couldn't save the checklist. ${err.message}`);
    }
  };

  async function decide(nextStatus, withReason) {
    setBusy(true);
    setError('');
    try {
      const updated = await api.adminSetAdvertiserStatus(advertiser.id, {
        status: nextStatus,
        reason: withReason ? reason : undefined,
        checks,
      });
      setAction(null);
      setReason('');
      await onSaved(`${updated.company}: ${statusLabel(updated.status).toLowerCase()}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const canCheck = status === 'pending' || status === 'suspended';

  return (
    <section className="review" aria-labelledby="review-h">
      <h3 id="review-h">Review</h3>

      {advertiser.reviewed_by && (
        <p className="review-meta">
          {statusLabel(status)} by {advertiser.reviewed_by} on {shortDate(advertiser.reviewed_at)}
          {advertiser.status_reason && <>: “{advertiser.status_reason}”</>}
        </p>
      )}
      {!advertiser.reviewed_by && advertiser.status_reason && <p className="review-meta">{advertiser.status_reason}</p>}

      <ul className="review-checks">
        {list.map((c) => (
          <li key={c.id}>
            <label className="check">
              <input
                type="checkbox"
                checked={Boolean(checks[c.id])}
                onChange={() => toggle(c.id)}
                disabled={!canCheck || busy}
              />
              {c.label}
            </label>
          </li>
        ))}
      </ul>

      {action ? (
        <div className="reason-box">
          <label className="field">
            <span>{action === 'rejected' ? 'Why is it rejected?' : 'Why is it suspended?'}</span>
            <textarea
              className="textarea"
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              autoFocus
              maxLength={300}
            />
          </label>
          <div className="drawer-actions">
            <button className="btn btn-ghost btn-small" onClick={() => setAction(null)} disabled={busy}>
              Cancel
            </button>
            <button className="btn btn-danger btn-small" onClick={() => decide(action, true)} disabled={busy || !reason.trim()}>
              {action === 'rejected' ? 'Reject advertiser' : 'Suspend advertiser'}
            </button>
          </div>
        </div>
      ) : (
        <div className="review-actions">
          {status === 'pending' && (
            <>
              <button
                className="btn btn-primary btn-small"
                onClick={() => decide('approved')}
                disabled={busy || disabled || !complete}
                title={blockers[0]}
              >
                Approve
              </button>
              <button className="btn btn-ghost btn-ghost--danger btn-small" onClick={() => setAction('rejected')} disabled={busy}>
                Reject
              </button>
            </>
          )}
          {status === 'approved' && (
            <button className="btn btn-ghost btn-ghost--danger btn-small" onClick={() => setAction('suspended')} disabled={busy}>
              Suspend
            </button>
          )}
          {status === 'suspended' && (
            <button className="btn btn-primary btn-small" onClick={() => decide('approved')} disabled={busy || !complete}>
              Reactivate
            </button>
          )}
          {status === 'rejected' && (
            <button className="btn btn-ghost btn-small" onClick={() => decide('pending')} disabled={busy}>
              Move back to review
            </button>
          )}
          {(status === 'pending' || status === 'suspended') && !complete && (
            <span className="review-hint">{blockers[0]}</span>
          )}
          {disabled && status === 'pending' && complete && <span className="review-hint">Save your edits first.</span>}
        </div>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
