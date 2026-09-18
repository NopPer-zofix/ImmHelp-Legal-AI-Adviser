import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { timeAgo, shortDate } from '../../lib/format';
import { ROLES } from '../../lib/roles';
import BanDialog from './BanDialog';
import ConfirmDialog from '../ConfirmDialog';

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'active', label: 'Active' },
  { id: 'banned', label: 'Banned' },
];

export default function UsersTable({ users, currentUser, onBan, onUnban }) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [banTarget, setBanTarget] = useState(null);
  const [unbanTarget, setUnbanTarget] = useState(null);
  const [notice, setNotice] = useState('');

  const visible = useMemo(() => {
    if (!users) return [];
    const q = query.trim().toLowerCase();
    return users
      .filter((u) => (filter === 'all' ? true : filter === 'banned' ? u.is_banned : !u.is_banned))
      .filter((u) => !q || u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
      .sort((a, b) => (b.last_active_at ?? '').localeCompare(a.last_active_at ?? ''));
  }, [users, query, filter]);

  // Why the ban button is unavailable for a row, or null if it is available
  const banBlocked = (u) => {
    if (u.id === currentUser.id) return "You can't ban yourself";
    if (u.role === ROLES.ADMIN) return "Admins can't be banned";
    return null;
  };

  return (
    <section className="panel" aria-labelledby="users-h">
      <div className="panel-head">
        <div>
          <h2 id="users-h">Users</h2>
          <p className="panel-note">{users ? `${visible.length} of ${users.length}` : 'Loading…'}</p>
        </div>
        <div className="users-tools">
          <label className="search">
            <Search size={15} aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name or email"
              aria-label="Search users"
            />
          </label>
          <div className="segmented segmented--inline segmented--small" role="radiogroup" aria-label="Status">
            {FILTERS.map((f) => (
              <button key={f.id} role="radio" aria-checked={filter === f.id} onClick={() => setFilter(f.id)}>
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {notice && (
        <p className="panel-notice" role="status">
          {notice}
        </p>
      )}

      <div className="table-wrap">
        <table className="users">
          <thead>
            <tr>
              <th scope="col">User</th>
              <th scope="col">Role</th>
              <th scope="col">Joined</th>
              <th scope="col" className="num">
                Questions
              </th>
              <th scope="col">Last active</th>
              <th scope="col">Status</th>
              <th scope="col">
                <span className="visually-hidden">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((u) => {
              const blocked = banBlocked(u);
              return (
                <tr key={u.id} className={u.is_banned ? 'is-banned' : undefined}>
                  <td>
                    <div className="user-cell">
                      <strong>
                        {u.username}
                        {u.id === currentUser.id && <span className="you"> (you)</span>}
                      </strong>
                      <span>{u.email}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`role role--${u.role}`}>{u.role === ROLES.ADMIN ? 'Admin' : 'User'}</span>
                  </td>
                  <td>{shortDate(u.created_at)}</td>
                  <td className="num">{u.message_count}</td>
                  <td>{timeAgo(u.last_active_at)}</td>
                  <td>
                    {u.is_banned ? (
                      <span className="status status--banned" title={u.banned_reason ?? undefined}>
                        Banned {shortDate(u.banned_at)}
                        {u.banned_reason && <span className="status-reason">{u.banned_reason}</span>}
                      </span>
                    ) : (
                      <span className="status status--active">Active</span>
                    )}
                  </td>
                  <td className="actions">
                    {u.is_banned ? (
                      <button className="btn btn-ghost btn-small" onClick={() => setUnbanTarget(u)}>
                        Unban
                      </button>
                    ) : (
                      <button
                        className="btn btn-ghost btn-ghost--danger btn-small"
                        onClick={() => setBanTarget(u)}
                        disabled={Boolean(blocked)}
                        title={blocked ?? undefined}
                      >
                        Ban
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {users && visible.length === 0 && (
              <tr>
                <td colSpan={7} className="panel-empty">
                  No users match this search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <BanDialog
        user={banTarget}
        onCancel={() => setBanTarget(null)}
        onBan={async (id, reason) => {
          await onBan(id, reason);
          setNotice(`${banTarget.username} is banned.`);
          setBanTarget(null);
        }}
      />

      <ConfirmDialog
        open={unbanTarget != null}
        tone="neutral"
        title={`Unban ${unbanTarget?.username ?? ''}?`}
        body="They'll be able to log in and ask questions again."
        confirmLabel="Unban"
        onCancel={() => setUnbanTarget(null)}
        onConfirm={async () => {
          const target = unbanTarget;
          setUnbanTarget(null);
          try {
            await onUnban(target.id);
            setNotice(`${target.username} is unbanned.`);
          } catch (err) {
            setNotice(`Couldn't unban ${target.username}. ${err.message}`);
          }
        }}
      />
    </section>
  );
}
