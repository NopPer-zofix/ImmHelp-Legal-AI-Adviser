import { BriefcaseBusiness, Car, GraduationCap, House } from 'lucide-react';
import Composer from './Composer';
import ComposerGate from './ComposerGate';

const SUGGESTIONS = [
  { icon: GraduationCap, label: 'Student visa', prompt: 'What documents do I need to apply for a student visa in Cyprus?' },
  {
    icon: BriefcaseBusiness,
    label: 'Changing employer',
    prompt: 'How do I renew my domestic worker permit after changing employer?',
  },
  { icon: Car, label: 'Driving licence', prompt: 'Can I drive in Cyprus with a driving licence from my home country?' },
  { icon: House, label: 'Renting a flat', prompt: 'What should I check before signing a rental contract in Cyprus?' },
];

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return 'Up late';
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function Welcome({ user, subscription, onSend, onUpgrade, busy, loading }) {
  const firstName = user.username.trim().split(/\s+/)[0];

  return (
    <section className="welcome">
      <h2 className="welcome-title">
        <span className="welcome-mark" aria-hidden="true">
          👽
        </span>
        {greeting()}, {firstName}
      </h2>

      <ComposerGate subscription={subscription} onUpgrade={onUpgrade}>
        <Composer
          onSend={onSend}
          busy={busy || loading}
          autoFocus
          placeholder="What would you like to know about moving to Cyprus?"
        />
      </ComposerGate>

      <div className="suggestions">
        {SUGGESTIONS.map(({ icon: Icon, label, prompt }) => (
          <button key={label} className="chip" onClick={() => onSend(prompt)} disabled={busy || loading || !subscription.canSend} title={prompt}>
            <Icon size={16} strokeWidth={1.75} />
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}
