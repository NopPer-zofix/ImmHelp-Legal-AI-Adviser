import { useCallback, useRef, useState } from 'react';
import { ChevronsUpDown, CreditCard, LogOut, ShieldCheck, Sparkles } from 'lucide-react';
import { isAdmin } from '../lib/roles';
import { useDismiss } from '../hooks/useDismiss';
import { formatDate } from '../lib/plans';
import UsageMeter from './UsageMeter';

function initials(name = '') {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?';
}

function planLine(sub) {
  if (sub.isPro) return 'Pro plan';
  // An admin has no daily limit, so there is no count to show and nothing to upgrade
  if (sub.isAdmin) return 'Admin, unlimited';
  if (!sub.canSend) return 'Free plan, limit reached';
  return `Free plan, ${sub.remaining} left today`;
}

export default function UserMenu({ user, subscription: sub, onUpgrade, onManage, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(open, close, ref);

  const run = (fn) => () => {
    setOpen(false);
    fn();
  };

  return (
    <div className="user" ref={ref}>
      {open && (
        <div className="menu menu--up" role="menu">
          <p className="menu-caption">{user.email}</p>

          <div className="plan-panel">
            <div className="plan-panel-head">
              <span className="plan-name">{sub.isPro ? 'ImmHelp Pro' : sub.isAdmin ? 'Admin access' : 'Free plan'}</span>
              {sub.isPro && <span className="plan-badge">Pro</span>}
            </div>

            {sub.isPro ? (
              <p className="plan-meta">
                {sub.plan.status === 'cancelled'
                  ? `Ends on ${formatDate(sub.plan.endsAt)}`
                  : `Unlimited questions. Renews on ${formatDate(sub.plan.renewsAt)}.`}
              </p>
            ) : sub.isAdmin ? (
              <p className="plan-meta">Unlimited questions and every model, as an admin.</p>
            ) : (
              <>
                <UsageMeter used={sub.used} limit={sub.limit} />
                <p className="plan-meta">Resets {sub.resetsIn}.</p>
                <button className="btn btn-primary btn-small btn-block" onClick={run(onUpgrade)}>
                  <Sparkles size={14} /> Upgrade to Pro
                </button>
              </>
            )}
          </div>

          {isAdmin(user) && (
            <a role="menuitem" className="menu-link" href="#/admin" onClick={() => setOpen(false)}>
              <ShieldCheck size={15} /> Admin dashboard
            </a>
          )}
          {sub.isPro && (
            <button role="menuitem" onClick={run(onManage)}>
              <CreditCard size={15} /> Manage subscription
            </button>
          )}
          <button role="menuitem" onClick={onLogout}>
            <LogOut size={15} /> Log out
          </button>
        </div>
      )}

      <button className="user-btn" onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open}>
        <span className="avatar" aria-hidden="true">
          {initials(user.username)}
        </span>
        <span className="user-text">
          <span className="user-name">
            {user.username}
            {isAdmin(user) && <span className="admin-tag">Admin</span>}
          </span>
          <span className={`user-plan${sub.isPro ? ' is-pro' : ''}`}>{planLine(sub)}</span>
        </span>
        <ChevronsUpDown size={15} className="user-chevron" />
      </button>
    </div>
  );
}
