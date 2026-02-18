/**
 * PROMEOS — ScopeSummary
 * Single source of truth for displaying current org + site count.
 * Reads from ScopeContext so every page shows the exact same value.
 *
 * Usage:
 *   <ScopeSummary />                        → "SCI Les Terrasses · 10 sites"
 *   <ScopeSummary separator=" — " />        → "SCI Les Terrasses — Tous les sites"
 *   <ScopeSummary className="text-sm" />
 *
 * Props:
 *   separator   {string}   between org name and site info (default " · ")
 *   className   {string}   extra Tailwind classes
 *   showCount   {boolean}  show site count when all sites selected (default true)
 */
import { useScope } from '../contexts/ScopeContext';

export default function ScopeSummary({ separator = ' \u00b7 ', className = '', showCount = true }) {
  const { org, scopeLabel, orgSites, sitesCount } = useScope();
  const orgNom = org?.nom || '—';

  let right;
  if (scopeLabel && scopeLabel !== 'Tous les sites') {
    // Single-site mode: "Site : Bureau Paris #01"
    right = scopeLabel;
  } else if (showCount) {
    // All-sites mode: "10 sites" or "Tous les sites" while loading
    right = sitesCount > 0
      ? `${sitesCount}\u00a0site${sitesCount !== 1 ? 's' : ''}`
      : orgSites.length === 0 && org
        ? 'chargement…'
        : 'Tous les sites';
  } else {
    right = 'Tous les sites';
  }

  return (
    <span className={className}>
      {orgNom}{separator}{right}
    </span>
  );
}
