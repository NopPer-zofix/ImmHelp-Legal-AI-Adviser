import { useEffect, useState } from 'react';

// Tiny hash router: "#/admin" → "/admin". Chat links use "#chat-12" and read as "/".
function currentRoute() {
  const hash = window.location.hash;
  return hash.startsWith('#/') ? hash.slice(1) : '/';
}

export function navigate(path) {
  window.location.hash = path === '/' ? '' : path;
  if (path === '/') window.history.replaceState(null, '', window.location.pathname);
  window.dispatchEvent(new HashChangeEvent('hashchange'));
}

export function useHashRoute() {
  const [route, setRoute] = useState(currentRoute);
  useEffect(() => {
    const onChange = () => setRoute(currentRoute());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}
