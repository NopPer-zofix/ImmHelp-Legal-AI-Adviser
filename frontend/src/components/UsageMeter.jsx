export default function UsageMeter({ used, limit }) {
  const value = Math.min(used, limit);
  return (
    <div className="usage">
      <div className="usage-text">
        <span>Messages today</span>
        <span>
          {value} of {limit}
        </span>
      </div>
      <div
        className={`usage-bar${value >= limit ? ' is-full' : ''}`}
        role="progressbar"
        aria-label="Free messages used today"
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={value}
      >
        <span style={{ width: `${(value / limit) * 100}%` }} />
      </div>
    </div>
  );
}
