import { RefreshCw } from 'lucide-react';
import { useAdminData } from '../../hooks/useAdminData';
import TopQuestions from './TopQuestions';
import UsersTable from './UsersTable';

export default function Dashboard({ currentUser }) {
  const data = useAdminData();
  const { stats } = data;

  const figures = [
    { label: 'Users', value: stats?.users },
    { label: 'Active', value: stats?.active_users },
    { label: 'Banned', value: stats?.banned_users },
    { label: 'Questions, last 7 days', value: stats?.messages_7d },
    { label: 'Questions, all time', value: stats?.messages_total },
  ];

  return (
    <div className="dash">
      <div className="dash-head">
        <div>
          <h1>Dashboard</h1>
          <p className="dash-sub">
            {data.updatedAt ? `Updated ${data.updatedAt.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}` : 'Loading…'}
          </p>
        </div>
        <button className="btn btn-ghost btn-small" onClick={data.refresh}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {data.error && (
        <p className="form-error" role="alert">
          {data.error}
        </p>
      )}

      <dl className="figures">
        {figures.map((f) => (
          <div key={f.label}>
            <dt>{f.label}</dt>
            <dd>{f.value ?? '–'}</dd>
          </div>
        ))}
      </dl>

      <TopQuestions items={data.top} days={data.days} onDaysChange={data.setDays} />
      <UsersTable users={data.users} currentUser={currentUser} onBan={data.ban} onUnban={data.unban} />
    </div>
  );
}
