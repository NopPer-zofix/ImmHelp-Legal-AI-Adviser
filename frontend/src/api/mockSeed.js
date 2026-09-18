// Fake users and message history so the admin dashboard has something to show in mock mode.

const DAY = 86_400_000;
const ago = (days, hours = 0) => new Date(Date.now() - days * DAY - hours * 3_600_000).toISOString();

export const SEED_USERS = [
  { id: 1, email: 'demo@immhelp.cy', password: 'demo1234', username: 'Demo User', role: 'user', created_at: ago(40) },
  { id: 2, email: 'admin@immhelp.cy', password: 'admin1234', username: 'Kostia Admin', role: 'admin', created_at: ago(60) },
  { id: 3, email: 'maria.k@example.com', password: 'x', username: 'Maria Kovalenko', role: 'user', created_at: ago(33) },
  { id: 4, email: 'r.fernando@example.com', password: 'x', username: 'Ravi Fernando', role: 'user', created_at: ago(28) },
  { id: 5, email: 'anna.s@example.com', password: 'x', username: 'Anna Sidorova', role: 'user', created_at: ago(21) },
  { id: 6, email: 'j.smith@example.com', password: 'x', username: 'James Smith', role: 'user', created_at: ago(19) },
  {
    id: 7,
    email: 'promo-deals@example.com',
    password: 'x',
    username: 'Best Deals',
    role: 'user',
    created_at: ago(9),
    is_banned: true,
    banned_reason: 'Posting advertising links in questions',
    banned_at: ago(3),
  },
  { id: 8, email: 'l.nguyen@example.com', password: 'x', username: 'Linh Nguyen', role: 'user', created_at: ago(12) },
  { id: 9, email: 'o.petrenko@example.com', password: 'x', username: 'Oleh Petrenko', role: 'user', created_at: ago(7) },
  { id: 10, email: 'k.ahmed@example.com', password: 'x', username: 'Karim Ahmed', role: 'user', created_at: ago(4) },
  { id: 11, email: 'e.georgiou@example.com', password: 'x', username: 'Elena Georgiou', role: 'user', created_at: ago(2) },
];

// [question, how many times, spread over how many days]
const QUESTION_POOL = [
  ['What documents do I need for a student visa in Cyprus?', 23, 20],
  ['How do I renew my residence permit?', 17, 25],
  ['Can I drive in Cyprus with a foreign driving licence?', 14, 25],
  ['How long does a pink slip take to process?', 12, 15],
  ['What should I check before signing a rental contract?', 11, 30],
  ['How do I change employer on a domestic worker permit?', 9, 12],
  ['Can my family join me on a work permit?', 8, 30],
  ['How do I register my address with the migration office?', 7, 6],
  ['Is medical insurance mandatory for a temporary residence permit?', 6, 5],
  ['How do I get a bus card in Limassol?', 5, 4],
  ['What is the minimum income for a visitor permit?', 4, 30],
  ['Where do I submit biometrics?', 3, 3],
];

export function seedMessages(startId) {
  const activeUsers = SEED_USERS.filter((u) => u.id > 2 && !u.is_banned).map((u) => u.id);
  const messages = [];
  let id = startId;
  let n = 0;
  for (const [text, count, spread] of QUESTION_POOL) {
    for (let i = 0; i < count; i += 1) {
      n += 1;
      // Vary case and punctuation so grouping has to normalise, like real input
      const variant = i % 3 === 0 ? text.toLowerCase() : i % 3 === 1 ? text.replace(/\?$/, '') : text;
      messages.push({
        id: ++id,
        chat_id: null,
        user_id: activeUsers[n % activeUsers.length],
        role: 'user',
        content: variant,
        created_at: ago((i * spread) / count, n % 24),
      });
    }
  }
  return messages;
}

export const SEED_ADVERTISERS = [
  {
    id: 1,
    company: 'Andreou & Partners LLC',
    reg_number: 'HE 284511',
    website: 'https://andreou-law.example',
    category: 'law_firm',
    licence_number: 'CBA 11845',
    contact_name: 'Christina Andreou',
    contact_email: 'c.andreou@andreou-law.example',
    contact_phone: '+357 25 000 111',
    topics: ['VISA'],
    notes: 'Immigration and residence permits. Wants to target student visa questions.',
    status: 'approved',
    checks: { registration: true, licence: true, website: true },
    created_at: ago(25),
    reviewed_at: ago(22),
  },
  {
    id: 2,
    company: 'Seaside Homes Ltd',
    reg_number: 'HE 402117',
    website: 'https://seasidehomes.example',
    category: 'real_estate',
    licence_number: '',
    contact_name: 'Nikos Pavlou',
    contact_email: 'nikos@seasidehomes.example',
    contact_phone: '',
    topics: ['REAL_ESTATE'],
    notes: 'Long-term rentals in Limassol. Licence number not sent yet.',
    status: 'pending',
    checks: { registration: true },
    created_at: ago(2),
  },
  {
    id: 3,
    company: 'MoveEasy Relocation',
    reg_number: 'HE 377020',
    website: 'https://moveeasy.example',
    category: 'relocation',
    licence_number: '',
    contact_name: 'Olga Ivanova',
    contact_email: 'olga@moveeasy.example',
    contact_phone: '+357 99 000 222',
    topics: ['VISA', 'REAL_ESTATE'],
    notes: '',
    status: 'pending',
    checks: {},
    created_at: ago(1),
  },
  {
    id: 4,
    company: 'FastVisa Consult',
    reg_number: 'HE 999001',
    website: 'https://fastvisa.example',
    category: 'other',
    licence_number: '',
    contact_name: 'Unknown',
    contact_email: 'info@fastvisa.example',
    contact_phone: '',
    topics: ['VISA'],
    notes: '',
    status: 'rejected',
    status_reason: 'Website promises a "100% guaranteed" permit. Not a licensed lawyer.',
    checks: { registration: true },
    created_at: ago(14),
    reviewed_at: ago(13),
  },
  {
    id: 5,
    company: 'CyRide Car Rentals',
    reg_number: 'HE 150333',
    website: 'https://cyride.example',
    category: 'transport',
    licence_number: '',
    contact_name: 'Marios Charalambous',
    contact_email: 'marios@cyride.example',
    contact_phone: '+357 24 000 333',
    topics: ['TRANSPORT'],
    notes: '',
    status: 'suspended',
    status_reason: 'Unpaid invoice for August.',
    checks: { registration: true, website: true },
    created_at: ago(45),
    reviewed_at: ago(5),
  },
];
