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
 *   onRuleClick       — callback optionnel (rule_code) → drawer reason_human
 *
 * Display-only.
 */

const RULE_LABELS = {
  DT: { code: 'DT', label: 'Décret tertiaire' },
  BACS: { code: 'BACS', label: 'Régulation chauffage' },
  APER: { code: 'APER', label: 'EnR parking / toiture' },
  SME: { code: 'SMÉ', label: 'Audit énergétique' },
  BEGES: { code: 'BEGES', label: 'Bilan GES réglementaire' },
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
          return (
            <button
              type="button"
              key={rule}
              onClick={onRuleClick ? () => onRuleClick(rule) : undefined}
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
                cursor: onRuleClick ? 'pointer' : 'default',
              }}
              data-rule={rule}
              data-status={summary.status}
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
