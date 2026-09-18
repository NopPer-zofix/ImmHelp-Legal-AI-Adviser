const PERIODS = [
  { days: 7, label: '7 days' },
  { days: 30, label: '30 days' },
  { days: 0, label: 'All time' },
];

export default function TopQuestions({ items, days, onDaysChange }) {
  const max = items?.[0]?.count ?? 1;

  return (
    <section className="panel" aria-labelledby="top-q">
      <div className="panel-head">
        <div>
          <h2 id="top-q">Most asked questions</h2>
          <p className="panel-note">Questions with the same wording, ignoring case and punctuation.</p>
        </div>
        <div className="segmented segmented--inline segmented--small" role="radiogroup" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p.days} role="radio" aria-checked={days === p.days} onClick={() => onDaysChange(p.days)}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {!items && <p className="panel-empty">Loading questions…</p>}
      {items?.length === 0 && <p className="panel-empty">No questions in this period.</p>}

      {items?.length > 0 && (
        <ol className="top-list">
          {items.map((q, i) => (
            <li key={q.question}>
              <span className="top-rank">{i + 1}</span>
              <div className="top-body">
                <span className="top-text">{q.question}</span>
                <span className="top-bar" aria-hidden="true">
                  <span style={{ width: `${(q.count / max) * 100}%` }} />
                </span>
              </div>
              <span className="top-count">
                {q.count} <span className="visually-hidden">times</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
