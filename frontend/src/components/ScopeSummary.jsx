/**
 * PROMEOS — ScopeSummary (Sprint V14)
 * Single source of truth for "N sites" display everywhere.
 *
 * Uses ScopeContext.sitesCount (= orgSites.length from real API) to display:
 *   - When siteId null  : "OrgNom — Tous les sites (N)"
 *   - When siteId set   : "OrgNom — Site : <nom>"
 *
 * Props:
 *   showCount   boolean — show " (N)" after label (default true)
 *   className   string  — extra tailwind classes
 */
import { useScope } from '../contexts/ScopeContext';

export default function ScopeSummary({ showCount = true, className = '' }) {
  const { org, scopeLabel, sitesCount, selectedSiteId } = useScope();

  if (!org) return null;

  const label = selectedSiteId
    ? `${org.nom} — ${scopeLabel}`
    : `${org.nom} — Tous les sites${showCount && sitesCount ? ` (${sitesCount})` : ''}`;

  return (
    <span className={`font-medium text-gray-700 ${className}`} aria-label={label}>
      {label}
    </span>
  );
}
