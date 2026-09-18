// Synthetic but stable numbers for the Analytics page in mock mode.

// Small seeded PRNG so charts don't jump around on every refresh
function rng(seed) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

const DAY = 86_400_000;

function localDates(days, tz) {
  const today = new Date(Date.now() - tz * 60_000);
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(today.getTime() - (days - 1 - i) * DAY);
    return d.toISOString().slice(0, 10);
  });
}

// Weekends are quieter
const weekday = (iso) => [0.55, 1, 1.05, 1, 0.95, 0.9, 0.6][new Date(`${iso}T12:00:00Z`).getUTCDay()];
const daySeed = (iso) => Number(iso.replaceAll('-', ''));

export function mockUsersSeries({ days, tz }) {
  const dates = localDates(days, tz);
  const all = localDates(365, tz);
  let total = 12;
  const byDate = {};
  for (const d of all) {
    const r = rng(daySeed(d));
    const growth = 0.4 + (all.indexOf(d) / all.length) * 2.2;
    const fresh = Math.round(growth * weekday(d) * (0.5 + r()));
    total += fresh;
    byDate[d] = { date: d, new_users: fresh, total_users: total, active_users: Math.round(total * (0.18 + r() * 0.08) * weekday(d)) };
  }
  return { days: dates.map((d) => byDate[d]) };
}

const TOPIC_BASE = { VISA: 22, REAL_ESTATE: 11, TRANSPORT: 7, GENERAL: 5, OUT_OF_SCOPE: 2 };

export function mockTopicsSeries({ days, tz }) {
  const dates = localDates(days, tz);
  const labels = Object.keys(TOPIC_BASE);
  const totals = Object.fromEntries(labels.map((l) => [l, 0]));
  const series = dates.map((d) => {
    const r = rng(daySeed(d) * 7);
    const row = { date: d };
    for (const l of labels) {
      row[l] = Math.round(TOPIC_BASE[l] * weekday(d) * (0.6 + r() * 0.8));
      totals[l] += row[l];
    }
    return row;
  });
  const questions = Object.values(totals).reduce((a, b) => a + b, 0);
  return { labels, totals, questions, untagged: 0, days: series };
}

export function mockLoad({ hours }) {
  const bucketMin = hours <= 12 ? 5 : 15;
  const step = bucketMin * 60_000;
  const now = Date.now();
  const first = Math.floor((now - hours * 3_600_000) / step) * step;
  const series = [];
  for (let t = first; t <= now; t += step) {
    const hour = new Date(t).getHours() + new Date(t).getMinutes() / 60;
    // Busy late morning and evening, quiet at night
    const curve = Math.max(0.05, Math.sin(((hour - 6) / 24) * Math.PI * 2) * 0.5 + 0.55 + Math.sin(((hour - 15) / 12) * Math.PI * 2) * 0.15);
    const r = rng(Math.floor(t / step));
    series.push({ time: new Date(t).toISOString(), active: Math.round(curve * 14 + r() * 4) });
  }
  const r = rng(Math.floor(now / 30_000));
  return {
    active_now: series.at(-1).active,
    window_minutes: 2,
    answering_now: Math.floor(r() * 4),
    questions_last_hour: 20 + Math.floor(r() * 25),
    bucket_minutes: bucketMin,
    series,
  };
}
