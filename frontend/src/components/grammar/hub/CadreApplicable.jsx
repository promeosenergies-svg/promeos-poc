/**
 * grammar/hub/CadreApplicable — Bloc « Mon cadre applicable » sous le hero.
 *
 * Affiche un grid de 5 règles (DT, BACS, APER, SMÉ, BEGES) avec leur statut
 * APPLICABLE / NOT_APPLICABLE / UNKNOWN / DATA_MISSING.
 *
 * Props :
 *   applicability     — dict { DT: [{...}], BACS: [...], ... } provenant
 *                       du backend (ADR-024 schema RuleApplicability.to_dict)
 *   maturity          — float [0..1] (rendu en %)
 *   onRuleClick       — callback optionnel (rule_code) — appelé si fourni,
 *                       sinon comportement par défaut P0-B : ouvre un panneau
 *                       interne "Données à compléter" avec CTA vers
 *                       /patrimoine?incomplete=<RULE>.
 *
 * P0-B 2026-05-23 : interactif — clic sur une carte DATA_MISSING affiche
 * un panneau listant les sites concernés + leur champ manquant + un CTA
 * navigant vers la page Patrimoine filtrée.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const RULE_LABELS = {
  DT: { code: 'DT', label: 'Décret tertiaire' },
  BACS: { code: 'BACS', label: 'Régulation chauffage' },
  APER: { code: 'APER', label: 'EnR parking / toiture' },
  SME: { code: 'SMÉ', label: 'Audit énergétique' },
  BEGES: { code: 'BEGES', label: 'Bilan GES réglementaire' },
};

// P0 cleanup cockpit (2026-05-25) — Mapping code Cockpit → param chip
// /conformite. Aligné avec ConformitePage.REGULATION_CHIPS (post PR #300).
// SMÉ et BEGES sont groupés sous le chip 'audit-sme' qui couvre les codes
// audit_sme + audit_energetique + beges + bilan_ges.
const CONFORMITE_REGULATION_PARAM = {
  DT: 'dt',
  BACS: 'bacs',
  APER: 'aper',
  SME: 'audit-sme',
  BEGES: 'audit-sme',
};

const STATUS_TIER = {
  applicable: 'applicable',
  not_applicable: 'not_applicable',
  unknown: 'unknown',
  data_missing: 'data_missing',
};

function summarizeRule(entries) {
  if (!entries || entries.length === 0) return { status: 'unknown', count: 0 };
  // Statut prédominant : APPLICABLE > DATA_MISSING > UNKNOWN > NOT_APPLICABLE
  const order = ['applicable', 'data_missing', 'unknown', 'not_applicable'];
  for (const status of order) {
    const matches = entries.filter((e) => e.status === status);
    if (matches.length > 0) return { status, count: matches.length };
  }
  return { status: entries[0].status, count: entries.length };
}

export default function CadreApplicable({ applicability = {}, maturity, onRuleClick }) {
  const rules = ['DT', 'BACS', 'APER', 'SME', 'BEGES'];
  const maturityPct = Math.round((maturity ?? 0) * 100);
  const [openRule, setOpenRule] = useState(null);
  // useNavigate peut être undefined hors RouterProvider (cas Storybook/test isolé) → fallback.
  let navigate = null;
  try {
    navigate = useNavigate();
  } catch (_e) {
    navigate = null;
  }

  const handleTileClick = (rule, summary) => {
    if (onRuleClick) {
      onRuleClick(rule, summary);
      return;
    }
    if (summary.status === 'data_missing') {
      setOpenRule(rule);
      return;
    }
    // P0 cleanup cockpit (2026-05-25) — Si applicable / unknown, drill-down
    // vers /conformite filtré sur la règle (chip réglementaire pré-sélectionnée).
    // Aligne avec ConformitePage P2-A simplification + cleanup sidebar #300.
    if (summary.status === 'applicable' || summary.status === 'unknown') {
      const param = CONFORMITE_REGULATION_PARAM[rule];
      if (!param) return;
      const target = `/conformite?regulation=${param}`;
      if (navigate) {
        navigate(target);
      } else if (typeof window !== 'undefined') {
        window.location.assign(target);
      }
    }
  };

  const handleClose = () => setOpenRule(null);

  const handleCtaNavigate = (rule) => {
    handleClose();
    if (navigate) {
      navigate(`/patrimoine?incomplete=${rule}`);
    } else if (typeof window !== 'undefined') {
      window.location.assign(`/patrimoine?incomplete=${rule}`);
    }
  };

  return (
    <section
      data-component="CadreApplicable"
      className="sol-cadre mb-5 rounded-md border p-5"
      style={{
        background: 'var(--sol-bg-card, #FFFFFF)',
        borderColor: 'var(--sol-ink-200, #E5DDD0)',
      }}
    >
      <header className="mb-3 flex items-baseline justify-between">
        <h2
          className="sol-cadre-title"
          style={{
            fontFamily: 'var(--sol-font-display, "Fraunces", serif)',
            fontSize: '18px',
            color: 'var(--sol-ink-900, #1A1612)',
            margin: 0,
          }}
        >
          Mon cadre applicable
        </h2>
        <span
          className="sol-mono"
          style={{
            fontFamily: 'var(--sol-font-mono, monospace)',
            fontSize: '11px',
            color: 'var(--sol-ink-500, #7A6E5C)',
          }}
        >
          Maturité patrimoine · {maturityPct} %
        </span>
      </header>
      <div className="grid grid-cols-5 gap-3">
        {rules.map((rule) => {
          const meta = RULE_LABELS[rule];
          const summary = summarizeRule(applicability[rule]);
          const tierClass = STATUS_TIER[summary.status] || 'unknown';
          // P0 cleanup cockpit (2026-05-25) — Toutes les règles deviennent
          // cliquables (sauf not_applicable). applicable/unknown drill-down
          // vers /conformite?regulation=X, data_missing ouvre le panneau
          // interne avec CTA vers /patrimoine?incomplete=X.
          const isClickable =
            onRuleClick != null ||
            summary.status === 'data_missing' ||
            summary.status === 'applicable' ||
            summary.status === 'unknown';
          return (
            <button
              type="button"
              key={rule}
              onClick={isClickable ? () => handleTileClick(rule, summary) : undefined}
              className={`sol-cadre-rule sol-cadre-rule--${tierClass} rounded-md p-3 text-left transition`}
              style={{
                background:
                  tierClass === 'applicable'
                    ? 'var(--sol-bg-success-soft, #EAF2EB)'
                    : tierClass === 'data_missing'
                      ? 'var(--sol-bg-warn-soft, #FBF1E0)'
                      : 'var(--sol-bg-paper, #FAF7F2)',
                borderColor:
                  tierClass === 'applicable'
                    ? 'var(--sol-succes, #3F7C5A)'
                    : tierClass === 'data_missing'
                      ? 'var(--sol-attention, #C68A3D)'
                      : 'var(--sol-ink-200, #E5DDD0)',
                borderWidth: '1px',
                borderStyle: 'solid',
                opacity: tierClass === 'not_applicable' ? 0.55 : 1,
                cursor: isClickable ? 'pointer' : 'default',
              }}
              data-rule={rule}
              data-status={summary.status}
              data-actionable={isClickable ? 'true' : 'false'}
            >
              <span
                style={{
                  fontFamily: 'var(--sol-font-mono, monospace)',
                  fontSize: '11px',
                  letterSpacing: '0.10em',
                  color: 'var(--sol-ink-500, #7A6E5C)',
                  display: 'block',
                }}
              >
                {meta.code}
              </span>
              <span
                style={{
                  fontFamily: 'var(--sol-font-display, serif)',
                  fontSize: '14px',
                  color: 'var(--sol-ink-900, #1A1612)',
                  display: 'block',
                  margin: '4px 0 6px',
                }}
              >
                {meta.label}
              </span>
              <span
                style={{
                  fontSize: '11.5px',
                  color:
                    tierClass === 'applicable'
                      ? 'var(--sol-succes, #2F5C44)'
                      : 'var(--sol-ink-700, #3D362C)',
                  fontWeight: tierClass === 'applicable' ? 600 : 400,
                }}
              >
                {labelForStatus(summary.status, summary.count)}
              </span>
            </button>
          );
        })}
      </div>

      {openRule && !onRuleClick && (
        <DataMissingPanel
          rule={openRule}
          entries={(applicability[openRule] || []).filter((e) => e.status === 'data_missing')}
          onClose={handleClose}
          onCta={() => handleCtaNavigate(openRule)}
        />
      )}
    </section>
  );
}

function labelForStatus(status, count) {
  switch (status) {
    case 'applicable':
      return count > 1 ? `Applicable · ${count} sites` : 'Applicable';
    case 'not_applicable':
      return 'Non applicable';
    case 'data_missing':
      return count > 1 ? `Données manquantes · ${count} sites` : 'Données manquantes';
    case 'unknown':
      return 'À qualifier';
    default:
      return '—';
  }
}

/**
 * Panneau "Données à compléter" — interne à CadreApplicable.
 *
 * Affiche : titre règle, liste des sites concernés avec leur champ manquant
 * et explication courte FR, puis un seul CTA "Compléter dans Patrimoine"
 * qui navigue vers `/patrimoine?incomplete=<RULE>`.
 *
 * Pas de nouvelle page créée — réutilise Patrimoine existante.
 */
function DataMissingPanel({ rule, entries, onClose, onCta }) {
  const meta = RULE_LABELS[rule];
  const ctaLabel =
    entries.find((e) => e.cta_label_fr)?.cta_label_fr || 'Compléter dans Patrimoine';
  return (
    <div
      role="dialog"
      aria-label={`Données à compléter — ${meta.label}`}
      data-component="CadreApplicable.DataMissingPanel"
      data-rule={rule}
      className="mt-4 rounded-md border p-4"
      style={{
        background: 'var(--sol-bg-paper, #FAF7F2)',
        borderColor: 'var(--sol-attention, #C68A3D)',
      }}
    >
      <header className="mb-3 flex items-center justify-between">
        <h3
          style={{
            fontFamily: 'var(--sol-font-display, serif)',
            fontSize: '15px',
            color: 'var(--sol-ink-900, #1A1612)',
            margin: 0,
          }}
        >
          Données à compléter — {meta.label}
        </h3>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fermer"
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            fontSize: '14px',
            color: 'var(--sol-ink-500, #7A6E5C)',
          }}
        >
          ✕
        </button>
      </header>

      {entries.length === 0 ? (
        <p style={{ fontSize: '13px', color: 'var(--sol-ink-700, #3D362C)' }}>
          Aucune donnée à compléter pour cette règle.
        </p>
      ) : (
        <ul
          style={{
            listStyle: 'none',
            padding: 0,
            margin: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          {entries.map((e) => (
            <li
              key={`${e.scope_level}-${e.scope_id}-${e.reason_code}`}
              data-scope-id={e.scope_id}
              data-remediation-field={e.remediation_field}
              style={{
                background: 'var(--sol-bg-card, #FFFFFF)',
                border: '1px solid var(--sol-ink-200, #E5DDD0)',
                borderRadius: '6px',
                padding: '10px 12px',
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--sol-font-mono, monospace)',
                  fontSize: '11px',
                  color: 'var(--sol-ink-500, #7A6E5C)',
                  letterSpacing: '0.05em',
                }}
              >
                {e.scope_label || `${e.scope_level} #${e.scope_id ?? '—'}`}
              </div>
              <div
                style={{
                  fontSize: '13.5px',
                  color: 'var(--sol-ink-900, #1A1612)',
                  marginTop: '2px',
                  fontWeight: 600,
                }}
              >
                {e.remediation_label_fr || 'Donnée manquante'}
              </div>
              {e.remediation_hint_fr && (
                <p
                  style={{
                    fontSize: '12.5px',
                    color: 'var(--sol-ink-700, #3D362C)',
                    margin: '4px 0 0',
                  }}
                >
                  {e.remediation_hint_fr}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={onCta}
          data-action="cadre-applicable-cta-patrimoine"
          style={{
            background: 'var(--sol-attention, #C68A3D)',
            color: '#FFFFFF',
            border: 'none',
            padding: '8px 14px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: 600,
          }}
        >
          {ctaLabel}
        </button>
      </div>
    </div>
  );
}
