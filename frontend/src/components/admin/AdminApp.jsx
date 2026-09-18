import { ArrowLeft, ChartLine, LayoutDashboard, LogOut, Megaphone } from 'lucide-react';
import { navigate } from '../../hooks/useHashRoute';
import Dashboard from './Dashboard';
import Advertisers from './Advertisers';
import Analytics from './Analytics';

const NAV = [
  { path: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/admin/analytics', label: 'Analytics', icon: ChartLine },
  { path: '/admin/ads', label: 'Advertisers', icon: Megaphone },
];

export default function AdminApp({ user, route, onLogout }) {
  const page = NAV.find((n) => n.path === route) ?? NAV[0];

  return (
    <div className="admin">
      <header className="admin-bar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">👽</span>
          ImmHelp <span className="admin-tag">Admin</span>
        </div>

        <nav className="admin-nav" aria-label="Admin pages">
          {NAV.map(({ path, label, icon: Icon }) => (
            <a key={path} href={`#${path}`} aria-current={page.path === path ? 'page' : undefined}>
              <Icon size={16} /> {label}
            </a>
          ))}
        </nav>

        <div className="admin-bar-end">
          <button className="btn btn-ghost btn-small" onClick={() => navigate('/')}>
            <ArrowLeft size={14} /> Back to chat
          </button>
          <button className="icon-btn" onClick={onLogout} aria-label="Log out" title={`Log out ${user.email}`}>
            <LogOut size={17} />
          </button>
        </div>
      </header>

      <main className="admin-main">
        {page.path === '/admin' && <Dashboard currentUser={user} />}
        {page.path === '/admin/analytics' && <Analytics />}
        {page.path === '/admin/ads' && <Advertisers />}
      </main>
    </div>
  );
}
