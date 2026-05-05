/**
 * TraceTooltip — wrapper d'Explain pour métriques sourcées (Sprint C-3 Phase 3.5).
 *
 * Comble GAP audit Phase B R10 (TraceTooltip réglementaire FE — différenciateur
 * cardinal vs Deepki / Spacewell / Energisme). Chaque chiffre / label réglementaire
 * dans l'UI peut être tracé jusqu'à sa source légale (Légifrance / CRE / ADEME).
 *
 * Architecture (ADR Phase 3.1) :
 * - Composition via `Explain.content` (pas refactor d'Explain)
 * - Hook `useRegulatorySource(termId)` Phase 3.3 consommé pour fetch SoT
 *   `backend/config/sources_reglementaires.yaml` (68 termes, 11 domaines)
 * - Fallback graceful : term inconnu / loading / erreur → enfants seuls (no crash)
 *
 * Usage typique :
 *   <TraceTooltip termId="COMPLIANCE_DT_PENALTY_EUR">7 500 € / site</TraceTooltip>
 *   <TraceTooltip termId="CO2_FACTOR_ELEC_KGCO2_PER_KWH">0,052 kgCO₂/kWh</TraceTooltip>
 *
 * Props :
 *   - termId : clé YAML (ex "COMPLIANCE_DT_PENALTY_EUR", "CO2_FACTOR_ELEC_KGCO2_PER_KWH")
 *   - children : ReactNode affiché (la valeur cliquable/hoverable)
 *   - position : 'top' | 'bottom' (défaut top, propagé à Explain)
 *   - className : classes additionnelles
 */
import React from 'react';
import Explain from './Explain';
import { useRegulatorySource } from '../contexts/RegulatoryRatesContext';

export default function TraceTooltip({ termId, children, position = 'top', className = '' }) {
  const trace = useRegulatorySource(termId);

  // Fallback graceful : term inconnu / loading / erreur → enfants seuls (pas de crash)
  if (!trace) {
    return <span className={className}>{children}</span>;
  }

  // Sprint C-4 Phase 4.2d (ADR-010) — termes en attente de vérification source officielle :
  // certaines sources réglementaires (Légifrance/CRE/RTE) n'ont pas pu être vérifiées via
  // WebFetch (allow-list). Pour ces termes, on AFFICHE valeur + bannière warning au lieu
  // du lien externe (évite redirection 404 + transparence sur l'incertitude). Différenciateur
  // R10 préservé : PROMEOS ne ment jamais sur ses sources.
  const isPendingVerification = trace.status === 'pending_source_verification';

  const tooltipContent = (
    <div className="space-y-1.5 text-xs">
      <div>
        <strong className="text-gray-900">Valeur :</strong>
        <span className="font-mono ml-1 text-gray-700">
          {String(trace.value)} {trace.unit}
        </span>
      </div>
      <div className="text-gray-700">
        <strong className="text-gray-900">Source :</strong> {trace.source.label}
      </div>
      {isPendingVerification ? (
        <div className="text-amber-700 text-[11px] italic bg-amber-50 px-1.5 py-0.5 rounded">
          ⚠️ Source en cours de vérification (Sprint C-7+)
        </div>
      ) : (
        trace.source.url && (
          <a
            href={trace.source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline block break-all"
          >
            {trace.source.version} · applicable depuis {trace.source.effective_date} →
          </a>
        )
      )}
      {trace.formula && (
        <div className="text-gray-600 italic">
          <strong className="text-gray-900 not-italic">Formule :</strong>{' '}
          <code className="text-[11px]">{trace.formula}</code>
        </div>
      )}
      {trace.notes && <div className="text-gray-500 text-[11px]">{trace.notes}</div>}
    </div>
  );

  return (
    <Explain content={tooltipContent} position={position} className={className}>
      {children}
    </Explain>
  );
}
