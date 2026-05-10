/**
 * grammar/hub/HubPage — Wrapper compound component L11 Hub Page.
 *
 * Doctrine Sol §12 Loi L11 Hub Page : enveloppe canonique pour toutes
 * les pages-hub PROMEOS (Briefing, Energie, Conformite, Factures, Achat, Patrimoine).
 *
 * Compound components :
 *   HubPage.KpiTriptych — exactement 3 enfants KpiCard
 *   HubPage.ChartPair   — exactement 2 enfants ChartFrame
 *   HubPage.Highlights  — 3 a 5 enfants HubHighlight avec header titre + lien
 *
 * Validation runtime DEV (NODE_ENV !== 'production') : console.error si
 * cardinalites violees. Ne throw pas — le rendu se fait avec avertissement.
 *
 * Piliers acceptes : briefing | energie | conformite | factures | achat | patrimoine
 * Contenant : max-w-[1180px] mx-auto px-7 py-6
 *
 * Display-only — zero calcul metier (doctrine PROMEOS regle d'or).
 *
 * @param {Object} props
 * @param {'briefing'|'energie'|'conformite'|'factures'|'achat'|'patrimoine'} props.pillar
 * @param {React.ReactNode} props.children
 * @param {string} [props.className='']
 */

const VALID_PILLARS = ['briefing', 'energie', 'conformite', 'factures', 'achat', 'patrimoine'];

/**
 * Slot KpiTriptych — grille 3 colonnes pour 3 KpiCard.
 * Validation DEV : exactement 3 enfants.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - Exactement 3 KpiCard
 */
function KpiTriptych({ children }) {
  if (process.env.NODE_ENV !== 'production') {
    const count = Array.isArray(children) ? children.length : children ? 1 : 0;
    if (count !== 3) {
      // eslint-disable-next-line no-console
      console.error(
        `[HubPage.KpiTriptych] Loi L11.2 : KpiTriptych attend exactement 3 enfants, recu ${count}. PROMEOS doctrine §12.`
      );
    }
  }
  return (
    <div data-testid="hub-kpi-triptych" className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mb-5">
      {children}
    </div>
  );
}

/**
 * Slot ChartPair — grille 2 colonnes pour 2 ChartFrame.
 * Validation DEV : exactement 2 enfants.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - Exactement 2 ChartFrame
 */
function ChartPair({ children }) {
  if (process.env.NODE_ENV !== 'production') {
    const count = Array.isArray(children) ? children.length : children ? 1 : 0;
    if (count !== 2) {
      // eslint-disable-next-line no-console
      console.error(
        `[HubPage.ChartPair] Loi L11.2 : ChartPair attend exactement 2 enfants, recu ${count}. PROMEOS doctrine §12.`
      );
    }
  }
  return (
    <div data-testid="hub-chart-pair" className="grid grid-cols-1 md:grid-cols-2 gap-3.5 mb-5">
      {children}
    </div>
  );
}

/**
 * Slot Highlights — section Top priorites avec header titre + lien optionnel.
 * Validation DEV : 3 a 5 enfants HubHighlight.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - 3 a 5 HubHighlight
 * @param {string} [props.title] - Titre de la section (ex. "Top 3 priorites")
 * @param {string} [props.linkAll] - Href "Voir tout" (ex. "/centre-action")
 */
function Highlights({ children, title, linkAll }) {
  if (process.env.NODE_ENV !== 'production') {
    const count = Array.isArray(children) ? children.length : children ? 1 : 0;
    if (count < 3 || count > 5) {
      // eslint-disable-next-line no-console
      console.error(
        `[HubPage.Highlights] Loi L11.2 : Highlights attend 3 a 5 enfants, recu ${count}. PROMEOS doctrine §12.`
      );
    }
  }
  return (
    <section data-testid="hub-highlights" className="mb-5">
      {(title || linkAll) && (
        <div className="flex items-center justify-between mb-3">
          {title && (
            <span
              className="font-mono text-[10.5px] uppercase tracking-[0.14em]"
              style={{ color: 'var(--sol-ink-500)' }}
            >
              {title}
            </span>
          )}
          {linkAll && (
            <a
              href={linkAll}
              className="font-mono text-[10.5px] uppercase tracking-[0.1em] hover:underline"
              style={{ color: 'var(--sol-calme-fg)' }}
            >
              Voir tout →
            </a>
          )}
        </div>
      )}
      <div className="space-y-2">{children}</div>
    </section>
  );
}

/**
 * HubPage — composant racine.
 */
export default function HubPage({ pillar, children, className = '' }) {
  if (process.env.NODE_ENV !== 'production') {
    if (!VALID_PILLARS.includes(pillar)) {
      // eslint-disable-next-line no-console
      console.error(
        `[HubPage] pillar "${pillar}" invalide. Valeurs acceptees : ${VALID_PILLARS.join(' | ')}. PROMEOS doctrine §12.`
      );
    }
  }

  return (
    <main
      data-component="HubPage"
      data-pillar={pillar}
      className={`max-w-[1180px] mx-auto px-7 py-6 ${className}`}
    >
      {children}
    </main>
  );
}

HubPage.KpiTriptych = KpiTriptych;
HubPage.ChartPair = ChartPair;
HubPage.Highlights = Highlights;
