import { useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { RefreshCw } from 'lucide-react';
import { useChartTheme } from '../../hooks/useChartTheme';
import { useLiveLoad, useTrends } from '../../hooks/useAnalytics';

const RANGES = [
  { value: 7, label: '7 days' },
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
];

const LOAD_RANGES = [
  { value: 6, label: '6 hours' },
  { value: 24, label: '24 hours' },
];

const TOPIC_NAMES = {
  VISA: 'Visas and permits',
  REAL_ESTATE: 'Housing and property',
  TRANSPORT: 'Transport',
  GENERAL: 'General',
  OUT_OF_SCOPE: 'Off-topic',
};
const topicName = (t) => TOPIC_NAMES[t] ?? t;

const dayFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const timeFmt = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit' });
const formatDay = (iso) => dayFmt.format(new Date(`${iso}T12:00:00`));
const formatTime = (iso) => timeFmt.format(new Date(iso));

function Segmented({ options, value, onChange, label }) {
  return (
    <div className="segmented segmented--inline segmented--small" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

// Shared look for every chart: quiet grid, small axis labels, a tooltip in the app's style
function useChartProps() {
  const c = useChartTheme();
  return {
    c,
    grid: <CartesianGrid stroke={c.line} strokeDasharray="0" vertical={false} />,
    axis: { stroke: c['ink-3'], fontSize: 12, tickLine: false, axisLine: false },
    tooltip: {
      contentStyle: {
        background: c.surface,
        border: `1px solid ${c.line}`,
        borderRadius: 10,
        fontSize: 13,
        color: c.ink,
        boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
      },
      labelStyle: { color: c['ink-2'], marginBottom: 4 },
      cursor: { fill: c.line, fillOpacity: 0.35, stroke: c.line },
    },
  };
}

function ChartBox({ height = 260, children, empty }) {
  if (empty) return <div className="chart-empty" style={{ height }}>{empty}</div>;
  return (
    <div className="chart" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

function Legend({ items }) {
  return (
    <ul className="chart-legend">
      {items.map((i) => (
        <li key={i.label}>
          <span className={`swatch${i.line ? ' swatch--line' : ''}`} style={{ background: i.color }} aria-hidden="true" />
          {i.label}
        </li>
      ))}
    </ul>
  );
}

export default function Analytics() {
  const [days, setDays] = useState(30);
  const [hours, setHours] = useState(6);
  const trends = useTrends(days);
  const live = useLiveLoad(hours);
  const { c, grid, axis, tooltip } = useChartProps();

  const topicColors = {
    VISA: c['chart-1'],
    REAL_ESTATE: c['chart-2'],
    TRANSPORT: c['chart-3'],
    GENERAL: c['chart-4'],
    OUT_OF_SCOPE: c['chart-5'],
  };

  const users = trends.users;
  const last = users?.at(-1);
  const newInRange = users?.reduce((sum, d) => sum + d.new_users, 0);

  const topics = trends.topics;
  const tagged = topics ? Object.values(topics.totals).reduce((a, b) => a + b, 0) : 0;

  const load = live.load;

  return (
    <div className="dash">
      <div className="dash-head">
        <div>
          <h1>Analytics</h1>
          <p className="dash-sub">Users, topics and how busy the service is right now.</p>
        </div>
      </div>

      {(trends.error || live.error) && (
        <p className="form-error" role="alert">
          {trends.error || live.error}
        </p>
      )}

      {/* ---------------- Live load ---------------- */}
      <section className="panel" aria-labelledby="live-h">
        <div className="panel-head">
          <div>
            <h2 id="live-h">
              Right now <span className="live-dot" aria-hidden="true" />
            </h2>
            <p className="panel-note">
              {live.updatedAt
                ? `Updates every 30 seconds. Last update ${timeFmt.format(live.updatedAt)}.`
                : 'Loading…'}
            </p>
          </div>
          <div className="panel-tools">
            <Segmented options={LOAD_RANGES} value={hours} onChange={setHours} label="Load period" />
            <button className="icon-btn" onClick={live.refresh} aria-label="Refresh now">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        <dl className="figures figures--3">
          <div>
            <dt>Active sessions</dt>
            <dd>{load?.active_now ?? '–'}</dd>
            <p className="figure-note">Users with the app open in the last {load?.window_minutes ?? 2} minutes</p>
          </div>
          <div>
            <dt>Answers being written</dt>
            <dd>{load?.answering_now ?? '–'}</dd>
            <p className="figure-note">Questions waiting for the model at this moment</p>
          </div>
          <div>
            <dt>Questions in the last hour</dt>
            <dd>{load?.questions_last_hour ?? '–'}</dd>
            <p className="figure-note">Across all users</p>
          </div>
        </dl>

        <h3 className="chart-title">Active sessions, every {load?.bucket_minutes ?? 5} minutes</h3>
        <ChartBox height={200} empty={!load ? 'Loading…' : null}>
          <AreaChart data={load?.series} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
            <defs>
              <linearGradient id="loadFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={c.accent} stopOpacity={0.28} />
                <stop offset="100%" stopColor={c.accent} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            {grid}
            <XAxis dataKey="time" tickFormatter={formatTime} minTickGap={40} {...axis} />
            <YAxis allowDecimals={false} {...axis} />
            <Tooltip {...tooltip} labelFormatter={formatTime} formatter={(v) => [v, 'Active sessions']} />
            <Area type="monotone" dataKey="active" stroke={c.accent} strokeWidth={2} fill="url(#loadFill)" isAnimationActive={false} />
          </AreaChart>
        </ChartBox>
      </section>

      <div className="range-bar">
        <span>Period for the charts below</span>
        <Segmented options={RANGES} value={days} onChange={setDays} label="Period" />
      </div>

      {/* ---------------- Users ---------------- */}
      <section className="panel" aria-labelledby="users-chart-h">
        <div className="panel-head">
          <div>
            <h2 id="users-chart-h">Users</h2>
            <p className="panel-note">Total accounts and how many were active each day.</p>
          </div>
        </div>

        <dl className="figures figures--3">
          <div>
            <dt>Total users</dt>
            <dd>{last?.total_users ?? '–'}</dd>
          </div>
          <div>
            <dt>New in the last {days} days</dt>
            <dd>{newInRange ?? '–'}</dd>
          </div>
          <div>
            <dt>Active today</dt>
            <dd>{last?.active_users ?? '–'}</dd>
          </div>
        </dl>

        <Legend
          items={[
            { label: 'Total users', color: c.accent },
            { label: 'Active that day', color: c['chart-2'], line: true },
          ]}
        />
        <ChartBox empty={!users ? 'Loading…' : null}>
          <ComposedChart data={users} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
            <defs>
              <linearGradient id="usersFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={c.accent} stopOpacity={0.22} />
                <stop offset="100%" stopColor={c.accent} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            {grid}
            <XAxis dataKey="date" tickFormatter={formatDay} minTickGap={28} {...axis} />
            <YAxis allowDecimals={false} {...axis} />
            <Tooltip {...tooltip} labelFormatter={formatDay} />
            <Area type="monotone" dataKey="total_users" name="Total users" stroke={c.accent} strokeWidth={2} fill="url(#usersFill)" isAnimationActive={false} />
            <Line type="monotone" dataKey="active_users" name="Active that day" stroke={c['chart-2']} strokeWidth={2} dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ChartBox>

        <h3 className="chart-title">New sign-ups per day</h3>
        <ChartBox height={140} empty={!users ? 'Loading…' : null}>
          <BarChart data={users} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            {grid}
            <XAxis dataKey="date" tickFormatter={formatDay} minTickGap={28} {...axis} />
            <YAxis allowDecimals={false} {...axis} />
            <Tooltip {...tooltip} labelFormatter={formatDay} formatter={(v) => [v, 'New users']} />
            <Bar dataKey="new_users" fill={c.accent} radius={[3, 3, 0, 0]} maxBarSize={18} isAnimationActive={false} />
          </BarChart>
        </ChartBox>
      </section>

      {/* ---------------- Topics ---------------- */}
      <section className="panel" aria-labelledby="topics-h">
        <div className="panel-head">
          <div>
            <h2 id="topics-h">Topics</h2>
            <p className="panel-note">
              What questions are about, as decided by the router. A question can have two topics.
            </p>
          </div>
        </div>

        {topics && tagged === 0 ? (
          <p className="panel-empty">
            No topics recorded in this period yet. Topics are saved for questions asked after this update.
          </p>
        ) : (
          <div className="topics-grid">
            <div>
              <ul className="share-list">
                {(topics?.labels ?? []).map((t) => {
                  const n = topics.totals[t];
                  const pct = tagged ? Math.round((n / tagged) * 100) : 0;
                  return (
                    <li key={t}>
                      <div className="share-row">
                        <span className="share-name">
                          <span className="swatch" style={{ background: topicColors[t] ?? c['ink-3'] }} aria-hidden="true" />
                          {topicName(t)}
                        </span>
                        <span className="share-num">
                          {n} <span>{pct}%</span>
                        </span>
                      </div>
                      <span className="share-bar" aria-hidden="true">
                        <span style={{ width: `${pct}%`, background: topicColors[t] ?? c['ink-3'] }} />
                      </span>
                    </li>
                  );
                })}
              </ul>
              {topics?.untagged > 0 && (
                <p className="panel-note share-foot">
                  {topics.untagged} older or very short questions have no topic.
                </p>
              )}
            </div>

            <ChartBox height={280} empty={!topics ? 'Loading…' : null}>
              <BarChart data={topics?.days} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                {grid}
                <XAxis dataKey="date" tickFormatter={formatDay} minTickGap={28} {...axis} />
                <YAxis allowDecimals={false} {...axis} />
                <Tooltip {...tooltip} labelFormatter={formatDay} formatter={(v, name) => [v, topicName(name)]} />
                {(topics?.labels ?? []).map((t, i, all) => (
                  <Bar
                    key={t}
                    dataKey={t}
                    stackId="topics"
                    fill={topicColors[t] ?? c['ink-3']}
                    maxBarSize={22}
                    radius={i === all.length - 1 ? [3, 3, 0, 0] : 0}
                    isAnimationActive={false}
                  />
                ))}
              </BarChart>
            </ChartBox>
          </div>
        )}
      </section>
    </div>
  );
}
