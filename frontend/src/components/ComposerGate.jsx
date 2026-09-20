import { Lock } from 'lucide-react';
import { LOW_MESSAGES_WARNING } from '../lib/plans';

// Wraps the composer: warns when free messages run low and replaces it once they run out.
export default function ComposerGate({ subscription, onUpgrade, children }) {
  const { unlimited, canSend, remaining, limit, resetsIn } = subscription;

  if (!canSend) {
    return (
      <div className="limit-card" role="status">
        <span className="limit-icon" aria-hidden="true">
          <Lock size={18} />
        </span>
        <div className="limit-text">
          <strong>You've used today's {limit} free messages</strong>
          <p>New free messages arrive {resetsIn}. Upgrade to Pro to keep asking now.</p>
        </div>
        <button className="btn btn-primary" onClick={onUpgrade}>
          Upgrade to Pro
        </button>
      </div>
    );
  }

  return (
    <>
      {!unlimited && remaining <= LOW_MESSAGES_WARNING && (
        <p className="usage-note">
          {remaining === 1 ? '1 free message' : `${remaining} free messages`} left today.{' '}
          <button className="link-btn" onClick={onUpgrade}>
            Get unlimited
          </button>
        </p>
      )}
      {children}
    </>
  );
}
