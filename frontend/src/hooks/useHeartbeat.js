import { useEffect } from 'react';
import { api } from '../api';

const EVERY_MS = 60_000;

// Tells the server this user has the app open, so admins see real "active sessions".
// Only visible tabs report; a tab left in the background stops counting after ~2 minutes.
export function useHeartbeat(enabled) {
  useEffect(() => {
    if (!enabled) return undefined;
    const beat = () => {
      if (document.visibilityState === 'visible') api.heartbeat().catch(() => {});
    };
    beat();
    const timer = setInterval(beat, EVERY_MS);
    document.addEventListener('visibilitychange', beat);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', beat);
    };
  }, [enabled]);
}
