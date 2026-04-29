/**
 * SolCockpitHeaderPills — pills info droite (alertes / EPEX) + CTA Centre d'action.
 *
 * Phase 1.2 du sprint refonte cockpit dual sol2 (29/04/2026). Affiche les
 * pills contextuelles à droite du header Cockpit + le bouton CTA primary
 * vers /actions. Sert les 2 vues (Briefing du jour + Synthèse stratégique).
 *
 * Cibles maquettes :
 *   - `cockpit-pilotage-briefing-jour.html` lignes 229-235
 *   - `cockpit-synthese-strategique.html` même section
 *
 * Composant pur display (doctrine §8.1) — props-driven, zero fetch.
 * Endpoint backend ciblé Phase 1.2bis :
 *   - `/api/cockpit/_facts.alerts` → alertsCount (à câbler côté caller)
 *   - `/api/action-center/actions/summary` → CTA (handler caller)
 *
 * Props :
 *   - alertsCount : number — nombre d'alertes (pill amber si > 0)
 *   - epexPriceEurMwh : number | null — prix marché spot (pill optionnel)
 *   - onActionCenterClick : function — handler CTA (sinon navigate /actions)
 *   - className : string
 */
import { useNavigate } from 'react-router-dom';

export default function SolCockpitHeaderPills({
  alertsCount = 0,
  epexPriceEurMwh = null,
  onActionCenterClick = null,
  className = '',
}) {
  const navigate = useNavigate();

  const handleCta = () => {
    if (onActionCenterClick) {
      onActionCenterClick();
    } else {
      navigate('/actions');
    }
  };

  return (
    <div
      data-testid="sol-cockpit-header-pills"
      className={`flex items-center gap-1.5 flex-wrap ${className}`}
    >
      {alertsCount > 0 && (
        <span
          data-testid="sol-cockpit-pill-alerts"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
          style={{
            background: 'var(--sol-attention-bg, rgba(192,151,0,.08))',
            color: 'var(--sol-attention-fg, #8a6c00)',
            border: '0.5px solid var(--sol-attention-line, rgba(192,151,0,.2))',
          }}
        >
          <span
            aria-hidden="true"
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: 'var(--sol-attention-fg, #8a6c00)' }}
          />
          {alertsCount} alerte{alertsCount > 1 ? 's' : ''}
        </span>
      )}
      {epexPriceEurMwh != null && epexPriceEurMwh > 0 && (
        <span
          data-testid="sol-cockpit-pill-epex"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs"
          style={{
            background: 'var(--sol-bg-canvas, #f7f5ef)',
            color: 'var(--sol-ink-700)',
            border: '0.5px solid var(--sol-line, rgba(26,24,21,.12))',
          }}
        >
          EPEX {Math.round(epexPriceEurMwh)} €/MWh
        </span>
      )}
      <button
        type="button"
        onClick={handleCta}
        data-testid="sol-cockpit-cta-action-center"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-white hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]"
        style={{ background: 'var(--sol-ink-900, #1a1815)' }}
        aria-label="Ouvrir le centre d'action"
      >
        Centre d&apos;action →
      </button>
    </div>
  );
}
