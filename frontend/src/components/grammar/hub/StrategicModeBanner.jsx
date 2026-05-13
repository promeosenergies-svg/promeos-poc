/**
 * grammar/hub/StrategicModeBanner — Bandeau du mode stratégique en haut de page.
 *
 * Composant visuel cardinal Synthèse Stratégique (ADR-023 §5).
 * Affiche le mode actif (REGULATORY/PERFORMANCE/PROCUREMENT/OPPORTUNITY/
 * DATA_INSUFFICIENT) avec un libellé court + une phrase de contexte + lien
 * "Pourquoi ?" qui ouvre un drawer optionnel.
 *
 * Props :
 *   mode             — string parmi 5 modes (StrategicMode v1.0)
 *   onWhyClick       — callback optionnel pour ouvrir le drawer mode-explanation
 *
 * Display-only — zero calcul metier (le mode est calculé backend).
 */

const MODE_LABELS = {
  regulatory_driven: 'RÉGIME · RÉGLEMENTAIRE',
  performance_driven: 'RÉGIME · PERFORMANCE',
  procurement_driven: 'RÉGIME · ACHAT',
  opportunity_driven: 'RÉGIME · OPPORTUNITÉ',
  data_insufficient: 'RÉGIME · DONNÉES INSUFFISANTES',
};

const MODE_HEADLINES = {
  regulatory_driven: 'Votre patrimoine est assujetti à une trajectoire réglementaire active.',
  performance_driven: 'Aucune trajectoire DT à tenir. Votre contrainte principale est économique.',
  procurement_driven: 'Une fenêtre achat se ferme à court terme. Décision recommandée.',
  opportunity_driven: 'Plusieurs opportunités chiffrées non encore activées.',
  data_insufficient: 'Cadre réglementaire indéterminé. Patrimoine à compléter avant arbitrage.',
};

export default function StrategicModeBanner({ mode, onWhyClick }) {
  const label = MODE_LABELS[mode] || 'RÉGIME · NON STATUÉ';
  const headline = MODE_HEADLINES[mode] || 'Mode non identifié.';
  return (
    <div
      data-component="StrategicModeBanner"
      data-mode={mode}
      className="sol-mode-banner mb-4 flex items-center gap-3 rounded-md px-5 py-3"
      style={{
        background:
          'linear-gradient(90deg, var(--sol-night-bg, #1A1612) 0%, var(--sol-night-bg-alt, #3D362C) 100%)',
        color: 'var(--sol-ink-50, #FAF7F2)',
      }}
    >
      <span
        className="sol-mode-pill"
        style={{
          fontFamily: 'var(--sol-font-mono, "JetBrains Mono", monospace)',
          fontSize: '11px',
          letterSpacing: '0.14em',
          padding: '4px 10px',
          background: 'rgba(255,255,255,0.12)',
          borderRadius: '4px',
        }}
      >
        {label}
      </span>
      <span className="flex-1" style={{ fontSize: '13.5px' }}>
        {headline}
      </span>
      {onWhyClick && (
        <button
          type="button"
          onClick={onWhyClick}
          className="sol-mode-link"
          style={{
            color: 'var(--sol-ink-200, #E5DDD0)',
            textDecoration: 'underline',
            textUnderlineOffset: '3px',
            fontSize: '12.5px',
            background: 'transparent',
            border: 0,
            cursor: 'pointer',
          }}
        >
          Pourquoi ? →
        </button>
      )}
    </div>
  );
}
