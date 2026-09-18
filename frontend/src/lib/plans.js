// Plan settings for the paid-access mock-up. Prices and limits are placeholders:
// change them here and the whole UI follows.

export const FREE_DAILY_LIMIT = 10;

// Start warning the user when this many free messages are left
export const LOW_MESSAGES_WARNING = 3;

export const PRO_PRICE = {
  month: 9.99, // charged monthly
  year: 95.88, // charged once a year (7.99 per month)
};

export const FREE_FEATURES = [
  `${FREE_DAILY_LIMIT} questions a day`,
  'GPT-5 model',
  'Visas, transport and housing topics',
  'Chat history on every device',
  'Includes sponsored suggestions',
];

export const PRO_FEATURES = [
  'Unlimited questions',
  'No ads',
  'Claude, our most capable model',
  'Visas, transport and housing topics',
  'Chat history on every device',
  'Priority support by email',
];

const eur = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR' });
export const formatPrice = (amount) => eur.format(amount);

export const monthlyEquivalent = (interval) => (interval === 'year' ? PRO_PRICE.year / 12 : PRO_PRICE.month);

export const yearlySavingPercent = Math.round((1 - PRO_PRICE.year / (PRO_PRICE.month * 12)) * 100);

const dateFormat = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
export const formatDate = (iso) => dateFormat.format(new Date(iso));
