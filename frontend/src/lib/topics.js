// Labels the backend router returns in /ask → { topics: [...] }
const TOPIC_NAMES = {
  VISA: 'visas and permits',
  TRANSPORT: 'transport',
  REAL_ESTATE: 'housing and property',
};

export function describeTopics(topics = []) {
  const names = topics.map((t) => TOPIC_NAMES[t]).filter(Boolean);
  if (!names.length) return '';
  return `Based on ${names.join(' and ')} documents`;
}
