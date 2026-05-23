import { useActionCenterV4Impact } from '../../../../hooks/v4';
import { IMPACT_COPY, IMPACT_DIMENSIONS, IMPACT_DIMENSION_ORDER } from '../../constants';

/**
 * M2-5.10.C — Section Impact financier 4 quadrants (maquette §8.5 + drawer
 * détail §8.4 lignes 853-885).
 *
 * Posée dans le drawer détail entre `ItemHeader` et `Tabs`. Lit l'endpoint
 * `GET /api/v4/action-center/items/{id}/impact` via `useActionCenterV4Impact`.
 *
 * Doctrine v0.3 §8.5 : un chiffre € sans source/formule est un chiffre
 * menteur. Quand `value_eur === null`, la card affiche « — » (pas « 0 € »).
 * Quand toutes les dimensions sont vides (has_data=false), un empty state
 * explicite renvoie vers la dette M3+ (engine économique non livré MV3).
 *
 * Fallback gracieux : `error` → ErrorState compact ; le drawer reste lisible
 * sans la section Impact (les onglets ci-dessous restent fonctionnels).
 */

function formatEuro(value) {
  if (value == null) return IMPACT_COPY.noValueDash;
  // Format FR sans décimale, avec espace insécable + « € ».
  // Pas de calcul métier : c'est de la mise en forme pure (règle d'or PROMEOS).
  const rounded = Math.round(value);
  // Affichage compact si grand nombre (k€ pour > 1000).
  if (Math.abs(rounded) >= 1000) {
    const k = (rounded / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 });
    return `${k} k€`;
  }
  return `${rounded.toLocaleString('fr-FR')} €`;
}

function DimensionCard({ dimensionKey, data }) {
  const meta = IMPACT_DIMENSIONS[dimensionKey];
  if (!meta) return null;
  const hasValue = data?.value_eur != null;

  return (
    <div
      className="rounded-[6px] border p-3"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
        borderTop: `3px solid ${meta.accentColor}`,
      }}
    >
      <span
        className="mb-1.5 inline-block cursor-help border-b border-dotted pb-px font-mono text-[9px] font-medium uppercase tracking-[0.16em]"
        style={{ color: 'var(--sol-ink-500)', borderColor: 'var(--sol-ink-400)' }}
        title={meta.tooltip}
      >
        {meta.label}
      </span>
      <div
        className="font-mono text-[22px] font-medium leading-none tracking-[-0.02em] tabular-nums"
        style={{ color: hasValue ? 'var(--sol-ink-900)' : 'var(--sol-ink-400)' }}
      >
        {formatEuro(data?.value_eur)}
      </div>
      {data?.detail && (
        <p
          className="mt-1.5 text-[11px] italic leading-[1.35]"
          style={{
            fontFamily: 'var(--sol-font-display)',
            color: 'var(--sol-ink-500)',
          }}
        >
          {data.detail}
        </p>
      )}
      {(data?.source || data?.formula) && (
        <div
          className="mt-2 border-t border-dashed pt-1.5 font-mono text-[9.5px] tracking-[0.02em]"
          style={{ color: 'var(--sol-ink-500)', borderColor: 'var(--sol-rule)' }}
        >
          {data.source && (
            <div>
              Source · <b style={{ color: 'var(--sol-ink-700)', fontWeight: 500 }}>{data.source}</b>
            </div>
          )}
          {data.formula && (
            <div>
              Formule ·{' '}
              <b style={{ color: 'var(--sol-ink-700)', fontWeight: 500 }}>{data.formula}</b>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ImpactSection({ itemId }) {
  const { data, loading, error } = useActionCenterV4Impact(itemId);

  if (loading) {
    return (
      <section className="my-4" aria-busy="true">
        <div className="grid grid-cols-2 gap-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-[100px] animate-pulse rounded-[6px] border"
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
              }}
            />
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section
        className="my-4 rounded-[6px] border p-3 text-[12.5px]"
        style={{
          background: 'var(--sol-refuse-bg)',
          borderColor: 'var(--sol-refuse-line)',
          color: 'var(--sol-refuse-fg)',
        }}
        role="alert"
      >
        {IMPACT_COPY.errorTitle}
      </section>
    );
  }

  if (!data) return null;

  return (
    <section className="my-4">
      <div
        className="mb-3 flex items-center gap-2 font-mono text-[9.5px] font-semibold uppercase tracking-[0.16em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        <span>{IMPACT_COPY.sectionTitle}</span>
        <span
          className="ml-auto rounded-full border px-1.5 py-px text-[9px] tracking-[0.06em]"
          style={{
            background: 'var(--sol-bg-panel)',
            borderColor: 'var(--sol-rule)',
            color: 'var(--sol-ink-500)',
          }}
        >
          {IMPACT_COPY.sectionPeriodBadge}
        </span>
      </div>

      {!data.has_data ? (
        <div
          className="rounded-[6px] border p-3 text-[12px] leading-[1.5]"
          style={{
            background: 'var(--sol-bg-panel)',
            borderColor: 'var(--sol-rule)',
            color: 'var(--sol-ink-500)',
          }}
        >
          <div
            className="mb-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--sol-ink-700)' }}
          >
            {IMPACT_COPY.emptyTitle}
          </div>
          <p className="text-[11.5px] italic" style={{ fontFamily: 'var(--sol-font-display)' }}>
            {IMPACT_COPY.emptyText}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {IMPACT_DIMENSION_ORDER.map((key) => (
            <DimensionCard key={key} dimensionKey={key} data={data[key]} />
          ))}
        </div>
      )}
    </section>
  );
}
