import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { api } from '../../api';
import { AD_STATUSES, AD_TOPICS, findCategory, statusLabel } from '../../lib/advertisers';
import { shortDate } from '../../lib/format';
import AdvertiserDrawer from './AdvertiserDrawer';

const TABS = [{ id: 'all', label: 'All' }, ...AD_STATUSES];

const hostOf = (url) => {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
};

export default function Advertisers() {
  const [list, setList] = useState(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('all');
  const [openId, setOpenId] = useState(null); // advertiser id, 'new', or null
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      setList(await api.adminAdvertisers());
      setError('');
    } catch (err) {
      setError(
        err.status === 404 || err.status === 405
          ? "This server doesn't have the advertiser API yet. Preview it with npm run dev:mock."
          : err.message,
      );
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const c = { all: list?.length ?? 0 };
    for (const a of list ?? []) c[a.status] = (c[a.status] ?? 0) + 1;
    return c;
  }, [list]);

  const visible = (list ?? []).filter((a) => tab === 'all' || a.status === tab);
  const selected = openId === 'new' ? null : list?.find((a) => a.id === openId) ?? null;

  const onSaved = async (message) => {
    await load();
    if (message) setNotice(message);
  };

  return (
    <div className="dash">
      <div className="dash-head">
        <div>
          <h1>Advertisers</h1>
          <p className="dash-sub">Add companies, check their documents and approve them before any ads run.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setOpenId('new')}>
          <Plus size={16} /> Add advertiser
        </button>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <section className="panel" aria-label="Advertisers">
        <div className="tabs" role="tablist" aria-label="Filter by status">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
              {t.label}
              <span className="tab-count">{counts[t.id] ?? 0}</span>
            </button>
          ))}
        </div>

        {notice && (
          <p className="panel-notice" role="status">
            {notice}
          </p>
        )}

        <div className="table-wrap">
          <table className="users ads-table">
            <thead>
              <tr>
                <th scope="col">Company</th>
                <th scope="col">Category</th>
                <th scope="col">Topics</th>
                <th scope="col">Status</th>
                <th scope="col">Added</th>
                <th scope="col">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {!list && !error && (
                <tr>
                  <td colSpan={6} className="panel-empty">
                    Loading advertisers…
                  </td>
                </tr>
              )}
              {list && visible.length === 0 && (
                <tr>
                  <td colSpan={6} className="panel-empty">
                    {tab === 'pending' ? 'Nothing waiting for review.' : 'No advertisers here yet.'}
                  </td>
                </tr>
              )}
              {visible.map((a) => (
                <tr key={a.id}>
                  <td>
                    <div className="user-cell">
                      <strong>{a.company}</strong>
                      <span>{hostOf(a.website)}</span>
                    </div>
                  </td>
                  <td>{findCategory(a.category).label}</td>
                  <td>
                    <span className="topic-list">
                      {a.topics.map((t) => (
                        <span key={t} className="topic">
                          {AD_TOPICS.find((x) => x.id === t)?.label ?? t}
                        </span>
                      ))}
                    </span>
                  </td>
                  <td>
                    <span className={`pill pill--${a.status}`}>{statusLabel(a.status)}</span>
                    {a.status_reason && a.status !== 'approved' && (
                      <span className="status-reason" title={a.status_reason}>
                        {a.status_reason}
                      </span>
                    )}
                  </td>
                  <td>{shortDate(a.created_at)}</td>
                  <td className="actions">
                    <button className="btn btn-ghost btn-small" onClick={() => setOpenId(a.id)}>
                      {a.status === 'pending' ? 'Review' : 'Open'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <AdvertiserDrawer
        open={openId != null}
        advertiser={selected}
        onClose={() => setOpenId(null)}
        onCreated={async (created) => {
          await onSaved(`${created.company} was added and is waiting for review.`);
          setOpenId(created.id);
        }}
        onSaved={onSaved}
      />
    </div>
  );
}
