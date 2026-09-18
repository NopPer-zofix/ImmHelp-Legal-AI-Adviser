import { useCallback, useState } from 'react';
import { modelPref } from '../lib/storage';
import { DEFAULT_MODEL_ID, MODELS, findModel } from '../lib/models';

export function useModel(user, isPro) {
  const [selectedId, setSelectedId] = useState(() => modelPref.load(user.id) ?? DEFAULT_MODEL_ID);

  // A Pro-only choice falls back to the default once Pro ends
  const selected = findModel(selectedId);
  const model = selected.pro && !isPro ? findModel(DEFAULT_MODEL_ID) : selected;

  const select = useCallback(
    (id) => {
      const next = findModel(id);
      if (next.pro && !isPro) return false;
      modelPref.save(user.id, next.id);
      setSelectedId(next.id);
      return true;
    },
    [user.id, isPro],
  );

  return { model, models: MODELS, select };
}
