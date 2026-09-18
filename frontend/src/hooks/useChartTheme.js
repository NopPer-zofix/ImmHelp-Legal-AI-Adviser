import { useEffect, useState } from 'react';

// Recharts takes colours as plain strings, so read the CSS tokens and re-read on theme change
const TOKENS = ['--ink', '--ink-2', '--ink-3', '--line', '--surface', '--accent', '--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5'];

function read() {
  const css = getComputedStyle(document.documentElement);
  return Object.fromEntries(TOKENS.map((t) => [t.slice(2), css.getPropertyValue(t).trim()]));
}

export function useChartTheme() {
  const [theme, setTheme] = useState(read);
  useEffect(() => {
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setTheme(read());
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);
  return theme;
}
