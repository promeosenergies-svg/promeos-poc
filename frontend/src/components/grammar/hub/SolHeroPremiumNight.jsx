/**
 * grammar/hub/SolHeroPremiumNight — Hero bleu nuit avec illustration filaire SVG.
 *
 * Composant visuel signature B2B PROMEOS (Loi L11.1 doctrine §12).
 * Background : gradient linear-gradient(135deg, --sol-night-bg, --sol-night-bg-alt).
 * Illustration filaire SVG 8 buildings + connexions + dots en background absolu.
 *
 * Props :
 *   eyebrow  — label mono supérieur (ex. "Briefing du jour · samedi 9 mai")
 *   title    — ReactNode Fraunces 32px (peut contenir <em> pour tonalite secondaire)
 *   sub      — sous-titre Inter 15px
 *   meta     — { quality, confidence, period, scope } footer meta
 *   alerts   — { count, criticalCount } pilule rouge si count > 0
 *   primaryCta — { label, href } bouton blanc principal
 *
 * Source-guards : data-component="SolHeroPremiumNight" data-hero
 * Display-only — zero calcul metier.
 *
 * @param {Object} props
 * @param {string} props.eyebrow - Label mono uppercase
 * @param {React.ReactNode} props.title - Titre display Fraunces (peut contenir <em>)
 * @param {string} props.sub - Sous-titre descriptif
 * @param {{ quality: number, confidence: string, period: string, scope: string }} props.meta
 * @param {{ count: number, criticalCount: number }} [props.alerts]
 * @param {{ label: string, href: string }} [props.primaryCta]
 * @param {string} [props.className='']
 */

/**
 * SVG illustration filaire 8 buildings + connexions + dots — maquette de reference.
 * Opacite globale 0.7 pour ne pas dominer le contenu textuel.
 */
function WireframeSvg() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 520 200"
      xmlns="http://www.w3.org/2000/svg"
      style={{
        position: 'absolute',
        right: 0,
        top: 0,
        width: '60%',
        height: '100%',
        opacity: 0.7,
        pointerEvents: 'none',
      }}
    >
      {/* Building 1 — grand immeuble de bureaux (droite) */}
      <rect
        x="380"
        y="40"
        width="44"
        height="140"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="1"
      />
      <rect
        x="387"
        y="50"
        width="8"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="401"
        y="50"
        width="8"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="415"
        y="50"
        width="5"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="387"
        y="67"
        width="8"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="401"
        y="67"
        width="8"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="415"
        y="67"
        width="5"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="387"
        y="84"
        width="8"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="401"
        y="84"
        width="8"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="415"
        y="84"
        width="5"
        height="10"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <line x1="380" y1="130" x2="424" y2="130" stroke="var(--sol-night-line)" strokeWidth="0.5" />

      {/* Building 2 — tour fine centrale */}
      <rect
        x="440"
        y="20"
        width="28"
        height="160"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="1"
      />
      <rect
        x="446"
        y="30"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="458"
        y="30"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="446"
        y="45"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="458"
        y="45"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="446"
        y="60"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="458"
        y="60"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="446"
        y="75"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="458"
        y="75"
        width="6"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />

      {/* Building 3 — immeuble large droite extreme */}
      <rect
        x="478"
        y="60"
        width="38"
        height="120"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="1"
      />
      <rect
        x="484"
        y="70"
        width="7"
        height="9"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="497"
        y="70"
        width="7"
        height="9"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="484"
        y="85"
        width="7"
        height="9"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="497"
        y="85"
        width="7"
        height="9"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="484"
        y="100"
        width="7"
        height="9"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <rect
        x="497"
        y="100"
        width="7"
        height="9"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />

      {/* Building 4 — petit bâtiment centre-droit */}
      <rect
        x="310"
        y="90"
        width="34"
        height="90"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.8"
      />
      <rect
        x="317"
        y="100"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="330"
        y="100"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="317"
        y="114"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="330"
        y="114"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />

      {/* Building 5 — entrepôt bas gauche */}
      <rect
        x="255"
        y="120"
        width="46"
        height="60"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.8"
      />
      <line x1="255" y1="140" x2="301" y2="140" stroke="var(--sol-night-line)" strokeWidth="0.5" />
      <line x1="255" y1="158" x2="301" y2="158" stroke="var(--sol-night-line)" strokeWidth="0.5" />

      {/* Building 6 — tour moyenne centre */}
      <rect
        x="335"
        y="55"
        width="36"
        height="125"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.8"
      />
      <rect
        x="341"
        y="65"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="354"
        y="65"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="341"
        y="79"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="354"
        y="79"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="341"
        y="93"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="354"
        y="93"
        width="7"
        height="8"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />

      {/* Building 7 — bloc logistique */}
      <rect
        x="210"
        y="105"
        width="38"
        height="75"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.7"
      />
      <line x1="210" y1="125" x2="248" y2="125" stroke="var(--sol-night-line)" strokeWidth="0.5" />

      {/* Building 8 — petit pavillon arriere-plan */}
      <rect
        x="170"
        y="130"
        width="32"
        height="50"
        rx="1"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
      />
      <rect
        x="177"
        y="138"
        width="6"
        height="7"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.5"
      />
      <rect
        x="189"
        y="138"
        width="6"
        height="7"
        rx="0.5"
        fill="none"
        stroke="var(--sol-night-line)"
        strokeWidth="0.5"
      />

      {/* Lignes de connexion inter-bâtiments */}
      <line
        x1="327"
        y1="100"
        x2="335"
        y2="100"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
        strokeDasharray="2,2"
      />
      <line
        x1="371"
        y1="90"
        x2="380"
        y2="90"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
        strokeDasharray="2,2"
      />
      <line
        x1="424"
        y1="80"
        x2="440"
        y2="80"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
        strokeDasharray="2,2"
      />
      <line
        x1="468"
        y1="75"
        x2="478"
        y2="85"
        stroke="var(--sol-night-line)"
        strokeWidth="0.6"
        strokeDasharray="2,2"
      />
      <line
        x1="248"
        y1="130"
        x2="255"
        y2="135"
        stroke="var(--sol-night-line)"
        strokeWidth="0.5"
        strokeDasharray="2,2"
      />
      <line
        x1="202"
        y1="130"
        x2="210"
        y2="130"
        stroke="var(--sol-night-line)"
        strokeWidth="0.5"
        strokeDasharray="2,2"
      />

      {/* Ligne de sol */}
      <line x1="160" y1="180" x2="520" y2="180" stroke="var(--sol-night-line)" strokeWidth="0.5" />

      {/* Dots connexions — normaux */}
      <circle cx="327" cy="100" r="2.5" fill="var(--sol-night-dot)" />
      <circle cx="371" cy="90" r="2.5" fill="var(--sol-night-dot)" />
      <circle cx="424" cy="80" r="2.5" fill="var(--sol-night-dot)" />
      <circle cx="468" cy="75" r="2.5" fill="var(--sol-night-dot)" />
      <circle cx="248" cy="130" r="2" fill="var(--sol-night-dot)" />
      <circle cx="202" cy="130" r="2" fill="var(--sol-night-dot)" />

      {/* Dot anomaly — couleur chaude (anomaly indicator) */}
      <circle cx="395" cy="50" r="3.5" fill="var(--sol-night-dot-hot)" />
      <circle cx="453" cy="30" r="2.5" fill="var(--sol-night-dot-hot)" />
    </svg>
  );
}

export default function SolHeroPremiumNight({
  eyebrow,
  title,
  sub,
  meta = {},
  alerts,
  primaryCta,
  className = '',
}) {
  const { quality, confidence, period, scope } = meta;

  return (
    <div
      data-component="SolHeroPremiumNight"
      data-hero
      className={`relative overflow-hidden mb-5 ${className}`}
      style={{
        background: 'linear-gradient(135deg, var(--sol-night-bg) 0%, var(--sol-night-bg-alt) 100%)',
        borderRadius: '14px',
        padding: '30px 36px 26px',
        color: 'white',
      }}
    >
      {/* Illustration filaire SVG arriere-plan */}
      <WireframeSvg />

      {/* Contenu principal — z-index relatif pour rester au-dessus du SVG */}
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: '24px',
        }}
      >
        {/* Bloc textuel gauche */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Eyebrow */}
          {eyebrow && (
            <div
              className="font-mono uppercase"
              style={{
                fontSize: '10.5px',
                letterSpacing: '0.18em',
                color: 'rgba(255,255,255,0.72)',
                marginBottom: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: '24px',
                  height: '1px',
                  background: 'rgba(255,255,255,0.4)',
                  flexShrink: 0,
                }}
              />
              {eyebrow}
            </div>
          )}

          {/* Title — Fraunces display */}
          {title && (
            <h1
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: '32px',
                fontWeight: 500,
                lineHeight: 1.18,
                letterSpacing: '-0.012em',
                color: 'white',
                margin: '0 0 12px 0',
              }}
            >
              {title}
            </h1>
          )}

          {/* Sub */}
          {sub && (
            <p
              style={{
                fontSize: '15px',
                color: 'var(--sol-night-fg-soft)',
                lineHeight: 1.55,
                maxWidth: '720px',
                margin: '0 0 16px 0',
              }}
            >
              {sub}
            </p>
          )}

          {/* Meta footer */}
          {(quality != null || confidence || period || scope) && (
            <div
              className="font-mono uppercase"
              style={{
                fontSize: '11px',
                letterSpacing: '0.1em',
                color: 'var(--sol-night-fg-meta)',
                display: 'flex',
                flexWrap: 'wrap',
                gap: '10px',
                alignItems: 'center',
              }}
            >
              {quality != null && (
                <span>
                  Qualite{' '}
                  <strong style={{ fontWeight: 600, color: 'rgba(255,255,255,0.82)' }}>
                    {quality} %
                  </strong>
                </span>
              )}
              {quality != null && confidence && (
                <span style={{ color: 'rgba(255,255,255,0.32)' }}>·</span>
              )}
              {confidence && (
                <span>
                  Confiance{' '}
                  {{ high: 'haute', medium: 'moyenne', low: 'basse' }[confidence] ?? confidence}
                </span>
              )}
              {(quality != null || confidence) && period && (
                <span style={{ color: 'rgba(255,255,255,0.32)' }}>·</span>
              )}
              {period && <span>{period}</span>}
              {period && scope && <span style={{ color: 'rgba(255,255,255,0.32)' }}>·</span>}
              {scope && <span>{scope}</span>}
            </div>
          )}
        </div>

        {/* Bloc actions droite */}
        {(alerts?.count > 0 || primaryCta) && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              alignItems: 'flex-end',
              flexShrink: 0,
            }}
          >
            {/* Pilule alertes */}
            {alerts?.count > 0 && (
              <div
                style={{
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(199,73,73,0.6)',
                  borderRadius: '10px',
                  padding: '9px 14px',
                  color: 'rgba(255,230,230,0.95)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  fontWeight: 500,
                  fontSize: '13px',
                }}
              >
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    background: 'rgba(220, 80, 80, 0.9)',
                    flexShrink: 0,
                  }}
                />
                <span>
                  <b>{alerts.count} alertes</b>
                  <span style={{ color: 'rgba(255,230,230,0.65)', margin: '0 4px' }}>·</span>
                  {alerts.criticalCount} critiques
                </span>
              </div>
            )}

            {/* Bouton primaire blanc */}
            {primaryCta && (
              <a
                href={primaryCta.href}
                style={{
                  background: 'white',
                  color: 'var(--sol-night-bg)',
                  borderRadius: '10px',
                  padding: '9px 14px',
                  fontWeight: 500,
                  fontSize: '13.5px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '7px',
                  textDecoration: 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                {primaryCta.label}
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 13 13"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    d="M2.5 6.5h8M7 3l3.5 3.5L7 10"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
