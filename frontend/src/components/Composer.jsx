import { useLayoutEffect, useRef, useState } from 'react';
import { ArrowUp } from 'lucide-react';

const MAX_HEIGHT = 240;

export default function Composer({ onSend, busy, autoFocus = true, placeholder = 'Reply to ImmHelp…', picker = null }) {
  const [value, setValue] = useState('');
  const ref = useRef(null);

  // Grow with the text up to MAX_HEIGHT, then scroll inside
  useLayoutEffect(() => {
    const el = ref.current;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  const canSend = value.trim().length > 0 && !busy;

  async function submit() {
    if (!canSend) return;
    const text = value;
    setValue('');
    const sent = await onSend(text);
    if (!sent) setValue(text); // e.g. the chat couldn't be created — don't lose what was typed
    ref.current?.focus();
  }

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      onClick={() => ref.current.focus()}
    >
      <label htmlFor="composer-input" className="visually-hidden">
        Your question
      </label>
      <textarea
        id="composer-input"
        ref={ref}
        rows={1}
        value={value}
        autoFocus={autoFocus}
        placeholder={placeholder}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <div className="composer-row">
        <span className="composer-hint">Shift + Enter for a new line</span>
        {picker}
        <button className="send-btn" disabled={!canSend} aria-label="Send">
          <ArrowUp size={18} strokeWidth={2.25} />
        </button>
      </div>
    </form>
  );
}
