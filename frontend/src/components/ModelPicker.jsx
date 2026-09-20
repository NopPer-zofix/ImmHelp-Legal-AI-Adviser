import { useCallback, useRef, useState } from 'react';
import { Check, ChevronDown, Lock } from 'lucide-react';
import { useDismiss } from '../hooks/useDismiss';

export default function ModelPicker({ model, models, unlocked, onSelect, onLocked }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(open, close, ref);

  const choose = (m) => {
    setOpen(false);
    if (m.pro && !unlocked) onLocked();
    else onSelect(m.id);
  };

  return (
    // Stop clicks from reaching the composer, which would steal focus into the textarea
    <div className="model-picker" ref={ref} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        className="model-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Model: ${model.name}`}
        onClick={() => setOpen((v) => !v)}
      >
        {model.name}
        <ChevronDown size={14} />
      </button>

      {open && (
        <div className="menu model-menu" role="listbox" aria-label="Choose a model">
          {models.map((m) => {
            const locked = m.pro && !unlocked;
            const selected = m.id === model.id;
            return (
              <button
                type="button"
                key={m.id}
                role="option"
                aria-selected={selected}
                className={`model-option${locked ? ' is-locked' : ''}`}
                onClick={() => choose(m)}
              >
                <span className="model-option-text">
                  <span className="model-option-name">
                    {m.name}
                    {m.pro && <span className="plan-badge">Pro</span>}
                  </span>
                  <span className="model-option-desc">{m.description}</span>
                </span>
                {selected && <Check size={16} className="model-check" />}
                {locked && <Lock size={14} className="model-lock" aria-label="Requires Pro" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
