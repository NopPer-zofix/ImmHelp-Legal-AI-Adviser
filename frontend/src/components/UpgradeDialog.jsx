import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Check, CreditCard, Info, X } from 'lucide-react';
import {
  FREE_DAILY_LIMIT,
  FREE_FEATURES,
  PRO_FEATURES,
  PRO_PRICE,
  formatDate,
  formatPrice,
  monthlyEquivalent,
  yearlySavingPercent,
} from '../lib/plans';

// Mock-up of the paid plan flow: plans → checkout → success, plus "manage" for Pro users.
// Nothing here talks to a payment provider; card details never leave this component.

const EMPTY_CARD = { number: '', expiry: '', cvc: '', name: '' };

function formatCardNumber(value) {
  return value.replace(/\D/g, '').slice(0, 16).replace(/(\d{4})(?=\d)/g, '$1 ');
}

function formatExpiry(value) {
  const digits = value.replace(/\D/g, '').slice(0, 4);
  return digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
}

function validateCard(card) {
  const errors = {};
  if (card.number.replace(/\s/g, '').length !== 16) errors.number = 'Enter the 16-digit card number.';

  const [mm, yy] = card.expiry.split('/').map(Number);
  const expiryEnd = new Date(2000 + yy, mm, 1); // first day of the month after expiry
  if (!mm || !yy || mm > 12 || expiryEnd <= new Date()) errors.expiry = 'Enter a future date as MM/YY.';

  if (!/^\d{3,4}$/.test(card.cvc)) errors.cvc = 'Enter the 3 or 4 digits on the back.';
  if (!card.name.trim()) errors.name = 'Enter the name shown on the card.';
  return errors;
}

export default function UpgradeDialog({ open, reason, user, subscription: sub, onClose }) {
  const ref = useRef(null);
  const [view, setView] = useState('plans'); // plans | checkout | success | manage
  const [interval, setBillingInterval] = useState('year');
  const [card, setCard] = useState(EMPTY_CARD);
  const [errors, setErrors] = useState({});
  const [processing, setProcessing] = useState(false);

  // Start fresh every time the dialog opens
  useEffect(() => {
    const dialog = ref.current;
    if (open) {
      setView(reason === 'manage' ? 'manage' : 'plans');
      setCard(EMPTY_CARD);
      setErrors({});
      setProcessing(false);
      if (!dialog.open) dialog.showModal();
    } else if (dialog.open) {
      dialog.close();
    }
  }, [open, reason]);

  const requestClose = () => {
    if (!processing) onClose();
  };

  const price = PRO_PRICE[interval];

  async function pay(e) {
    e.preventDefault();
    const found = validateCard(card);
    setErrors(found);
    if (Object.keys(found).length) return;

    setProcessing(true);
    await new Promise((r) => setTimeout(r, 1400)); // pretend to talk to the payment provider
    sub.subscribe({ interval, cardLast4: card.number.replace(/\s/g, '').slice(-4) });
    setProcessing(false);
    setView('success');
  }

  const field = (name, format = (v) => v) => ({
    value: card[name],
    onChange: (e) => {
      setCard((c) => ({ ...c, [name]: format(e.target.value) }));
      if (errors[name]) setErrors((err) => ({ ...err, [name]: undefined }));
    },
    'aria-invalid': Boolean(errors[name]),
    disabled: processing,
  });

  return (
    <dialog
      ref={ref}
      className={`dialog dialog--wide${view === 'plans' ? ' is-plans' : ''}`}
      aria-labelledby="upgrade-title"
      onCancel={(e) => {
        e.preventDefault();
        requestClose();
      }}
      onClick={(e) => e.target === ref.current && requestClose()}
    >
      <div className="dialog-body">
        <div className="dialog-top">
          {view === 'checkout' ? (
            <button className="icon-btn" onClick={() => setView('plans')} aria-label="Back to plans" disabled={processing}>
              <ArrowLeft size={18} />
            </button>
          ) : (
            <span />
          )}
          <button className="icon-btn" onClick={requestClose} aria-label="Close" disabled={processing}>
            <X size={18} />
          </button>
        </div>

        {view === 'plans' && (
          <>
            <h2 id="upgrade-title" className="upgrade-title">
              {reason === 'limit' ? "You've reached today's free limit" : 'Upgrade to ImmHelp Pro'}
            </h2>
            <p className="upgrade-lede">
              {reason === 'limit'
                ? `The free plan includes ${FREE_DAILY_LIMIT} questions a day. Pro removes the limit so you can finish your paperwork in one sitting.`
                : 'Ask as many questions as your move needs, about visas, permits, transport and housing.'}
            </p>

            <div className="segmented segmented--inline" role="radiogroup" aria-label="Billing period">
              <button role="radio" aria-checked={interval === 'month'} onClick={() => setBillingInterval('month')}>
                Monthly
              </button>
              <button role="radio" aria-checked={interval === 'year'} onClick={() => setBillingInterval('year')}>
                Yearly <span className="save-tag">−{yearlySavingPercent}%</span>
              </button>
            </div>

            <div className="plans">
              <section className="plan-card" aria-labelledby="plan-free">
                <h3 id="plan-free">Free</h3>
                <p className="plan-price">
                  <span className="plan-amount">{formatPrice(0)}</span>
                </p>
                <p className="plan-billing">Free forever</p>
                <button className="btn btn-ghost btn-block" disabled>
                  Current plan
                </button>
                <FeatureList items={FREE_FEATURES} />
              </section>

              <section className="plan-card plan-card--pro" aria-labelledby="plan-pro">
                <h3 id="plan-pro">
                  Pro <span className="plan-badge">Recommended</span>
                </h3>
                <p className="plan-price">
                  <span className="plan-amount">{formatPrice(monthlyEquivalent(interval))}</span>
                  <span className="plan-per">per month</span>
                </p>
                <p className="plan-billing">
                  {interval === 'year' ? `${formatPrice(PRO_PRICE.year)} billed yearly` : 'Billed monthly, cancel anytime'}
                </p>
                <button className="btn btn-primary btn-block" onClick={() => setView('checkout')}>
                  Continue with Pro
                </button>
                <FeatureList items={PRO_FEATURES} />
              </section>
            </div>
          </>
        )}

        {view === 'checkout' && (
          <form className="checkout" onSubmit={pay} noValidate>
            <h2 id="upgrade-title" className="upgrade-title">
              Checkout
            </h2>

            <div className="order">
              <div>
                <strong>ImmHelp Pro</strong>
                <span>{interval === 'year' ? 'Yearly plan' : 'Monthly plan'}</span>
              </div>
              <div className="order-total">
                <strong>{formatPrice(price)}</strong>
                <span>due today</span>
              </div>
            </div>

            <label className="field">
              <span>Email</span>
              <input value={user.email} readOnly />
            </label>

            <label className="field">
              <span>Card number</span>
              <div className="input-icon">
                <CreditCard size={16} aria-hidden="true" />
                <input
                  {...field('number', formatCardNumber)}
                  inputMode="numeric"
                  autoComplete="cc-number"
                  placeholder="1234 1234 1234 1234"
                />
              </div>
              {errors.number && <em className="field-error">{errors.number}</em>}
            </label>

            <div className="field-row">
              <label className="field">
                <span>Expiry</span>
                <input {...field('expiry', formatExpiry)} inputMode="numeric" autoComplete="cc-exp" placeholder="MM/YY" />
                {errors.expiry && <em className="field-error">{errors.expiry}</em>}
              </label>
              <label className="field">
                <span>CVC</span>
                <input
                  {...field('cvc', (v) => v.replace(/\D/g, '').slice(0, 4))}
                  inputMode="numeric"
                  autoComplete="cc-csc"
                  placeholder="123"
                />
                {errors.cvc && <em className="field-error">{errors.cvc}</em>}
              </label>
            </div>

            <label className="field">
              <span>Name on card</span>
              <input {...field('name')} autoComplete="cc-name" placeholder={user.username} />
              {errors.name && <em className="field-error">{errors.name}</em>}
            </label>

            <p className="demo-note">
              <Info size={15} aria-hidden="true" />
              Demo checkout. No payment is taken and card details are not sent anywhere. Try 4242 4242 4242 4242.
            </p>

            <button className="btn btn-primary btn-block btn-large" disabled={processing}>
              {processing ? (
                <>
                  <span className="spinner" aria-hidden="true" /> Processing payment…
                </>
              ) : (
                `Pay ${formatPrice(price)}`
              )}
            </button>
            <p className="fine-print">
              {interval === 'year'
                ? 'Renews every year at the same price until you cancel.'
                : 'Renews every month at the same price until you cancel.'}
            </p>
          </form>
        )}

        {view === 'success' && sub.plan && (
          <div className="success">
            <span className="success-icon" aria-hidden="true">
              <Check size={28} strokeWidth={2.5} />
            </span>
            <h2 id="upgrade-title" className="upgrade-title">
              You're on Pro
            </h2>
            <p className="upgrade-lede">
              Unlimited questions are on. Your plan renews on {formatDate(sub.plan.renewsAt)}.
            </p>
            <button className="btn btn-primary btn-large" onClick={onClose} autoFocus>
              Start asking
            </button>
          </div>
        )}

        {view === 'manage' && sub.plan && (
          <div className="manage">
            <h2 id="upgrade-title" className="upgrade-title">
              Your subscription
            </h2>
            <dl className="manage-list">
              <div>
                <dt>Plan</dt>
                <dd>ImmHelp Pro, {sub.plan.interval === 'year' ? 'yearly' : 'monthly'}</dd>
              </div>
              <div>
                <dt>Price</dt>
                <dd>
                  {formatPrice(PRO_PRICE[sub.plan.interval])} per {sub.plan.interval}
                </dd>
              </div>
              <div>
                <dt>{sub.plan.status === 'cancelled' ? 'Access until' : 'Next payment'}</dt>
                <dd>{formatDate(sub.plan.status === 'cancelled' ? sub.plan.endsAt : sub.plan.renewsAt)}</dd>
              </div>
              <div>
                <dt>Payment method</dt>
                <dd>Card ending in {sub.plan.cardLast4}</dd>
              </div>
            </dl>

            {sub.plan.status === 'cancelled' ? (
              <>
                <p className="manage-note">
                  Your subscription is cancelled. You keep Pro until {formatDate(sub.plan.endsAt)}, then move to the free
                  plan.
                </p>
                <button className="btn btn-primary" onClick={sub.resume}>
                  Resume subscription
                </button>
              </>
            ) : (
              <>
                <p className="manage-note">
                  If you cancel, you keep Pro until {formatDate(sub.plan.renewsAt)} and won't be charged again.
                </p>
                <button className="btn btn-ghost btn-ghost--danger" onClick={sub.cancel}>
                  Cancel subscription
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </dialog>
  );
}

function FeatureList({ items }) {
  return (
    <ul className="features">
      {items.map((item) => (
        <li key={item}>
          <Check size={16} aria-hidden="true" />
          {item}
        </li>
      ))}
    </ul>
  );
}
