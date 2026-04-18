/**
 * PROMEOS — Cockpit Refonte V2 raw
 *
 * Rupture visuelle complète dans l'esprit de la maquette
 * docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html (V2 raw).
 *
 * Insight produit : "le journal en terrasse" — l'ouvrier et le cadre
 * dirigeant partagent la lecture du journal malgré leur statut social.
 * Slate pro compétent + accents warm éditoriaux familiers.
 *
 * Cette première version utilise des **fixtures** représentatives pour
 * figer le visuel. Prochaine itération : brancher les hooks existants
 * (getNotificationsSummary, getComplianceScoreTrend, etc.) sans toucher
 * à la logique backend.
 */
import { useState } from 'react';

// ─────────────────────────────────────────────────────────────────────────────
// Fixtures (à remplacer par hooks réels en prochaine itération)
// ─────────────────────────────────────────────────────────────────────────────

const DATA = {
  week: 16,
  month: 'avril',
  patrimoine: 'Patrimoine HELIOS',
  sites_count: 5,
  sol_hero: {
    title: 'Contester la facture Lyon de mars auprès d\'EDF Entreprises',
    summary:
      "Vous avez été facturé l'accise T1 sur toute la période, alors que vous êtes basculé en T2 depuis le 15 février. Je peux rédiger le courrier et l'envoyer — vous relisez avant, vous gardez la main pendant 24 h.",
    metrics: [
      { value: '1 847,20\u202F€', label: 'à récupérer' },
      { value: '94\u202F%', label: 'confiance du calcul' },
      { value: '3\u202Fmin', label: 'pour valider' },
    ],
  },
  kpis: [
    {
      label: 'Facture énergie · mars',
      value: '47\u202F382',
      unit: '€ HT',
      delta: { dir: 'up', text: '▲ +8,2\u202F% vs février' },
      headline: 'Hausse tirée par Lyon et Nice — principalement saisonnière, mais une anomalie sur Lyon explique un tiers de l\'écart.',
      source: 'Source · factures · 3 fournisseurs',
    },
    {
      label: 'Conformité Décret tertiaire',
      value: '62',
      unit: '/100',
      delta: { dir: 'down', text: '▼ −3 pts sur 3 mois' },
      headline: 'Vous êtes en zone à risque — trois sites tirent le score vers le bas, Marseille école en tête.',
      source: 'Source · Enedis · mis à jour il y a 23 h',
    },
    {
      label: 'Consommation · patrimoine',
      value: '1\u202F847',
      unit: 'MWh',
      delta: { dir: 'down', text: '▼ −4,1\u202F% vs n−1' },
      headline: 'Vous consommez moins qu\'à la même période l\'an dernier — Paris et Toulouse portent la baisse.',
      source: 'Source · Enedis + GRDF',
    },
  ],
  weekcards: [
    {
      tag: 'À regarder',
      tagKind: 'attention',
      title: 'Marseille école dérive',
      body:
        'Consommation en hausse de **+12 %** sur 90 jours glissants — probablement la CTA défectueuse signalée en février. Je peux générer le plan d\'action.',
      footer: ['chiffré : +4 200 € / an si non-traité', '⌘K'],
    },
    {
      tag: 'À faire',
      tagKind: 'afaire',
      title: 'OPERAT Lyon · 30 sept',
      body:
        'Déclaration annuelle à déposer dans **5 mois**. Je peux préparer le fichier CSV v3.2 à partir de vos données — il vous restera à le déposer.',
      footer: ['préparation : 4 h → 3 min', 'Automatisable'],
    },
    {
      tag: 'Bonne nouvelle',
      tagKind: 'succes',
      title: 'Paris bureaux · BACS validé',
      body:
        'L\'obligation BACS sur Paris est **conforme** depuis le rapport d\'homologation reçu hier. Votre score de conformité gagne **+4 points**.',
      footer: ['conforme · pièce au dossier', '✓ Clean'],
    },
  ],
};

// Helper renderer avec markdown-light (** = bold)
const renderBody = (text) => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**') ? (
      <strong key={i} style={{ color: 'var(--sol-ink-900)', fontWeight: 600 }}>
        {p.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Composants internes (réutilisent tokens + patterns index.css refonte)
// ─────────────────────────────────────────────────────────────────────────────

function LayerToggle({ value, onChange }) {
  const options = [
    { key: 'surface', label: 'Surface' },
    { key: 'inspect', label: 'Inspecter' },
    { key: 'expert', label: 'Expert' },
  ];
  return (
    <div
      style={{
        display: 'inline-flex',
        border: '1px solid var(--sol-rule)',
        borderRadius: 4,
        overflow: 'hidden',
        background: 'var(--sol-bg-paper)',
      }}
    >
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          onClick={() => onChange(o.key)}
          style={{
            padding: '7px 14px',
            fontSize: 12,
            fontWeight: 500,
            fontFamily: 'var(--sol-font-body)',
            background: value === o.key ? 'var(--sol-ink-900)' : 'transparent',
            color: value === o.key ? 'var(--sol-bg-canvas)' : 'var(--sol-ink-500)',
            border: 'none',
            borderRight: '1px solid var(--sol-rule)',
            cursor: 'pointer',
            transition: 'all 120ms ease',
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function SolHero() {
  const h = DATA.sol_hero;
  return (
    <section
      className="sol-hero"
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 24,
        alignItems: 'center',
      }}
    >
      <div>
        <span className="sol-hero-chip">Sol propose · action agentique</span>
        <h3 className="sol-hero-title">{h.title}</h3>
        <p className="sol-hero-sub">{h.summary}</p>
        <div style={{ display: 'flex', gap: 24, marginTop: 14 }}>
          {h.metrics.map((m) => (
            <div key={m.label}>
              <div
                style={{
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 16,
                  fontWeight: 600,
                  color: 'var(--sol-ink-900)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {m.value}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--sol-ink-500)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                }}
              >
                {m.label}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 180 }}>
        <button
          type="button"
          style={{
            fontSize: 13.5,
            fontWeight: 500,
            padding: '9px 16px',
            borderRadius: 4,
            border: '1px solid transparent',
            background: 'var(--sol-calme-fg)',
            color: '#FFFFFF',
            cursor: 'pointer',
          }}
        >
          Voir ce que j'enverrai
        </button>
        <button
          type="button"
          style={{
            fontSize: 13.5,
            fontWeight: 500,
            padding: '9px 16px',
            borderRadius: 4,
            border: 'none',
            background: 'transparent',
            color: 'var(--sol-ink-500)',
            cursor: 'pointer',
          }}
        >
          Plus tard
        </button>
      </div>
    </section>
  );
}

function KpiCard({ kpi }) {
  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-rule)',
        borderRadius: 6,
        padding: '16px 18px 14px',
      }}
    >
      <div className="sol-kpi-label">{kpi.label}</div>
      <div>
        <span className="sol-kpi-value">{kpi.value}</span>
        <span className="sol-kpi-unit">{kpi.unit}</span>
      </div>
      <div className={`sol-kpi-delta-pill ${kpi.delta.dir === 'down' ? 'sol-delta-down' : 'sol-delta-up'}`}>
        {kpi.delta.text}
      </div>
      <p
        style={{
          fontSize: 12.5,
          color: 'var(--sol-ink-500)',
          lineHeight: 1.5,
          margin: '10px 0 0 0',
        }}
      >
        {renderBody(kpi.headline)}
      </p>
      <div className="sol-source-chip" style={{ marginTop: 10 }}>
        {kpi.source}
      </div>
    </div>
  );
}

function WeekCard({ card }) {
  return (
    <div className="sol-week-card">
      <div className={`sol-week-tag sol-tag-${card.tagKind}`}>{card.tag}</div>
      <h4 className="sol-week-card-title">{card.title}</h4>
      <p className="sol-week-card-body">{renderBody(card.body)}</p>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: 14,
          paddingTop: 12,
          borderTop: '1px dashed var(--sol-ink-200)',
          fontSize: 11,
          color: 'var(--sol-ink-500)',
          fontFamily: 'var(--sol-font-mono)',
        }}
      >
        <span>{card.footer[0]}</span>
        <span>{card.footer[1]}</span>
      </div>
    </div>
  );
}

function LoadCurveHPHC() {
  // SVG signature — courbe de charge HP/HC Lyon, hier (pattern maquette V2)
  return (
    <>
      <svg width="100%" height="180" viewBox="0 0 900 180" preserveAspectRatio="none">
        <defs>
          <linearGradient id="cockpit-refonte-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0F172A" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#0F172A" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Bandes tarifaires */}
        <rect x="0" y="0" width="220" height="180" fill="var(--sol-hch-bg)" opacity="0.5" />
        <rect x="220" y="0" width="420" height="180" fill="var(--sol-hph-bg)" opacity="0.5" />
        <rect x="640" y="0" width="260" height="180" fill="var(--sol-hch-bg)" opacity="0.5" />
        {/* Grille */}
        <line x1="0" y1="45" x2="900" y2="45" stroke="#E2E8F0" strokeDasharray="2,3" />
        <line x1="0" y1="90" x2="900" y2="90" stroke="#E2E8F0" strokeDasharray="2,3" />
        <line x1="0" y1="135" x2="900" y2="135" stroke="#E2E8F0" strokeDasharray="2,3" />
        {/* Area fill */}
        <path
          d="M 0,130 L 50,128 L 100,125 L 150,118 L 200,95 L 250,70 L 300,55 L 350,48 L 400,52 L 450,62 L 500,70 L 550,58 L 600,45 L 650,38 L 700,55 L 750,82 L 800,105 L 850,118 L 900,125 L 900,180 L 0,180 Z"
          fill="url(#cockpit-refonte-area)"
        />
        {/* Courbe */}
        <path
          d="M 0,130 L 50,128 L 100,125 L 150,118 L 200,95 L 250,70 L 300,55 L 350,48 L 400,52 L 450,62 L 500,70 L 550,58 L 600,45 L 650,38 L 700,55 L 750,82 L 800,105 L 850,118 L 900,125"
          stroke="var(--sol-ink-900)"
          strokeWidth="1.8"
          fill="none"
          strokeLinejoin="round"
        />
        {/* Point "pic maintenant" */}
        <circle cx="648" cy="38" r="4" fill="var(--sol-calme-fg)" />
        <text x="656" y="34" fontFamily="JetBrains Mono" fontSize="10" fill="var(--sol-calme-fg)" fontWeight="600">
          pic 14h · 118 kW
        </text>
        {/* Légende HP/HC */}
        <text x="10" y="172" fontFamily="JetBrains Mono" fontSize="10" fill="var(--sol-ink-500)">
          HC 00:00 → 06:00
        </text>
        <text x="230" y="172" fontFamily="JetBrains Mono" fontSize="10" fill="var(--sol-hph-fg)" fontWeight="600">
          HP 06:00 → 22:00
        </text>
        <text x="650" y="172" fontFamily="JetBrains Mono" fontSize="10" fill="var(--sol-ink-500)">
          HC 22:00 → 24:00
        </text>
      </svg>
      <div
        style={{
          fontSize: 12.5,
          color: 'var(--sol-ink-500)',
          marginTop: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span>
          <strong style={{ color: 'var(--sol-ink-900)' }}>85 % de votre consommation</strong> tombe
          en heures pleines — attendu pour un bureau. Votre contrat est bien calibré.
        </span>
        <span className="sol-source-chip">Enedis · M023 · complète</span>
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Cockpit Refonte — page orchestration
// ─────────────────────────────────────────────────────────────────────────────

export default function CockpitRefonte() {
  const [layer, setLayer] = useState('surface');

  return (
    <div style={{ padding: '28px 40px 60px' }}>
      {/* Page head : kicker + title + layer toggle */}
      <header
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          paddingBottom: 18,
          borderBottom: '1px solid var(--sol-rule)',
          marginBottom: 24,
        }}
      >
        <div>
          <div className="sol-page-kicker">
            Cockpit · semaine {DATA.week} · {DATA.patrimoine.toLowerCase()}
          </div>
          <h1 className="sol-page-title">
            Bonjour <em>— voici votre semaine</em>
          </h1>
        </div>
        <LayerToggle value={layer} onChange={setLayer} />
      </header>

      {/* Sol headline + subline — ton éditorial */}
      <div>
        <p className="sol-headline">
          Trois points méritent votre attention cette semaine. L'action la plus urgente concerne{' '}
          <em>la facture de mars sur Lyon</em>, que je peux contester à votre place.
        </p>
        <p className="sol-subline">
          Votre patrimoine de {DATA.sites_count} sites consomme au rythme attendu pour la saison. Un site dérive
          de sa trajectoire Décret Tertiaire. Votre prochain comex est dans 11 jours — le rapport sera
          prêt la veille.
        </p>
      </div>

      {/* Sol hero : action agentique proposée */}
      <SolHero />

      {/* Row 3 KPIs signature */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, marginBottom: 28 }}>
        {DATA.kpis.map((k) => (
          <KpiCard key={k.label} kpi={k} />
        ))}
      </div>

      {/* Section "Cette semaine chez vous" — 3 week-cards */}
      <div className="sol-section-head">
        <h2 className="sol-section-title">Cette semaine chez vous</h2>
        <span className="sol-section-meta">3 points · actualisé il y a 47 min</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 32 }}>
        {DATA.weekcards.map((c) => (
          <WeekCard key={c.title} card={c} />
        ))}
      </div>

      {/* Section "Courbe de charge Lyon" — signature HP/HC */}
      <div className="sol-section-head">
        <h2 className="sol-section-title">Courbe de charge — Lyon, hier</h2>
        <span className="sol-section-meta">pas 30 min · HP / HC tarifaires</span>
      </div>
      <LoadCurveHPHC />

      {/* Timerail footer */}
      <div
        className="sol-timerail"
        style={{
          marginTop: 40,
          marginLeft: -40,
          marginRight: -40,
          paddingLeft: 40,
          paddingRight: 40,
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'var(--sol-calme-fg)',
              animation: 'sol-pulse 3s ease-in-out infinite',
            }}
          />
          14 h 32 ·{' '}
          <strong style={{ color: 'var(--sol-hph-fg)' }}>HP</strong> en cours · jusqu'à 22 h
        </span>
        <span style={{ width: 1, height: 16, background: 'var(--sol-ink-200)' }} />
        <span>Sem. {DATA.week} · {DATA.month}</span>
        <span style={{ width: 1, height: 16, background: 'var(--sol-ink-200)' }} />
        <span style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
          Trajectoire DT 2030 :
          <span
            style={{
              width: 120,
              height: 4,
              background: 'var(--sol-ink-200)',
              borderRadius: 2,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <span
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                height: '100%',
                width: '62%',
                background: 'linear-gradient(to right, var(--sol-calme-fg), var(--sol-attention-fg))',
              }}
            />
          </span>
          <span>
            <strong style={{ color: 'var(--sol-ink-900)' }}>−12,4 %</strong> sur −25 % requis · en retard
          </span>
        </span>
        <span style={{ width: 1, height: 16, background: 'var(--sol-ink-200)' }} />
        <span>Sol · en veille · 3 actions en attente</span>
      </div>

      {/* Sol cartouche fixed bas-droit */}
      <button
        type="button"
        role="status"
        aria-live="polite"
        aria-label="Sol propose · 1 847 € à récupérer"
        style={{
          position: 'fixed',
          bottom: 48,
          right: 24,
          zIndex: 50,
          padding: '10px 14px',
          borderRadius: 4,
          border: '1px solid var(--sol-calme-fg)',
          background: 'var(--sol-calme-bg)',
          color: 'var(--sol-ink-700)',
          fontSize: 12.5,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          maxWidth: 340,
          cursor: 'pointer',
          boxShadow: '0 2px 8px rgba(15, 23, 42, 0.06)',
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: 'var(--sol-calme-fg)',
            animation: 'sol-pulse 3s ease-in-out infinite',
          }}
        />
        <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 2 }}>
          <span
            style={{
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 10.5,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: 'var(--sol-ink-500)',
            }}
          >
            Sol
          </span>
          <span style={{ fontWeight: 500, color: 'var(--sol-ink-900)' }}>
            Je propose une action —{' '}
            <span style={{ color: 'var(--sol-calme-fg)', fontWeight: 600 }}>1 847 €</span> à récupérer
          </span>
        </span>
      </button>
    </div>
  );
}
