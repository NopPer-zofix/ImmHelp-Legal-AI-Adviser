import { useEffect, useRef } from 'react';
import Message from './Message';

export default function Thread({ chat, pending, onRetry }) {
  const endRef = useRef(null);
  const count = chat.messages.length;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [chat.id, count, pending]);

  return (
    <div className="thread" aria-live="polite">
      <div className="thread-inner">
        {chat.messages.map((m, i) => (
          <Message key={m.id ?? `local-${i}`} message={m} onRetry={onRetry} canRetry={i === count - 1 && !pending} />
        ))}

        {pending && (
          <div className="thinking" role="status">
            <span className="thinking-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            Checking the documents…
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
