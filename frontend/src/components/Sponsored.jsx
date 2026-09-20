import { ExternalLink } from 'lucide-react';
import { findCategory, hostOf } from '../lib/advertisers';

// The sponsored slot that /ask returns next to an answer. It is rendered as its
// own labelled block, outside the answer's prose, so paid placement is never
// mistaken for part of the guidance.
export default function Sponsored({ ad }) {
  if (!ad?.company) return null;

  const label = ad.label || 'Sponsored';
  const category = findCategory(ad.category).label;

  return (
    <aside className="sponsored" aria-label={label}>
      <span className="sponsored-label">{label}</span>
      <div className="sponsored-body">
        <strong className="sponsored-company">{ad.company}</strong>
        <span className="sponsored-category">{category}</span>
      </div>
      {ad.website && (
        <a className="sponsored-link" href={ad.website} target="_blank" rel="sponsored noreferrer">
          {hostOf(ad.website)}
          <ExternalLink size={13} aria-hidden="true" />
        </a>
      )}
    </aside>
  );
}
