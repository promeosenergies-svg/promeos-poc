/**
 * components/patrimoine/IncompleteBanner — bandeau affiché en haut de Patrimoine
 * quand l'URL contient `?incomplete=<RULE>`. Le filtre est piloté depuis
 * `CadreApplicable` (Cockpit Stratégique).
 *
 * P0-B 2026-05-23 — explique en français quelle règle est en cause, combien
 * de sites sont concernés, et propose d'effacer le filtre. Si la donnée
 * manquante est au niveau organisation/EJ, affiche un message clair sans
 * casser le parcours (l'écran org est en préparation, hors scope P0-B).
 */

import { AlertTriangle } from 'lucide-react';

const RULE_LABELS_FR = {
  DT: 'Décret Tertiaire',
  BACS: 'Régulation chauffage (BACS)',
  APER: 'EnR parking / toiture (APER)',
  SME: 'Audit énergétique (SMÉ)',
  BEGES: 'Bilan GES réglementaire',
};

export default function IncompleteBanner({ rule, remediation, siteCount, onClear }) {
  const label = RULE_LABELS_FR[rule] || rule;
  const isOrgLevel =
    remediation &&
    (remediation.remediation_level === 'organisation' ||
      remediation.remediation_level === 'entite_juridique');
  return (
    <div
      data-component="PatrimoineIncompleteBanner"
      data-rule={rule}
      role="status"
      className="my-3 rounded-md border px-4 py-3 flex items-start gap-3"
      style={{
        background: 'var(--sol-bg-warn-soft, #FBF1E0)',
        borderColor: 'var(--sol-attention, #C68A3D)',
        color: 'var(--sol-ink-900, #1A1612)',
      }}
    >
      <AlertTriangle size={18} className="shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="font-semibold text-sm" style={{ margin: 0 }}>
          Sites à compléter pour le {label}
          {typeof siteCount === 'number' && siteCount > 0
            ? ` — ${siteCount} site${siteCount > 1 ? 's' : ''}`
            : ''}
        </p>
        {remediation?.remediation_hint_fr && (
          <p className="text-[12.5px] mt-1" style={{ margin: '4px 0 0' }}>
            {remediation.remediation_hint_fr}
          </p>
        )}
        {isOrgLevel && (
          <p
            className="text-[12px] mt-1 italic"
            style={{ margin: '4px 0 0', color: 'var(--sol-ink-500, #7A6E5C)' }}
          >
            À compléter dans les informations de l'organisation{' '}
            <span style={{ opacity: 0.7 }}>(écran en préparation)</span>.
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={onClear}
        className="text-[12px] font-medium underline shrink-0"
        style={{
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--sol-ink-700, #3D362C)',
        }}
        data-action="patrimoine-incomplete-banner-clear"
      >
        Effacer le filtre
      </button>
    </div>
  );
}
