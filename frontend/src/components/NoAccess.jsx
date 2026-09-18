import { ShieldOff } from 'lucide-react';

export default function NoAccess({ onBack }) {
  return (
    <div className="auth">
      <div className="auth-inner no-access">
        <span className="consent-icon" aria-hidden="true">
          <ShieldOff size={22} />
        </span>
        <h1 className="auth-title">This page is for administrators</h1>
        <p className="auth-lede">Your account doesn't have admin access. Ask an administrator if you need it.</p>
        <button className="btn btn-primary" onClick={onBack}>
          Back to chat
        </button>
      </div>
    </div>
  );
}
