// Advertiser manager mock-up: categories, targeting topics and review rules.

export const AD_TOPICS = [
  { id: 'VISA', label: 'Visas and permits' },
  { id: 'TRANSPORT', label: 'Transport' },
  { id: 'REAL_ESTATE', label: 'Housing and property' },
];

// `licence` = which body issues the licence the admin must check before approving
export const AD_CATEGORIES = [
  { id: 'law_firm', label: 'Law firm', licence: 'Cyprus Bar Association', topics: ['VISA'] },
  { id: 'real_estate', label: 'Real estate agency', licence: 'Estate Agents Registration Council', topics: ['REAL_ESTATE'] },
  { id: 'relocation', label: 'Relocation services', licence: null, topics: ['VISA', 'REAL_ESTATE'] },
  { id: 'insurance', label: 'Health insurance', licence: 'Insurance Companies Control Service', topics: ['VISA'] },
  { id: 'transport', label: 'Car rental and transport', licence: null, topics: ['TRANSPORT'] },
  { id: 'education', label: 'Language school or university', licence: null, topics: ['VISA'] },
  { id: 'other', label: 'Other', licence: null, topics: [] },
];

export const findCategory = (id) => AD_CATEGORIES.find((c) => c.id === id) ?? AD_CATEGORIES.at(-1);

// Advertiser websites are shown by host, both in the admin table and in the
// sponsored slot under an answer. Unparseable values are shown as stored.
export const hostOf = (url) => {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
};

export const AD_STATUSES = [
  { id: 'pending', label: 'Pending review' },
  { id: 'approved', label: 'Approved' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'suspended', label: 'Suspended' },
];

export const statusLabel = (id) => AD_STATUSES.find((s) => s.id === id)?.label ?? id;

// Everything on this list must be ticked before an advertiser can be approved
export function reviewChecks(category) {
  const checks = [
    { id: 'registration', label: 'Company registration matches the Registrar of Companies' },
    { id: 'website', label: 'Website reviewed: no "guaranteed visa" or other outcome promises' },
  ];
  const licence = findCategory(category).licence;
  if (licence) checks.splice(1, 0, { id: 'licence', label: `Licence confirmed with the ${licence}` });
  return checks;
}

export const checksComplete = (advertiser) =>
  reviewChecks(advertiser.category).every((c) => advertiser.checks?.[c.id]);

// Why an advertiser can't be approved yet (empty list = ready)
export function approvalBlockers(advertiser) {
  const blockers = [];
  if (findCategory(advertiser.category).licence && !advertiser.licence_number?.trim()) {
    blockers.push('Add the licence number first.');
  }
  if (!checksComplete(advertiser)) blockers.push('Tick every check to approve.');
  return blockers;
}

// Fields that, when changed on an approved advertiser, send it back to review
export const REVIEWED_FIELDS = ['company', 'reg_number', 'category', 'licence_number', 'website'];
